/** @param {string} name */
export function normalizePersonSurface(name) {
  return name.normalize('NFC').trim();
}

/**
 * Split a Chinese person label using Norbert pass-2 logic (longest known surname prefix).
 * @param {string} fullName
 * @param {string[]} surnames longest-first
 * @returns {{ familyName: string, givenName: string } | null}
 */
export function segmentPersonName(fullName, surnames) {
  const name = normalizePersonSurface(fullName);
  if (!name || !/^[\u4e00-\u9fff]+$/u.test(name)) return null;
  if ([...name].length < 2) return null;

  for (const surname of surnames) {
    if (!surname || name.length <= surname.length) continue;
    if (name.startsWith(surname)) {
      const givenName = name.slice(surname.length);
      if (givenName) return { familyName: surname, givenName };
    }
  }
  return null;
}

/**
 * @param {{ familyName: string, givenName: string }} split
 * @param {(part: string) => string | null | undefined} romanize
 * @param {string} fallbackName
 */
export function romanizeSplitParts(split, romanize, fallbackName) {
  const parts = [split.familyName, split.givenName]
    .map((part) => romanize(part))
    .filter((value) => typeof value === 'string' && value.trim());
  if (parts.length >= 2) return parts.join(' ');
  if (parts.length === 1) return parts[0];
  return romanize(fallbackName) ?? null;
}
