#!/usr/bin/env python3
"""
Build bundled Kanripo work metadata for plugin-kanripo-import.

Reads bundled CSVs under ``data/metadata/sources/`` and ``data/concordance/``.
When a KR_ID maps to a DZID, full Daozang metadata (all authors, vols, dates)
is merged in from ``dz_metadata_*`` tables.

Output: data/metadata/krp_works_by_id.json + manifest.json
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import shutil
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

_DATES_RE = re.compile(r"^\s*(-?\d+)\s*-\s*(-?\d+)\s*$")
_EXTENT_RE = re.compile(r"(\d+)")


def _plugin_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _sources_dir() -> Path:
    return _plugin_root() / "data" / "metadata" / "sources"


def _concordance_dir() -> Path:
    return _plugin_root() / "data" / "concordance"


def _rel_source(path: Path) -> str:
    try:
        return path.relative_to(_plugin_root()).as_posix()
    except ValueError:
        return path.name


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return [{k: (v or "") for k, v in row.items()} for row in csv.DictReader(f)]


def _parse_extent(extent: str) -> str:
    s = (extent or "").strip()
    if not s:
        return ""
    m = _EXTENT_RE.search(s)
    return m.group(1) if m else s


def _parse_dates(dates: str) -> tuple[str, str, str]:
    s = (dates or "").strip()
    if not s:
        return "", "", ""
    m = _DATES_RE.match(s)
    if m:
        return s, m.group(1), m.group(2)
    return s, "", ""


def _person_id_str(value: str) -> str:
    s = (value or "").strip()
    if not s:
        return ""
    if s.endswith(".0"):
        s = s[:-2]
    return s


def _dzid_norm(raw: str) -> str:
    s = (raw or "").strip().upper()
    if not s:
        return ""
    if s.startswith("DZ"):
        return s
    if s.replace(".", "", 1).isdigit() or s.isdigit():
        return f"DZ{int(float(s)):04d}"
    return s


def _vols_str(value: str) -> str:
    s = (value or "").strip()
    if not s:
        return ""
    if s.endswith(".0"):
        s = s[:-2]
    return _parse_extent(s) or s


def _load_normalized_hints(path: Path) -> tuple[dict[str, dict], dict[tuple[str, str], dict]]:
    by_dzid: dict[str, dict] = {}
    by_author: dict[tuple[str, str], dict] = {}
    if not path.is_file():
        return by_dzid, by_author
    for row in _read_csv(path):
        raw_dz = (row.get("docclass") or "").strip()
        if not raw_dz.upper().startswith("DZ"):
            continue
        dzid = _dzid_norm(raw_dz)
        author = (row.get("metadata/Name") or row.get("author") or "").strip()
        hint = {
            "time_dynasty": (row.get("time_dynasty") or "").strip(),
            "date_not_before": (row.get("date_not_before") or "").strip(),
            "date_not_after": (row.get("date_not_after") or "").strip(),
            "author_dates": (row.get("metadata/AuthorDates") or "").strip(),
        }
        if dzid and dzid not in by_dzid and any(hint.values()):
            by_dzid[dzid] = hint
        if dzid and author:
            by_author[(dzid, author)] = hint
    return by_dzid, by_author


def sync_sources(*, metadata_root: Path, sources: Path) -> None:
    tables = metadata_root / "tables_output"
    copies = {
        "krp_works.csv": tables / "krp_works.csv",
        "skqs_org_authorship.csv": tables / "skqs_org_authorship.csv",
        "dz_metadata_works.csv": tables / "dz_metadata_works.csv",
        "dz_metadata_authors.csv": tables / "dz_metadata_authors.csv",
    }
    sources.mkdir(parents=True, exist_ok=True)
    for dest_name, src in copies.items():
        if not src.is_file():
            raise SystemExit(f"Missing upstream table: {src}")
        shutil.copy2(src, sources / dest_name)
        print(f"Synced {_rel_source(sources / dest_name)}")
    norm_src = metadata_root.parent / "Corpora" / "DaoCanon_txt_chm" / "DZ_metadata_normalized.csv"
    if not norm_src.is_file():
        norm_src = tables / "DZ_metadata_normalized.csv"
    if norm_src.is_file():
        shutil.copy2(norm_src, sources / "DZ_metadata_normalized.csv")
        print(f"Synced {_rel_source(sources / 'DZ_metadata_normalized.csv')}")


def _load_org_by_kr(rows: list[dict[str, str]]) -> dict[str, dict[str, str]]:
    out: dict[str, dict[str, str]] = {}
    for row in rows:
        kr_id = (row.get("KR_ID") or "").strip()
        if not kr_id:
            continue
        cbeta = (row.get("CBETA_ID") or "").strip()
        dzid = _dzid_norm(row.get("DZID") or "")
        if kr_id not in out:
            out[kr_id] = {"cbeta_id": cbeta, "dzid": dzid}
        elif cbeta and not out[kr_id]["cbeta_id"]:
            out[kr_id]["cbeta_id"] = cbeta
        if dzid and not out[kr_id]["dzid"]:
            out[kr_id]["dzid"] = dzid
    return out


def _load_dz_authors_by_dz(
    rows: list[dict[str, str]],
    *,
    norm_by_author: dict[tuple[str, str], dict],
) -> dict[str, list[dict[str, str]]]:
    by_dz: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        dzid = _dzid_norm(row.get("dzid") or "")
        if not dzid:
            continue
        name = (row.get("person_name") or "").strip()
        ah = norm_by_author.get((dzid, name), {})
        by_dz[dzid].append(
            {
                "author_index": (row.get("author_index") or "").strip(),
                "person_name": name,
                "person_id": _person_id_str(row.get("person_id") or ""),
                "function": (row.get("FUNCTION") or "").strip(),
                "time_dynasty": ah.get("time_dynasty", ""),
                "author_dates": ah.get("author_dates", ""),
                "date_not_before": ah.get("date_not_before", ""),
                "date_not_after": ah.get("date_not_after", ""),
            }
        )
    for dzid in by_dz:
        by_dz[dzid].sort(key=lambda r: int(r.get("author_index") or "0"))
    return by_dz


def _load_dz_works_by_dz(rows: list[dict[str, str]]) -> dict[str, dict[str, str]]:
    out: dict[str, dict[str, str]] = {}
    for row in rows:
        dzid = _dzid_norm(row.get("dzid") or "")
        if dzid and dzid not in out:
            out[dzid] = row
    return out


def _authorship_from_skqs(rows: list[dict[str, str]], kr_id: str) -> list[dict[str, str]]:
    out: list[dict[str, str]] = []
    for a in rows:
        dates, nb, na = _parse_dates(a.get("DATES") or "")
        out.append(
            {
                "author_index": (a.get("author_index") or "").strip(),
                "person_name": (a.get("person_name") or "").strip(),
                "person_id": "",
                "function": (a.get("FUNCTION") or "").strip(),
                "time_dynasty": (a.get("DYNASTY") or "").strip(),
                "author_dates": dates,
                "date_not_before": nb,
                "date_not_after": na,
                "source": "skqs",
            }
        )
    return out


def _merge_authorship(
    skqs_auth: list[dict[str, str]],
    dz_auth: list[dict[str, str]],
) -> list[dict[str, str]]:
    if not skqs_auth:
        return [{k: v for k, v in a.items() if k != "source"} for a in dz_auth]
    if not dz_auth:
        return [{k: v for k, v in a.items() if k != "source"} for a in skqs_auth]

    dz_by_name = {a["person_name"]: a for a in dz_auth if a.get("person_name")}
    merged: list[dict[str, str]] = []
    seen: set[str] = set()
    for a in skqs_auth:
        name = a.get("person_name") or ""
        dz = dz_by_name.get(name, {})
        merged.append(
            {
                "author_index": a.get("author_index") or dz.get("author_index") or "",
                "person_name": name,
                "person_id": a.get("person_id") or dz.get("person_id") or "",
                "function": a.get("function") or dz.get("function") or "",
                "time_dynasty": a.get("time_dynasty") or dz.get("time_dynasty") or "",
                "author_dates": a.get("author_dates") or dz.get("author_dates") or "",
                "date_not_before": a.get("date_not_before") or dz.get("date_not_before") or "",
                "date_not_after": a.get("date_not_after") or dz.get("date_not_after") or "",
            }
        )
        if name:
            seen.add(name)

    for a in dz_auth:
        name = a.get("person_name") or ""
        if name and name not in seen:
            merged.append({k: v for k, v in a.items() if k != "source"})
            seen.add(name)

    merged.sort(key=lambda r: int(r.get("author_index") or "0") or 999)
    for i, row in enumerate(merged, start=1):
        if not row.get("author_index"):
            row["author_index"] = str(i)
    return merged


def build_entries(
    *,
    works: list[dict[str, str]],
    skqs: list[dict[str, str]],
    org_by_kr: dict[str, dict[str, str]],
    kr_to_dz: dict[str, str],
    dz_authors_by_dz: dict[str, list[dict[str, str]]],
    dz_works_by_dz: dict[str, dict[str, str]],
    norm_by_dzid: dict[str, dict],
) -> dict[str, dict]:
    skqs_by_kr: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in skqs:
        kr_id = (row.get("KR_ID") or "").strip()
        if kr_id:
            skqs_by_kr[kr_id].append(row)
    for kr_id in skqs_by_kr:
        skqs_by_kr[kr_id].sort(key=lambda r: int(r.get("author_index") or "0"))

    out: dict[str, dict] = {}
    for row in works:
        kr_id = (row.get("KR_ID") or "").strip()
        if not kr_id:
            continue
        title = (row.get("text_title") or "").strip()
        juan_count = str(row.get("files") or "").strip()
        if juan_count.endswith(".0"):
            juan_count = juan_count[:-2]

        skqs_rows = skqs_by_kr.get(kr_id, [])
        org = org_by_kr.get(kr_id, {})
        dzid = org.get("dzid") or kr_to_dz.get(kr_id, "")
        dzid = _dzid_norm(dzid)
        dz_auth = dz_authors_by_dz.get(dzid, []) if dzid else []
        dz_work = dz_works_by_dz.get(dzid, {}) if dzid else {}
        dz_hint = norm_by_dzid.get(dzid, {}) if dzid else {}

        skqs_auth = _authorship_from_skqs(skqs_rows, kr_id)
        authorship = _merge_authorship(skqs_auth, dz_auth)

        source = (skqs_rows[0].get("SOURCE") or "").strip() if skqs_rows else ""
        if not source and dzid:
            source = "正統道藏 Zhengtong Daozang"

        extent = ""
        if skqs_rows:
            extent = _parse_extent(skqs_rows[0].get("EXTENT") or "")
            if not title:
                title = (skqs_rows[0].get("title") or "").strip()
        if not extent and dz_work:
            extent = _vols_str(dz_work.get("vols") or "")
        if not extent and juan_count:
            extent = juan_count
        if not title and dz_work:
            title = (dz_work.get("title") or "").strip()

        dynasty = (row.get("DYNASTY") or "").strip()
        if not dynasty and authorship:
            dynasty = authorship[0].get("time_dynasty") or ""
        if not dynasty:
            dynasty = dz_hint.get("time_dynasty") or ""

        work_dates = dz_hint.get("author_dates") or ""
        work_nb = dz_hint.get("date_not_before") or ""
        work_na = dz_hint.get("date_not_after") or ""
        for a in authorship:
            if a.get("author_dates"):
                work_dates = a["author_dates"]
                work_nb = a.get("date_not_before") or ""
                work_na = a.get("date_not_after") or ""
                break

        out[kr_id] = {
            "kr_id": kr_id,
            "title": title,
            "vols": extent,
            "juan_count": juan_count,
            "source": source,
            "cbeta_id": org.get("cbeta_id") or "",
            "dzid": dzid,
            "time_dynasty": dynasty,
            "date_not_before": work_nb,
            "date_not_after": work_na,
            "author_dates": work_dates,
            "authorship": authorship,
            "metadata_sources": {
                "skqs": bool(skqs_rows),
                "daozang": bool(dzid),
            },
        }
    return out


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sources-dir", type=Path, default=_sources_dir())
    parser.add_argument(
        "--sync-from",
        type=Path,
        metavar="METADATA_ROOT",
        help="Copy tables from chinese_corpus_metadata before build (maintainers only)",
    )
    parser.add_argument("--out-dir", type=Path, default=_plugin_root() / "data" / "metadata")
    args = parser.parse_args()

    if args.sync_from:
        sync_sources(metadata_root=args.sync_from, sources=args.sources_dir)

    works_csv = args.sources_dir / "krp_works.csv"
    skqs_csv = args.sources_dir / "skqs_org_authorship.csv"
    dz_works_csv = args.sources_dir / "dz_metadata_works.csv"
    dz_authors_csv = args.sources_dir / "dz_metadata_authors.csv"
    normalized_csv = args.sources_dir / "DZ_metadata_normalized.csv"
    org_csv = _concordance_dir() / "kanripo_org_concordance.csv"
    dz_collation_csv = _concordance_dir() / "krp_dz_collation.csv"
    required = (works_csv, skqs_csv, dz_works_csv, dz_authors_csv, org_csv, dz_collation_csv)
    for p in required:
        if not p.is_file():
            raise SystemExit(
                f"Missing bundled source: {_rel_source(p)}. "
                "Run --sync-from and build:concordance first."
            )

    norm_by_dzid, norm_by_author = _load_normalized_hints(normalized_csv)
    kr_to_dz = {
        (row.get("KR_ID") or "").strip(): _dzid_norm(row.get("DZID") or "")
        for row in _read_csv(dz_collation_csv)
        if (row.get("KR_ID") or "").strip()
    }

    entries = build_entries(
        works=_read_csv(works_csv),
        skqs=_read_csv(skqs_csv),
        org_by_kr=_load_org_by_kr(_read_csv(org_csv)),
        kr_to_dz=kr_to_dz,
        dz_authors_by_dz=_load_dz_authors_by_dz(
            _read_csv(dz_authors_csv), norm_by_author=norm_by_author
        ),
        dz_works_by_dz=_load_dz_works_by_dz(_read_csv(dz_works_csv)),
        norm_by_dzid=norm_by_dzid,
    )

    out = args.out_dir
    out.mkdir(parents=True, exist_ok=True)
    generated_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat()

    with_auth = sum(1 for e in entries.values() if e.get("authorship"))
    multi_auth = sum(1 for e in entries.values() if len(e.get("authorship") or []) > 1)
    with_dz = sum(1 for e in entries.values() if e.get("dzid"))
    with_dynasty = sum(1 for e in entries.values() if e.get("time_dynasty"))
    with_dates = sum(
        1
        for e in entries.values()
        if e.get("author_dates") or e.get("date_not_before")
    )
    with_pid = sum(
        1
        for e in entries.values()
        for a in e.get("authorship") or []
        if a.get("person_id")
    )

    payload = {
        "version": 1,
        "generatedAt": generated_at,
        "entryCount": len(entries),
        "sources": {
            "krp_works": _rel_source(works_csv),
            "skqs_org_authorship": _rel_source(skqs_csv),
            "dz_metadata_works": _rel_source(dz_works_csv),
            "dz_metadata_authors": _rel_source(dz_authors_csv),
            "dz_metadata_normalized": _rel_source(normalized_csv)
            if normalized_csv.is_file()
            else None,
            "kanripo_org_concordance": _rel_source(org_csv),
            "krp_dz_collation": _rel_source(dz_collation_csv),
        },
        "entries": entries,
    }
    (out / "krp_works_by_id.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    manifest = {
        "packKind": "ljb-kanripo-metadata",
        "generatedAt": generated_at,
        "stats": {
            "works": len(entries),
            "with_dzid": with_dz,
            "with_authorship": with_auth,
            "multi_author_works": multi_auth,
            "with_time_dynasty": with_dynasty,
            "with_author_dates": with_dates,
            "authorship_with_person_id": with_pid,
        },
    }
    (out / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"Wrote {len(entries)} work metadata entries to {out}")
    print(
        f"  with DZID: {with_dz}; multi-author: {multi_auth}; "
        f"dynasty: {with_dynasty}; person_id rows: {with_pid}"
    )


if __name__ == "__main__":
    main()
