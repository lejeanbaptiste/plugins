# LJB plugins

Optional plugins for [Le Jean-Baptiste](https://github.com/lejeanbaptiste/lejeanbaptiste): specialized tools that not every user needs, installed from **Tools → Plugins**.

## Layout

```
plugins/
  docs/manifest.md          # manifest spec
  schema/                   # JSON Schema
  packages/
    plugin-sdk/             # validate manifests
    plugin-cjk-dates/       # East Asian dates (Sanmiao)
    plugin-norbert/         # Chinese prosopography
```

Each plugin folder contains **`plugin.manifest.json`** — the contract the LJB host reads at install time.

## Quick start

```bash
npm run validate    # check all plugin.manifest.json files
npm run release     # build GitHub Release archives and plugins-index.json
```

## Plugins (planned)

| Plugin | Id | For |
|--------|-----|-----|
| East Asian dates | `cjk-dates` | Premodern China, Japan, Korea — date tagging & disambiguation |
| Norbert | `norbert` | Chinese entity tagging, contextual disambiguation, noble titles, Norbert authority pack |

## Related repos

- **lejeanbaptiste** — editor + plugin *host* (Tools panel, suggestion pipeline)
- **authoritypacks** — compile Norbert/CBDB/Wikidata NDJSON packs; Norbert plugin references those releases

## Documentation

See [`docs/manifest.md`](docs/manifest.md) for the full manifest format.

## Releases

`npm run release` builds each plugin's runtime entry and emits a versioned
`ljb-plugin-<id>-<version>.tar.gz` archive plus `plugins-index.json`. The
`build-plugins` GitHub Actions workflow publishes those files as release
assets when a `v*` tag is pushed. LJB fetches that index from the latest
release, verifies the archive SHA-256, checks archive paths, and installs the
package under its per-user plugin directory. Platform-specific Python
runtimes are downloaded after installation, so archives remain portable.
