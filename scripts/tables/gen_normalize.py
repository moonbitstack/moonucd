#!/usr/bin/env python3
"""Write src/normalize/tables.mbt and the test vectors from the UCD.

`moonucd/normalize` answers the Unicode normalization questions:
`normalize(form, s)` (NFC/NFD/NFKC/NFKD), `is_normalized`, `combining`
(the canonical combining class) and `decomposition` (the first-level mapping).

The conformance digests below are folded over *unicodedata2* 17.0.0 — the
Python oracle that actually carries Unicode 17.0.0, unlike the standard
library's `unicodedata`, which on this machine is still 15.1.0. A second
generator-side pass replays the real NormalizationTest source lines so the
MoonBit side can prove it matches the suite without shipping 20k expected
strings.

    python scripts/tables/gen_normalize.py
"""

import argparse
import sys

sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parent))

import ucd
import unicodedata2 as ud

ROOT = ucd.ROOT
SRC = ROOT / "src" / "normalize"
VERSION = "17.0.0"

FNV_SEED = 0x811C9DC5
FNV_PRIME = 0x01000193


def fnv_str(h, s):
    for ch in s:
        h = ((h ^ ord(ch)) * FNV_PRIME) & 0xFFFFFFFF
    return h


def fnv_int(h, v):
    h = ((h ^ (v & 0xFFFFFFFF)) * FNV_PRIME) & 0xFFFFFFFF
    return h


def parse_decomp(field):
    """(prefix, kind, [targets]) of a UnicodeData field-5 value. `prefix` is the
    literal text Python's `decomposition` emits before the hex — "" for a
    canonical mapping, "<tag> " for a compatibility one. `kind` is 0 canonical,
    1 compatibility; canonical mappings are applied under every form, the
    compatibility ones only under NFKC/NFKD."""
    field = field.strip()
    if field.startswith("<"):
        tag = field.split()[0]
        return tag + " ", 1, [int(x, 16) for x in field.split()[1:]]
    if field:
        return "", 0, [int(x, 16) for x in field.split()]
    return "", 0, []


def parse_unicode_data(version):
    """ccc and decomposition for every code point, ranges expanded."""
    text = ucd.fetch(version, "UnicodeData.txt")
    ccc = {}
    dec = {}
    pending = None
    for line in text.splitlines():
        line = line.split("#", 1)[0].strip()
        if not line:
            continue
        f = [x.strip() for x in line.split(";")]
        cp0, cp1 = ucd.span(f[0])
        name = f[1]
        ccc_val = int(f[3])
        if name.endswith("First>"):
            pending = (cp0, ccc_val, f[5])
            continue
        if name.endswith("Last>"):
            start, rc, rd = pending
            for cp in range(start, cp1 + 1):
                ccc[cp] = rc
                if rd:
                    dec[cp] = parse_decomp(rd)
            pending = None
            continue
        ccc[cp0] = ccc_val
        if f[5].strip():
            dec[cp0] = parse_decomp(f[5])
    return ccc, dec


def parse_exclusions(version):
    text = ucd.fetch(version, "CompositionExclusions.txt")
    out = set()
    for f in ucd.records(text):
        out.add(int(f[0], 16))
    return out


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--version", default=VERSION)
    version = parser.parse_args().version

    ccc, dec = parse_unicode_data(version)
    exclusions = parse_exclusions(version)

    # ---- ccc runs: merge consecutive code points sharing a non-zero value ----
    ccc_runs = []
    for cp in sorted(ccc):
        v = ccc[cp]
        if v == 0:
            continue
        if ccc_runs and ccc_runs[-1][1] == cp - 1 and ccc_runs[-1][2] == v:
            ccc_runs[-1][1] = cp
        else:
            ccc_runs.append([cp, cp, v])
    ccc_starts = [r[0] for r in ccc_runs]
    ccc_ends = [r[1] for r in ccc_runs]
    ccc_values = [r[2] for r in ccc_runs]

    # ---- decomposition table (sorted by code point) ----
    dec_items = sorted(dec.items())  # (cp, (prefix, kind, targets))
    dec_keys = [cp for cp, _ in dec_items]
    tag_list = [""]
    tag_index = {"": 0}
    dec_tag = []
    for _, (prefix, _, _) in dec_items:
        if prefix not in tag_index:
            tag_index[prefix] = len(tag_list)
            tag_list.append(prefix)
        dec_tag.append(tag_index[prefix])
    dec_offsets = [0]
    dec_targets = []
    for _, (_, _, targets) in dec_items:
        dec_targets.extend(targets)
        dec_offsets.append(len(dec_targets))

    # ---- canonical composition pairs (no Hangul; those are algorithmic) ----
    pairs = []
    for cp, (_, kind, targets) in dec_items:
        if kind != 0 or len(targets) != 2:
            continue
        a, b = targets
        if ccc.get(a, 0) != 0:  # non-starter decomposition is excluded
            continue
        if cp in exclusions:
            continue
        pairs.append((a, b, cp))
    pairs.sort()
    comp_a = [p[0] for p in pairs]
    comp_b = [p[1] for p in pairs]
    comp_c = [p[2] for p in pairs]

    # ---- emit tables.mbt ----
    lines = ucd.header("gen_normalize.py", version) + [
        "",
        "///|",
        f'let ucd_version : String = "{version}"',
        "",
        "///|",
        "/// Non-zero Canonical_Combining_Class runs: a code point not in a run has ccc 0.",
        ucd.mbt_ints("ccc_starts", ccc_starts, typ="Int"),
        "",
        "///|",
        ucd.mbt_ints("ccc_ends", ccc_ends, typ="Int"),
        "",
        "///|",
        ucd.mbt_ints("ccc_values", ccc_values, typ="Int"),
        "",
        "///|",
        "/// Code points that have a decomposition mapping (canonical, kind 0, or",
        "/// compatibility, kind 1), sorted; paired with dec_offsets / dec_kind / dec_targets.",
        ucd.mbt_ints("dec_keys", dec_keys, typ="Int"),
        "",
        "///|",
        "/// Offset into dec_targets where each key's mapping begins (length n + 1).",
        ucd.mbt_ints("dec_offsets", dec_offsets, typ="Int"),
        "",
        "///|",
        "/// Index into dec_tags for each key: 0 is a canonical mapping, any",
        "/// other index is a compatibility tag such as \"<noBreak> \".",
        ucd.mbt_ints("dec_tag", dec_tag, typ="Int"),
        "",
        "///|",
        "/// The literal decomposition prefixes emitted by `decomposition`.",
        ucd.mbt_strings("dec_tags", tag_list),
        "",
        "///|",
        "/// The concatenation of every decomposition's target code points.",
        ucd.mbt_ints("dec_targets", dec_targets, typ="Int"),
        "",
        "///|",
        "/// Canonical composition pairs (A, B) -> C, sorted by A then B. Hangul is",
        "/// resolved algorithmically and is not stored here.",
        ucd.mbt_ints("comp_a", comp_a, typ="Int"),
        "",
        "///|",
        ucd.mbt_ints("comp_b", comp_b, typ="Int"),
        "",
        "///|",
        ucd.mbt_ints("comp_c", comp_c, typ="Int"),
        "",
    ]
    ucd.write(SRC / "tables.mbt", lines)
    print(
        f"  ccc_runs={len(ccc_runs)} dec={len(dec_keys)} "
        f"targets={len(dec_targets)} pairs={len(pairs)}"
    )

    # ---- conformance: per-code-point normalize / combining / decomposition ----
    cp_norm = FNV_SEED
    comb = FNV_SEED
    decomp = FNV_SEED
    for cp in range(0x110000):
        if 0xD800 <= cp <= 0xDFFF:  # lone surrogates can't live in a MoonBit String
            continue
        s = chr(cp)
        for form in ("NFC", "NFD", "NFKC", "NFKD"):
            cp_norm = fnv_str(cp_norm, ud.normalize(form, s))
        comb = fnv_int(comb, ud.combining(s))
        decomp = fnv_str(decomp, ud.decomposition(s))

    # ---- conformance: the real NormalizationTest source lines ----
    nt_text = ucd.fetch(version, "NormalizationTest.txt")
    sources = []
    bounds = [0]
    nt_norm = FNV_SEED
    nt_norm_checkpoints = []
    for line in nt_text.splitlines():
        line = line.split("#", 1)[0].strip()
        if not line or line.startswith("@") or ";" not in line:
            continue
        cols = line.split(";")
        src = ""
        for part in cols[0].split():
            if part:
                src += chr(int(part, 16))
        sources.append(src)
        bounds.append(bounds[-1] + len(src))
        for form in ("NFC", "NFD", "NFKC", "NFKD"):
            nt_norm = fnv_str(nt_norm, ud.normalize(form, src))
        nt_norm_checkpoints.append(nt_norm)

    pool = ucd.mbt_string_pool(
        "nt_sources_concat", "".join(sources), escaper=ucd.quote_full
    )
    vectors = ucd.header(
        "gen_normalize.py", version, "Test vectors only; not part of the package."
    ) + [
        "",
        "///|",
        "/// FNV-1a over normalize(NFC/NFD/NFKC/NFKD) for every code point.",
        f"let cp_norm_digest : UInt32 = {cp_norm}",
        "",
        "///|",
        "/// FNV-1a over normalize(NFC/NFD/NFKC/NFKD) for every source line of",
        "/// the UCD 17.0.0 NormalizationTest (replayed in the test).",
        f"let nt_norm_digest : UInt32 = {nt_norm}",
        "",
        "///|",
        "/// Cumulative FNV-1a of the NormalizationTest sources, after each one,",
        "/// so the test can localise the first line that diverges from the oracle.",
        ucd.mbt_ints("nt_norm_checkpoints", nt_norm_checkpoints, typ="UInt32"),
        "",
        "///|",
        "/// FNV-1a over unicodedata.combining for every code point.",
        f"let combining_digest : UInt32 = {comb}",
        "",
        "///|",
        "/// FNV-1a over unicodedata.decomposition for every code point.",
        f"let decomposition_digest : UInt32 = {decomp}",
        "",
        "///|",
        "/// The NormalizationTest sources concatenated; slice with nt_source_bounds.",
        pool,
        "",
        "///|",
        "/// Cumulative code-point length of each NormalizationTest source.",
        ucd.mbt_ints("nt_source_bounds", bounds, typ="Int"),
        "",
    ]
    ucd.write(SRC / "normalize_vectors_test.mbt", vectors)
    print(
        f"  cp_norm_digest={cp_norm} nt_norm_digest={nt_norm} "
        f"combining_digest={comb} decomposition_digest={decomp} nt_lines={len(sources)}"
    )


if __name__ == "__main__":
    main()
