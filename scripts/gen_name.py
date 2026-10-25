#!/usr/bin/env python3
"""Write src/name/tables.mbt, src/name/name_vectors_test.mbt and the lookup
tables from the Unicode Character Database 17.0.0.

`moonucd/name` answers two questions the Standard poses about a code point:
its name, and which code point a name names. The names that the database
gives by formula (every CJK Unified Ideograph and every Hangul Syllable) are
computed, not stored; everything else is kept in a compact name pool. The
lookup table holds the normalised (UAX #44 LM2) form of every canonical
name and every NameAliases alias.

    python scripts/gen_name.py
"""

import argparse
import re
import sys

sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parent))

import ucd
import unicodedata2 as ud

ROOT = ucd.ROOT
SRC = ROOT / "src" / "name"

# Algorithmic ranges Python's unicodedata names directly from the code point.
# Every marker below is one CPython's name() resolves; the Tangut Ideograph
# markers are deliberately absent because unicodedata returns no name for them.
CJK_MARKERS = [
    (0x3400, 0x4DBF),
    (0x4E00, 0x9FFF),
    (0x20000, 0x2A6DF),
    (0x2A700, 0x2B73F),
    (0x2B740, 0x2B81D),
    (0x2B820, 0x2CEAD),
    (0x2CEB0, 0x2EBE0),
    (0x2EBF0, 0x2EE5D),
    (0x30000, 0x3134A),
    (0x31350, 0x323AF),
    (0x323B0, 0x33479),
]
HANGUL_START = 0xAC00
HANGUL_END = 0xD7A3
LBASE, VBASE, TBASE, SBASE = 0x1100, 0x1161, 0x11A7, 0xAC00
LCOUNT, VCOUNT, TCOUNT, NCOUNT = 19, 21, 28, 588


def lm2(name):
    """UAX #44 LM2: upper case, ignore spaces, underscores, medial hyphens —
    except the hyphen in U+1180's name, which is significant."""
    up = name.upper()
    key = up.replace(" ", "").replace("_", "")
    if up == "HANGUL JUNGSEONG O-E":
        return key
    return key.replace("-", "")


def in_cjk(cp):
    return any(a <= cp <= b for a, b in CJK_MARKERS)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--version", default="17.0.0")
    version = parser.parse_args().version
    data = ucd.fetch(version, "UnicodeData.txt")
    aliases_text = ucd.fetch(version, "NameAliases.txt")

    # ---- the name pool: every name Python gives, stored verbatim ----
    # CJK Unified Ideographs and Hangul Syllables are named by formula in the
    # Standard, but the Extension blocks have unassigned gaps where the database
    # gives no name; storing the names Python actually returns keeps `name`
    # exact without a formula that must second-guess assignment.
    names = {}
    for cp in range(0x110000):
        if 0xD800 <= cp <= 0xDFFF:
            continue
        try:
            nm = ud.name(chr(cp))
        except ValueError:
            continue
        names[cp] = nm

    cps = sorted(names)
    pool = "".join(names[cp] for cp in cps)
    offsets = [0]
    for cp in cps:
        offsets.append(offsets[-1] + len(names[cp]))

    # ---- the lookup table: normalised name -> code point ----
    # Canonical names first so they win over aliases; aliases keep file order.
    lookup = {}
    for cp in range(0x110000):
        if 0xD800 <= cp <= 0xDFFF:
            continue
        if in_cjk(cp):
            continue
        try:
            nm = ud.name(chr(cp))
        except ValueError:
            continue
        lookup.setdefault(lm2(nm), cp)
    for line in ucd.records(aliases_text):
        cp = int(line[0], 16)
        alias = line[1]
        lookup.setdefault(lm2(alias), cp)
    lk_pairs = sorted((k, v) for k, v in lookup.items())
    lk_keys = "".join(k for k, _ in lk_pairs)
    lk_offsets = [0]
    for k, _ in lk_pairs:
        lk_offsets.append(lk_offsets[-1] + len(k))
    lk_values = [v for _, v in lk_pairs]

    # ---- tables.mbt ----------------------------------------------------------
    lines = ucd.header("gen_name.py", version) + [
        "",
        "///|",
        f'let ucd_version : String = "{version}"',
        "",
        "///|",
        "/// Code points that carry an explicit name, in ascending order.",
        ucd.mbt_ints("name_cps", cps),
        "",
        "///|",
        "/// Every explicit name, packed back to back; `name_offsets` marks them.",
        ucd.mbt_string_pool("name_pool", pool, width=60),
        "",
        "///|",
        "/// One past the end of each name in `name_pool`, in code points.",
        ucd.mbt_ints("name_offsets", offsets, typ="Int"),
        "",
        "///|",
        "/// The CJK Unified Ideograph ranges the database names.",
        ucd.mbt_ints("cjk_starts", [a for a, _ in CJK_MARKERS]),
        "",
        "///|",
        ucd.mbt_ints("cjk_ends", [b for _, b in CJK_MARKERS]),
        "",
        "///|",
        "/// Normalised (UAX #44 LM2) names, sorted so `lookup` can binary search.",
        ucd.mbt_ints("lookup_values", lk_values),
        "",
        "///|",
        ucd.mbt_string_pool("lookup_pool", lk_keys, width=60),
        "",
        "///|",
        "/// One past the end of each key in `lookup_pool`, in code points.",
        ucd.mbt_ints("lookup_offsets", lk_offsets, typ="Int"),
        "",
    ]
    ucd.write(SRC / "tables.mbt", lines)
    print(f"  {len(cps)} explicit names, {len(lk_pairs)} lookup entries")

    # ---- the name digest: replicate name() over every scalar value ----
    def name_digest():
        h = 0x811C9DC5
        for cp in range(0x110000):
            if 0xD800 <= cp <= 0xDFFF:
                continue
            try:
                nm = ud.name(chr(cp))
            except ValueError:
                nm = None
            if nm is None:
                h = ((h ^ 0) * 0x01000193) & 0xFFFFFFFF
            else:
                h = ((h ^ len(nm)) * 0x01000193) & 0xFFFFFFFF
                for ch in nm:
                    h = ((h ^ ord(ch)) * 0x01000193) & 0xFFFFFFFF
        return h

    nd = name_digest()

    # ---- lookup probe set: names Python resolves, plus LM2 variants ----
    probes = []
    for cp in [
        0x0041, 0x03B1, 0x1F514, 0x00E9, 0x4E00, 0x20000, 0xAC00, 0xB098,
        0xD7A3, 0x18800, 0x1B170, 0x18B00, 0x1180, 0x116C, 0x000D, 0x000A,
        0x09, 0x0A,
    ]:
        try:
            probes.append(ud.name(chr(cp)))
        except ValueError:
            pass
    probes += [
        "LATIN CAPITAL LETTER A", "latin capital letter a", "LATIN CAPITAL LETTER A",
        "GREEK SMALL LETTER ALPHA", "BELL", "CJK UNIFIED IDEOGRAPH-4E00",
        "HANGUL SYLLABLE GA", "HANGUL SYLLABLE NA", "TANGUT COMPONENT-001",
        "NUSHU CHARACTER-1B170", "KHITAN SMALL SCRIPT CHARACTER-18B00",
        "CARRIAGE RETURN", "LINE FEED", "CR", "LF", "HT", "TAB",
        "HANGUL JUNGSEONG O-E", "HANGUL JUNGSEONG OE",
        "LATIN-CAPITAL_LETTER A", "nonexistent name", "", "GREEK SMALL LETTER ALPHA X",
    ]

    def parse_cjk(pat):
        """Resolve a CJK UNIFIED IDEOGRAPH-XXXX probe to a code point."""
        if pat.startswith("CJKUNIFIEDIDEOGRAPH"):
            tail = pat[len("CJKUNIFIEDIDEOGRAPH"):]
            if all(c in "0123456789ABCDEF" for c in tail):
                cp = int(tail, 16)
                if in_cjk(cp):
                    return cp
        return None

    def lookup_ref(nm):
        if not nm:
            return None
        pat = lm2(nm)
        cjk = parse_cjk(pat)
        if cjk is not None:
            return cjk
        return lookup.get(pat)

    def lookup_digest():
        h = 0x811C9DC5
        for nm in probes:
            cp = lookup_ref(nm)
            if cp is None:
                h = ((h ^ 0) * 0x01000193) & 0xFFFFFFFF
            else:
                h = ((h ^ cp) * 0x01000193) & 0xFFFFFFFF
        return h

    ld = lookup_digest()

    vectors = ucd.header("gen_name.py", version, "Test vectors only; not part of the package.") + [
        "",
        "///|",
        f"let name_digest : UInt32 = {nd}",
        "",
        "///|",
        f"let lookup_digest : UInt32 = {ld}",
        "",
        "///|",
        "/// The names `name` is probed against, in order, for the lookup digest.",
        "let lookup_probes : Array[String] = [",
        *[f"  {ucd.quote(p)}," for p in probes],
        "]",
        "",
    ]
    ucd.write(SRC / "name_vectors_test.mbt", vectors)


if __name__ == "__main__":
    main()
