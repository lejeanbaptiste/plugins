#!/usr/bin/env node
/**
 * Compile reviewed wiki ↔ Norbert matches into a portable plugin asset.
 * Ships person ids + names + wiki links — NOT the full Norbert SQL dump.
 *
 * Usage:
 *   node scripts/compile-wiki-nt-asset.mjs
 *   node scripts/compile-wiki-nt-asset.mjs --review data/wiki-norbert-review.csv
 */
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { compileWikiNtAsset } from '../src/wikiNobleTitles/compileWikiNtAsset.mjs';

const __dirname = path.dirname(fileURLToPath(import.meta.url));

function arg(name, fallback = null) {
  const index = process.argv.indexOf(name);
  return index >= 0 && process.argv[index + 1] ? process.argv[index + 1] : fallback;
}

function parseCsv(text) {
  const lines = text.trim().split('\n');
  if (!lines.length) return [];
  const headers = parseCsvLine(lines[0]);
  return lines.slice(1).map((line) => {
    const values = parseCsvLine(line);
    /** @type {Record<string, string>} */
    const row = {};
    headers.forEach((header, i) => {
      row[header] = values[i] ?? '';
    });
    return row;
  });
}

/** @param {string} line */
function parseCsvLine(line) {
  /** @type {string[]} */
  const out = [];
  let cur = '';
  let inQuotes = false;
  for (let i = 0; i < line.length; i += 1) {
    const ch = line[i];
    if (inQuotes) {
      if (ch === '"') {
        if (line[i + 1] === '"') {
          cur += '"';
          i += 1;
        } else inQuotes = false;
      } else cur += ch;
      continue;
    }
    if (ch === '"') {
      inQuotes = true;
      continue;
    }
    if (ch === ',') {
      out.push(cur);
      cur = '';
      continue;
    }
    cur += ch;
  }
  out.push(cur);
  return out;
}

const ndjsonPath = path.resolve(__dirname, '../data', arg('--in', 'wiki-norbert-review.ndjson'));
const reviewCsv = path.resolve(__dirname, '../data', arg('--review', 'wiki-norbert-review.csv'));
const outJson = path.resolve(__dirname, '../data', arg('--out', 'wiki-nt-links.json'));
const outNdjson = path.resolve(__dirname, '../data', arg('--ndjson', 'wiki-nt-links.ndjson'));

const rows = fs.readFileSync(ndjsonPath, 'utf8').trim().split('\n').map((line, index) => ({
  review_id: index + 1,
  ...JSON.parse(line),
}));

/** @type {Record<string, Record<string, string>>} */
const correctionsByReviewId = {};
if (fs.existsSync(reviewCsv)) {
  for (const csvRow of parseCsv(fs.readFileSync(reviewCsv, 'utf8'))) {
    correctionsByReviewId[String(csvRow.review_id)] = csvRow;
  }
  console.log(`merged ${Object.keys(correctionsByReviewId).length} manual corrections`);
}

const asset = compileWikiNtAsset(rows, correctionsByReviewId);

fs.writeFileSync(outJson, `${JSON.stringify(asset, null, 2)}\n`);
fs.writeFileSync(outNdjson, `${asset.records.map((r) => JSON.stringify(r)).join('\n')}\n`);

console.log(`wrote ${outJson} (${asset.recordCount} records)`);
console.log(`wrote ${outNdjson}`);
console.log('actions:', asset.actionCounts);
