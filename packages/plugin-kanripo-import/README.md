# Kanripo import plugin

Self-contained hybrid plugin: Mandoku → TEI conversion, bundled gaiji tables/PNGs, parallel punctuation, and work search index. **No external `normalization_zh` checkout required.**

## What ships in the plugin

| Piece | Location |
| --- | --- |
| Mandoku → TEI body | `python/kanripo_import/kanripo_tei.py` |
| Gaiji (`&KRnnnn;`) resolution | `python/kanripo_import/kanripo_gaiji.py` |
| KR-Gaiji charlist + PNGs | `data/gaiji/` |
| DPM + hard-replacement CSVs | `data/normalize/` |
| Parallel punctuation | `python/kanripo_import/parallel_punct.py` |
| Work search index | `data/krp_works.json` |
| KR ↔ DZ / Daozang concordance | `data/concordance/` (see below) |
| Wizard UI | LJB host module (`kanripoImportUi`) |

## Concordance data (Kanripo ↔ 方瞳子 Daozang)

Bundled under `data/concordance/` for offline KR_ID ↔ DZID ↔ bundled Daozang filename lookup:

| File | Role |
| --- | --- |
| `krp_dz_collation.csv` | Work-level KR_ID ↔ DZID (~1500 Daoist texts; from `chinese_corpus_metadata`) |
| `kanripo_org_concordance.csv` | Kanripo.org catalogue ↔ CBETA / DZID |
| `dz_corpus_works.csv` | DZID ↔ Fang Tongzi corpus filename |
| `duren_jing_index.csv` | Curated Duren jing KR ↔ DZ paths (`dz_krp/index.csv`) |
| `kanripo_daozang_map.json` | Runtime map: KR_ID → bundled Daozang `rel_path` |
| `kanripo_daozang_overrides.csv` | Manual overrides (maintainer-edited) |

Refresh from upstream tables:

```bash
npm run build:concordance -w @ljb/plugin-kanripo-import
```

Python API: `kanripo_import.concordance.lookup_daozang_rel_path("KR5a0087")`.

## Gaiji handling

- Unicode or IDS entries from [kanripo/KR-Gaiji](https://github.com/kanripo/KR-Gaiji) resolve to characters or bracket notation.
- Image-only entries emit inline TEI:

  `<g type="kanripo" n="KR0954"><graphic url="_gaiji/KR0954.png" height="1em"/></g>`

  PNGs are copied into `<project>/imported/kanripo/<KR_ID>/_gaiji/` during import. The visual editor resolves `_gaiji/…` relative to the open XML file and renders these at **1em height** (inline, baseline-aligned). Paste/crop tooling is a follow-up.

## Refresh gaiji data

```bash
npm run download:gaiji -w @ljb/plugin-kanripo-import
```

## Dev smoke test

```bash
npm run build:kanripo-import
npm run smoke:kanripo-import
```

## Batch parallel test (no GUI)

Check every juan in a Kanripo work against one parallel source — well-formed XML and coverage per file:

```bash
npm run test:parallel-batch -w @ljb/plugin-kanripo-import -- \
  --kanripo /path/to/KR4h0002 \
  --ctext-url 'https://ctext.org/wiki.pl?if=gb&chapter=793335'
```

Or with a saved parallel file:

```bash
npm run fetch:ctext -w @ljb/plugin-kanripo-import -- \
  --url 'https://ctext.org/wiki.pl?if=gb&chapter=793335' > /tmp/ctext.txt

npm run test:parallel-batch -w @ljb/plugin-kanripo-import -- \
  --kanripo /path/to/KR4h0002 --parallel /tmp/ctext.txt
```

**ctext URL:** use a **wiki commentary page** (`…/wiki.pl?…&chapter=…`), not a library/reading root URL. One wiki chapter often matches only part of a multi-juan Kanripo work (other juans correctly show ~0% overlap).

Requires sibling `leaf-writer` (or `LJB_HOST_ROOT`) for host UI wiring check. Python tests run against bundled data with `LJB_PLUGIN_INSTALL_PATH` set automatically in smoke.

## CLI: convert + segmented parallel punctuation

From the plugin package root, with sibling `leaf-writer` for bundled Python:

```bash
PLUGIN="/path/to/plugins/packages/plugin-kanripo-import"
PY="/path/to/leaf-writer/apps/desktop/resources/python/bin/python3"
export LJB_PLUGIN_INSTALL_PATH="$PLUGIN" PYTHONPATH="$PLUGIN/python"

# 1. Convert Kanripo txt → TEI body
echo '{"path":"/path/to/KR4h0002_001.txt","normalize":"off","gaiji_dest_dir":"/tmp/_gaiji"}' \
  | "$PY" -c "from kanripo_import.ljb_bridge import cli_main; cli_main()" \
  > /tmp/kanripo-body.json

# 2. Fetch whole ctext wiki chapter (default: all rows on the page)
npm run fetch:ctext -w @ljb/plugin-kanripo-import -- \
  --url 'https://ctext.org/wiki.pl?if=gb&chapter=793335' \
  > /tmp/ctext-whole.txt

# Optional: one section only
npm run fetch:ctext -w @ljb/plugin-kanripo-import -- \
  --url 'https://ctext.org/wiki.pl?if=gb&chapter=793335' --section 兩都賦序 \
  > /tmp/ctext-section.txt

# 3. Apply segmented punctuation (basetext + commentary matched separately)
python3 - <<'PY'
import json, os, subprocess
from pathlib import Path
plugin = Path(os.environ["LJB_PLUGIN_INSTALL_PATH"])
body = json.loads(Path("/tmp/kanripo-body.json").read_text())["body_xml"]
parallel = Path("/tmp/ctext-whole.txt").read_text()
payload = {"op": "parallel_punct", "mode": "segmented", "body_xml": body, "parallel_text": parallel}
proc = subprocess.run(
    ["python3", "-c", "from kanripo_import.ljb_bridge import cli_main; cli_main()"],
    input=json.dumps(payload),
    text=True,
    capture_output=True,
    cwd=plugin / "python",
    env={**os.environ, "PYTHONPATH": str(plugin / "python")},
    check=True,
)
print(json.loads(proc.stdout)["coverage"])
PY
```

`mode: "segmented"` merges split commentary notes (`</note></p><p><note type="comm">`), then matches basetext and `<note type="comm">` segments separately against ctext-style inline commentary. Use `mode: "tape"` (default) for a single contiguous Han sticker.

## Install in LJB

1. `npm run build:kanripo-import` in `plugins`
2. `npm run dev:desktop` in `leaf-writer`
3. Tools → Plugins → install `packages/plugin-kanripo-import`, enable per project
