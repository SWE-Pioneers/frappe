# Frappe Books — Vue Frontend Architecture

Renderer UI: `src/` · Shared core library: `fyo/` · Electron main + preload: `main/` · Shared low-level: `utils/`, `schemas/`, `models/`.

Stack: Vue 3.2 (Options API + some `<script setup>`), `vue-router` 4 (`createWebHistory`), Tailwind (postcss7-compat), TypeScript, Electron 22. Vite build (`build/scripts/*.mjs`). **No Vuex/Pinia** — global state is the reactive `fyo` singleton plus a handful of module-level `ref`s.

---

## 1. Entry & wiring

### Entry point — `src/renderer.ts` (not `src/main.ts`)

`src/renderer.ts:1-61` boot sequence:
1. `:17-21` — read persisted language from `fyo.config`, `setLanguageMap`.
2. `:23` — `registerIpcRendererListeners()`.
3. `:24-30` — `await ipc.getEnv()` fills `fyo.store` (`isDevelopment`, `appVersion`, `platform`). **First thing that requires the `ipc` global — the app cannot boot without it.**
4. `:33-43` — `createApp`, register router, global components `FeatherIcon`/`Badge`, `on-outside-click` directive.
5. `:44-57` — a **global mixin** injects `this.fyo`, `this.platform`, `this.t`, `this.T` into every component (why components use `fyo`/`t` without importing).
6. `:60` — `app.mount('body')`.
7. `:63-105` — global error handlers (`window.onerror`, `onunhandledrejection`, custom `LOG_UNEXPECTED`, `app.config.errorHandler`) → `src/errorHandling.ts`.

### The `fyo` instance — `src/initFyo.ts:8`

`export const fyo = new Fyo({ isTest: false, isElectron: true });` — **`isElectron: true` is hardcoded**; this flag is the master switch for the demux layer (§4).

### Global state

- `fyo` singleton (docs cache, schema map, singles, store).
- Module-level refs in `src/utils/refs.ts:4-10`: `showSidebar`, `docsPathRef`, `systemLanguageRef`, `historyState`.
- `App.vue` provides via `src/utils/injectionKeys.ts`: `keysKey` (pressed keys), `searcherKey` (Search), `shortcutsKey` (Shortcuts), `languageDirectionKey` (ltr/rtl) — `src/App.vue:102-105`.

### `src/utils/*`

There is **no `src/utils/ipc.ts`** — the IPC wrapper is the preload's global `ipc` (see 04-desktop doc). `src/utils/` (25 files) are UI/domain helpers: `initialization.ts` (`initializeInstance`), `db.ts` (connect + error dialogs `:19-94`), `ui.ts` (~1000 lines: `routeTo`, `getFormRoute`, `openQuickEdit`, doc actions, file helpers), `search.ts`, `shortcuts.ts`, `sidebarConfig.ts`, `printTemplates.ts`, `language.ts`, `theme.ts`, `filters.ts`, `export.ts`, `api.ts`, `erpnextSync.ts`, `pos.ts`, `chart.ts`, `colors.ts`, `interactive.ts` (dialogs/toasts), `injectionKeys.ts`, `refs.ts`, `vueUtils.ts`, `misc.ts`, `getStartedConfig.ts`, `doc.ts`, `types.ts`, `index.ts`.

### App shell — `src/App.vue`

A **3-screen state machine** (`activeScreen`: `Desk` | `DatabaseSelector` | `SetupWizard`, `src/App.vue:80-84`); the router only operates *inside* Desk. Boot:
- `setInitialScreen` (`:149-161`) reads `fyo.config.get('lastSelectedFilePath')` → open that DB or show `DatabaseSelector`.
- `fileSelected` → `checkDbAccess` → `showSetupWizardOrDesk` → `connectToDatabase` → (setup wizard if incomplete) → `initializeInstance` → `setDesk`.
- `setDesk` (`:166-179`): language, telemetry, `ipc.checkForUpdates`, company name, `Search` index.
- `setDeskRoute` (`:301-311`): `/get-started`, or `localStorage.lastRoute`, or `/`.
- `WindowsTitleBar` rendered only when `platform === 'Windows'` (`:15-19`); hosts `#toast-container`.

### Router — `src/router.ts`

`createWebHistory()` (`:142`). `afterEach` persists `lastRoute` to `localStorage` (`:144-154`). Routes:

| Path | Component | Notes |
|---|---|---|
| `/` | `Dashboard` | |
| `/get-started` | `GetStarted` | onboarding |
| `/edit/:schemaName/:name` | `CommonForm` (+ `edit`=`QuickEditForm`) | |
| `/list/:schemaName/:pageTitle?` | `ListView` (+ `edit`) | filters via `route.query.filters` JSON |
| `/print/:schemaName/:name` | `PrintView` | |
| `/report-print/:reportName` | `ReportPrintView` | |
| `/report/:reportClassName` | `Report` | |
| `/chart-of-accounts` | `ChartOfAccounts` (+ `edit`) | |
| `/import-wizard` | `ImportWizard` | |
| `/template-builder/:name` | `TemplateBuilder` | |
| `/customize-form` | `CustomizeForm` | |
| `/settings` | `Settings` (+ `edit`) | |
| `/pos` | `POS` (+ `edit`) | |

The `edit` named router-view is a slide-in quick-edit panel inside `Desk.vue` (`src/pages/Desk.vue:43-53`), gated on `route.query.edit`. Primary `router-view` is `keep-alive`d keyed on `$route.path` (`:32-41`).

---

## 2. Page inventory (`src/pages/`)

- **Desk** — the shell: `Sidebar` + `router-view` + quick-edit view.
- **DatabaseSelector** — company-file chooser (§7): recent DB files via `ipc.getDbList()` (`:434`), create-new, open-existing (native dialog), create-demo (`:408-432`).
- **SetupWizard** (`src/pages/SetupWizard/SetupWizard.vue`) — first-run org setup (company, country, currency, fiscal year) → `setup-complete` → `setupInstance` (`src/setup/setupInstance`).
- **GetStarted** — onboarding card grid; config from `getStartedConfig.ts`.
- **Dashboard** (`src/pages/Dashboard/`) — `Cashflow.vue`, `Expenses.vue`, `ProfitAndLoss.vue`, `UnpaidInvoices.vue` over `BaseDashboardChart.vue` + `PeriodSelector.vue`. Data via `fyo.db` bespoke aggregates.
- **ListView** (`ListView.vue` + `List.vue` + `ListCell.vue`) — schema-driven grid; columns from schema, rows from `fyo.db.getAll`; filters/sort; row click → CommonForm.
- **CommonForm** (+ `CommonFormSection.vue`, `RowEditForm.vue`, `LinkedEntries.vue`) — the generic FormView: sections of `FormControl`s, submit/cancel/delete/print actions, barcode & exchange-rate widgets, linked-entries panel.
- **QuickEditForm** — condensed side-panel form (`openQuickEdit`, `src/utils/ui.ts:46`).
- **ChartOfAccounts** — account tree with inline quick-edit.
- **Report** — generic viewer driven by report classes (`fyo.store.reports`): filter bar + `ReportTable`.
- **Settings** (`src/pages/Settings/`) — tabbed single-doc editor; `ipc.reloadWindow` on some changes (`:265`).
- **ImportWizard** — CSV/XLSX import: pick schema, map columns, preview, submit; template download via `ipc.saveData` (`:838`).
- **PrintView / ReportPrintView** — render doc/report through a print template to HTML with Save-PDF/Print buttons (§6).
- **TemplateBuilder** (`src/pages/TemplateBuilder/`) — print-template editor: `TemplateEditor.vue` (CodeMirror + `@codemirror/lang-vue`), `PrintContainer.vue`, `ScaledContainer.vue`, etc. Edits `PrintTemplate` docs.
- **CustomizeForm** — end-user schema customization → `CustomField`/`CustomForm` docs.
- **POS** (`src/pages/POS/`) — full point-of-sale: `POS.vue` switches `ClassicPOS.vue`/`ModernPOS.vue`; ~15 modals (`PaymentModal`, `OpenPOSShiftModal`/`ClosePOSShiftModal`, `CouponCodeModal`, `LoyaltyProgramModal`, `PriceListModal`, `BatchSelectionModal`, `ReturnSalesInvoiceModal`, `SavedInvoiceModal`, `ItemEnquiryModal`, `KeyboardModal`, `AlertModal`, `POSQuickActions`). Logic in `src/utils/pos.ts`.

---

## 3. Component library (`src/components/`)

### Form controls (`src/components/Controls/`)

Dispatcher **`FormControl.vue`** (`:60-68`): functional `render()` maps `$attrs.df.fieldtype` → component (`:21-39`), default `Data`. So a schema field with `fieldtype:'Currency'` renders `Currency.vue`, `'Link'` → `Link.vue`, etc.

Controls: `Data`, `Text`, `Int`, `Float`, `Currency`, `Check`, `Select`, `AutoComplete`, `Link`, `DynamicLink`, `MultiLabelLink`, `Date`, `Datetime` (+ pickers), `Color`, `Secret`, `Attachment`, `AttachImage`, `Barcode`/`WeightEnabledBarcode`, `ExchangeRate`, `LanguageSelector`, `Button`, `Table`/`TableRow` (child tables).

- **`Base.vue`** — shared `<input>` base: injects the parent `doc` (`:41-46`), reads `df`, computes readonly/required via `evaluateReadOnly`/`evaluateRequired` (`src/utils/doc.ts`), emits `input`/`focus`/`blur`.
- **`Table.vue` + `TableRow.vue`** — the child-table grid; each cell is a `FormControl` bound to a child doc field; add/remove/reorder.
- **`Link.vue`/`AutoComplete.vue`** — pickers backed by `fyo.db.getAll` searches; `DynamicLink` resolves target from a sibling field.

Value flow: control emits `input` → form calls `doc.set(fieldname, value)` on the fyo `Doc` (validation + formulas live in the `Doc`, not the control).

### Generic UI

`Button`, `Badge`, `Avatar`, `Dialog.vue`, `Dropdown.vue`, `DropdownWithActions.vue`, `FilterDropdown.vue`, `FormContainer.vue`, `FormHeader.vue`, `Sidebar.vue`, `SearchBar.vue`, `Icon.vue`/`FeatherIcon.vue` + `Icons/{12,16,18,24}/*`, `Charts/{Bar,Donut,Line}Chart.vue` (hand-rolled SVG), `HorizontalResizer.vue`, `ErrorBoundary.vue`, `ExportWizard.vue`, `HowTo.vue`, `WindowsTitleBar.vue`, `Toast.vue`.

### Modals / dialogs / shortcuts

- **Dialogs & toasts are pure Vue**, mounted imperatively — `src/utils/interactive.ts:8-37` (`showDialog`), `:39+` (`showToast`). Not Electron-native → web-portable as-is.
- **Shortcuts** — `src/utils/shortcuts.ts` (`Shortcuts` class, context-scoped chords, `pmod` = ⌘/Ctrl), fed by `useKeys()` (`src/utils/vueUtils.ts`), provided app-wide.

---

## 4. DB/doc call path & web-incompatibility points

### Call path

```
Component (FormControl emits)
  → Doc.set()/sync()/delete()            fyo/model/doc.ts
  → fyo.db.<method>()                     fyo/core/dbHandler.ts
  → DatabaseDemux.call(method, ...args)   fyo/demux/db.ts
  → ipc.db.call(method, ...args)          global ipc (main/preload.ts:248)
  → ipcRenderer.invoke(DB_CALL, ...)      Electron IPC
  → DatabaseManager (knex + better-sqlite3)  backend/
```

### The clean seam — the demux layer

`fyo/demux/db.ts` already branches on `#isElectron`; every method has `if (!isElectron) throw NotImplemented`. **The architecture already anticipates a non-Electron transport** — swap `DatabaseDemux` for an HTTP demux and everything above (`DatabaseHandler`, `Doc`, all controls/pages) is unchanged. `Fyo`'s constructor accepts injected `conf.DatabaseDemux`/`conf.AuthDemux` (`fyo/index.ts:54-55`), so a web build passes a REST-backed demux without editing the core. Same pattern in `fyo/demux/config.ts:4-11` (`ipc.store` vs in-memory Map) and `fyo/demux/auth.ts:11-17`.

### The `ipc` global

Built in `main/preload.ts`, exposed via `contextBridge` (`:280`), typed in `src/shims-tsx.d.ts:4-18` (`declare global { const ipc: IPC }`).

### Every `src/` ipc call site (web-incompatibility inventory — 35 sites, 20 files)

- `src/renderer.ts:24` `ipc.getEnv` — **boot-blocking**.
- `src/App.vue:171,185,206,247` — `checkForUpdates`, `checkDbAccess`, `getDbDefaultPath`, `initScheduler`.
- `src/utils/ui.ts:487,1025,1031,1060,1068` — `selectFile`, `showItemInFolder`, `deleteFile`, `getOpenFilePath`, `getSaveFilePath`.
- `src/utils/language.ts:54,72` — `reloadWindow`, `getLanguageMap`.
- `src/utils/printTemplates.ts:462,470,536` — `makePDF`, `printDocument`, `getTemplates`.
- `src/utils/api.ts:5`, `src/utils/erpnextSync.ts:880` — `sendAPIRequest` (CORS-dodging proxy).
- `src/errorHandling.ts:45,156,286` — `sendError`, `showError`, `openExternalUrl`.
- `src/renderer/registerIpcRendererListeners.ts:6,29,33` — main-process event listeners.
- `src/components/Controls/AttachImage.vue:126` — `selectFile`.
- `src/components/ExportWizard.vue:261`, `src/pages/ImportWizard.vue:838` — `saveData`.
- `src/components/{Sidebar,SearchBar,HowTo}.vue`, `src/pages/GetStarted.vue` — `openLink`/`openExternalUrl`.
- `src/components/WindowsTitleBar.vue:103,106,110` — window controls.
- `src/pages/DatabaseSelector.vue:434` — `getDbList`.
- `src/pages/Settings/Settings.vue:265`, `src/pages/POS/ClosePOSShiftModal.vue:236` — `reloadWindow`.

No file in `src/` imports `electron` directly — **the entire electron surface is one injectable object.** Lowest-effort web path: ship a browser `ipc` shim on `window` that (a) proxies `ipc.db.*`/`ipc.store.*` to HTTP, (b) no-ops or web-substitutes window/file/print calls.

---

## 5. Search, shortcuts, sidebar, customization

- **Search/command palette** — `src/utils/search.ts` (`Search` class), built in `App.setSearcher` (`src/App.vue:162-165`); groups Create/List/Report/Docs/Page/Recent (`:68-77`); UI `SearchBar.vue`; fuzzy match via `fuzzyMatch`.
- **Sidebar** — `src/utils/sidebarConfig.ts` `getSidebarConfig()` (`:6-27`): full tree filtered by `hidden()` predicates reading feature flags from `fyo.singles.AccountingSettings` (`enableInventory`, `gstin`, ...). Rendered by `Sidebar.vue`.
- **Customization** — `CustomizeForm.vue` → `CustomField`/`CustomForm` docs; schema map merged with custom fields at load; list columns and form sections derive from the (customized) schema — data-driven.

---

## 6. Print flow (renderer side)

- Templates are `PrintTemplate` docs (Vue-ish markup in a `template` field), edited in TemplateBuilder. Built-ins shipped as files, synced into the DB by `updatePrintTemplates` (`src/utils/printTemplates.ts:535-549`) via `ipc.getTemplates`.
- To screen: PrintView builds `PrintTemplateData` (`getPrintTemplateDocValues` `:431-445`) and renders in-page.
- To PDF/printer: `getPathAndMakePDF` (`:448-477`); `constructPrintDocument` (`:479-516`) assembles a standalone HTML string inlining **all** page CSS (`getAllCSSAsStyleElem` `:518-533`) + `@media print` reset; then `ipc.makePDF(...)` (`:462`) or `ipc.printDocument(...)` (`:470`).
- **Port note:** HTML assembly is browser-native and reusable; only the final two ipc calls are Electron. Web: `window.print()` (CSS already print-ready) or a server PDF endpoint.

---

## 7. Setup wizard & multi-file handling (local-file assumptions)

- **DatabaseSelector** is the company-file screen: lists known `.db` files (`ipc.getDbList`), native open dialog for "Existing", SetupWizard for "New", native save dialog + `setupDummyInstance` for "Demo". Every selection resolves to a **filesystem path**.
- **Switching**: `App.showDbSelector` (`src/App.vue:312-321`) clears `localStorage`, resets `lastSelectedFilePath`, `fyo.purgeCache()`. `fyo.config.get('lastSelectedFilePath')` is the persisted "current company".
- **SetupWizard** → `ipc.getDbDefaultPath(companyName)` (`App.vue:206`) → `setupInstance(filePath, ...)`.
- **To redesign for web:** the whole pick-a-file UX (`getDbList`/`getDbDefaultPath`/`checkDbAccess`, dialogs, `:memory:` special-casing) becomes "select a company/tenant" server-side.

---

## 8. i18n

- `t`/`T` from `fyo/utils/translation.ts` (tagged template literals), exposed via the render mixin.
- Loading: `src/utils/language.ts` — `setLanguageMap(lang)` (`:30-57`); non-English fetches via `ipc.getLanguageMap(code)` (`:72`) (main process reads CSV from disk). `fyo.db.translateSchemaMap(map)` re-translates schema labels.
- Switching persists to `fyo.config` then **`ipc.reloadWindow()`** (`:53-55`). Direction (ltr/rtl) from `RTL_LANGUAGES` (`src/App.vue:98-99,325-327`) drives `:dir` on `#app` + `tailwindcss-rtl`. (Arabic translations exist upstream — relevant for us.)
- **Port:** serve language maps over HTTP; replace reloadWindow with in-app re-init.

---

## 9. Styling & theming

- **Tailwind** — `tailwind.config.js` (postcss7-compat, `darkMode:'class'`, custom 11–28px font scale, Inter, `tailwindcss-rtl` `:82`).
- **Colors** — `colors.json` at repo root spread into `theme.extend.colors` (`tailwind.config.js:1-4,65`); helper `src/utils/colors.ts`.
- **Dark mode** — class-based; `src/utils/theme.ts:1-11` toggles on `<html>`; driven by `fyo.singles.SystemSettings.darkMode` (`src/App.vue:144-146`). Electron-only `.window-drag` `-webkit-app-region` rules in `src/styles/index.css:42-48`.

---

## 10. Port notes — what changes for web

**Good news:** the Electron surface is one injectable `ipc` global + three demux classes that already have non-Electron branches. Swap the transport and the entire `src/` (pages, controls, router, dialogs, charts) runs unchanged. Dialogs/toasts/charts are pure Vue; router already uses `createWebHistory`.

**Core work — the transport swap:**
1. HTTP `DatabaseDemux` (`getSchemaMap`, `createNewDatabase`/`connectToDatabase` → tenant select, `call`, `callBespoke`) against Frappe REST/RPC; flip `isElectron:false` and inject.
2. Replace `Config` with server- or localStorage-backed store.
3. Browser `ipc` shim on `window` (or refactor the 35 call sites) so boot doesn't die at `ipc.getEnv`.

**Auth/login — none exists today.** No login/session/user concept in `src/`; `App.vue` goes straight from "pick file" to Desk. A web deployment must add login/session before the selector step, and a per-user permission model (single-user desktop assumption throughout).

**File-based flows to redesign (§7):** DatabaseSelector, db-path helpers, native dialogs, `showItemInFolder`, `saveData` → tenant selection + HTTP upload/download + attachment endpoints.

**Electron-only affordances:** `WindowsTitleBar`, `.window-drag` CSS, `reloadWindow` (language/Settings/POS-close), `checkForUpdates`/`initScheduler`, `openExternalUrl` (→ `<a target=_blank>`). All cosmetic/no-op-able.

**Bottom line:** the SPA can be served by a Frappe bench largely unchanged **provided** (a) the IPC layer is swapped for HTTP at the demux seam, (b) login/session + permissions are added in front of the 3-screen boot machine, (c) the file-picker becomes tenant selection. The Vue component tree, router, form-control/schema system, reports, POS, dashboards need essentially no changes. A desktop build stays viable by keeping the `isElectron:true` path — the demux branch lets both transports coexist.

---

### Key files quick-reference

- Boot: `src/renderer.ts`, `src/initFyo.ts`, `src/App.vue`, `src/router.ts`
- IPC seam: `main/preload.ts`, `src/shims-tsx.d.ts`, `fyo/demux/{db,config,auth}.ts`, `fyo/core/dbHandler.ts`, `fyo/index.ts`
- Controls: `src/components/Controls/FormControl.vue`, `Base.vue`, `Table.vue`
- Systems: `src/utils/{search,shortcuts,sidebarConfig,printTemplates,language,theme,ui,interactive,refs,injectionKeys}.ts`
- Styling: `tailwind.config.js`, `colors.json`, `src/styles/index.css`
- Pages: `src/pages/**`
