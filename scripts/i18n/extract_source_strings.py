"""Extract translatable strings directly from app source into a .po file.

A bench-free stand-in for `bench generate-pot-file`: scans source for
translation-wrapped literals and writes/updates an <app>/locale/ar.po with
empty msgstr entries (or merges new msgids into an existing ar.po).

Captured call forms:
  JS / TS / Vue :  __("..."), __('...')            (frappe-ui `__`)
  Python        :  _("..."), _('...')              (frappe `_`)
  Jinja / HTML  :  {{ _("...") }}, _('...')         (same `_`)

Concatenated literals and template-literal / f-string interpolations are NOT
extracted (they can't be a single msgid). This is best-effort: run
`bench generate-pot-file` later to also pick up doctype/report metadata.

Usage:
    python extract_source_strings.py --app-root <path-to-app-repo> \
        --out <path-to/locale/ar.po> [--src DIR ...]

If --src is omitted, sensible defaults are scanned (frontend/src, <pkg>, etc.).
"""

import argparse
import os
import re
import sys

import polib

# match "__(" or "_(" then a single- or double-quoted literal with \-escapes
JS_RE = re.compile(r'\b__\(\s*(?:"((?:[^"\\]|\\.)*)"|\'((?:[^\'\\]|\\.)*)\')')
PY_JINJA_RE = re.compile(r'(?<![\w.])_\(\s*(?:"((?:[^"\\]|\\.)*)"|\'((?:[^\'\\]|\\.)*)\')')

JS_EXT = {".js", ".ts", ".vue", ".jsx", ".tsx"}
PY_EXT = {".py"}
JINJA_EXT = {".html", ".md", ".txt", ".json"}

SKIP_DIRS = {"node_modules", ".git", "dist", "__pycache__", ".vite", "build", "public"}


def _unescape(js_style, s):
    # turn source-level escapes into the actual string value
    out = s.replace('\\"', '"').replace("\\'", "'").replace("\\n", "\n").replace("\\t", "\t")
    out = out.replace("\\\\", "\\")
    return out


def scan_file(path):
    ext = os.path.splitext(path)[1].lower()
    try:
        text = open(path, encoding="utf-8").read()
    except (UnicodeDecodeError, OSError):
        return set()
    found = set()
    if ext in JS_EXT:
        for m in JS_RE.finditer(text):
            found.add(_unescape(True, m.group(1) if m.group(1) is not None else m.group(2)))
    if ext in PY_EXT or ext in JINJA_EXT:
        for m in PY_JINJA_RE.finditer(text):
            found.add(_unescape(False, m.group(1) if m.group(1) is not None else m.group(2)))
    return found


def default_srcs(app_root):
    cands = []
    for rel in ("frontend/src", "desk/src", "src"):
        if os.path.isdir(os.path.join(app_root, rel)):
            cands.append(rel)
    # the python package dir (same name as repo, holds templates/www/py)
    base = os.path.basename(os.path.abspath(app_root))
    if os.path.isdir(os.path.join(app_root, base)):
        cands.append(base)
    return cands


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--app-root", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--src", nargs="*", default=None)
    ap.add_argument("--lang", default="ar")
    args = ap.parse_args()

    srcs = args.src or default_srcs(args.app_root)
    if not srcs:
        print(f"no source dirs found under {args.app_root}", file=sys.stderr)
        return 2

    msgids = set()
    scanned = 0
    for rel in srcs:
        root = os.path.join(args.app_root, rel)
        for dirpath, dirnames, filenames in os.walk(root):
            dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
            for fn in filenames:
                ext = os.path.splitext(fn)[1].lower()
                if ext in JS_EXT or ext in PY_EXT or ext in JINJA_EXT:
                    scanned += 1
                    msgids |= scan_file(os.path.join(dirpath, fn))

    msgids = {m for m in msgids if m.strip()}

    if os.path.exists(args.out):
        po = polib.pofile(args.out, wrapwidth=0)
        existing = {(e.msgctxt, e.msgid) for e in po}
    else:
        po = polib.POFile(wrapwidth=0)
        po.metadata = {
            "Project-Id-Version": "frappe",
            "MIME-Version": "1.0",
            "Content-Type": "text/plain; charset=UTF-8",
            "Content-Transfer-Encoding": "8bit",
            "Language": args.lang,
            "Language-Team": "Arabic",
            "Plural-Forms": (
                "nplurals=6; plural=(n==0 ? 0 : n==1 ? 1 : n==2 ? 2 : "
                "n%100>=3 && n%100<=10 ? 3 : n%100>=11 && n%100<=99 ? 4 : 5);"
            ),
        }
        existing = set()

    added = 0
    for mid in sorted(msgids):
        if (None, mid) in existing:
            continue
        po.append(polib.POEntry(msgid=mid, msgstr=""))
        added += 1

    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    po.save(args.out)
    print(
        f"scanned {scanned} files under {srcs}; unique msgids found={len(msgids)}, "
        f"new added to {args.out}={added}, total now={len(po)}"
    )


if __name__ == "__main__":
    sys.exit(main())
