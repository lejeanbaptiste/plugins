#!/usr/bin/env python3
"""
Build bundled Daozang work metadata for plugin-daozang-import.

Reads only from bundled CSVs under ``data/metadata/sources/`` (self-contained).
Optional ``--sync-from`` copies fresh tables from a maintainer machine before build.

Output: data/metadata/dz_works_by_rel_path.json + manifest.json

Run from plugin package root::

    python scripts/build-daozang-metadata.py
    python scripts/build-daozang-metadata.py --sync-from ~/Python/chinese_corpus_metadata
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

_DYNASTY_AUTHOR_RE = re.compile(r"-([^-]+)-([^-]+)\.txt$", re.UNICODE)


def _plugin_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _sources_dir() -> Path:
    return _plugin_root() / "data" / "metadata" / "sources"


def _rel_source(path: Path) -> str:
    try:
        return path.relative_to(_plugin_root()).as_posix()
    except ValueError:
        return path.name


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return [{k: (v or "") for k, v in row.items()} for row in csv.DictReader(f)]


def _dzid_norm(dz_id: str) -> str:
    s = (dz_id or "").strip().upper()
    if not s:
        return ""
    if s.startswith("DZ"):
        return s
    if s.replace(".", "", 1).isdigit() or s.isdigit():
        num = s.split(".")[0]
        return f"DZ{int(num):04d}"
    return s


def _edition_from_rel_path(rel_path: str) -> str:
    part = rel_path.split("-", 1)[0].strip()
    return part or "正統道藏"


def _variant_class_from_rel_path(rel_path: str) -> str:
    parts = rel_path.split("-")
    if len(parts) >= 2:
        return parts[1].strip()
    return ""


def _dynasty_from_filename(rel_path: str) -> str:
    m = _DYNASTY_AUTHOR_RE.search(rel_path)
    if not m:
        return ""
    dynasty = m.group(1).strip()
    if dynasty in ("txt",) or len(dynasty) > 12:
        return ""
    return dynasty


def _load_normalized_hints(path: Path) -> tuple[dict[str, dict], dict[tuple[str, str], dict]]:
    """Work-level and (dzid, author_name) hints from bundled normalized CSV."""
    by_dzid: dict[str, dict] = {}
    by_author: dict[tuple[str, str], dict] = {}
    if not path.is_file():
        return by_dzid, by_author
    for row in _read_csv(path):
        raw_dz = (row.get("docclass") or "").strip()
        if raw_dz.upper().startswith("DZ"):
            dzid = _dzid_norm(raw_dz)
        else:
            continue
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


def sync_sources(
    *,
    metadata_root: Path,
    normalized_csv: Path | None,
    sources: Path,
) -> None:
    """Copy upstream tables into bundled ``data/metadata/sources/``."""
    tables = metadata_root / "tables_output"
    copies = {
        "dz_metadata_works.csv": tables / "dz_metadata_works.csv",
        "dz_metadata_authors.csv": tables / "dz_metadata_authors.csv",
        "krp_dz_collation.csv": tables / "krp_dz_collation.csv",
    }
    sources.mkdir(parents=True, exist_ok=True)
    for dest_name, src in copies.items():
        if not src.is_file():
            raise SystemExit(f"Missing upstream table: {src}")
        shutil.copy2(src, sources / dest_name)
        print(f"Synced {_rel_source(sources / dest_name)}")
    if normalized_csv and normalized_csv.is_file():
        shutil.copy2(normalized_csv, sources / "DZ_metadata_normalized.csv")
        print(f"Synced {_rel_source(sources / 'DZ_metadata_normalized.csv')}")


def build_entries(
    *,
    works: list[dict[str, str]],
    authors: list[dict[str, str]],
    krp_dz: list[dict[str, str]],
    norm_by_dzid: dict[str, dict],
    norm_by_author: dict[tuple[str, str], dict],
) -> dict[str, dict]:
    authors_by_dz: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in authors:
        dzid = _dzid_norm(row.get("dzid") or "")
        if dzid:
            authors_by_dz[dzid].append(row)

    krp_by_dz: dict[str, dict[str, str]] = {}
    for row in krp_dz:
        dzid = _dzid_norm(row.get("DZID") or "")
        kr_id = (row.get("KR_ID") or "").strip()
        if dzid and kr_id and dzid not in krp_by_dz:
            krp_by_dz[dzid] = row

    out: dict[str, dict] = {}
    for row in works:
        rel = (row.get("file_name") or "").strip()
        if not rel:
            continue
        dzid = _dzid_norm(row.get("dzid") or "")
        dz_no = dzid[2:].lstrip("0") if dzid.startswith("DZ") else (row.get("hyid") or "").strip()
        krp_row = krp_by_dz.get(dzid, {})
        kr_id = (krp_row.get("KR_ID") or "").strip()
        work_hint = norm_by_dzid.get(dzid, {})
        filename_dynasty = _dynasty_from_filename(rel)

        authorship: list[dict[str, str]] = []
        for a in sorted(authors_by_dz.get(dzid, []), key=lambda r: int(r.get("author_index") or "0")):
            name = (a.get("person_name") or "").strip()
            ah = norm_by_author.get((dzid, name), {})
            authorship.append(
                {
                    "author_index": (a.get("author_index") or "").strip(),
                    "person_name": name,
                    "person_id": (a.get("person_id") or "").strip(),
                    "function": (a.get("FUNCTION") or "").strip(),
                    "time_dynasty": ah.get("time_dynasty", ""),
                    "author_dates": ah.get("author_dates", ""),
                    "date_not_before": ah.get("date_not_before", ""),
                    "date_not_after": ah.get("date_not_after", ""),
                }
            )

        dynasty = (
            work_hint.get("time_dynasty")
            or filename_dynasty
            or (authorship[0].get("time_dynasty") if authorship else "")
        )

        out[rel] = {
            "rel_path": rel,
            "dzid": dzid,
            "dz_no": dz_no,
            "ctid": (row.get("ctid") or "").strip(),
            "hyid": (row.get("hyid") or "").strip(),
            "title": (row.get("title") or "").strip(),
            "vols": (row.get("vols") or "").strip(),
            "kr_id": kr_id,
            "krp_title": (krp_row.get("title") or "").strip(),
            "edition": _edition_from_rel_path(rel),
            "variant_class": _variant_class_from_rel_path(rel),
            "file_name_match": (row.get("file_name_match") or "").strip(),
            "authorship": authorship,
            "time_dynasty": dynasty,
            "date_not_before": work_hint.get("date_not_before", ""),
            "date_not_after": work_hint.get("date_not_after", ""),
            "author_dates": work_hint.get("author_dates", ""),
            "source": "方瞳子源 Fang Tongzi transcription (homeinmists.com)",
        }
    return out


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--sources-dir",
        type=Path,
        default=_sources_dir(),
        help="Bundled CSV inputs (default: data/metadata/sources/)",
    )
    parser.add_argument(
        "--sync-from",
        type=Path,
        metavar="METADATA_ROOT",
        help="Copy tables from chinese_corpus_metadata before build (maintainers only)",
    )
    parser.add_argument(
        "--normalized-csv",
        type=Path,
        help="Optional DZ_metadata_normalized.csv when using --sync-from",
    )
    parser.add_argument("--out-dir", type=Path, default=_plugin_root() / "data" / "metadata")
    args = parser.parse_args()

    if args.sync_from:
        norm = args.normalized_csv
        sync_sources(
            metadata_root=args.sync_from,
            normalized_csv=norm,
            sources=args.sources_dir,
        )

    works_csv = args.sources_dir / "dz_metadata_works.csv"
    authors_csv = args.sources_dir / "dz_metadata_authors.csv"
    krp_dz_csv = args.sources_dir / "krp_dz_collation.csv"
    normalized_csv = args.sources_dir / "DZ_metadata_normalized.csv"
    for p in (works_csv, authors_csv, krp_dz_csv):
        if not p.is_file():
            raise SystemExit(
                f"Missing bundled source: {_rel_source(p)}. "
                "Run with --sync-from /path/to/chinese_corpus_metadata first."
            )

    norm_by_dzid, norm_by_author = _load_normalized_hints(normalized_csv)
    entries = build_entries(
        works=_read_csv(works_csv),
        authors=_read_csv(authors_csv),
        krp_dz=_read_csv(krp_dz_csv),
        norm_by_dzid=norm_by_dzid,
        norm_by_author=norm_by_author,
    )

    out = args.out_dir
    out.mkdir(parents=True, exist_ok=True)
    generated_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat()

    with_auth = sum(1 for e in entries.values() if e.get("authorship"))
    multi_auth = sum(1 for e in entries.values() if len(e.get("authorship") or []) > 1)
    with_kr = sum(1 for e in entries.values() if e.get("kr_id"))
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
            "dz_metadata_works": _rel_source(works_csv),
            "dz_metadata_authors": _rel_source(authors_csv),
            "krp_dz_collation": _rel_source(krp_dz_csv),
            "dz_metadata_normalized": _rel_source(normalized_csv)
            if normalized_csv.is_file()
            else None,
        },
        "entries": entries,
    }
    (out / "dz_works_by_rel_path.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    manifest = {
        "packKind": "ljb-daozang-metadata",
        "generatedAt": generated_at,
        "stats": {
            "works": len(entries),
            "with_kr_id": with_kr,
            "with_authorship": with_auth,
            "multi_author_works": multi_auth,
            "authorship_with_person_id": with_pid,
            "with_time_dynasty": sum(1 for e in entries.values() if e.get("time_dynasty")),
        },
    }
    (out / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"Wrote {len(entries)} work metadata entries to {out}")
    print(f"  with KR_ID: {with_kr}; multi-author works: {multi_auth}; person_id rows: {with_pid}")


if __name__ == "__main__":
    main()
