/**
 * Daozang import plugin entry. UI lives in the LJB host webpack bundle.
 */

const HOST_UI_MODULE = "daozang-import-ui";

async function register(context) {
  context.log("loading Daozang import UI from host");
  const ui = await context.loadHostModule(HOST_UI_MODULE);
  if (typeof ui.registerDaozangImportUi !== "function") {
    throw new Error(`${HOST_UI_MODULE} is missing registerDaozangImportUi`);
  }
  ui.registerDaozangImportUi(context);
}

export { register };
