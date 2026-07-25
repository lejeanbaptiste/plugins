#!/usr/bin/env node
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { PLUGIN_MANIFEST_FILENAME } from './types.mjs';
import { validatePluginManifest } from './validate.mjs';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const repoRoot = path.resolve(__dirname, '../..');
const packagesDir = path.join(repoRoot, 'packages');

/** @type {string[]} */
const errors = [];
let checked = 0;

for (const entry of fs.readdirSync(packagesDir, { withFileTypes: true })) {
  if (!entry.isDirectory() || entry.name === 'plugin-sdk') continue;
  const manifestPath = path.join(packagesDir, entry.name, PLUGIN_MANIFEST_FILENAME);
  if (!fs.existsSync(manifestPath)) continue;

  checked += 1;
  const raw = JSON.parse(fs.readFileSync(manifestPath, 'utf8'));
  const result = validatePluginManifest(raw);
  if (!result.ok) {
    errors.push(`${entry.name}:`);
    for (const err of result.errors) errors.push(`  - ${err}`);
  } else {
    console.log(`ok  ${entry.name} (${result.manifest.id}@${result.manifest.version})`);
  }
}

if (checked === 0) {
  console.error('No plugin.manifest.json files found under packages/');
  process.exit(1);
}

if (errors.length) {
  console.error('\nValidation failed:\n');
  for (const line of errors) console.error(line);
  process.exit(1);
}

console.log(`\n${checked} manifest(s) valid.`);
