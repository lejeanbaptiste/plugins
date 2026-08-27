"""Infix / superset overlap: copy punctuation from a parallel onto Kanripo TEI.

The Kanripo ``body_xml`` is the tape. The parallel is often a shorter sticker.
Unmatched prefix/suffix stay as-is. Wrong text → no overlap (empty coverage).
"""

from __future__ import annotations

import re
from difflib import SequenceMatcher
from typing import TypedDict
from xml.etree import ElementTree as ET

HAN_RE = re.compile(r"[\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff]")
PUNCT_CHARS = set("。，、：；？！「」『』（）〔〕.,;:!?")
SEG_ANA = "ljb:parallel-punct"
SEG_OPEN = f'<seg ana="{SEG_ANA}">'
NOTE_RE = re.compile(r"<note\b[^>]*>.*?</note>", re.DOTALL)
PB_RE = re.compile(r"<pb\b[^>]*/>")
TAG_RE = re.compile(r"</?[A-Za-z][^>]*>")
SEG_OPEN_RE = re.compile(r'<seg\b[^>]*\bana="[^"]*\bljb:parallel-punct[^"]*"[^>]*>')
MIN_BLOCK = 8
MIN_STICKER_COVER = 0.8


class CoverageSpan(TypedDict):
    start: float
    end: float
    covered_chars: int
    source: str
    preview: str


class Coverage(TypedDict):
    start: float
    end: float
    covered_chars: int
    total_chars: int
    ratio: float
    empty: bool
    spans: list[CoverageSpan]


class ParallelPunctResult(TypedDict):
    body_xml: str
    coverage: Coverage
    applied: bool


def han_only(text: str) -> str:
    return "".join(HAN_RE.findall(text))


def _empty_coverage(total: int) -> Coverage:
    return {
        "start": 0.0,
        "end": 0.0,
        "covered_chars": 0,
        "total_chars": total,
        "ratio": 0.0,
        "empty": True,
        "spans": [],
    }


def _union_covered(intervals: list[tuple[int, int]]) -> int:
    if not intervals:
        return 0
    ordered = sorted(intervals)
    merged: list[list[int]] = [list(ordered[0])]
    for start, end in ordered[1:]:
        last = merged[-1]
        if start <= last[1]:
            last[1] = max(last[1], end)
        else:
            merged.append([start, end])
    return sum(end - start for start, end in merged)


def _coverage_from_intervals(
    total: int, intervals: list[tuple[int, int]], spans: list[CoverageSpan]
) -> Coverage:
    covered = _union_covered(intervals)
    if not intervals or not total:
        return _empty_coverage(total)
    start = min(item[0] for item in intervals)
    end = max(item[1] for item in intervals)
    return {
        "start": start / total,
        "end": end / total,
        "covered_chars": covered,
        "total_chars": total,
        "ratio": covered / total,
        "empty": covered == 0,
        "spans": spans,
    }


def find_han_overlap(tape: str, sticker: str) -> tuple[int, int] | None:
    """Return ``(tape_start, tape_end)`` han indices, or None."""
    if not tape or not sticker:
        return None
    if len(sticker) <= len(tape):
        exact = tape.find(sticker)
        if exact >= 0:
            return exact, exact + len(sticker)
        matcher = SequenceMatcher(a=tape, b=sticker, autojunk=False)
        blocks = [block for block in matcher.get_matching_blocks() if block.size >= MIN_BLOCK]
        if not blocks:
            return None
        best = max(blocks, key=lambda block: block.size)
        if best.size / len(sticker) < MIN_STICKER_COVER:
            return None
        return best.a, best.a + best.size
    exact = sticker.find(tape)
    if exact >= 0:
        return 0, len(tape)
    matcher = SequenceMatcher(a=sticker, b=tape, autojunk=False)
    blocks = [block for block in matcher.get_matching_blocks() if block.size >= MIN_BLOCK]
    if not blocks:
        return None
    best = max(blocks, key=lambda block: block.size)
    if best.size / len(tape) < MIN_STICKER_COVER:
        return None
    return best.b, best.b + best.size


def _iter_xml_atoms(xml: str) -> list[str]:
    """Split XML into notes, pb milestones, other tags, and single characters."""
    atoms: list[str] = []
    i = 0
    n = len(xml)
    while i < n:
        if xml.startswith("<", i):
            note = NOTE_RE.match(xml, i)
            if note:
                atoms.append(note.group(0))
                i = note.end()
                continue
            pb = PB_RE.match(xml, i)
            if pb:
                atoms.append(pb.group(0))
                i = pb.end()
                continue
            tag = TAG_RE.match(xml, i)
            if tag:
                atoms.append(tag.group(0))
                i = tag.end()
                continue
        atoms.append(xml[i])
        i += 1
    return atoms


def _is_markup(atom: str) -> bool:
    return atom.startswith("<")


def _is_stamp_open(atom: str) -> bool:
    return bool(SEG_OPEN_RE.fullmatch(atom) or atom == SEG_OPEN)


def _stamp_depth_delta(atom: str, stamp_depth: int, other_seg_depth: int) -> tuple[int, int]:
    """Track our stamped ``<seg>`` separately from any other ``<seg>``."""
    if _is_stamp_open(atom):
        return stamp_depth + 1, other_seg_depth
    if atom.startswith("<seg") and not atom.startswith("</"):
        return stamp_depth, other_seg_depth + 1
    if atom == "</seg>":
        if other_seg_depth > 0:
            return stamp_depth, other_seg_depth - 1
        if stamp_depth > 0:
            return stamp_depth - 1, other_seg_depth
    return stamp_depth, other_seg_depth


def _han_tape(atoms: list[str]) -> tuple[str, list[int]]:
    han_atom_index: list[int] = []
    for idx, atom in enumerate(atoms):
        if not _is_markup(atom) and HAN_RE.fullmatch(atom):
            han_atom_index.append(idx)
    tape = "".join(atoms[i] for i in han_atom_index)
    return tape, han_atom_index


def coverage_from_stamps(body_xml: str) -> Coverage:
    """Rebuild coverage from existing ``ana="ljb:parallel-punct"`` stretches."""
    atoms = _iter_xml_atoms(body_xml)
    tape, _ = _han_tape(atoms)
    total = len(tape)
    intervals: list[tuple[int, int]] = []
    spans: list[CoverageSpan] = []
    stamp_depth = 0
    other_seg_depth = 0
    run_start: int | None = None
    han_seen = -1
    for atom in atoms:
        prev = stamp_depth
        stamp_depth, other_seg_depth = _stamp_depth_delta(atom, stamp_depth, other_seg_depth)
        if stamp_depth > prev:
            if prev == 0:
                run_start = han_seen + 1
            continue
        if stamp_depth < prev:
            if stamp_depth == 0 and run_start is not None and han_seen >= run_start:
                start, end = run_start, han_seen + 1
                intervals.append((start, end))
                preview = tape[start:end][:40]
                spans.append(
                    {
                        "start": start / total if total else 0.0,
                        "end": end / total if total else 0.0,
                        "covered_chars": end - start,
                        "source": "stamped",
                        "preview": preview,
                    }
                )
            run_start = None
            continue
        if not _is_markup(atom) and HAN_RE.fullmatch(atom):
            han_seen += 1
    return _coverage_from_intervals(total, intervals, spans)


def _apply_one(body_xml: str, parallel_text: str) -> tuple[str, tuple[int, int] | None, str]:
    atoms = _iter_xml_atoms(body_xml)
    tape, _ = _han_tape(atoms)
    sticker = han_only(parallel_text)
    overlap = find_han_overlap(tape, sticker)
    if overlap is None:
        return body_xml, None, ""

    tape_start, tape_end = overlap
    insertions: dict[int, str] = {}
    para_after: set[int] = set()

    if len(sticker) <= len(tape) and tape[tape_start:tape_end] == sticker:
        sticker_origin = 0
    elif len(sticker) > len(tape) and sticker.find(tape) >= 0:
        sticker_origin = sticker.find(tape)
    else:
        sticker_origin = 0

    han_in_sticker = 0
    pending_nl = 0
    for char in parallel_text.replace("\r\n", "\n").replace("\r", "\n"):
        if HAN_RE.fullmatch(char):
            if pending_nl >= 2:
                local = han_in_sticker - sticker_origin - 1
                if 0 <= local < (tape_end - tape_start):
                    para_after.add(tape_start + local)
            pending_nl = 0
            han_in_sticker += 1
            continue
        if char == "\n":
            pending_nl += 1
            continue
        pending_nl = 0
        if char in PUNCT_CHARS:
            local = han_in_sticker - sticker_origin - 1
            if 0 <= local < (tape_end - tape_start):
                at = tape_start + local
                insertions[at] = insertions.get(at, "") + char

    out: list[str] = []
    han_seen = -1
    opened_here = 0
    stamp_depth = 0
    other_seg_depth = 0
    for atom in atoms:
        is_han = (not _is_markup(atom)) and HAN_RE.fullmatch(atom)
        stamp_depth, other_seg_depth = _stamp_depth_delta(atom, stamp_depth, other_seg_depth)
        if is_han:
            han_seen += 1
            if (
                han_seen == tape_start
                and stamp_depth == 0
                and opened_here == 0
            ):
                out.append(SEG_OPEN)
                opened_here += 1
                stamp_depth += 1
        out.append(atom)
        if is_han:
            extra = insertions.get(han_seen, "")
            if extra:
                out.append(extra)
            if han_seen in para_after:
                if opened_here > 0:
                    out.append(f"</seg></p><p>{SEG_OPEN}")
                else:
                    out.append("</p><p>")
            if han_seen == tape_end - 1 and opened_here > 0:
                out.append("</seg>")
                opened_here -= 1
                stamp_depth = max(0, stamp_depth - 1)
    while opened_here > 0:
        out.append("</seg>")
        opened_here -= 1

    preview = tape[tape_start:tape_end][:40]
    return "".join(out), overlap, preview


def apply_parallel_punctuation(body_xml: str, parallel_text: str) -> ParallelPunctResult:
    """Insert parallel punctuation/paragraphs onto the overlapping Han range."""
    return apply_parallel_sources(body_xml, [{"id": "paste", "label": "Paste", "text": parallel_text}])


def apply_parallel_sources(body_xml: str, sources: list[dict[str, str]]) -> ParallelPunctResult:
    """Apply named sources in order. Fail closed per source. Union coverage."""
    atoms = _iter_xml_atoms(body_xml)
    tape, _ = _han_tape(atoms)
    total = len(tape)
    xml = body_xml
    intervals: list[tuple[int, int]] = []
    spans: list[CoverageSpan] = []
    applied_any = False

    for source in sources:
        text = str(source.get("text") or "")
        label = str(source.get("label") or source.get("id") or "source")
        if not text.strip():
            continue
        xml, overlap, preview = _apply_one(xml, text)
        if overlap is None:
            continue
        start, end = overlap
        applied_any = True
        intervals.append((start, end))
        spans.append(
            {
                "start": start / total if total else 0.0,
                "end": end / total if total else 0.0,
                "covered_chars": end - start,
                "source": label,
                "preview": preview,
            }
        )

    coverage = _coverage_from_intervals(total, intervals, spans)
    return {"body_xml": xml, "coverage": coverage, "applied": applied_any}


def assert_well_formed(xml: str) -> None:
    """Raise if ``xml`` is not a well-formed fragment (wrapped for parse)."""
    ET.fromstring(f"<root>{xml}</root>")
