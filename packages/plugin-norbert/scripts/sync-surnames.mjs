#!/usr/bin/env node
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const src = path.resolve(__dirname, '../../../../authoritypacks/packs/norbert/surnames.json');
const dest = path.join(__dirname, '../data/surnames.json');

if (!fs.existsSync(src)) {
  console.warn(`[plugin-norbert] surnames source missing (${src}); keeping bundled data`);
  process.exit(0);
}

fs.mkdirSync(path.dirname(dest), { recursive: true });
fs.copyFileSync(src, dest);
console.log(`[plugin-norbert] synced surnames → data/surnames.json`);
