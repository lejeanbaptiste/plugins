#!/usr/bin/env node
/**
 * Fetch zh.wikipedia noble-title disambiguation pages and emit NDJSON rows.
 *
 * Usage:
 *   node scripts/fetch-wiki-noble-titles.mjs [--category CAT] [--limit N] [--out PATH]
 *   node scripts/fetch-wiki-noble-titles.mjs --delay-ms 3000 --proxy socks5://127.0.0.1:9050
 *   node scripts/fetch-wiki-noble-titles.mjs --resume
 *   node scripts/fetch-wiki-noble-titles.mjs --fixture src/wikiNobleTitles/fixtures/donghai-wang.wikitext
 */
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { DEFAULT_WIKI_CATEGORY } from '../src/wikiNobleTitles/constants.mjs';
import { parseNobleTitlePage, isNobleTitleDisambigPage } from '../src/wikiNobleTitles/parseWikitext.mjs';
import { fetchCategoryMembers, fetchPagesWikitext } from '../src/wikiNobleTitles/wikiApi.mjs';
import { enrichWikiLinks } from '../src/wikiNobleTitles/enrichWikiLinks.mjs';
import { createWikiClient, resolveDelayMs, resolveProxyUrl } from '../src/wikiNobleTitles/wikiClient.mjs';

const __dirname = path.dirname(fileURLToPath(import.meta.url));

function arg(name, fallback = null) {
  const index = process.argv.indexOf(name);
  return index >= 0 && process.argv[index + 1] ? process.argv[index + 1] : fallback;
}

function hasFlag(name) {
  return process.argv.includes(name);
}

const fixturePath = arg('--fixture');
const category = arg('--category', DEFAULT_WIKI_CATEGORY);
const limit = arg('--limit') ? Number(arg('--limit')) : undefined;
const delayMs = resolveDelayMs(arg('--delay-ms'), 2000);
const proxy = resolveProxyUrl(arg('--proxy'));
const batchSize = arg('--batch-size') ? Math.max(1, Number(arg('--batch-size'))) : 1;
const resume = hasFlag('--resume');
const outPath = path.resolve(
  __dirname,
  '../data',
  arg('--out', 'wiki-noble-titles.ndjson'),
);
const checkpointPath = path.resolve(
  __dirname,
  '../data',
  arg('--checkpoint', '.wiki-noble-titles.checkpoint.json'),
);

/** @param {import('../src/wikiNobleTitles/parseWikitext.mjs').WikiNobleTitleRow[]} rows */
function writeNdjson(rows) {
  fs.mkdirSync(path.dirname(outPath), { recursive: true });
  const body = rows.map((row) => JSON.stringify({ source: 'zh.wikipedia', ...row })).join('\n');
  fs.writeFileSync(outPath, body ? `${body}\n` : '');
}

/** @returns {{ category: string, fetchedTitles: string[], rows: import('../src/wikiNobleTitles/parseWikitext.mjs').WikiNobleTitleRow[] } | null} */
function readCheckpoint() {
  if (!fs.existsSync(checkpointPath)) return null;
  try {
    return JSON.parse(fs.readFileSync(checkpointPath, 'utf8'));
  } catch {
    return null;
  }
}

/** @param {{ category: string, fetchedTitles: string[], rows: unknown[] }} checkpoint */
function writeCheckpoint(checkpoint) {
  fs.mkdirSync(path.dirname(checkpointPath), { recursive: true });
  fs.writeFileSync(checkpointPath, `${JSON.stringify(checkpoint, null, 2)}\n`);
}

/**
 * @param {string} title
 * @param {{ wikitext: string, pageId: number, url: string, wikidataId: string|null }|null|undefined} pageMeta
 * @param {import('../src/wikiNobleTitles/parseWikitext.mjs').WikiNobleTitleRow[]} rows
 */
function ingestPage(title, pageMeta, rows) {
  const wikitext = pageMeta?.wikitext;
  if (!wikitext || wikitext.startsWith('#REDIRECT')) return;
  if (!isNobleTitleDisambigPage(wikitext)) {
    console.warn(`skip (not disambig): ${title}`);
    return;
  }
  for (const row of parseNobleTitlePage(wikitext, title)) {
    rows.push({
      ...row,
      sourcePageId: pageMeta?.pageId ?? null,
      sourcePageUrl: pageMeta?.url ?? null,
      sourceWikidataId: pageMeta?.wikidataId ?? null,
    });
  }
}

async function main() {
  /** @type {import('../src/wikiNobleTitles/parseWikitext.mjs').WikiNobleTitleRow[]} */
  let rows = [];
  /** @type {Set<string>} */
  let fetchedTitles = new Set();

  if (fixturePath) {
    const resolved = path.resolve(process.cwd(), fixturePath);
    const wikitext = fs.readFileSync(resolved, 'utf8');
    const title = arg('--title', path.basename(resolved, '.wikitext'));
    rows = parseNobleTitlePage(wikitext, title);
    console.log(`parsed fixture ${resolved}: ${rows.length} holder rows`);
  } else {
    const checkpoint = resume ? readCheckpoint() : null;
    if (checkpoint?.category && checkpoint.category !== category) {
      console.warn(`checkpoint category ${checkpoint.category} differs from ${category}; starting fresh`);
    } else if (checkpoint) {
      fetchedTitles = new Set(checkpoint.fetchedTitles ?? []);
      rows = checkpoint.rows ?? [];
      console.log(`resuming: ${fetchedTitles.size} pages already fetched`);
    }

    console.log(
      `fetching ${category}${limit ? ` (limit ${limit})` : ''} ` +
        `[delay ${delayMs}ms, batch ${batchSize}${proxy ? `, proxy ${proxy}` : ''}]...`,
    );

    const client = createWikiClient({
      delayMs,
      proxy: proxy ?? undefined,
      log: (message) => console.warn(message),
    });

    const members = await fetchCategoryMembers(client, category, { limit });
    const titles = members.map((member) => member.title);
    const pending = titles.filter((title) => !fetchedTitles.has(title));
    console.log(`${titles.length} category members, ${pending.length} pages to fetch`);

    let done = fetchedTitles.size;
    for (let i = 0; i < pending.length; i += batchSize) {
      const batch = pending.slice(i, i + batchSize);
      const wikitextByTitle = await fetchPagesWikitext(client, batch, { batchSize });

      for (const title of batch) {
        const pageMeta = wikitextByTitle.get(title) ?? null;
        ingestPage(title, pageMeta, rows);
        fetchedTitles.add(title);
        done += 1;
        writeCheckpoint({ category, fetchedTitles: [...fetchedTitles], rows });
        process.stdout.write(`\rfetched ${done}/${titles.length}: ${title}`.padEnd(80));
      }
    }
    process.stdout.write('\n');

    const missing = titles.filter((title) => !fetchedTitles.has(title));
    if (missing.length) {
      console.warn(`warning: ${missing.length} pages not fetched`);
    }
    console.log(`parsed ${titles.length} pages → ${rows.length} holder rows`);

    console.log('resolving person page ids and wikidata q-ids...');
    rows = await enrichWikiLinks(rows, client, (msg) => console.log(msg));
  }

  writeNdjson(rows);
  const reviewCount = rows.filter((row) => row.needsReview).length;
  console.log(`wrote ${outPath}`);
  console.log(`needsReview: ${reviewCount}/${rows.length}`);

  if (hasFlag('--print-sample')) {
    console.log(JSON.stringify(rows.slice(0, 3), null, 2));
  }
}

main().catch((error) => {
  console.error(error);
  console.error('Tip: retry with --resume, increase --delay-ms, or route via Tor: --proxy socks5://127.0.0.1:9050');
  process.exit(1);
});
