/**
 * Fetch plain parallel text from Wikisource via the MediaWiki API.
 * Supports work indexes, edition roots, and single 卷 pages.
 */

const FETCH_HEADERS = {
  'User-Agent': 'ljb-plugin-kanripo-import/0.1 (+https://github.com/leJeanBaptiste)',
};

const WIKISOURCE_HOST_RE = /^(?:[a-z-]+\.)?wikisource\.org$/i;
const VOLUME_SUFFIX_RE = /\/卷(\d+)$/;
const CHAPTER_SKIP_RE = /(?:^|\/)(?:全覽|序言?)$/;
const FETCH_DELAY_MS = 300;

const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms));

export function parseWikisourceUrl(url) {
  let parsed;
  try {
    parsed = new URL(String(url || '').trim());
  } catch {
    return null;
  }
  if (parsed.protocol !== 'http:' && parsed.protocol !== 'https:') return null;
  if (!WIKISOURCE_HOST_RE.test(parsed.hostname)) return null;
  const match =
    parsed.pathname.match(/^\/wiki\/(.+)$/) ||
    parsed.pathname.match(/^\/[a-z]{2,3}(?:-[a-zA-Z]+)?\/(.+)$/);
  if (!match) return null;
  try {
    const title = decodeURIComponent(match[1].replace(/_/g, ' '));
    return { apiHost: parsed.hostname, title, origin: parsed.origin };
  } catch {
    return null;
  }
}

export function wikisourceTitleToUrl(wiki, title) {
  return `${wiki.origin}/wiki/${encodeURIComponent(title.replace(/ /g, '_'))}`;
}

export function volumeNumberFromTitle(title) {
  const match = String(title || '').match(VOLUME_SUFFIX_RE);
  return match ? Number.parseInt(match[1], 10) : null;
}

export function listChapterPages(linkTitles, workRoot) {
  const prefix = String(workRoot || '').trim();
  return linkTitles
    .filter((item) => {
      if (!item.startsWith(`${prefix}/`)) return false;
      if (VOLUME_SUFFIX_RE.test(item)) return false;
      const suffix = item.slice(prefix.length + 1);
      if (!suffix || suffix.includes('(')) return false;
      if (CHAPTER_SKIP_RE.test(item)) return false;
      return true;
    })
    .sort((a, b) => a.localeCompare(b, 'zh-Hant'));
}

export function resolveEditionRoot(pageTitle, linkTitles) {
  const title = String(pageTitle || '').trim();
  const titles = linkTitles.map((item) => String(item || '').trim()).filter(Boolean);

  const volumeParent = title.match(/^(.+)\/卷\d+$/);
  if (volumeParent) return volumeParent[1];

  const directVolumes = listVolumePages(titles, title);
  if (directVolumes.length) return title;

  // Prefer punctuated chapter pages (荀子/勸學篇) over scanned 四庫全書本 卷 pages.
  const chapters = listChapterPages(titles, title);
  if (chapters.length >= 2) return title;

  const editionCandidates = titles.filter(
    (item) => item.startsWith(`${title} (`) || item.startsWith(`${title}(`),
  );
  if (editionCandidates.length) {
    return (
      editionCandidates.find((item) => item.includes('四庫全書本')) ||
      editionCandidates.find((item) => item.includes('四部叢刊本')) ||
      editionCandidates[0]
    );
  }

  const prefixes = new Map();
  for (const item of titles) {
    const match = item.match(/^(.+)\/卷\d+$/);
    if (!match) continue;
    prefixes.set(match[1], (prefixes.get(match[1]) || 0) + 1);
  }
  if (prefixes.size) {
    return [...prefixes.entries()].sort((a, b) => b[1] - a[1])[0][0];
  }

  return title;
}

export function listVolumePages(linkTitles, editionRoot) {
  const prefix = String(editionRoot || '').trim();
  const volumes = linkTitles
    .filter((item) => item.startsWith(`${prefix}/卷`))
    .sort((a, b) => (volumeNumberFromTitle(a) || 0) - (volumeNumberFromTitle(b) || 0));
  if (volumes.length) return volumes;
  return listChapterPages(linkTitles, prefix);
}

export function htmlToParallelText(html) {
  const withoutNoise = html
    .replace(/<script\b[^>]*>[\s\S]*?<\/script>/gi, '')
    .replace(/<style\b[^>]*>[\s\S]*?<\/style>/gi, '')
    .replace(/<!--[\s\S]*?-->/g, '')
    .replace(/<table\b[^>]*class="[^"]*\bmetadata\b[^"]*"[^>]*>[\s\S]*?<\/table>/gi, '')
    .replace(/<div\b[^>]*id="headerContainer"[^>]*>[\s\S]*?<\/div>/gi, '')
    .replace(/<div\b[^>]*id="footer"[^>]*>[\s\S]*?<\/div>/gi, '');

  const text = withoutNoise
    .replace(/<\/?(?:p|div|br|h[1-6]|li|tr|section|article)\b[^>]*>/gi, '\n')
    .replace(/<[^>]+>/g, '')
    .replace(/&amp;/g, '&')
    .replace(/&lt;/g, '<')
    .replace(/&gt;/g, '>')
    .replace(/&quot;/g, '"')
    .replace(/&#(\d+);/g, (_match, digits) => {
      const code = Number.parseInt(digits, 10);
      return Number.isFinite(code) ? String.fromCharCode(code) : '';
    })
    .replace(/&#x([0-9a-fA-F]+);/g, (_match, hex) => {
      const code = Number.parseInt(hex, 16);
      return Number.isFinite(code) ? String.fromCharCode(code) : '';
    });

  return text
    .replace(/[ \t]+\n/g, '\n')
    .replace(/\n{3,}/g, '\n\n')
    .trim();
}

async function mediaWikiGet(apiHost, params) {
  const apiUrl = `https://${apiHost}/w/api.php?${new URLSearchParams(params).toString()}`;
  const response = await fetch(apiUrl, { headers: FETCH_HEADERS });
  if (!response.ok) {
    throw new Error(`Wikisource API HTTP ${response.status}`);
  }
  return response.json();
}

export async function fetchPageLinks(apiHost, title) {
  const titles = [];
  let continueToken = null;

  do {
    const params = {
      action: 'query',
      titles: title,
      prop: 'links',
      pllimit: '500',
      format: 'json',
    };
    if (continueToken) {
      params.plcontinue = continueToken;
    }
    const data = await mediaWikiGet(apiHost, params);
    const page = Object.values(data.query?.pages || {})[0];
    if (page?.missing !== undefined) {
      throw new Error(`Wikisource page “${title}” does not exist.`);
    }
    for (const link of page?.links || []) {
      if (link.ns === 0 && link.title) titles.push(link.title);
    }
    continueToken = data.continue?.plcontinue || null;
  } while (continueToken);

  return titles;
}

async function fetchPageText(apiHost, title) {
  const data = await mediaWikiGet(apiHost, {
    action: 'parse',
    page: title,
    prop: 'text',
    format: 'json',
    disablelimitreport: '1',
    disableeditsection: '1',
  });
  if (data.error) {
    throw new Error(data.error.info || data.error.code || 'Wikisource API error.');
  }
  const html = data.parse?.text?.['*'] ?? '';
  const text = htmlToParallelText(html);
  if (!text.trim()) {
    throw new Error(`Wikisource page “${title}” returned no readable text.`);
  }
  return {
    text,
    pageTitle: data.parse?.title || title,
  };
}

export async function resolveWikisourceCatalog(url) {
  const parsed = parseWikisourceUrl(url);
  if (!parsed) throw new Error('Not a Wikisource URL (expected …wikisource.org/wiki/… or …/zh-hant/…).');

  let links = await fetchPageLinks(parsed.apiHost, parsed.title);
  let editionRoot = resolveEditionRoot(parsed.title, links);
  if (editionRoot !== parsed.title) {
    links = await fetchPageLinks(parsed.apiHost, editionRoot);
  }
  const volumes = listVolumePages(links, editionRoot);
  return {
    apiHost: parsed.apiHost,
    origin: parsed.origin,
    pageTitle: parsed.title,
    editionRoot,
    volumes,
  };
}

export function catalogToSections(catalog) {
  if (catalog.volumes.length) {
    return catalog.volumes.map((title) => ({
      id: title,
      slug: title,
      title: title.split('/').pop() || title,
      rowCount: 0,
    }));
  }
  return [
    {
      id: catalog.editionRoot,
      slug: catalog.editionRoot,
      title: catalog.editionRoot,
      rowCount: 0,
    },
  ];
}

export async function listWikisourceCatalog(url) {
  const catalog = await resolveWikisourceCatalog(url);
  return catalogToSections(catalog);
}

export async function fetchWikisourceParallel(url, options = {}) {
  const parsed = parseWikisourceUrl(url);
  if (!parsed) throw new Error('Not a Wikisource URL (expected …wikisource.org/wiki/… or …/zh-hant/…).');

  const fetchAll = Boolean(options.fetchAll);
  const catalog = await resolveWikisourceCatalog(url);
  const { editionRoot, volumes } = catalog;

  if (!volumes.length) {
    const single = await fetchPageText(parsed.apiHost, parsed.title);
    return {
      text: single.text,
      label: `Wikisource: ${single.pageTitle}`,
      kind: 'wikisource',
      url: url.trim(),
      pageTitle: single.pageTitle,
      sections: catalogToSections(catalog),
    };
  }

  if (!fetchAll && VOLUME_SUFFIX_RE.test(parsed.title)) {
    const single = await fetchPageText(parsed.apiHost, parsed.title);
    return {
      text: single.text,
      label: `Wikisource: ${single.pageTitle}`,
      kind: 'wikisource',
      url: url.trim(),
      pageTitle: single.pageTitle,
      sections: catalogToSections(catalog),
    };
  }

  if (!fetchAll) {
    throw new Error(
      `This Wikisource URL is a work index (${volumes.length} 卷 under “${editionRoot}”). ` +
        'On import, Fetch URL loads the whole edition automatically. In the editor, open a single 卷 page instead.',
    );
  }

  const parts = [];
  for (let index = 0; index < volumes.length; index += 1) {
    if (index > 0) await sleep(FETCH_DELAY_MS);
    const volumeTitle = volumes[index];
    const volume = await fetchPageText(parsed.apiHost, volumeTitle);
    parts.push(volume.text);
  }

  return {
    text: parts.join('\n'),
    label: `Wikisource: ${editionRoot} (${volumes.length} 卷)`,
    kind: 'wikisource',
    url: url.trim(),
    pageTitle: editionRoot,
    sections: catalogToSections(catalog),
  };
}
