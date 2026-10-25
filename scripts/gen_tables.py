#!/usr/bin/env python3
"""Write src/tables.mbt from the Unicode Character Database.

The UCD files are fetched once into scripts/.ucd/<version>/ and reused, so a
second run works offline. The same version always writes the same bytes.

    python scripts/gen_tables.py               # Unicode 17.0.0
    python scripts/gen_tables.py --version 16.0.0
"""

import argparse
import sys

sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parent))

import ucd

ROOT = ucd.ROOT
OUT = ROOT / "src" / "tables.mbt"

FILES = [
    "UnicodeData.txt",
    "SpecialCasing.txt",
    "CaseFolding.txt",
    "PropList.txt",
    "DerivedCoreProperties.txt",
    "emoji/emoji-data.txt",
    "extracted/DerivedNumericType.txt",
    "extracted/DerivedBidiClass.txt",
]

CATEGORIES = [
    "Lu", "Ll", "Lt", "Lm", "Lo", "Mn", "Mc", "Me", "Nd", "Nl", "No", "Pc",
    "Pd", "Ps", "Pe", "Pi", "Pf", "Po", "Sm", "Sc", "Sk", "So", "Zs", "Zl",
    "Zp", "Cc", "Cf", "Cs", "Co", "Cn",
]

BIDI = [
    "L", "R", "AL", "EN", "ES", "ET", "AN", "CS", "NSM", "BN", "B", "S", "WS",
    "ON", "LRE", "LRO", "RLE", "RLO", "PDF", "LRI", "RLI", "FSI", "PDI",
]

PROPERTIES = [
    # DerivedCoreProperties.txt
    "Alphabetic", "Lowercase", "Uppercase", "Cased", "Case_Ignorable",
    "Changes_When_Lowercased", "Changes_When_Uppercased",
    "Changes_When_Titlecased", "Changes_When_Casefolded",
    "Changes_When_Casemapped", "ID_Start", "ID_Continue", "XID_Start",
    "XID_Continue", "Default_Ignorable_Code_Point", "Grapheme_Extend",
    "Grapheme_Base", "Math",
    # PropList.txt
    "White_Space", "Bidi_Control", "Join_Control", "Dash", "Hyphen",
    "Quotation_Mark", "Terminal_Punctuation", "Hex_Digit", "ASCII_Hex_Digit",
    "Ideographic", "Diacritic", "Extender", "Noncharacter_Code_Point",
    "IDS_Binary_Operator", "IDS_Trinary_Operator", "Radical",
    "Unified_Ideograph", "Deprecated", "Soft_Dotted",
    "Logical_Order_Exception", "Sentence_Terminal", "Variation_Selector",
    "Pattern_White_Space", "Pattern_Syntax", "Prepended_Concatenation_Mark",
    "Regional_Indicator",
    # emoji-data.txt
    "Emoji", "Emoji_Presentation", "Emoji_Modifier", "Emoji_Modifier_Base",
    "Emoji_Component", "Extended_Pictographic",
]

NUMERIC = ["Decimal", "Digit", "Numeric"]


def unicode_data(text):
    """General category, bidi class and simple case mappings per code point,
    with the <..., First>/<..., Last> pairs expanded."""
    category, bidi, upper, lower, title = {}, {}, {}, {}, {}
    first = None
    for f in ucd.records(text):
        cp = int(f[0], 16)
        if f[1].endswith(", First>"):
            first = cp
            continue
        lo = first if first is not None and f[1].endswith(", Last>") else cp
        first = None
        for c in range(lo, cp + 1):
            category[c] = f[2]
            bidi[c] = f[4]
        if f[12]:
            upper[cp] = int(f[12], 16)
        if f[13]:
            lower[cp] = int(f[13], 16)
        if f[14]:
            title[cp] = int(f[14], 16)
        elif f[12]:
            title[cp] = int(f[12], 16)
    return category, bidi, upper, lower, title


def special_casing(text):
    """The unconditional entries: code point to (lower, title, upper)."""
    out = {}
    for f in ucd.records(text):
        if len(f) > 4 and f[4]:
            continue
        cp = int(f[0], 16)
        out[cp] = tuple(
            [int(x, 16) for x in field.split()] for field in (f[1], f[2], f[3])
        )
    return out


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--version", default="17.0.0")
    version = parser.parse_args().version
    text = {name: ucd.fetch(version, name) for name in FILES}

    category, bidi, upper, lower, title = unicode_data(text["UnicodeData.txt"])
    for f in ucd.records(text["extracted/DerivedBidiClass.txt"]):
        a, b = ucd.span(f[0])
        for c in range(a, b + 1):
            bidi.setdefault(c, f[1])

    props = {name: [] for name in PROPERTIES}
    for source in ("PropList.txt", "DerivedCoreProperties.txt", "emoji/emoji-data.txt"):
        for f in ucd.records(text[source]):
            if len(f) == 2 and f[1] in props:
                props[f[1]].append(ucd.span(f[0]))

    numeric = {}
    for f in ucd.records(text["extracted/DerivedNumericType.txt"]):
        a, b = ucd.span(f[0])
        for c in range(a, b + 1):
            numeric[c] = f[1]

    special = special_casing(text["SpecialCasing.txt"])
    full_upper, full_lower, full_title = {}, {}, {}
    for cp in set(upper) | set(lower) | set(title) | set(special):
        lo, ti, up = special.get(cp, (None, None, None))
        full_lower[cp] = lo if lo is not None else [lower.get(cp, cp)]
        full_title[cp] = ti if ti is not None else [title.get(cp, cp)]
        full_upper[cp] = up if up is not None else [upper.get(cp, cp)]

    fold = {}
    for f in ucd.records(text["CaseFolding.txt"]):
        if f[1] in ("C", "F"):
            fold[int(f[0], 16)] = [int(x, 16) for x in f[2].split()]

    out = ucd.header("gen_tables.py", version) + [
        "",
        "///|",
        f'let ucd_version : String = "{version}"',
        "",
    ]

    cat_runs = ucd.runs(category, "Cn")
    out += ["///|", ucd.mbt_ints("category_starts", [r[0] for r in cat_runs]), ""]
    out += ["///|", ucd.mbt_ints("category_ends", [r[1] for r in cat_runs]), ""]
    out += ["///|", ucd.mbt_ints("category_values", [CATEGORIES.index(r[2]) for r in cat_runs]), ""]

    bidi_runs = ucd.runs(bidi, "L")
    out += ["///|", ucd.mbt_ints("bidi_starts", [r[0] for r in bidi_runs]), ""]
    out += ["///|", ucd.mbt_ints("bidi_ends", [r[1] for r in bidi_runs]), ""]
    out += ["///|", ucd.mbt_ints("bidi_values", [BIDI.index(r[2]) for r in bidi_runs]), ""]

    num_runs = ucd.runs(numeric, None)
    out += ["///|", ucd.mbt_ints("numeric_starts", [r[0] for r in num_runs]), ""]
    out += ["///|", ucd.mbt_ints("numeric_ends", [r[1] for r in num_runs]), ""]
    out += ["///|", ucd.mbt_ints("numeric_values", [NUMERIC.index(r[2]) for r in num_runs]), ""]

    flat = []
    offsets = [0]
    for name in PROPERTIES:
        for a, b in ucd.merge(props[name]):
            flat += [a, b]
        offsets.append(len(flat))
    out += ["///|", "/// Ranges of every property, start and end interleaved; property `i`", "/// owns `property_ranges[property_offsets[i]:property_offsets[i + 1]]`.", ucd.mbt_ints("property_ranges", flat), ""]
    out += ["///|", ucd.mbt_ints("property_offsets", offsets), ""]

    def mapping(name, table):
        keys = sorted(cp for cp, v in table.items() if v != [cp])
        starts, values = [], []
        for cp in keys:
            starts.append(len(values))
            values += table[cp]
        starts.append(len(values))
        return [
            "///|", ucd.mbt_ints(f"{name}_keys", keys), "",
            "///|", ucd.mbt_ints(f"{name}_offsets", starts), "",
            "///|", ucd.mbt_ints(f"{name}_values", values), "",
        ]

    out += mapping("upper", full_upper)
    out += mapping("lower", full_lower)
    out += mapping("title", full_title)
    out += mapping("fold", fold)

    ucd.write(OUT, out)
    print(f"  {len(cat_runs)} category runs, {len(flat) // 2} property ranges")


if __name__ == "__main__":
    main()
