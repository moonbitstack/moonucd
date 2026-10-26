#!/usr/bin/env python3
"""Write src/width/tables.mbt and test vectors from wcwidth 0.2.14 and the UCD.

`moonucd/width` answers the terminal-cell width questions. `east_asian_width`
is the UCD `ea` property, checked against CPython's unicodedata. `width` is
Markus Kuhn's wcwidth as shipped by wcwidth 0.2.14 — its latest table is the
Unicode 17.0.0 one — and `text_width` is wcswidth from the same source.

    python scripts/tables/gen_width.py
"""

import argparse
import sys

sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parent))

import ucd
import unicodedata2 as ud
import wcwidth as wcw
from wcwidth.wcwidth import WIDE_EASTASIAN, ZERO_WIDTH
from wcwidth.table_vs16 import VS16_NARROW_TO_WIDE

ROOT = ucd.ROOT
SRC = ROOT / "src" / "width"
VERSION = "17.0.0"

# East Asian Width property codes (UCD `ea`); 'N' IS stored because
# EastAsianWidth.txt nests 'N' exceptions inside broader ranges, and the lookup
# must pick the innermost (last) matching range.
EAW_CODE = {"A": 0, "F": 1, "H": 2, "N": 3, "Na": 4, "W": 5}
# The letter a digest folds.
EAW_DIGEST = {"A": 0, "F": 1, "H": 2, "N": 3, "Na": 4, "W": 5}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--version", default=VERSION)
    version = parser.parse_args().version

    # ---- width tables straight from wcwidth 0.2.14 (latest == 17.0.0) ----
    zero = ZERO_WIDTH[version]   # list of (start, end)
    wide = WIDE_EASTASIAN[version]
    vs16 = VS16_NARROW_TO_WIDE["9.0.0"]

    # ---- east_asian_width from EastAsianWidth.txt (complete, 'N' included) ----
    text = ucd.fetch(version, "EastAsianWidth.txt")
    eaw = []  # (start, end, code) for every range the file lists
    for f in ucd.records(text):
        a, b = ucd.span(f[0])
        prop = f[1]
        eaw.append((a, b, EAW_CODE[prop]))
    eaw.sort(key=lambda x: x[0])

    lines = ucd.header("gen_width.py", version) + [
        "",
        "///|",
        f'let ucd_version : String = "{version}"',
        "",
        "///|",
        "/// wcwidth 0.2.14 zero-width ranges (Unicode 17.0.0): every code point",
        "/// here takes no terminal cell.",
        ucd.mbt_ints("zero_starts", [a for a, _ in zero]),
        "",
        "///|",
        ucd.mbt_ints("zero_ends", [b for _, b in zero]),
        "",
        "///|",
        "/// wcwidth 0.2.14 wide (Fullwidth/Wide) ranges: a hit adds one cell.",
        ucd.mbt_ints("wide_starts", [a for a, _ in wide]),
        "",
        "///|",
        ucd.mbt_ints("wide_ends", [b for _, b in wide]),
        "",
        "///|",
        "/// wcwidth 0.2.14 VS16 (U+FE0F) narrow-to-wide ranges (9.0.0), used by",
        "/// text_width to widen an Emoji that gained a presentation form.",
        ucd.mbt_ints("vs16_starts", [a for a, _ in vs16]),
        "",
        "///|",
        ucd.mbt_ints("vs16_ends", [b for _, b in vs16]),
        "",
        "///|",
        "/// East Asian Width ranges from EastAsianWidth.txt, every range the",
        "/// file lists (including 'N', which nests inside broader ranges).",
        "/// Codes: A=0 F=1 H=2 N=3 Na=4 W=5.",
        ucd.mbt_ints("eaw_starts", [a for a, _, _ in eaw]),
        "",
        "///|",
        ucd.mbt_ints("eaw_ends", [b for _, b, _ in eaw]),
        "",
        "///|",
        ucd.mbt_ints("eaw_codes", [c for _, _, c in eaw]),
        "",
    ]
    ucd.write(SRC / "tables.mbt", lines)
    print(f"  zero={len(zero)} wide={len(wide)} vs16={len(vs16)} eaw={len(eaw)}")

    # ---- conformance digests -------------------------------------------
    width_digest = 0x811C9DC5
    eaw_digest = 0x811C9DC5
    for cp in range(0x110000):
        w = wcw.wcwidth(chr(cp))
        width_digest = ((width_digest ^ (w & 0xFFFFFFFF)) * 0x01000193) & 0xFFFFFFFF
        eaw_digest = (
            (eaw_digest ^ EAW_DIGEST[ud.east_asian_width(chr(cp))]) * 0x01000193
        ) & 0xFFFFFFFF

    # text_width probes: strings wcswidth must agree with, measured now.
    probes = [
        "",
        "A",
        "hello",
        "hello, world",
        "日本語",
        "日本語のテスト",
        "A\u200dB",
        "1\uFE0F",
        "©",
        "😀",
        "\u1F600\u1F600",
        "A\u1F600",
        "abc\u0301",
        "\u0915\u093c",
        "→",
        "　",
        "Café",
        "\u2615",
        "🫶",
    ]
    probe_expect = [wcw.wcswidth(p) for p in probes]

    vectors = ucd.header(
        "gen_width.py", version, "Test vectors only; not part of the package."
    ) + [
        "",
        "///|",
        f"let width_digest : UInt32 = {width_digest}",
        "",
        "///|",
        f"let eaw_digest : UInt32 = {eaw_digest}",
        "",
        "///|",
        "/// Strings text_width is checked against, in order, paired with the",
        "/// width wcswidth gives them (see text_width_expect).",
        "let text_width_probes : Array[String] = [",
        *[f"  {ucd.quote(p)}," for p in probes],
        "]",
        "",
        "///|",
        "/// The widths wcswidth assigns the probe strings above.",
        "let text_width_expect : Array[Int] = [",
        *[f"  {e}," for e in probe_expect],
        "]",
        "",
    ]
    ucd.write(SRC / "width_vectors_test.mbt", vectors)
    print(f"  width_digest={width_digest} eaw_digest={eaw_digest}")


if __name__ == "__main__":
    main()
