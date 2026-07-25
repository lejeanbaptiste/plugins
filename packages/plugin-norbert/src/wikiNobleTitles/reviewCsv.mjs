/** @param {unknown} value */
export function csvCell(value) {
  if (value == null) return '';
  const text = String(value);
  if (/[",\n\r]/.test(text)) return `"${text.replace(/"/g, '""')}"`;
  return text;
}

export const REVIEW_COLUMNS = [
  'review_id',
  'suggested_action',
  'action',
  'match_status',
  'match_tier',
  'match_note',
  'wiki_sourcePage',
  'wiki_dynastySection',
  'wiki_dyn_candidates',
  'wiki_fief',
  'wiki_pn',
  'wiki_nt',
  'wiki_person',
  'wiki_personBare',
  'wiki_startYear',
  'wiki_endYear',
  'wikidataId',
  'wikiPersonUrl',
  'norbert_person_id',
  'norbert_nt_ind',
  'norbert_can_name',
  'norbert_dyn',
  'norbert_fief',
  'norbert_pn',
  'norbert_nt',
  'norbert_start_year',
  'norbert_end_year',
  'norbert_dyn_id',
  'fill_notes',
  'reviewer_notes',
];

/**
 * @param {Record<string, unknown>[]} rows
 */
export function rowsToReviewCsv(rows) {
  const body = rows.map((row, index) => {
    const norbert = /** @type {Record<string, unknown>|null} */ (row.norbert ?? null);
    const record = {
      review_id: index + 1,
      suggested_action: row.suggestedAction ?? '',
      action: '',
      match_status: row.matchStatus ?? '',
      match_tier: row.matchTier ?? '',
      match_note: row.matchNote ?? '',
      wiki_sourcePage: row.sourcePage ?? '',
      wiki_dynastySection: row.dynastySection ?? '',
      wiki_dyn_candidates: Array.isArray(row.dynCandidates) ? row.dynCandidates.join('|') : '',
      wiki_fief: row.fief ?? '',
      wiki_pn: row.pn ?? '',
      wiki_nt: row.nt ?? '',
      wiki_person: row.person ?? '',
      wiki_personBare: row.personBare ?? '',
      wiki_startYear: row.startYear ?? '',
      wiki_endYear: row.endYear ?? '',
      wikidataId: row.wikidataId ?? '',
      wikiPersonUrl: row.wikiPersonUrl ?? '',
      norbert_person_id: norbert?.person_id ?? '',
      norbert_nt_ind: norbert?.ind ?? '',
      norbert_can_name: norbert?.can_name ?? '',
      norbert_dyn: norbert?.dyn ?? '',
      norbert_fief: norbert?.fief ?? '',
      norbert_pn: norbert?.pn ?? '',
      norbert_nt: norbert?.nt ?? '',
      norbert_start_year: norbert?.start_year ?? '',
      norbert_end_year: norbert?.end_year ?? '',
      norbert_dyn_id: norbert?.dyn_id ?? '',
      fill_notes: row.fillNotes ?? '',
      reviewer_notes: '',
    };
    return REVIEW_COLUMNS.map((col) => csvCell(record[col])).join(',');
  });
  return `${REVIEW_COLUMNS.map(csvCell).join(',')}\n${body.join('\n')}\n`;
}
