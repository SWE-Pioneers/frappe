# Frappe Books — Desktop/Electron Layer

A map of everything desktop-coupled in Frappe Books, for a port to a Frappe bench web backend while optionally keeping a desktop build. All paths relative to the `books/` repo root.

## Architecture in one paragraph

Frappe Books is Electron with a strict process split. The **renderer** (Vue 3 app under `src/`, `fyo/`, `models/`, `reports/`) never touches Node — it has zero `require`/`fs`/`path`/`electron` imports (grep for those in `src/` returns nothing). All native work goes through a single `window.ipc` object exposed by a preload script over `contextBridge`. The **main process** (`main.ts` + `main/`) owns the filesystem, dialogs, the SQLite database (`better-sqlite3` via `backend/database/manager.ts`), printing, auto-update, telemetry creds, and a `bree` job scheduler. The renderer/main seam is a set of enums in `utils/messages.ts`. Whether IPC is live is decided by `fyo.isElectron = !!window?.ipc` (`fyo/index.ts:99`); the non-Electron path is stubbed (`DatabaseDemux` throws `NotImplemented`), so the "web" branch already exists as a placeholder.

---

## 1. `main.ts` and `main/` — boot, window, security

### Boot sequence

- `main.ts:2` installs `source-map-support` (main-process stack traces).
- `main.ts:205` `export default new Main()` — constructing the singleton runs the whole setup.
- Constructor (`main.ts:36-60`):
  - resolves app icon (dev: `./build/icon.png`; prod: `__dirname/icons/512x512.png`).
  - `protocol.registerSchemesAsPrivileged` for a custom `app://` scheme (`main.ts:41`).
  - `app.commandLine.appendSwitch('disable-http2')` and sets no-cache `autoUpdater.requestHeaders` (`main.ts:50-54`) — workaround for electron-builder update caching.
  - `registerListeners()` (`main.ts:78-84`) wires the five listener modules.
- `registerAppLifecycleListeners.ts:20` — on `app.on('ready')`: installs Vue devtools in dev, then `main.createWindow()`. `activate`/`window-all-closed` handled per-platform (`:8-18`).

### Window creation

- `createWindow()` (`main.ts:118-134`): builds `BrowserWindow`, then either `setViteServerURL()` (dev) or `registerAppProtocol()` (prod), loads the URL, opens devtools in dev, sets window listeners.
- Dev URL: `http://<VITE_HOST>:<VITE_PORT>/` default `0.0.0.0:6969` (`main.ts:136-147`).
- Prod URL: `app://./index.html`, served by `registerBufferProtocol('app', bufferProtocolCallback)` which reads files off disk from `__dirname/src/...` and maps MIME types (`main.ts:149-203`).
- `did-fail-load` retries `loadURL` (`main.ts:165-169`).

### Security settings — `getOptions()` (`main.ts:86-116`)

- `contextIsolation: true`
- `nodeIntegration: false`
- `sandbox: false`  ← note: sandbox disabled, so preload runs with full Node.
- `preload: __dirname/main/preload.js`
- `titleBarStyle: 'hidden'`, `autoHideMenuBar: true`, `frame: !isMac`.

This is the standard hardened config: the renderer cannot touch Node directly, only the curated `ipc` bridge.

### Preload — `main/preload.ts`

- Imports `electron` (`contextBridge`, `ipcRenderer`), plus `utils/config` (`electron-store`) and message enums.
- Builds one `ipc` object (`:23-278`) and `contextBridge.exposeInMainWorld('ipc', ipc)` (`:280`). Type exported as `IPC` (`:281`) and declared on `Window`/global in `src/shims-tsx.d.ts:5,16`.
- Notably `store` (`:265-277`) calls `electron-store` **directly in the preload context** (not over IPC) — the config file is read/written from the preload process synchronously.

### Registered listener modules

| Module | Registers |
|---|---|
| `main/registerIpcMainMessageListeners.ts` | `ipcMain.on` fire-and-forget window/shell channels |
| `main/registerIpcMainActionListeners.ts` | `ipcMain.handle` request/response channels (incl. DB) |
| `main/registerAutoUpdaterListeners.ts` | `electron-updater` events |
| `main/registerAppLifecycleListeners.ts` | `app` lifecycle |
| `main/registerProcessListeners.ts` | process signals + error forwarding to renderer |

Note: **no application menu is ever built** — grep for `setApplicationMenu`/`buildFromTemplate` returns nothing. `IPC_MESSAGES.OPEN_MENU` pops `Menu.getApplicationMenu()` which is `null`, so it's effectively a no-op (`registerIpcMainMessageListeners.ts:7-18`). The UI chrome is the custom `WindowsTitleBar.vue`.

---

## 2. The complete IPC surface

Three channel groups (`utils/messages.ts`):
- `IPC_MESSAGES` — `ipcRenderer.send` → `ipcMain.on` (fire-and-forget, `:2-15`)
- `IPC_ACTIONS` — `ipcRenderer.invoke` → `ipcMain.handle` (request/response, `:18-45`)
- `IPC_CHANNELS` — `webContents.send` → `ipcRenderer.on` (main → renderer push, `:48-52`)

### 2a. `IPC_MESSAGES` (send / on)

| Channel (value) | Args | Returns | What it does | Main handler | Renderer call site(s) |
|---|---|---|---|---|---|
| `open-menu` | — | — | Pops app menu (null → no-op) | `registerIpcMainMessageListeners.ts:7` | not wired in preload; unused |
| `reload-main-window` | — | — | `mainWindow.reload()` | `:20` | `preload.ts:27`; callers: `language.ts:54`, `Settings.vue:265`, `ERPNextSyncSettings.ts:62,85`, `ClosePOSShiftModal.vue:236` |
| `minimize-main-window` | — | — | `mainWindow.minimize()` | `:24` | `preload.ts:31`; `WindowsTitleBar.vue:103` |
| `maximize-main-window` | — | — | toggle maximize | `:28` | `preload.ts:35`; `WindowsTitleBar.vue:106` |
| `ismaximized-main-window` | — | replies `ismaximized-result` | query maximize state | `:34` | `preload.ts:39` (`isMaximized()` promise) |
| `ismaximized-result` | bool | — | reply channel | (sender.send) | `preload.ts:41` once-listener |
| `isfullscreen-main-window` | — | replies `isfullscreen-result` | query fullscreen | `:39` | `preload.ts:51` |
| `isfullscreen-result` | bool | — | reply channel | (sender.send) | `preload.ts:53` |
| `close-main-window` | — | — | `mainWindow.close()` | `:44` | `preload.ts:63`; `WindowsTitleBar.vue:110` |
| `open-external` | `link: string` | — | `shell.openExternal` | `:48` | `preload.ts:122` (`openLink`) & `:190` (`openExternalUrl`); callers: `SearchBar.vue:360`, `Sidebar.vue:295`, `GetStarted.vue:117`, `HowTo.vue:25`, `errorHandling.ts:286` |
| `show-item-in-folder` | `filePath: string` | — | `shell.showItemInFolder` | `:52` | `preload.ts:137`; `ui.ts:1025` (showExportInFolder) |
| `open-settings` | — | — | declared, **unused** (no handler) | — | — |

### 2b. `IPC_ACTIONS` (invoke / handle)

| Channel (value) | Args | Returns | What it does | Main handler | Renderer call site(s) |
|---|---|---|---|---|---|
| `check-db-access` | `filePath` | `boolean` | `fs.access(W_OK\|R_OK)` | `registerIpcMainActionListeners.ts:34` | `preload.ts:110`; `App.vue:185` |
| `get-db-default-path` | `companyName` | `string` | Computes `Documents/Frappe Books/<co>.books.db`, ensures `backups/`, prompts overwrite/new via dialog | `:44` | `preload.ts:174`; `App.vue:206` |
| `open-dialog` | `OpenDialogOptions` | `OpenDialogReturnValue` | `dialog.showOpenDialog` | `:91` | `preload.ts:103` (`getOpenFilePath`); `ui.ts:1060` (`getSelectedFilePath` — pick `.db` to restore/open) |
| `save-dialog` | `SaveDialogOptions` | `SaveDialogReturnValue` | `dialog.showSaveDialog` | `:98` | `preload.ts:96` (`getSaveFilePath`); `ui.ts:1068` (`getSavePath`) |
| `show-message-box` | `MessageBoxOptions` | `MessageBoxReturnValue` | `dialog.showMessageBox` | `:105` | *(handler exists but no renderer bridge method — dead surface)* |
| `show-error` | `{title, content}` | — | `dialog.showErrorBox` | `:116` | `preload.ts:193`; `errorHandling.ts:156` |
| `save-html-as-pdf` | `html, savePath, width, height` | `boolean` | Render HTML in hidden window → `printToPDF` → write file | `:123` | `preload.ts:140` (`makePDF`); `printTemplates.ts:462` |
| `print-html-document` | `html, width, height` | `boolean` | Render HTML → `webContents.print` (native dialog) | `:136` | `preload.ts:155` (`printDocument`); `printTemplates.ts:470` |
| `save-data` | `data, savePath` | — | `fs.writeFile` (utf-8) | `:143` | `preload.ts:132` (`saveData`); `ExportWizard.vue:261`, `commonExporter.ts:186`, `ImportWizard.vue:838` |
| `send-error` | `bodyJson: string` | — | POST error to Mothership | `:150` | `preload.ts:197`; `errorHandling.ts:45` |
| `check-for-updates` | — | — | `autoUpdater.checkForUpdates()` | `:154` | `preload.ts:117`; `App.vue:171` |
| `get-language-map` | `code: string` | `{languageMap, success, message}` | Load/fetch translation CSV | `:171` | `preload.ts:70`; `language.ts:72` |
| `select-file` | `SelectFileOptions` | `SelectFileReturn {name, filePath, success, data:Buffer, canceled}` | Open dialog + read file bytes | `:183` | `preload.ts:89`; `ui.ts:487` (`selectTextFile`), `AttachImage.vue:126` (attachments) |
| `get-creds` | — | `Creds {errorLogUrl, telemetryUrl, tokenString}` | Read bundled `log_creds.txt` | `:216` | `preload.ts:66`; `auth.ts:13` (demux) |
| `delete-file` | `filePath` | `BackendResponse` | `fs.unlink` | `:220` | `preload.ts:125`; `ui.ts:1031` (`deleteDb`) |
| `get-db-list` | — | `ConfigFilesWithModified[]` | Clean config file list + stat mtimes | `:224` | `preload.ts:168`; `DatabaseSelector.vue:434` |
| `get-env` | — | `{isDevelopment, platform, version}` | App env/version | `:229` | `preload.ts:181`; `renderer.ts:24` |
| `get-templates` | `posPrintWidth?` | `TemplateFile[]` | Read print template files | `:243` | `preload.ts:78`; `printTemplates.ts:536` |
| `init-scheduler` | `interval: string` | — | Start `bree` jobs | `:250` | `preload.ts:85`; `App.vue:247` |
| `send-api-request` | `endpoint, options` | JSON array | `node-fetch` proxy (bypasses CORS) | `:254` | `preload.ts:201`; `api.ts:5`, `erpnextSync.ts:880` |
| **`db-create`** | `dbPath, countryCode` | `BackendResponse` | `databaseManager.createNewDatabase` | `:265` | `preload.ts:232` → `fyo/demux/db.ts:46` |
| **`db-connect`** | `dbPath, countryCode?` | `BackendResponse` | `databaseManager.connectToDatabase` | `:274` | `preload.ts:240` → `fyo/demux/db.ts:59` |
| **`db-call`** | `method, ...args` | `BackendResponse` | **DB demux** — `databaseManager.call(method,...)` | `:283` | `preload.ts:248` → `fyo/demux/db.ts:69` |
| **`db-bespoke`** | `method, ...args` | `BackendResponse` | Bespoke query demux | `:292` | `preload.ts:256` → `fyo/demux/db.ts:79` |
| **`db-schema`** | — | `BackendResponse` (SchemaMap) | `databaseManager.getSchemaMap` | `:301` | `preload.ts:226` → `fyo/demux/db.ts:33` |

### 2c. `IPC_CHANNELS` (main → renderer push)

| Channel (value) | Payload | What it does | Emitter | Renderer listener |
|---|---|---|---|---|
| `main-process-error` | `error, more` | Forward main-process errors to renderer error handler | `registerProcessListeners.ts:21,29,35`; via `emitMainProcessError` (`backend/helpers`) | `preload.ts:213`; `registerIpcRendererListeners.ts:6` |
| `trigger-erpnext-sync` | — | Fires when a bree worker is created → renderer runs ERPNext sync | `initSheduler.ts:43` | `preload.ts:217`; `registerIpcRendererListeners.ts:29` → `syncDocumentsToERPNext` |
| `console-log` | `...args` | Main-process debug logging into renderer console | `helpers.ts:73` (`rendererLog`) | `preload.ts:221`; `registerIpcRendererListeners.ts:33` |

### The database demux specifically

The renderer holds no DB. Every DB operation is marshalled across IPC:

1. Renderer code calls `fyo.db.*` → `DatabaseHandler` → `DatabaseDemux` (`fyo/demux/db.ts`).
2. `DatabaseDemux` calls `ipc.db.call(method, ...args)` etc. (`db.ts:69`), which is `ipcRenderer.invoke('db-call', method, ...args)` (`preload.ts:248`).
3. Main handler `db-call` (`registerIpcMainActionListeners.ts:283`) → `databaseManager.call(method, ...args)`.
4. `DatabaseManager.call` (`backend/database/manager.ts:137`) validates `method` against `databaseMethodSet`, then dynamically dispatches `this.db[method](...args)` on `DatabaseCore` (`better-sqlite3` + `knex`).
5. Results wrapped by `getErrorHandledReponse` (`helpers.ts:53`) into `{data, error}`; `DatabaseDemux.#handleDBCall` (`db.ts:13`) unwraps, re-throwing serialized errors as `DatabaseError`.

So there are effectively **5 DB demux channels**: `db-schema`, `db-create`, `db-connect`, `db-call` (the generic CRUD/query demux — the heavily-trafficked one), and `db-bespoke` (named custom queries in `backend/database/bespoke.ts`). The generic `db-call` is the "one channel to rule them all" — all model reads/writes flow through it as `(methodName, ...args)`.

---

## 3. Filesystem-touching features

- **Open/Save dialogs**: `open-dialog`/`save-dialog`/`select-file` (`registerIpcMainActionListeners.ts:91,98,183`). `select-file` also reads bytes into a Buffer returned to renderer.
- **DB path + implicit backup dir**: `get-db-default-path` ensures `Documents/Frappe Books/backups/` and prompts on collision (`:44-88`).
- **SQLite backup**: automatic, main-process only — `DatabaseManager.#createBackup` (`manager.ts:182`) runs before migrations/patches, opening a **read-only** `better-sqlite3` driver and `.backup()` to `backups/<name>_<version>_<date>.books.db` (`manager.ts:193-214,229-236`). There's no explicit "restore" IPC — restore = user picks a `.db` via `getSelectedFilePath` (`ui.ts:1059`) and connects to it.
- **DB delete**: `delete-file` → `fs.unlink` (`:220`), driven by `deleteDb` (`ui.ts:1030`) with EBUSY/ENOENT/EPERM handling.
- **Export CSV/JSON**: renderer generates the string (`reports/commonExporter.ts`, `src/components/ExportWizard.vue:261`), then `save-data` writes it (`registerIpcMainActionListeners.ts:143`). Import templates also written via `save-data` (`ImportWizard.vue:838`).
- **Print-to-PDF**: `save-html-as-pdf` (`main/saveHtmlAsPdf.ts`) — writes HTML to `app.getPath('temp')`, loads it into a hidden `BrowserWindow` sized `cm*28.33` px, `printToPDF` with cm→inch page size, writes file, unlinks temp.
- **Native print**: `print-html-document` (`main/printHtmlDocument.ts`) — same temp-HTML approach, `webContents.print({silent:false})` (OS print dialog).
- **Attachments**: `AttachImage.vue:126` uses `select-file` to read image bytes into the renderer (stored in DB, not a separate FS store).
- **Template files**: `main/getPrintTemplates.ts` reads `../templates` (packaged via `extraResources`) or dev `templates/`; returns file contents + mtime + POS width/height heuristic.

---

## 4. Config, auto-update, telemetry, error logging, deep links, menu

- **electron-store**: `utils/config.ts` — `new Store<ConfigMap>()`. Used **directly in the preload** (`preload.ts:265-277`) and in main (`main/helpers.ts` for the `files` list). Renderer accesses it through `fyo/demux/config.ts` which points `this.config = ipc.store` when Electron (`config.ts:9`). This is the app-level settings/recent-files store, distinct from the SQLite DB.
- **Auto-update**: `electron-updater` via GitHub provider (`electron-builder-config.mjs` `publish: ['github']` on every platform). `registerAutoUpdaterListeners.ts`: `autoDownload=false`, `allowPrerelease=true`, `autoInstallOnAppQuit=true`; prompts before downloading a beta from a stable build (`:25-48`) and before restart-to-install (`:51-64`). Triggered by `check-for-updates` (`App.vue:171`).
- **Telemetry**: `fyo/telemetry/telemetry.ts` — `navigator.sendBeacon(telemetryUrl, {token, telemetryData})` (`:103`) from the **renderer**. Endpoint + token come from `get-creds` (main reads `log_creds.txt`). Suppressed by `skipTelemetryLogging` and an ignore list (ledger entries). Verbs logged on create/submit/cancel/delete (`fyo/model/doc.ts:905,1008,1021,1034`) and on app open/resume/close.
- **Error logging (remote)**: `main/contactMothership.ts` — `sendError` POSTs JSON to `errorLogUrl` (Frappe "Mothership") with `token <key>:<secret>` auth (`:49-60`); creds from `log_creds.txt` (`extraResources` → `../creds/log_creds.txt`, `electron-builder-config.mjs:23`). Renderer entry: `errorHandling.ts:45` → `send-error`.
- **Other remote endpoints**: translation fetch hits **GitHub API + raw.githubusercontent** (`main/getLanguageMap.ts:96,107,134`); `send-api-request` is a generic `node-fetch` proxy used for ERPNext sync (`main/api.ts`, `erpnextSync.ts:880`).
- **Deep links**: none. The only custom scheme is `app://` for serving prod renderer files (`main.ts:41,149`); no `setAsDefaultProtocolClient`/`open-url`.
- **Menu**: no application menu is built (see §1). Window chrome is custom (`WindowsTitleBar.vue`), `autoHideMenuBar: true`.

---

## 5. Build scripts, `electron-builder-config.mjs`, `vite.config.ts`

**Two independent bundlers**: esbuild for main+preload, Vite for renderer.

- `build/scripts/helpers.mjs` — shared esbuild config: entry points `main.ts` + `main/preload.ts`, `platform: 'node'`, `target: 'node20'`, `external: ['knex','electron','better-sqlite3','electron-store']` (these stay as `require` in the bundled main, shipped as real `node_modules`). A plugin strips vendor source maps.
- **Dev** (`build/scripts/dev.mjs`, `yarn dev`): sets `NODE_ENV=development`, `VITE_HOST=127.0.0.1`, `VITE_PORT=6969`; runs `yarn vite` (renderer dev server), an esbuild `context` that rebuilds main on file changes (chokidar watches `main.ts`, `main/`, `backend/`, `schemas/`), and launches `electron --inspect=5858 dist_electron/dev/main.js`. Electron loads the renderer from the Vite URL.
- **Prod** (`build/scripts/build.mjs`, `yarn build`): `updatePaths()` → `buildMainProcessSource()` (esbuild → `dist_electron/build`) → `buildRendererProcessSource()` (Vite `vite.build` with `base: '/app://'`, output `dist_electron/build/src`, then `removeBaseLeadingSlash` rewrites `/app://`→`app://` so the custom protocol resolves) → `copyPackageJson()` (trims package.json to only the 4 external deps + `main: main.js`) → `packageApp()` (electron-builder). Flags: `--nosign`, `--nopackage`.
- `vite.config.ts` — **dev-only** (per its header comment); prod uses the programmatic Vite build in `build.mjs`. Both define the same path aliases (`fyo`, `src`, `schemas`, `backend`, `models`, `utils`, `regional`, `reports`, `dummy`, `fixtures`).
- `electron-builder-config.mjs` — `appId: io.frappe.books`, `asarUnpack: **/*.node` (native better-sqlite3), `extraResources`: `log_creds.txt`→`../creds/`, `translations`→`../translations`, `templates`→`../templates`. Targets: mac (dmg, notarized, hardened, finance category), win (nsis + portable, x64/ia32), linux (deb/AppImage/rpm). All publish to GitHub.
- **Renderer node usage outside IPC**: none. Grep for `require(`/`from 'fs'`/`from 'path'`/`from 'electron'`/`node:` in `src/` → no matches. The renderer talks to the OS exclusively via `window.ipc`. `fyo/demux/config.ts:2` only *type-imports* `IPC` from `main/preload`.

---

## 6. `jobs/` — bree scheduler

`main/initSheduler.ts` creates a `Bree` instance rooted at `jobs/` (`defaultExtension: 'ts'`, runs workers via `ts-node/register`) with two jobs:

- **`jobs/triggerErpNextSync.ts`** — interval is the `init-scheduler` arg (user-configured). The worker itself just `parentPort.postMessage({type:'trigger-erpnext-sync'})`; the actual work is fired by bree's `'worker created'` event → `mainWindow.webContents.send('trigger-erpnext-sync')` (`initSheduler.ts:42-44`) → renderer runs `syncDocumentsToERPNext`. (Note: the sync work runs in the **renderer**, not the worker.)
- **`jobs/checkLoyaltyProgramExpiry.ts`** — fixed `24 hours`. Runs **in the worker process**: spins up its own `DatabaseManager`, queries `LoyaltyProgram`, marks expired ones via `knex`, then `dm.call('close')`.

---

## 7. Port notes — what each piece becomes on a Frappe web backend

The renderer already has a demux seam (`isElectron`), so the port is mostly: implement the web branch of each demux and replace `window.ipc` with an HTTP/RPC client. `DatabaseDemux`/`AuthDemux` already throw `NotImplemented` for `!isElectron` — those are the stubs to fill.

### Database (the big one)

- `db-schema`, `db-create`, `db-connect`, `db-call`, `db-bespoke` → **Frappe REST/RPC**. On bench, the DB is server-side already, so `DatabaseDemux` should call Frappe's `/api/method/...` endpoints instead of `ipc.db.*`. The generic `db-call(method, ...args)` maps cleanly onto a single RPC endpoint that dispatches server-side (or is re-expressed as Frappe doctype CRUD). `db-bespoke` → server whitelisted methods. `db-create`/`db-connect` largely disappear (one central DB, selected by session/site, not a file path).
- `check-db-access`, `get-db-list`, `get-db-default-path`, `delete-file` (DB) → replaced by **site/company selection** on the server; no per-file SQLite paths. The whole `DatabaseSelector.vue` flow becomes a site/login screen.

### Filesystem features

- `select-file` (attachments/import) → browser `<input type="file">` + upload to Frappe File doctype.
- `save-data` / export CSV/JSON → **browser download** (`Blob` + `a[download]`), or server-generated file + download URL.
- `save-html-as-pdf` → server-side PDF (Frappe's `frappe.utils.pdf`) returning a download, **or** keep client-side via a headless render. `print-html-document` → browser `window.print()`.
- `show-item-in-folder`, `open-dialog`/`save-dialog` → no equivalent; drop (browser handles download location).
- SQLite auto-backup (`manager.ts:#createBackup`) → server DB backup (bench `--backup`), not app concern.
- `get-templates` → serve templates from the server (static or a doctype).

### Config / creds / telemetry / update

- `electron-store` (`ipc.store`) → server-side user/site settings doctype, or `localStorage` for pure-UI prefs. `fyo/demux/config.ts` gets a web branch.
- `get-creds` / telemetry / error-log → creds live server-side; `send-error` and `sendBeacon` can target the same Mothership from the server (or a server proxy). Telemetry already uses `navigator.sendBeacon`, so it works in a browser if the URL/token are provided.
- `check-for-updates` / `electron-updater` → **desktop-only**; drop on web (server is updated via bench).
- `send-api-request` (CORS-bypass proxy) → on web, either call directly from the browser (same-origin) or keep a server proxy endpoint. ERPNext sync (`erpnextSync.ts`) moves naturally to a **server job**.
- Translation fetch (`getLanguageMap` hitting GitHub) → serve from the Frappe app's translation assets.

### Window / shell / process

- `reload/minimize/maximize/close/isMaximized/isFullscreen`, `WindowsTitleBar.vue` → **desktop-only**; the browser provides window chrome. `open-external` → plain `<a target="_blank">`. `main-process-error`/`console-log` push channels → drop; browser has its own error handling.

### Jobs

- `bree` + `jobs/` → **Frappe scheduler** (`scheduler_events` / background jobs). `checkLoyaltyProgramExpiry` becomes a daily server cron; `triggerErpNextSync` becomes a server-scheduled sync (no need to bounce through the renderer).

### What a future desktop build still needs

Even after a web port, a desktop build must retain: `main.ts`/`main/` boot + `BrowserWindow` + `app://` protocol; the preload `contextBridge`; `electron-updater` (auto-update); native print/PDF (`saveHtmlAsPdf.ts`, `printHtmlDocument.ts`) if you keep client-side PDF; local SQLite via `better-sqlite3` + the full `db-*` IPC demux and `DatabaseManager` (for the offline/local-file mode that is Books' main selling point); `electron-store`; dialogs and `select-file`; and the `build/scripts/*` + `electron-builder-config.mjs` packaging. The cleanest port keeps the `isElectron` demux switch as the single fork: Electron → IPC to local SQLite; web → RPC to bench.

---

### Notes / dead surface

- `IPC_MESSAGES.OPEN_SETTINGS` and `IPC_ACTIONS.GET_DIALOG_RESPONSE` (`show-message-box`) have handlers/enum entries but no live renderer bridge method in `preload.ts` — dead-ish surface, confirm before relying on them.
- The `open-menu` popup is a no-op because no application menu is ever set.
