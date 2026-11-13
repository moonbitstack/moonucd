#!/usr/bin/env python3
"""Compare the dump of `src/tools/dump_ucd` with a second implementation.

Python's `unicodedata2` is a build of the CPython Unicode database module for
the exact Unicode version this library carries, and `wcwidth` is the other
widely used answer to "how many cells". Every code point is compared, and the
count of differences per property is printed; a difference stops the run with
the first few rows named, so a table that drifts is not mistaken for a pass.

    python scripts/differential/compare.py ucd.tsv
    python scripts/differential/compare.py ucd.tsv --json out.json

`--json` writes the same counts for the README table, and is what CI reads.
"""

import argparse
import json
import sys

import unicodedata2 as ud
import wcwidth

# UAX #44 rule NR2 gives some ranges their name at read time instead of listing
# it: Tangut, its supplement and components, Khitan small script, Nushu, the
# Egyptian hieroglyphs, and the CJK ideographs. CPython derives Hangul and part
# of the CJK ranges; for the rest it answers no name at all. Where the two
# disagree that way the specification wins, and the row is counted as excused
# rather than as a difference, with the block it sits in checked as well.
NR2 = [
    ("TANGUT IDEOGRAPH", ("Tangut", "Tangut Supplement", "Tangut Components")),
    ("TANGUT COMPONENT", ("Tangut Components",)),
    ("KHITAN SMALL SCRIPT CHARACTER", ("Khitan Small Script",)),
    ("NUSHU CHARACTER", ("Nushu",)),
    ("EGYPTIAN HIEROGLYPH", ("Egyptian Hieroglyphs", "Egyptian Hieroglyphs Extended-A")),
    ("CJK UNIFIED IDEOGRAPH", ("CJK Unified Ideographs",)),
]

# The dump's columns, in order.
(
    CP, CATEGORY, CCC, BIDI, EAW, CELLS, NUMERIC_TYPE, NUMERIC_VALUE,
    SCRIPT, BLOCK, UPPER, LOWER, TITLE, FOLD, LINE_BREAK, NAME,
    NFC, NFD, NFKC, NFKD,
) = range(20)

FORMS = {NFC: "NFC", NFD: "NFD", NFKC: "NFKC", NFKD: "NFKD"}
FIELDS = [
    (CATEGORY, "category"),
    (CCC, "combining class"),
    (EAW, "East Asian Width"),
    (CELLS, "terminal cells"),
    (NUMERIC_TYPE, "numeric type"),
    (NUMERIC_VALUE, "numeric value"),
    (NAME, "name"),
    (NFC, "NFC"),
    (NFD, "NFD"),
    (NFKC, "NFKC"),
    (NFKD, "NFKD"),
]


def numeric_type(ch):
    if ud.decimal(ch, None) is not None:
        return "Decimal"
    if ud.digit(ch, None) is not None:
        return "Digit"
    if ud.numeric(ch, None) is not None:
        return "Numeric"
    return ""


def spell(text):
    return " ".join(f"{ord(c):04X}" for c in text)


def excused_name(cp, mine, want, block):
    """True when the only disagreement is the name CPython does not derive."""
    if want != "":
        return False
    for prefix, blocks in NR2:
        if mine == f"{prefix}-{cp:04X}" and block.startswith(blocks):
            return True
    return False


def expected(ch, field):
    """What unicodedata2 and wcwidth say for one field."""
    if field == CATEGORY:
        return ud.category(ch)
    if field == CCC:
        return str(ud.combining(ch))
    if field == EAW:
        return ud.east_asian_width(ch)
    if field == CELLS:
        return str(wcwidth.wcwidth(ch))
    if field == NUMERIC_TYPE:
        return numeric_type(ch)
    if field == NUMERIC_VALUE:
        value = ud.numeric(ch, None)
        return "" if value is None else repr(value)
    if field == NAME:
        return ud.name(ch, "")
    return spell(ud.normalize(FORMS[field], ch))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("table", help="the dump written by src/tools/dump_ucd")
    parser.add_argument("--json", help="write the counts here")
    parser.add_argument("--limit", type=int, default=8, help="differences to name")
    args = parser.parse_args()

    counted = {label: 0 for _, label in FIELDS}
    excused = {label: 0 for _, label in FIELDS}
    compared = 0
    bad = []
    with open(args.table, encoding="utf-8", newline="") as table:
        for line in table:
            f = line.rstrip("\r\n").split("\t")
            if len(f) != 20:
                sys.exit(f"a line has {len(f)} fields, not 20: {line[:80]!r}")
            cp = int(f[CP])
            ch = chr(cp)
            compared += 1
            for field, label in FIELDS:
                mine = f[field]
                if field == NUMERIC_VALUE and mine:
                    mine = repr(float(mine))
                if mine == "*":
                    # Unassigned: the character normalizes to itself, and the
                    # library says so without a table.
                    continue
                want = expected(ch, field)
                if mine == want:
                    continue
                if field == NAME and excused_name(cp, mine, want, f[BLOCK]):
                    excused[label] += 1
                    continue
                counted[label] += 1
                if len(bad) < args.limit:
                    bad.append(f"U+{cp:04X} {label}: we say {mine!r}, "
                               f"unicodedata2 says {want!r}")

    version = getattr(wcwidth, "__version__", "?")
    print(f"compared {compared} code points with unicodedata2 "
          f"{ud.unidata_version} and wcwidth {version}")
    for _, label in FIELDS:
        note = f" ({excused[label]} excused)" if excused[label] else ""
        print(f"  {label:18} {counted[label]:6} different{note}")
    for row in bad:
        print(f"  {row}")
    if args.json:
        with open(args.json, "w", encoding="utf-8", newline="\n") as out:
            json.dump(
                {"code points": compared, "differences": counted, "excused": excused},
                out,
                indent=2,
            )
            out.write("\n")
    return 1 if any(counted.values()) else 0


if __name__ == "__main__":
    sys.exit(main())
