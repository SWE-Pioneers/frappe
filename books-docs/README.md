# books-docs — Frappe Books architecture study

Findings from a full study of the `books/` submodule (our fork of frappe/books), made to ground the plan for re-architecting it into a Frappe-bench app that works **web + desktop** and can be offered on subscription.

Docs live here (in the umbrella repo) rather than inside the fork so the fork stays cleanly rebaseable on upstream until the port actually starts.

| Doc | Covers |
|---|---|
| [01-overview.md](01-overview.md) | What Books is, repo layout, the 3 load-bearing facts, Path A vs Path B port strategies, risks, product framing |
| [02-fyo-framework.md](02-fyo-framework.md) | The in-house `fyo` framework: `Fyo`, the `Doc` ORM + lifecycle hooks, `DatabaseHandler`/demux bridge, money (pesa), Converter, i18n — with fyo→Frappe concept mapping |
| [03-data-layer-schemas.md](03-data-layer-schemas.md) | Schema JSON shape + full inventory, build/merge pipeline, `DatabaseCore` ORM, migrations/patches, singles/child storage, naming series, schema-key→DocType-key table, SQLite→MariaDB breakage list |
| [04-desktop-shell-ipc.md](04-desktop-shell-ipc.md) | Electron main process, the **complete IPC surface** (every channel), FS features, build system, jobs — and what each becomes on a web backend |
| [05-business-logic.md](05-business-logic.md) | Every model class, the ledger posting engine, inventory FIFO/valuation, reports, regional (India GST), print templates — with Books→ERPNext equivalence table |
| [06-frontend.md](06-frontend.md) | Vue app: boot, router, pages, form-control system, the demux seam, all 35 ipc call sites, print flow, i18n, what changes for web |

Studied at fork commit corresponding to upstream v0.37.0 (2026-07-21).
