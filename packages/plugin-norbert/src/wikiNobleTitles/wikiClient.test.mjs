import test from 'node:test';
import assert from 'node:assert/strict';
import { resolveDelayMs, resolveProxyUrl, sleep } from './wikiClient.mjs';

test('resolveDelayMs prefers CLI over env', () => {
  const prev = process.env.WIKI_DELAY_MS;
  process.env.WIKI_DELAY_MS = '5000';
  assert.equal(resolveDelayMs('1000', 2000), 1000);
  assert.equal(resolveDelayMs(null, 2000), 5000);
  process.env.WIKI_DELAY_MS = prev;
});

test('resolveProxyUrl reads WIKI_PROXY', () => {
  const prev = process.env.WIKI_PROXY;
  process.env.WIKI_PROXY = 'socks5://127.0.0.1:9050';
  assert.equal(resolveProxyUrl(null), 'socks5://127.0.0.1:9050');
  assert.equal(resolveProxyUrl('http://127.0.0.1:8118'), 'http://127.0.0.1:8118');
  process.env.WIKI_PROXY = prev;
});

test('sleep waits roughly the requested duration', async () => {
  const start = Date.now();
  await sleep(50);
  assert.ok(Date.now() - start >= 45);
});
