import { NT_SUFFIXES, SKIP_SECTIONS } from './constants.mjs';

/**
 * @typedef {Object} WikiNobleTitleRow
 * @property {string} sourcePage
 * @property {string|null} dynastySection
 * @property {string} rawLine
 * @property {string|null} fief
 * @property {string|null} pn
 * @property {string|null} nt
 * @property {string|null} person
 * @property {string|null} wikiPersonTitle
 * @property {number|null} startYear
 * @property {number|null} endYear
 * @property {'high'|'medium'|'low'} confidence
 * @property {boolean} needsReview
 */

/**
 * Split a page title like 東海王 into fief + noble rank.
 * @param {string} title
 */
export function splitPageTitle(title) {
  const normalized = title.trim();
  for (const nt of NT_SUFFIXES) {
    if (normalized.endsWith(nt) && normalized.length > nt.length) {
      return {
        pageTitle: normalized,
        fief: normalized.slice(0, -nt.length),
        nt,
      };
    }
  }
  return { pageTitle: normalized, fief: null, nt: null };
}

/**
 * Parse a holder label such as 東海恭王 or 崇德侯.
 * @param {string} label
 * @param {string|null} defaultFief
 * @param {string|null} defaultNt
 */
export function parseTitleLabel(label, defaultFief, defaultNt) {
  const cleaned = label.replace(/\[\[[^\]]+\]\]/g, '').replace(/[，,].*$/, '').trim();
  if (!cleaned) {
    return { fief: defaultFief, pn: null, nt: defaultNt };
  }

  for (const nt of NT_SUFFIXES) {
    if (!cleaned.endsWith(nt)) continue;
    const body = cleaned.slice(0, -nt.length);
    if (defaultFief && body.startsWith(defaultFief) && body.length > defaultFief.length) {
      return {
        fief: defaultFief,
        pn: body.slice(defaultFief.length) || null,
        nt,
      };
    }
    if (defaultFief && body === defaultFief) {
      return { fief: defaultFief, pn: null, nt };
    }
    return { fief: body || defaultFief, pn: null, nt };
  }

  return { fief: defaultFief, pn: null, nt: defaultNt };
}

/** @param {string} text */
export function extractWikiLinks(text) {
  /** @type {{ target: string, display: string }[]} */
  const links = [];
  const re = /\[\[([^|\]#]+)(?:#[^\]|]+)?(?:\|([^\]]+))?\]\]/g;
  let match = re.exec(text);
  while (match) {
    links.push({
      target: match[1].trim(),
      display: (match[2] ?? match[1]).trim(),
    });
    match = re.exec(text);
  }
  return links;
}

/** @param {string} text */
export function parseReignDates(text) {
  const range = text.match(/(\d+|\?)年\s*-\s*(\d+|\?)年/);
  if (range) {
    return {
      startYear: range[1] === '?' ? null : Number(range[1]),
      endYear: range[2] === '?' ? null : Number(range[2]),
    };
  }
  const openEnd = text.match(/(\d+|\?)年\s*-\s*(\d+|\?)年/);
  if (openEnd) {
    return {
      startYear: openEnd[1] === '?' ? null : Number(openEnd[1]),
      endYear: openEnd[2] === '?' ? null : Number(openEnd[2]),
    };
  }
  return { startYear: null, endYear: null };
}

/**
 * @param {string} line
 * @param {string} pageTitle
 * @param {string|null} dynastySection
 * @param {string|null} defaultFief
 * @param {string|null} defaultNt
 * @returns {WikiNobleTitleRow|null}
 */
export function parseHolderLine(line, pageTitle, dynastySection, defaultFief, defaultNt) {
  const trimmed = line.replace(/^\*+\s*/, '').trim();
  if (!trimmed || trimmed.startsWith('第') && trimmed.includes('册封')) return null;
  if (/^第[一二三四五六七八九十\d]+次/.test(trimmed)) return null;

  const links = extractWikiLinks(trimmed);
  const personLink = links.find((link) => !/列表$/.test(link.target)) ?? links[0] ?? null;
  const labelEnd = personLink ? trimmed.indexOf(`[[${personLink.target}`) : trimmed.length;
  const label = labelEnd > 0 ? trimmed.slice(0, labelEnd) : '';
  const parsed = parseTitleLabel(label, defaultFief, defaultNt);
  const dates = parseReignDates(trimmed);

  if (!personLink && !parsed.fief && !parsed.nt) return null;

  const rankChanged = Boolean(defaultNt && parsed.nt && parsed.nt !== defaultNt);
  const fiefChanged = Boolean(defaultFief && parsed.fief && parsed.fief !== defaultFief);
  const hasPerson = Boolean(personLink);
  const hasDates = dates.startYear != null || dates.endYear != null;

  let confidence = 'high';
  if (!hasPerson || rankChanged || fiefChanged) confidence = 'medium';
  if (!hasPerson && !label.trim()) confidence = 'low';

  return {
    sourcePage: pageTitle,
    dynastySection,
    rawLine: trimmed,
    fief: parsed.fief,
    pn: parsed.pn,
    nt: parsed.nt,
    person: personLink?.display ?? null,
    wikiPersonTitle: personLink?.target ?? null,
    startYear: dates.startYear,
    endYear: dates.endYear,
    confidence,
    needsReview: confidence !== 'high' || !hasDates,
  };
}

/**
 * True when wikitext looks like a noble-title holder index (not a biography stub).
 * @param {string} wikitext
 */
export function isNobleTitleDisambigPage(wikitext) {
  return /\{\{disambig/i.test(wikitext) || /\{\{Otheruses/i.test(wikitext);
}

/**
 * Parse a zh.wikipedia noble-title disambiguation page wikitext.
 * @param {string} wikitext
 * @param {string} pageTitle
 * @returns {WikiNobleTitleRow[]}
 */
export function parseNobleTitlePage(wikitext, pageTitle) {
  const { fief: defaultFief, nt: defaultNt } = splitPageTitle(pageTitle);
  /** @type {WikiNobleTitleRow[]} */
  const rows = [];

  const sections = wikitext.split(/^==\s*([^=\n]+?)\s*==\s*$/m);
  if (sections.length === 1) {
    collectLines(wikitext, null, pageTitle, defaultFief, defaultNt, rows);
    return rows;
  }

  for (let i = 1; i < sections.length; i += 2) {
    const header = sections[i].trim();
    const body = sections[i + 1] ?? '';
    if (SKIP_SECTIONS.has(header)) continue;
    collectLines(body, header, pageTitle, defaultFief, defaultNt, rows);
  }

  return rows;
}

/**
 * @param {string} body
 * @param {string|null} dynastySection
 * @param {string} pageTitle
 * @param {string|null} defaultFief
 * @param {string|null} defaultNt
 * @param {WikiNobleTitleRow[]} rows
 */
function collectLines(body, dynastySection, pageTitle, defaultFief, defaultNt, rows) {
  for (const line of body.split('\n')) {
    if (!/^\*+/.test(line)) continue;
    const row = parseHolderLine(line, pageTitle, dynastySection, defaultFief, defaultNt);
    if (row) rows.push(row);
  }
}
