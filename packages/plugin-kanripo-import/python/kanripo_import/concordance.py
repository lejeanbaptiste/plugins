"""Load bundled Kanripo ↔ Daozang / DZ concordance tables."""

from __future__ import annotations

import csv
import json
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any

from kanripo_import._paths import concordance_dir as _concordance_dir


def concordance_dir() -> Path:
    return _concordance_dir()


@dataclass(frozen=True)
class DaozangMapEntry:
    kr_id: str
    dz_id: str
    daozang_rel_path: str
    daozang_title: str
    match_method: str
    title: str
    note: str


def _read_csv(path: Path) -> list[dict[str, str]]:
    if not path.is_file():
        return []
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return [{k: (v or "") for k, v in row.items()} for row in csv.DictReader(f)]


@lru_cache(maxsize=1)
def load_manifest() -> dict[str, Any]:
    path = concordance_dir() / "manifest.json"
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


@lru_cache(maxsize=1)
def load_krp_dz_collation() -> list[dict[str, str]]:
    return _read_csv(concordance_dir() / "krp_dz_collation.csv")


@lru_cache(maxsize=1)
def load_org_concordance() -> list[dict[str, str]]:
    return _read_csv(concordance_dir() / "kanripo_org_concordance.csv")


@lru_cache(maxsize=1)
def load_dz_corpus_works() -> list[dict[str, str]]:
    return _read_csv(concordance_dir() / "dz_corpus_works.csv")


@lru_cache(maxsize=1)
def load_duren_jing_index() -> list[dict[str, str]]:
    return _read_csv(concordance_dir() / "duren_jing_index.csv")


@lru_cache(maxsize=1)
def _load_daozang_map_doc() -> dict[str, Any]:
    path = concordance_dir() / "kanripo_daozang_map.json"
    if not path.is_file():
        return {"entries": {}}
    return json.loads(path.read_text(encoding="utf-8"))


@lru_cache(maxsize=1)
def load_daozang_map() -> dict[str, DaozangMapEntry]:
    doc = _load_daozang_map_doc()
    raw = doc.get("entries") or {}
    out: dict[str, DaozangMapEntry] = {}
    for kr_id, row in raw.items():
        if not isinstance(row, dict):
            continue
        out[kr_id] = DaozangMapEntry(
            kr_id=(row.get("kr_id") or kr_id).strip(),
            dz_id=(row.get("dz_id") or "").strip(),
            daozang_rel_path=(row.get("daozang_rel_path") or "").strip(),
            daozang_title=(row.get("daozang_title") or "").strip(),
            match_method=(row.get("match_method") or "").strip(),
            title=(row.get("title") or "").strip(),
            note=(row.get("note") or "").strip(),
        )
    return out


def lookup_daozang_rel_path(kr_id: str) -> DaozangMapEntry | None:
    return load_daozang_map().get((kr_id or "").strip())


def lookup_dz_id(kr_id: str) -> str:
    entry = lookup_daozang_rel_path(kr_id)
    if entry and entry.dz_id:
        return entry.dz_id
    kr = (kr_id or "").strip()
    for row in load_krp_dz_collation():
        if (row.get("KR_ID") or "").strip() == kr:
            return (row.get("DZID") or "").strip()
    for row in load_org_concordance():
        if (row.get("KR_ID") or "").strip() == kr:
            return (row.get("DZID") or "").strip()
    return ""


def clear_concordance_cache() -> None:
    load_manifest.cache_clear()
    load_krp_dz_collation.cache_clear()
    load_org_concordance.cache_clear()
    load_dz_corpus_works.cache_clear()
    load_duren_jing_index.cache_clear()
    _load_daozang_map_doc.cache_clear()
    load_daozang_map.cache_clear()
