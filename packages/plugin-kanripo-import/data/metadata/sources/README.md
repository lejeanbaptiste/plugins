# Bundled metadata sources

Self-contained CSV inputs for `npm run build:metadata`. No external paths required at build or import time.

| File | Role |
|------|------|
| `krp_works.csv` | Titles, juan file counts |
| `skqs_org_authorship.csv` | SKQS authors, dynasty, dates, extent |
| `dz_metadata_works.csv` | Daozang work titles, volumes (for KR ↔ DZ) |
| `dz_metadata_authors.csv` | **All** Daozang authors with Norbert `person_id` |
| `DZ_metadata_normalized.csv` | Dynasty and date hints for Daozang works |

KR_ID → DZID crosswalk: bundled `data/concordance/krp_dz_collation.csv` and `kanripo_org_concordance.csv`.

When a Kanripo work maps to a DZID, the build merges **full** Daozang authorship (not just the lead author from collation).

Maintainers may refresh tables:

```bash
python3 scripts/build-kanripo-metadata.py --sync-from /path/to/chinese_corpus_metadata
npm run build:metadata
```
