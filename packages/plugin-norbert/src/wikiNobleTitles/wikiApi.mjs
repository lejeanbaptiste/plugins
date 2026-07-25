import { DEFAULT_WIKI_CATEGORY } from './constants.mjs';
import { wikiTitleUrl } from './wikiUrls.mjs';

/**
 * @typedef {import('./wikiClient.mjs').WikiClientOptions & {
 *   limit?: number,
 *   batchSize?: number,
 *   fetchedTitles?: Set<string>,
 *   onProgress?: (info: { done: number, total: number, title?: string }) => void,
 * }} FetchPagesOptions
 */

/**
 * @param {import('./wikiClient.mjs').ReturnType<import('./wikiClient.mjs').createWikiClient>} client
 * @param {string} category
 * @param {FetchPagesOptions} [options]
 */
export async function fetchCategoryMembers(client, category, options = {}) {
  /** @type {{ pageid: number, title: string }[]} */
  const members = [];
  let cmcontinue;

  while (true) {
    /** @type {Record<string, string>} */
    const params = {
      action: 'query',
      list: 'categorymembers',
      cmtitle: category,
      cmlimit: '500',
    };
    if (cmcontinue) params.cmcontinue = cmcontinue;

    const data = await client.get(params);
    members.push(...(data.query?.categorymembers ?? []));

    if (options.limit && members.length >= options.limit) {
      return members.slice(0, options.limit);
    }
    cmcontinue = data.continue?.cmcontinue;
    if (!cmcontinue) break;
  }

  return members;
}

/**
 * @typedef {Object} WikiPageInfo
 * @property {number} pageId
 * @property {string} url
 * @property {string|null} wikidataId
 */

/**
 * @param {import('./wikiClient.mjs').ReturnType<import('./wikiClient.mjs').createWikiClient>} client
 * @param {string[]} titles
 * @returns {Promise<Map<string, WikiPageInfo>>}
 */
export async function resolvePageInfo(client, titles) {
  const unique = [...new Set(titles.filter(Boolean))];
  /** @type {Map<string, WikiPageInfo>} */
  const out = new Map();
  const batchSize = 50;

  for (let i = 0; i < unique.length; i += batchSize) {
    const batch = unique.slice(i, i + batchSize);
    const data = await client.get({
      action: 'query',
      titles: batch.join('|'),
      prop: 'pageprops|info',
      inprop: 'url',
      ppprop: 'wikibase_item',
      redirects: '1',
    });

    /** @type {Record<string, string>} */
    const redirects = {};
    for (const redirect of data.query?.redirects ?? []) {
      redirects[redirect.from] = redirect.to;
    }

    /** @type {Record<string, WikiPageInfo>} */
    const byTitle = {};
    for (const page of Object.values(data.query?.pages ?? {})) {
      if (page.missing != null) continue;
      const info = {
        pageId: page.pageid,
        url: page.fullurl ?? wikiTitleUrl(page.title),
        wikidataId: page.pageprops?.wikibase_item ?? null,
      };
      byTitle[page.title] = info;
      out.set(page.title, info);
    }

    for (const requested of batch) {
      if (out.has(requested)) continue;
      const redirected = redirects[requested];
      if (redirected && byTitle[redirected]) {
        out.set(requested, byTitle[redirected]);
      }
    }
  }

  return out;
}

/**
 * @param {import('./wikiClient.mjs').ReturnType<import('./wikiClient.mjs').createWikiClient>} client
 * @param {string[]} titles
 * @param {FetchPagesOptions} [options]
 * @returns {Promise<Map<string, { wikitext: string, pageId: number, url: string, wikidataId: string|null }>>}
 */
export async function fetchPagesWikitext(client, titles, options = {}) {
  const pending = titles.filter((title) => !options.fetchedTitles?.has(title));
  /** @type {Map<string, { wikitext: string, pageId: number, url: string, wikidataId: string|null }>} */
  const out = new Map();
  if (pending.length === 0) return out;

  const batchSize = Math.max(1, options.batchSize ?? 1);
  const total = titles.length;
  let done = options.fetchedTitles?.size ?? 0;

  for (let i = 0; i < pending.length; i += batchSize) {
    const batch = pending.slice(i, i + batchSize);
    const data = await client.get({
      action: 'query',
      prop: 'revisions|pageprops|info',
      rvprop: 'content',
      rvslots: 'main',
      inprop: 'url',
      ppprop: 'wikibase_item',
      redirects: '1',
      titles: batch.join('|'),
    });

    /** @type {Record<string, string>} */
    const redirects = {};
    for (const redirect of data.query?.redirects ?? []) {
      redirects[redirect.to] = redirect.from;
    }

    /** @type {Record<string, { wikitext: string, pageId: number, url: string, wikidataId: string|null }>} */
    const byResolvedTitle = {};
    for (const page of Object.values(data.query?.pages ?? {})) {
      if (page.missing != null) continue;
      const wikitext = page.revisions?.[0]?.slots?.main?.['*'];
      if (typeof wikitext !== 'string') continue;
      byResolvedTitle[page.title] = {
        wikitext,
        pageId: page.pageid,
        url: page.fullurl ?? wikiTitleUrl(page.title),
        wikidataId: page.pageprops?.wikibase_item ?? null,
      };
      done += 1;
      options.onProgress?.({ done, total, title: page.title });
    }

    for (const requested of batch) {
      if (byResolvedTitle[requested]) {
        out.set(requested, byResolvedTitle[requested]);
        continue;
      }
      const resolved = Object.entries(byResolvedTitle).find(([title]) => redirects[title] === requested);
      if (resolved) out.set(requested, resolved[1]);
    }
  }

  return out;
}

/**
 * @param {import('./wikiClient.mjs').ReturnType<import('./wikiClient.mjs').createWikiClient>} client
 * @param {string} [category]
 * @param {FetchPagesOptions} [options]
 */
export async function fetchNobleTitlePages(client, category = DEFAULT_WIKI_CATEGORY, options = {}) {
  const members = await fetchCategoryMembers(client, category, options);
  const titles = members.map((member) => member.title);
  const wikitextByTitle = await fetchPagesWikitext(client, titles, options);
  return titles.map((title) => ({
    title,
    wikitext: wikitextByTitle.get(title) ?? null,
  }));
}
