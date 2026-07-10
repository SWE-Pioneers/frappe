"""Extract untranslated entries from a .po file into JSON batch files.

Usage:
    python extract_empty.py <path-to-ar.po> <output-dir> [--batch-size 120]

Writes batch_000.json, batch_001.json, ... Each is a list of objects:
    {"msgctxt": str|null, "msgid": str, "msgstr": ""}
The translator fills "msgstr" and the file is fed to apply_translations.py.

Plural entries (msgid_plural) and fuzzy entries are skipped and counted;
they need manual handling.
"""

import argparse
import json
import os
import sys

import polib


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("po_file")
    ap.add_argument("out_dir")
    ap.add_argument("--batch-size", type=int, default=120)
    args = ap.parse_args()

    po = polib.pofile(args.po_file, wrapwidth=0)
    os.makedirs(args.out_dir, exist_ok=True)

    todo = []
    n_plural = n_fuzzy = n_translated = 0
    for e in po:
        if e.obsolete:
            continue
        if e.msgid_plural:
            n_plural += 1
            continue
        if "fuzzy" in e.flags:
            n_fuzzy += 1
            continue
        if e.msgstr.strip():
            n_translated += 1
            continue
        todo.append({"msgctxt": e.msgctxt, "msgid": e.msgid, "msgstr": ""})

    for i in range(0, len(todo), args.batch_size):
        batch = todo[i : i + args.batch_size]
        path = os.path.join(args.out_dir, f"batch_{i // args.batch_size:03d}.json")
        with open(path, "w", encoding="utf-8") as f:
            json.dump(batch, f, ensure_ascii=False, indent=1)

    n_batches = (len(todo) + args.batch_size - 1) // args.batch_size
    print(
        f"{args.po_file}: {len(todo)} untranslated -> {n_batches} batches in {args.out_dir} "
        f"(already translated: {n_translated}, skipped plural: {n_plural}, skipped fuzzy: {n_fuzzy})"
    )


if __name__ == "__main__":
    sys.exit(main())
