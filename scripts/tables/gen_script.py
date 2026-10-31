#!/usr/bin/env python3
"""Write src/script/tables.mbt and the test vectors from the UCD.

Scripts.txt gives every code point its script, ScriptExtensions.txt the
scripts a code point can belong to, and PropertyValueAliases.txt the long
name and four-letter code of each. The script enum is ordered by long
name; the tables index into that order.

    python scripts/tables/gen_script.py
"""

import argparse
import sys

sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parent))

import ucd

ROOT = ucd.ROOT
SRC = ROOT / "src" / "script"

FILES = ["Scripts.txt", "ScriptExtensions.txt", "PropertyValueAliases.txt"]

# U+1CF5..1CF6 are `Beng Deva` in ScriptExtensions.txt; ICU's tables still
# answer Bengali alone. The file is the specification, so the table follows
# it, and the two are named here rather than hidden in a broken comparison.
ICU_DISAGREES = {(0x1CF5, "Deva"), (0x1CF6, "Deva")}


def aliases(text):
    """(code, long name) for every script, from the `sc` section."""
    out = []
    in_scripts = False
    for line in text.splitlines():
        if line.startswith("# Script ("):
            in_scripts = True
            continue
        if in_scripts and line.startswith("#") and "(" in line:
            break
        if not in_scripts:
            continue
        f = [x.strip() for x in line.split(";")]
        if len(f) >= 3 and f[0] == "sc":
            out.append((f[1], f[2]))
    return out


def loose_key(name):
    """UAX44-LM3: case, whitespace, underscore, hyphen and a leading "is" go."""
    key = "".join(ch for ch in name if ch not in " \t_-").lower()
    if key.startswith("is"):
        key = key[2:]
    return key


def cross_check(long_names, codes, script_buckets, scx_buckets):
    """Compare the ranges with a second implementation — `regex`, whose tables
    come from ICU rather than from the UCD files — at the ends and the middle
    of every range. Nothing is written; a disagreement stops the run."""
    try:
        import regex
    except ImportError:
        print("  regex is not installed: no ICU cross-check")
        return
    checked, excused = 0, 0
    for i, long in enumerate(long_names):
        if long == "Unknown":
            # ICU leaves some unassigned code points out of its script sets
            # and keeps them in others, so it cannot judge this one; the file
            # is the only witness, and every other script is checked here.
            continue
        for table, kind in ((script_buckets[i], "Script"), (scx_buckets[i], "scx")):
            pattern = regex.compile(rf"\p{{{kind}={codes[i]}}}")
            for a, b in table:
                for cp in {a, b, a + (b - a) // 2}:
                    if 0xD800 <= cp <= 0xDFFF:
                        continue
                    if (cp, codes[i]) in ICU_DISAGREES:
                        excused += 1
                        continue
                    if not pattern.fullmatch(chr(cp)):
                        sys.exit(f"{long} at U+{cp:04X}: ICU disagrees")
                    checked += 1
    print(f"  {checked} code points agree with ICU, {excused} known to differ")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--version", default="17.0.0")
    version = parser.parse_args().version
    text = {name: ucd.fetch(version, name) for name in FILES}

    pairs = aliases(text["PropertyValueAliases.txt"])
    by_long = {long: code for code, long in pairs}
    code_index = {code: long for code, long in pairs}
    long_names = sorted(by_long)
    index = {long: i for i, long in enumerate(long_names)}
    codes = [by_long[long] for long in long_names]

    scripts = {}
    for f in ucd.records(text["Scripts.txt"]):
        a, b = ucd.span(f[0])
        long = f[1]
        if long not in index:
            sys.exit(f"script {long!r} has no alias in PropertyValueAliases.txt")
        for c in range(a, b + 1):
            scripts[c] = long

    extensions = {}
    ext_ranges = []
    for f in ucd.records(text["ScriptExtensions.txt"]):
        a, b = ucd.span(f[0])
        seq = [index[code_index[code]] for code in f[1].split()]
        ext_ranges.append((a, b, seq))
        for c in range(a, b + 1):
            extensions[c] = seq

    pairs_by_key = {}
    for long in long_names:
        pairs_by_key.setdefault(loose_key(long), index[long])
    for code, long in zip(codes, long_names):
        key = loose_key(code)
        if key in pairs_by_key and pairs_by_key[key] != index[long]:
            sys.exit(f"loose key {key!r} names two scripts")
        pairs_by_key[key] = index[long]
    pairs_by_key = sorted(pairs_by_key.items())
    keys = [k for k, _ in pairs_by_key]

    if len(set(keys)) != len(keys):
        sys.exit("two scripts share a loose key")
    if any(k.startswith("is") for k in keys):
        sys.exit("a script alias starts with 'is'; the input-side strip would shadow it")

    script_runs = ucd.runs(scripts, "Unknown")
    ext_runs = []
    for a, b, seq in ext_ranges:
        if ext_runs and a <= ext_runs[-1][1] + 1 and ext_runs[-1][2] == seq:
            ext_runs[-1] = (ext_runs[-1][0], b, seq)
        else:
            ext_runs.append((a, b, seq))
    flat, offsets = [], [0]
    for a, b, seq in ext_runs:
        flat += seq
        offsets.append(len(flat))

    # The ranges of a script cover the code space between them, so Unknown
    # takes the unassigned gaps and the runs above keep it out.
    script_buckets = {i: [] for i in range(len(long_names))}
    for a, b, long in ucd.runs_all(scripts, "Unknown"):
        script_buckets[index[long]].append((a, b))

    # Script_Extensions: a code point with no entry of its own belongs to the
    # script Scripts.txt gives it, and to nothing else.
    scx_buckets = {i: [] for i in range(len(long_names))}
    prev, start = None, 0
    for cp in range(0x110000):
        seq = extensions.get(cp)
        key = tuple(seq) if seq is not None else (index[scripts.get(cp, "Unknown")],)
        if key != prev:
            if prev is not None:
                for s in prev:
                    scx_buckets[s].append((start, cp - 1))
            prev, start = key, cp
    for s in prev:
        scx_buckets[s].append((start, 0x10FFFF))
    for s in scx_buckets:
        scx_buckets[s] = ucd.merge(scx_buckets[s])

    script_flat, script_offsets = [], [0]
    scx_flat, scx_offsets = [], [0]
    for i in range(len(long_names)):
        for a, b in script_buckets[i]:
            script_flat += [a, b]
        for a, b in scx_buckets[i]:
            scx_flat += [a, b]
        script_offsets.append(len(script_flat))
        scx_offsets.append(len(scx_flat))

    cross_check(long_names, codes, script_buckets, scx_buckets)

    lines = ucd.header("gen_script.py", version) + [
        "",
        "///|",
        f'let ucd_version : String = "{version}"',
        "",
        "///|",
        "/// Every script, indexed as the Script enum declares them.",
        ucd.mbt_ints("script_starts", [r[0] for r in script_runs]),
        "",
        "///|",
        ucd.mbt_ints("script_ends", [r[1] for r in script_runs]),
        "",
        "///|",
        ucd.mbt_ints("script_values", [index[r[2]] for r in script_runs]),
        "",
        "///|",
        ucd.mbt_strings("script_names", long_names),
        "",
        "///|",
        "/// The Script value of each index, in the same order.",
        "let scripts : FixedArray[Script] = [",
        *[f"  {ucd.camel(long)}," for long in long_names],
        "]",
        "",
        "///|",
        "/// Ranges of every script, start and end interleaved; script `i`",
        "/// owns `script_ranges[script_ranges_offsets[i]:script_ranges_offsets[i + 1]]`.",
        ucd.mbt_ints("script_ranges", script_flat),
        "",
        "///|",
        ucd.mbt_ints("script_ranges_offsets", script_offsets),
        "",
        "///|",
        "/// Code points with script extensions: ranges, then the script indices",
        "/// each range owns, `ext_values[ext_offsets[i]:ext_offsets[i + 1]]`.",
        ucd.mbt_ints("ext_starts", [r[0] for r in ext_runs]),
        "",
        "///|",
        ucd.mbt_ints("ext_ends", [r[1] for r in ext_runs]),
        "",
        "///|",
        ucd.mbt_ints("ext_offsets", offsets),
        "",
        "///|",
        ucd.mbt_ints("ext_values", flat),
        "",
        "///|",
        "/// Ranges of every script under Script_Extensions, start and end",
        "/// interleaved; script `i` owns",
        "/// `scx_ranges[scx_ranges_offsets[i]:scx_ranges_offsets[i + 1]]`.",
        ucd.mbt_ints("scx_ranges", scx_flat),
        "",
        "///|",
        ucd.mbt_ints("scx_ranges_offsets", scx_offsets),
        "",
        "///|",
        "/// Every loose key (UAX #44 LM3) with the script it names, sorted by",
        "/// key so `Script::of` can binary search it.",
        ucd.mbt_strings("loose_keys", [k for k, _ in pairs_by_key]),
        "",
        "///|",
        ucd.mbt_ints("loose_values", [v for _, v in pairs_by_key]),
        "",
    ]
    ucd.write(SRC / "tables.mbt", lines)
    print(f"  {len(long_names)} scripts, {len(script_runs)} runs, {len(ext_runs)} extension runs")

    # ---- test vectors -------------------------------------------------
    def fnv(seq):
        h = 0x811C9DC5
        for x in seq:
            h = ((h ^ (x & 0xFFFFFFFF)) * 0x01000193) & 0xFFFFFFFF
        return h

    def spelled(name):
        return [len(name)] + [ord(c) for c in name]

    script_seq, ext_seq = [], []
    for cp in range(0x110000):
        if 0xD800 <= cp <= 0xDFFF:
            continue
        long = scripts.get(cp, "Unknown")
        script_seq += spelled(long)
        ext = extensions.get(cp)
        names = [long_names[i] for i in ext] if ext is not None else [long]
        ext_seq.append(len(names))
        for nm in names:
            ext_seq += spelled(nm)
    h, h2 = fnv(script_seq), fnv(ext_seq)
    print(f"  script digest {h}, extensions digest {h2}")

    def ranges_digest(buckets):
        seq = []
        for i in range(len(long_names)):
            for a, b in buckets[i]:
                seq += [a, b]
        return fnv(seq)

    h3, h4 = ranges_digest(script_buckets), ranges_digest(scx_buckets)

    of_pairs = [(long, long) for long in long_names] + [
        (code, long) for code, long in zip(codes, long_names)
    ]

    variants = ucd.enum_variants(SRC / "script.mbt", "Script")
    if variants != [ucd.camel(long) for long in long_names]:
        sys.exit("the enum and the table order no longer agree")

    vectors = ucd.header("gen_script.py", version, "Test vectors only; not part of the package.") + [
        "",
        "///|",
        "/// Every script in the order the enum declares them, the order the range",
        "/// digests were taken in.",
        "let script_ranges_order : FixedArray[@script.Script] = [",
        *[f"  {v}," for v in variants],
        "]",
        "",
        "///|",
        f"let script_digest : UInt32 = {h}",
        "",
        "///|",
        f"let extensions_digest : UInt32 = {h2}",
        "",
        "///|",
        "/// Every script's ranges, in the order the enum declares them, each as",
        "/// its start and then its end.",
        f"let script_ranges_digest : UInt32 = {h3}",
        "",
        "///|",
        "/// The same over Script_Extensions.",
        f"let scx_ranges_digest : UInt32 = {h4}",
        "",
        "///|",
        "/// Every long name and four-letter code, with the long name it names.",
        "let of_keys : Array[String] = [",
        *[f"  {ucd.quote(k)}," for k, _ in of_pairs],
        "]",
        "",
        "///|",
        "let of_names : Array[String] = [",
        *[f"  {ucd.quote(n)}," for _, n in of_pairs],
        "]",
        "",
    ]
    ucd.write(SRC / "script_vectors_test.mbt", vectors)


if __name__ == "__main__":
    main()
