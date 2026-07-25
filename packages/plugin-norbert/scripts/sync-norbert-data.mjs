#!/usr/bin/env node
/** Copy compiled Norbert auxiliary data from authoritypacks into the plugin bundle. */
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const packDir = path.resolve(__dirname, '../../../../authoritypacks/packs/norbert');
const outDir = path.resolve(__dirname, '../data');

const files = ['surnames.json', 'geo-admin-suffixes.json'];

for (const file of files) {
  const src = path.join(packDir, file);
  if (!fs.existsSync(src)) {
    console.error(`Missing ${src} — run: cd authoritypacks && npm run compile:norbert`);
    process.exit(1);
  }
  fs.mkdirSync(outDir, { recursive: true });
  fs.copyFileSync(src, path.join(outDir, file));
  console.log(`synced ${file}`);
}
