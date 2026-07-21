# Frappe Books — Business-Logic Layer (models, ledger, inventory, reports)

Scope: `models/`, `reports/`, `regional/`, `templates/`, plus the SQL layer in `backend/database/bespoke.ts` that the models depend on. Frappe Books is built on its own in-house micro-ORM ("fyo") — every model extends `fyo/model/doc.Doc`, schemas are JSON, money is the `pesa` library (integer-cents `Money`), and the DB is SQLite via knex. This matters for the port: **the accounting/domain logic lives entirely in these TS model classes as lifecycle hooks (`validate`, `beforeSubmit`, `afterSubmit`, `afterCancel`, `beforeSync`, `formulas`), not in the schema.**

---

## 1. `models/` full inventory

Registered in `models/index.ts:62` (the `models` map) and `models/index.ts:128` (`getRegionalModels`). "Backs schema" = the `schemaName` string the class is registered under.

### 1.1 Setup / company / settings (singles)
| Class | File | Notes |
|---|---|---|
| `SetupWizard` | `models/baseModels/SetupWizard/SetupWizard.ts:58` | Company creation wizard. `formulas` derive `fiscalYearStart/End`, `currency`, `chartOfAccounts` from `country` (`:62`). `getCOAList()` (`:22`) enumerates bundled charts of accounts (ae, ca, in, fr, sg…). |
| `AccountingSettings` | `models/baseModels/AccountingSettings/AccountingSettings.ts:16` | Master feature-flag single: `enableInventory, enableDiscounting, enablePriceList, enablePricingRule, enableCouponCode, enableLoyaltyProgram, enableInvoiceReturns, enableERPNextSync, enablePartialPayment, enableitemGroup`. Holds `discountAccount, roundOffAccount, writeOffAccount, gstin, fiscalYearStart/End`. `change()` (`:91`) auto-creates the discount account and cascades POS-without-inventory settings. Flags are latch-once read-only (`readOnly` `:55`). |
| `InventorySettings` | `models/inventory/InventorySettings.ts:5` | `stockInHand, stockReceivedButNotBilled, costOfGoodsSold` accounts (used by stock ledger posting), `defaultLocation`, `enableBatches/SerialNumber/UomConversions/Barcodes/StockReturns/PointOfSale`. |
| `Defaults` | `models/baseModels/Defaults/Defaults.ts` | Default number series, terms, auto-payment/auto-stock-transfer accounts/locations (`salesPaymentAccount`, `shipmentLocation`, etc.). |
| `PrintSettings`, `Misc` | `models/baseModels/PrintSettings/PrintSettings.ts`, `models/baseModels/Misc.ts` | Print/company branding; misc single. |

### 1.2 Chart of accounts
- `Account` — `models/baseModels/Account/Account.ts:16`. Tree (`parentAccount`, NestedSet `lft/rgt` present but unused — `:47`). `rootType` ∈ Asset/Liability/Income/Expense/Equity (`types.ts`). `get isDebit` (`:21`) = Asset|Expense → the sign convention used everywhere. `accountType` inherited from parent in `beforeSync` (`:57`). Tree view root label = company name.
- `AccountingLedgerEntry` — see §2.

### 1.3 Parties / CRM
- `Party` — `models/baseModels/Party/Party.ts:19`. Roles Customer/Supplier/**Both**. `updateOutstandingAmount()` (`:26`) recomputes from submitted invoices; `updateLoyaltyPoints()` (`:59`); `defaultAccount` formula picks `Debtors`/`Creditors` (`:123`). `afterSync/afterDelete` flip linked `Lead` status (`:187`).
- `Lead` — `models/baseModels/Lead/Lead.ts` (CRM lead, converts to Party).
- `Address` — `models/baseModels/Address/Address.ts` (+ regional India variant, §5).
- `ItemEnquiry` — `models/baseModels/ItemEnquiry/ItemEnquiry.ts` (POS "item not found" capture).

### 1.4 Items / groups / UOM
- `Item` — `models/baseModels/Item/Item.ts:23`. `trackItem` (inventory), `hasBatch`, `hasSerialNumber`, `uomConversions`, `itemType` Product/Service. `formulas` derive `incomeAccount`/`expenseAccount` (tracked items → `stockReceivedButNotBilled`, else COGS account) (`:37`). `afterSync` auto-creates `SerialNumberSeries`/`BatchSeries` docs (`:114`). Validations: barcode 12 digits, HSN 4–8 digits.
- `ItemGroup` — `models/baseModels/ItemGroup/ItemGroup.ts` (carries HSN code).

### 1.5 Sales
- `Invoice` (abstract base) — `models/baseModels/Invoice/Invoice.ts:81`. **The single largest business-logic file (~2090 lines).** Extends `Transactional`. Owns: tax computation (`getTaxItems` `:420`, `getTaxSummary` `:463`), discounting (item/invoice, before/after tax — `getGrandTotal` `:537`, `getDiscountAmount` `:584`), multi-currency (`exchangeRate`/`baseGrandTotal` formulas `:1190`), outstanding-amount tracking, returns/credit-notes (`getReturnDoc` `:738`, `isReturn` `:188`), loyalty redemption, coupons, pricing rules + free items (`getPricingRule` `:1923`, `applyProductDiscount` `:1807`), auto-payment (`getPayment` `:1445`) and auto-stock-transfer (`getStockTransfer` `:1506`). `getPosting()` is abstract.
- `SalesInvoice` — `models/baseModels/SalesInvoice/SalesInvoice.ts:20`. Implements `getPosting()` (`:23`, see §2), loyalty-point validation.
- `SalesInvoiceItem` / `InvoiceItem` (base) — row-level rate/qty/amount/discount/tax formulas, `itemDiscountedTotal`, `itemTaxedTotal`.
- `SalesQuote` / `SalesQuoteItem` — `models/baseModels/SalesQuote/SalesQuote.ts`. A quote is an `Invoice` subclass with `isQuote` short-circuiting posting/loyalty (`Invoice.ts:122`, `:199`); converts to SalesInvoice.

### 1.6 Purchases
- `PurchaseInvoice` — `models/baseModels/PurchaseInvoice/PurchaseInvoice.ts:10`. `getPosting()` (`:46`) mirrors Sales with reversed Dr/Cr. `beforeSubmit` auto-creates batches (`:13`).
- `PurchaseInvoiceItem` — `models/baseModels/PurchaseInvoiceItem/PurchaseInvoiceItem.ts`.

### 1.7 Payments
- `Payment` — `models/baseModels/Payment/Payment.ts:36`. Extends `Transactional`. Receive/Pay, `for[]` (PaymentFor allocation rows), write-off, partial-payment gating (`beforeSync` `:480`), payment tax (`getTaxSummary` `:250`), account auto-selection by party role + payment method (`formulas` `:615`). `getPosting()` `:330`. Updates reference & party outstanding on submit/cancel (`:456`, `:513`).
- `PaymentFor` — child: which invoice + amount.
- `PaymentMethod` — Cash/Bank + linked account.

### 1.8 Journal entries
- `JournalEntry` — `models/baseModels/JournalEntry/JournalEntry.ts:21`. `accounts[]` child rows; `getPosting()` (`:24`) simply debits/credits each row (manual double entry).
- `JournalEntryAccount` — child rows.

### 1.9 Inventory (see §3 for engine)
Stock docs (all under `models/inventory/`): `StockMovement`+`StockMovementItem` (material issue/receipt/transfer/manufacture, non-transactional — no GL), `Shipment`+`ShipmentItem`, `PurchaseReceipt`+`PurchaseReceiptItem` (these two post GL), `StockLedgerEntry`, `Location`, `Batch`, `SerialNumber`. Base classes: `Transfer` (`Transfer.ts:7`), `StockTransfer` (`StockTransfer.ts:34`), `TransferItem`/`StockTransferItem`. Engine: `StockManager.ts`, `stockQueue.ts`.

### 1.10 POS
Under `models/inventory/Point of Sale/`: `POSSettings`, `POSProfile` (`models/baseModels/POSProfile/PosProfile.ts`), `POSOpeningShift`, `POSClosingShift` (cash reconciliation via `closingCashAmount`), `OpeningCash`/`ClosingCash`, `OpeningAmounts`/`ClosingAmounts`, `CashDenominations`/`DefaultCashDenominations`. POS reuses `SalesInvoice` with `isPOS` flag (see `bespoke.getPOSTransactedAmount` `bespoke.ts:412`).

### 1.11 Price lists / pricing rules
- `PriceList` + `PriceListItem` — sales/purchase, per-item rates.
- `PricingRule` — `models/baseModels/PricingRule/PricingRule.ts:15`. Price vs Product (free-item) discount, coupon-based, recursive free items, qty/amount thresholds, validity dates, priority. Applied in `Invoice.getPricingRule/applyProductDiscount`.
- `PricingRuleItem` / `PricingRuleDetail` — matching + applied-detail child tables.

### 1.12 Taxes
- `Tax` — `models/baseModels/Tax/Tax.ts:4`. **Essentially empty** — just a named doc; the tax `details[]` (account + rate, optional `payment_account` for cash-basis tax) are child rows consumed by `Invoice.getTaxItems`.
- `TaxSummary` — computed per-invoice tax breakup rows.

### 1.13 Loyalty
- `LoyaltyProgram` — collection rules/tiers, conversion factor, expiry, maximumUse/used.
- `LoyaltyPointEntry` — ledger of earned/redeemed points.
- `CollectionRulesItems` — tier rows.

### 1.14 Coupons
- `CouponCode` — linked to a PricingRule, `used` count, validity, min-amount.
- `AppliedCouponCodes` — child on invoice.

### 1.15 E-invoicing
**None.** No IRN/GST e-invoice/EWB generation exists. GST support is report-only (§4/§5). Notable gap vs ERPNext.

### 1.16 ERPNext sync / online services
- `ERPNextSyncSettings` — `models/baseModels/ERPNextSyncSettings/ERPNextSyncSettings.ts:6`. Two-way sync with an ERPNext instance (`baseURL`, `authToken`, `deviceID`, intervals). `change()` (`:52`) calls `initERPNSync` / `syncDocumentsToERPNext` from `src/utils/erpnextSync`.
- `ERPNextSyncQueue`, `FetchFromERPNextQueue` — outbound/inbound sync queues.
- `IntegrationErrorLog` — sync error log.
- `PrintTemplate` — see §6.

---

## 2. The ledger posting engine (GL)

Three collaborating pieces:

**`Transactional` (abstract base)** — `models/Transactional/Transactional.ts:22`. Any doc that posts GL extends it. Wires lifecycle to posting:
- `afterSubmit` (`:45`) → `getPosting()` then `posting.post()`.
- `afterCancel` (`:59`) → `posting.postReverse()`.
- `afterDelete` (`:73`) → hard-deletes all `AccountingLedgerEntry` rows for the doc.
- `validate` (`:31`) → `posting.validate()` (balance check before submit).
- `getPosting()` is abstract; each doc builds its own Dr/Cr set.

**`LedgerPosting`** — `models/Transactional/LedgerPosting.ts:23`. Accumulates entries for one source doc.
- `debit(account, amount)` / `credit(account, amount)` (`:40`, `:45`) accumulate into per-account `AccountingLedgerEntry` docs (one entry per account per side, deduped via `debitMap`/`creditMap`, `_getLedgerEntry` `:95`).
- Each entry is stamped `referenceType=schemaName`, `referenceName=name`, `party`, and a **timezone-normalized date forced to 00:00 local** (`timezoneDateTimeAdjuster` `:64`).
- `post()` (`:50`) → `_validateIsEqual()` then syncs all entries. `_validateIsEqual` (`:131`) throws if ΣDebit ≠ ΣCredit — **this is the balancing guarantee, enforced per document, not system-wide**.
- **Rounding**: `makeRoundOffEntry()` (`:79`) computes Dr−Cr diff and books the remainder to `AccountingSettings.roundOffAccount`. Called explicitly at the end of each `getPosting()`.
- **Reversal/cancellation**: `postReverse()` (`:55`) → `_syncReverseLedgerEntries` (`:171`) loads existing non-reverted entries and calls `doc.revert()`.

**`AccountingLedgerEntry`** — `models/baseModels/AccountingLedgerEntry/AccountingLedgerEntry.ts:6`. Fields: `date, account, party, debit, credit, referenceType, referenceName, reverted, reverts`. `revert()` (`:16`) marks the original `reverted=true` **and inserts a mirror entry with debit/credit swapped** (`reverts` = original name) — reversal is additive, both rows kept (audit-preserving). Reports filter `reverted=false`.

**Multi-currency**: invoices store `exchangeRate` (`Invoice.getExchangeRate` `:400`, rounded to 2dp) and post in **company currency** — every posting line multiplies `item.amount.mul(exchangeRate)` and debits/credits `baseGrandTotal` (`SalesInvoice.ts:24`). Payments post in doc amount directly. No exchange-gain/loss account handling.

**Concrete postings:**
- **SalesInvoice** (`SalesInvoice.ts:23`): Dr debtor `account` = `baseGrandTotal`; Cr each `item.account` (income); Cr each `tax.account`; Dr `discountAccount`; Dr loyalty `expenseAccount` if redeeming; round-off. `isReturn` flips all sides.
- **PurchaseInvoice** (`PurchaseInvoice.ts:46`): Cr creditor `account`; Dr `item.account` (expense/asset); Dr taxes; Cr discount; round-off.
- **Payment** (`Payment.ts:330`): Dr `paymentAccount`, Cr `account`; tax Dr/Cr by Receive/Pay (`:353`); write-off posting (`applyWriteOffPosting` `:371`) to `writeOffAccount`.
- **JournalEntry** (`JournalEntry.ts:24`): passthrough of manual rows.
- **StockTransfer (Shipment/PurchaseReceipt)** (`StockTransfer.ts:211`): inventory GL — see §3.

---

## 3. Inventory ledger & valuation

**Stock ledger doc**: `StockLedgerEntry` (`models/inventory/StockLedgerEntry.ts:5`) — `date, item, rate, quantity (+in/−out), location, batch, serialNumber, referenceType, referenceName`. A plain `Doc`, **not** `Transactional` — SLEs are written by the StockManager, not the LedgerPosting engine.

**Engine**: `StockManager` (`models/inventory/StockManager.ts:10`) + inner `StockManagerItem` (`:210`).
- Driven by the `Transfer` base (`Transfer.ts:7`): `beforeSubmit`→validate, `afterSubmit`→`createTransfers`, `beforeCancel`→`validateCancel`, `afterCancel`→`cancelTransfers` (`deleteAll` SLEs for the ref, `StockManager.ts:50`).
- Validation (`#validate` `:88`): rate>0, qty>0, at least one location, and **stock availability incl. future-negative check** (`#validateStockAvailability` `:135` — prevents a back-dated issue from making later balances negative).
- Movement (`#moveStockForBothLocations` `:268`): out from `fromLocation` (negative qty), in to `toLocation`; serial-numbered items produce one SLE per serial (`:305`).

**Valuation**: `StockQueue` (`models/inventory/stockQueue.ts:1`) maintains **both** a FIFO queue and a moving average simultaneously.
- `inward(rate, qty)` (`:27`) updates `movingAverage` and pushes onto the FIFO queue.
- `outward(qty)` (`:53`) consumes FIFO layers and returns the consumed rate.
- `get fifo` (`:14`) = value/quantity. `ValuationMethod` enum has FIFO and MovingAverage, **but valuation is hardcoded to FIFO** in the stock reports (`StockLedger._setRawData` `reports/inventory/StockLedger.ts:93`). Moving average is computed but unused.
- COGS for shipments is computed by **replaying the FIFO queue over historical SLEs** at posting time: `getShipmentCOGSAmountFromSLEs` (`reports/inventory/helpers.ts:44`), called by `StockTransfer.getPostingAmount` (`StockTransfer.ts:253`).

**Inventory GL** (`StockTransfer.getPosting` `StockTransfer.ts:211`), using `InventorySettings` accounts:
- Shipment (sales): Dr COGS, Cr StockInHand (reversed on return).
- PurchaseReceipt: Dr StockInHand, Cr StockReceivedButNotBilled.

**Stock quantity queries** use **raw SQL/knex** (not the queue): `bespoke.ts getStockQuantity` (`:144`) sums `quantity` from SLE with item/location/batch/serial/date filters. Return-balance math: `getReturnBalanceItemsQty` (`:186`).

---

## 4. `reports/`

All reports extend `Report` (`reports/Report.ts:10`, an `Observable`) with the lifecycle `initialize → setDefaultFilters → getFilters → getColumns → setReportData`. Registered in `reports/index.ts:10`. Rendering model is a generic `ReportData = ReportRow[]` of `ReportCell{value, rawValue, align, width, bold, color…}` consumed by a generic Vue report viewer (no per-report templates). Reports auto-refresh via `fyo.doc.observer` listeners on `sync:/delete:` events.

**Data access is mixed**: financial reports use `fyo.db.getAllRaw`; dashboard aggregates use **raw knex SQL** in `bespoke.ts`.

**Ledger/account reports:**
- `LedgerReport` (abstract) — `reports/LedgerReport.ts:12`. Loads `AccountingLedgerEntry` via `getAllRaw` (`_setRawData` `:78`), groups by account/party/reference (`_getGroupedMap` `:46`).
- `GeneralLedger` — `reports/GeneralLedger/GeneralLedger.ts:24`. Running balance, group totals, closing row, ref-type filter, pagination (`_getQueryFilters` `:242`).
- `AccountReport` (abstract) — `reports/AccountReport.ts:35`. The tree/period engine for financial statements: builds account tree, per-date-range value maps, rolls child values into parents, prunes empty branches (`_getAccountTree` `:191`, `pruneAccountTree` `:573`). Periodicity (Monthly…Yearly), fiscal-year vs until-date, consolidation. `getFiscalEndpoints` `:447`.
- `TrialBalance` — `reports/TrialBalance/TrialBalance.ts:32`. Opening/Debit/Credit/Closing via three synthetic date ranges (`_getDateRanges` `:133`).
- `ProfitAndLoss` — `reports/ProfitAndLoss/ProfitAndLoss.ts:17`. Income − Expense = Total Profit.
- `BalanceSheet` — `reports/BalanceSheet/BalanceSheet.ts:13`. Asset/Liability/Equity roots with totals.

**GST reports (India):**
- `BaseGSTR` (abstract) — `reports/GoodsAndServiceTax/BaseGSTR.ts:15`. Builds GSTR rows from submitted invoices, resolves place-of-supply from party address/GSTIN state code (`getGstrRow` `:142`), classifies B2B/B2CL/B2CS/NR (`transferFilterFunction` `:97`), splits IGST/CGST/SGST (`setTaxValuesOnGSTRRow` `:194`).
- `GSTR1` (sales) / `GSTR2` (purchases). Export via `gstExporter.ts` (JSON for the govt portal) and `commonExporter.ts` (CSV).

**Inventory reports:**
- `StockLedger` — `reports/inventory/StockLedger.ts:17`. Replays FIFO over all SLEs (`getStockLedgerEntries` `helpers.ts:111`) → per-move balance qty/value/valuation.
- `StockBalance` — `reports/inventory/StockBalance.ts:11` (extends StockLedger). Opening/in/out/closing qty & value per item/location/batch/serial (`getStockBalanceEntries` `helpers.ts:188`).

---

## 5. `regional/`

Minimal and India-only.
- `regional/in.ts:1` — `codeStateMap`: GST state-code → state-name lookup (the only file in the directory).
- `models/regionalModels/in/` — `Address.ts`, `Party.ts`, `types.ts`. India adds `gstin`, `gstType`, `pos` (place-of-supply) fields.
- Hook-in mechanism: `models/index.ts:128 getRegionalModels(countryCode)` returns `{Address, Party}` overrides only when `countryCode === 'in'`; otherwise `{}`. GST behavior surfaces only in reports (§4) and hidden-field toggles (`AccountingSettings.hidden.gstin` `:84`). **No other country has regional logic.**

---

## 6. `templates/` — print

Six bundled print formats: `Basic`, `Business`, `Minimal`, `Business-POS`, `Business.Payment`, `Business.Shipment` (`templates/*.template.html`).

**Rendering engine = Vue at runtime.** The `.template.html` files are Vue templates (`v-if`, `{{ }}`, `:style`, `:src` — see `templates/Basic.template.html:1`). They are compiled and mounted by `src/pages/PrintView/PrintView.vue` / `PrintContainer.vue`; editable copies are managed by the `PrintTemplate` model (`models/baseModels/PrintTemplate.ts:7`) and the Template Builder page. PDF is produced by rendering the Vue component and printing (see `src/utils/printTemplates.ts:456`).

**Data context** is assembled by `src/utils/printTemplates.ts getPrintTemplatePropValues` (`:46`): a `PrintTemplateData` object with `doc.*` (name, date, items, taxes, totals, `grandTotalInWords`, `subTotal`, `totalDiscount`, `showHSN`, payment details) and `print.*` (company name, logo, address, gstin, font). Templates are chosen per `schemaName` (`PrintTemplate.lists.type` `:47` lists SalesInvoice, SalesQuote, PurchaseInvoice, JournalEntry, Payment, Shipment, PurchaseReceipt, StockMovement).

---

## 7. Payment / subscription / licensing / online services

- **No licensing/paywall/subscription code** exists. Books is open-source desktop; there is no license check, entitlement, or billing model. (Relevant for us: subscription gating is greenfield to add.)
- **Online service = ERPNext sync only** (§1.16): a client of an ERPNext server (push/pull docs), not a SaaS backend.
- Telemetry hooks exist (`fyo/telemetry`) but no financial/online-service gating.

---

## 8. Port notes — Books → ERPNext/Frappe mapping

Because the target Frappe deployment already runs ERPNext, most of Books' domain is **redundant with ERPNext**. Books' value is that it is a **radically simplified subset** — useful as a spec for a lightweight product, not as new server logic.

| Books model / logic | Nearest ERPNext equivalent | Where Books is simpler | Port verdict |
|---|---|---|---|
| `Account` | Account | No true NestedSet (lft/rgt unused); rootType-only sign | Reuse ERPNext |
| `AccountingLedgerEntry` + `LedgerPosting`/`Transactional` | GL Entry + `make_gl_entries` | Per-doc balance only; reversal = swap-row insert; no cost-center/dimensions/period-close | **Redundant** — ERPNext GL is a superset |
| `SalesInvoice` | Sales Invoice | No sales-order flow, no schedules, no deferred rev | Reuse ERPNext |
| `PurchaseInvoice` | Purchase Invoice | No PO/three-way match | Reuse ERPNext |
| `SalesQuote` | Quotation | Quote = Invoice subclass, no order stage | Reuse ERPNext |
| `Payment` + `PaymentFor` | Payment Entry + references | No bank reconciliation tool, simpler tax-on-payment | Reuse ERPNext |
| `JournalEntry` | Journal Entry | Nearly identical, simpler | Reuse ERPNext |
| `StockLedgerEntry` + `StockManager` + `StockQueue` | Stock Ledger Entry + valuation | **FIFO only**; COGS via FIFO replay; no repost engine, no serial/batch bundle doctype | Reuse ERPNext |
| `StockMovement` | Stock Entry | 4 movement types, no BOM/work order | Reuse ERPNext |
| `Shipment` / `PurchaseReceipt` | Delivery Note / Purchase Receipt | Simpler; auto-created from invoice | Reuse ERPNext |
| `Item`/`ItemGroup`/UOM | Item / Item Group / UOM | No variants, no per-company item defaults | Reuse ERPNext |
| `Party` (Customer/Supplier/Both) | Customer + Supplier (separate) | **Unified party with role** — a genuine model difference; ERPNext has no "Both" party | Map carefully |
| `PricingRule`/`CouponCode` | Pricing Rule / Coupon Code | Very close; Books adds recursive free-item | Reuse ERPNext |
| `PriceList`/`PriceListItem` | Price List / Item Price | Simpler | Reuse ERPNext |
| `Tax`/`TaxSummary` | Sales/Purchase Taxes and Charges Template | Books `Tax` is nearly empty; flat rate rows, cash-basis via `payment_account` | Reuse ERPNext |
| `LoyaltyProgram`/`LoyaltyPointEntry` | Loyalty Program / Loyalty Point Entry | Same concept, simpler tiers | Reuse ERPNext |
| POS (`POSProfile`, opening/closing shift, denominations) | POS Profile / POS Opening & Closing Entry | Simpler cash reconciliation | Reuse ERPNext |
| GSTR1/GSTR2 + `regional/in` | ERPNext India Compliance (GST) | **No e-invoice/IRN/EWB**, report-only | Reuse ERPNext India app |
| `PrintTemplate` + Vue templates | Print Format (Jinja/HTML) | Vue-based, incompatible engine | **Do not port** — rebuild as Frappe Print Formats |
| ERPNext Sync models | N/A (Books-side client) | — | **Drop** — irrelevant once running inside Frappe |
| `SetupWizard`/`AccountingSettings`/`InventorySettings`/`Defaults` | Setup Wizard / Accounts Settings / Stock Settings | Single feature-flag single vs many doctypes | Map to ERPNext settings |

**Portable as-is (worth keeping as reference):** the FIFO `StockQueue` (`stockQueue.ts`) and the COGS-from-SLE replay are clean, self-contained algorithms. The return/credit-note qty-balancing (`bespoke.getReturnBalanceItemsQty`) encodes non-trivial batch/serial rules.

**Redundant with ERPNext (do not re-implement):** the entire GL posting engine, multi-currency posting, tax/discount math, outstanding-amount tracking, perpetual-inventory GL, financial statement tree reports — ERPNext's equivalents are strict supersets.

**Genuine gaps/differences to remember:** (1) unified `Party` with a "Both" role has no direct ERPNext analog; (2) no e-invoicing anywhere in Books; (3) valuation is FIFO-only despite the enum; (4) rounding is a single `roundOffAccount` per document with no per-line rounding; (5) reversal keeps mirror rows rather than deleting — matches ERPNext's cancel-and-reverse philosophy, so GL semantics align well.

---

Skipped: exhaustive per-row child-model listing (InvoiceItem child formula math) and `models/helpers.ts` internals (pure helpers for loyalty/pricing/exchange-rate) — catalogue them when the port needs field-level fidelity.
