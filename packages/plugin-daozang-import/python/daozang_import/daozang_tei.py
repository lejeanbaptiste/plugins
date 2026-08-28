"""Convert a cached UTF-8 Daozang text file to a TEI body div."""

from __future__ import annotations

import re
from pathlib import Path

from daozang_import.corpus_index import parse_dz_no, title_from_filename, variant_from_relpath

_XML_ESCAPE = str.maketrans({"&": "&amp;", "<": "&lt;", ">": "&gt;"})


def _xml_escape(text: str) -> str:
    return text.translate(_XML_ESCAPE)


def _paragraphs_from_text(text: str) -> list[str]:
    normalized = text.replace("\r\n", "\n").replace("\r", "\n").strip()
    if not normalized:
        return []
    chunks = re.split(r"\n\s*\n+", normalized)
    paragraphs: list[str] = []
    for chunk in chunks:
        lines = [line.strip() for line in chunk.split("\n") if line.strip()]
        if not lines:
            continue
        joined = "".join(lines) if all(len(line) <= 2 for line in lines) else "\n".join(lines)
        paragraphs.append(joined)
    return paragraphs or [normalized]


def convert_daozang_txt(path: Path, *, rel_path: str = "") -> dict[str, object]:
    path = Path(path)
    if not path.is_file():
        raise FileNotFoundError(f"Daozang text not found: {path}")

    rel = rel_path or path.name
    stem = path.stem
    dz_no = parse_dz_no(stem)
    title = title_from_filename(stem, dz_no)
    variant = variant_from_relpath(rel)
    text = path.read_text(encoding="utf-8")
    paragraphs = _paragraphs_from_text(text)

    body_parts = [
        f'<div type="text" n="{_xml_escape(dz_no or stem)}">',
        f'  <head>{_xml_escape(title)}</head>',
    ]
    for paragraph in paragraphs:
        body_parts.append(f"  <p>{_xml_escape(paragraph)}</p>")
    body_parts.append("</div>")
    body_xml = "\n".join(body_parts)

    return {
        "body_xml": body_xml,
        "meta": {
            "title": title,
            "dz_no": dz_no,
            "variant": variant,
            "rel_path": rel,
            "stem": stem,
            "source": "方瞳子源 Fang Tongzi transcription (homeinmists.com)",
        },
    }
