import { resolvePageInfo } from './wikiApi.mjs';
import { wikiTitleUrl } from './wikiUrls.mjs';

/**
 * @typedef {Object} WikiNobleTitleRow
 * @property {string} sourcePage
 * @property {string|null} [dynastySection]
 * @property {string} [rawLine]
 * @property {string|null} [fief]
 * @property {string|null} [pn]
 * @property {string|null} [nt]
 * @property {string|null} [person]
 * @property {string|null} [wikiPersonTitle]
 * @property {number|null} [startYear]
 * @property {number|null} [endYear]
 * @property {string} [confidence]
 * @property {boolean} [needsReview]
 * @property {number|null} [sourcePageId]
 * @property {string|null} [sourcePageUrl]
 * @property {string|null} [sourceWikidataId]
 * @property {number|null} [wikiPersonPageId]
 * @property {string|null} [wikiPersonUrl]
 * @property {string|null} [wikidataId]
 * @property {string} [source]
 */

/**
 * @param {WikiNobleTitleRow[]} rows
 * @param {import('./wikiClient.mjs').ReturnType<import('./wikiClient.mjs').createWikiClient>} client
 * @param {(message: string) => void} [log]
 */
export async function enrichWikiLinks(rows, client, log = () => {}) {
  const sourceTitles = [...new Set(rows.map((row) => row.sourcePage).filter(Boolean))];
  const personTitles = [...new Set(rows.map((row) => row.wikiPersonTitle).filter(Boolean))];

  log(`resolving ${sourceTitles.length} source pages...`);
  const sourceInfo = await resolvePageInfo(client, sourceTitles);

  log(`resolving ${personTitles.length} person pages...`);
  const personInfo = await resolvePageInfo(client, personTitles);

  return rows.map((row) => {
    const source = sourceInfo.get(row.sourcePage);
    const person = row.wikiPersonTitle ? personInfo.get(row.wikiPersonTitle) : null;
    return {
      ...row,
      sourcePageId: source?.pageId ?? row.sourcePageId ?? null,
      sourcePageUrl: source?.url ?? row.sourcePageUrl ?? wikiTitleUrl(row.sourcePage),
      sourceWikidataId: source?.wikidataId ?? row.sourceWikidataId ?? null,
      wikiPersonPageId: person?.pageId ?? row.wikiPersonPageId ?? null,
      wikiPersonUrl: person?.url ?? row.wikiPersonUrl ?? (row.wikiPersonTitle ? wikiTitleUrl(row.wikiPersonTitle) : null),
      wikidataId: person?.wikidataId ?? row.wikidataId ?? null,
    };
  });
}
