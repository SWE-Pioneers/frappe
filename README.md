# frappe — SWE-Pioneers app monorepo

A single parent repository that ties together SWE-Pioneers' forks of the Frappe
standalone apps as **git submodules**. Each app lives in its own repo under the
[SWE-Pioneers](https://github.com/SWE-Pioneers) org (named `frappe-<app>`, forked from the
upstream `frappe/<app>`), and is referenced here at a pinned commit on a chosen branch.

## What this repo is the source of truth for (and what it is not)

**It is not.** The single source of truth for what we ship to customers is
[`vps-infra/frappe-apps/apps.json`](https://github.com/SWE-Pioneers/vps-infra/blob/main/frappe-apps/apps.json).
That manifest, paired with `ops/preclone-frappe-forks.sh`, is what the image build clones, and
`ci/check-app-sources.sh` gates it (fork-only URLs, matching app sets, matching branches).

**This repo is the LOCAL MIRROR of those same forks** — one clone puts every app's source on disk, so
you can read and edit the code we actually run without hunting down 16 repositories. Its job is to
agree with the shipping manifest, never to diverge from it.

That agreement is now enforced, because it broke silently once: this repo declared `helpdesk` on
`main` while the image shipped `swe-v16` — the branch carrying our Arabic/RTL work *and* the
triage-bot API — and `telephony` was missing entirely despite shipping. Anyone reading helpdesk
source here was reading code we do not run. Run the guard after touching submodules, and after any
`apps.json` change lands in `vps-infra`:

```bash
tools/check-against-apps-json.sh                                  # fetches apps.json via gh
tools/check-against-apps-json.sh ../vps/frappe-apps/apps.json     # or point at a local vps checkout
CHECK_PINS=1 tools/check-against-apps-json.sh                     # also report pins behind their branch
```

## Apps

Branches mirror `apps.json` — **do not change one without the other**, the guard will fail.

| Submodule path | Repo | Branch | Ships |
|---|---|---|---|
| `blog` | [frappe-blog](https://github.com/SWE-Pioneers/frappe-blog) | version-16 | ✅ |
| `builder` | [frappe-builder](https://github.com/SWE-Pioneers/frappe-builder) | develop | ✅ |
| `crm` | [frappe-crm](https://github.com/SWE-Pioneers/frappe-crm) | main | ✅ |
| `drive` | [frappe-drive](https://github.com/SWE-Pioneers/frappe-drive) | main | ⚠️ declared, but **not baked into the image yet** |
| `erpnext` | [frappe-erpnext](https://github.com/SWE-Pioneers/frappe-erpnext) | version-16 | ✅ |
| `gameplan` | [frappe-gameplan](https://github.com/SWE-Pioneers/frappe-gameplan) | main | ✅ |
| `healthcare` | [frappe-healthcare](https://github.com/SWE-Pioneers/frappe-healthcare) | version-16 | ✅ |
| `helpdesk` | [frappe-helpdesk](https://github.com/SWE-Pioneers/frappe-helpdesk) | **swe-v16** | ✅ |
| `hrms` | [frappe-hrms](https://github.com/SWE-Pioneers/frappe-hrms) | version-16 | ✅ |
| `insights` | [frappe-insights](https://github.com/SWE-Pioneers/frappe-insights) | main | ✅ |
| `lms` | [frappe-lms](https://github.com/SWE-Pioneers/frappe-lms) | main | ✅ |
| `payments` | [frappe-payments](https://github.com/SWE-Pioneers/frappe-payments) | version-16 | ✅ |
| `print_designer` | [frappe-print_designer](https://github.com/SWE-Pioneers/frappe-print_designer) | main | ✅ |
| `telephony` | [frappe-telephony](https://github.com/SWE-Pioneers/frappe-telephony) | develop | ✅ (helpdesk dependency) |
| `webshop` | [frappe-webshop](https://github.com/SWE-Pioneers/frappe-webshop) | version-16 | ✅ |
| `wiki` | [frappe-wiki](https://github.com/SWE-Pioneers/frappe-wiki) | develop | ✅ |
| `books` | [frappe-books](https://github.com/SWE-Pioneers/frappe-books) | master | ❌ not in `apps.json` — kept for study |

> **`helpdesk` is pinned to `swe-v16`, not `main`.** That branch is the compatible upstream tag with
> our Arabic/RTL commits and the automated-triage API cherry-picked on top. Building from `main`
> silently drops both.

## Clone

```bash
git clone --recurse-submodules https://github.com/SWE-Pioneers/frappe.git
# or, after a plain clone:
git submodule update --init --recursive
```

## Working on an app

Each submodule is a full fork with an upstream link, so you can customize freely and still
pull Frappe's updates:

```bash
cd lms
git remote add upstream https://github.com/frappe/lms.git   # one-time
git fetch upstream && git merge upstream/main               # pull upstream changes
# ...make changes, commit, push to the SWE-Pioneers fork...
git push origin <branch>
```

After moving a submodule to a new commit, record the new pin in this parent repo:

```bash
cd ..            # parent repo root
git add <app>
git commit -m "Bump <app> to <short-sha>"
git push
```

## Related

These apps are built into demo/product images and hosted per the deployment recipe in the
sibling **vps** repo ([SWE-Pioneers/vps-infra](https://github.com/SWE-Pioneers/vps-infra)),
`guides/06-deploying-a-frappe-app.md`.
