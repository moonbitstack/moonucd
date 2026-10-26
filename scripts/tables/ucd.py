#!/usr/bin/env python3
"""Shared helpers for the table generators: the UCD cache, the file formats,
and the MoonBit emitters.

Every generator fetches the files it needs once into scripts/tables/.ucd/<version>/
and reuses them, so a second run works offline. The same version always writes
the same bytes.

The UCD files are the ground truth: what a generator writes is derived from
them here, in one place, so no two generators can disagree about a format.
"""

import pathlib
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parents[2]
CACHE = pathlib.Path(__file__).resolve().parent / ".ucd"
BASE = "https://www.unicode.org/Public/{v}/ucd/{f}"


def fetch(version, name):
    """The text of a UCD file, downloaded once per version and cached."""
    path = CACHE / version / name
    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        with urllib.request.urlopen(BASE.format(v=version, f=name)) as r:
            path.write_bytes(r.read())
    return path.read_text(encoding="utf-8")


def records(text):
    """Fields of every record, comments and blank lines dropped."""
    for line in text.splitlines():
        line = line.split("#", 1)[0].strip()
        if line:
            yield [field.strip() for field in line.split(";")]


def span(field):
    """A code point field: one value, or an inclusive `first..last` range."""
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


def mbt_ints(name, values, per_line=12, typ="Int32"):
    """A `let` of a FixedArray of ints, wrapped for a readable width."""
    lines = [f"let {name} : FixedArray[{typ}] = ["]
    for i in range(0, len(values), per_line):
        chunk = ", ".join(str(v) for v in values[i : i + per_line])
        lines.append(f"  {chunk},")
    lines.append("]")
    return "\n".join(lines)


def mbt_strings(name, values, per_line=1):
    """A `let` of a FixedArray of string literals, one per line."""
    lines = [f"let {name} : FixedArray[String] = ["]
    for i in range(0, len(values), per_line):
        chunk = ", ".join(quote(v) for v in values[i : i + per_line])
        lines.append(f"  {chunk},")
    lines.append("]")
    return "\n".join(lines)


def mbt_string_pool(name, text, width=60, per_chunk_chars=180000, escaper=None):
    """A `let` holding `text` as a `String`, split into chunks small enough to
    stay under MoonBit's per-value string-literal length limit and its
    cumulative "text segment" line limit.

    `text` is cut into `width`-char pieces (each its own quoted literal, joined
    with `+`); the pieces are grouped into chunks whose total stays under
    `per_chunk_chars`, each chunk its own `let` preceded by a `///|` segment
    marker so MoonBit counts every chunk as its own text segment (it otherwise
    merges contiguous string-literal `let`s into one and trips
    `text_segment_excceed`), and the named value is the concatenation of every
    chunk. The result is one `String` equal to `text`, but no single
    literal—and no single segment—approaches the limit."""
    if escaper is None:
        escaper = quote_raw
    pieces = []
    i = 0
    while i < len(text):
        piece = text[i : i + width]
        # Escape each piece as a whole: no escape can be split across a piece
        # boundary, so no balancing of `\u{`/`}` against the raw text is needed
        # (and doing so would loop forever when the content contains a literal
        # `}` that is unrelated to an escape).
        pieces.append(f'"{escaper(piece)}"')
        i += len(piece)
    chunks = []
    cur = []
    curlen = 0
    for p in pieces:
        if curlen + len(p) > per_chunk_chars and cur:
            chunks.append(cur)
            cur = []
            curlen = 0
        cur.append(p)
        curlen += len(p)
    if cur:
        chunks.append(cur)
    lines = []
    varnames = []
    for ci, ch in enumerate(chunks):
        v = f"{name}_part{ci}"
        body = "\n".join(
            f"  {p} +" if idx < len(ch) - 1 else f"  {p}"
            for idx, p in enumerate(ch)
        )
        lines.append(f"///|\nlet {v} : String =\n{body}")
        varnames.append(v)
    lines.append(f"///|\nlet {name} : String = " + " + ".join(varnames))
    return "\n".join(lines)


def quote_raw(text):
    """A MoonBit string literal body (no surrounding quotes): escapes only what
    MoonBit string syntax needs; everything else passes through verbatim."""
    out = []
    for ch in text:
        if ch == '"':
            out.append('\\"')
        elif ch == "\\":
            out.append("\\\\")
        elif ch == "\n":
            out.append("\\n")
        elif ch == "\t":
            out.append("\\t")
        elif ch == "\r":
            out.append("\\r")
        else:
            out.append(ch)
    return "".join(out)


def quote_full(text):
    """The body of a MoonBit string literal that escapes every non-ASCII code
    point as `\\u{...}`, so the lexer never meets a character it refuses to read
    literally. Returns the body only (no surrounding quotes) — `mbt_string_pool`
    adds those."""
    out = []
    for ch in text:
        cp = ord(ch)
        if ch == '"':
            out.append('\\"')
        elif ch == "\\":
            out.append("\\\\")
        elif ch == "\n":
            out.append("\\n")
        elif ch == "\t":
            out.append("\\t")
        elif ch == "\r":
            out.append("\\r")
        elif cp < 0x20 or cp == 0x7F or cp >= 0x80:
            out.append(f"\\u{{{cp:04X}}}")
        else:
            out.append(ch)
    return "".join(out)


def quote(text):
    """A MoonBit string literal: escapes for backslash, quote and controls."""
    out = ['"']
    for ch in text:
        cp = ord(ch)
        if ch == '"':
            out.append('\\"')
        elif ch == "\\":
            out.append("\\\\")
        elif ch == "\n":
            out.append("\\n")
        elif ch == "\t":
            out.append("\\t")
        elif ch == "\r":
            out.append("\\r")
        elif cp < 0x20 or cp == 0x7F:
            out.append(f"\\u{{{cp:04X}}}")
        else:
            out.append(ch)
    out.append('"')
    return "".join(out)


def header(script, version, extra=None):
    """The banner every generated file opens with."""
    lines = [
        f"// Generated by scripts/tables/{script} from the Unicode Character",
        f"// Database {version}. Do not edit by hand.",
    ]
    if extra:
        lines.append(f"// {extra}")
    return lines


def write(path, lines):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
    print(f"wrote {path.relative_to(ROOT)}")
