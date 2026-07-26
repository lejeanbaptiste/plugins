import test from 'node:test';
import assert from 'node:assert/strict';
import { inferConcatenatedOfficeRelation } from './officeRelations.mjs';

const office = (source, authorityId, followsOffice = false) => ({
  source,
  authorityId,
  kind: 'office',
  primaryName: authorityId,
  metadata: { followsOffice },
});

test('first adjacent office becomes parent when the second follows an office', () => {
  assert.deepEqual(
    inferConcatenatedOfficeRelation({
      first: office('CBDB', 'parent'),
      second: office('Norbert', 'child', true),
      adjacent: true,
    }),
    {
      source: 'norbert',
      rule: 'office-concatenation',
      sourceIds: ['parent', 'child'],
      confidence: 'inferred',
    },
  );
});

test('does not infer from a gap or an ordinary Norbert office', () => {
  assert.equal(
    inferConcatenatedOfficeRelation({
      first: office('Norbert', 'parent'),
      second: office('Norbert', 'child', true),
      adjacent: false,
    }),
    null,
  );
  assert.equal(
    inferConcatenatedOfficeRelation({
      first: office('Norbert', 'parent'),
      second: office('Norbert', 'child'),
      adjacent: true,
    }),
    null,
  );
});
