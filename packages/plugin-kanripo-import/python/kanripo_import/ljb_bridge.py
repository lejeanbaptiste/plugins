"""JSON stdin/stdout bridge for Kanripo convert + parallel punctuation."""

from __future__ import annotations

import json
import sys
from pathlib import Path


def cli_main() -> None:
    payload = json.load(sys.stdin)
    op = payload.get("op") or "convert"

    if op == "parallel_punct":
        from kanripo_import.parallel_punct import apply_parallel_sources, coverage_from_stamps

        body_xml = str(payload.get("body_xml") or "")
        if payload.get("stamps_only"):
            result = {
                "body_xml": body_xml,
                "coverage": coverage_from_stamps(body_xml),
                "applied": False,
            }
            json.dump(result, sys.stdout, ensure_ascii=False)
            sys.stdout.write("\n")
            return

        sources = payload.get("sources")
        if not isinstance(sources, list):
            sources = [
                {
                    "id": "paste",
                    "label": "Paste",
                    "text": str(payload.get("parallel_text") or ""),
                }
            ]
        result = apply_parallel_sources(body_xml, sources)
        json.dump(result, sys.stdout, ensure_ascii=False)
        sys.stdout.write("\n")
        return

    from normalization_zh.kanripo_tei import convert_kanripo_txt

    path = Path(str(payload.get("path") or ""))
    if not path.is_file():
        raise SystemExit(f"Kanripo file not found: {path}")
    normalize = payload.get("normalize") or "off"
    if normalize not in ("off", "dpm", "hard_replacements"):
        raise SystemExit(f"Unknown normalize mode: {normalize}")
    result = convert_kanripo_txt(path, normalize=normalize)
    json.dump(result, sys.stdout, ensure_ascii=False)
    sys.stdout.write("\n")


if __name__ == "__main__":
    cli_main()
