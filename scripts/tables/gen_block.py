#!/usr/bin/env python3
"""Write src/block/tables.mbt and the test vectors from the UCD.

Blocks.txt names every block of the code space; `block` reads it, and
`range` reads it backwards, by name, the loose way of UAX #44 (LM3).

    python scripts/tables/gen_block.py
"""

import argparse
import sys

sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parent))

import ucd

ROOT = ucd.ROOT
SRC = ROOT / "src" / "block"


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
    text = ucd.fetch(version, "Blocks.txt")

    blocks = []
    for f in ucd.records(text):
        a, b = ucd.span(f[0])
        blocks.append((a, b, f[1]))

    # Blocks.txt is sorted by code point, but sort defensively so the binary
    # search can rely on it.
    blocks.sort(key=lambda x: x[0])

    pairs_by_key = {}
    for i, (a, b, name) in enumerate(blocks):
        key = loose_key(name)
        if key in pairs_by_key:
            sys.exit(f"two blocks share the loose key {key!r}")
        pairs_by_key[key] = i
    for f in ucd.records(ucd.fetch(version, "PropertyValueAliases.txt")):
        if f[0] != "blk" or f[2] == "No_Block":
            continue
        target = pairs_by_key.get(loose_key(f[2]))
        if target is None:
            sys.exit(f"the block alias {f[1]!r} names no block")
        for alias in [f[1], *f[3:]]:
            pairs_by_key.setdefault(loose_key(alias), target)
    pairs_by_key = sorted(pairs_by_key.items())

    lines = ucd.header("gen_block.py", version) + [
        "",
        "///|",
        f'let ucd_version : String = "{version}"',
        "",
        "///|",
        "/// Every block, in code point order.",
        ucd.mbt_ints("block_starts", [a for a, _, _ in blocks]),
        "",
        "///|",
        ucd.mbt_ints("block_ends", [b for _, b, _ in blocks]),
        "",
        "///|",
        ucd.mbt_strings("block_names", [name for _, _, name in blocks]),
        "",
        "///|",
        "/// Every loose key (UAX #44 LM3) with the block it names, sorted by",
        "/// key so `range` can binary search it.",
        ucd.mbt_strings("loose_keys", [k for k, _ in pairs_by_key]),
        "",
        "///|",
        ucd.mbt_ints("loose_values", [v for _, v in pairs_by_key]),
        "",
    ]
    ucd.write(SRC / "tables.mbt", lines)
    print(f"  {len(blocks)} blocks")

    # ---- test vectors -------------------------------------------------
    import bisect

    def fnv(seq):
        h = 0x811C9DC5
        for x in seq:
            h = ((h ^ (x & 0xFFFFFFFF)) * 0x01000193) & 0xFFFFFFFF
        return h

    def spelled(name):
        return [len(name)] + [ord(c) for c in name]

    starts = [a for a, _, _ in blocks]
    seq = []
    for cp in range(0x110000):
        if 0xD800 <= cp <= 0xDFFF:
            continue
        i = bisect.bisect_right(starts, cp) - 1
        if i >= 0 and blocks[i][0] <= cp <= blocks[i][1]:
            seq += spelled(blocks[i][2])
        else:
            seq.append(0)
    h = fnv(seq)
    print(f"  block digest {h}")

    vectors = ucd.header("gen_block.py", version, "Test vectors only; not part of the package.") + [
        "",
        "///|",
        f"let block_digest : UInt32 = {h}",
        "",
        "///|",
        "/// Every block name, in code point order, for `range` to be read back.",
        "let block_names_all : Array[String] = [",
        *[f"  {ucd.quote(name)}," for _, _, name in blocks],
        "]",
        "",
    ]
    ucd.write(SRC / "block_vectors_test.mbt", vectors)


if __name__ == "__main__":
    main()
