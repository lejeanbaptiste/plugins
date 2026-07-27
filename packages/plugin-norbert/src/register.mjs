import surnamesData from '../data/surnames.json';
import { romanizeSplitParts, segmentPersonName } from './segmentPersonName.mjs';
import { inferConcatenatedOfficeRelation } from './officeRelations.mjs';
import { extractNorbertEntityData } from './entityDataExtractor.mjs';
import { registerNobleTitlePatternProducer } from './nobleTitlePatternProducer.mjs';

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
  context.registerEntityDataExtractor?.(extractNorbertEntityData);
  registerNobleTitlePatternProducer(context);
  context.log(`person-name segmenter ready (${surnames.length} surnames)`);
}
