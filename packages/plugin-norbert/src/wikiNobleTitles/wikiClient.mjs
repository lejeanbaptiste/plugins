import https from 'node:https';
import { fetch as undiciFetch, ProxyAgent } from 'undici';
import { WIKI_API, WIKI_USER_AGENT } from './constants.mjs';

/** @param {number} ms */
export function sleep(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

/**
 * @typedef {Object} WikiResponse
 * @property {boolean} ok
 * @property {number} status
 * @property {string} statusText
 * @property {(name: string) => string|null} getHeader
 * @property {() => Promise<unknown>} json
 */

/**
 * SOCKS proxies (Tor) must use node:https — SocksProxyAgent is not an undici Dispatcher.
 * @param {URL} url
 * @param {import('socks-proxy-agent').SocksProxyAgent} agent
 */
function fetchViaSocks(url, agent) {
  return new Promise((resolve, reject) => {
    const request = https.get(
      url,
      {
        agent,
        headers: { 'User-Agent': WIKI_USER_AGENT },
      },
      (response) => {
        /** @type {Buffer[]} */
        const chunks = [];
        response.on('data', (chunk) => chunks.push(chunk));
        response.on('end', () => {
          const body = Buffer.concat(chunks).toString('utf8');
          resolve({
            ok: (response.statusCode ?? 500) >= 200 && (response.statusCode ?? 500) < 300,
            status: response.statusCode ?? 500,
            statusText: response.statusMessage ?? '',
            getHeader: (name) => {
              const value = response.headers[name.toLowerCase()];
              return Array.isArray(value) ? value[0] : value ?? null;
            },
            json: async () => JSON.parse(body),
          });
        });
      },
    );
    request.on('error', (error) => {
      if (error && typeof error === 'object' && 'code' in error && error.code === 'ECONNREFUSED') {
        reject(
          new Error(
            'Could not connect to SOCKS proxy (is Tor running?). Try: sudo systemctl start tor\n' +
              'Or drop --proxy and fetch directly with a longer --delay-ms.',
          ),
        );
        return;
      }
      reject(error);
    });
  });
}

/**
 * @param {URL} url
 * @param {{ proxy?: string, dispatcher?: import('undici').Dispatcher, socksAgent?: import('socks-proxy-agent').SocksProxyAgent }} transport
 * @returns {Promise<WikiResponse>}
 */
async function wikiFetch(url, transport) {
  if (transport.socksAgent) {
    return fetchViaSocks(url, transport.socksAgent);
  }
  if (transport.dispatcher) {
    const response = await undiciFetch(url, {
      headers: { 'User-Agent': WIKI_USER_AGENT },
      dispatcher: transport.dispatcher,
    });
    return {
      ok: response.ok,
      status: response.status,
      statusText: response.statusText,
      getHeader: (name) => response.headers.get(name),
      json: () => response.json(),
    };
  }
  const response = await fetch(url, { headers: { 'User-Agent': WIKI_USER_AGENT } });
  return {
    ok: response.ok,
    status: response.status,
    statusText: response.statusText,
    getHeader: (name) => response.headers.get(name),
    json: () => response.json(),
  };
}

/**
 * @typedef {Object} WikiClientOptions
 * @property {number} [delayMs] Minimum pause between successful requests.
 * @property {number} [maxRetries] Retry count for 429/503 responses.
 * @property {string} [proxy] HTTP/HTTPS/SOCKS proxy URL (e.g. socks5://127.0.0.1:9050 for Tor).
 * @property {(message: string) => void} [log]
 */

/**
 * Polite Wikipedia API client: spacing, retries, optional Tor/proxy.
 * @param {WikiClientOptions} [options]
 */
export function createWikiClient(options = {}) {
  const delayMs = options.delayMs ?? 2000;
  const maxRetries = options.maxRetries ?? 6;
  const log = options.log ?? (() => {});
  /** @type {{ proxy?: string, dispatcher?: import('undici').Dispatcher, socksAgent?: import('socks-proxy-agent').SocksProxyAgent }} */
  let transport = {};

  async function ensureTransport() {
    if (!options.proxy || transport.proxy === options.proxy) return;
    if (options.proxy.startsWith('socks')) {
      try {
        const { SocksProxyAgent } = await import('socks-proxy-agent');
        transport = { proxy: options.proxy, socksAgent: new SocksProxyAgent(options.proxy) };
      } catch {
        throw new Error(
          'SOCKS proxy requested but socks-proxy-agent is not installed. Run: npm install (in plugin-norbert)',
        );
      }
    } else {
      transport = { proxy: options.proxy, dispatcher: new ProxyAgent(options.proxy) };
    }
    log(`using proxy ${options.proxy}`);
  }

  let lastRequestAt = 0;

  async function throttle() {
    const elapsed = Date.now() - lastRequestAt;
    if (elapsed < delayMs) {
      await sleep(delayMs - elapsed);
    }
  }

  /**
   * @param {Record<string, string>} params
   */
  async function get(params) {
    await ensureTransport();

    const url = new URL(WIKI_API);
    for (const [key, value] of Object.entries({ format: 'json', maxlag: '5', ...params })) {
      url.searchParams.set(key, value);
    }

    let attempt = 0;
    while (true) {
      await throttle();
      lastRequestAt = Date.now();

      let response;
      try {
        response = await wikiFetch(url, transport);
      } catch (error) {
        const message = error instanceof Error ? error.message : String(error);
        if (message.includes('ECONNREFUSED') && options.proxy?.includes('9050')) {
          throw new Error(
            'Could not connect to Tor on 127.0.0.1:9050 (tor.service is not running).\n' +
              '  Start it: sudo systemctl start tor\n' +
              '  Or fetch without Tor: npm run fetch:wiki-noble-titles -- --resume --delay-ms 7000',
          );
        }
        throw error;
      }

      if (response.ok) {
        return response.json();
      }

      const retryable = response.status === 429 || response.status === 503;
      if (!retryable || attempt >= maxRetries) {
        throw new Error(`Wikipedia API ${response.status}: ${response.statusText}`);
      }

      const retryAfterHeader = response.getHeader('retry-after');
      const retryAfterSec = retryAfterHeader ? Number(retryAfterHeader) : NaN;
      const backoffMs = Number.isFinite(retryAfterSec)
        ? retryAfterSec * 1000
        : delayMs * 2 ** attempt;
      attempt += 1;
      log(
        `rate limited (${response.status}); waiting ${Math.round(backoffMs / 1000)}s before retry ${attempt}/${maxRetries}`,
      );
      await sleep(backoffMs);
    }
  }

  return { get };
}

/**
 * Resolve proxy URL from CLI flag or common env vars.
 * @param {string|null|undefined} cliProxy
 */
export function resolveProxyUrl(cliProxy) {
  return cliProxy || process.env.WIKI_PROXY || process.env.ALL_PROXY || null;
}

/**
 * Resolve delay from CLI flag or env (milliseconds).
 * @param {string|null|undefined} cliDelay
 * @param {number} fallback
 */
export function resolveDelayMs(cliDelay, fallback = 2000) {
  const raw = cliDelay ?? process.env.WIKI_DELAY_MS;
  if (raw == null || raw === '') return fallback;
  const parsed = Number(raw);
  return Number.isFinite(parsed) && parsed >= 0 ? parsed : fallback;
}
