#!/usr/bin/env python3
"""Write src/name/tables.mbt and src/name/name_vectors_test.mbt from the
Unicode Character Database.

Names the Standard derives from the code point are computed at run time:
Hangul syllables by rule NR1, and every name of the form `PREFIX-XXXX` whose
hex part is the code point itself (CJK unified and compatibility ideographs,
Tangut ideographs, Khitan small script, Nushu, Egyptian hieroglyphs) by rule
NR2. Only the remaining explicit names are stored. The reference is CPython's
`unicodedata`, which must carry the same Unicode version, so run this with
Python 3.15 or later for Unicode 17.0.0.

    python scripts/tables/gen_name.py
"""

import argparse
import re
import sys
import unicodedata as ud

sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parent))
import ucd

ROOT = ucd.ROOT
SRC = ROOT / "src" / "name"

HANGUL_FIRST, HANGUL_LAST = 0xAC00, 0xD7A3
NR2 = re.compile(r"^(.+-)([0-9A-F]{4,6})$")


def lm2(name):
    """UAX #44 LM2: case, spaces, underscores and medial hyphens (a hyphen
    between two letters or digits) are ignored, except the hyphen in U+1180's
    name."""
    up = name.upper()
    keep = up == "HANGUL JUNGSEONG O-E"
    out = []
    for i, ch in enumerate(up):
        if ch in " _":
            continue
        if ch == "-" and not keep and 0 < i < len(up) - 1 and up[i - 1].isalnum() and up[i + 1].isalnum():
            continue
        out.append(ch)
    return "".join(out)


def fnv(h, v):
    return ((h ^ v) * 0x01000193) & 0xFFFFFFFF


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--version", default="17.0.0")
    version = parser.parse_args().version
    if ud.unidata_version != version:
        sys.exit(f"unicodedata carries {ud.unidata_version}, not {version}; run with a matching Python")

    names = {}
    for cp in range(0x110000):
        if 0xD800 <= cp <= 0xDFFF:
            continue
        try:
            names[cp] = ud.name(chr(cp))
        except ValueError:
            pass

    rules, explicit = [], {}
    for cp in sorted(names):
        m = NR2.match(names[cp])
        if HANGUL_FIRST <= cp <= HANGUL_LAST:
            continue
        if m and m.group(2) == f"{cp:04X}":
            if rules and rules[-1][2] == m.group(1) and rules[-1][1] == cp - 1:
                rules[-1][1] = cp
            else:
                rules.append([cp, cp, m.group(1)])
        else:
            explicit[cp] = names[cp]
    prefixes = sorted({p for _, _, p in rules})

    jamo = {}
    for f in ucd.records(ucd.fetch(version, "Jamo.txt")):
        jamo[int(f[0], 16)] = f[1]
    leads = [jamo[0x1100 + i] for i in range(19)]
    vowels = [jamo[0x1161 + i] for i in range(21)]
    tails = [""] + [jamo[0x11A8 + i] for i in range(27)]

    cps = sorted(explicit)
    pool = "".join(explicit[cp] for cp in cps)
    offsets = [0]
    for cp in cps:
        offsets.append(offsets[-1] + len(explicit[cp]))

    aliases = []
    for f in ucd.records(ucd.fetch(version, "NameAliases.txt")):
        aliases.append((int(f[0], 16), f[1]))

    keys = {}
    for i, cp in enumerate(cps):
        if lm2(explicit[cp]) in keys:
            sys.exit(f"{explicit[cp]!r} shares its LM2 key with another name")
        keys[lm2(explicit[cp])] = i
    for j, (cp, alias) in enumerate(aliases):
        keys.setdefault(lm2(alias), -1 - j)
    order = [v for _, v in sorted(keys.items())]

    lines = ucd.header("gen_name.py", version) + [
        "",
        "///|",
        f'let ucd_version : String = "{version}"',
        "",
        "///|",
        "/// Code points with an explicit name, ascending.",
        ucd.mbt_ints("name_cps", cps),
        "",
        "///|",
        "/// The explicit names back to back; `name_offsets` marks them.",
        ucd.mbt_string_pool("name_pool", pool, width=60),
        "",
        "///|",
        ucd.mbt_ints("name_offsets", offsets, typ="Int"),
        "",
        "///|",
        "/// Runs of code points named `prefix` + hex by rule NR2.",
        ucd.mbt_ints("rule_starts", [a for a, _, _ in rules]),
        "",
        "///|",
        ucd.mbt_ints("rule_ends", [b for _, b, _ in rules]),
        "",
        "///|",
        ucd.mbt_ints("rule_prefix", [prefixes.index(p) for _, _, p in rules]),
        "",
        "///|",
        ucd.mbt_strings("prefixes", prefixes),
        "",
        "///|",
        "/// The Jamo short names rule NR1 spells Hangul syllables with.",
        ucd.mbt_strings("jamo_leads", leads, per_line=10),
        "",
        "///|",
        ucd.mbt_strings("jamo_vowels", vowels, per_line=10),
        "",
        "///|",
        ucd.mbt_strings("jamo_tails", tails, per_line=10),
        "",
        "///|",
        "/// NameAliases.txt, in file order.",
        ucd.mbt_ints("alias_cps", [cp for cp, _ in aliases]),
        "",
        "///|",
        ucd.mbt_strings("alias_names", [a for _, a in aliases], per_line=4),
        "",
        "///|",
        "/// Every explicit name and alias by LM2 key: an index into the names, or",
        "/// -1 - i for alias i. Names come first, so a name beats an alias.",
        ucd.mbt_ints("lookup_order", order, typ="Int"),
        "",
    ]
    ucd.write(SRC / "tables.mbt", lines)
    print(f"  {len(cps)} explicit names, {len(rules)} NR2 runs, {len(aliases)} aliases")

    h = 0x811C9DC5
    for cp in range(0x110000):
        if 0xD800 <= cp <= 0xDFFF:
            continue
        nm = names.get(cp)
        if nm is None:
            h = fnv(h, 0)
        else:
            h = fnv(h, len(nm))
            for ch in nm:
                h = fnv(h, ord(ch))
    name_digest = h

    probes = [
        "LATIN CAPITAL LETTER A", "latin capital letter a", "LATIN-CAPITAL_LETTER A",
        "GREEK SMALL LETTER ALPHA", "BELL", "LATIN SMALL LETTER E WITH ACUTE",
        "CJK UNIFIED IDEOGRAPH-4E00", "cjk unified ideograph-20000", "CJK UNIFIED IDEOGRAPH-04E00",
        "CJK UNIFIED IDEOGRAPH-9FFF0", "CJK UNIFIED IDEOGRAPH-", "CJK COMPATIBILITY IDEOGRAPH-F900",
        "CJK COMPATIBILITY IDEOGRAPH-FA6E", "TANGUT IDEOGRAPH-17000", "TANGUT IDEOGRAPH-18D00",
        "TANGUT IDEOGRAPH-18800", "TANGUT COMPONENT-001", "NUSHU CHARACTER-1B170",
        "KHITAN SMALL SCRIPT CHARACTER-18B00", "EGYPTIAN HIEROGLYPH-13460",
        "HANGUL SYLLABLE GA", "HANGUL SYLLABLE NA", "HANGUL SYLLABLE HIH", "HANGUL SYLLABLE A",
        "HANGUL SYLLABLE GGWAELH", "HANGUL SYLLABLE GAX", "HANGUL SYLLABLE",
        "HANGUL JUNGSEONG O-E", "HANGUL JUNGSEONG OE", "CARRIAGE RETURN", "LINE FEED",
        "CR", "LF", "NULL", "BYTE ORDER MARK", "nonexistent name", "", "GREEK SMALL LETTER ALPHA X",
    ]

    def resolve(nm):
        key = lm2(nm)
        if key.startswith("HANGULSYLLABLE"):
            rest = key[len("HANGULSYLLABLE"):]
            for li, l in sorted(enumerate(leads), key=lambda x: -len(x[1])):
                if not rest.startswith(l):
                    continue
                for vi, v in sorted(enumerate(vowels), key=lambda x: -len(x[1])):
                    if not rest[len(l):].startswith(v):
                        continue
                    for ti, t in enumerate(tails):
                        if rest[len(l) + len(v):] == t:
                            return HANGUL_FIRST + (li * 21 + vi) * 28 + ti
                    return None
                return None
            return None
        for _, _, p in rules:
            head = lm2(p[:-1])
            tail = key[len(head):]
            if key.startswith(head) and re.fullmatch(r"[0-9A-F]{4,6}", tail):
                cp = int(tail, 16)
                if f"{cp:04X}" == tail and any(x <= cp <= y and q == p for x, y, q in rules):
                    return cp
        i = keys.get(key)
        if i is None:
            return None
        return cps[i] if i >= 0 else aliases[-1 - i][0]

    h = 0x811C9DC5
    for nm in probes:
        cp = resolve(nm)
        try:
            exact = ord(ud.lookup(nm))
        except KeyError:
            exact = None
        if exact is not None and nm == nm.upper() and cp != exact:
            sys.exit(f"the reference lookup disagrees with unicodedata on {nm!r}")
        h = fnv(h, 0 if cp is None else cp)
    lookup_digest = h

    vectors = ucd.header("gen_name.py", version, "Test vectors only; not part of the package.") + [
        "",
        "///|",
        f"let name_digest : UInt32 = {name_digest}",
        "",
        "///|",
        f"let lookup_digest : UInt32 = {lookup_digest}",
        "",
        "///|",
        "/// The names `lookup` is probed with, in order, for the lookup digest.",
        "let lookup_probes : Array[String] = [",
        *[f"  {ucd.quote(p)}," for p in probes],
        "]",
        "",
    ]
    ucd.write(SRC / "name_vectors_test.mbt", vectors)


if __name__ == "__main__":
    main()
