import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { loadNorbertTables } from '../../../../../authoritypacks/norbert/parseSqlDump.mjs';
import { normKey } from './normalizeWikiNt.mjs';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
export const DEFAULT_NORBERT_SQL = path.resolve(
  __dirname,
  '../../../../../authoritypacks/norbert_secret/norbert_humanum_2026-07-25-1938.sql',
);

/** person_nt column indices */
export const NT_COL = {
  ind: 0,
  person_id: 1,
  dyn: 2,
  fief: 3,
  pn: 4,
  pn_abr: 5,
  nt: 6,
  tn: 7,
  start_year: 10,
  end_year: 11,
  dyn_id: 12,
};

/**
 * @param {string} sqlPath
 */
export async function loadNorbertMatchData(sqlPath = DEFAULT_NORBERT_SQL) {
  const tables = await loadNorbertTables(sqlPath, ['person', 'person_nt', 'date_dynasties']);
  /** @type {Map<number, string>} */
  const personById = new Map();
  for (const row of tables.person) {
    personById.set(row[0], row[1]);
  }

  /** @type {Map<string, number>} */
  const dynIdByName = new Map();
  for (const row of tables.date_dynasties) {
    if (row[1]) dynIdByName.set(normKey(row[1]), row[0]);
  }

  /** @type {Array<Record<string, unknown>>} */
  const ntRows = [];
  for (const row of tables.person_nt) {
    const personId = row[NT_COL.person_id];
    ntRows.push({
      ind: row[NT_COL.ind],
      person_id: personId,
      can_name: personById.get(personId) ?? null,
      dyn: row[NT_COL.dyn],
      fief: row[NT_COL.fief],
      pn: row[NT_COL.pn],
      pn_abr: row[NT_COL.pn_abr],
      nt: row[NT_COL.nt],
      tn: row[NT_COL.tn],
      start_year: row[NT_COL.start_year],
      end_year: row[NT_COL.end_year],
      dyn_id: row[NT_COL.dyn_id],
    });
  }

  /** @type {Map<string, Record<string, unknown>[]>} */
  const ntByComposite = new Map();
  /** @type {Map<string, Record<string, unknown>[]>} */
  const ntByShort = new Map();
  /** @type {Map<string, Record<string, unknown>[]>} */
  const personsByName = new Map();

  for (const nt of ntRows) {
    const fullKey = [normKey(nt.dyn), normKey(nt.fief), normKey(nt.pn), normKey(nt.nt), normKey(nt.can_name)].join('|');
    const shortKey = [normKey(nt.dyn), normKey(nt.fief), normKey(nt.nt), normKey(nt.can_name)].join('|');
    if (!ntByComposite.has(fullKey)) ntByComposite.set(fullKey, []);
    ntByComposite.get(fullKey).push(nt);
    if (!ntByShort.has(shortKey)) ntByShort.set(shortKey, []);
    ntByShort.get(shortKey).push(nt);

    const nameKey = normKey(nt.can_name);
    if (nameKey) {
      if (!personsByName.has(nameKey)) personsByName.set(nameKey, []);
      personsByName.get(nameKey).push(nt);
    }
  }

  return { ntRows, ntByComposite, ntByShort, personsByName, dynIdByName, personById };
}

/**
 * @param {Record<string, unknown>} wiki
 * @param {Awaited<ReturnType<loadNorbertMatchData>>} norbert
 */
export function matchWikiRow(wiki, norbert) {
  if (wiki.skipReason || wiki.reviewStatus === 'duplicate') {
    return {
      matchStatus: wiki.reviewStatus ?? 'skip',
      matchTier: null,
      suggestedAction: 'skip',
      norbert: null,
      matchNote: wiki.skipReason ?? 'duplicate',
    };
  }

  const personBare = normKey(wiki.personBare);
  const dynCandidates = /** @type {string[]} */ (wiki.dynCandidates ?? ['']);
  /** @type {Record<string, unknown>[]} */
  let matches = [];

  for (const dyn of dynCandidates) {
    const fullKey = [normKey(dyn), normKey(wiki.fief), normKey(wiki.pn), normKey(wiki.nt), personBare].join('|');
    matches.push(...(norbert.ntByComposite.get(fullKey) ?? []));
  }

  let matchTier = 'B';
  if (matches.length === 0) {
    for (const dyn of dynCandidates) {
      const shortKey = [normKey(dyn), normKey(wiki.fief), normKey(wiki.nt), personBare].join('|');
      matches.push(...(norbert.ntByShort.get(shortKey) ?? []));
    }
    matchTier = 'C';
  }

  if (matches.length === 0 && personBare) {
    matches = norbert.personsByName.get(personBare) ?? [];
    matchTier = 'D';
  }

  if (matches.length === 0) {
    const personId = [...norbert.personById.entries()].find(([, name]) => normKey(name) === personBare)?.[0];
    if (personId) {
      return {
        matchStatus: 'person_only',
        matchTier: 'E',
        suggestedAction: 'insert_nt',
        norbert: { person_id: personId, can_name: norbert.personById.get(personId) },
        matchNote: 'person in Norbert, no matching NT row',
      };
    }
    return {
      matchStatus: 'wiki_only',
      matchTier: null,
      suggestedAction: 'review',
      norbert: null,
      matchNote: 'no Norbert match',
    };
  }

  if (matches.length > 1) {
    return {
      matchStatus: 'ambiguous',
      matchTier,
      suggestedAction: 'review',
      norbert: matches[0],
      matchNote: `${matches.length} Norbert candidates`,
      matchCount: matches.length,
    };
  }

  const nt = matches[0];
  const missingPn = !nt.pn && wiki.pn;
  const missingDates = (!nt.start_year && wiki.startYear) || (!nt.end_year && wiki.endYear);
  let suggestedAction = 'link';
  if (missingPn || missingDates) suggestedAction = 'update_nt';

  return {
    matchStatus: 'matched',
    matchTier,
    suggestedAction,
    norbert: nt,
    matchNote: missingPn || missingDates ? 'Norbert row incomplete' : 'full NT match',
  };
}

/**
 * @param {Record<string, unknown>[]} wikiRows
 * @param {Awaited<ReturnType<loadNorbertMatchData>>} norbert
 */
export function matchWikiRows(wikiRows, norbert) {
  return wikiRows.map((wiki) => {
    const match = matchWikiRow(wiki, norbert);
    return { ...wiki, ...match };
  });
}
