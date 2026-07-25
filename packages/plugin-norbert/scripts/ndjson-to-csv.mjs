#!/usr/bin/env node
/**
 * Convert wiki-noble-titles.ndjson → CSV for manual review.
 *
 * Usage:
 *   node scripts/ndjson-to-csv.mjs [--in PATH] [--out PATH]
 */
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));

function arg(name, fallback) {
  const index = process.argv.indexOf(name);
  return index >= 0 && process.argv[index + 1] ? process.argv[index + 1] : fallback;
}

const inPath = path.resolve(__dirname, '../data', arg('--in', 'wiki-noble-titles.ndjson'));
const outPath = path.resolve(__dirname, '../data', arg('--out', 'wiki-noble-titles.csv'));

const COLUMNS = [
  'sourcePage',
  'sourcePageId',
  'sourcePageUrl',
  'sourceWikidataId',
  'dynastySection',
  'fief',
  'pn',
  'nt',
  'person',
  'wikiPersonTitle',
  'wikiPersonPageId',
  'wikiPersonUrl',
  'wikidataId',
  'startYear',
  'endYear',
  'confidence',
  'needsReview',
  'rawLine',
  'source',
];

/** @param {unknown} value */
function csvCell(value) {
  if (value == null) return '';
  const text = String(value);
  if (/[",\n\r]/.test(text)) return `"${text.replace(/"/g, '""')}"`;
  return text;
}

const text = fs.readFileSync(inPath, 'utf8').trim();
if (!text) {
  console.error(`empty input: ${inPath}`);
  process.exit(1);
}

const rows = text.split('\n').map((line) => JSON.parse(line));
const header = COLUMNS.map(csvCell).join(',');
const body = rows.map((row) => COLUMNS.map((col) => csvCell(row[col])).join(',')).join('\n');

fs.writeFileSync(outPath, `${header}\n${body}\n`);
console.log(`wrote ${rows.length} rows → ${outPath}`);
