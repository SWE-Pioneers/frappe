# frappe — SWE-Pioneers app monorepo

A single parent repository that ties together SWE-Pioneers' forks of the Frappe
standalone apps as **git submodules**. Each app lives in its own repo under the
[SWE-Pioneers](https://github.com/SWE-Pioneers) org (named `frappe-<app>`, forked from the
upstream `frappe/<app>`), and is referenced here at a pinned commit on a chosen branch.

## Apps

| Submodule path | Repo | Branch |
|---|---|---|
| `blog` | [frappe-blog](https://github.com/SWE-Pioneers/frappe-blog) | version-16 |
| `builder` | [frappe-builder](https://github.com/SWE-Pioneers/frappe-builder) | develop |
| `crm` | [frappe-crm](https://github.com/SWE-Pioneers/frappe-crm) | main |
| `drive` | [frappe-drive](https://github.com/SWE-Pioneers/frappe-drive) | main |
| `erpnext` | [frappe-erpnext](https://github.com/SWE-Pioneers/frappe-erpnext) | version-16 |
| `gameplan` | [frappe-gameplan](https://github.com/SWE-Pioneers/frappe-gameplan) | main |
| `healthcare` | [frappe-healthcare](https://github.com/SWE-Pioneers/frappe-healthcare) | version-16 |
| `helpdesk` | [frappe-helpdesk](https://github.com/SWE-Pioneers/frappe-helpdesk) | main |
| `hrms` | [frappe-hrms](https://github.com/SWE-Pioneers/frappe-hrms) | version-16 |
| `insights` | [frappe-insights](https://github.com/SWE-Pioneers/frappe-insights) | main |
| `lms` | [frappe-lms](https://github.com/SWE-Pioneers/frappe-lms) | main |
| `payments` | [frappe-payments](https://github.com/SWE-Pioneers/frappe-payments) | version-16 |
| `print_designer` | [frappe-print_designer](https://github.com/SWE-Pioneers/frappe-print_designer) | main |
| `webshop` | [frappe-webshop](https://github.com/SWE-Pioneers/frappe-webshop) | version-16 |
| `wiki` | [frappe-wiki](https://github.com/SWE-Pioneers/frappe-wiki) | develop |

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
