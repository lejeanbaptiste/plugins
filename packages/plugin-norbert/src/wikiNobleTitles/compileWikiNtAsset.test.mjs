import test from 'node:test';
import assert from 'node:assert/strict';
import {
  buildMatchKey,
  buildNtSearchStrings,
  compileWikiNtAsset,
  planToAssetRecord,
} from './compileWikiNtAsset.mjs';
import { buildApplyPlan } from './applyWikiReview.mjs';

test('buildNtSearchStrings composes title variants', () => {
  const strings = buildNtSearchStrings({ fief: '東海', pn: '恭', nt: '王', person: '劉彊' });
  assert.ok(strings.includes('東海恭王'));
  assert.ok(strings.includes('東海恭王劉彊'));
});

test('planToAssetRecord includes norbert ids without sql', () => {
  const plan = buildApplyPlan(
    {
      suggestedAction: 'update_nt',
      fief: '東海',
      pn: '恭',
      nt: '王',
      personBare: '劉彊',
      startYear: 43,
      endYear: 58,
      wikidataId: 'Q347788',
      norbert_person_id: 7582,
      norbert_nt_ind: 1182,
      norbert_can_name: '劉彊',
      norbert_dyn: '漢',
      norbert_fief: '東海',
      norbert_pn: '恭',
      norbert_nt: '王',
      norbert_dyn_id: 46,
    },
    new Map(),
  );
  const record = planToAssetRecord(plan, plan, 0);
  assert.ok(record);
  assert.equal(record.action, 'update_nt');
  assert.equal(record.norbert.personId, '7582');
  assert.equal(record.norbert.ntInd, '1182');
  assert.equal(record.wiki.wikidataId, 'Q347788');
  assert.equal(record.proposedNt.startYear, 43);
});

test('title_only records have wiki but no norbert', () => {
  const plan = buildApplyPlan(
    {
      matchStatus: 'wiki_only',
      fief: '南康',
      pn: '文宣',
      nt: '公',
      personBare: '劉穆之',
      wikidataId: 'Q10900239',
      fief_corrected: '南康',
      pn_corrected: '文宣',
    },
    new Map(),
  );
  const record = planToAssetRecord(plan, plan, 0);
  assert.equal(record?.action, 'title_only');
  assert.equal(record?.norbert, null);
  assert.equal(record?.wiki.fief, '南康');
});

test('compileWikiNtAsset skips rejected rows', () => {
  const asset = compileWikiNtAsset(
    [
      { suggestedAction: 'link', norbert_person_id: 1, fief: '東海', nt: '王', personBare: '劉彊' },
      { suggestedAction: 'skip', matchStatus: 'duplicate' },
    ],
    {},
  );
  assert.equal(asset.recordCount, 1);
  assert.equal(asset.actionCounts.link, 1);
});
