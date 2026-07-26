/**
 * Renderer-side plugin registration API (manifestVersion 1.0.0).
 */

/**
 * @typedef {Object} PluginRegisterContext
 * @property {string} pluginId
 * @property {(message: string) => void} log
 * @property {(action: string, handler: PluginToolActionHandler) => void} registerToolAction
 * @property {(type: string, component: unknown) => void} registerDialog
 * @property {(matcher: (suggestions: unknown[]) => boolean, component: unknown, options?: { finishWhenIdle?: boolean | ((suggestions: unknown[]) => boolean) }) => void} registerReviewPanel
 * @property {(item: { id: string; icon: string; title: string; tooltip?: string; group?: string; isAvailable: () => boolean; onClick: (ctx: { openCalendar: (notice?: string) => void }) => void }) => void} registerToolbarItem
 * @property {(moduleId: string) => Promise<{ registerCjkDatesUi?: (context: PluginRegisterContext) => void }>} loadHostModule
 * @property {(segmenter: (input: { name: string; projectLang: string | null; romanize: (part: string) => string | null }) => { familyName: string; givenName: string; romanizedName?: string | null } | null) => void} registerPersonNameSegmenter
 * @property {(extractor: (input: { first: unknown, second: unknown, adjacent: boolean }) => { source: string, rule: string, sourceIds: string[], confidence: 'asserted'|'inferred' } | null) => void} [registerOfficeRelationExtractor]
 * @property {() => void} [onEnable]
 * @property {() => void} [onDisable]
 */

/**
 * @typedef {Object} PluginToolActionContext
 * @property {(message: string) => void} notify
 */

/**
 * @typedef {(ctx: PluginToolActionContext) => void | Promise<void>} PluginToolActionHandler
 */

export {};
