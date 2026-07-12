"""Merge an app's main.pot into its ar.po (add msgids present in the POT but
missing from the PO as empty entries), then report the untranslated set.

This is the host-side equivalent of `bench update-po-files --locale ar`:
brings the PO up to the full current string set without a bench, using the
main.pot that Frappe's generate-pot-file already produced.

Usage:
    python sync_pot_to_po.py <app-root> <app-pkg>
      e.g. python sync_pot_to_po.py E:/.../lms lms   -> operates on lms/lms/locale/{main.pot,ar.po}
Prints counts; writes the merged ar.po back in place.
"""
import os
import sys
import polib


def main():
    app_root, pkg = sys.argv[1], sys.argv[2]
    locale = os.path.join(app_root, pkg, "locale")
    pot_path = os.path.join(locale, "main.pot")
    po_path = os.path.join(locale, "ar.po")
    if not os.path.exists(pot_path):
        print(f"{pkg}: no main.pot -> needs bench generate-pot-file (skip host-side merge)")
        return 0
    pot = polib.pofile(pot_path, wrapwidth=0)
    po = polib.pofile(po_path, wrapwidth=0)
    po_keys = {(e.msgctxt, e.msgid) for e in po}
    added = 0
    for e in pot:
        if e.obsolete:
            continue
        key = (e.msgctxt, e.msgid)
        if key not in po_keys:
            po.append(polib.POEntry(msgid=e.msgid, msgctxt=e.msgctxt, msgstr=""))
            po_keys.add(key)
            added += 1
    po.save(po_path)
    entries = [e for e in po if not e.obsolete and not e.msgid_plural]
    empty = sum(1 for e in entries if not e.msgstr.strip())
    print(f"{pkg}: pot={len([e for e in pot if not e.obsolete])} po_total={len(entries)} "
          f"added_from_pot={added} now_empty={empty} translated={len(entries)-empty}")


if __name__ == "__main__":
    sys.exit(main())
