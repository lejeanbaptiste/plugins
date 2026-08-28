"""Decode legacy Chinese encodings to UTF-8."""

from __future__ import annotations

from daozang_import.constants import GB_ENCODINGS


def decode_legacy_text(raw: bytes) -> str:
    """Return UTF-8 text decoded from GB-family bytes, with UTF-8 BOM fallback."""
    if raw.startswith(b"\xef\xbb\xbf"):
        return raw[3:].decode("utf-8")
    for encoding in GB_ENCODINGS:
        try:
            return raw.decode(encoding)
        except UnicodeDecodeError:
            continue
    return raw.decode("utf-8", errors="replace")
