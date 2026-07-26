/** Extract refreshable facts from a Norbert person wrapper. */
export function extractNorbertEntityData({ wrapper }) {
  const assertions = [];
  const descendants = (name) => Array.from(wrapper.getElementsByTagName(name));
  for (const node of descendants('nationality')) {
    const value = node.textContent?.trim();
    if (value) assertions.push({ element: 'nationality', value, ref: node.getAttribute('ref') ?? undefined });
  }
  for (const node of descendants('placeOfOrigin')) {
    const value = node.textContent?.trim();
    if (value) assertions.push({ element: 'placeName', value, ref: node.getAttribute('ref') ?? undefined });
  }
  for (const node of descendants('officeName')) {
    const value = node.textContent?.trim();
    if (value) assertions.push({ element: 'state', value, ref: node.getAttribute('ref') ?? undefined });
  }
  for (const node of descendants('nobleTitle')) {
    const place = node.getElementsByTagName('placeName')[0];
    const role = node.getElementsByTagName('roleName')[0];
    const posthumous = Array.from(node.getElementsByTagName('persName'))
      .find((person) => person.getAttribute('type') === 'posthumous');
    const value = node.textContent?.trim();
    if (value) {
      assertions.push({
        element: 'nobleTitle',
        value,
        ref: node.getAttribute('ref') ?? undefined,
        children: [
          ...(place ? [{ element: 'placeName', value: place.textContent?.trim() ?? '', ref: place.getAttribute('ref') ?? undefined }] : []),
          ...(role ? [{ element: 'roleName', value: role.textContent?.trim() ?? '', ref: role.getAttribute('ref') ?? undefined }] : []),
          ...(posthumous ? [{ element: 'persName', value: posthumous.textContent?.trim() ?? '', ref: posthumous.getAttribute('ref') ?? undefined }] : []),
        ],
      });
    }
  }
  return assertions;
}
