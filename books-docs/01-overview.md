# Frappe Books — Codebase Overview & Port Assessment

Study of `frappy/books` (fork of [frappe/books](https://github.com/frappe/books) at SWE-Pioneers/frappe-books, v0.37.0), done 2026-07-21 to ground the plan for turning it into a **real Frappe app** (bench, DocTypes, MariaDB) that works **web + desktop** and can be sold on **subscription**.

## What Frappe Books is

A single-user, offline-first desktop accounting app: Vue 3 renderer + Electron main process, one **SQLite file per company**, money via the exact-decimal `pesa` library, ~90 hand-authored JSON schemas, and an in-house micro-framework called **fyo** that re-implements a miniature Frappe (Doc ORM, schema meta, singles, child tables, naming series, patches). Despite the name, it shares **no runtime code** with the Frappe framework — but its concepts map onto Frappe nearly one-to-one because it was designed by the same people (old patches even rename `creation→created`, `parenttype→parentSchemaName` — it drifted *away* from Frappe conventions).

## Repo layout (who owns what)

| Folder | Side | Role |
|---|---|---|
| `main.ts`, `main/` | server (Electron main) | boot, window, preload/IPC handlers, print/PDF, updater, bree jobs |
| `backend/` | server | `DatabaseManager`/`DatabaseCore` — knex + better-sqlite3 ORM, migrations, patches |
| `schemas/` | server | the ~90 DocType-like JSON schemas + build/merge pipeline |
| `fyo/` | client* | the framework: `Doc` ORM, `DatabaseHandler`, demuxes, money, i18n, telemetry |
| `models/` | client* | ALL business logic (invoices, ledger posting, inventory, POS) as `Doc` subclasses |
| `reports/` | client* | GL, Trial Balance, P&L, Balance Sheet, GSTR, stock reports |
| `src/` | client | Vue app: pages, controls, router, print, POS UI |
| `utils/`, `regional/`, `templates/`, `fixtures/`, `dummy/`, `translations/` | agnostic | shared types, India GST, print templates, CoA seeds, demo data, 19-language CSVs |

Detailed docs: [02 fyo framework](02-fyo-framework.md) · [03 data layer & schemas](03-data-layer-schemas.md) · [04 desktop shell & IPC](04-desktop-shell-ipc.md) · [05 business logic](05-business-logic.md) · [06 frontend](06-frontend.md).

## The three load-bearing architectural facts

1. **There is a designed platform seam.** The renderer never touches Electron directly — everything goes through one `window.ipc` object, and inside fyo through three **demux** classes (`fyo/demux/db.ts`, `config.ts`, `auth.ts`) that already branch on `isElectron` (the non-Electron branch currently throws `NotImplemented`). `Fyo` even accepts injected demux classes in its constructor. **A web build = write an HTTP demux + a browser `ipc` shim (~35 call sites); the entire Vue tree, form-control system, reports, POS and dashboards run unchanged.**
2. **All business logic lives in TS model classes, not in schemas or SQL.** Ledger posting (`Transactional`/`LedgerPosting`), inventory FIFO (`StockManager`/`StockQueue`), tax/discount/pricing-rule math — all in `models/` as lifecycle hooks on the fyo `Doc`. A "make it a real Frappe app" port means re-expressing this in Python controllers — OR keeping the TS layer and having Frappe act as storage/auth/transport.
3. **What's missing for our product goals:** no auth/users/roles/permissions at all (single-user desktop assumption), no multi-tenancy (file = company), no subscription/licensing code anywhere, no e-invoicing, valuation FIFO-only. Frappe provides the first two natively (sites, Users, RBAC); subscription gating is greenfield.

## Port-strategy tension to settle in planning

Two credible architectures — this is THE decision for the planning session:

- **Path A — true Frappe app (full port):** convert the ~90 schemas to DocTypes (mechanical — see the key-mapping table in doc 03 §1.6), rewrite `models/` business logic as Python controllers, rebuild reports as Frappe reports/pages, and either reuse Books' Vue UI as a bundled SPA (like Frappe LMS/CRM do) or drop it for Frappe Desk. Maximum "same architecture as other Frappe products", maximum effort — and functionally it converges on "a simplified ERPNext", which we already host.
- **Path B — transport swap (Books frontend + Frappe backend):** keep fyo + models + Vue UI intact; implement the demux contract (`getSchemaMap`, `call(method,...)`, `callBespoke`) as whitelisted methods in a thin Frappe app that stores docs in MariaDB doctypes generated from the Books schemas. Frappe supplies sites/auth/hosting/subscriptions; Books supplies the whole UX and business logic. Much less work, keeps the desktop build nearly free (same code, `isElectron` flips the transport), but the business logic stays client-side TS (server must still re-validate the money paths) and it's *architecturally* not like other Frappe apps.
- (Hybrid: B first as the shippable product, migrating hot paths server-side over time.)

**Known risks either way:** the `pesa` exact-decimal Money (string-stored) vs Frappe float+precision — highest-risk area, touches the ledger; dual-boolean `submitted/cancelled` vs `docstatus`; SQLite-dialect bespoke SQL (`strftime`, casts) needing MariaDB rewrites; Vue-based print templates incompatible with Frappe Print Formats.

**Assets we get for free:** 19-language translations **including Arabic**, per-country CoA templates (same format as ERPNext's), a full POS, a demo-data generator (`dummy/` — perfect for our personalized-demo sales model), and a clean, small UI that is Books' entire selling point over ERPNext.

## Product framing (for the subscription offering)

Books' differentiator is **simplicity** — it's ERPNext's accounting core minus the enterprise surface. The subscription product is "simple accounting for small business, in the browser, with an offline desktop app" — the desktop app remains the free/open funnel, the hosted multi-company version with backups/support is the paid tier. No licensing code exists upstream, so entitlement gating plugs into our existing platform (cloud-portal entitlements, per-site provisioning on the bench).
