/**
 * East Asian dates plugin entry (phase 1).
 *
 * Core LJB still hosts sanmiao IPC and date UI; this module registers the
 * plugin id and documents contributions declared in plugin.manifest.json.
 * Later phases will move date TS/Python here and load this via the plugin host.
 */

/** @type {import('@ljb/plugin-sdk').PluginRegisterContext} */
export function register(context) {
  context.registerPlugin({
    id: 'cjk-dates',
    onEnable() {
      window.dispatchEvent(new CustomEvent('ljb:plugin-enabled', { detail: { id: 'cjk-dates' } }));
    },
    onDisable() {
      window.dispatchEvent(new CustomEvent('ljb:plugin-disabled', { detail: { id: 'cjk-dates' } }));
    },
  });
}
