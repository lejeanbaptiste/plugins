"""JSON stdin/stdout bridge for Kanripo convert + parallel punctuation."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path


def _ensure_plugin_install_path() -> None:
    if os.environ.get("LJB_PLUGIN_INSTALL_PATH", "").strip():
        return
    inferred = Path(__file__).resolve().parents[2]
    if (inferred / "data" / "gaiji" / "charlist.org.txt").is_file():
        os.environ["LJB_PLUGIN_INSTALL_PATH"] = str(inferred)


def cli_main() -> None:
    payload = json.load(sys.stdin)
    _ensure_plugin_install_path()

    op = payload.get("op") or "convert"

    if op == "parallel_punct":
        from kanripo_import.parallel_punct import (
            apply_parallel_segmented_sources,
            apply_parallel_sources,
            coverage_from_stamps,
            merge_split_comm_notes,
        )

        body_xml = str(payload.get("body_xml") or "")
        mode = str(payload.get("mode") or "tape")
        if payload.get("merge_comm", True):
            body_xml = merge_split_comm_notes(body_xml)
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
        if mode == "segmented":
            result = apply_parallel_segmented_sources(body_xml, sources)
        else:
            result = apply_parallel_sources(body_xml, sources)
        json.dump(result, sys.stdout, ensure_ascii=False)
        sys.stdout.write("\n")
        return

    from kanripo_import.kanripo_tei import convert_kanripo_txt

    path = Path(str(payload.get("path") or ""))
    if not path.is_file():
        raise SystemExit(f"Kanripo file not found: {path}")
    normalize = payload.get("normalize") or "off"
    if normalize not in ("off", "dpm", "hard_replacements"):
        raise SystemExit(f"Unknown normalize mode: {normalize}")

    gaiji_dest = payload.get("gaiji_dest_dir")
    result = convert_kanripo_txt(
        path,
        normalize=normalize,
        gaiji_dest_dir=Path(gaiji_dest) if gaiji_dest else None,
    )
    json.dump(result, sys.stdout, ensure_ascii=False)
    sys.stdout.write("\n")


if __name__ == "__main__":
    cli_main()
