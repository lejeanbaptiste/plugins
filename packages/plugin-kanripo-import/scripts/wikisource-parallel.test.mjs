#!/usr/bin/env node
import assert from 'node:assert/strict';
import test from 'node:test';
import {
  listVolumePages,
  parseWikisourceUrl,
  resolveEditionRoot,
  volumeNumberFromTitle,
} from './wikisource-parallel.mjs';

test('parseWikisourceUrl accepts wiki and zh-hant paths', () => {
  assert.deepEqual(parseWikisourceUrl('https://zh.wikisource.org/zh-hant/%E8%8D%80%E5%AD%90'), {
    apiHost: 'zh.wikisource.org',
    title: '荀子',
    origin: 'https://zh.wikisource.org',
  });
});

test('resolveEditionRoot prefers chapter pages over scanned editions', () => {
  const links = ['荀子 (四庫全書本)', '荀子 (四部叢刊本)', '荀子/勸學篇', '荀子/修身篇'];
  assert.equal(resolveEditionRoot('荀子', links), '荀子');
});

test('resolveEditionRoot falls back to 四庫全書本 when no chapters', () => {
  const links = ['荀子 (四庫全書本)', '荀子 (四部叢刊本)'];
  assert.equal(resolveEditionRoot('荀子', links), '荀子 (四庫全書本)');
});

test('resolveEditionRoot moves from volume page to edition root', () => {
  assert.equal(
    resolveEditionRoot('荀子 (四庫全書本)/卷01', ['荀子 (四庫全書本)/卷02']),
    '荀子 (四庫全書本)',
  );
});

test('listVolumePages lists chapter pages when no 卷 pages exist', () => {
  const chapters = listVolumePages(['荀子/修身篇', '荀子/勸學篇'], '荀子');
  assert.deepEqual(chapters, ['荀子/修身篇', '荀子/勸學篇']);
});

test('listVolumePages sorts 卷 pages numerically', () => {
  const volumes = listVolumePages(
    ['荀子 (四庫全書本)/卷10', '荀子 (四庫全書本)/卷02', '荀子 (四庫全書本)/卷01'],
    '荀子 (四庫全書本)',
  );
  assert.deepEqual(volumes, [
    '荀子 (四庫全書本)/卷01',
    '荀子 (四庫全書本)/卷02',
    '荀子 (四庫全書本)/卷10',
  ]);
  assert.equal(volumeNumberFromTitle('荀子 (四庫全書本)/卷10'), 10);
});
