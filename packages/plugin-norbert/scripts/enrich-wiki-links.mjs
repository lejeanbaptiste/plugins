#!/usr/bin/env node
/**
 * Add Wikipedia page IDs, URLs, and Wikidata Q-ids to wiki-noble-titles.ndjson.
 *
 * Usage:
 *   node scripts/enrich-wiki-links.mjs [--in PATH] [--out PATH] [--delay-ms N]
 */
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { enrichWikiLinks } from '../src/wikiNobleTitles/enrichWikiLinks.mjs';
import { createWikiClient, resolveDelayMs, resolveProxyUrl } from '../src/wikiNobleTitles/wikiClient.mjs';

const __dirname = path.dirname(fileURLToPath(import.meta.url));

function arg(name, fallback) {
  const index = process.argv.indexOf(name);
  return index >= 0 && process.argv[index + 1] ? process.argv[index + 1] : fallback;
}

const inPath = path.resolve(__dirname, '../data', arg('--in', 'wiki-noble-titles.ndjson'));
const outPath = path.resolve(__dirname, '../data', arg('--out', 'wiki-noble-titles.ndjson'));
const delayMs = resolveDelayMs(arg('--delay-ms'), 2000);
const proxy = resolveProxyUrl(arg('--proxy'));

const text = fs.readFileSync(inPath, 'utf8').trim();
if (!text) {
  console.error(`empty input: ${inPath}`);
  process.exit(1);
}

const rows = text.split('\n').map((line) => JSON.parse(line));
console.log(`enriching ${rows.length} rows [delay ${delayMs}ms]...`);

const client = createWikiClient({ delayMs, proxy: proxy ?? undefined, log: (msg) => console.warn(msg) });
const enriched = await enrichWikiLinks(rows, client, (msg) => console.log(msg));

const body = enriched.map((row) => JSON.stringify(row)).join('\n');
fs.writeFileSync(outPath, `${body}\n`);
console.log(`wrote ${outPath}`);

const withPersonId = enriched.filter((row) => row.wikiPersonPageId).length;
const withWikidata = enriched.filter((row) => row.wikidataId).length;
console.log(`person page ids: ${withPersonId}/${enriched.length}`);
console.log(`wikidata ids: ${withWikidata}/${enriched.length}`);
