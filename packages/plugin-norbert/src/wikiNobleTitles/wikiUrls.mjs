export const WIKI_BASE = 'https://zh.wikipedia.org/wiki/';

/** @param {string} title */
export function wikiTitleUrl(title) {
  return `${WIKI_BASE}${encodeURIComponent(title.replace(/ /g, '_'))}`;
}
