# i18n pipeline — AI-assisted Arabic translation for the app forks

Fills the empty `msgstr` entries in each app's `<app>/<app>/locale/ar.po` with
Libyan-appropriate Modern Standard Arabic, tagged `ai-translated; needs-native-review`
for a later native-speaker review pass (grep the .po for that comment).

Requires: Python 3.10+, `pip install polib`.

## Run order (per app)

```bash
# 1. (on a bench, when available) refresh msgids first:
#    bench generate-pot-file --app <app> && bench update-po-files --app <app> --locale ar

# 2. extract untranslated entries into JSON batches
python extract_empty.py <app>/<app>/locale/ar.po /tmp/<app>_batches

# 3. translate: fill the "msgstr" field of every object in each batch_NNN.json
#    (done by Claude subagents; rules: glossary_ar.csv, placeholders byte-identical,
#    HTML tags/punctuation preserved, brand names untranslated, no diacritics)

# 4. apply — rejects any entry whose placeholders don't match; fix and re-run until 0 rejected
python apply_translations.py <app>/<app>/locale/ar.po /tmp/<app>_batches/batch_*.json

# 5. hard validation gate (also wired for CI)
python validate_po.py <app>/<app>/locale/ar.po

# 6. (on a bench) bench compile-po-to-mo --app <app>, smoke-test UI with user language ar
```

Commit only the `.po` file to the app fork (branch `feat/arabic`).

## Files

- `extract_empty.py` — dump empty-msgstr entries to JSON batches (skips plural/fuzzy, reports counts)
- `apply_translations.py` — apply filled batches; per-entry placeholder gate; adds the review comment; never sets `fuzzy` (gettext would skip those at compile)
- `validate_po.py` — file-level gate: placeholder multiset equality ({0}/{n}, %(x)s, %s/%d, HTML tags), parse round-trip, duplicate check
- `glossary_ar.csv` — term consistency across all apps (Course=دورة تدريبية, Invoice=فاتورة, ...)
