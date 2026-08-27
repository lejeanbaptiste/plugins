# Kanripo import (`kanripo-import`)

Clone a [Kanseki Repository](https://github.com/kanripo) work and convert each juan to project TEI.

Conversion lives in `normalization_zh.kanripo_tei` (not `segment_kanripo_document`, which strips page breaks for reuse matching). Parallel punctuation (several files/pastes, overlap only) lives in this plugin: `kanripo_import.parallel_punct`.

## Build

```bash
cd plugins
npm install
npm run build:kanripo-import
npm run smoke:kanripo-import
```

## Development with LJB desktop

1. Build the plugin
2. Start LJB (`npm run dev:desktop` from `lejeanbaptiste`)
3. Enable **Kanripo import** in Tools → Plugins
4. Python must import `normalization_zh` (sibling `normalization_zh/src` on `PYTHONPATH` in dev)

## Architecture

| Layer | Location |
|-------|----------|
| Manifest, work index, Python bridge | This package |
| Thin `dist/register.mjs` | This package |
| Wizard UI | LJB host module `plugins/hostModules/kanripoImportUi.ts` |
| Mandoku → TEI body | `normalization_zh.kanripo_tei` (to be vendored) |
| Parallel punctuate | `python/kanripo_import/parallel_punct.py` |
