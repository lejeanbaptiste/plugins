"""JSON stdin/stdout bridge: convert one Kanripo .txt via normalization_zh."""

from __future__ import annotations

import json
import sys
from pathlib import Path


def cli_main() -> None:
    payload = json.load(sys.stdin)
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
