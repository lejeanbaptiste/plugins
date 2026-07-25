// src/register.ts
var HOST_UI_MODULE = "cjk-dates-ui";
async function register(context) {
  context.log("loading East Asian dates UI from host");
  const ui = await context.loadHostModule(HOST_UI_MODULE);
  if (typeof ui.registerCjkDatesUi !== "function") {
    throw new Error(`${HOST_UI_MODULE} is missing registerCjkDatesUi`);
  }
  ui.registerCjkDatesUi(context);
}
export {
  register
};
//# sourceMappingURL=register.mjs.map
