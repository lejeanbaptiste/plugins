import dynastySectionMap from './dynastySectionMap.json' with { type: 'json' };
import { splitPageTitle } from './parseWikitext.mjs';

/** Sections that are not dynasty lists — skip for NT import. */
export const SKIP_DYNASTY_SECTIONS = new Set([
  '参考资料',
  '參考資料',
  '参见',
  '參見',
  '相关条目',
  '相關條目',
  '諡號',
  '谥号',
  '封號',
  '封号',
  '封爵',
  '庙号',
  '廟號',
  '爵位',
  '头衔',
  '頭銜',
]);

/** @type {((text: string) => string) | null} */
let toTraditional = null;

async function ensureConverter() {
  if (toTraditional) return;
  try {
    const { Converter } = await import('opencc-js');
    toTraditional = Converter({ from: 'cn', to: 'tw' });
  } catch {
    toTraditional = (text) => text;
  }
}

/** @param {string|null|undefined} text */
export async function trad(text) {
  if (text == null || text === '') return text ?? null;
  await ensureConverter();
  return toTraditional(text);
}

/** @param {string|null|undefined} person */
export function stripDisambig(person) {
  if (!person) return null;
  const match = person.match(/^([^()（）]+?)(?:\s*[(（][^)）]+[)）])?$/);
  return (match?.[1] ?? person).trim() || null;
}

/**
 * @param {string|null|undefined} section
 */
export function mapDynastySection(section) {
  if (!section || SKIP_DYNASTY_SECTIONS.has(section)) return [];
  const mapped = dynastySectionMap[section];
  if (mapped) return mapped;
  return [section];
}

/**
 * @param {Record<string, unknown>} row
 */
export async function normalizeWikiRow(row) {
  const sourcePage = await trad(row.sourcePage);
  const pageParts = splitPageTitle(sourcePage ?? '');
  const dynastySection = await trad(row.dynastySection);
  const dynCandidates = mapDynastySection(dynastySection);

  let fief = await trad(row.fief ?? pageParts.fief);
  let nt = await trad(row.nt ?? pageParts.nt);
  let pn = await trad(row.pn);
  const person = await trad(row.person);
  const personBare = stripDisambig(person);
  const wikiPersonTitle = await trad(row.wikiPersonTitle);

  /** @type {string[]} */
  const fillNotes = [];
  if (!row.fief && pageParts.fief) fillNotes.push('fief←sourcePage');
  if (!row.nt && pageParts.nt) fillNotes.push('nt←sourcePage');
  if (!row.pn && row.rawLine && /[\u4e00-\u9fff]{2,}王/.test(String(row.rawLine))) {
    // pn already parsed when present in raw line
  }

  const skipReason = SKIP_DYNASTY_SECTIONS.has(dynastySection ?? '')
    ? `section:${dynastySection}`
    : null;

  return {
    ...row,
    sourcePage,
    dynastySection,
    dynCandidates,
    fief,
    pn,
    nt,
    person,
    personBare,
    wikiPersonTitle,
    startYear: row.startYear ?? null,
    endYear: row.endYear ?? null,
    fillNotes: fillNotes.join('; '),
    skipReason,
    cleanKey: [sourcePage, dynCandidates[0] ?? '', fief ?? '', pn ?? '', nt ?? '', personBare ?? '', row.startYear ?? ''].join('|'),
  };
}

/**
 * @param {Record<string, unknown>[]} rows
 */
export async function normalizeWikiRows(rows) {
  /** @type {Record<string, unknown>[]} */
  const cleaned = [];
  const seen = new Set();

  for (const row of rows) {
    const normalized = await normalizeWikiRow(row);
    if (normalized.skipReason) {
      normalized.reviewStatus = 'skip_section';
      normalized.suggestedAction = 'skip';
      cleaned.push(normalized);
      continue;
    }
    if (seen.has(normalized.cleanKey)) {
      normalized.reviewStatus = 'duplicate';
      normalized.suggestedAction = 'skip';
      cleaned.push(normalized);
      continue;
    }
    seen.add(normalized.cleanKey);
    normalized.reviewStatus = 'ready';
    cleaned.push(normalized);
  }

  return cleaned;
}

/** @param {string|null|undefined} text */
export function normKey(text) {
  if (text == null) return '';
  return String(text).normalize('NFC').trim();
}
