# Daozang import

Import 方瞳子源 (Fang Tongzi) transcriptions of the Zhengtong and Wanli Supplement Daozang into project TEI.

The plugin ships with a **bundled UTF-8 corpus** (`data/corpus/`, 1,513 texts, ~77 MB). Users can search and import immediately after install — no download from third-party sites.

## Bundled corpus (maintainers)

Build or refresh bundled data before `npm run release`:

```bash
cd plugins/packages/plugin-daozang-import

# From the Fang Tongzi RAR (slow: extract + convert)
node scripts/build-corpus-data.mjs --from-rar ~/Downloads/DaoCanon_txt_chm.rar

# Or from an already-extracted 道藏_txt folder (fast)
node scripts/build-corpus-data.mjs --from-utf8 ~/Downloads/DaoCanon_txt_chm/道藏_txt
```

This writes:

```
data/corpus/
  utf8/           # UTF-8 .txt files
  index.json      # search index
  manifest.json   # provenance
```

These paths are listed in `plugin.manifest.json` → `bundled`, so they are included in the plugin release archive.

**Kanripo crosswalk:** KR_ID → bundled Daozang filename lives in the sibling **kanripo-import** plugin (`data/concordance/kanripo_daozang_map.json`). Rebuild with `npm run build:concordance -w @ljb/plugin-kanripo-import`.

`data/corpus/utf8/` is gitignored locally because of size; CI/release machines run the build script before packaging.

Optional separate redistributable pack (same bytes, different layout):

```bash
node scripts/build-corpus-pack.mjs --from-utf8 data/corpus/utf8
```

## User workflow

1. Install and enable the plugin (**Tools → Plugins**).
2. **File → Import from Daozang…** — bundled corpus is ready immediately.
3. Optionally **Install corpus from file…** to replace the cache with a newer local copy.

## Requirements

- Python 3 on `PATH` (for TEI conversion and optional local corpus install)
- A RAR extractor only if installing from `.rar` locally: `unar`, `7z`, `unrar`, or `bsdtar`

## Development

```bash
cd plugins
npm run smoke:daozang-import
```

Install in LJB via **Tools → Plugins → Install from folder…** pointing at `packages/plugin-daozang-import` (after `build-corpus-data` has been run once).
