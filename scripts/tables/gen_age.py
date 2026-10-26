#!/usr/bin/env python3
"""Write src/age/tables.mbt and the test vectors from the UCD.

DerivedAge.txt says when each code point was first assigned; a code point
that is still unassigned has no age at all.

    python scripts/tables/gen_age.py
"""

import argparse
import sys

sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parent))

import ucd

ROOT = ucd.ROOT
SRC = ROOT / "src" / "age"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--version", default="17.0.0")
    version = parser.parse_args().version
    text = ucd.fetch(version, "DerivedAge.txt")

    ages = []
    for f in ucd.records(text):
        a, b = ucd.span(f[0])
        major, minor = (int(x) for x in f[1].split("."))
        ages.append((a, b, major, minor))

    # DerivedAge.txt groups ranges by version, so the file is *not* sorted by
    # code point; sort the runs by start so the binary search can rely on it.
    ages.sort(key=lambda x: x[0])

    lines = ucd.header("gen_age.py", version) + [
        "",
        "///|",
        f'let ucd_version : String = "{version}"',
        "",
        "///|",
        "/// When each code point was first assigned, as runs over the code space.",
        ucd.mbt_ints("age_starts", [a for a, _, _, _ in ages]),
        "",
        "///|",
        ucd.mbt_ints("age_ends", [b for _, b, _, _ in ages]),
        "",
        "///|",
        ucd.mbt_ints("age_major", [m for _, _, m, _ in ages]),
        "",
        "///|",
        ucd.mbt_ints("age_minor", [n for _, _, _, n in ages]),
        "",
    ]
    ucd.write(SRC / "tables.mbt", lines)
    print(f"  {len(ages)} age runs")

    # ---- test vectors -------------------------------------------------
    def fnv(seq):
        h = 0x811C9DC5
        for x in seq:
            h = ((h ^ (x & 0xFFFFFFFF)) * 0x01000193) & 0xFFFFFFFF
        return h

    seq = []
    for cp in range(0x110000):
        if 0xD800 <= cp <= 0xDFFF:
            continue
        for a, b, major, minor in ages:
            if a <= cp <= b:
                seq += [major, minor]
                break
        else:
            seq += [255, 255]
    h = fnv(seq)
    print(f"  age digest {h}")

    vectors = ucd.header("gen_age.py", version, "Test vectors only; not part of the package.") + [
        "",
        "///|",
        f"let age_digest : UInt32 = {h}",
        "",
    ]
    ucd.write(SRC / "age_vectors_test.mbt", vectors)


if __name__ == "__main__":
    main()
