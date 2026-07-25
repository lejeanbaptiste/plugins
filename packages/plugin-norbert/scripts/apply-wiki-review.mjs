#!/usr/bin/env node
/**
 * Generate SQL from reviewed wiki ↔ Norbert matches.
 *
 * Policy (unless action column overrides):
 *   link / insert_nt / update_nt  → apply to person_nt + person_wiki
 *   wiki_only / ambiguous         → nt_wiki title link only
 *   rows with fief_corrected/pn_corrected in review CSV → nt_wiki (kept)
 *
 * Usage:
 *   node scripts/apply-wiki-review.mjs
 *   node scripts/apply-wiki-review.mjs --review data/wiki-norbert-review.csv
 */
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import {
  buildApplyPlan,
  mergeCorrections,
  planToSql,
} from '../src/wikiNobleTitles/applyWikiReview.mjs';
import {
  DEFAULT_NORBERT_SQL,
  loadNorbertMatchData,
} from '../src/wikiNobleTitles/matchWikiNorbert.mjs';

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
const reviewCsv = path.resolve(
  __dirname,
  '../data',
  arg('--review', 'wiki-norbert-review.csv'),
);
const outSql = path.resolve(__dirname, '../data', arg('--out', 'wiki-apply.sql'));
const outSummary = path.resolve(__dirname, '../data', arg('--summary', 'wiki-apply-summary.txt'));
const sqlPath = path.resolve(arg('--sql', DEFAULT_NORBERT_SQL));
const schemaPath = path.resolve(__dirname, '../../../../norbert/SQL/create_wiki_nt_link.sql');

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
  console.log(`loaded ${Object.keys(correctionsByReviewId).length} manual corrections from ${reviewCsv}`);
}

console.log(`loading dynasty map from ${sqlPath}...`);
const norbert = await loadNorbertMatchData(sqlPath);

/** @type {Record<string, number>} */
const counts = {};
/** @type {string[]} */
const statements = [];

if (fs.existsSync(schemaPath)) {
  statements.push(fs.readFileSync(schemaPath, 'utf8').trim(), '');
}

for (const row of rows) {
  const merged = mergeCorrections(row, correctionsByReviewId);
  const plan = buildApplyPlan(merged, norbert.dynIdByName);
  counts[plan.action] = (counts[plan.action] ?? 0) + 1;
  statements.push(...planToSql(plan));
}

const body = statements.join('\n');
fs.writeFileSync(outSql, body ? `${body}\n` : '');
fs.writeFileSync(
  outSummary,
  [
    `wiki apply summary`,
    `source: ${ndjsonPath}`,
    `manual corrections: ${reviewCsv}`,
    `generated: ${new Date().toISOString()}`,
    '',
    'actions:',
    ...Object.entries(counts)
      .sort((a, b) => b[1] - a[1])
      .map(([k, v]) => `  ${k}: ${v}`),
    '',
    `SQL statements: ${statements.filter((s) => s.startsWith('INSERT') || s.startsWith('UPDATE')).length}`,
    `output: ${outSql}`,
    '',
    'Apply:',
    `  mysql norbert < ${outSql}`,
  ].join('\n'),
);

console.log(`wrote ${outSql}`);
console.log('actions:', counts);
console.log(`\nApply when ready:\n  mysql norbert < ${outSql}`);
