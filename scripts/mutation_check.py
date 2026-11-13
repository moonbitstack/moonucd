#!/usr/bin/env python3
"""Break one line at a time and check that a test notices.

A test suite is only as good as the mistakes it catches. Each mutation below
is a real edit to the source that makes the library wrong in a way a reader
would care about; the script applies it, runs the tests on the native target,
records which tests go red, and puts the file back. A mutation with no failing
test means the suite does not cover that line, and the run says so.

    python scripts/mutation_check.py
    python scripts/mutation_check.py --only 3

Nothing is committed by this script; it leaves the working tree as it found it.
"""

import argparse
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# file, the text to break, the text that breaks it, what the mistake would do
MUTATIONS = [
    (
        "src/moonucd.mbt",
        "    Some(i) => categories[category_values[i]]\n    None => Cn",
        "    Some(i) => categories[category_values[i]]\n    None => Co",
        "an unassigned code point is reported as private use",
    ),
    (
        "src/normalize/normalize.mbt",
        "      if a.ccc > 0 && b.ccc > 0 && a.ccc > b.ccc {",
        "      if a.ccc > 0 && b.ccc > 0 && a.ccc < b.ccc {",
        "canonical ordering sorts the marks by descending combining class",
    ),
    (
        "src/segment/span.mbt",
        "  if at < 0 || at >= s.length() {",
        "  if at >= s.length() {",
        "a negative offset is reported as the piece at the start of the string",
    ),
    (
        "src/linebreak/breaks.mbt",
        "      let mandatory = cls == lb_bk ||",
        "      let mandatory = cls == lb_sp ||",
        "a mandatory break is reported as an optional one",
    ),
    (
        "src/name/name.mbt",
        '  "HANGUL SYLLABLE " +',
        '  "HANGUL SYLLABLES " +',
        "the Hangul name rule spells its prefix wrong",
    ),
    (
        "src/width/width.mbt",
        "    Some(a) if w == 1 && east_asian_width(ch) == Eaw::A => a",
        "    Some(_) if w == 1 && east_asian_width(ch) == Eaw::A => 1",
        "an ambiguous character ignores the width the caller asked for",
    ),
    (
        "src/block/block.mbt",
        '  if key.has_prefix("is") {',
        "  if false {",
        "the leading `Is` of a block name is no longer dropped",
    ),
    (
        "src/script/script.mbt",
        "    None => [script(ch)]",
        "    None => []",
        "a character used in one script only answers no script at all",
    ),
]

FAILED = re.compile(r"^\[[^\]]+\] test [^ ]+ \(\"([^\"]+)\"\) failed", re.M)
FAILED_PANIC = re.compile(r"^\[[^\]]+\] test ([^ ]+) failed", re.M)


def run_tests():
    result = subprocess.run(
        ["moon", "test", "--target", "native"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    out = result.stdout + result.stderr
    names = FAILED.findall(out) or FAILED_PANIC.findall(out)
    return result.returncode, names, out


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--only", type=int, help="run the mutation with this number")
    args = parser.parse_args()

    clean, _, _ = run_tests()
    if clean != 0:
        sys.exit("the tests are already failing; nothing to learn from a mutation")

    caught = 0
    for i, (rel, old, new, note) in enumerate(MUTATIONS, start=1):
        if args.only is not None and args.only != i:
            continue
        path = ROOT / rel
        original = path.read_text(encoding="utf-8")
        if original.count(old) != 1:
            print(f"{i}. {rel}: the line to break is not there exactly once")
            continue
        path.write_text(original.replace(old, new), encoding="utf-8", newline="\n")
        try:
            code, names, out = run_tests()
        finally:
            path.write_text(original, encoding="utf-8", newline="\n")
        if code == 0:
            print(f"{i}. {rel}: {note}\n   NOT CAUGHT: every test still passes")
            continue
        caught += 1
        shown = ", ".join(dict.fromkeys(names)) or "the build stopped"
        print(f"{i}. {rel}: {note}\n   caught by: {shown}")

    print(f"{caught} of {len(MUTATIONS)} mutations were caught")
    return 0 if caught == len(MUTATIONS) else 1


if __name__ == "__main__":
    sys.exit(main())
