import test from 'node:test';
import assert from 'node:assert/strict';
import { romanizeSplitParts, segmentPersonName } from './segmentPersonName.mjs';

const SURNAMES = ['莫多婁', '成公', '公孫', '歐陽', '司馬', '王', '李', '张', '張'].sort(
  (a, b) => b.length - a.length,
);

test('segmentPersonName splits simple two-character names', () => {
  assert.deepEqual(segmentPersonName('張良', SURNAMES), { familyName: '張', givenName: '良' });
  assert.deepEqual(segmentPersonName('张良', SURNAMES), { familyName: '张', givenName: '良' });
});

test('segmentPersonName splits three-character names', () => {
  assert.deepEqual(segmentPersonName('王安石', SURNAMES), { familyName: '王', givenName: '安石' });
});

test('segmentPersonName prefers compound surnames', () => {
  const withOuyang = ['欧阳', '司马', '王', '张'];
  assert.deepEqual(segmentPersonName('欧阳修', withOuyang), {
    familyName: '欧阳',
    givenName: '修',
  });
  assert.deepEqual(segmentPersonName('司马相如', ['司马', '王']), {
    familyName: '司马',
    givenName: '相如',
  });
});

test('segmentPersonName returns null for unknown patterns', () => {
  assert.equal(segmentPersonName('A', SURNAMES), null);
  assert.equal(segmentPersonName('某', SURNAMES), null);
});

test('romanizeSplitParts joins family and given romanizations', () => {
  const split = { familyName: '王', givenName: '安石' };
  const romanized = romanizeSplitParts(split, (part) => (part === '王' ? 'Wang' : 'Anshi'), '王安石');
  assert.equal(romanized, 'Wang Anshi');
});
