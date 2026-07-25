import {
  buildApplyPlan,
  effectiveFief,
  effectivePn,
  mergeCorrections,
  resolveApplyAction,
} from './applyWikiReview.mjs';

export { mergeCorrections, resolveApplyAction, buildApplyPlan };

/**
 * @param {{ dyn?: string|null, fief?: string|null, pn?: string|null, nt?: string|null, person?: string|null }} parts
 */
export function buildNtSearchStrings(parts) {
  const { dyn, fief, pn, nt, person } = parts;
  /** @type {string[]} */
  const strings = [];
  const add = (s) => {
    if (s && !strings.includes(s)) strings.push(s);
  };

  if (fief && pn && nt) add(`${fief}${pn}${nt}`);
  if (fief && nt) add(`${fief}${nt}`);
  if (fief && pn && nt && person) add(`${fief}${pn}${nt}${person}`);
  if (fief && nt && person) add(`${fief}${nt}${person}`);
  if (dyn && fief && pn && nt) add(`${dyn}${fief}${pn}${nt}`);
  if (dyn && fief && pn && nt && person) add(`${dyn}${fief}${pn}${nt}${person}`);

  return strings;
}

/**
 * @param {{ dyn?: string|null, fief?: string|null, pn?: string|null, nt?: string|null, person?: string|null }} parts
 */
export function buildMatchKey(parts) {
  return [parts.dyn ?? '', parts.fief ?? '', parts.pn ?? '', parts.nt ?? '', parts.person ?? ''].join('|');
}

/**
 * @param {ReturnType<buildApplyPlan>} plan
 * @param {Record<string, unknown>} row
 * @param {number} index
 */
export function planToAssetRecord(plan, row, index) {
  if (plan.action === 'skip') return null;

  const action = plan.action === 'link_title' ? 'title_only' : plan.action;
  const wiki = {
    sourcePage: plan.sourcePage,
    sourcePageId: plan.sourcePageId ?? null,
    sourcePageUrl: row.sourcePageUrl ?? null,
    sourceWikidataId: plan.sourceWikidataId ?? null,
    dynastySection: row.dynastySection ?? row.wiki_dynastySection ?? null,
    dyn: plan.dyn,
    fief: plan.fief,
    pn: plan.pn,
    nt: plan.nt,
    person: plan.personBare,
    startYear: plan.startYear ?? null,
    endYear: plan.endYear ?? null,
    wikidataId: plan.wikidataId ?? null,
    wikiPersonUrl: plan.wikiPersonUrl ?? null,
  };

  const norbertPersonId = plan.personId ? String(plan.personId) : null;
  const norbertNtInd = plan.ntInd ? String(plan.ntInd) : null;
  const canName = row.norbert?.can_name ?? row.norbert_can_name ?? plan.personBare ?? null;

  /** @type {Record<string, unknown>|null} */
  let norbert = null;
  if (norbertPersonId || norbertNtInd) {
    norbert = {
      personId: norbertPersonId,
      ntInd: norbertNtInd,
      canName,
      dyn: row.norbert?.dyn ?? row.norbert_dyn ?? plan.dyn ?? null,
      fief: row.norbert?.fief ?? row.norbert_fief ?? null,
      pn: row.norbert?.pn ?? row.norbert_pn ?? null,
      nt: row.norbert?.nt ?? row.norbert_nt ?? null,
      dynId: row.norbert?.dyn_id ?? row.norbert_dyn_id ?? plan.dynId ?? null,
      startYear: row.norbert?.start_year ?? row.norbert_start_year ?? null,
      endYear: row.norbert?.end_year ?? row.norbert_end_year ?? null,
    };
  }

  /** @type {Record<string, unknown>|null} */
  let proposedNt = null;
  if (action === 'insert_nt' || action === 'update_nt') {
    proposedNt = {
      dyn: plan.dyn,
      fief: plan.fief,
      pn: plan.pn,
      nt: plan.nt,
      dynId: plan.dynId ?? null,
      startYear: plan.startYear ?? null,
      endYear: plan.endYear ?? null,
    };
  }

  const matchKey = buildMatchKey({
    dyn: plan.dyn,
    fief: plan.fief,
    pn: plan.pn,
    nt: plan.nt,
    person: plan.personBare,
  });

  return {
    id: `wnt-${String(index + 1).padStart(4, '0')}`,
    action,
    matchKey,
    searchStrings: buildNtSearchStrings(wiki),
    wiki,
    norbert,
    proposedNt,
    reviewerNotes: row.reviewer_notes ?? null,
  };
}

/**
 * @param {Record<string, unknown>[]} rows
 * @param {Record<string, Record<string, string>>} correctionsByReviewId
 * @param {Map<string, number>} [dynIdByName]
 */
export function compileWikiNtAsset(rows, correctionsByReviewId, dynIdByName = new Map()) {
  /** @type {Record<string, unknown>[]} */
  const records = [];
  /** @type {Record<string, number>} */
  const actionCounts = {};

  for (const [index, row] of rows.entries()) {
    const merged = mergeCorrections(row, correctionsByReviewId);
    const plan = buildApplyPlan(merged, dynIdByName);
    const record = planToAssetRecord(plan, merged, records.length);
    if (!record) continue;
    records.push(record);
    const key = String(record.action);
    actionCounts[key] = (actionCounts[key] ?? 0) + 1;
  }

  return {
    id: 'norbert-wiki-nt',
    source: 'zh.wikipedia',
    assetVersion: '1',
    compiledAt: new Date().toISOString(),
    license: 'CC-BY-SA-4.0',
    attribution: 'Noble title holders from zh.wikipedia; Norbert person ids/names curated locally.',
    recordCount: records.length,
    actionCounts,
    records,
  };
}
