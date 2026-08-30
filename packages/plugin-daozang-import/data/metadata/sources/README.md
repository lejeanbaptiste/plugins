# Bundled metadata sources

These CSVs are copied into the plugin so builds and imports need no external paths.

| File | Role |
|------|------|
| `dz_metadata_works.csv` | DZID, title, volumes, Fang Tongzi filename |
| `dz_metadata_authors.csv` | Authors with Norbert `person_id` |
| `krp_dz_collation.csv` | Kanripo KR_ID ↔ DZID |
| `DZ_metadata_normalized.csv` | Dynasty and date hints (optional) |
| `dz_wikidata_qids.json` | Wikisource TOC matches: page, URL, Q-id, `match_tier` |

Refresh from upstream (maintainers):

```bash
python3 scripts/build-daozang-metadata.py --sync-from /path/to/chinese_corpus_metadata \
  --normalized-csv /path/to/DZ_metadata_normalized.csv
npm run build:metadata
```

Wikisource ids come from `tables_output/wikidata_explore/dz_wikidata_qids.json` (run `export_dz_wikidata_qids.py` in chinese_corpus_metadata first).
