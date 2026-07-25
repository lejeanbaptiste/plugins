#!/usr/bin/env node
/**
 * Normalize wiki NT rows, match against Norbert, export human-review CSV.
 *
 * Usage:
 *   node scripts/prepare-wiki-review.mjs
 *   node scripts/prepare-wiki-review.mjs --sql /path/to/norbert.sql
 *   node scripts/prepare-wiki-review.mjs --only-matched
 */
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { normalizeWikiRows } from '../src/wikiNobleTitles/normalizeWikiNt.mjs';
import {
  DEFAULT_NORBERT_SQL,
  loadNorbertMatchData,
  matchWikiRows,
} from '../src/wikiNobleTitles/matchWikiNorbert.mjs';
import { rowsToReviewCsv } from '../src/wikiNobleTitles/reviewCsv.mjs';

const __dirname = path.dirname(fileURLToPath(import.meta.url));

function arg(name, fallback = null) {
  const index = process.argv.indexOf(name);
  return index >= 0 && process.argv[index + 1] ? process.argv[index + 1] : fallback;
}

function hasFlag(name) {
  return process.argv.includes(name);
}

const inPath = path.resolve(__dirname, '../data', arg('--in', 'wiki-noble-titles.ndjson'));
const outCsv = path.resolve(__dirname, '../data', arg('--out', 'wiki-norbert-review.csv'));
const outJson = path.resolve(__dirname, '../data', arg('--json', 'wiki-norbert-review.ndjson'));
const sqlPath = path.resolve(arg('--sql', DEFAULT_NORBERT_SQL));
const onlyMatched = hasFlag('--only-matched');

const rawText = fs.readFileSync(inPath, 'utf8').trim();
if (!rawText) {
  console.error(`empty input: ${inPath}`);
  process.exit(1);
}

const rawRows = rawText.split('\n').map((line) => JSON.parse(line));
console.log(`loaded ${rawRows.length} wiki rows from ${inPath}`);

console.log('normalizing (traditional Chinese, fill gaps)...');
const cleaned = await normalizeWikiRows(rawRows);
const ready = cleaned.filter((row) => row.reviewStatus === 'ready');
console.log(`  ready: ${ready.length}, skipped sections/duplicates: ${cleaned.length - ready.length}`);

console.log(`loading Norbert from ${sqlPath}...`);
const norbert = await loadNorbertMatchData(sqlPath);
console.log(`  person_nt rows: ${norbert.ntRows.length}`);

console.log('matching...');
let matched = matchWikiRows(cleaned, norbert);

if (onlyMatched) {
  matched = matched.filter((row) =>
    ['matched', 'person_only', 'ambiguous'].includes(String(row.matchStatus)),
  );
}

const counts = {};
for (const row of matched) {
  const key = String(row.suggestedAction ?? 'none');
  counts[key] = (counts[key] ?? 0) + 1;
}

fs.writeFileSync(outJson, `${matched.map((row) => JSON.stringify(row)).join('\n')}\n`);
fs.writeFileSync(outCsv, rowsToReviewCsv(matched));

console.log(`wrote ${outCsv}`);
console.log(`wrote ${outJson}`);
console.log('suggested actions:', counts);
console.log('');
console.log('Review instructions:');
console.log('  1. Open wiki-norbert-review.csv in a spreadsheet');
console.log('  2. Fill the "action" column (override suggested_action if needed):');
console.log('       link      = same NT row, add wiki crosswalk only');
console.log('       insert_nt = person exists, add person_nt row from wiki');
console.log('       update_nt = fill missing pn/dates on existing person_nt');
console.log('       skip      = ignore this row');
console.log('       review    = needs manual decision');
console.log('  3. Add notes in reviewer_notes as needed');
