"""Load bundled Kanripo work metadata for import."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from functools import lru_cache
from typing import Any

from kanripo_import._paths import metadata_dir

_KR_ID_RE = re.compile(r"^KR[a-z0-9]+$", re.IGNORECASE)


@dataclass(frozen=True)
class AuthorshipRecord:
    author_index: str
    person_name: str
    person_id: str
    function: str
    time_dynasty: str
    author_dates: str
    date_not_before: str
    date_not_after: str


@dataclass(frozen=True)
class WorkMetadata:
    kr_id: str
    title: str
    vols: str
    juan_count: str
    source: str
    cbeta_id: str
    dzid: str
    time_dynasty: str
    date_not_before: str
    date_not_after: str
    author_dates: str
    authorship: tuple[AuthorshipRecord, ...]


def _parse_authorship(raw: list[dict[str, str]] | None) -> tuple[AuthorshipRecord, ...]:
    out: list[AuthorshipRecord] = []
    for row in raw or []:
        out.append(
            AuthorshipRecord(
                author_index=(row.get("author_index") or "").strip(),
                person_name=(row.get("person_name") or "").strip(),
                person_id=(row.get("person_id") or "").strip(),
                function=(row.get("function") or row.get("FUNCTION") or "").strip(),
                time_dynasty=(row.get("time_dynasty") or row.get("DYNASTY") or "").strip(),
                author_dates=(row.get("author_dates") or row.get("DATES") or "").strip(),
                date_not_before=(row.get("date_not_before") or "").strip(),
                date_not_after=(row.get("date_not_after") or "").strip(),
            )
        )
    return tuple(out)


def _record_from_raw(row: dict[str, Any]) -> WorkMetadata:
    return WorkMetadata(
        kr_id=(row.get("kr_id") or row.get("KR_ID") or "").strip(),
        title=(row.get("title") or row.get("text_title") or "").strip(),
        vols=(row.get("vols") or "").strip(),
        juan_count=(row.get("juan_count") or row.get("files") or "").strip(),
        source=(row.get("source") or row.get("SOURCE") or "").strip(),
        cbeta_id=(row.get("cbeta_id") or "").strip(),
        dzid=(row.get("dzid") or row.get("DZID") or "").strip(),
        time_dynasty=(row.get("time_dynasty") or row.get("DYNASTY") or "").strip(),
        date_not_before=(row.get("date_not_before") or "").strip(),
        date_not_after=(row.get("date_not_after") or "").strip(),
        author_dates=(row.get("author_dates") or "").strip(),
        authorship=_parse_authorship(row.get("authorship")),
    )


def _normalize_kr_id(kr_id: str) -> str:
    s = (kr_id or "").strip()
    if not s:
        return ""
    return s if _KR_ID_RE.match(s) else s


@lru_cache(maxsize=1)
def _load_doc() -> dict[str, Any]:
    path = metadata_dir() / "krp_works_by_id.json"
    if not path.is_file():
        return {"entries": {}}
    return json.loads(path.read_text(encoding="utf-8"))


@lru_cache(maxsize=1)
def load_work_metadata_index() -> dict[str, WorkMetadata]:
    entries = _load_doc().get("entries") or {}
    out: dict[str, WorkMetadata] = {}
    for kr_id, raw in entries.items():
        if isinstance(raw, dict):
            key = _normalize_kr_id(str(kr_id))
            if key:
                out[key] = _record_from_raw(raw)
    return out


def lookup_work_metadata(kr_id: str) -> WorkMetadata | None:
    key = _normalize_kr_id(kr_id)
    if not key:
        return None
    return load_work_metadata_index().get(key)


def clear_work_metadata_cache() -> None:
    _load_doc.cache_clear()
    load_work_metadata_index.cache_clear()
