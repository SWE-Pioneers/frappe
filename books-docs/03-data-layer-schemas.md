# Frappe Books — Data Layer (schemas, backend ORM, migrations, naming)

Maps the Books home-grown ORM/schema system onto the real Frappe framework (DocTypes, MariaDB, bench) for the port. All paths relative to the `books/` repo root.

## 0. The big picture

Frappe Books ships its own miniature re-implementation of Frappe's metadata + ORM stack:

- **Schemas** (`schemas/`) are static `.json` files ≈ Frappe **DocType** definitions, but hand-authored and bundled at build time (imported as TS modules), not stored in the DB.
- **DatabaseCore** (`backend/database/core.ts`) is the ORM ≈ `frappe.db` + `frappe.model`, built on **knex** over **better-sqlite3**.
- **Migration** = diff current SQLite table columns against the built schema map and ALTER/recreate ≈ `bench migrate` + `frappe.model.sync`.
- **Patches** (`backend/patches/`) ≈ `patches.txt` + `frappe/patches/`.
- One **SQLite file per company** ≈ one **MariaDB site database** per site.

Self-description at `backend/database/core.ts:29-46`: "This is the ORM, the DatabaseCore interface ... should be replicated by the frontend demuxes and all the backend muxes."

---

## 1. `schemas/` — organization, shape, loading pipeline, inventory

### 1.1 Directory organization

Four source groups (`schemas/schemas.ts:88-199`):

| Group | Path | Constant | Role |
|-------|------|----------|------|
| **core** | `schemas/core/` | `coreSchemas` (`schemas.ts:88`) | Framework-level tables always present |
| **meta** | `schemas/meta/` | `metaSchemas` (`schemas.ts:94`) | Field mixins injected into every schema (not tables) |
| **app** | `schemas/app/` (+ `inventory/`, `inventory/Point of Sale/`) | `appSchemas` (`schemas.ts:101`) | The accounting/inventory/POS doctypes |
| **regional** | `schemas/regional/<cc>/` | `regionalSchemas` (`schemas/regional/index.ts`) | Country overrides, keyed by country code |

Types: `schemas/types.ts`. Build/merge pipeline: `schemas/index.ts`. Registry (static imports): `schemas/schemas.ts`. Tests: `schemas/tests/testSchemaBuilder.spec.ts`.

### 1.2 Schema shape (the "DocType JSON")

Top-level `Schema` — `schemas/types.ts:114-132`:

```
name, label, fields[],
isTree?, extends?, isChild?, isSingle?, isAbstract?,
tableFields?, isSubmittable?, keywordFields?, quickEditFields?,
linkDisplayField?, create?, naming?, titleField?, removeFields?
```

Field union — `schemas/types.ts:53-110`. `BaseField` (`:53-78`) carries `fieldname`, `fieldtype`, `label`, `required` (→ NOT NULL), `default`, plus UI-only flags (`hidden`, `readOnly`, `section`, `tab`, `filter`, `computed`, `meta`, etc.). Specializations:

- `OptionField` (`:81-85`) — `Select`/`AutoComplete`/`Color`, adds `options: {value,label}[]`, `allowCustom`.
- `TargetField` (`:87-92`) — `Link`/`Table`, adds `target`, `create`, `edit`.
- `DynamicLinkField` (`:94-97`) — adds `references` (an option field naming the target schema).
- `NumberField` (`:99-103`) — `Int`/`Float`, adds `minvalue`/`maxvalue`.

**Fieldtypes** (`types.ts:3-20`): `Data, Select, Link, Date, Datetime, Table, AutoComplete, Check, AttachImage, DynamicLink, Int, Float, Currency, Text, Color, Button, Attachment`.

**Naming** — `'autoincrement' | 'random' | 'numberSeries' | 'manual'` (`types.ts:112`).

Worked examples: `schemas/app/Account.json` (tree/links/select/quickEditFields); `schemas/app/Invoice.json` (`isAbstract`, `isSubmittable`) + `schemas/app/SalesInvoice.json` (`extends:"Invoice"`, `naming:"numberSeries"`); `schemas/app/InvoiceItem.json` (`isChild`, `isAbstract`).

### 1.3 Meta mixins (`schemas/meta/`)

Field bundles merged into every schema at build (`schemas/index.ts:94-125`):

- `meta/base.json` — `createdBy, modifiedBy, created, modified` (all `meta:true`). ≈ `owner, modified_by, creation, modified`.
- `meta/child.json` — `idx, parent, parentSchemaName, parentFieldname`. ≈ `idx, parent, parenttype, parentfield`.
- `meta/submittable.json` — `submitted, cancelled` (Check). ≈ `docstatus` (0/1/2), but **two booleans instead of one integer**.
- `meta/tree.json` — `lft, rgt` (nested set; Books omits `old_parent`).

Selection (`index.ts:103-120`): tree+submittable → both; tree → tree; submittable → submittable; child → child; else → base. Singles get **no** meta fields (`index.ts:105-107`).

### 1.4 Build / merge pipeline (`schemas/index.ts`)

`getSchemas(countryCode, rawCustomFields)` (`index.ts:26-41`), in order:

1. `getCoreSchemas()` (`:149-153`) — clone core → resolve abstract/extends → clean.
2. `getAppSchemas(countryCode)` (`:155-164`):
   a. `getRegionalCombinedSchemas` (`:239-257`) — **regional override merge**: deep-merge fields via `getCombined` (`:181-205`).
   b. `getAbstractCombinedSchemas` (`:207-237`) — resolve `extends` (Subclass + Abstract → Complete).
3. Merge app+core (`:33`).
4. `addMetaFields` (`:94`); `addNameField` (`:133-147`, adds the `name` PK if absent, `NAME_FIELD` `:18-24`); `addTitleField` (`:127-131`, default `titleField='name'`).
5. `removeFields` (`:51-77`).
6. `setSchemaNameOnFields` (`:43-49`).
7. `addCustomFields` (`:270-360`) — appends user custom fields loaded from the `CustomField` table at runtime.
8. `deepFreeze` (`:79-92`).

**Regional wiring**: `schemas/regional/index.ts` exports `{ in: IndianSchemas, ch: SwissSchemas }`. India bundles `AccountingSettings` (adds `gstin`), `Address`, `Party`. Country code from `SystemSettings.countryCode` (`backend/database/core.ts:68-89`), default `'in'`.

### 1.5 FULL schema inventory (grouped)

- **Core/framework** (`schemas/core/`): `SingleValue`, `SystemSettings`, `PatchRun`, `CustomForm`, `CustomField`.
- **Meta mixins** (not tables): `base`, `child`, `submittable`, `tree`.
- **Accounting**: `Account` (tree), `AccountingLedgerEntry`, `AccountingSettings` (single), `JournalEntry` (submittable), `JournalEntryAccount` (child), `Tax`, `TaxDetail` (child), `TaxSummary` (child), `Currency`, `Defaults` (single), `NumberSeries`.
- **Party/CRM/Items**: `Party`, `Address`, `Lead`, `ItemEnquiry`, `Item`, `ItemGroup` (tree), `UOM`, `UOMConversionItem` (child).
- **Sales/Purchase**: `Invoice` (abstract), `InvoiceItem` (abstract child), `SalesInvoice`, `SalesInvoiceItem`, `PurchaseInvoice`, `PurchaseInvoiceItem`, `SalesQuote`, `SalesQuoteItem`.
- **Payments**: `Payment` (submittable), `PaymentFor` (child), `PaymentMethod`.
- **Pricing/Promotions**: `PriceList`, `PriceListItem` (child), `PricingRule`, `PricingRuleItem` (child), `PricingRuleDetail` (child), `CouponCode`, `AppliedCouponCodes` (child), `CollectionRulesItems` (child), `LoyaltyProgram`, `LoyaltyPointEntry`.
- **Inventory** (`schemas/app/inventory/`): `InventorySettings` (single), `Location`, `StockLedgerEntry`, `StockMovement` (submittable), `StockMovementItem` (child), `StockTransfer`, `StockTransferItem` (child), `Shipment`, `ShipmentItem` (child), `PurchaseReceipt`, `PurchaseReceiptItem` (child), `SerialNumber`; plus `Batch`, `BatchSeries`, `SerialNumberSeries`.
- **Point of Sale**: `POSSettings` (single), `POSProfile`, `POSOpeningShift`, `POSClosingShift`, `POSShiftAmounts`, `OpeningAmounts`, `OpeningCash`, `ClosingAmounts`, `ClosingCash`, `CashDenominations`, `DefaultCashDenominations` (children as noted).
- **ERPNext sync/integration**: `ERPNextSyncSettings` (single), `ERPNextSyncQueue`, `FetchFromERPNextQueue`, `IntegrationErrorLog`.
- **Print/UI/setup**: `PrintSettings` (single), `PrintTemplate`, `SetupWizard` (single), `GetStarted` (single), `Misc` (single), `Color`.
- **Regional overrides**: `in/` → `AccountingSettings`, `Address`, `Party`; `ch/` → `AccountingSettings`.

### 1.6 Schema-JSON key → Frappe DocType JSON key mapping

| Books key | Frappe key | Notes |
|---|---|---|
| `name` (schema) | doctype name | schema `name` = table + doctype name |
| `label` | `label` | |
| `field.fieldname` | `fieldname` | direct |
| `field.fieldtype` | `fieldtype` | value mapping below |
| `field.required` | `reqd` | |
| `field.hidden` | `hidden` | |
| `field.readOnly` | `read_only` | |
| `field.default` | `default` | |
| `field.description` | `description` | |
| `field.options` (Select) | `options` | **Books `{value,label}[]` → Frappe newline-delimited text** |
| `field.target` (Link/Table) | `options` | Frappe overloads `options` |
| `field.references` (DynamicLink) | `options` | points at the Link fieldname |
| `field.section` / `field.tab` | Section Break / Tab Break rows | Frappe layout is positional field rows |
| `field.minvalue`/`maxvalue` | — | validate in controller |
| `naming` | `autoname` | `numberSeries`→`naming_series:`, `autoincrement`→`autoincrement`, `random`→`hash`, `manual`→`Prompt`/`field:` |
| `isChild` | `istable` | |
| `isSingle` | `issingle` | |
| `isSubmittable` | `is_submittable` | |
| `isTree` | `is_tree` (+ NestedSet) | |
| `titleField` | `title_field` | |
| `keywordFields` | `search_fields` | approx |
| `quickEditFields` | — | Books UI-only |
| `extends` / `isAbstract` | **no equiv** | flatten at conversion time |
| `removeFields` | **no equiv** | build-time stripping |
| `tableFields` | ~child `in_list_view` | |
| `linkDisplayField` | — | |
| `field.computed` | `is_virtual` | not stored |
| `field.meta` | implicit | Frappe standard fields aren't flagged |
| `field.filter/bold/groupBy/sub_label/rows/getOptions/invisible/placeholder` | mostly none (`placeholder` exists in newer Frappe) | UI-only |

**Fieldtype values:** `Data→Data`, `Select→Select`, `Link→Link`, `Date→Date`, `Datetime→Datetime`, `Table→Table`, `AutoComplete→Autocomplete/Data`, `Check→Check`, `AttachImage→Attach Image`, `DynamicLink→Dynamic Link`, `Int→Int`, `Float→Float`, `Currency→Currency`, `Text→Small Text/Text`, `Color→Color`, `Button→Button`, `Attachment→Attach`.

---

## 2. `backend/` — the database core

### 2.1 knex / better-sqlite3 wrapping

`DatabaseCore` (`backend/database/core.ts:48`): knex with `client: 'better-sqlite3'`, `connection.filename = dbPath` (default `:memory:`), `useNullAsDefault: true` (`:55-66`). `connect()` (`:95-98`) runs `PRAGMA foreign_keys=ON`. Column type mapping `sqliteTypeMap` (`backend/helpers.ts:7-28`) — notably **`Currency` maps to `text`** (decimals stored as strings, cast at query time: `bespoke.ts:46` `cast(debit as real)`).

Call sequence (`core.ts:36-42`): `new DatabaseCore(path)` → `connect()` → `setSchemaMap()` → `migrate()` → ORM calls → `close()`.

Orchestrator: `DatabaseManager` (`backend/database/manager.ts:16`, singleton `:239`) — schema building, custom fields, migration, patches, backups. `call(method, ...args)` (`:137-153`) gated by `databaseMethodSet` (`helpers.ts:42-53`). `callBespoke` (`:155-167`) → `BespokeQueries`.

### 2.2 CRUD API surface (`DatabaseCore`)

| Method | Location | Notes |
|---|---|---|
| `insert` | `core.ts:195-209` | single→`#updateSingleValues`; else `#insertOne` + children |
| `get` | `core.ts:211-264` | single→`#getSingle`; loads children |
| `getAll` | `core.ts:266-299` | filters/offset/limit/groupBy/orderBy; default orderBy=`created` desc |
| `update` | `core.ts:353-363` | parent then children (upsert + delete-missing) |
| `delete` | `core.ts:365-380` | doc + all child rows by `parent` |
| `deleteAll` | `core.ts:301-305` | bulk delete by filters |
| `exists` | `core.ts:173-193` | |
| `rename` | `core.ts:342-351` | **only updates `name`; TODOs note links/childtables NOT re-pointed** |
| `getSingleValues` | `core.ts:307-340` | reads EAV `SingleValue` rows |

Filter DSL (`#applyFiltersToBuilder`/`#getFiltersArray`, `core.ts:489-558`): `{status:"Open"}`, `{name:["like","apple%"]}`, `{date:[">=",d1,"<=",d2]}`, `in` with null handling.

RPC allow-list `databaseMethodSet` (`helpers.ts:42-53`): `insert, get, getAll, getSingleValues, rename, update, delete, deleteAll, close, exists`.

### 2.3 Transactions

**No explicit transaction wrapper.** Parent+children writes (`#insertOrUpdateChildren` `core.ts:943-985`) and table rebuilds (`prestigeTheTable` `core.ts:404-420`) run as sequential awaited knex statements, not inside `knex.transaction()`. FK enforcement via PRAGMA, toggled OFF during rebuilds. **Port implication:** Frappe wraps each request in a transaction automatically; review code that relied on partial writes.

### 2.4 Table creation & migration (schema→DDL)

`migrate(config)` (`core.ts:104-142`):

1. `#getCreateAlterList()` (`:144-171`) — per non-single schema: table missing → create; else `#getColumnDiff` (`:560-582`) + `#getNewForeignKeys` (`:584-597`) → alter.
2. Singles via `#getSinglesUpdateList` (`:865-892`).
3. Short-circuits if nothing to do.
4. `config.pre?.()` → create → alter → `#initializeSingles` → `config.post?.()`.

**Create**: `#createTable`→`#runCreateTableQuery` (`:663-677`) with `#buildColumnForTable` (`:599-641`): type from `typeMap`, `name` = `primary()`, `defaultTo`, `notNullable()`, `Link` fields get `foreign().references('name').inTable(target).onUpdate('CASCADE').onDelete('RESTRICT')` (`:631-640`). `Table` fields skipped (children live in their own tables).

**Alter**: added columns via `knex.schema.table` (`#alterTable` `:643-661`); dropped via `#dropColumns` (`:398-402`); **new FKs** require **`prestigeTheTable`** (`:404-420`) — the SQLite ALTER hack: create `__<table>` with the new shape, `batchInsert` all rows, drop original, rename (FKs OFF during swap).

Only non-`computed` fields whose fieldtype is in `typeMap` are materialized (`:565-569`, `:665-667`).

### 2.5 Patch / migration system

`backend/patches/index.ts` — ordered registry (≈ `patches.txt`), each `{name, version, patch, priority?}`. Current patches: `testPatch`, `updateSchemas` (priority 100, `beforeMigrate`), `addUOMs`, `fixRoundOffAccount`, `createInventoryNumberSeries`, `setPaymentReferenceType`, `fixLedgerDateTime`, `fixItemHSNField`, `createPaymentMethods`.

Orchestration (`DatabaseManager.#executeMigration` `manager.ts:74-94`):

1. Read app version from `SingleValue` (`SystemSettings.version`) (`:216-227`).
2. `#getPatchesToExecute(version)` (`:96-135`): runs if not-yet-run and `version <= patch.version`, OR previously `failed` in a different version. Sorted by priority; split `pre` (`beforeMigrate`) / `post`.
3. If patches exist → `#createBackup` (`:182-214`, read-only better-sqlite3 `.backup()` to `backups/<file>_<version>_<date>.books.db`).
4. `runPatches(pre)` → `db.migrate({pre})` → `runPatches(post)`.

`runPatch` (`backend/database/runPatch.ts:18-36`) records outcome in `PatchRun` (`makeEntry` `:38-60`); failures logged with `failed:true` and re-run later. `PatchRun` presence is also the "first run" sentinel (`manager.ts:169-180`).

`backend/patches/updateSchemas.ts` is the heavyweight example (0.4.3→0.5.0 rewrite): builds a fresh destination DB (`getDestinationDM` `:343-356`), copies+transforms every table (renames `creation→created`, `owner→createdBy`, `parenttype→parentSchemaName`, `parentfield→parentFieldname` — `:12-17`; note these are **the Frappe names**, evidence Books forked from Frappe conventions), `notNullify`s required fields (`:375-396`), swaps files (`replaceDatabaseCore` `:81-93`).

**Port mapping:** registry → `patches.txt` (`beforeMigrate` → `[pre_model_sync]`); `execute(dm)` → patch `execute()`; `PatchRun` → Patch Log; `#createBackup` → bench auto-backup; schema diff/ALTER → `bench migrate`.

---

## 3. Singles and child tables — storage

### 3.1 Singles (EAV, one shared table)

Single schemas (`SystemSettings`, `AccountingSettings`, `InventorySettings`, `Defaults`, `POSSettings`, `PrintSettings`, `GetStarted`, `Misc`, `SetupWizard`) get **no table** — stored as rows in **`SingleValue`** (`schemas/core/SingleValue.json`): `parent` (= single's schema name), `fieldname`, `value` (text).

- Read: `#getSingle` (`core.ts:769-788`) pivots rows into a field map.
- Write: `#updateSingleValues`/`#updateSingleValue` (`:808-848`) upsert per-field; `#insertSingleValue` (`:850-863`).
- Defaults/new fields back-filled by `#initializeSingles` (`:865-920`) — single "migrations" need no ALTER.

**Maps 1:1 to Frappe `tabSingles(doctype, field, value)`.**

### 3.2 Child tables (real table per child doctype)

Child schemas get their own table (e.g. `SalesInvoiceItem`). Linkage via `idx, parent, parentSchemaName, parentFieldname` (from `meta/child.json`). Parent's `Table` field is virtual (no column). Upsert path `#insertOrUpdateChildren` (`core.ts:943-985`) + `#prepareChild` (`:725-739`) + delete-missing (`#runDeleteOtherChildren` `:713-723`). Read via `#loadChildren` (`:746-759`) ordered by `idx`.

**Maps directly to Frappe child tables**: `parentSchemaName`→`parenttype`, `parentFieldname`→`parentfield`.

---

## 4. `fixtures/`, `dummy/`, `translations/`

### 4.1 `fixtures/`

- `fixtures/countryInfo.json` — per-country metadata (`code, currency, fiscal_year_start/end, locale, timezones...`). ≈ `frappe/geo/country_info.json`.
- `fixtures/verified/*.json` — country **Charts of Accounts** (`ae, ca, ch, fr, gt, hu, id, in, mx, ni, nl, sg`) + `standardCOA.json`. Loaded at setup by `src/setup/createCOA.ts` (nested tree, leaf attrs `accountType, accountNumber, rootType, isGroup`). ≈ ERPNext's `chart_of_accounts/verified/*.json` — near-identical format, clean port.

### 4.2 `dummy/` (demo data)

`dummy/index.ts` — `setupDummyInstance(dbPath, fyo, years, baseCount, notifier)` (`:25`) builds demo company "Flo's Clothes" (India, INR): static items/parties from `dummy/items.json`/`parties.json`, randomized transactions (`generateDynamicEntries`). Helpers: seasonality/flow in `dummy/helpers.ts`. Very relevant for our sales-demo model.

### 4.3 `translations/`

Plain **CSV** per language: `ar, ca-ES, da, de, es, fa, fr, gu, hi, id, ko, nl, np, pt, sq, sv, tr, zh-CN, zh-Hant`. Format `"source","translation",context` with `${0}` positional placeholders (template-literal `t` tags) vs Frappe's `{0}`. **Arabic exists upstream.** Loader: `src/utils/language.ts`. Auto-translated schema keys: `label`, `description`, `placeholder` (`schemas/README.md:42-43`). Port: rewrite placeholders `${0}`→`{0}`; otherwise close to Frappe CSV format.

---

## 5. Naming / numbering series

Driven by `schema.naming`, implemented in `fyo/model/naming.ts`:

- `setName(doc, fyo)` (`:30-58`): `manual` → none; `autoincrement` → `getNextId` (`:60-63`, `getLastInserted+1` zero-padded to 9, via `bespoke.ts:17-31` `cast(name as int)`); has `numberSeries` field → `getSeriesNext` (`:65-85`); `isSingle` → schemaName; else → `getRandomString()` (`utils/index.ts:29-33`).
- `NumberSeries` doctype (`schemas/app/NumberSeries.json`, PK = prefix) stores `start`, `padZeros` (default 4), `referenceType`, `current`. Model `fyo/models/NumberSeries.ts`: `next()` increments `current`, collision check, returns `prefix + current.padStart(padZeros,'0')`. Invalid chars `/ ? & = %` rejected. Auto-create via `createNumberSeries` (`naming.ts:87-105`).
- Default prefixes: `PAY-`, `JV-`, `SINV-`, `PINV-`, `SQUOT-` (`updateSchemas.ts:19-25`, field defaults e.g. `SalesInvoice.json:15`).

**Port:** `numberSeries` → Frappe `naming_series` + `tabSeries`; Books' per-series `start`/`padZeros` are richer than the fixed `#####` mask — needs series masks (e.g. `SINV-.#####`) or custom autoname.

---

## 6. Port notes

### 6.1 Converter checklist (schema JSON → DocType JSON)

1. Flatten `options:[{value,label}]` → newline `options`.
2. `target` → DocField `options`; `references` → `options`.
3. `section`/`tab` attrs → explicit Section/Tab Break rows.
4. `naming` → `autoname` (§5).
5. Flatten `extends`/`isAbstract` at conversion.
6. Regional merges → Custom Fields / Property Setters in a regional module (no runtime country-merge in Frappe).
7. `submitted`+`cancelled` → `docstatus`; rewrite all queries `submitted=1 and cancelled=0` → `docstatus=1` (`bespoke.ts:67-69,194-197`).
8. Drop meta mixins (Frappe injects standard fields); `parentSchemaName`/`parentFieldname` → `parenttype`/`parentfield`.
9. Books `CustomField` rows → `tabCustom Field`.
10. Drop/relocate: `quickEditFields`, `linkDisplayField`, `removeFields`, UI-only field flags; `computed` → `is_virtual`.

### 6.2 Storage differences

| Concern | Books | Frappe |
|---|---|---|
| DB engine | better-sqlite3 file | MariaDB per site |
| Granularity | one `.db` per company | one site DB |
| Table names | schema name verbatim | `tab` prefix |
| Singles | `SingleValue` EAV | `tabSingles` — direct match |
| Child rows | per-child table, `parent` FK | `tab<Child>` — direct match |
| PK | `name` text `primary()` | `name` varchar(140) — direct match |
| Currency | **TEXT**, `cast(... as real)` | `decimal(21,9)` |
| FKs | real SQLite FKs (CASCADE/RESTRICT) | app-layer link integrity, no DB FKs |
| Backups | copy `.db` file | `bench backup` |

### 6.3 SQLite-specific behavior that breaks on MariaDB

1. **`prestigeTheTable`** rebuild hack (`core.ts:404-420`) — delete; native ALTER.
2. **PRAGMAs** (`foreign_keys`, `table_info`, `foreign_key_list` — `core.ts:97,410,419,423-425,443-448`) → `information_schema` / Frappe meta.
3. **`sqlite_schema`/`sqlite_master`** (`core.ts:431-434`, `manager.ts:175`) → `information_schema.tables`.
4. **SQLite date functions** in bespoke SQL — `strftime('%Y-%m', date)` (`bespoke.ts:78,100,116`), `datetime(date)` (`:171-176`) → `DATE_FORMAT`/native datetime. Every query in `bespoke.ts` needs dialect review.
5. **Currency-as-text casts** (`bespoke.ts:23,46,100,116,137`; `cast(name as int)` for autoincrement) — unnecessary with decimal columns / real naming.
6. `useNullAsDefault` — knex/SQLite-only.
7. Dual-boolean `submitted/cancelled` → `docstatus`.
8. SQLite dynamic typing hides type mismatches; MariaDB is strict — text-vs-decimal and string-date comparisons surface as errors.
9. `getRandomString` naming → standardize on Frappe `hash`.
10. No transactions today (§2.3) — Frappe's automatic transactions change failure semantics; audit parent/child write sequences.

---

### Key files reference

- Schema types: `schemas/types.ts` · build/merge: `schemas/index.ts` · registry: `schemas/schemas.ts` · mixins: `schemas/meta/*.json`
- ORM/DDL/migration: `backend/database/core.ts` · manager (patches/backups/version/RPC): `backend/database/manager.ts` · patch runner: `backend/database/runPatch.ts` · patch registry: `backend/patches/index.ts` (big example: `updateSchemas.ts`)
- Type map + RPC allow-list: `backend/helpers.ts` · analytics SQL: `backend/database/bespoke.ts`
- Naming: `fyo/model/naming.ts`, `fyo/models/NumberSeries.ts`
- Seed data: `fixtures/countryInfo.json`, `fixtures/verified/*.json`, `src/setup/createCOA.ts` · demo: `dummy/index.ts`
- Translations: `translations/*.csv`, `src/utils/language.ts`

Skipped: the ~90 individual app schema JSONs were sampled (representative ones per category), not exhaustively read — open them individually when the port needs field-level fidelity for a specific doctype.
