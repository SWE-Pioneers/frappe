# The `fyo` Framework — Core Architecture

`fyo/` is Frappe Books' in-house application framework — the client-side analogue of Python's `frappe` framework. It runs **inside the renderer process** of an Electron app (Vue 3 + TypeScript). It owns the model/ORM layer, schema access, value serialization, currency math, translations, auth, config and telemetry. It does **not** own SQL: all persistence is delegated across an IPC boundary to a backend `DatabaseManager` (knex + better-sqlite3). Understanding that split is the single most important thing for the port — most of `fyo` is the "in-memory Doc/meta" half of what Frappe's Python `frappe.model.document.Document` + `frappe.db` do together.

Key correspondence up front:

| fyo concept | Frappe-framework equivalent |
|---|---|
| `Fyo` instance (`src/initFyo.ts`) | `frappe` global / `frappe.local` |
| `Doc` (`fyo/model/doc.ts`) | `frappe.model.document.Document` |
| `Schema` (`schemas/types.ts`) | DocType + DocField meta |
| `DatabaseHandler` (`fyo/core/dbHandler.ts`) | `frappe.db` (query builder facade) |
| `DatabaseDemux` → IPC → `DatabaseManager` | the SQL driver itself |
| `Converter` (`fyo/core/converter.ts`) | field type get/set casting in `frappe.model` |
| `pesa`/`Money` | no direct equivalent (Frappe uses float + `flt`/precision) |
| Single schema | Single DocType |
| child table `Doc` | child DocType row |

---

## 1. The `Fyo` class

**File: `fyo/index.ts:25` (`export class Fyo`)**

### Construction

`constructor(conf: FyoConfig = {})` at `fyo/index.ts:50`. `FyoConfig` (`fyo/core/types.ts:48`) has four optional fields: `DatabaseDemux`, `AuthDemux` (constructor injections for testing), `isElectron`, `isTest`.

The constructor:
- sets mode flags `this.isTest = conf.isTest ?? false` and `this.isElectron = conf.isElectron ?? true` (`fyo/index.ts:51-52`);
- builds the three subsystem handlers, passing `this` (back-reference) into each:
  - `this.auth = new AuthHandler(this, conf.AuthDemux)` (`:54`)
  - `this.db = new DatabaseHandler(this, conf.DatabaseDemux)` (`:55`)
  - `this.doc = new DocHandler(this)` (`:56`)
- constructs a `pesa` MoneyMaker with default currency/precision (`:58-63`);
- `this.telemetry = new TelemetryManager(this)` (`:65`);
- `this.config = new Config(this.isElectron && !this.isTest)` (`:66`).

### Subsystems it owns (fields)

- `auth: AuthHandler`, `db: DatabaseHandler`, `doc: DocHandler` — the three core handlers.
- `pesa: MoneyMaker` — money factory (rebuilt after DB connect to pick up configured precision/currency).
- `telemetry: TelemetryManager`, `config: Config`.
- `t = t`, `T = T` — translation tag functions bound directly (`:26-27`).
- `errors = errors` — the error-class module exposed as a property (`:29`).
- `currencyFormatter?`, `currencySymbols` — number-formatting cache.
- `errorLog: ErrorLog[]`, `temp?` — scratch state.
- `store` (`:226-237`) — a plain object holding app-level runtime state: `isDevelopment`, `appVersion`, `platform`, `language`, `instanceId`, `deviceId`, `openCount`, `appFlags`, cached `reports`.

### Convenience getters (delegation)

`fyo/index.ts:69-91`: `initialized`, `docs`→`doc.docs`, `models`→`doc.models`, `singles`→`doc.singles`, `schemaMap`→`db.schemaMap`, `fieldMap`→`db.fieldMap`.

### Mode flags

- `isElectron` — decides whether demuxes talk over IPC (`ipc.*`) or throw `NotImplemented` (see §3). `setIsElectron()` (`:97-103`) re-derives it from `window.ipc`.
- `isTest` — suppresses persistent config (`Config` gets an in-memory `Map`) and telemetry. Tests build their own `Fyo` (`fyo/tests/helpers.ts`), so `Fyo` is **instantiated, not a singleton** at the framework level.
- The app-wide singleton is created in **`src/initFyo.ts:8`**: `export const fyo = new Fyo({ isTest: false, isElectron: true })`. See §5.

### Lifecycle methods

- `initializeAndRegister(models, regionalModels, force)` (`:105-118`): the main bootstrap. Calls `#initializeModules()` (inits doc/auth handlers and `await this.db.init()`), `#initializeMoneyMaker()`, then `this.doc.registerModels(...)` and eagerly loads `SystemSettings`. Sets `_initialized = true`.
- `#initializeMoneyMaker()` (`:129-163`): reads `internalPrecision`/`displayPrecision`/`currency` single values from the DB and rebuilds `this.pesa`.
- `getValue(schemaName, name, fieldname)` (`:173-206`): high-level read; resolves Single vs normal, loads the doc, falls back to `db.getSingleValues`.
- `getField(schemaName, fieldname)` (`:169`): meta lookup via `fieldMap`.
- `format(value, field, doc?)` (`:93-95`): delegates to `utils/format.ts`.
- `purgeCache()` (`:208-224`) / `close()` (`:165-167`): teardown on DB switch.

**Frappe mapping:** `Fyo` ≈ the `frappe` module namespace + `frappe.local` request context. `initializeAndRegister` ≈ `frappe.init()` + controller-class registration (Frappe autoloads by DocType module path; fyo registers explicitly). `fyo.getValue` ≈ `frappe.db.get_value` / `get_single_value`.

---

## 2. The Doc / model ORM

**File: `fyo/model/doc.ts:51` — `export class Doc extends Observable<DocValue | Doc[]>`.**

`Doc` is the base "controller + document" class. Domain models subclass it (e.g. `fyo/models/NumberSeries.ts`, and the whole `models/` tree). Direct analogue of Frappe's `Document`.

### Construction & reactivity

`constructor(schema, data, fyo, convertToDocValue=true)` (`:74-92`):
- `this.fyo = markRaw(fyo)` (keeps Fyo out of Vue reactivity), `this.schema = schema`, `this.fieldMap = getMapFromList(schema.fields, 'fieldname')`.
- If `schema.isSingle`, sets `name = schemaName`.
- Calls `_setDefaults()` then `_setValuesWithoutChecks(data, convertToDocValue)`.
- **Returns `reactive(this)`** — every Doc is a Vue reactive proxy. Fyo-specific, no Frappe equivalent; it's why fields are read/written as plain properties yet the UI updates live.

Field values live as **direct instance properties** (`this[fieldname]`). `Doc extends Observable`, and `Observable.get(key)`/`set(key)` (`fyo/utils/observable.ts:31-48`) read/write `this[key]`, so `doc.get('rate')` ≡ `doc.rate`.

### Field / schema access

- `schema: Readonly<Schema>` and `fieldMap: Record<string, Field>` — per-doc meta.
- `get schemaName()` (`:94`), `get tableFields()` (`:106` — fields with `fieldtype === 'Table'`), `get quickEditFields()` (`:116`).
- Schema shape in **`schemas/types.ts`** (`Field`, `Schema`). Field flags mirror Frappe DocField closely: `required`→`reqd`/NOT NULL, `hidden`, `readOnly`, `default`, `computed` (not stored — like `is_virtual`), `meta` (db-only meta field), `filter`, `options` (Select), `target` (Link/Table target ≈ Frappe `options`). Schema flags: `isSingle`, `isChild`, `isSubmittable`, `isTree`, `isAbstract`, `extends` (abstract-schema inheritance — no direct Frappe equivalent), `naming`, `titleField`, `quickEditFields`, `keywordFields`.

### get / set

- **`set(fieldname | map, value, retriggerChildDocApplyChange?)`** (`:312-349`): the canonical mutator. If passed an object → `setMultiple`. Otherwise: guards via `_canSet`, marks `_setDirty(true)`, trims strings, validates the single field via `_validateField`, assigns `this[fieldname] = value`, then runs `_applyChange` (formulas + `change` event). For child docs it also re-runs the parent's `_applyChange`. **This is async** — a critical difference from Frappe's synchronous `doc.x = y`.
- `_canSet` (`:364-386`): blocks setting `numberSeries` after insert, blocks unknown fields, skips no-op sets via `areDocValuesEqual`.
- `setMultiple`, `setAndSync(fieldname, value)` (`:1086-1089`, `= set + sync`).

### Defaults

`_setDefaults()` (`:401-422`): per-field pre-default by type (`getPreDefaultValues` in `fyo/model/helpers.ts:29` — `[]` for Table, `pesa(0)` for Currency, `0` for Int/Float, else `null`), then overrides with a model `defaults[fieldname]` function or the schema's static `default`.

### Validation

- `_validateSync()` (`:506-509`) → `_validateMandatory()` + `_validateFields()`.
- `_validateMandatory()` (`:511-535`): self + all child rows, via `getMissingMandatoryMessage` (`helpers.ts:46`) honoring static `field.required` and dynamic model `required[fieldname]()`. Throws `MandatoryError`.
- `_validateField(field, value)` (`:549-568`): Select/AutoComplete → `validateOptions`; then `validateRequired`; then the model's `validations[fieldname]` async validator (`fyo/model/validationFunction.ts`).
- Empty controller hook `async validate() {}` (`:1132`) called via `trigger('validate')` in `_preSync`. **Exact analogue of Frappe's `def validate(self)`.**

### Lifecycle hooks (the load-bearing part for the port)

Declared as empty async methods at **`fyo/model/doc.ts:1131-1142`**, overridden by subclasses:

```
change, validate, beforeSync, afterSync, beforeSubmit, afterSubmit,
beforeRename, afterRename, beforeCancel, afterCancel, beforeDelete, afterDelete
```

Dispatched through **`trigger(event, params)`** (`:1051-1057`) — calls the same-named instance method, then `Observable.trigger` for external listeners. Each lifecycle point is both an overridable method and an event.

**Insert/update path — `sync()` (`:944-993`):**
1. `_syncing = true`; `trigger('beforeSync')`.
2. If `notInserted` → `_insert()`, else `_update()`.
3. `_notInserted = false`; `trigger('afterSync')`; fire `doc.observer` `sync:<schema>` event.
4. ERPNext-sync-queue side-effect block (app-specific).
5. `_syncing = false`.

**`_insert()` (`:891-907`):** `_setBaseMetaValues()` → `_preSync()` → `setName(this, fyo)` → `getValidDict(false, true)` → `fyo.db.insert(schemaName, validDict)` (errors wrapped by `getDbSyncError`) → `_syncValues(data)` → telemetry `Created`.

**`_update()` (`:909-923`):** `_validateDbNotModified()` (optimistic concurrency — compares `modified` timestamps, throws `ConflictError`) → `_updateModifiedMetaValues()` → `_preSync()` → `getValidDict` → `fyo.db.update` → `_syncValues`.

**`_preSync()` (`:883-889`):** `_setChildDocsIdx()` → `_setChildDocsParent()` → `_applyFormula()` (all formulas) → `_validateSync()` → `trigger('validate')`.

**`_setBaseMetaValues()` (`:603-618`):** sets `submitted=false`,`cancelled=false` (if submittable), `createdBy`, `created`, modified meta. ≈ Frappe's `owner`, `creation`, `modified`, `modified_by`, `docstatus`.

**Submit — `submit()` (`:1012-1023`):** guards on `isSubmittable`/state → `beforeSubmit` → `setAndSync('submitted', true)` → `afterSubmit` → telemetry. `cancel()` (`:1025-1036`) symmetric with `cancelled`. Note: fyo represents docstatus as **two booleans** `submitted`/`cancelled` (getters `isSubmitted`/`isCancelled` `:130-136`), vs Frappe's single integer `docstatus` (0/1/2).

**Delete — `delete()` (`:995-1010`):** removes uninserted from cache; guards `canDelete`; `beforeDelete` → `fyo.db.delete` → `afterDelete` → telemetry.

**Rename — `rename(newName)` (`:1038-1049`):** blocked if submitted; `beforeRename` → `fyo.db.rename` → set `this.name` → `afterRename`. ≈ Frappe `rename_doc`.

**Permission getters** (`:142-253`): `canDelete`, `canEdit`, `canSave`, `canSubmit`, `canCancel` — pure state machines over `notInserted`/`dirty`/`submitted`/`cancelled`/schema flags. These are UI-gating, **not** user-permission checks — fyo has no role/permission model (gap vs Frappe; see §6).

### Computed / formula fields

- Model classes declare `formulas: FormulaMap` (`:1144`): `{ formula: async (fieldname?)=>value, dependsOn?: string[] }` (`fyo/model/types.ts:32-43`).
- `_applyFormula(changedFieldname?, retrigger?)` (`:786-800`): recurses into child tables then `_applyFormulaForFields`.
- `_applyFormulaForFields` (`:837-861`): orders fields via `getFormulaSequence` (topological sort by `dependsOn`, `helpers.ts:153`), gates on `shouldApplyFormula` (`helpers.ts:86`), computes via `_getValueFromFormula`, assigns if changed.
- `computed` fields recomputed on load in `_setComputedValuesFromFormulas` (`:721-731`) and **excluded from DB writes** via `getValidDict(false, true)`.

**Frappe mapping:** `formulas` ≈ a mix of `fetch_from`, virtual fields, and imperative logic in `validate()`. Frappe has no declarative `dependsOn` reactive formula graph — on the port this becomes client form scripts + server `validate`.

### Child tables

- A Table field's value is a `Doc[]`. Child docs carry `parentdoc`, `parentFieldname`, `parentSchemaName`, `idx` (`:62-66`).
- `push`/`append`/`remove` (`:435-453`, `:424-433`) manage rows and re-index.
- `_getChildDoc` (`:472-504`) builds a child `Doc`, stamping `parent`/`parentSchemaName`/`parentFieldname` and a random `name`.
- On save, `getValidDict` serializes children recursively (`:584-588`); `Converter.#toRawValueMap` flattens them (`converter.ts:141-150`).

**Frappe mapping:** direct — `parent`, `parenttype`, `parentfield`, `idx`.

### Links

- `Link` fields hold the linked doc's `name`. `loadLinks()` (`:647-658`) resolves Link/DynamicLink fields into `this.links[fieldname]` (a full `Doc`) via `fyo.doc.getDoc`.
- `getLink(fieldname)` (`:695`) / `loadAndGetLink` (`:699`).
- `DynamicLink` (`:680-689`): target schema comes from another field (`references`) — exactly Frappe's Dynamic Link.

### Other notable methods

- `getValidDict(filterMeta, filterComputed)` (`:570-601`): the persistable `DocValueMap` (copies `pesa`, recurses children, drops nulls on singles).
- `duplicate()` (`:1091-1116`): clone for "copy" UI action.
- `getSum(tablefield, childfield)` (`:1059-1084`): pesa-safe summation over child rows.
- Static config maps (`:1151-1167`): `lists`, `filters`, `createFilters`, `defaults`, `emptyMessages`, plus static `getListViewSettings`, `getTreeSettings`, `getActions` — UI metadata on the model class (≈ Frappe list-view settings + doctype JS actions, in TS).

---

## 3. DatabaseHandler / db access layer (the bridge)

Three layers on the fyo side plus a shared abstract contract:

### 3a. The abstract contract — `utils/db/types.ts`

- **`DatabaseBase`** (`utils/db/types.ts:12-53`): abstract class declaring `insert`, `get`, `getAll`, `getSingleValues`, `rename`, `update`, `delete`, `deleteAll`, `close`, `exists`. Both the frontend `DatabaseHandler` **and** the backend `DatabaseCore` implement these signatures. `type DatabaseMethod = keyof DatabaseBase` (`:55`) is the set of method names that can cross the bridge.
- **`DatabaseDemuxBase`** (`:79-95`): abstract transport — `getSchemaMap`, `createNewDatabase`, `connectToDatabase`, `call(method, ...args)`, `callBespoke(method, ...args)`. The indirection exists so tests can plug the real `DatabaseManager` in directly, bypassing IPC.
- `GetAllOptions` (`:57-65`): `fields, filters, offset, limit, groupBy, orderBy, order` — ≈ `frappe.get_all` args. `QueryFilter` (`:67-70`) supports operator arrays — ≈ Frappe filter tuples.

### 3b. `DatabaseHandler` — `fyo/core/dbHandler.ts:34`

This is `fyo.db`. It holds `converter: Converter`, private `#demux: DatabaseDemuxBase`, `#schemaMap`, `#fieldMap`, and an `observer: Observable`.
- **Every CRUD method converts values and delegates to `#demux.call(<methodName>, ...args)`**, then fires an observer event. E.g. `insert` (`:104-119`): `converter.toRawValueMap` → `#demux.call('insert', ...)` → `observer.trigger('insert:'+schema)` → `converter.toDocValueMap`. Similarly `get` (`:122`), `getAll` (`:137`), `getAllRaw` (`:150`), `count` (`:184`), `getSingleValues` (`:160`), `update` (`:206`), `rename` (`:196`), `delete` (`:214`), `deleteAll` (`:220`), `exists` (`:232`), `close` (`:243`).
- `init()` (`:82-86`): `#schemaMap = await #demux.getSchemaMap()`; builds `#fieldMap` (`:373-382`).
- **Bespoke queries** (`:257-357`): `getLastInserted`, `getTopExpenses`, `getTotalOutstanding`, `getCashflow`, `getIncomeAndExpenses`, `getTotalCreditAndDebit`, `getStockQuantity`, `getReturnBalanceItemsQty`, `getPOSTransactedAmount` — call `#demux.callBespoke(name, ...args)`, return **raw** values. Backed by `backend/database/bespoke.ts`. **Frappe mapping:** Query Reports / `frappe.db.sql` / dedicated whitelisted methods.

### 3c. `DatabaseDemux` — `fyo/demux/db.ts:6`

The IPC transport. Every method checks `if (!this.#isElectron) throw new NotImplemented()` — in a browser build there is no DB. `call` (`:63-71`) → `ipc.db.call(...)`; `callBespoke` (`:73-81`); `getSchemaMap` → `ipc.db.getSchema()`; `createNewDatabase`/`connectToDatabase` → `ipc.db.create/connect`. `#handleDBCall` (`:13-25`) unwraps `BackendResponse`, re-throwing errors as `DatabaseError`.

### 3d. The backend side (across the IPC boundary)

`fyo.db.insert(...)` → `DatabaseHandler` → `DatabaseDemux.call('insert', ...)` → `ipc.db.call` (preload) → `main/registerIpcMainActionListeners.ts:283` → `backend/database/manager.ts:16` (`DatabaseManager extends DatabaseDemuxBase`), whose `call` (`:137`) dispatches to `DatabaseCore` (knex + better-sqlite3). `DatabaseManager` also owns `getSchemaMap()`, connect/create, and migrations/patches (`#migrate`, `runPatches`, `:61-135`).

**Interface the fyo side expects from the backend** (the contract to re-implement on Frappe):
- `getSchema()` → a `SchemaMap` (all doctype metas as JSON).
- `create(dbPath, countryCode)` / `connect(dbPath, countryCode)` → returns `countryCode`.
- `call(method, ...args)` where `method ∈ DatabaseMethod`, args/returns are **RawValueMaps** (JSON-serializable). Returns `{ data, error }`.
- `bespoke(method, ...args)` → raw aggregate results.

**Frappe mapping:** `DatabaseHandler` ≈ `frappe.db` + `frappe.client`. RawValueMap-over-IPC ≈ Frappe REST/RPC. `getSchema()` ≈ shipping DocType meta to the client (bootinfo / `frappe.get_meta`). Migrations/patches ≈ `bench migrate` + `patches.txt`.

---

## 4. Auth, Config, Telemetry, Translations, Money, Converter

### AuthHandler — `fyo/core/authHandler.ts:18`

Minimal. Private `#config` (serverURL/backend/port — defaults `sqlite`, `:27-31`) and `#session {user, token}` (`:33-36`). Exposes `user`, `session`, `config`, `init()` (no-op), `getCreds()` (`:65-71`, cached from `AuthDemux.getCreds()` → `ipc.getCreds()` in electron, else empty). **There is effectively no real authentication** — `session.user` only stamps `createdBy`/`modifiedBy`. **Biggest divergence from Frappe** (full user/session/role/permission stack). See §6.

### Config — `fyo/demux/config.ts:4`

Thin wrapper over `ipc.store` (electron-store) or an in-memory `Map` when not electron/test. Typed get/set/delete over `ConfigMap` (`fyo/core/types.ts:34-39`: `files`, `lastSelectedFilePath`, `language`, `deviceId`). ≈ desktop per-machine settings, not Frappe site config.

### Telemetry — `fyo/telemetry/telemetry.ts:35`

`TelemetryManager` fires anonymized beacons via `navigator.sendBeacon` (`:103`). `log(verb, noun, more?)` called from Doc lifecycle (`doc.ts:905,1008,1021,1034`) and app open/resume/close. Creds from `fyo.auth.getCreds()`. Ignores ledger-entry nouns (`:30-33`).

### Translations — `fyo/utils/translation.ts`

- `t` (`:90-92`) is a **template-tag function**: `` fyo.t`Value missing for ${x}` `` builds a `TranslationString` → `.s`. `T` (`:86`) returns the object (for `.ctx()`).
- `TranslationString` (`:13`) stitches literals; with a `languageMap` installed (`setLanguageMapOnTranslationString` `:94`) it substitutes translations preserving positional args (`#translate` `:37-48`).
- `translateSchema` (`:100-136`) walks the schema map translating whitelisted keys. **Mapping:** `t` ≈ `_()`/`__()`; `languageMap` ≈ CSV/PO files.

### Money / pesa

- `fyo.pesa(value)` produces a `Money` (integer-backed exact decimal). Precision/currency from `SystemSettings` (`#initializeMoneyMaker`). `Money` wrapped in `markRaw`.
- Currency fields are always `Money` in Doc-space, serialized to a **string** (`value.store`) for the DB (`converter.ts:297`).
- Formatting: `utils/format.ts` — `formatCurrency` (`:111`) uses cached `Intl.NumberFormat`; `getCurrency` (`:179`) resolves per-field currency via the model's `getCurrencies` map.
- **Frappe has no Money type** — float Currency + `precision`/`flt()` + `fmt_money`. **Real conflict for the port** (see §6).

### Converter — `fyo/core/converter.ts:26`

Serialization boundary between **DocValue** (rich JS: `Money`, `Date`, `boolean`, `Attachment`) and **RawValue** (`string | number | boolean | null`). Static `toDocValue`/`toRawValue` (`:59-103`) switch on fieldtype (`toDocCurrency`→pesa, `toDocDate`→luxon→`Date`, `toDocCheck`→bool, `toDocAttachment`→`JSON.parse`, and inverses). Map-level `toDocValueMap`/`toRawValueMap` (`:35-57`) + recursive private variants (`:105-161`) handle child-table arrays. Only `dbHandler` should call the map methods.

---

## 5. How the frontend obtains and uses the fyo instance

- **Module singleton:** `src/initFyo.ts:8` — `const fyo = new Fyo({ isTest: false, isElectron: true })`. Components `import { fyo } from 'src/initFyo'` directly (dozens of call sites). No Vue provide/inject for fyo itself.
- **Initialization:** `App.vue:231` → `initializeInstance(filePath, false, countryCode, fyo)` (`src/utils/initialization.ts:12`) → `fyo.initializeAndRegister(models, regionalModels)` — wiring the domain `models/` classes into the framework. `src/setup/setupInstance.ts:80` does the same for new-DB setup.
- **Dev exposure:** `src/renderer.ts:115` sets `window.fyo` in development.
- Every `Doc` carries `this.fyo`, so model code reaches the framework without importing the singleton.

---

## 6. Port notes (fyo → real Frappe framework)

### Maps ~1:1

- **`Schema`/`Field` → DocType/DocField** — flags line up nearly field-for-field (see 03-data-layer doc §1.6 for the full key table).
- **`Doc` lifecycle hooks → controller hooks:** `validate`→`validate`, `beforeSync`/`afterSync` ≈ `before_save`/`after_save` (or `before_insert`/`after_insert`), `beforeSubmit`/`afterSubmit` ≈ `before_submit`/`on_submit`, `beforeCancel`/`afterCancel` ≈ `before_cancel`/`on_cancel`, `beforeDelete`/`afterDelete` ≈ `on_trash`/`after_delete`, `beforeRename`/`afterRename` ≈ `before_rename`/`after_rename`. `sync()` ≈ `insert()`/`save()`.
- **Meta fields** `created/createdBy/modified/modifiedBy` → `creation/owner/modified/modified_by`.
- **Optimistic concurrency** `_validateDbNotModified` → Frappe `TimestampMismatchError`.
- **CRUD + `GetAllOptions`/`QueryFilter`** → `frappe.db` / `frappe.get_all`.
- **Child tables, DynamicLink, NumberSeries** (`fyo/model/naming.ts` ≈ naming series/`make_autoname`), **translations `t` → `_()`**, **patches → `patches.txt`**, **error classes** (`fyo/utils/errors.ts:83` `getDbError` ≈ `DuplicateEntryError`, `LinkValidationError`).

### Conflicts (need translation, not a copy)

- **docstatus:** two booleans `submitted`/`cancelled` vs Frappe's single int (0/1/2). Mechanical but pervasive.
- **Money/pesa:** exact-decimal `Money` (stored as string) vs Frappe float Currency + precision. Touches the ledger — highest-risk area of the whole port.
- **Reactive async `set` + formula DAG:** Frappe splits this into client form scripts (`fetch_from`, `frm.add_fetch`) + server `validate`. The declarative `formulas` map has no server-side Frappe home.
- **Converter:** mostly unnecessary on typed MariaDB columns, except Money-as-string, Attachment-as-JSON, Date/ISO handling.
- **Single storage:** fyo `SingleValue(parent, fieldname, value)` EAV ≈ Frappe `tabSingles` — conceptually identical, API differs.
- **DB bridge shape:** the IPC `call(method, ...RawValueMap)` demux collapses into server-side ORM + client REST/RPC on bench. `DatabaseBase` is a useful spec for the client SDK.

### No equivalent / must be added

- **Authentication, users, roles, permissions.** `AuthHandler` is a stub. The `can*` getters are UI-state gates, not permission checks — the port must add a real permission layer.
- **The `Fyo` god-object/module-singleton** and `fyo.config` (electron-store: which DB files exist) — inherently desktop.
- **Vue reactivity on Docs** (`reactive(this)`) — renderer concern only.
- **`Observable` event bus** (`db.observer`, `doc.observer`, cache-invalidation in `docHandler.ts:170-189`) — moves to frontend state management.
- **DocHandler in-memory doc cache** (`fyo/core/docHandler.ts` — `docs`, `singles`, temp-name counters, `getDoc`/`getNewDoc`) — a client-side identity map; frontend concern.
- **Bespoke aggregate queries** — become Query Reports / whitelisted methods / `frappe.db.sql`.

---

### Key file reference index

- `fyo/index.ts` — `Fyo` class, bootstrap, `getValue`, `format`, `store`.
- `fyo/core/dbHandler.ts` — `DatabaseHandler` (db facade + bespoke queries).
- `fyo/core/docHandler.ts` — `DocHandler` (model registry, doc cache).
- `fyo/core/authHandler.ts` — `AuthHandler` (session/creds stub).
- `fyo/core/converter.ts` — `Converter` (DocValue↔RawValue).
- `fyo/core/types.ts` — `DocValue`, `DocValueMap`, `RawValueMap`, `FyoConfig`, `ConfigMap`.
- `fyo/model/doc.ts` — `Doc` base ORM class (**the core**).
- `fyo/model/types.ts` — `FormulaMap`, `ValidationMap`, `Action`, `ListViewSettings`.
- `fyo/model/helpers.ts` — formula sequencing, mandatory checks.
- `fyo/model/naming.ts` — `setName`, `getSeriesNext`, `getNextId`.
- `fyo/demux/db.ts` / `auth.ts` / `config.ts` — IPC transports (the port seam).
- `fyo/utils/observable.ts`, `translation.ts`, `format.ts`, `errors.ts`.
- `fyo/telemetry/telemetry.ts` — `TelemetryManager`.
- `schemas/types.ts` — `Field`/`Schema` meta.
- `utils/db/types.ts` — `DatabaseBase`/`DatabaseDemuxBase` contracts, `GetAllOptions`, `QueryFilter`.
- `src/initFyo.ts` — the app singleton; `src/utils/initialization.ts` — `initializeInstance`.
- `backend/database/manager.ts` / `core.ts` / `bespoke.ts` — backend side of the bridge.
- `main/registerIpcMainActionListeners.ts:283-296` — IPC `DB_CALL`/`DB_BESPOKE` handlers.

**Caveat on the money path:** the exact-decimal `pesa` handling (`Money.store` string round-trip, `getSum`, currency formulas) is the highest-risk part of any Frappe port — Frappe's float+precision Currency is not bit-for-bit equivalent, so ledger math needs deliberate rounding/precision decisions rather than a mechanical translation.
