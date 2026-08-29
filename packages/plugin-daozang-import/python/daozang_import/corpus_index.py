"""Build and search the local UTF-8 corpus index."""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path

from daozang_import.constants import CORPUS_INDEX_NAME, SIMP_MARKERS, TRAD_MARKERS

_DZ_RE = re.compile(r"(?:^|[^0-9])(DZ|dz)?(\d{1,4})(?:[^0-9]|$)")
_TITLE_FROM_NAME_RE = re.compile(
    r"^(?:DZ|dz)?\d{1,4}[\s._\-—–]*(.+?)(?:\.txt)?$",
    re.UNICODE,
)


@dataclass(frozen=True)
class CorpusEntry:
    id: str
    dz_no: str
    title: str
    variant: str
    rel_path: str
    bytes: int


def variant_from_relpath(rel_path: str) -> str:
    lowered = rel_path.lower()
    for marker in TRAD_MARKERS:
        if marker.lower() in lowered:
            return "trad"
    for marker in SIMP_MARKERS:
        if marker.lower() in lowered:
            return "simp"
    return "trad"


def parse_dz_no(stem: str) -> str:
    match = _DZ_RE.search(stem)
    if not match:
        return ""
    return match.group(2).lstrip("0") or "0"


def title_from_filename(stem: str, dz_no: str) -> str:
    cleaned = stem.strip()
    if dz_no:
        cleaned = re.sub(rf"^(?:DZ|dz)?0*{re.escape(dz_no)}\s*[\._\-—–]*", "", cleaned)
    match = _TITLE_FROM_NAME_RE.match(stem)
    if match and match.group(1).strip():
        return match.group(1).strip()
    return cleaned or stem


def entry_id(dz_no: str, variant: str, rel_path: str) -> str:
    """Stable, unique id for index rows (Chinese filenames have no ASCII slug)."""
    dz = (dz_no or "0").zfill(4)
    digest = hashlib.sha1(rel_path.encode("utf-8")).hexdigest()[:12]
    return f"dz{dz}-{variant}-{digest}"


def build_index(utf8_root: Path) -> list[CorpusEntry]:
    entries: list[CorpusEntry] = []
    if not utf8_root.is_dir():
        return entries
    for path in sorted(utf8_root.rglob("*.txt")):
        if not path.is_file():
            continue
        rel_path = path.relative_to(utf8_root).as_posix()
        stem = path.stem
        variant = variant_from_relpath(rel_path)
        dz_no = parse_dz_no(stem)
        title = title_from_filename(stem, dz_no)
        entries.append(
            CorpusEntry(
                id=entry_id(dz_no, variant, rel_path),
                dz_no=dz_no,
                title=title,
                variant=variant,
                rel_path=rel_path,
                bytes=path.stat().st_size,
            )
        )
    entries.sort(key=lambda item: (item.dz_no.zfill(5), item.variant, item.title))
    return entries


def write_index(utf8_root: Path, index_path: Path) -> list[CorpusEntry]:
    entries = build_index(utf8_root)
    payload = [asdict(entry) for entry in entries]
    index_path.parent.mkdir(parents=True, exist_ok=True)
    index_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return entries


def load_index(index_path: Path) -> list[CorpusEntry]:
    if not index_path.is_file():
        return []
    raw = json.loads(index_path.read_text(encoding="utf-8"))
    return [CorpusEntry(**item) for item in raw]


def search_index(entries: list[CorpusEntry], query: str, limit: int = 40) -> list[CorpusEntry]:
    q = query.strip()
    if not q:
        return entries[: min(30, len(entries))]
    lower = q.lower()
    matched = [
        entry
        for entry in entries
        if lower in entry.id.lower()
        or q in entry.title
        or q in entry.dz_no
        or lower in entry.rel_path.lower()
    ]
    matched.sort(
        key=lambda entry: (
            0 if entry.dz_no == q.lstrip("0") or entry.dz_no == q else 1,
            0 if entry.title.startswith(q) else 1,
            entry.dz_no.zfill(5),
            entry.title,
        )
    )
    return matched[:limit]
