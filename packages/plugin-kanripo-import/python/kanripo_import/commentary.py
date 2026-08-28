"""Validate Kanripo parenthetical commentary spans."""

from __future__ import annotations

import re
from dataclasses import dataclass

_GAIJI_BRACKET_RE = re.compile(r"\[[^\]\n]*\]")


@dataclass(frozen=True)
class RawCommentarySpan:
    text: str
    start_offset: int
    end_offset: int
    start_line: int
    end_line: int


def _protect_parens_inside_gaiji_brackets(text: str) -> str:
    def _repl(match: re.Match[str]) -> str:
        return match.group(0).replace("(", "（").replace(")", "）")

    return _GAIJI_BRACKET_RE.sub(_repl, text)


def extract_commentary_from_text(text: str) -> tuple[str, list[RawCommentarySpan]]:
    in_commentary = False
    line_no = 1
    seg_start_offset = -1
    seg_start_line = -1
    square_depth = 0
    seg_chars: list[str] = []
    base_chars: list[str] = []
    spans: list[RawCommentarySpan] = []

    parse_text = _protect_parens_inside_gaiji_brackets(text)
    for index, ch in enumerate(parse_text):
        orig_ch = text[index]
        if orig_ch == "\n":
            line_no += 1

        if in_commentary:
            if ch == "[":
                square_depth += 1
                seg_chars.append(orig_ch)
                continue
            if ch == "]":
                if square_depth > 0:
                    square_depth -= 1
                seg_chars.append(orig_ch)
                continue
            if ch == ")" and square_depth == 0:
                spans.append(
                    RawCommentarySpan(
                        text="".join(seg_chars),
                        start_offset=seg_start_offset,
                        end_offset=index + 1,
                        start_line=seg_start_line,
                        end_line=line_no,
                    )
                )
                in_commentary = False
                square_depth = 0
                seg_chars = []
            else:
                seg_chars.append(orig_ch)
            continue

        if ch == "(":
            in_commentary = True
            seg_start_offset = index
            seg_start_line = line_no
            seg_chars = []
            continue
        if ch == ")":
            base_chars.append(orig_ch)
            continue
        base_chars.append(orig_ch)

    if in_commentary:
        raise ValueError(
            f"Unclosed '(' starting at line {seg_start_line}, offset {seg_start_offset}"
        )
    return "".join(base_chars), spans
