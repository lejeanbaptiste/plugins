#!/usr/bin/env node
import assert from 'node:assert/strict';
import test from 'node:test';
import {
  chapterUrlFrom,
  isCtextCaptchaPage,
  listWikiCatalog,
  parseCtextWikiUrl,
  parseWikiResIndex,
} from './ctext-wiki-parallel.mjs';

const RES_INDEX_SNIPPET = `
<a href="wiki.pl?if=gb&amp;chapter=793335">賦甲</a><br />
<a href="wiki.pl?if=gb&amp;chapter=793335#京都上">京都上</a><br />
<a href="wiki.pl?if=gb&amp;chapter=793336">賦乙</a><br />
`;

test('parseCtextWikiUrl accepts chapter and res wiki URLs', () => {
  assert.deepEqual(parseCtextWikiUrl('https://ctext.org/wiki.pl?if=gb&chapter=793335'), {
    kind: 'chapter',
    chapter: '793335',
    origin: 'https://ctext.org',
    wikiPath: '/wiki.pl',
    if: 'gb',
  });
  assert.deepEqual(parseCtextWikiUrl('https://ctext.org/wiki.pl?if=gb&res=150222'), {
    kind: 'res',
    res: '150222',
    origin: 'https://ctext.org',
    wikiPath: '/wiki.pl',
    if: 'gb',
  });
  assert.equal(parseCtextWikiUrl('https://ctext.org/analects'), null);
});

test('parseWikiResIndex deduplicates chapter links and keeps top-level titles', () => {
  assert.deepEqual(parseWikiResIndex(RES_INDEX_SNIPPET), [
    { id: '793335', if: 'gb', title: '賦甲' },
    { id: '793336', if: 'gb', title: '賦乙' },
  ]);
});

test('listWikiCatalog returns chapters when page has no content rows', () => {
  const catalog = listWikiCatalog(RES_INDEX_SNIPPET);
  assert.equal(catalog.length, 2);
  assert.equal(catalog[0].title, '賦甲');
  assert.equal(catalog[1].id, '793336');
});

test('isCtextCaptchaPage detects human-verification pages', () => {
  assert.equal(isCtextCaptchaPage('<title>Please confirm that you are human!</title>'), true);
  assert.equal(isCtextCaptchaPage('<tr class="result">子曰</tr>'), false);
});

test('chapterUrlFrom builds chapter fetch URLs', () => {
  const wiki = parseCtextWikiUrl('https://ctext.org/wiki.pl?if=gb&res=150222');
  assert.equal(
    chapterUrlFrom(wiki, '793335'),
    'https://ctext.org/wiki.pl?if=gb&chapter=793335',
  );
});
