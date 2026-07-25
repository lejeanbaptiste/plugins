# East Asian dates (`cjk-dates`)

Premodern date tagging and disambiguation for China, Japan, and Korea using [Sanmiao](https://pypi.org/project/sanmiao/).

## Status

**Phase 1 (current):** LJB gates calendar tools, East Asian date fields, and schema merge on this plugin being enabled. The bundled Python runtime is symlinked/copied into `{userData}/plugins/cjk-dates/python/` when the plugin is installed or enabled.

**Later phases:** Move sanmiao TypeScript UI, IPC bridge, and bundled Python out of core LJB into this package.

## Development

When you run the desktop app from source with an empty plugin folder, LJB seeds this package from `plugins/packages/` and auto-enables it so existing date workflows keep working.

To install manually: **Tools → Plugins… → Install from folder** and select this directory.

## Python runtime

The plugin manifest declares a bundled CPython tree under `python/`. In dev, the desktop app links that from `lejeanbaptiste/apps/desktop/resources/python` (populated by `npm run python:download` in `apps/desktop`).
