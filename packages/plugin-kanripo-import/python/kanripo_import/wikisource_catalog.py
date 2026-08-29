"""Match Kanripo juan bodies to Wikisource catalog chapters."""

from __future__ import annotations

import re
from typing import Any, TypedDict

from kanripo_import.parallel_punct import (
    find_han_overlap,
    find_han_overlap_flexible,
    han_only,
    strip_wikisource_commentary,
    _han_tape,
    _iter_xml_atoms,
)

ORDINAL_SUFFIX_RE = re.compile(r"第[一二三四五六七八九十百千零]+(?:[上中下])?$")
COMM_NOTE_RE = re.compile(r'<note type="comm">[\s\S]*?</note>')
SKIP_TITLE_CHARS_RE = re.compile(r"(?:書曰|傳解|詩曰)")
CHAPTER_HEAD_RE = re.compile(
    r"([\u4e00-\u9fff]{2,12}(?:篇|紀|列傳|傳|志)第[一二三四五六七八九十百千零上中下]+)"
)
SHORT_CHAPTER_P_RE = re.compile(
    r"<p>\s*(?:<pb\b[^>]*/>\s*)*"
    r"(?:[\u4e00-\u9fff]{0,12}卷[\u4e00-\u9fff第一二三四五六七八九十百千零上中下]*\s*)*"
    rf"{CHAPTER_HEAD_RE.pattern}\s*</p>"
)
EMBEDDED_CHAPTER_RE = CHAPTER_HEAD_RE
MAX_TITLE_MATCHES = 5


class WikisourceChapter(TypedDict):
    id: str
    title: str
    text: str


class CatalogMatch(TypedDict):
    text: str
    chapter_ids: list[str]
    method: str
    labels: list[str]


def normalize_chapter_title(title: str) -> str:
    """Strip ordinal suffix and whitespace for title comparison."""
    core = str(title or "").strip()
    if core.startswith("注"):
        core = core[1:]
    core = ORDINAL_SUFFIX_RE.sub("", core)
    return core.replace(" ", "").replace("　", "")


def _chapter_title_ok(raw: str) -> bool:
    norm = normalize_chapter_title(raw)
    if len(norm) < 3 or len(norm) > 16:
        return False
    if not re.search(r"(篇|紀|列傳|傳|志)$", norm):
        return False
    if SKIP_TITLE_CHARS_RE.search(norm):
        return False
    return True


def extract_body_chapter_titles(body_xml: str) -> list[str]:
    """Find chapter heads (``…篇`` / ``…紀`` / ``…傳`` / ``…志``) in document order."""
    stripped = COMM_NOTE_RE.sub("", body_xml)
    seen: set[str] = set()
    titles: list[str] = []

    def add(raw: str) -> None:
        if not _chapter_title_ok(raw):
            return
        norm = normalize_chapter_title(raw)
        if not norm or norm in seen:
            return
        seen.add(norm)
        titles.append(norm)

    for match in SHORT_CHAPTER_P_RE.finditer(stripped):
        add(match.group(1))
    for match in EMBEDDED_CHAPTER_RE.finditer(stripped):
        add(match.group(1))
    return titles


def _lookup_chapter(
    lookup: dict[str, WikisourceChapter],
    title: str,
) -> WikisourceChapter | None:
    chapter = lookup.get(title)
    if chapter is not None:
        return chapter
    if title.startswith("脩"):
        chapter = lookup.get("修" + title[1:])
        if chapter is not None:
            return chapter
    if title.startswith("修"):
        chapter = lookup.get("脩" + title[1:])
        if chapter is not None:
            return chapter
    for suffix in re.finditer(r"([\u4e00-\u9fff]{2,10}(?:篇|紀|列傳|傳|志))$", title):
        chapter = lookup.get(suffix.group(1))
        if chapter is not None:
            return chapter
    return None


def _chapter_lookup(chapters: list[WikisourceChapter]) -> dict[str, WikisourceChapter]:
    lookup: dict[str, WikisourceChapter] = {}
    for chapter in chapters:
        norm = normalize_chapter_title(chapter.get("title") or "")
        if norm and norm not in lookup:
            lookup[norm] = chapter
        chapter_id = str(chapter.get("id") or "")
        if chapter_id:
            tail = chapter_id.split("/")[-1]
            tail_norm = normalize_chapter_title(tail)
            if tail_norm and tail_norm not in lookup:
                lookup[tail_norm] = chapter
        # Kanripo sometimes uses 脩 where Wikisource uses 修
        if norm.startswith("脩"):
            alt = "修" + norm[1:]
            if alt not in lookup:
                lookup[alt] = chapter
    return lookup


def _overlap_score(body_xml: str, parallel_text: str) -> tuple[float, tuple[int, int] | None]:
    atoms = _iter_xml_atoms(body_xml)
    tape, _ = _han_tape(atoms)
    if not tape:
        return 0.0, None
    sticker = han_only(strip_wikisource_commentary(parallel_text))
    if not sticker:
        return 0.0, None
    overlap = find_han_overlap_flexible(tape, sticker)
    if overlap is None:
        return 0.0, None
    start, end = overlap
    matched = end - start
    tape_ratio = matched / len(tape)
    sticker_ratio = matched / len(sticker)
    return max(tape_ratio, sticker_ratio), overlap


def match_chapters_by_title(
    body_xml: str,
    chapters: list[WikisourceChapter],
    *,
    used_ids: set[str] | None = None,
) -> CatalogMatch | None:
    """Pair body chapter heads with catalog entries by normalized title."""
    if not chapters:
        return None
    used = used_ids or set()
    titles = extract_body_chapter_titles(body_xml)
    if len(titles) > MAX_TITLE_MATCHES:
        return None
    lookup = _chapter_lookup(chapters)
    matched: list[WikisourceChapter] = []
    for title in titles:
        chapter = _lookup_chapter(lookup, title)
        if chapter is None:
            continue
        chapter_id = str(chapter.get("id") or "")
        if chapter_id and chapter_id in used:
            continue
        matched.append(chapter)
        if chapter_id:
            used.add(chapter_id)
    if not matched:
        return None
    return {
        "text": "\n".join(str(item.get("text") or "") for item in matched),
        "chapter_ids": [str(item.get("id") or "") for item in matched if item.get("id")],
        "method": "title",
        "labels": [str(item.get("title") or item.get("id") or "") for item in matched],
    }


def _quick_overlap_prefilter(body_tape: str, parallel_text: str) -> bool:
    """Cheap reject before full fuzzy overlap on large Wikisource catalogs."""
    sticker = han_only(strip_wikisource_commentary(parallel_text))
    if len(sticker) < 40 or len(body_tape) < 40:
        return True
    for anchor_len in (80, 40):
        anchor = sticker[:anchor_len]
        if anchor in body_tape:
            return True
    return find_han_overlap(body_tape[:1200], sticker[:400]) is not None


def match_chapter_by_overlap(
    body_xml: str,
    chapters: list[WikisourceChapter],
    *,
    used_ids: set[str] | None = None,
    min_ratio: float = 0.25,
) -> CatalogMatch | None:
    """Pick the unused catalog chapter with the best Han overlap score."""
    used = used_ids or set()
    best: WikisourceChapter | None = None
    best_score = 0.0
    atoms = _iter_xml_atoms(body_xml)
    body_tape, _ = _han_tape(atoms)
    for chapter in chapters:
        chapter_id = str(chapter.get("id") or "")
        if chapter_id and chapter_id in used:
            continue
        text = str(chapter.get("text") or "")
        if not text.strip():
            continue
        if not _quick_overlap_prefilter(body_tape, text):
            continue
        score, _ = _overlap_score(body_xml, text)
        if score > best_score:
            best_score = score
            best = chapter
    if best is None or best_score < min_ratio:
        return None
    chapter_id = str(best.get("id") or "")
    if chapter_id:
        used.add(chapter_id)
    return {
        "text": str(best.get("text") or ""),
        "chapter_ids": [chapter_id] if chapter_id else [],
        "method": "overlap",
        "labels": [str(best.get("title") or best.get("id") or "")],
    }


def resolve_wikisource_parallel(
    body_xml: str,
    source: dict[str, Any],
    *,
    used_ids: set[str] | None = None,
) -> tuple[str, CatalogMatch | None]:
    """Choose parallel text for one juan from a Wikisource catalog source."""
    chapters_raw = source.get("chapters")
    if not isinstance(chapters_raw, list) or len(chapters_raw) < 2:
        return str(source.get("text") or ""), None

    chapters: list[WikisourceChapter] = []
    for item in chapters_raw:
        if not isinstance(item, dict):
            continue
        text = str(item.get("text") or "")
        if not text.strip():
            continue
        chapters.append(
            {
                "id": str(item.get("id") or ""),
                "title": str(item.get("title") or ""),
                "text": text,
            }
        )
    if len(chapters) < 2:
        return str(source.get("text") or ""), None

    titles = extract_body_chapter_titles(body_xml)
    if len(titles) > MAX_TITLE_MATCHES:
        return "", None

    used = set(used_ids or [])
    title_match = match_chapters_by_title(body_xml, chapters, used_ids=used)
    if title_match and title_match["text"].strip():
        return title_match["text"], title_match

    overlap_match = match_chapter_by_overlap(body_xml, chapters, used_ids=used)
    if overlap_match and overlap_match["text"].strip():
        return overlap_match["text"], overlap_match

    return str(source.get("text") or ""), None
