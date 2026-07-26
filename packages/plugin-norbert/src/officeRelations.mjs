/**
 * Norbert's position-sensitive concatenation rule. When a Norbert office row
 * marked followsOffice is tagged immediately after another resolved office,
 * retain the first as the inferred parent of the second.
 *
 * @param {{ first: any, second: any, adjacent: boolean }} input
 */
export function inferConcatenatedOfficeRelation({ first, second, adjacent }) {
  if (!adjacent) return null;
  if (first?.kind !== 'office' || second?.kind !== 'office') return null;
  if (String(second.source).toLowerCase() !== 'norbert') return null;
  if (!second.metadata?.followsOffice) return null;
  return {
    source: 'norbert',
    rule: 'office-concatenation',
    sourceIds: [String(first.authorityId), String(second.authorityId)],
    confidence: 'inferred',
  };
}
