import test from 'node:test';
import assert from 'node:assert/strict';
import {
  buildApplyPlan,
  effectiveFief,
  effectivePn,
  planToSql,
  resolveApplyAction,
} from './applyWikiReview.mjs';

test('resolveApplyAction accepts link insert update automatically', () => {
  assert.equal(resolveApplyAction({ suggestedAction: 'link' }), 'link');
  assert.equal(resolveApplyAction({ suggestedAction: 'insert_nt' }), 'insert_nt');
  assert.equal(resolveApplyAction({ matchStatus: 'wiki_only' }), 'link_title');
  assert.equal(resolveApplyAction({ matchStatus: 'ambiguous' }), 'link_title');
});

test('corrections override parsed fief and pn', () => {
  const row = { wiki_fief: '南康文宣', fief_corrected: '南康', pn_corrected: '文宣' };
  assert.equal(effectiveFief(row), '南康');
  assert.equal(effectivePn(row), '文宣');
  assert.equal(resolveApplyAction(row), 'link_title');
});

test('planToSql emits person_wiki for link', () => {
  const sql = planToSql({
    action: 'link',
    personId: 7582,
    ntInd: 1182,
    wikidataId: 'Q347788',
    wikiPersonUrl: 'https://zh.wikipedia.org/wiki/%E5%8A%89%E5%BD%8A',
    sourcePage: '東海王',
  });
  assert.equal(sql.length, 1);
  assert.match(sql[0], /INSERT INTO person_wiki/);
  assert.match(sql[0], /7582/);
});

test('planToSql emits nt_wiki for title-only link', () => {
  const sql = planToSql({
    action: 'link_title',
    dyn: '漢',
    fief: '南康',
    pn: '文宣',
    nt: '公',
    wikidataId: 'Q10900239',
    sourcePage: '文宣公',
  });
  assert.equal(sql.length, 1);
  assert.match(sql[0], /INSERT INTO nt_wiki/);
  assert.match(sql[0], /南康/);
});
