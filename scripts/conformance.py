#!/usr/bin/env python3
"""The conformance counts, read from the vectors the tests replay.

The official test files are turned into MoonBit vectors by `scripts/tables`;
each vector records how many cases the file holds, and the test that replays
it checks that the record still matches the data. This script reads those
records so the numbers in the README and in a review cannot drift from the
repository:

    python scripts/conformance.py           # print the table
    python scripts/conformance.py --write   # rewrite the README table
    python scripts/conformance.py --check   # fail if the README table is stale

The README block is the one between `<!-- conformance -->` and
`<!-- /conformance -->`; the table there is the only place the counts appear.
"""

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# suite, the file the Standard ships, the vector that holds the cases, the
# constant in that vector, and how the README names it
SUITES = [
    ("grapheme cluster boundaries", "GraphemeBreakTest.txt", "src/segment/segment_vectors_test.mbt", "grapheme_case_count"),
    ("sentence boundaries", "SentenceBreakTest.txt", "src/segment/segment_vectors_test.mbt", "sentence_case_count"),
    ("word boundaries", "WordBreakTest.txt", "src/segment/segment_vectors_test.mbt", "word_case_count"),
    ("line-break opportunities", "LineBreakTest.txt", "src/linebreak/linebreak_vectors_test.mbt", "lb_case_count"),
    ("normalization", "NormalizationTest.txt", "src/normalize/normalize_vectors_test.mbt", "nt_source_count"),
]

BEGIN = "<!-- conformance -->"
END = "<!-- /conformance -->"
TABLE = re.compile(re.escape(BEGIN) + r".*?" + re.escape(END), re.S)


def count(path, name):
    text = (ROOT / path).read_text(encoding="utf-8")
    found = re.search(rf"^let {name} : Int32 = (\d+)$", text, re.M)
    if found is None:
        raise SystemExit(f"{path} has no `let {name}`")
    return int(found.group(1))


def rows():
    return [
        {"suite": suite, "file": file, "cases": count(path, name)}
        for suite, file, path, name in SUITES
    ]


def block(rows):
    lines = [BEGIN, "| File | Cases |", "|:--|--:|"]
    for row in rows:
        lines.append(f"| `{row['file']}` | {row['cases']:,} |")
    lines.append(END)
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--json", action="store_true", help="print the table as JSON")
    parser.add_argument("--write", action="store_true", help="rewrite the README table")
    parser.add_argument("--check", action="store_true", help="fail if the README table is stale")
    args = parser.parse_args()

    measured = rows()
    if args.json:
        print(json.dumps(measured, indent=2))
        return 0
    if not (args.write or args.check):
        width = max(len(row["file"]) for row in measured)
        for row in measured:
            print(f"{row['suite']:26} {row['file']:<{width}} {row['cases']:>7} cases")
        print(f"{'total':26} {'':<{width}} {sum(r['cases'] for r in measured):>7} cases")
        return 0

    readme = ROOT / "README.md"
    text = readme.read_text(encoding="utf-8")
    if not TABLE.search(text):
        sys.exit("README.md has no conformance block")
    updated = TABLE.sub(block(measured), text, count=1)
    if args.write:
        readme.write_text(updated, encoding="utf-8", newline="\n")
        print("README.md: the conformance table is up to date")
        return 0
    if updated != text:
        print("README.md: the conformance table does not match the vectors")
        print(block(measured))
        return 1
    print("README.md: the conformance table matches the vectors")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
