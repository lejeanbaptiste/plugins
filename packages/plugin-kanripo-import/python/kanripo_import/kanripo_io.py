"""Read Kanripo Mandoku ``.txt`` headers and body (minimal I/O slice)."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

_KANRIPO_PB_RE = re.compile(r"<pb:([^_>]+)_[^_]+_(\d+)-")
_KANRIPO_HEADER_LINE_RE = re.compile(r"^\s*#")


@dataclass(frozen=True)
class KanripoMetadata:
    kanripo_id: str
    juan: int


def extract_kanripo_metadata(path: Path) -> KanripoMetadata | None:
    text = path.read_text(encoding="utf-8", errors="replace")
    match = _KANRIPO_PB_RE.search(text)
    if not match:
        return None
    return KanripoMetadata(kanripo_id=match.group(1), juan=int(match.group(2)))


def load_kanripo_text(path: Path) -> str:
    raw = path.read_text(encoding="utf-8", errors="replace")
    lines = raw.splitlines(keepends=True)
    index = 0
    while index < len(lines):
        line = lines[index]
        stripped = line.strip()
        if stripped == "" or _KANRIPO_HEADER_LINE_RE.match(line):
            index += 1
            continue
        break
    return "".join(lines[index:])
