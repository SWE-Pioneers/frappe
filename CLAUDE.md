# CLAUDE.md — SWE-Pioneers Frappe app monorepo

Parent repo that ties SWE-Pioneers' forks of the Frappe apps together as git submodules
(each app is `github.com/SWE-Pioneers/frappe-<app>`, forked from `frappe/<app>`). This file
documents the changes made across the apps so future sessions have context.

## Arabic (ar) internationalization — DONE across all 15 apps

Every app fork ships a completed Arabic catalog at `<app>/<app>/locale/ar.po`, translated to
**100% of app-owned strings** (Libyan-appropriate MSA). Framework-core strings (Frappe's own
menus/messages) are intentionally out of scope — they live in the frappe framework, not our forks.

### The pipeline — `scripts/i18n/`
- `extract_source_strings.py` — bench-free extractor: scans `__()`/`_()`/`{{ _() }}` in JS/TS/Vue/Py/Jinja and builds/updates an `ar.po` (used for apps that shipped no catalog).
- `sync_pot_to_po.py` — merges an app's `locale/main.pot` (Frappe's full `generate-pot-file` extraction, incl. doctype/field/report labels) into `ar.po`, adding missing msgids.
- `extract_empty.py` / `apply_translations.py` — dump untranslated entries to JSON batches, fill them (LLM), apply back with a **per-entry placeholder gate** (tags each `ai-translated; needs-native-review`).
- `validate_po.py` — hard gate: placeholder multiset equality (`{0}`/`{n}`, `%(x)s`, `%s/%d`, HTML tags), parse round-trip, duplicate check.
- `glossary_ar.csv` — shared terminology (Course=دورة تدريبية, Invoice=فاتورة, Submit=اعتماد, …).

To reach **true 100%** (doctype/field metadata, not just `__()`/`_()` calls) run
`bench generate-pot-file --app <app>` on a bench, `bench update-po-files --app <app> --locale ar`,
then fill via the pipeline. polib saves unwrapped (`wrapwidth=0`) → `.po` diffs show wrap churn (expected).

### RTL
Server-authoritative, following the LMS pattern: the app's `www/*.py` `get_boot()`/context exposes
`lang` + `text_direction` (via `frappe.utils.jinja_globals.is_rtl`), and the SPA `index.html`'s
`<html>` tag consumes them (`lang="{{ boot.lang }}" dir="{{ boot.text_direction }}"`). Applied to
crm, helpdesk, drive, hrms, wiki, gameplan, insights, builder; lms/erpnext/healthcare already had it.
Greenfield SPAs (gameplan/insights/builder) also got a full i18n retrofit: a `get_translations`
endpoint (copied from `crm/crm/api/__init__.py`), a `translation.js` plugin, and `__()`-wrapping
across their components.

### Per-app catalog status (app-owned strings)
lms, erpnext, healthcare, crm, helpdesk, hrms, drive, wiki, webshop, blog, payments,
print_designer, gameplan, insights, builder — all merged to their standing branches
(main / version-16 / develop per `.gitmodules`). lms + blog additionally verified live in Arabic
via Playwright on the VPS.

## Blog — visitor commenting + fixes (frappe-blog)
See `blog/CLAUDE.md` for detail. Summary:
- **Anonymous + register-to-comment**: `Blog Settings → Allow Guest to comment` (name+email, no
  account) plus website signup (new users get the built-in **Website User** type).
- **Account-level moderation**: under-review accounts are allowed in and may comment, but their
  comments stay hidden (`published=0`) until a supervisor confirms the *account* by granting the
  desk-less **"Approved Commenter"** role (auto-created on install/migrate). On approval, that
  account's held comments are released live. Post authors + System Managers post live.
- **Email-safe likes/comments**: `safe_sendmail()` — notifications no longer crash with "Please
  setup default outgoing Email Account" when a site has no SMTP.
- **CSS fix**: `web_include_css` referenced the raw `blog.scss` (served as `application/octet-stream`,
  refused by strict-MIME browsers). Renamed to a compiled bundle `public/scss/blog.bundle.scss`
  (SCSS globals → CSS `var(--…)`, breakpoint mixin inlined) + `web_include_css = "blog.bundle.css"`.

## Deployment (VPS `swe-server-ly`, 102.203.201.196:6934, `deploy` user)
Access: plain `ssh -p 6934 deploy@102.203.201.196` (the `vps_ed25519` key is passphrase-protected
and loaded in the agent — do NOT force it with `-i … IdentitiesOnly=yes`, that uses the encrypted
file and fails). The correct IP is **.196** (the ministry access-map's `.160` is stale).

Apps are deployed as multi-tenant demo stacks under `/opt/apps/demo-<app>/` (Traefik, `*-<app>.swe.com.ly`),
built from `~/build/<app>-custom/Containerfile`. To ship changes to an app:
1. Update `~/build/<app>-custom/Containerfile` (repointed to `SWE-Pioneers/frappe-<app>` + the compile step).
2. `docker build --no-cache -f Containerfile -t <app>-swe:v16-swe1 .` — **`--no-cache` is required**, else BuildKit reuses the stale `get-app` layer and ships the old code.
3. `cd /opt/apps/demo-<app> && docker compose up -d --force-recreate` (rolling; tenant sites persist in volumes).

### Frappe-v16 translation mechanics (load-bearing — see the vps Containerfiles)
- Frappe serves **compiled `.mo`** from `assets/locale/<lang>/LC_MESSAGES/<app>.mo` at runtime. It
  does NOT read `.po`, and `bench build` does NOT compile translations.
- So catalogs must be compiled: `bench compile-po-to-mo --app <app> --force` (the `--force` all-apps
  form needs a running site; the **per-app** form works site-lessly — compile `frappe` + each app).
- Compile writes to `sites/assets/locale/` which is a **discarded VOLUME** at build time, so the
  Containerfile must `rm -rf assets && cp -a sites/assets assets` AFTER compiling.
- erpnext ships in the `frappe/erpnext` base image (not a get-app) → its `ar.po` is overlaid via `curl`.

## Verification
Playwright specs live in the worktree `tests/` (arabic-verify, arabic-coverage with an English-leak
detector, live-blog, live-lms, blog-comments). Blog + lms are verified **live in Arabic** on the VPS
(`sanad-blog.swe.com.ly`, `wendy-lms.swe.com.ly`). Blog commenting/likes/moderation verified live.

## Pending
- Live Arabic verification for **helpdesk, hrms, print_designer** (catalogs 100% + merged; build on
  the VPS like blog/lms — local SPA builds fail on this network).
- Roll blog-comment settings (`allow_guest_to_comment`, signup) to the other tenant blogs + make
  them install defaults; re-bump parent submodule pins for the latest blog/lms commits.
- **Libyan payment gateways** (DPAY/Moamalat/Plutu in the payments fork) — a separate, untouched track.
