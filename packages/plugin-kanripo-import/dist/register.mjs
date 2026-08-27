/**
 * Thin plugin entry. UI is loaded from the LJB host webpack bundle.
 */
const HOST_UI_MODULE = 'kanripo-import-ui';

export async function register(context) {
  context.log('loading Kanripo import UI from host');
  const ui = await context.loadHostModule(HOST_UI_MODULE);
  if (typeof ui.registerKanripoImportUi !== 'function') {
    throw new Error(`${HOST_UI_MODULE} is missing registerKanripoImportUi`);
  }
  ui.registerKanripoImportUi(context);
}
