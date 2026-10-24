#!/usr/bin/env python3
"""Write src/tables.mbt from the Unicode Character Database.

The UCD files are fetched once into scripts/.ucd/<version>/ and reused, so a
second run works offline. The same version always writes the same bytes.

    python scripts/gen_tables.py               # Unicode 17.0.0
    python scripts/gen_tables.py --version 16.0.0
"""

import argparse
import pathlib
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parent.parent
OUT = ROOT / "src" / "tables.mbt"
CACHE = ROOT / "scripts" / ".ucd"
BASE = "https://www.unicode.org/Public/{v}/ucd/{f}"

FILES = [
    "UnicodeData.txt",
    "SpecialCasing.txt",
    "CaseFolding.txt",
    "PropList.txt",
    "DerivedCoreProperties.txt",
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
]

NUMERIC = ["Decimal", "Digit", "Numeric"]


def fetch(version, name):
    path = CACHE / version / name
    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        with urllib.request.urlopen(BASE.format(v=version, f=name)) as r:
            path.write_bytes(r.read())
    return path.read_text(encoding="utf-8")


def records(text):
    for line in text.splitlines():
        line = line.split("#", 1)[0].strip()
        if line:
            yield [field.strip() for field in line.split(";")]


def span(field):
    if ".." in field:
        a, b = field.split("..")
        return int(a, 16), int(b, 16)
    return int(field, 16), int(field, 16)


def merge(pairs):
    """Sorted, non-overlapping (start, end) ranges with neighbours joined."""
    out = []
    for a, b in sorted(pairs):
        if out and a <= out[-1][1] + 1:
            out[-1] = (out[-1][0], max(out[-1][1], b))
        else:
            out.append((a, b))
    return out


def runs(values, default):
    """(start, end, value) runs over the whole code space, the default left out."""
    out = []
    start = 0
    current = values.get(0, default)
    for cp in range(1, 0x110000):
        v = values.get(cp, default)
        if v != current:
            if current != default:
                out.append((start, cp - 1, current))
            start, current = cp, v
    if current != default:
        out.append((start, 0x10FFFF, current))
    return out


def unicode_data(text):
    """General category, bidi class and simple case mappings per code point,
    with the <..., First>/<..., Last> pairs expanded."""
    category, bidi, upper, lower, title = {}, {}, {}, {}, {}
    first = None
    for f in records(text):
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
    for f in records(text):
        if len(f) > 4 and f[4]:
            continue
        cp = int(f[0], 16)
        out[cp] = tuple(
            [int(x, 16) for x in field.split()] for field in (f[1], f[2], f[3])
        )
    return out


def mbt_ints(name, values, per_line=12):
    lines = [f"let {name} : FixedArray[Int] = ["]
    for i in range(0, len(values), per_line):
        chunk = ", ".join(str(v) for v in values[i : i + per_line])
        lines.append(f"  {chunk},")
    lines.append("]")
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--version", default="17.0.0")
    version = parser.parse_args().version
    text = {name: fetch(version, name) for name in FILES}

    category, bidi, upper, lower, title = unicode_data(text["UnicodeData.txt"])
    for f in records(text["extracted/DerivedBidiClass.txt"]):
        a, b = span(f[0])
        for c in range(a, b + 1):
            bidi.setdefault(c, f[1])

    props = {name: [] for name in PROPERTIES}
    for source in ("PropList.txt", "DerivedCoreProperties.txt"):
        for f in records(text[source]):
            if len(f) == 2 and f[1] in props:
                props[f[1]].append(span(f[0]))

    numeric = {}
    for f in records(text["extracted/DerivedNumericType.txt"]):
        a, b = span(f[0])
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
    for f in records(text["CaseFolding.txt"]):
        if f[1] in ("C", "F"):
            fold[int(f[0], 16)] = [int(x, 16) for x in f[2].split()]

    out = [
        "// Generated by scripts/gen_tables.py from the Unicode Character",
        f"// Database {version}. Do not edit by hand.",
        "",
        "///|",
        f'let ucd_version : String = "{version}"',
        "",
    ]

    cat_runs = runs(category, "Cn")
    out += ["///|", mbt_ints("category_starts", [r[0] for r in cat_runs]), ""]
    out += ["///|", mbt_ints("category_ends", [r[1] for r in cat_runs]), ""]
    out += ["///|", mbt_ints("category_values", [CATEGORIES.index(r[2]) for r in cat_runs]), ""]

    bidi_runs = runs(bidi, "L")
    out += ["///|", mbt_ints("bidi_starts", [r[0] for r in bidi_runs]), ""]
    out += ["///|", mbt_ints("bidi_ends", [r[1] for r in bidi_runs]), ""]
    out += ["///|", mbt_ints("bidi_values", [BIDI.index(r[2]) for r in bidi_runs]), ""]

    num_runs = runs(numeric, None)
    out += ["///|", mbt_ints("numeric_starts", [r[0] for r in num_runs]), ""]
    out += ["///|", mbt_ints("numeric_ends", [r[1] for r in num_runs]), ""]
    out += ["///|", mbt_ints("numeric_values", [NUMERIC.index(r[2]) for r in num_runs]), ""]

    flat = []
    offsets = [0]
    for name in PROPERTIES:
        for a, b in merge(props[name]):
            flat += [a, b]
        offsets.append(len(flat))
    out += ["///|", "/// Ranges of every property, start and end interleaved; property `i`", "/// owns `property_ranges[property_offsets[i]:property_offsets[i + 1]]`.", mbt_ints("property_ranges", flat), ""]
    out += ["///|", mbt_ints("property_offsets", offsets), ""]

    def mapping(name, table):
        keys = sorted(cp for cp, v in table.items() if v != [cp])
        starts, values = [], []
        for cp in keys:
            starts.append(len(values))
            values += table[cp]
        starts.append(len(values))
        return [
            "///|", mbt_ints(f"{name}_keys", keys), "",
            "///|", mbt_ints(f"{name}_offsets", starts), "",
            "///|", mbt_ints(f"{name}_values", values), "",
        ]

    out += mapping("upper", full_upper)
    out += mapping("lower", full_lower)
    out += mapping("title", full_title)
    out += mapping("fold", fold)

    OUT.write_text("\n".join(out), encoding="utf-8", newline="\n")
    print(f"wrote {OUT.relative_to(ROOT)}: {len(cat_runs)} category runs, {len(flat) // 2} property ranges")


if __name__ == "__main__":
    main()
