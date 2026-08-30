"""Fetch one Kanripo juan via pykanripo (kanripo.org API)."""

from __future__ import annotations

import re
from pathlib import Path

_KR_ID_RE = re.compile(r"^KR[a-z0-9]+$", re.I)
_LOC_RE = re.compile(r"^(KR[a-z0-9]+)_(\d+)$", re.I)


def resolve_juan_loc(kr_id: str, juan: str) -> str:
    """Resolve user input to a Kanripo file loc (stem of ``.txt``)."""
    kid = (kr_id or "").strip()
    if not _KR_ID_RE.match(kid):
        raise ValueError(f"Invalid Kanripo work id: {kr_id!r}")

    raw = (juan or "").strip()
    if not raw:
        raise ValueError("Enter a juan number (e.g. 001) or full loc (KR1a0030_001).")

    if raw.lower().endswith(".txt"):
        raw = raw[:-4]

    if raw.upper().startswith("KR") and "_" in raw:
        loc = raw
        match = _LOC_RE.match(loc)
        if not match:
            raise ValueError(f"Invalid loc: {raw!r}")
        if match.group(1).upper() != kid.upper():
            raise ValueError(f"Loc {loc!r} does not match work id {kid}.")
        suffix = int(match.group(2))
        return f"{kid}_{suffix:03d}"

    digits = re.sub(r"\D", "", raw)
    if digits.isdigit():
        return f"{kid}_{int(digits):03d}"

    raise ValueError(
        f"Could not parse juan {juan!r}. Use a number (1, 001) or full loc ({kid}_001)."
    )


def fetch_juan_text(loc: str) -> str:
    try:
        import kanripo  # pykanripo
    except ImportError as exc:
        raise RuntimeError(
            "kanripo API client is not installed in the desktop Python environment. "
            "Run npm run python:download in apps/desktop, or: pip install kanripo"
        ) from exc

    try:
        text = kanripo.get_result_file(loc)
    except Exception as exc:
        raise RuntimeError(f"Kanripo API fetch failed for {loc}: {exc}") from exc

    if text is None:
        raise RuntimeError(f"Kanripo API returned no text for {loc}.")
    if not isinstance(text, str):
        text = str(text)
    if not text.strip():
        raise RuntimeError(f"Kanripo API returned empty text for {loc}.")
    return text


def fetch_juan_to_cache(*, kr_id: str, juan: str, cache_root: str | Path) -> Path:
    loc = resolve_juan_loc(kr_id, juan)
    text = fetch_juan_text(loc)
    dest_dir = Path(cache_root) / kr_id
    dest_dir.mkdir(parents=True, exist_ok=True)
    path = dest_dir / f"{loc}.txt"
    path.write_text(text, encoding="utf-8")
    return path
