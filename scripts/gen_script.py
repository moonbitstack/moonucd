#!/usr/bin/env python3
"""Write src/script/tables.mbt and the test vectors from the UCD.

Scripts.txt gives every code point its script, ScriptExtensions.txt the
scripts a code point can belong to, and PropertyValueAliases.txt the long
name and four-letter code of each. The script enum is ordered by long
name; the tables index into that order.

    python scripts/gen_script.py
"""

import argparse
import sys

sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parent))

import ucd

ROOT = ucd.ROOT
SRC = ROOT / "src" / "script"

FILES = ["Scripts.txt", "ScriptExtensions.txt", "PropertyValueAliases.txt"]


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

    enum_name = lambda long: "".join(
        part.capitalize() if part.islower() else part
        for part in long.replace("-", "_").split("_")
    )

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
        *[f"  {enum_name(long)}," for long in long_names],
        "]",
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

    of_pairs = [(long, long) for long in long_names] + [
        (code, long) for code, long in zip(codes, long_names)
    ]

    vectors = ucd.header("gen_script.py", version, "Test vectors only; not part of the package.") + [
        "",
        "///|",
        f"let script_digest : UInt32 = {h}",
        "",
        "///|",
        f"let extensions_digest : UInt32 = {h2}",
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
