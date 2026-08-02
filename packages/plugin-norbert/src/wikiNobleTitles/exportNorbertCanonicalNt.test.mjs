import test from 'node:test';
import assert from 'node:assert/strict';
import { buildCanonicalNtRecords, coveredKeysFromExistingAsset } from './exportNorbertCanonicalNt.mjs';

test('builds a canonical record for an uncovered person_nt row', () => {
  const records = buildCanonicalNtRecords({
    ntRows: [
      { ind: 1112, personId: 3710, dyn: '漢', fief: '漢', pn: '昭烈', nt: '帝', dynId: 49, startYear: null, endYear: null },
    ],
    personNameById: new Map([['3710', '劉備']]),
    coveredKeys: new Set(),
    startIndex: 682,
  });
  assert.equal(records.length, 1);
  const record = records[0];
  assert.equal(record.id, 'wnt-0683');
  assert.equal(record.source, 'norbert-direct');
  assert.equal(record.action, 'norbert_canonical');
  assert.equal(record.norbert.personId, '3710');
  assert.equal(record.norbert.ntInd, '1112');
  // dyn === fief ("漢") must not produce a duplicated "漢漢昭烈帝" string.
  assert.deepEqual(record.searchStrings, ['漢昭烈帝', '漢帝', '漢昭烈帝劉備', '漢帝劉備']);
  assert.equal(record.metadata.wrapper.personId, '3710');
  assert.equal(record.metadata.wrapper.components.posthumousName, '昭烈');
});

test('skips rows already covered by a wiki-matched record', () => {
  const records = buildCanonicalNtRecords({
    ntRows: [
      { ind: 1182, personId: 7582, dyn: '漢', fief: '東海', pn: '恭', nt: '王', dynId: 46, startYear: 43, endYear: 58 },
    ],
    personNameById: new Map([['7582', '劉彊']]),
    coveredKeys: coveredKeysFromExistingAsset([
      { norbert: { personId: '7582', ntInd: '1182' } },
    ]),
    startIndex: 0,
  });
  assert.equal(records.length, 0);
});

test('emits a no-fief empress title with its complete posthumous title', () => {
  const records = buildCanonicalNtRecords({
    ntRows: [
      { ind: 1, personId: 9547, dyn: null, fief: null, pn: null, nt: '后', dynId: null, startYear: null, endYear: null },
      { ind: 2, personId: 2, dyn: '漢', fief: '東海', pn: null, nt: null, dynId: 1, startYear: null, endYear: null },
    ],
    personNameById: new Map(),
    personDisplayNameById: new Map([['9547', '孝元皇后']]),
    coveredKeys: new Set(),
    startIndex: 0,
  });
  assert.equal(records.length, 1);
  assert.deepEqual(records[0].searchStrings, ['孝元皇后']);
  assert.equal(records[0].metadata.wrapper, undefined);
  assert.deepEqual(records[0].metadata.nobleTitle, {
    fief: null,
    roleName: '皇后',
    posthumousName: '孝元',
  });
});

test('a person with no name in the persons pack still emits a title-only record', () => {
  const records = buildCanonicalNtRecords({
    ntRows: [
      { ind: 5, personId: 999999, dyn: '漢', fief: '中山', pn: '靖', nt: '王', dynId: 46, startYear: null, endYear: null },
    ],
    personNameById: new Map(),
    coveredKeys: new Set(),
    startIndex: 0,
  });
  assert.equal(records.length, 1);
  assert.equal(records[0].metadata.wrapper, undefined);
  assert.equal(records[0].metadata.teiTag, 'nobleTitle');
  assert.deepEqual(records[0].names, []);
});
