import { buildMatchKey, buildNtSearchStrings } from './compileWikiNtAsset.mjs';

/**
 * Norbert's `person_nt` table is the canonical noble-title record — it must
 * appear in the compiled asset even when no zh.wikipedia noble-title list
 * page happens to cover it (most emperors/founders, e.g. Liu Bei's 漢昭烈帝,
 * never will: the wiki crawl only walks princely/ducal fief list pages).
 * This builds those records directly from `person_nt`, independent of the
 * Wikipedia-matched `norbert-wikipedia` rows compiled elsewhere in this file.
 *
 * @param {{
 *   ntRows: Array<{ ind: number, personId: number, dyn: string|null, fief: string|null, pn: string|null, nt: string|null, dynId: number|null, startYear: number|null, endYear: number|null }>,
 *   personNameById: Map<string, string>,
 *   personDisplayNameById?: Map<string, string>,
 *   coveredKeys: Set<string>,
 *   startIndex: number,
 * }} params
 */
export function buildCanonicalNtRecords({ ntRows, personNameById, personDisplayNameById = new Map(), coveredKeys, startIndex }) {
  /** @type {Record<string, unknown>[]} */
  const records = [];
  let index = startIndex;

  for (const row of ntRows) {
    const key = `${row.personId}:${row.ind}`;
    if (coveredKeys.has(key)) continue;
    if (!row.nt) continue;

    const person = personNameById.get(String(row.personId)) ?? null;
    const displayName = personDisplayNameById.get(String(row.personId)) ?? person;
    let roleName = row.nt;
    let posthumousName = row.pn;
    if (!row.fief && !posthumousName && displayName && row.nt === '后' && displayName.endsWith('皇后')) {
      roleName = '皇后';
      posthumousName = displayName.slice(0, -roleName.length) || null;
    }
    const searchStrings = buildNtSearchStrings({
      dyn: row.dyn,
      fief: row.fief,
      pn: posthumousName,
      nt: roleName,
      person,
    });
    if (searchStrings.length === 0) continue;

    index += 1;
    const id = `wnt-${String(index).padStart(4, '0')}`;
    const wrapperSearchStrings = person ? searchStrings.filter((s) => s.endsWith(person)) : [];
    const titleSearchStrings = person
      ? searchStrings.filter((s) => !s.endsWith(person))
      : searchStrings;

    const personId = String(row.personId);
    const wrapper = person
      ? {
          personId,
          titleRowId: id,
          components: {
            fief: row.fief,
            roleName,
            posthumousName: posthumousName ?? undefined,
            persName: person,
          },
        }
      : undefined;

    records.push({
      id,
      source: 'norbert-direct',
      authorityId: `wiki-nt:${String(index).padStart(4, '0')}`,
      kind: 'person',
      primaryName: person || [row.fief, posthumousName, roleName].filter(Boolean).join(''),
      action: 'norbert_canonical',
      matchKey: buildMatchKey({ dyn: row.dyn, fief: row.fief, pn: posthumousName, nt: roleName, person }),
      searchStrings,
      names: person ? [{ text: person, type: 'wrapper-person' }] : [],
      wiki: null,
      norbert: {
        personId,
        ntInd: String(row.ind),
        canName: person,
        dyn: row.dyn,
        fief: row.fief,
        pn: posthumousName,
        nt: roleName,
        dynId: row.dynId ?? null,
        startYear: row.startYear ?? null,
        endYear: row.endYear ?? null,
      },
      proposedNt: null,
      reviewerNotes:
        'Exported directly from Norbert person_nt; no zh.wikipedia noble-title list page match was attempted for this record.',
      metadata: {
        isNobleTitle: true,
        teiTag: wrapper ? undefined : 'nobleTitle',
        sourceRef: null,
        dynasty: row.dyn ?? undefined,
        crosswalk: { norbert: personId },
        wrapper,
        wrapperSearchStrings,
        titleSearchStrings,
        nobleTitle: {
          fief: row.fief,
          roleName,
          posthumousName: posthumousName ?? undefined,
        },
      },
    });
  }

  return records;
}

/** Builds the (personId, ind) key set already covered by wiki-matched norbert rows. */
export function coveredKeysFromExistingAsset(existingRecords) {
  const covered = new Set();
  for (const record of existingRecords) {
    const norbert = record.norbert;
    if (norbert?.personId && norbert?.ntInd) covered.add(`${norbert.personId}:${norbert.ntInd}`);
  }
  return covered;
}
