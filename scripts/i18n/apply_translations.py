"""Apply translated JSON batches back into a .po file.

Usage:
    python apply_translations.py <path-to-ar.po> <batch.json> [<batch.json> ...]

Each batch is the format produced by extract_empty.py with "msgstr" filled.
Every applied entry gets the extracted comment
"ai-translated; needs-native-review" (NOT the fuzzy flag - gettext skips
fuzzy entries at compile time, which would silently un-translate the UI).

Placeholder safety is enforced per entry: an entry whose msgstr does not
carry the exact same multiset of placeholders/HTML tags as its msgid is
REJECTED (left untranslated) and reported. Exit code is non-zero if any
entry was rejected, so a re-translation pass can fix them.
"""

import argparse
import json
import sys

import polib

from validate_po import placeholder_mismatch

AI_COMMENT = "ai-translated; needs-native-review"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("po_file")
    ap.add_argument("batches", nargs="+")
    args = ap.parse_args()

    po = polib.pofile(args.po_file, wrapwidth=0)
    index = {}
    for e in po:
        if not e.obsolete and not e.msgid_plural:
            index[(e.msgctxt, e.msgid)] = e

    applied = skipped_missing = skipped_filled = 0
    rejected = []
    for batch_path in args.batches:
        with open(batch_path, encoding="utf-8") as f:
            batch = json.load(f)
        for item in batch:
            msgstr = (item.get("msgstr") or "").strip()
            if not msgstr:
                continue
            entry = index.get((item.get("msgctxt"), item["msgid"]))
            if entry is None:
                skipped_missing += 1
                continue
            if entry.msgstr.strip():
                skipped_filled += 1
                continue
            mismatch = placeholder_mismatch(item["msgid"], msgstr)
            if mismatch:
                rejected.append((item["msgid"], msgstr, mismatch))
                continue
            entry.msgstr = msgstr
            if AI_COMMENT not in (entry.comment or ""):
                entry.comment = (
                    f"{entry.comment}\n{AI_COMMENT}" if entry.comment else AI_COMMENT
                )
            applied += 1

    po.save(args.po_file)
    print(
        f"{args.po_file}: applied {applied}, rejected {len(rejected)} (placeholder mismatch), "
        f"skipped {skipped_missing} unknown msgid, {skipped_filled} already filled"
    )
    if rejected:
        print("\nREJECTED (fix and re-apply):")
        for msgid, msgstr, mismatch in rejected:
            print(f"- msgid: {msgid!r}\n  msgstr: {msgstr!r}\n  mismatch: {mismatch}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
