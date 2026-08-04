# Frappe Sales System Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build `sales_system_setup` — a custom Frappe app that turns a blank ERPNext v16 site into a productized Libyan omnichannel sell-stack (Accounting + POS + Webshop on one backend), configurable per client by a chosen vertical profile (v1: grocery, clothing).

**Architecture:** One ERPNext v16 site per client is the single backend. A new app, `sales_system_setup`, carries (a) idempotent setup functions + fixtures that apply a shared Libyan base and a chosen vertical profile, (b) a pure weight-embedded-barcode parser + POS resolver, and (c) PWA manifests + a role launcher. ERPNext, Webshop, and the built-in POS provide the actual business logic; our app only configures and glues them.

**Tech Stack:** Frappe Framework v16, ERPNext v16, Webshop v16, `payments` fork (Libyan gateways — deferred), `print_designer` fork; Python 3.11 (unittest/`FrappeTestCase` + plain pytest for pure code); Playwright/TypeScript for E2E; `frappe_docker` dev bench; Docker + Traefik for deploy.

**Spec:** [docs/superpowers/specs/2026-08-04-frappe-sales-system-design.md](../specs/2026-08-04-frappe-sales-system-design.md)

## Global Constraints

Every task's requirements implicitly include these (verbatim from the spec):

- **Currency:** LYD. **Language:** Arabic (`ar`) default, **RTL** default.
- **Tax:** no tax enforcement (Libyan govt doesn't enforce); tax templates OFF; books kept clean and **compliance-ready**. CoA = the **baked-in bilingual tree** at `docs/superpowers/assets/coa_libya_ar_en.{md,csv,ods,xlsx}` (207 accounts, AR+EN, ERPNext types/defaults pre-mapped) — copied into the app as `data/coa_libya_ar_en.csv`; tests assert against real accounts (5111 COGS, 1131 Receivable, …).
- **Inventory valuation:** **perpetual** (COGS accuracy first).
- **Payments v1:** cash + **manual methods only** (Cash-on-Delivery + Bank Transfer / mark-as-paid). Libyan gateway is a **later drop-in** — build checkout so the gateway slots into the existing Payment Request flow without reworking the storefront. Do NOT block v1 on the gateway.
- **POS engine:** ERPNext **built-in POS**. Offline POS = cash only.
- **Webshop:** enabled by default for every vertical (online selling is baseline, not a profile).
- **Desktop:** whole ERPNext is **PWA-installable**. Truly offline = POS (browser) only; whole-desk offline comes from on-prem hosting (Spec 2), NOT the browser — do not promise browser-level whole-desk offline.
- **v1 verticals:** grocery + clothing only. Everything else (cafe, pharmacy, electronics, bakery, hardware, dining/hospitality) is roadmap.
- **All setup is idempotent:** re-running any `apply_*` must not duplicate records or error.
- **No Claude attribution** in any commit message (user rule).

---

## File Structure

New app repo `SWE-Pioneers/frappe-sales_system_setup`, added to this monorepo as a submodule at `sales_system_setup/`. Layout:

```
sales_system_setup/
  pyproject.toml
  sales_system_setup/
    __init__.py                     # __version__
    hooks.py                        # app_name, fixtures, after_install, overrides, pwa wiring
    modules.txt                     # "Sales System Setup"
    barcode.py                      # PURE weight-embedded-barcode parser (no frappe imports)
    api.py                          # whitelisted: apply_profile(), resolve_scanned_barcode()
    data/
      coa_libya_ar_en.csv           # baked-in 207-account bilingual CoA (from docs/superpowers/assets/)
    setup/
      __init__.py
      base.py                       # apply_base(): locale, company defaults, domain
      coa.py                        # import_chart_of_accounts(csv) + set_default_accounts()
      coa_defaults.py               # {account_number: Company/MoP field} default map
      webshop.py                    # enable_webshop(): manual-payment checkout
      pwa.py                        # write/serve manifests + launcher config
      profiles/
        __init__.py
        grocery.py                  # apply_grocery()
        clothing.py                 # apply_clothing()
    fixtures/                       # static records exported/committed as JSON
      role.json                     # Cashier, Store Manager, Accountant, Owner
      mode_of_payment.json          # Cash, Bank Transfer
      item_attribute.json           # Size, Colour (clothing)
      workspace.json                # role-based landing workspaces
    sales_system_setup/doctype/
      grocery_barcode_settings/     # Single doctype: embedded-barcode config
    tests/
      __init__.py
      test_barcode.py               # pure pytest
      test_base.py                  # FrappeTestCase
      test_coa.py
      test_grocery.py
      test_clothing.py
      test_webshop.py
      test_apply_profile.py
      # (no sample CoA — tests import the real baked-in data/coa_libya_ar_en.csv)
  Containerfile                     # deploy image (bundles the forks)
  scripts/provision-client.sh       # bench new-site + install + apply_profile
```

Repo-root Playwright specs (existing `tests/` harness) get new files:
```
tests/sales-grocery.spec.ts
tests/sales-clothing.spec.ts
tests/sales-webshop.spec.ts
tests/sales-arabic-rtl.spec.ts
```

**Integration-API note for the implementer:** where a task references an ERPNext/Frappe doctype, hook, or setting (e.g. `POS Profile`, `Webshop Settings`, `Domain Settings`, `override_whitelisted_methods`, the PWA manifest mechanism), **Task 1 checks it out and greps the real source** before wiring. Doctype/field names below are the confident ones; the exact call site is verified in Task 1, not assumed.

---

### Task 1: App scaffold + dev bench + test site

**Files:**
- Create: whole `sales_system_setup/` app skeleton (`pyproject.toml`, `hooks.py`, `modules.txt`, `__init__.py`).
- Create: `sales_system_setup/tests/test_smoke.py`
- Modify: this monorepo `.gitmodules` (add the new submodule).

**Interfaces:**
- Produces: an installable app `sales_system_setup` on a v16 bench; a dev bench with `frappe + erpnext + webshop + payments + print_designer + sales_system_setup`; a test site `test.localhost`.

- [ ] **Step 1: Bring up a dev bench.** Use `frappe_docker` dev container (reliable given local-build network issues). Get frappe v16 + erpnext v16 + webshop v16 on it. Check out the monorepo submodules you need to read: `git submodule update --init erpnext webshop payments print_designer`.
- [ ] **Step 2: Verify integration APIs against source** (fills the "Integration-API note"). Grep and record exact names for: POS scan override / whitelisted method used by the POS page (`grep -rn "get_items\|search_by_term\|barcode" erpnext/erpnext/selling/page/point_of_sale/`), Webshop payment/checkout entry (`grep -rn "payment\|Payment Request\|razorpay" webshop/webshop/`), the PWA manifest mechanism (`grep -rniE "manifest|serviceworker|pwa" frappe/frappe/ | head`). Write findings into `sales_system_setup/INTEGRATION_NOTES.md`.
- [ ] **Step 3: Scaffold the app:** `bench new-app sales_system_setup` (or hand-create the skeleton above). Set `__version__ = "0.1.0"`.
- [ ] **Step 4: Create the test site + install:** `bench new-site test.localhost --install-app erpnext --install-app webshop`, then `bench --site test.localhost install-app sales_system_setup`.
- [ ] **Step 5: Write the smoke test.**

```python
# sales_system_setup/tests/test_smoke.py
import frappe
def test_app_installed():
    assert "sales_system_setup" in frappe.get_installed_apps()
```

- [ ] **Step 6: Run it.** `bench --site test.localhost run-tests --module sales_system_setup.tests.test_smoke` → PASS.
- [ ] **Step 7: Commit** (in the app repo): `feat: scaffold sales_system_setup app + dev bench + smoke test`. Add the submodule pin in the monorepo.

---

### Task 2: Weight-embedded barcode parser (pure, full TDD)

Grocery scales print EAN-13 labels with weight or price embedded. This is a pure function so it needs no bench — plain pytest, textbook TDD.

**Files:**
- Create: `sales_system_setup/barcode.py`
- Test: `sales_system_setup/tests/test_barcode.py`

**Interfaces:**
- Produces:
  - `EmbeddedBarcodeConfig(prefix: str, item_code_slice: tuple[int,int], value_slice: tuple[int,int], value_type: str, value_divisor: int)`
  - `parse_embedded_barcode(code: str, config: EmbeddedBarcodeConfig) -> dict | None` — returns `{"item_code": str, "qty": float}` when `value_type=="weight"`, `{"item_code": str, "amount": float}` when `"price"`, or `None` when `code` doesn't start with `config.prefix` (caller then does a normal item lookup).

- [ ] **Step 1: Write failing tests.**

```python
# sales_system_setup/tests/test_barcode.py
from sales_system_setup.barcode import parse_embedded_barcode, EmbeddedBarcodeConfig

# EAN-13: "2" + 5-digit item code + 5-digit weight(grams) + check digit
WEIGHT_CFG = EmbeddedBarcodeConfig("2", (1, 6), (6, 11), "weight", 1000)
PRICE_CFG  = EmbeddedBarcodeConfig("2", (1, 6), (6, 11), "price", 100)

def test_weight_barcode_parses_item_and_kg():
    # item 00042, 01500 grams -> 1.5 kg
    assert parse_embedded_barcode("2000420150005", WEIGHT_CFG) == {"item_code": "00042", "qty": 1.5}

def test_price_barcode_parses_item_and_amount():
    # item 00042, 01234 -> 12.34 LYD
    assert parse_embedded_barcode("2000420123405", PRICE_CFG) == {"item_code": "00042", "amount": 12.34}

def test_non_matching_prefix_returns_none():
    assert parse_embedded_barcode("6221031492006", WEIGHT_CFG) is None  # normal retail EAN

def test_empty_or_short_code_returns_none():
    assert parse_embedded_barcode("", WEIGHT_CFG) is None
    assert parse_embedded_barcode("2001", WEIGHT_CFG) is None
```

- [ ] **Step 2: Run → FAIL** (`ModuleNotFoundError` / not defined). `pytest sales_system_setup/tests/test_barcode.py -v`
- [ ] **Step 3: Implement.**

```python
# sales_system_setup/barcode.py
from dataclasses import dataclass

@dataclass
class EmbeddedBarcodeConfig:
    prefix: str
    item_code_slice: tuple
    value_slice: tuple
    value_type: str      # "weight" | "price"
    value_divisor: int

def parse_embedded_barcode(code: str, config: EmbeddedBarcodeConfig):
    if not code or not code.startswith(config.prefix):
        return None
    needed = max(config.item_code_slice[1], config.value_slice[1])
    if len(code) < needed:
        return None
    item_code = code[config.item_code_slice[0]:config.item_code_slice[1]]
    raw = code[config.value_slice[0]:config.value_slice[1]]
    if not raw.isdigit():
        return None
    value = int(raw) / config.value_divisor
    key = "qty" if config.value_type == "weight" else "amount"
    return {"item_code": item_code, key: value}
```

- [ ] **Step 4: Run → PASS.**
- [ ] **Step 5: Commit** `feat: pure weight/price embedded-barcode parser`.

---

### Task 3: Shared Libyan base + real bilingual CoA import (207 accounts)

Everything every client gets: locale/company defaults + the **baked-in Libyan CoA** + its ERPNext default-account wiring. The CoA is real and pre-annotated — `docs/superpowers/assets/coa_libya_ar_en.{md,csv,ods,xlsx}` (207 accounts, AR-primary + EN, `account_number`/`account_type`/`root_type` mapped, ERPNext default accounts flagged in the `الاستخدام المقترح` column; read `coa_libya_ar_en.md` for the summary).

**Files:**
- Create: `sales_system_setup/setup/base.py`, `setup/coa.py`, `setup/coa_defaults.py`
- Create data: `sales_system_setup/data/coa_libya_ar_en.csv` (copy of `docs/superpowers/assets/coa_libya_ar_en.csv`)
- Create fixtures: `fixtures/role.json` (Cashier, Store Manager, Accountant, Owner), `fixtures/mode_of_payment.json` (Cash→1111, Bank Transfer→1121), `fixtures/workspace.json`
- Modify: `hooks.py` (`fixtures = ["Role", "Mode of Payment", "Workspace", "Item Attribute"]`)
- Test: `sales_system_setup/tests/test_base.py`, `test_coa.py`

**Interfaces:**
- Produces:
  - `apply_base(company: str) -> None` — System Settings (`country="Libya"`, `currency="LYD"`, `language="ar"`, Libyan number/date formats), RTL on, `Domain Settings` active = `Retail`, Company `default_currency="LYD"` + `enable_perpetual_inventory=1`, ensures Modes of Payment. Idempotent.
  - `import_chart_of_accounts(company: str, csv_path: str = DEFAULT_COA_CSV) -> None` — parse the CSV → build a nested ERPNext `custom_chart` dict (children nested by `Parent Number`; reserved node keys `account_number`,`account_type`,`root_type`,`is_group`) → **validate every `account_type` against `frappe.get_meta("Account").get_field("account_type").options`** (blank + log unknowns — never silently mis-map; watch `Capital Work in Progress` and `Round Off for Opening`, which are version-sensitive) → call `erpnext.accounts.doctype.account.chart_of_accounts.chart_of_accounts.create_charts(company, custom_chart=tree)`. Idempotent: **skip if the company already has non-root accounts** (import into a company created without the standard CoA, else roots duplicate).
  - `set_default_accounts(company: str) -> None` — from the `coa_defaults.py` `{account_number: company_field}` map, wire Company defaults + Mode-of-Payment accounts. **Use only the VERIFIED Company fieldnames in `INTEGRATION_NOTES.md`** (the authoritative table). Core ones: 1131→`default_receivable_account`, 2111→`default_payable_account`, 5111→`default_expense_account` (COGS), 4110→`default_income_account`, 1141→`default_inventory_account`, 2141→`stock_received_but_not_billed`, 5123→`stock_adjustment_account`, 5291→`round_off_account`, 5292→`round_off_for_opening`, 5282→`write_off_account`, 5254→`disposal_account`, 5251→`depreciation_expense_account`, 5263→`exchange_gain_loss_account`; Mode of Payment Cash→1111, Bank Transfer→1121 (MoP `accounts` child table). **Do NOT** set SDBNB 1146 / service-RBNB 2143 / expenses-in-valuation 5121 (no Company field); 1910 (Temporary) is auto-found by account_type and 3310 (Retained Earnings) is chosen at period-closing — neither needs wiring.

- [ ] **Step 1: Copy the CoA data** into the app: `sales_system_setup/data/coa_libya_ar_en.csv` from `docs/superpowers/assets/coa_libya_ar_en.csv`. Set `DEFAULT_COA_CSV` in `setup/coa.py` to that path.
- [ ] **Step 2: Failing test for base.**

```python
# sales_system_setup/tests/test_base.py
import frappe
from frappe.tests.utils import FrappeTestCase
from sales_system_setup.setup.base import apply_base

class TestBase(FrappeTestCase):
    def test_apply_base_sets_locale_and_domain(self):
        apply_base(company="_Test Co LY")
        ss = frappe.get_single("System Settings")
        self.assertEqual(ss.language, "ar")
        self.assertEqual(ss.country, "Libya")
        self.assertIn("Retail", [d.domain for d in frappe.get_single("Domain Settings").active_domains])
        self.assertTrue(frappe.db.exists("Mode of Payment", "Cash"))
        self.assertTrue(frappe.db.exists("Mode of Payment", "Bank Transfer"))

    def test_apply_base_is_idempotent(self):
        apply_base(company="_Test Co LY")
        apply_base(company="_Test Co LY")  # must not raise or duplicate
        self.assertEqual(frappe.db.count("Mode of Payment", {"mode_of_payment": "Cash"}), 1)
```

- [ ] **Step 3: Run → FAIL, implement `apply_base()`** (`frappe.get_single(...).db_set(...)` for settings; `frappe.get_doc({...}).insert(ignore_if_duplicate=True)` for modes of payment; set `Domain Settings`; `enable_perpetual_inventory=1` on Company). Guard every create. **Run → PASS.**
- [ ] **Step 4: Failing test for the REAL CoA import + default wiring.**

```python
# sales_system_setup/tests/test_coa.py
import frappe
from frappe.tests.utils import FrappeTestCase
from sales_system_setup.setup.base import apply_base
from sales_system_setup.setup.coa import import_chart_of_accounts, set_default_accounts

class TestCoa(FrappeTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        apply_base(company="_Test Co LY")
        import_chart_of_accounts(company="_Test Co LY")   # baked-in 207-account CSV
        set_default_accounts(company="_Test Co LY")

    def _acc(self, number):
        return frappe.db.get_value("Account",
            {"account_number": number, "company": "_Test Co LY"},
            ["name", "account_type", "root_type"], as_dict=True)

    def test_key_accounts_imported_with_types(self):
        self.assertEqual(self._acc("5111").account_type, "Cost of Goods Sold")
        self.assertEqual(self._acc("5111").root_type, "Expense")
        self.assertEqual(self._acc("1131").account_type, "Receivable")
        self.assertEqual(self._acc("1111").account_type, "Cash")
        self.assertEqual(self._acc("1141").account_type, "Stock")
        self.assertEqual(self._acc("4110").root_type, "Income")

    def test_company_defaults_wired(self):
        c = frappe.get_doc("Company", "_Test Co LY")
        self.assertEqual(c.default_receivable_account, self._acc("1131").name)
        self.assertEqual(c.default_expense_account, self._acc("5111").name)  # COGS
        self.assertEqual(c.round_off_account, self._acc("5291").name)

    def test_bulk_import_and_idempotency(self):
        self.assertGreaterEqual(frappe.db.count("Account", {"company": "_Test Co LY"}), 200)
        import_chart_of_accounts(company="_Test Co LY")   # re-run: must not duplicate
        self.assertEqual(frappe.db.count("Account",
            {"company": "_Test Co LY", "account_number": "5111"}), 1)
```

- [ ] **Step 5: Run → FAIL. Implement** `setup/coa.py` (CSV→`custom_chart` builder using `Parent Number` links + account-type validation + `create_charts`), `setup/coa_defaults.py` (the account_number→Company-field map above). **Run → PASS.**
- [ ] **Step 6: Commit** `feat: shared Libyan base + baked-in 207-account bilingual CoA + ERPNext default-account wiring`.

---

### Task 4: Grocery profile + POS weight-barcode resolver

**Files:**
- Create: `sales_system_setup/setup/profiles/grocery.py`
- Create: `sales_system_setup/sales_system_setup/doctype/grocery_barcode_settings/` (Single: `prefix`, `item_code_start`, `item_code_end`, `value_start`, `value_end`, `value_type`, `value_divisor`)
- Modify: `sales_system_setup/api.py` (add `resolve_scanned_barcode`), `hooks.py` (POS override per Task-1 findings)
- Test: `sales_system_setup/tests/test_grocery.py`

**Interfaces:**
- Consumes: `apply_base` (Task 3); `parse_embedded_barcode` + `EmbeddedBarcodeConfig` (Task 2).
- Produces:
  - `apply_grocery(company: str, warehouse: str) -> None` — item groups (Produce/Dairy/Beverages/Dry Goods/Household), UOMs (Nos/Kg/Gram) + conversion, a perishable **Item Template** with `has_batch_no=1` + `has_expiry_date=1`, reorder defaults, negative-stock policy, a **POS Profile** (`_Grocery POS`: barcode-first, payments Cash + Bank Transfer, the warehouse + selling price list). Idempotent.
  - `resolve_scanned_barcode(code: str) -> dict` (whitelisted) — reads `Grocery Barcode Settings`, calls `parse_embedded_barcode`; if `None`, resolves `code` as a normal Item Barcode; returns `{"item_code","qty"}` (qty defaults 1 for normal scans).

- [ ] **Step 1: Failing test.**

```python
# sales_system_setup/tests/test_grocery.py
import frappe
from frappe.tests.utils import FrappeTestCase
from sales_system_setup.setup.base import apply_base
from sales_system_setup.setup.profiles.grocery import apply_grocery
from sales_system_setup.api import resolve_scanned_barcode

class TestGrocery(FrappeTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        apply_base(company="_Test Co LY")
        apply_grocery(company="_Test Co LY", warehouse="Stores - _TCL")

    def test_pos_profile_and_uoms_created(self):
        self.assertTrue(frappe.db.exists("POS Profile", "_Grocery POS"))
        self.assertTrue(frappe.db.exists("UOM", "Kg"))
        self.assertTrue(frappe.db.exists("Item Group", "Produce"))

    def test_perpetual_inventory_enabled(self):
        self.assertTrue(frappe.db.get_value("Company", "_Test Co LY", "enable_perpetual_inventory"))

    def test_weight_barcode_resolves_to_item_and_qty(self):
        # seed item "00042" + barcode settings, then scan
        frappe.get_doc({"doctype":"Grocery Barcode Settings","prefix":"2",
            "item_code_start":1,"item_code_end":6,"value_start":6,"value_end":11,
            "value_type":"weight","value_divisor":1000}).save()
        # assumes item 00042 exists (created in fixture/helper)
        out = resolve_scanned_barcode("2000420150005")
        self.assertEqual(out, {"item_code": "00042", "qty": 1.5})
```

- [ ] **Step 2: Run → FAIL.**
- [ ] **Step 3: Create the `Grocery Barcode Settings` Single doctype** (`bench --site test.localhost make-doctype` or JSON), export to the app.
- [ ] **Step 4: Implement `apply_grocery()`** (idempotent creates as in Task 3 style) and `resolve_scanned_barcode()` in `api.py`:

```python
# sales_system_setup/api.py
import frappe
from sales_system_setup.barcode import parse_embedded_barcode, EmbeddedBarcodeConfig

@frappe.whitelist()
def resolve_scanned_barcode(code: str) -> dict:
    s = frappe.get_single("Grocery Barcode Settings")
    parsed = None
    if s.prefix:
        cfg = EmbeddedBarcodeConfig(s.prefix, (s.item_code_start, s.item_code_end),
              (s.value_start, s.value_end), s.value_type, s.value_divisor)
        parsed = parse_embedded_barcode(code, cfg)
    if parsed:
        return {"item_code": parsed["item_code"], "qty": parsed.get("qty", 1)}
    item_code = frappe.db.get_value("Item Barcode", {"barcode": code}, "parent")
    return {"item_code": item_code, "qty": 1}
```

- [ ] **Step 5: Run → PASS.**
- [ ] **Step 6: Wire the POS scan** to call `resolve_scanned_barcode` (client-side hook on the POS page per Task-1 `INTEGRATION_NOTES.md`; a Client Script or a bundled JS `app_include_js`). Manual smoke on the POS page: scanning a weight label adds the item at the embedded kg.
- [ ] **Step 7: Commit** `feat: grocery profile + weight-barcode POS resolver`.

---

### Task 5: Clothing profile (variants + pricing)

**Files:**
- Create: `sales_system_setup/setup/profiles/clothing.py`
- Create fixture: `fixtures/item_attribute.json` (Size: S/M/L/XL/XXL; Colour: a starter set)
- Test: `sales_system_setup/tests/test_clothing.py`

**Interfaces:**
- Consumes: `apply_base` (Task 3).
- Produces: `apply_clothing(company: str, warehouse: str) -> None` — ensures Item Attributes (Size, Colour), a demo **variant template** (`has_variants=1`, attributes Size+Colour) + generates variants, a **Pricing Rule** (season discount example, disabled by default), a **POS Profile** `_Clothing POS` (variant picker + barcode, Cash + Bank Transfer). Idempotent.

- [ ] **Step 1: Failing test.**

```python
# sales_system_setup/tests/test_clothing.py
import frappe
from frappe.tests.utils import FrappeTestCase
from sales_system_setup.setup.base import apply_base
from sales_system_setup.setup.profiles.clothing import apply_clothing

class TestClothing(FrappeTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        apply_base(company="_Test Co LY")
        apply_clothing(company="_Test Co LY", warehouse="Stores - _TCL")

    def test_attributes_exist(self):
        self.assertTrue(frappe.db.exists("Item Attribute", "Size"))
        self.assertTrue(frappe.db.exists("Item Attribute", "Colour"))

    def test_template_generates_variants(self):
        variants = frappe.get_all("Item", filters={"variant_of": "_Test Shirt"})
        self.assertGreaterEqual(len(variants), 2)  # e.g. S/Red, M/Red...

    def test_clothing_pos_profile_created(self):
        self.assertTrue(frappe.db.exists("POS Profile", "_Clothing POS"))
```

- [ ] **Step 2: Run → FAIL. Step 3: Implement `apply_clothing()`** (use `frappe.model.utils` / ERPNext's variant creation — `erpnext.controllers.item_variant.create_variant`; verify exact import in Task 1 notes). **Step 4: Run → PASS.**
- [ ] **Step 5: Commit** `feat: clothing profile (size×colour variants + pricing rule)`.

---

### Task 6: Webshop base enablement (manual payments, v1)

**Files:**
- Create: `sales_system_setup/setup/webshop.py`
- Test: `sales_system_setup/tests/test_webshop.py`

**Interfaces:**
- Consumes: `apply_base` (Task 3).
- Produces: `enable_webshop(company: str, warehouse: str, price_list: str) -> None` — sets **Webshop Settings** (enabled, company, default price list, show stock from `warehouse`), **Shopping Cart** → creates **Sales Order**, checkout payment = **manual** (COD + Bank Transfer instructions; NO gateway). Idempotent. Leaves a clearly-marked seam (`# GATEWAY DROP-IN: set default Payment Gateway Account here when bank registration completes`) so Task-later wiring is trivial.

- [ ] **Step 1: Failing test.**

```python
# sales_system_setup/tests/test_webshop.py
import frappe
from frappe.tests.utils import FrappeTestCase
from sales_system_setup.setup.base import apply_base
from sales_system_setup.setup.webshop import enable_webshop

class TestWebshop(FrappeTestCase):
    def test_webshop_enabled_with_manual_checkout(self):
        apply_base(company="_Test Co LY")
        enable_webshop(company="_Test Co LY", warehouse="Stores - _TCL", price_list="Standard Selling")
        ws = frappe.get_single("Webshop Settings")
        self.assertTrue(ws.enabled)
        self.assertTrue(ws.enable_checkout)  # order can be placed
        # no payment gateway configured in v1
        self.assertFalse(getattr(ws, "payment_gateway_account", None))
```

- [ ] **Step 2: Run → FAIL. Step 3: Implement `enable_webshop()`** (verify exact `Webshop Settings` fieldnames in Task 1; set enabled, `enable_checkout`, default price list, stock warehouse; ensure the two manual Modes of Payment are the offered options). **Step 4: Run → PASS.**
- [ ] **Step 5: Commit** `feat: webshop base enablement with manual (COD/bank-transfer) checkout; gateway seam left for later`.

---

### Task 7: `apply_profile` orchestrator + install hook (idempotency gate)

**Files:**
- Modify: `sales_system_setup/api.py` (add `apply_profile`), `hooks.py` (optional `after_install`)
- Test: `sales_system_setup/tests/test_apply_profile.py`

**Interfaces:**
- Consumes: `apply_base`, `import_chart_of_accounts`, `set_default_accounts`, `apply_grocery`, `apply_clothing`, `enable_webshop`.
- Produces: `apply_profile(profile: str, company: str, warehouse: str, price_list: str = "Standard Selling") -> None` (whitelisted + runnable via `bench execute sales_system_setup.api.apply_profile --kwargs "{...}"`). Runs base → import the baked-in CoA + set default accounts → the vertical → webshop. Rejects unknown profile. Fully idempotent.

- [ ] **Step 1: Failing test.**

```python
# sales_system_setup/tests/test_apply_profile.py
import frappe
from frappe.tests.utils import FrappeTestCase
from sales_system_setup.api import apply_profile

class TestApplyProfile(FrappeTestCase):
    def test_grocery_end_to_end(self):
        apply_profile(profile="grocery", company="_Test Co LY", warehouse="Stores - _TCL")
        self.assertTrue(frappe.db.exists("POS Profile", "_Grocery POS"))
        self.assertTrue(frappe.get_single("Webshop Settings").enabled)

    def test_rerun_is_idempotent(self):
        apply_profile(profile="grocery", company="_Test Co LY", warehouse="Stores - _TCL")
        apply_profile(profile="grocery", company="_Test Co LY", warehouse="Stores - _TCL")
        self.assertEqual(frappe.db.count("POS Profile", {"name": "_Grocery POS"}), 1)

    def test_unknown_profile_raises(self):
        with self.assertRaises(frappe.ValidationError):
            apply_profile(profile="spaceship", company="_Test Co LY", warehouse="Stores - _TCL")
```

- [ ] **Step 2: Run → FAIL. Step 3: Implement `apply_profile()`** (dict dispatch `{"grocery": apply_grocery, "clothing": apply_clothing}`; `frappe.throw` on miss). **Step 4: Run → PASS.**
- [ ] **Step 5: Commit** `feat: apply_profile orchestrator (idempotent, bench-runnable)`.

---

### Task 8: PWA manifests + role launcher

**Files:**
- Create: `sales_system_setup/setup/pwa.py`, manifest assets under `sales_system_setup/public/`
- Modify: `hooks.py` (per Task-1 PWA findings), `fixtures/workspace.json`
- Test: `sales_system_setup/tests/test_pwa.py` (manifest validity) + a manual install check

**Interfaces:**
- Produces: valid web app manifest(s) so POS / Online Store / Accounting / whole desk are installable (name, short_name, icons ≥192+512, `start_url`, `display:"standalone"`, `dir:"rtl"`, `lang:"ar"`); role-based landing workspaces so each role opens into its app.

- [ ] **Step 1: Failing test** (manifest is valid + RTL/ar + required icons):

```python
# sales_system_setup/tests/test_pwa.py
import json, frappe
from frappe.tests.utils import FrappeTestCase
from sales_system_setup.setup.pwa import build_manifest

class TestPwa(FrappeTestCase):
    def test_manifest_is_valid_rtl_arabic(self):
        m = json.loads(build_manifest(app="pos"))
        self.assertEqual(m["display"], "standalone")
        self.assertEqual(m["dir"], "rtl")
        self.assertEqual(m["lang"], "ar")
        sizes = {i["sizes"] for i in m["icons"]}
        self.assertTrue({"192x192", "512x512"} <= sizes)
```

- [ ] **Step 2: Run → FAIL. Step 3: Implement `build_manifest(app)`** returning the JSON; wire serving + service-worker registration + an "Install" affordance per the mechanism recorded in `INTEGRATION_NOTES.md`. Add role workspaces to `fixtures/workspace.json`. **Step 4: Run → PASS.** Manual: Chrome shows "Install" for POS and it opens standalone RTL.
- [ ] **Step 5: Docs honesty:** add to the app README that whole-desk offline is via on-prem hosting (Spec 2), not the browser; only POS is browser-offline.
- [ ] **Step 6: Commit** `feat: PWA manifests (RTL/ar) + role launcher workspaces`.

---

### Task 9: Deployment recipe (image + per-client provisioning)

**Files:**
- Create: `sales_system_setup/Containerfile`, `sales_system_setup/scripts/provision-client.sh`

**Interfaces:**
- Produces: a Docker image bundling `frappe + erpnext + webshop + payments + print_designer + sales_system_setup` with Arabic `.mo` compiled (per the monorepo CLAUDE.md Frappe-v16 translation mechanics: `bench compile-po-to-mo` per app, then `rm -rf assets && cp -a sites/assets assets` AFTER compiling); `provision-client.sh <site> <profile> <company> <warehouse>` = `bench new-site` → `install-app` (erpnext, webshop, sales_system_setup) → `bench execute ...apply_profile`.

- [ ] **Step 1:** Write `Containerfile` starting from the pattern in `~/build/<app>-custom/Containerfile` on the VPS; **`--no-cache` build** (per CLAUDE.md, else stale `get-app` layer). Repoint get-app to `SWE-Pioneers/frappe-*`.
- [ ] **Step 2:** Write `provision-client.sh` (idempotent: skip if site exists). Add Traefik labels `*-<client>.swe.com.ly` following the existing demo-stack compose.
- [ ] **Step 3: Smoke test:** build the image; `provision-client.sh smoke.localhost grocery "Smoke Co" "Stores - SC"`; assert `curl -s localhost/api/method/ping` responds and `_Grocery POS` exists (`bench --site smoke.localhost execute "frappe.db.exists" --args '["POS Profile","_Grocery POS"]'`).
- [ ] **Step 4: Commit** `chore: deploy image + per-client provisioning (apply_profile on new site)`.

---

### Task 10: Verification specs (Playwright + ledger reconciliation)

Behavior-first E2E against a provisioned site. Assert **persisted GL rows**, not UI text.

**Files:**
- Create: `tests/sales-grocery.spec.ts`, `tests/sales-clothing.spec.ts`, `tests/sales-webshop.spec.ts`, `tests/sales-arabic-rtl.spec.ts`

**Interfaces:**
- Consumes: a site provisioned by Task 9 (grocery + clothing profiles).

- [ ] **Step 1: Grocery POS → GL.** Spec: open POS, scan/enter a weight-barcode item, pay Cash, submit; then via API assert the POS Invoice is submitted AND its GL Entries balance (sum debit == sum credit) with Income credited, Cash debited, and (perpetual) COGS + Stock entries present; stock ledger shows the qty decremented in kg. Run → PASS.
- [ ] **Step 2: Clothing variant → correct variant.** Sell a specific Size×Colour variant; assert the **variant** item's stock decremented (not the template) and GL balances. Run → PASS.
- [ ] **Step 3: Webshop order → invoice → reconcile.** Place a cart order, choose Bank Transfer, place; mark the resulting Sales Invoice paid; assert Sales Invoice + Payment Entry GL entries net to zero and the **trial balance is zero** (ledger-invariant). Run → PASS.
- [ ] **Step 4: Arabic/RTL live.** Load POS + storefront; assert `<html dir="rtl" lang="ar">` and a known Arabic label renders (no English leak) — reuse the existing arabic-coverage leak detector. Run → PASS.
- [ ] **Step 5: Commit** `test: e2e grocery/clothing/webshop GL reconciliation + Arabic RTL`.

---

## Self-Review

**1. Spec coverage** — every spec section maps to a task:
- §5 one backend / source-of-truth → Tasks 3,4,7 (base, CoA, orchestrator) + verified in 10.
- §5.3 deployment modes → Task 9 (cloud image + provisioning; on-prem is same image, Spec 2 adds sync).
- §6 shared base → Task 3 (+ fixtures) ; §6 Webshop-by-default → Tasks 6,7.
- §7.1 grocery → Task 4 ; §7.2 clothing → Task 5.
- §8 `sales_system_setup` app → Tasks 1,3–7 ; §9 payments (manual v1 + gateway seam) → Task 6.
- §10 PWA + offline honesty → Task 8 ; §11 custom vs config → the custom parts are exactly Tasks 2,4,6,7,8,9,10.
- §12 verification → Task 10 ; §13 resolutions honored in Global Constraints ; §7.3 roadmap + §15 Spec 2 → out of scope (correctly not tasked).

**2. Placeholder scan** — no "TBD/handle edge cases/similar to Task N". Integration-API uncertainty is handled by Task 1 Step 2 producing `INTEGRATION_NOTES.md` (a real deliverable), not deferred hand-waving.

**3. Type consistency** — `parse_embedded_barcode`/`EmbeddedBarcodeConfig` defined in Task 2, consumed with matching signature in Task 4. `apply_base(company)`, `apply_grocery(company, warehouse)`, `apply_clothing(company, warehouse)`, `enable_webshop(company, warehouse, price_list)`, `import_chart_of_accounts(company, tree)`, `apply_profile(profile, company, warehouse, price_list, coa_path)` — names/params consistent between definition and orchestrator (Task 7) and tests. `resolve_scanned_barcode(code)` returns `{item_code, qty}` consistently in Task 4.

**Known residual risk (flagged, not a placeholder):** exact ERPNext/Frappe wiring for the POS scan override, Webshop Settings fieldnames, and the PWA serve mechanism are confirmed in Task 1 Step 2 before use — the plan names the confident doctypes and defers only the precise call site to that verification deliverable.
