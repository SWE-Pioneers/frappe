# Frappe Sales System — Design Spec

- **Date:** 2026-08-04
- **Status:** Approved 2026-08-04 (open questions resolved); implementation plan in progress
- **Owner:** SWE-Pioneers (Sanad)
- **Branch:** `dev/frappe-sales-system-plan-*`
- **Scope of this spec:** Spec 1 of 2. The packaged sell-stack + vertical profiles (grocery + clothing first). The **Local↔Cloud Sync Service** is a separate subsystem — its own spec (Spec 2).

---

## 1. Problem

Package Frappe's sell-side apps into a **productized "full sales system"** we resell to many small Libyan businesses. Each client gets accounting ("books"), an in-store POS, and an online store — all on **one backend**, all sharing customers/items/stock/ledger, each surface installable as its own desktop/web app. The base is common across clients; the difference between a grocery and a clothing shop is **configuration, not a different product**.

## 2. Goals

- One shared Frappe backend per client; every module reads/writes the same database (no bridges).
- Three client-facing "apps" over that backend: **Point of Sale**, **Online Store**, **Accounting** (the "Books" face).
- **Online selling on by default** for every vertical (Webshop is part of the base, not a separate profile).
- Repeatable per-client setup: pick a **vertical profile** at install and the site is configured.
- Libya-fit: LYD, Arabic + RTL, cash-first payments + Libyan gateways, no-VAT default, offline-capable POS.
- Desktop feel via **PWA** (Electron optional, later).
- Each client runs **only the modules they need** (HRMS/CRM/etc. off unless asked).

## 3. Non-goals (this spec)

- The local↔cloud sync service (→ Spec 2).
- Verticals beyond **grocery** and **clothing** (others are roadmap presets).
- Full-service restaurant / dining (see Risks — the official app is archived).
- Electron/Tauri packaged installer, self-serve SaaS provisioning UI, deep per-client CoA/tax tuning.

## 4. Key decisions & why (the reconciliation)

These were settled during brainstorming and are load-bearing:

1. **Accounting = ERPNext Accounting, not the desktop Frappe Books app.** Frappe Books (per frappe.io/books) is desktop-only, single SQLite file, **no server, no API** — it cannot be "one backend everything communicates with." Its feature set (invoicing + P&L + GL + Balance Sheet) is a *subset* of ERPNext accounting, so we lose no capability, only the "runs on one offline laptop" trait — which conflicts with "one backend" anyway.
2. **POS and Webshop *are* ERPNext.** The POS is (Frappe's own words) "a module within ERPNext"; Webshop runs on ERPNext for items/stock/orders. So "one backend" ⇒ ERPNext is the engine. The client never sees "ERPNext" — they see three focused apps.
3. **POS engine = ERPNext built-in POS** (already in our `erpnext` fork, offline-capable, Arabic-translated). PosAwesome documented as an upgrade path only.
4. **Verticals are setup presets on one codebase/PWA**, not separate apps. Adding a vertical = a small config delta.
5. **Deployment mode is a per-client choice:** cloud-hosted (default) or on-premise/local-network. Same product, different place the single DB sits. On-prem + cloud hybrid is what Spec 2's sync service enables.

## 5. Architecture

### 5.1 One backend, three faces
```
                 ┌──────────────────────────────────────────────┐
                 │   One Frappe site per client (one database)   │
   Counter  ───▶ │  POS ─────┐                                    │
   Online   ───▶ │  Webshop ─┼─▶ Items · Stock · Customers ·      │
   Gateways ───▶ │  Payments ┘   Price Lists · Pricing Rules      │
                 │          all post to ─▶ ERPNext GL (the books)  │
                 └──────────────────────────────────────────────┘
   PWA installs: "Point of Sale" · "Online Store" · "Accounting"
```

### 5.2 Source-of-truth map
| Data | Owned by | Notes |
|---|---|---|
| Items / stock / warehouses | ERPNext | Single master; POS + Webshop both read it |
| Customers | ERPNext | Webshop signups + POS walk-ins create Customer here |
| Price lists / pricing rules / taxes | ERPNext | One selling price list drives both channels; per-client tax template (no-VAT default) |
| The ledger (books) | ERPNext Accounting | POS Invoice → GL; Webshop order → Sales Invoice → GL; one trial balance |

### 5.3 Deployment modes
| Mode | The one DB lives | Good for | Catch |
|---|---|---|---|
| **Cloud (default)** | Our VPS, one site per client behind Traefik | Running many clients, Webshop works natively | POS uses **offline mode** for internet blips |
| **On-premise** | One small server on the client's LAN; all terminals connect to it | Data on-site, fast LAN, works without internet | Webshop needs public reachability (tunnel/hosted front); we maintain each box; hybrid needs **Spec 2 sync** |

## 6. Shared base (every client)

Applied to every site regardless of vertical:

- **Locale/finance:** LYD currency; Arabic + RTL default; Libyan date/number formats.
- **Chart of Accounts:** the **client's provided CoA — supplied and baked in** at `docs/superpowers/assets/coa_libya_ar_en.{md,csv,ods,xlsx}` (**207 accounts**, Arabic-primary + English, ERPNext `account_type`/`root_type` + default accounts pre-mapped). **No tax enforcement** (Libyan govt doesn't currently enforce) — VAT accounts exist but tax templates stay off; books kept clean and **compliance-ready**. (resolved 2026-08-04)
- **Payments:** Cash (LYD) as default POS mode; Libyan gateways (from `payments` fork) as additional POS payment modes and as the Webshop checkout gateway.
- **Webshop:** enabled by default (online selling baseline for all verticals) — website items published from Items, cart → Sales Order, gateway checkout.
- **Roles + Workspaces:** Cashier / Store Manager / Accountant / Owner; each lands in its own workspace/app.
- **Print:** Arabic invoice + 80mm thermal receipt formats via the `print_designer` fork.
- **Domain:** ERPNext **Domain = Retail** to hide irrelevant modules (Manufacturing, Assets, Quality, …).
- **PWA:** install affordance for POS / Online Store / Accounting.
- **POS:** offline mode enabled; POS Opening/Closing Entry workflow → auto-posts to GL.
- **Not installed:** HRMS, CRM, Helpdesk, etc. (opt-in later, one command each).

## 7. Vertical profiles

### 7.1 Grocery / mini-market (v1)
- **Item groups:** Produce, Dairy, Beverages, Dry Goods, Household, …
- **UOMs:** Nos + Kg + Gram with conversions; per-kg items.
- **Weight-embedded barcodes:** parse scale labels (EAN-13 with embedded weight/price) → item + quantity. **Custom glue** (POS barcode hook) — not native.
- **Batch + expiry:** enabled on perishable item template; expiry alerts / near-expiry report.
- **Stock:** reorder levels + reorder report; negative-stock policy (config); **perpetual inventory** (COGS accuracy prioritized — resolved 2026-08-04).
- **POS Profile:** barcode-first, minimal fields, cash default + gateway, fast checkout.
- **Roles:** Cashier, Store Manager.

### 7.2 Clothing shop (v1)
- **Item Variants:** attributes **Size × Color**; item templates + generated variants; stock per variant.
- **Barcode per variant.**
- **Pricing:** seasonal price lists + Pricing Rules for discounts/end-of-season promos.
- **POS Profile:** variant-picker + barcode.
- **Optional:** loyalty points program.
- **Roles:** Cashier, Store Manager.

### 7.3 Roadmap profiles (later, same mechanism)
Cafe / coffee (counter-service via POS; optional BOM ingredient deduction; kitchen-ticket print) · Online-primary shop (Webshop-forward, POS optional) · Pharmacy (mandatory batch+expiry) · Electronics/mobile (serial/IMEI + warranty) · Bakery/sweets (light BOM, per-kg+per-piece) · Hardware/building materials (bulk UOM, credit customers + statements) · Auto-parts, Wholesale (price tiers + credit). Each is a preset delta on the base.

## 8. The setup app: `sales_system_setup`

The main custom deliverable. A small Frappe app that turns a blank site into a configured sell-stack:

- **Fixtures** for the shared base (roles, workspaces, domain, print formats, UOMs, payment mode templates, base CoA references).
- **Profile presets** (grocery, clothing) as data bundles (item groups, POS Profile template, price lists, variant attributes, batch/expiry flags).
- **Apply mechanism:** a whitelisted method / bench command `apply_profile("grocery"|"clothing")` run once per new site (invoked from the deployment recipe). **No wizard UI in v1** (YAGNI — a bench command is enough; a picker page can come later).
- Idempotent: re-running does not duplicate config.

## 9. Payments integration

- Register each Libyan gateway (from `payments` fork) as a **Payment Gateway Account**.
- **Webshop checkout** → ERPNext Payment Request → gateway → callback marks the Sales Invoice paid.
- **POS** → gateway as a POS payment mode; **cash always works offline**, card/online requires connectivity.
- **Status (resolved 2026-08-04): gateways are NOT live** — bank registration must complete first, so v1 has no online payment.
- **Implementation reality (verified during build):** Frappe v16 webshop has **no "checkout on, zero gateway" mode** (`WebshopSettings.validate_checkout()` force-resets `enable_checkout=0` without a `payment_gateway_account`). So **v1 manual payment = `enable_checkout=0`**: the storefront button becomes **"Request for Quote"** → submits a **Quotation**; the owner converts it to a Sales Order once payment is settled offline (cash on delivery / bank transfer). No online "Pay" button is ever rendered (it's gated on `enabled_checkout`), and **no placeholder gateway** is created. In-person cash/POS is unaffected.
- **Gateway drop-in (later):** once the Libyan processor is registered, create its Payment Gateway + Payment Gateway Account and set **both** `enable_checkout=1` and `payment_gateway_account` on Webshop Settings — that flips the storefront to Sales-Order-with-online-Pay checkout. The seam is marked in `setup/webshop.py`.

## 10. Desktop / PWA packaging & offline

- **Whole ERPNext as a PWA (resolved 2026-08-04):** the entire desk is PWA-installable (manifest + install affordance) — POS / Online Store / Accounting each get their own window + icon, plus the full desk. One backend.
- **Offline reality — be honest about what "offline-first" can mean:**
  - **POS: genuinely offline** (native offline mode — caches locally, syncs on reconnect). Ships in v1.
  - **Full-operation offline for the *whole* desk is achieved by *hosting*, not the browser:** run ERPNext **on the client's LAN (on-prem)** so it keeps working with no internet. That is Spec 2's territory (local hosting + local↔cloud sync).
  - **Browser-level offline for the whole desk is NOT feasible** natively (the Frappe desk needs server round-trips) — we will not promise it. PWA gives installability everywhere; true offline is POS (browser) + on-prem (hosting).
- **Launcher:** role-based landing so each department opens straight into its app (Workspaces + role home — mostly config).
- **Electron/Tauri:** later rung; only if a client demands a real `.exe`. Presentation only.

## 11. Custom vs config (effort split)

- **Config / native (~80%):** masters, POS Profile, Webshop settings, variants, batch/expiry, pricing rules, GL wiring, domain/workspaces — ERPNext already does this; our job is to configure and **verify** it.
- **Custom code (~20%):** `sales_system_setup` app + profile presets · weight-embedded barcode parse hook (grocery) · any payment-gateway glue not already in `payments` · PWA manifests + launcher · deployment recipe (Containerfile + per-client site provisioning) · verification specs.

## 12. Verification

Extend the existing `tests/` Playwright harness against one disposable site per profile:
- **Grocery:** cash POS sale (incl. a per-kg / weight-barcode item) → correct GL (income, cash, COGS if perpetual) + stock decrement; near-expiry report shows a batch.
- **Clothing:** variant sale → GL + stock decrement on the **correct** size/color variant; a Pricing Rule discount applies.
- **Webshop (both):** order → gateway payment → Sales Invoice → GL **reconciles** (ledger-invariants: entry balances, trial balance nets to zero).
- **Cross-cutting:** POS offline → sync; Arabic/RTL renders live.

## 13. Open questions — resolved (2026-08-04)

1. **Payment-gateway readiness** — ❗**Not ready; pending bank registration.** v1 online checkout uses **manual methods** (COD + bank transfer / mark-as-paid); gateway drops in later without reworking the storefront. In-person cash/POS ships now. (See §9.)
2. **Libya CoA / tax** — ✅ **Supplied & baked in**: `docs/superpowers/assets/coa_libya_ar_en.*` (207 accounts, AR/EN, types + defaults mapped). No tax enforcement now; keep books **compliance-ready**. (See §6.)
3. **POS offline + card** — Accepted: offline POS = cash only; card/online needs connectivity. Whole-desk offline = via on-prem hosting (Spec 2), not the browser. (See §10.)
4. **Inventory valuation** — ✅ **Perpetual inventory** (COGS accuracy first). (See §7.1.)
5. **Dining** — Planned post-v1 workstream: **fork `frappe/hospitality`, audit its internals, port it live to v16.** Not in v1 (v1 = grocery + clothing); gets its own audit/port spec. Do not ship on the archived upstream as-is.
6. **Weight-embedded barcodes** — Client will **calibrate/provide** the scale label format; the parse hook consumes it (config, not a fixed assumption).

## 14. Dependencies

- Existing forks (submodules): `erpnext` (v16), `webshop` (v16), `payments` (v16, Libyan gateways), `print_designer`.
- New: `sales_system_setup` (this project's custom app).
- Deployment: existing VPS/Traefik pattern (`*-<client>.swe.com.ly`, one site per client).
- Prior work reused: Arabic/RTL catalogs (done across forks).

## 15. Sequencing

1. **Spec 1 (this):** shared base + `sales_system_setup` + grocery & clothing presets + payments wiring + PWA + deployment recipe + verification. Ships cloud-hosted, standalone value.
2. **Spec 2 (next):** Local↔Cloud Sync Service. Presumed shape: local POS/accounting for offline reliability + cloud for Webshop & central reporting ⇒ mostly-directional sync (masters/stock push to cloud, online orders pull to local). Hard parts: change tracking, conflict resolution, idempotent apply, offline queue + resume. Its own brainstorm.
