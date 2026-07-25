/** @param {unknown} value */
export function sqlString(value) {
  if (value == null || value === '') return 'NULL';
  return `'${String(value).replace(/\\/g, '\\\\').replace(/'/g, "''")}'`;
}

/** @param {unknown} value */
export function sqlInt(value) {
  if (value == null || value === '') return 'NULL';
  const n = Number(value);
  return Number.isFinite(n) ? String(Math.trunc(n)) : 'NULL';
}

/**
 * @param {Record<string, unknown>} row
 * @param {Record<string, Record<string, string>>} correctionsByReviewId
 */
export function mergeCorrections(row, correctionsByReviewId) {
  const reviewId = String(row.review_id ?? row.reviewId ?? '');
  const patch = correctionsByReviewId[reviewId];
  if (!patch) return row;
  return {
    ...row,
    fief_corrected: patch.fief_corrected || row.fief_corrected,
    pn_corrected: patch.pn_corrected || row.pn_corrected,
    reviewer_notes: patch.reviewer_notes || row.reviewer_notes,
  };
}

/**
 * @param {Record<string, unknown>} row
 */
export function effectiveFief(row) {
  return row.fief_corrected || row.fief || row.wiki_fief || null;
}

/**
 * @param {Record<string, unknown>} row
 */
export function effectivePn(row) {
  return row.pn_corrected || row.pn || row.wiki_pn || null;
}

/**
 * @param {Record<string, unknown>} row
 */
export function resolveApplyAction(row) {
  const manual = String(row.action ?? '').trim();
  if (manual && manual !== 'skip') return manual;

  const suggested = String(row.suggestedAction ?? row.suggested_action ?? '').trim();
  if (['link', 'insert_nt', 'update_nt'].includes(suggested)) return suggested;

  const status = String(row.matchStatus ?? row.match_status ?? '');
  if (status === 'wiki_only' || status === 'ambiguous') return 'link_title';

  if (row.fief_corrected || row.pn_corrected) return 'link_title';

  return 'skip';
}

/**
 * @param {Record<string, unknown>} row
 * @param {Map<string, number>} dynIdByName
 */
export function resolveDyn(row, dynIdByName) {
  const norbertDynId = row.norbert?.dyn_id ?? row.norbert_dyn_id;
  if (norbertDynId) {
    return {
      dynId: Number(norbertDynId),
      dyn: row.norbert?.dyn ?? row.norbert_dyn ?? null,
    };
  }
  const candidates = String(row.dynCandidates ?? row.wiki_dyn_candidates ?? '')
    .split('|')
    .map((s) => s.trim())
    .filter(Boolean);
  for (const name of candidates) {
    const dynId = dynIdByName.get(name);
    if (dynId) return { dynId, dyn: name };
  }
  return { dynId: null, dyn: candidates[0] ?? null };
}

/**
 * @param {Record<string, unknown>} row
 * @param {Map<string, number>} dynIdByName
 */
export function buildApplyPlan(row, dynIdByName) {
  const action = resolveApplyAction(row);
  const fief = effectiveFief(row);
  const pn = effectivePn(row);
  const nt = row.nt ?? row.wiki_nt ?? null;
  const personId = row.norbert?.person_id ?? row.norbert_person_id ?? null;
  const ntInd = row.norbert?.ind ?? row.norbert_nt_ind ?? null;
  const { dynId, dyn } = resolveDyn(row, dynIdByName);

  return {
    action,
    fief,
    pn,
    nt,
    dyn,
    dynId,
    personId: personId ? Number(personId) : null,
    ntInd: ntInd ? Number(ntInd) : null,
    startYear: row.startYear ?? row.wiki_startYear ?? null,
    endYear: row.endYear ?? row.wiki_endYear ?? null,
    wikidataId: row.wikidataId ?? null,
    wikiPersonUrl: row.wikiPersonUrl ?? null,
    sourcePage: row.sourcePage ?? row.wiki_sourcePage ?? null,
    sourcePageId: row.sourcePageId ?? null,
    sourceWikidataId: row.sourceWikidataId ?? null,
    personBare: row.personBare ?? row.wiki_personBare ?? row.person ?? null,
  };
}

/**
 * @param {ReturnType<buildApplyPlan>} plan
 * @param {string} createdBy
 */
export function planToSql(plan, createdBy = 'wiki-import') {
  /** @type {string[]} */
  const statements = [];

  if (plan.action === 'skip') return statements;

  if (plan.action === 'insert_nt') {
    if (!plan.personId) return statements;
    statements.push(
      `INSERT INTO person_nt (person_id, dyn, fief, pn, nt, start_year, end_year, dyn_id, created_by) VALUES (${sqlInt(plan.personId)}, ${sqlString(plan.dyn)}, ${sqlString(plan.fief)}, ${sqlString(plan.pn)}, ${sqlString(plan.nt)}, ${sqlInt(plan.startYear)}, ${sqlInt(plan.endYear)}, ${sqlInt(plan.dynId)}, ${sqlString(createdBy)});`,
    );
    statements.push(
      `INSERT INTO person_wiki (person_id, person_nt_ind, wikidata_id, wiki_url, wiki_source_page, created_by) VALUES (${sqlInt(plan.personId)}, LAST_INSERT_ID(), ${sqlString(plan.wikidataId)}, ${sqlString(plan.wikiPersonUrl)}, ${sqlString(plan.sourcePage)}, ${sqlString(createdBy)});`,
    );
    return statements;
  }

  if (plan.action === 'update_nt') {
    if (!plan.ntInd) return statements;
    /** @type {string[]} */
    const sets = [`modified_by = ${sqlString(createdBy)}`, 'mod_date = NOW()'];
    if (plan.pn) sets.push(`pn = COALESCE(NULLIF(pn, ''), ${sqlString(plan.pn)})`);
    if (plan.startYear != null) sets.push(`start_year = COALESCE(start_year, ${sqlInt(plan.startYear)})`);
    if (plan.endYear != null) sets.push(`end_year = COALESCE(end_year, ${sqlInt(plan.endYear)})`);
    statements.push(`UPDATE person_nt SET ${sets.join(', ')} WHERE ind = ${sqlInt(plan.ntInd)};`);
    if (plan.personId) {
      statements.push(
        `INSERT INTO person_wiki (person_id, person_nt_ind, wikidata_id, wiki_url, wiki_source_page, created_by) VALUES (${sqlInt(plan.personId)}, ${sqlInt(plan.ntInd)}, ${sqlString(plan.wikidataId)}, ${sqlString(plan.wikiPersonUrl)}, ${sqlString(plan.sourcePage)}, ${sqlString(createdBy)});`,
      );
    }
    return statements;
  }

  if (plan.action === 'link') {
    if (!plan.personId) return statements;
    statements.push(
      `INSERT INTO person_wiki (person_id, person_nt_ind, wikidata_id, wiki_url, wiki_source_page, created_by) VALUES (${sqlInt(plan.personId)}, ${sqlInt(plan.ntInd)}, ${sqlString(plan.wikidataId)}, ${sqlString(plan.wikiPersonUrl)}, ${sqlString(plan.sourcePage)}, ${sqlString(createdBy)});`,
    );
    return statements;
  }

  if (plan.action === 'link_title') {
    statements.push(
      `INSERT INTO nt_wiki (dyn, fief, pn, nt, start_year, end_year, wiki_source_page, wiki_source_page_id, wiki_source_wikidata, wiki_person_wikidata, wiki_person_url, wiki_person_name, link_status, created_by) VALUES (${sqlString(plan.dyn)}, ${sqlString(plan.fief)}, ${sqlString(plan.pn)}, ${sqlString(plan.nt)}, ${sqlInt(plan.startYear)}, ${sqlInt(plan.endYear)}, ${sqlString(plan.sourcePage)}, ${sqlInt(plan.sourcePageId)}, ${sqlString(plan.sourceWikidataId)}, ${sqlString(plan.wikidataId)}, ${sqlString(plan.wikiPersonUrl)}, ${sqlString(plan.personBare)}, 'title_only', ${sqlString(createdBy)});`,
    );
    return statements;
  }

  return statements;
}
