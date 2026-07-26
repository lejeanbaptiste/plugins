import surnamesData from '../data/surnames.json';
import { romanizeSplitParts, segmentPersonName } from './segmentPersonName.mjs';
import { inferConcatenatedOfficeRelation } from './officeRelations.mjs';

/** @typedef {import('@ljb/plugin-sdk/register-context').PluginRegisterContext} PluginRegisterContext */

/**
 * @param {PluginRegisterContext} context
 */
export function register(context) {
  const surnames = surnamesData.surnames ?? [];
  context.registerPersonNameSegmenter(({ name, romanize }) => {
    const split = segmentPersonName(name, surnames);
    if (!split) return null;
    return {
      ...split,
      romanizedName: romanizeSplitParts(split, romanize, name),
    };
  });
  context.registerOfficeRelationExtractor?.(inferConcatenatedOfficeRelation);
  context.log(`person-name segmenter ready (${surnames.length} surnames)`);
}
