import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { validatePluginManifest } from './validate.mjs';
import { PLUGIN_MANIFEST_FILENAME } from './types.mjs';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const packagesDir = path.resolve(__dirname, '..');

test('validates cjk-dates and norbert manifests', () => {
  for (const pluginDir of ['plugin-cjk-dates', 'plugin-norbert']) {
    const raw = JSON.parse(
      fs.readFileSync(path.join(packagesDir, pluginDir, PLUGIN_MANIFEST_FILENAME), 'utf8'),
    );
    const result = validatePluginManifest(raw);
    assert.equal(result.ok, true, pluginDir);
    if (result.ok) {
      assert.equal(result.manifest.manifestVersion, '1.0.0');
      assert.match(result.manifest.id, /^[a-z][a-z0-9-]*$/);
    }
  }
});

test('rejects unknown manifest version', () => {
  const result = validatePluginManifest({ manifestVersion: '9.0.0', id: 'x' });
  assert.equal(result.ok, false);
});
