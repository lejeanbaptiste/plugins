import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import test from 'node:test';
import assert from 'node:assert/strict';
import {
  extractWikiLinks,
  parseHolderLine,
  parseNobleTitlePage,
  parseReignDates,
  parseTitleLabel,
  splitPageTitle,
} from './parseWikitext.mjs';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const fixture = fs.readFileSync(path.join(__dirname, 'fixtures/donghai-wang.wikitext'), 'utf8');

test('splitPageTitle splits fief and rank', () => {
  assert.deepEqual(splitPageTitle('东海王'), { pageTitle: '东海王', fief: '东海', nt: '王' });
  assert.deepEqual(splitPageTitle('崇德侯'), { pageTitle: '崇德侯', fief: '崇德', nt: '侯' });
});

test('parseTitleLabel extracts posthumous name from holder label', () => {
  assert.deepEqual(parseTitleLabel('东海恭王', '东海', '王'), {
    fief: '东海',
    pn: '恭',
    nt: '王',
  });
  assert.deepEqual(parseTitleLabel('崇德侯', '东海', '王'), {
    fief: '崇德',
    pn: null,
    nt: '侯',
  });
  assert.deepEqual(parseTitleLabel('东海文献王', '东海', '王'), {
    fief: '东海',
    pn: '文献',
    nt: '王',
  });
});

test('extractWikiLinks handles piped disambiguation links', () => {
  assert.deepEqual(extractWikiLinks('[[刘政 (东海王)|刘政]]'), [
    { target: '刘政 (东海王)', display: '刘政' },
  ]);
});

test('parseReignDates reads year ranges', () => {
  assert.deepEqual(parseReignDates('43年-58年在位'), { startYear: 43, endYear: 58 });
  assert.deepEqual(parseReignDates('250年-?年在位'), { startYear: 250, endYear: null });
});

test('parseNobleTitlePage extracts holders from 东海王 fixture', () => {
  const rows = parseNobleTitlePage(fixture, '东海王');
  const liuQiang = rows.find((row) => row.person === '刘彊');
  assert.ok(liuQiang);
  assert.equal(liuQiang.fief, '东海');
  assert.equal(liuQiang.pn, '恭');
  assert.equal(liuQiang.nt, '王');
  assert.equal(liuQiang.dynastySection, '汉朝');
  assert.equal(liuQiang.startYear, 43);
  assert.equal(liuQiang.endYear, 58);

  const chongde = rows.find((row) => row.person === '刘羡');
  assert.ok(chongde);
  assert.equal(chongde.fief, '崇德');
  assert.equal(chongde.nt, '侯');
  assert.equal(chongde.needsReview, true);

  const caoLin = rows.find((row) => row.person === '曹霖');
  assert.ok(caoLin);
  assert.equal(caoLin.dynastySection, '曹魏');
  assert.equal(caoLin.pn, '定');

  const simaYue = rows.find((row) => row.person === '司马越');
  assert.ok(simaYue);
  assert.equal(simaYue.pn, '文献');
});

test('parseHolderLine accepts name-only list items', () => {
  const row = parseHolderLine('**[[刘敦]]，212年-220年在位', '东海王', '汉朝', '东海', '王');
  assert.ok(row);
  assert.equal(row.person, '刘敦');
  assert.equal(row.fief, '东海');
  assert.equal(row.nt, '王');
  assert.equal(row.pn, null);
});

test('parseNobleTitlePage skips reference sections', () => {
  const rows = parseNobleTitlePage(fixture, '东海王');
  assert.equal(rows.some((row) => row.dynastySection === '参考资料'), false);
  assert.equal(rows.some((row) => row.dynastySection === '参见'), false);
});
