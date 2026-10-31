#!/usr/bin/env python3
"""Write src/tables.mbt and the test vectors from the Unicode Character
Database.

The UCD files are fetched once into scripts/tables/.ucd/<version>/ and reused, so a
second run works offline. The same version always writes the same bytes.

    python scripts/tables/gen_tables.py               # Unicode 17.0.0
    python scripts/tables/gen_tables.py --version 16.0.0

Under a Python whose `unicodedata` is the same Unicode version — 3.15 for
17.0.0 — the category ranges are also built a second time from `unicodedata`,
and the run stops if the two disagree. With another Python the second opinion
is skipped, and the ranges digest then comes from the file parse alone.
"""

import argparse
import sys
import unicodedata

sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parent))

import ucd

ROOT = ucd.ROOT
OUT = ROOT / "src" / "tables.mbt"
VECTORS = ROOT / "src" / "tables_vectors_test.mbt"

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


def fnv(values):
    """FNV-1a over 32-bit values: the digest a test recomputes by walking the
    same values in the same order."""
    h = 0x811C9DC5
    for x in values:
        h = ((h ^ (x & 0xFFFFFFFF)) * 0x01000193) & 0xFFFFFFFF
    return h


def ranges_digest(buckets, order):
    """The digest of every range of every name in `order`."""
    seq = []
    for name in order:
        for a, b in buckets[name]:
            seq += [a, b]
    return fnv(seq)


def reference_categories(version):
    """The category ranges of the whole code space, built from `unicodedata`
    instead of the files: a second opinion, when this Python speaks the same
    Unicode version. `None` otherwise."""
    if unicodedata.unidata_version != version:
        return None
    out = {name: [] for name in CATEGORIES}
    prev, start = None, 0
    for cp in range(0x110000):
        v = unicodedata.category(chr(cp))
        if v != prev:
            if prev is not None:
                out[prev].append((start, cp - 1))
            prev, start = v, cp
    out[prev].append((start, 0x10FFFF))
    return out


def fold_orbits(simple):
    """The classes the simple foldings join: each code point that takes part,
    mapped to every code point in its class, ascending."""
    parent = {}

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    for cp, to in simple.items():
        parent.setdefault(cp, cp)
        parent.setdefault(to, to)
        a, b = find(cp), find(to)
        if a != b:
            parent[max(a, b)] = min(a, b)
    classes = {}
    for cp in parent:
        classes.setdefault(find(cp), []).append(cp)
    orbit = {}
    for members in classes.values():
        members.sort()
        for cp in members:
            orbit[cp] = members
    return orbit


def write_vectors(version, cat_buckets, prop_buckets, simple, orbit):
    """The vectors the tests replay: a digest of each range table, of the fold
    of every code point, and of every fold class, plus the simple foldings as
    the file lists them."""
    scalar = [cp for cp in range(0x110000) if not 0xD800 <= cp <= 0xDFFF]
    folded = [simple.get(cp, cp) for cp in scalar]
    classes = []
    for cp in scalar:
        members = orbit.get(cp, [cp])
        classes += [len(members)] + members
    pairs = sorted(simple)
    categories = ucd.enum_variants(ROOT / "src" / "moonucd.mbt", "Category")
    properties = ucd.enum_variants(ROOT / "src" / "moonucd.mbt", "Property")
    for variants, order in ((categories, CATEGORIES), (properties, PROPERTIES)):
        if variants != [ucd.camel(name) for name in order]:
            sys.exit("the enum and the table order no longer agree")
    lines = ucd.header("gen_tables.py", version, "Test vectors only; not part of the package.") + [
        "",
        "///|",
        "/// Every category and property in the order the enum declares them, the",
        "/// order the range digests were taken in.",
        "let category_ranges_order : FixedArray[@moonucd.Category] = [",
        *[f"  {v}," for v in categories],
        "]",
        "",
        "///|",
        "let property_ranges_order : FixedArray[@moonucd.Property] = [",
        *[f"  {v}," for v in properties],
        "]",
        "",
        "///|",
        "/// FNV-1a over the ranges of every category, in the order the enum",
        "/// declares them, each range as its start and then its end.",
        f"let category_ranges_digest : UInt32 = {ranges_digest(cat_buckets, CATEGORIES)}",
        "",
        "///|",
        "/// The same over every property, in the order the enum declares them.",
        f"let property_ranges_digest : UInt32 = {ranges_digest(prop_buckets, PROPERTIES)}",
        "",
        "///|",
        "/// The simple folding of every code point that is not a surrogate.",
        f"let simple_fold_digest : UInt32 = {fnv(folded)}",
        "",
        "///|",
        "/// Each code point's fold class as its length and then its members, so a",
        "/// class that is short of one member changes the digest.",
        f"let fold_orbit_digest : UInt32 = {fnv(classes)}",
        "",
        "///|",
        "/// Every C and S entry of CaseFolding.txt, ascending by code point.",
        ucd.mbt_ints("simple_fold_from", pairs),
        "",
        "///|",
        ucd.mbt_ints("simple_fold_to", [simple[cp] for cp in pairs]),
        "",
    ]
    ucd.write(VECTORS, lines)


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
    simple = {}
    for f in ucd.records(text["CaseFolding.txt"]):
        cp = int(f[0], 16)
        if f[1] in ("C", "F"):
            fold[cp] = [int(x, 16) for x in f[2].split()]
        if f[1] in ("C", "S"):
            if len(f[2].split()) != 1:
                sys.exit(f"U+{cp:04X}: a C or S folding is one code point")
            simple[cp] = int(f[2], 16)

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

    # The ranges of a category cover the code space between them, so the ones
    # of Cn are the gaps the runs above leave; the runs therefore keep Cn out
    # and these do not.
    cat_buckets = {name: [] for name in CATEGORIES}
    for a, b, name in ucd.runs_all(category, "Cn"):
        cat_buckets[name].append((a, b))
    reference = reference_categories(version)
    for name in CATEGORIES:
        if reference is not None and reference[name] != cat_buckets[name]:
            sys.exit(f"category {name}: the files and unicodedata disagree")
    cat_flat, cat_offsets = [], [0]
    for name in CATEGORIES:
        for a, b in cat_buckets[name]:
            cat_flat += [a, b]
        cat_offsets.append(len(cat_flat))
    out += [
        "///|",
        "/// Ranges of every category, start and end interleaved; category `i`",
        "/// owns `category_ranges[category_ranges_offsets[i]:category_ranges_offsets[i + 1]]`.",
        ucd.mbt_ints("category_ranges", cat_flat),
        "",
    ]
    out += ["///|", ucd.mbt_ints("category_ranges_offsets", cat_offsets), ""]

    bidi_runs = ucd.runs(bidi, "L")
    out += ["///|", ucd.mbt_ints("bidi_starts", [r[0] for r in bidi_runs]), ""]
    out += ["///|", ucd.mbt_ints("bidi_ends", [r[1] for r in bidi_runs]), ""]
    out += ["///|", ucd.mbt_ints("bidi_values", [BIDI.index(r[2]) for r in bidi_runs]), ""]

    num_runs = ucd.runs(numeric, None)
    out += ["///|", ucd.mbt_ints("numeric_starts", [r[0] for r in num_runs]), ""]
    out += ["///|", ucd.mbt_ints("numeric_ends", [r[1] for r in num_runs]), ""]
    out += ["///|", ucd.mbt_ints("numeric_values", [NUMERIC.index(r[2]) for r in num_runs]), ""]

    prop_buckets = {name: ucd.merge(props[name]) for name in PROPERTIES}
    flat = []
    offsets = [0]
    for name in PROPERTIES:
        for a, b in prop_buckets[name]:
            flat += [a, b]
        offsets.append(len(flat))
    out += ["///|", "/// Ranges of every property, start and end interleaved; property `i`", "/// owns `property_ranges[property_ranges_offsets[i]:property_ranges_offsets[i + 1]]`.", ucd.mbt_ints("property_ranges", flat), ""]
    out += ["///|", ucd.mbt_ints("property_ranges_offsets", offsets), ""]

    out += ["///|", "/// The simple foldings, CaseFolding.txt's C and S classes: the code point,", "/// and the one code point it folds to.", ucd.mbt_ints("simple_fold_keys", sorted(simple)), ""]
    out += ["///|", ucd.mbt_ints("simple_fold_values", [simple[cp] for cp in sorted(simple)]), ""]

    orbit = fold_orbits(simple)
    orbit_keys = sorted(orbit)
    orbit_values, orbit_offsets = [], [0]
    for cp in orbit_keys:
        orbit_values += orbit[cp]
        orbit_offsets.append(len(orbit_values))
    out += ["///|", "/// The class of every code point a simple folding joins: the members of", "/// `fold_orbit_values[fold_orbit_offsets[i]:fold_orbit_offsets[i + 1]]`,", "/// ascending, hold the same list under each of their own keys.", ucd.mbt_ints("fold_orbit_keys", orbit_keys), ""]
    out += ["///|", ucd.mbt_ints("fold_orbit_offsets", orbit_offsets), ""]
    out += ["///|", ucd.mbt_ints("fold_orbit_values", orbit_values), ""]

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
    print(f"  {len(cat_runs)} category runs, {len(cat_flat) // 2} category ranges")
    print(f"  {len(flat) // 2} property ranges, {len(simple)} simple foldings")
    print(f"  {len(orbit_keys)} code points in {len(set(map(tuple, orbit.values())))} fold classes")
    if reference is None:
        print(f"  python {unicodedata.unidata_version} is not {version}: no unicodedata cross-check")
    else:
        print(f"  category ranges agree with unicodedata {version}")
    write_vectors(version, cat_buckets if reference is None else reference, prop_buckets, simple, orbit)


if __name__ == "__main__":
    main()
