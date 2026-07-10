"""Validation gate for .po translation files.

Usage:
    python validate_po.py <path-to.po> [<path-to.po> ...]

Checks, for every translated (non-empty msgstr) entry:
  - placeholder multiset equality between msgid and msgstr for all classes:
      {0} / {n} / {name}   curly placeholders
      %(name)s / %(n)d     python named
      %s / %d              python positional
      <b> / </a> ...       HTML tags
  - the file round-trips through polib (syntax)
  - no duplicate (msgctxt, msgid) pairs

Exits non-zero and prints offending msgids on any violation.
"""

import re
import sys
from collections import Counter

import polib

RE_CURLY = re.compile(r"\{[^{}]*\}")
RE_PYNAMED = re.compile(r"%\(\w+\)[sdfr]")
RE_PYPOS = re.compile(r"%[sdfr]")
RE_HTML = re.compile(r"</?[a-zA-Z][^>]*>")


def _tokens(text):
    named = RE_PYNAMED.findall(text)
    # remove named matches before scanning positional so %(x)s doesn't double-count
    stripped = RE_PYNAMED.sub("", text)
    return {
        "curly": Counter(RE_CURLY.findall(text)),
        "named": Counter(named),
        "pos": Counter(RE_PYPOS.findall(stripped)),
        "html": Counter(t.lower() for t in RE_HTML.findall(text)),
    }


def placeholder_mismatch(msgid, msgstr):
    """Return a human-readable mismatch description, or None if OK."""
    a, b = _tokens(msgid), _tokens(msgstr)
    problems = []
    for kind in a:
        if a[kind] != b[kind]:
            problems.append(f"{kind}: msgid has {dict(a[kind])}, msgstr has {dict(b[kind])}")
    return "; ".join(problems) or None


def validate_file(path):
    errors = []
    try:
        po = polib.pofile(path, wrapwidth=0)
    except Exception as exc:  # syntax error
        return [f"{path}: failed to parse: {exc}"]

    seen = set()
    for e in po:
        if e.obsolete:
            continue
        key = (e.msgctxt, e.msgid)
        if key in seen:
            errors.append(f"duplicate msgid: {e.msgid!r} (msgctxt={e.msgctxt!r})")
        seen.add(key)
        targets = [e.msgstr] if not e.msgid_plural else list(e.msgstr_plural.values())
        for t in targets:
            if not t.strip():
                continue
            mismatch = placeholder_mismatch(e.msgid, t)
            if mismatch:
                errors.append(f"placeholder mismatch in {e.msgid!r} -> {t!r}: {mismatch}")
    return [f"{path}: {err}" for err in errors]


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return 2
    all_errors = []
    for path in sys.argv[1:]:
        all_errors.extend(validate_file(path))
    if all_errors:
        print(f"FAILED: {len(all_errors)} problem(s)")
        for err in all_errors:
            print(f"  {err}")
        return 1
    print(f"OK: {len(sys.argv) - 1} file(s) validated")
    return 0


if __name__ == "__main__":
    sys.exit(main())
