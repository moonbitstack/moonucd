#!/usr/bin/env python3
"""Generate the `linebreak` sub-package (UAX #14 line breaking).

Tables come from the UCD 17.0.0 LineBreak.txt; conformance is checked by
replaying the official LineBreakTest.txt.

Run `python3 scripts/tables/gen_linebreak.py --check` to validate the rule engine
against the test file before emitting anything.
"""

import pathlib
import sys

import ucd

VERSION = "17.0.0"
SRC = pathlib.Path(__file__).resolve().parents[2] / "src" / "linebreak"

UCD = "https://www.unicode.org/Public/{v}/ucd/{f}"

CLASSES = [
    "XX",  # 0 (resolved to AL by LB1)
    "AI", "AK", "AL", "AP", "AS", "B2", "BA", "BB", "BK", "CB", "CJ", "CL",
    "CM", "CP", "CR", "EB", "EM", "EX", "GL", "H2", "H3", "HH", "HL", "HY",
    "ID", "IN", "IS", "JL", "JT", "JV", "LF", "NL", "NS", "NU", "OP", "PO",
    "PR", "QU", "RI", "SA", "SG", "SP", "SY", "VF", "VI", "WJ", "ZW", "ZWJ",
]

C = {name: i for i, name in enumerate(CLASSES)}
XX, AI, AK, AL, AP, AS, B2, BA, BB, BK, CB, CJ, CL, CM, CP, CR, EB, EM, EX, \
    GL, H2, H3, HH, HL, HY, ID, IN, IS, JL, JT, JV, LF, NL, NS, NU, OP, PO, \
    PR, QU, RI, SA, SG, SP, SY, VF, VI, WJ, ZW, ZWJ = (
        C[n] for n in CLASSES
    )

# U+2329 / U+232A are classified OP / CL but are mathematical angle brackets
# that must not participate in the parenthesis rules of LB30.
BRACKET_EXCEPTION = (0x2329, 0x232A)
# U+25CC DOTTED CIRCLE is the visible stand-in for a combining mark / virama
# (the `◌` slot) in the Brahmic rules LB28a.
DOTTED_CIRCLE = 0x25CC

_GC = None
_EXTPICT = None
EAW = {}


def fetch(name):
    return ucd.fetch(VERSION, name)


def load_eaw():
    """East_Asian_Width per code point (for the East-Asian-aware LB30 rules)."""
    global EAW
    if EAW:
        return EAW
    for line in fetch("EastAsianWidth.txt").splitlines():
        line = line.split("#", 1)[0].strip()
        if not line or ";" not in line:
            continue
        field, value = line.split(";", 1)
        field, value = field.strip(), value.strip()
        if ".." in field:
            a, b = field.split("..")
            for cp in range(int(a, 16), int(b, 16) + 1):
                EAW[cp] = value
        else:
            EAW[int(field, 16)] = value
    return EAW


def load_gc():
    """General category per code point (used for SA->CM and quote pairing)."""
    global _GC
    if _GC is not None:
        return _GC
    gc = {}
    for line in fetch("UnicodeData.txt").splitlines():
        f = line.split(";")
        if len(f) < 3:
            continue
        gc[int(f[0], 16)] = f[2]
    _GC = gc
    return gc


def load():
    """Line_Break property per code point."""
    raw = {}
    for line in fetch("LineBreak.txt").splitlines():
        line = line.split("#", 1)[0].strip()
        if not line or ";" not in line:
            continue
        field, value = line.split(";", 1)
        field, value = field.strip(), value.strip()
        if ".." in field:
            a, b = field.split("..")
            for cp in range(int(a, 16), int(b, 16) + 1):
                raw[cp] = value
        else:
            raw[int(field, 16)] = value
    return raw


def resolve(raw):
    """LB1: resolve the classes the algorithm does not treat specially.

    AI, SG, XX -> AL; CJ -> NS; SA -> CM when Mn/Mc, else AL."""
    gc = load_gc()
    out = {}
    for cp, v in raw.items():
        if v in ("AI", "SG", "XX"):
            out[cp] = AL
        elif v == "CJ":
            out[cp] = NS
        elif v == "SA":
            out[cp] = CM if gc.get(cp) in ("Mn", "Mc") else AL
        else:
            out[cp] = C[v]
    return out


def is_ako(cls, cp):
    """A character matching the `◌` slot in the Brahmic rules LB28a: an aksara
    start, an aksara, or the Dotted Circle stand-in."""
    return cls in (AK, AS) or cp == DOTTED_CIRCLE


def load_extpict():
    """Extended_Pictographic code points (for the second clause of LB30b).

    UCD 17.0.0 ships this property inside `emoji/emoji-data.txt`; an older
    standalone `emoji/Extended_Pictographic.txt` is tried as a fallback."""
    global _EXTPICT
    if _EXTPICT is not None:
        return _EXTPICT

    def parse(text):
        out = set()
        for line in text.splitlines():
            line = line.split("#", 1)[0].strip()
            if not line or ";" not in line:
                continue
            field, value = line.split(";", 1)
            field, value = field.strip(), value.strip()
            if value != "Extended_Pictographic":
                continue
            if ".." in field:
                a, b = field.split("..")
                for cp in range(int(a, 16), int(b, 16) + 1):
                    out.add(cp)
            else:
                out.add(int(field, 16))
        return out

    s = parse(fetch("emoji/emoji-data.txt"))
    if not s:
        s = parse(fetch("emoji/Extended_Pictographic.txt"))
    _EXTPICT = s
    return s


def build_tokens(cls, cps, gc):
    """LB9/LB10: absorb each combining mark / ZWJ into a usable base.

    Returns (tokens, absorbed). `absorbed[i]` is True when original position i
    is a combining mark or ZWJ glued to the preceding base, so there is no break
    opportunity before it. A mark without a usable base resolves to AL; a ZWJ
    without a usable base stays as a standalone ZWJ token that does not bind
    forward. A ZWJ that *is* absorbed into a real base sets the base token's
    `zwj` flag, which makes the break after it prohibited (rule 8.1)."""
    tokens = []
    absorbed = []
    for i, c in enumerate(cls):
        if c in (CM, ZWJ):
            if tokens and tokens[-1]["cls"] not in (BK, CR, LF, NL, SP, ZW, ZWJ):
                if c == ZWJ:
                    tokens[-1]["zwj"] = True
                absorbed.append(True)
                continue
            if c == ZWJ:
                tokens.append({
                    "idx": i, "cls": ZWJ, "cp": cps[i],
                    "gc": gc.get(cps[i], ""), "pi": False, "pf": False,
                    "zwj": False,
                })
            else:
                tokens.append({
                    "idx": i, "cls": AL, "cp": cps[i],
                    "gc": gc.get(cps[i], ""), "pi": False, "pf": False,
                    "zwj": False,
                })
            absorbed.append(False)
        else:
            g = gc.get(cps[i], "")
            tokens.append({
                "idx": i, "cls": c, "cp": cps[i], "gc": g,
                "pi": g == "Pi", "pf": g == "Pf", "zwj": False,
            })
            absorbed.append(False)
    return tokens, absorbed


def back_skip_sp(tokens, start):
    """Index of the token just before a run of spaces, or -1 for start-of-text."""
    j = start - 1
    while j >= 0 and tokens[j]["cls"] == SP:
        j -= 1
    return j


def num_ctx(tokens, k):
    """LB25 numeric context ending at the left side of the break (tokens[k-1]).

    The UAX #14 numeric rules (25.01-25.15) all share the `NU (SY|IS)*` prefix:
    a digit optionally followed by infix separators.  This returns the class of
    the *terminating* character of that run so the caller can select the exact
    sub-rule:

      'NU'  -- `NU (SY|IS)*`                       (number run, ends in NU/SY/IS),
      'CL'  -- `NU (SY|IS)* CL`                    (number run + close),
      'CP'  -- `NU (SY|IS)* CP`                    (number run + close),
      None  -- no qualifying numeric run.

    Spaces are skipped, matching the "even with intervening spaces" clause."""
    j = k - 1
    while j >= 0 and tokens[j]["cls"] == SP:
        j -= 1
    if j < 0:
        return None
    end = tokens[j]["cls"]
    if end in (CL, CP):
        p = j - 1
        while p >= 0 and tokens[p]["cls"] == SP:
            p -= 1
        if p < 0 or tokens[p]["cls"] not in (NU, SY, IS):
            return None
        q = p
        while q - 1 >= 0 and tokens[q - 1]["cls"] in (NU, SY, IS):
            q -= 1
        return "CL" if end == CL and tokens[q]["cls"] == NU else (
            "CP" if tokens[q]["cls"] == NU else None)
    if end == NU:
        # A lone digit is the head of `NU (SY|IS)*`; the break before it is a
        # number-internal break regardless of what precedes it.
        return "NU"
    if end in (SY, IS):
        # `NU (SY|IS)*`: the run must be NU-led (its head is a digit).
        q = j
        while q - 1 >= 0 and tokens[q - 1]["cls"] in (NU, SY, IS):
            q -= 1
        if tokens[q]["cls"] == NU:
            return "NU"
        return None
    return None


CONTEXT_BEFORE_QUOTE = (BK, CR, LF, NL, OP, QU, GL, SP, ZW)
AFTER_CLOSE_QUOTE = (SP, GL, WJ, CL, QU, CP, EX, IS, SY, BK, CR, LF, NL, ZW)


def break_at(tokens, k, extpict):
    """Break decision between tokens[k-1] and tokens[k]. True = break (÷),
    False = keep (×).

    Implements the canonical UAX #14 pair table (rules 0.2 .. 999.0) in the
    standard's application order: the first matching rule decides, and the
    implicit default (999.0) is to break. Combining marks / ZWJ are already
    absorbed into their base by build_tokens, so no break opportunity exists
    before an absorbed mark."""
    left = tokens[k - 1]
    right = tokens[k]
    lcls = left["cls"]
    rcls = right["cls"]
    nxt = tokens[k + 1]["cls"] if k + 1 < len(tokens) else -1

    # LB4: break after a mandatory break.
    if lcls == BK:
        return True
    # LB5: CR x LF, but break after CR, LF and NL.
    if lcls == CR and rcls == LF:
        return False
    if lcls in (CR, LF, NL):
        return True
    # LB6: do not break before hard breaks.
    if rcls in (BK, CR, LF, NL):
        return False
    # LB7: do not break before spaces or a zero width space.
    if rcls == SP:
        return False
    if rcls == ZW:
        return False
    # LB8: break after ZW, even with spaces in between.
    if lcls == ZW:
        return True
    if lcls == SP:
        j = back_skip_sp(tokens, k - 1)
        if j >= 0 and tokens[j]["cls"] == ZW:
            return True
    # LB8.1: do not break after a ZWJ.
    if lcls == ZWJ:
        return False
    # An absorbed ZWJ binds the base to the following character (rule 8.1).
    if left.get("zwj"):
        return False
    # LB11: do not break before or after a word joiner.
    if rcls == WJ:
        return False
    if lcls == WJ:
        return False
    # LB12 / LB12a: glue is sticky after, and sticky before except after a
    # space, break symbol, or hyphen.
    if lcls == GL:
        return False
    if rcls == GL and lcls not in (SP, BA, HY, HH):
        return False
    # LB15.3: space then infix separator followed by a digit -> allow break
    # (exception to LB13's × IS / × SY). This must precede LB13 so the break
    # overrides the keep.
    if lcls == SP and rcls == IS and nxt == NU:
        return True
    # LB13: do not break before closing punctuation / infix separators.
    if rcls in (EX, CL, CP, SY, IS):
        return False
    # LB14: do not break after an opening bracket, even with spaces.
    if lcls == OP:
        return False
    if lcls == SP:
        j = back_skip_sp(tokens, k - 1)
        if j >= 0 and tokens[j]["cls"] == OP:
            return False
    # LB15a (rule 15.11): do not break after an opening quote, even with
    # intervening spaces. The break is the one after the quote (or the space
    # run following it), so skip it when the right side is a space itself.
    if rcls != SP:
        j = k - 1
        while j >= 0 and tokens[j]["cls"] == SP:
            j -= 1
        if j >= 0 and tokens[j]["cls"] == QU and tokens[j]["pi"]:
            p = j - 1
            if p < 0 or tokens[p]["cls"] in CONTEXT_BEFORE_QUOTE:
                return False
    # LB15b: do not break before a closing quote followed by the listed classes
    # or end of text.
    if rcls == QU and right["pf"]:
        if k + 1 >= len(tokens) or nxt in AFTER_CLOSE_QUOTE:
            return False
    # LB16: do not break between closing punctuation and a non-starter.
    if rcls == NS:
        j = back_skip_sp(tokens, k - 1)
        if j >= 0 and tokens[j]["cls"] in (CL, CP):
            return False
    # LB17: do not break within a pair of em-dashes, even with intervening
    # spaces.
    if rcls == B2:
        j = back_skip_sp(tokens, k)
        if j >= 0 and tokens[j]["cls"] == B2:
            return False
    # LB18: break after spaces.
    if lcls == SP:
        return True
    # LB19 (canonical): × [QU - Pi] ; [QU - Pf] ×
    if rcls == QU and not right["pi"]:
        return False
    if lcls == QU and not left["pf"]:
        return False
    # LB19a: East-Asian-aware quote rules (EA = East_Asian_Width ∈ {A, W, F, H}).
    if rcls == QU and not is_ea_char(lcls, left["cp"]):
        return False                                # [^EA] × QU
    if rcls == QU:
        after = tokens[k + 1] if k + 1 < len(tokens) else None
        if after is None or not is_ea_char(after["cls"], after["cp"]):
            return False                            # × QU ([^EA]|eot)
    if lcls == QU and not is_ea_char(rcls, right["cp"]):
        return False                                # QU × [^EA]
    if lcls == QU:
        prev = tokens[k - 2] if k - 2 >= 0 else None
        if prev is None or not is_ea_char(prev["cls"], prev["cp"]):
            return False                            # (sot|[^EA]) QU ×
    # LB20: break before and after a contingent break.
    if lcls == CB or rcls == CB:
        return True
    # LB20a: a Hebrew hyphen / maqaf keeps with a letter when preceded by the
    # listed contexts.
    if lcls in (HY, HH) and rcls in (AL, HL):
        if k - 2 < 0 or tokens[k - 2]["cls"] in (BK, CR, LF, NL, SP, ZW, CB, GL):
            return False
    # LB21: do not break before a hyphen, non-starter, or Hebrew punctuation,
    # or after an acute accent.
    if rcls in (BA, HY, NS, HH):
        return False
    if lcls == BB:
        return False
    # LB21a: HL (HY | HH) × [^HL] -- do not break after a Hebrew letter
    # followed by a hyphen / Hebrew hyphen, unless the following character is
    # itself a Hebrew letter.
    if lcls in (HY, HH) and rcls != HL:
        p = k - 2
        while p >= 0 and tokens[p]["cls"] == SP:
            p -= 1
        if p >= 0 and tokens[p]["cls"] == HL:
            return False
    # LB21b: do not break between a solidus and a Hebrew letter.
    if lcls == SY and rcls == HL:
        return False
    # LB22: do not break before an inseparable character.
    if rcls == IN:
        return False
    # LB23: do not break between digits and letters.
    if lcls in (AL, HL) and rcls == NU:
        return False
    if lcls == NU and rcls in (AL, HL):
        return False
    # LB23a: prefix/postfix next to ideographs, or ideograph and postfix.
    if lcls == PR and rcls in (ID, EB, EM):
        return False
    if lcls in (ID, EB, EM) and rcls == PO:
        return False
    # LB24: prefix and postfix next to letters.
    if lcls in (PR, PO) and rcls in (AL, HL):
        return False
    if lcls in (AL, HL) and rcls in (PR, PO):
        return False
    # LB25: do not break within numbers (UAX #14 rules 25.01–25.15).
    ctx = num_ctx(tokens, k)
    if rcls == PO and ctx in ("NU", "CL", "CP"):
        return False                                   # 25.01–25.06 (NU(SY|IS)* × PO)
    if rcls == PR and ctx in ("NU", "CL", "CP"):
        return False                                   # 25.03/25.04/25.06 (NU(SY|IS)* × PR)
    if lcls in (PO, PR) and rcls == OP and _op_followed_by_nu(tokens, k):
        return False                                   # 25.07 / 25.1  (PO/PR × OP NU)
    if lcls in (PO, PR) and rcls == OP and _op_followed_by_is_nu(tokens, k):
        return False                                   # 25.08 / 25.11 (PO/PR × OP IS NU)
    if rcls == NU:
        if ctx in ("NU", "CL", "CP"):
            return False                               # 25.15 (NU(SY|IS)* × NU)
        if lcls in (PR, PO):
            return False                               # 25.09 / 25.12
        if lcls == HY:
            return False                               # 25.13
        if lcls == IS:
            return False                               # 25.14
    # LB26: do not break a Korean syllable.
    if lcls == JL and rcls in (JL, JV, H2, H3):
        return False
    if lcls in (JV, H2) and rcls in (JV, JT):
        return False
    if lcls in (JT, H3) and rcls == JT:
        return False
    # LB27: do not break a Korean syllable from its surrounding punctuation.
    if lcls in (JL, JV, JT, H2, H3) and rcls == PO:
        return False
    if lcls == PR and rcls in (JL, JV, JT, H2, H3):
        return False
    # LB28: do not break between alphabetics.
    if lcls in (AL, HL) and rcls in (AL, HL):
        return False
    # LB28a: do not break inside the orthographic syllables of Brahmic scripts.
    # `◌` in the rule patterns stands for an absorbed combining mark / virama,
    # which is carried by an aksara base (AK / AS).
    if lcls == AP and is_ako(rcls, right["cp"]):
        return False                                   # AP × (AK|◌|AS)
    if is_ako(lcls, left["cp"]) and rcls in (VF, VI):
        return False                                   # (AK|◌|AS) × (VF|VI)
    if lcls == VI and is_ako(rcls, right["cp"]):
        if k - 2 >= 0 and is_ako(tokens[k - 2]["cls"], tokens[k - 2]["cp"]):
            return False                               # (AK|◌|AS) VI × (AK|◌)
    if is_ako(lcls, left["cp"]) and is_ako(rcls, right["cp"]) and nxt == VF:
        return False                                   # (AK|◌|AS) × (AK|◌|AS) VF
    # LB29: do not break between a numeric infix separator and letters.
    if lcls == IS and rcls in (AL, HL):
        return False
    # LB30: do not break between letters, numbers, or symbols and opening or
    # closing parentheses. The mathematical angle brackets (U+2329/232A) are
    # excluded; fullwidth parentheses (East_Asian_Width W/F) do not participate.
    if lcls in (AL, HL, NU) and rcls == OP:
        if right["cp"] not in BRACKET_EXCEPTION and not _ea_wide(right["cp"]):
            return False
    if rcls in (AL, HL, NU) and lcls == CP:
        if left["cp"] not in BRACKET_EXCEPTION and not _ea_wide(left["cp"]):
            return False
    # LB30a: regional indicator symbols keep in pairs.
    if lcls == RI and rcls == RI:
        count = sum(1 for t in tokens[:k - 1] if t["cls"] == RI)
        if count % 2 == 0:
            return False
    # LB30b: do not break within an emoji modifier sequence.
    if lcls == EB and rcls == EM:
        return False
    if rcls == EM and left["gc"] in ("Cn", "") and left["cp"] in extpict:
        return False
    # LB31 / 999.0: break everywhere else.
    return True


def _ea_wide(cp):
    """True when a code point has East_Asian_Width W or F (a fullwidth / wide
    parenthesis, which does not participate in LB30)."""
    return EAW.get(cp) in ("W", "F")


def is_ea_char(cls, cp):
    """An "East Asian" character for the East-Asian-aware quote rules: a class
    in (ID, EB, EM, CJ), or any code point with East_Asian_Width in
    {A, W, F, H}."""
    if cls in (ID, EB, EM, CJ):
        return True
    return EAW.get(cp) in ("W", "F", "H", "A")


def _op_followed_by_nu(tokens, k):
    """LB25.07 / 25.1: is the opening parenthesis at tokens[k] followed (after
    optional spaces) by a digit?  Used for `PO × OP NU` and `PR × OP NU`."""
    if k >= len(tokens) or tokens[k]["cls"] != OP:
        return False
    m = k + 1
    while m < len(tokens) and tokens[m]["cls"] == SP:
        m += 1
    return m < len(tokens) and tokens[m]["cls"] == NU


def _op_followed_by_is_nu(tokens, k):
    """LB25.08 / 25.11: is the opening parenthesis at tokens[k] followed (after
    optional spaces) by IS (spaces) NU?  Used for `PO × OP IS NU` and
    `PR × OP IS NU`."""
    if k >= len(tokens) or tokens[k]["cls"] != OP:
        return False
    m = k + 1
    while m < len(tokens) and tokens[m]["cls"] == SP:
        m += 1
    if m >= len(tokens) or tokens[m]["cls"] != IS:
        return False
    m += 1
    while m < len(tokens) and tokens[m]["cls"] == SP:
        m += 1
    return m < len(tokens) and tokens[m]["cls"] == NU


def run(cls, cps):
    gc = load_gc()
    load_eaw()
    tokens, absorbed = build_tokens(cls, cps, gc)
    extpict = load_extpict()
    n = len(cls)
    result = [False] * (n - 1)
    first2tok = {t["idx"]: ti for ti, t in enumerate(tokens)}
    for i in range(1, n):
        if absorbed[i]:
            result[i - 1] = False  # LB9: no break before an absorbed mark
            continue
        ti = first2tok[i]
        if ti == 0:
            result[i - 1] = False  # start of text
        else:
            result[i - 1] = break_at(tokens, ti, extpict)
    return result


def parse_test(text):
    out = []
    for line in text.splitlines():
        line = line.split("#", 1)[0].strip()
        if not line or "÷" not in line:
            continue
        toks = line.split()
        codepoints = []
        marks = []
        i = 1  # toks[0] is the leading sot marker
        while i < len(toks):
            codepoints.append(int(toks[i], 16))
            i += 1
            if i < len(toks):
                marks.append(toks[i] == "÷")
                i += 1
        out.append((codepoints, marks[:-1]))
    return out


def validate():
    raw = load()
    res = resolve(raw)
    default = AL

    def class_of(cp):
        return res.get(cp, default)

    text = fetch("auxiliary/LineBreakTest.txt")
    total = errors = 0
    shown = 0
    for cps, expected in parse_test(text):
        cls = [class_of(cp) for cp in cps]
        got = run(cls, cps)
        total += 1
        if got != expected:
            errors += 1
            if shown < 12:
                shown += 1
                exp_s = " ".join("÷" if b else "×" for b in expected)
                got_s = " ".join("÷" if b else "×" for b in got)
                names = " ".join(CLASSES[c] for c in cls)
                print(f"  #{total}: exp[{exp_s}] got[{got_s}] :: "
                      + " ".join(f"{c:04X}" for c in cps) + f"  [{names}]")
    print(f"linebreak: {total} lines, {errors} errors")
    return errors


# ---------------------------------------------------------------------------
# The `linebreak` package sources
# ---------------------------------------------------------------------------

# Classes whose `let` alias the rule code never references (they are resolved
# away by LB1, so they are stored nowhere and only exist as enum variants).
LB_ALIAS_SKIP = ("XX", "AI", "SG", "SA")

EAW_CODE = {"A": 1, "F": 2, "H": 3, "N": 4, "Na": 5, "W": 6}
GC_CODE = {"Mn": 1, "Mc": 2, "Pi": 3, "Pf": 4, "Cn": 5}


def emit_enums():
    """The Lb enum plus the internal Int32 class aliases and the EAW / GC codes."""
    out = []
    out.append("///|")
    out.append("/// A line-break class, after the LB1 resolution the algorithm applies.")
    out.append("pub(all) enum Lb {")
    for v in CLASSES:
        out.append(f"  {v}")
    out.append("} derive(Eq)")
    out.append("///|")
    out.append("pub extend Lb with Eq::{equal, not_equal}")
    out.append("///|")
    out.append("pub impl Show for Lb with fn output(self, logger) {")
    out.append("  match self {")
    for v in CLASSES:
        out.append(f'    {v} => logger.write_string("{v}")')
    out.append("  }")
    out.append("}")
    out.append("///|")
    out.append("pub extend Lb with Show::{to_string, output}")
    out.append("///|")
    out.append("/// The Lb value of a stored class code.")
    out.append("fn lb_of_code(code : Int32) -> Lb {")
    out.append("  match code {")
    for i, v in enumerate(CLASSES):
        out.append(f"    {i} => {v}")
    out.append(f"    _ => {CLASSES[0]}")
    out.append("  }")
    out.append("}")
    out.append("///|")
    out.append("/// The line-break class of a character.")
    out.append("pub fn lb_property(ch : Char) -> Lb {")
    out.append("  lb_of_code(lb_lookup(ch.to_int()))")
    out.append("}")
    out.append("///|")
    out.append("// Line-break class codes, matching lb_values.")
    for i, v in enumerate(CLASSES):
        if v in LB_ALIAS_SKIP:
            continue
        alias = v.lower()
        if alias in ("as", "in"):  # MoonBit keywords
            alias += "_"
        out.append(f"let lb_{alias} : Int32 = {i}")
    out.append("///|")
    out.append("// East_Asian_Width codes (is_ea_char / ea_wide).")
    out.append("let eaw_a : Int32 = 1")
    out.append("let eaw_f : Int32 = 2")
    out.append("let eaw_h : Int32 = 3")
    out.append("let eaw_w : Int32 = 6")
    out.append("///|")
    out.append("// General_Category codes used by the rules (Pi / Pf, Cn).")
    out.append("let gc_pi : Int32 = 3")
    out.append("let gc_pf : Int32 = 4")
    out.append("let gc_cn : Int32 = 5")
    out.append("let gc_unassigned : Int32 = 7")
    out.append("///|")
    out.append("// U+25CC DOTTED CIRCLE, the stand-in for an absorbed mark in LB28a.")
    out.append("let dotted_circle : Int = 0x25CC")
    return "\n".join(out)


def emit_prop(key, rs):
    out = []
    out.append("///|")
    out.append(f"/// {key} runs over the code space (value other than the default).")
    out.append(ucd.mbt_ints(f"{key}_starts", [r[0] for r in rs], per_line=12))
    out.append("///|")
    out.append(ucd.mbt_ints(f"{key}_ends", [r[1] for r in rs], per_line=12))
    out.append("///|")
    out.append(ucd.mbt_ints(f"{key}_values", [r[2] for r in rs], per_line=12))
    return out


def emit_tables():
    """tables.mbt: the resolved Line_Break, East_Asian_Width, General_Category
    runs and the Extended_Pictographic set that the rules look up."""
    load_eaw()
    gc = load_gc()
    res = resolve(load())  # cp -> resolved class code (C[name])
    lines = ucd.header("gen_linebreak.py", VERSION)
    lines.append("///|")
    lines.append('let ucd_version : String = "17.0.0"')
    lines += emit_prop("lb", ucd.runs(res, C["AL"]))
    eaw_lookup = {cp: EAW_CODE.get(v, 0) for cp, v in EAW.items()}
    lines += emit_prop("eaw", ucd.runs(eaw_lookup, 0))
    gc_lookup = {cp: GC_CODE.get(v, 0) for cp, v in gc.items()}
    # Default 7 marks a code point absent from UnicodeData (unassigned), kept
    # distinct from 0 (an assigned code point with no special GC code).
    lines += emit_prop("gc", ucd.runs(gc_lookup, 7))
    ep = load_extpict()
    rs = ucd.merge([(cp, cp) for cp in sorted(ep)])
    lines.append("///|")
    lines.append("/// Extended_Pictographic ranges (LB30b).")
    lines.append(ucd.mbt_ints("ep_starts", [r[0] for r in rs], per_line=12))
    lines.append("///|")
    lines.append(ucd.mbt_ints("ep_ends", [r[1] for r in rs], per_line=12))
    return "\n".join(lines)


LINEBREAK_MBT = r'''
///|
/// Binary search over (start, end) runs.
fn find_run(
  starts : FixedArray[Int32],
  ends : FixedArray[Int32],
  cp : Int32,
) -> Int32? {
  let mut a = 0
  let mut b = starts.length()
  while a < b {
    let mid = (a + b) / 2
    if ends[mid] < cp {
      a = mid + 1
    } else {
      b = mid
    }
  }
  if a < starts.length() && starts[a] <= cp {
    Some(a)
  } else {
    None
  }
}

///|
fn lb_lookup(cp : Int) -> Int32 {
  match find_run(lb_starts, lb_ends, cp) {
    Some(i) => lb_values[i]
    None => lb_al
  }
}

///|
fn eaw_lookup(cp : Int) -> Int32 {
  match find_run(eaw_starts, eaw_ends, cp) {
    Some(i) => eaw_values[i]
    None => 0
  }
}

///|
fn gc_lookup(cp : Int) -> Int32 {
  match find_run(gc_starts, gc_ends, cp) {
    Some(i) => gc_values[i]
    None => gc_unassigned
  }
}

///|
fn is_ext_pict(cp : Int) -> Bool {
  match find_run(ep_starts, ep_ends, cp) {
    Some(_) => true
    None => false
  }
}

///|
/// East-Asian character for LB19a: an ideograph / Hangul / CJK class, or a code
/// point with East_Asian_Width A / W / F / H.
fn is_ea_char(cls : Int32, cp : Int) -> Bool {
  if cls == lb_id || cls == lb_eb || cls == lb_em || cls == lb_cj {
    true
  } else {
    let e = eaw_lookup(cp)
    e == eaw_a || e == eaw_f || e == eaw_h || e == eaw_w
  }
}

///|
/// An aksara start, an aksara, or the Dotted Circle stand-in (LB28a).
fn is_ako(cls : Int32, cp : Int) -> Bool {
  cls == lb_ak || cls == lb_as_ || cp == dotted_circle
}

///|
/// A fullwidth / wide parenthesis does not participate in LB30.
fn ea_wide(cp : Int) -> Bool {
  let e = eaw_lookup(cp)
  e == eaw_w || e == eaw_f
}

///|
fn back_skip_sp(tokens : Array[LbToken], start : Int) -> Int {
  let mut j = start - 1
  while j >= 0 && tokens[j].cls == lb_sp {
    j -= 1
  }
  j
}

///|
fn before_quote(c : Int32) -> Bool {
  c == lb_bk || c == lb_cr || c == lb_lf || c == lb_nl || c == lb_op ||
  c == lb_qu || c == lb_gl || c == lb_sp || c == lb_zw
}

///|
fn after_close(c : Int32) -> Bool {
  c == lb_sp || c == lb_gl || c == lb_wj || c == lb_cl || c == lb_qu ||
  c == lb_cp || c == lb_ex || c == lb_is || c == lb_sy || c == lb_bk ||
  c == lb_cr || c == lb_lf || c == lb_nl || c == lb_zw
}

///|
fn ctx_before(c : Int32) -> Bool {
  c == lb_bk || c == lb_cr || c == lb_lf || c == lb_nl || c == lb_sp ||
  c == lb_zw || c == lb_cb || c == lb_gl
}

///|
fn is_nu_sy_is(c : Int32) -> Bool {
  c == lb_nu || c == lb_sy || c == lb_is
}

// LB25 numeric context ending at the left side of the break (tokens[k-1]).
///|
fn num_ctx(tokens : Array[LbToken], k : Int) -> Int {
  let mut j = k - 1
  while j >= 0 && tokens[j].cls == lb_sp {
    j -= 1
  }
  if j < 0 {
    return 0
  }
  let end = tokens[j].cls
  if end == lb_cl || end == lb_cp {
    let mut p = j - 1
    while p >= 0 && tokens[p].cls == lb_sp {
      p -= 1
    }
    if p < 0 || !is_nu_sy_is(tokens[p].cls) {
      return 0
    }
    let mut q = p
    while q - 1 >= 0 && is_nu_sy_is(tokens[q - 1].cls) {
      q -= 1
    }
    if end == lb_cl && tokens[q].cls == lb_nu {
      return 2
    } else if tokens[q].cls == lb_nu {
      return 3
    } else {
      return 0
    }
  }
  if end == lb_nu {
    return 1
  }
  if end == lb_sy || end == lb_is {
    let mut q = j
    while q - 1 >= 0 && is_nu_sy_is(tokens[q - 1].cls) {
      q -= 1
    }
    if tokens[q].cls == lb_nu {
      return 1
    }
    return 0
  }
  return 0
}

///|
fn op_followed_by_nu(tokens : Array[LbToken], k : Int) -> Bool {
  if k >= tokens.length() || tokens[k].cls != lb_op {
    false
  } else {
    let mut m = k + 1
    while m < tokens.length() && tokens[m].cls == lb_sp {
      m += 1
    }
    m < tokens.length() && tokens[m].cls == lb_nu
  }
}

///|
fn op_followed_by_is_nu(tokens : Array[LbToken], k : Int) -> Bool {
  if k >= tokens.length() || tokens[k].cls != lb_op {
    false
  } else {
    let mut m = k + 1
    while m < tokens.length() && tokens[m].cls == lb_sp {
      m += 1
    }
    if m >= tokens.length() || tokens[m].cls != lb_is {
      false
    } else {
      m += 1
      while m < tokens.length() && tokens[m].cls == lb_sp {
        m += 1
      }
      m < tokens.length() && tokens[m].cls == lb_nu
    }
  }
}

///|
/// A token after LB9 / LB10: a code point with its class, code point, general
/// category, the Pi / Pf flags, and whether a ZWJ was absorbed into it.
priv struct LbToken {
  idx : Int
  cls : Int32
  cp : Int
  gc : Int32
  pi : Bool
  pf : Bool
  mut zwj : Bool
}

///|
/// LB9 / LB10: absorb each combining mark / ZWJ into a usable base.
fn build_tokens(
  lb : Array[Int32],
  cps : Array[Int],
  gc : Array[Int32],
) -> (Array[LbToken], Array[Bool]) {
  let tokens : Array[LbToken] = []
  let absorbed : Array[Bool] = []
  for i = 0; i < cps.length(); i = i + 1 {
    let c = lb[i]
    if c == lb_cm || c == lb_zwj {
      let absorbable = tokens.length() > 0 && {
        let last = tokens[tokens.length() - 1]
        !(
          last.cls == lb_bk || last.cls == lb_cr || last.cls == lb_lf ||
          last.cls == lb_nl || last.cls == lb_sp || last.cls == lb_zw ||
          last.cls == lb_zwj
        )
      }
      if absorbable {
        if c == lb_zwj {
          let t = tokens[tokens.length() - 1]
          t.zwj = true
          tokens[tokens.length() - 1] = t
        }
        absorbed.push(true)
      } else {
        if c == lb_zwj {
          tokens.push({
            idx: i, cls: lb_zwj, cp: cps[i], gc: gc[i], pi: false, pf: false,
            zwj: false,
          })
        } else {
          tokens.push({
            idx: i, cls: lb_al, cp: cps[i], gc: gc[i], pi: false, pf: false,
            zwj: false,
          })
        }
        absorbed.push(false)
      }
    } else {
      let g = gc[i]
      tokens.push({
        idx: i, cls: c, cp: cps[i], gc: g, pi: g == gc_pi, pf: g == gc_pf,
        zwj: false,
      })
      absorbed.push(false)
    }
  }
  (tokens, absorbed)
}

///|
/// Whether a break opportunity falls between tokens[k-1] and tokens[k].
/// `true` means break (÷); `false` means keep (×).
fn break_at(tokens : Array[LbToken], k : Int) -> Bool {
  let left = tokens[k - 1]
  let right = tokens[k]
  let lcls = left.cls
  let rcls = right.cls
  let nxt = if k + 1 < tokens.length() { tokens[k + 1].cls } else { -1 }
  // LB4
  if lcls == lb_bk {
    return true
  }
  // LB5
  if lcls == lb_cr && rcls == lb_lf {
    return false
  }
  if lcls == lb_cr || lcls == lb_lf || lcls == lb_nl {
    return true
  }
  // LB6
  if rcls == lb_bk || rcls == lb_cr || rcls == lb_lf || rcls == lb_nl {
    return false
  }
  // LB7
  if rcls == lb_sp {
    return false
  }
  if rcls == lb_zw {
    return false
  }
  // LB8
  if lcls == lb_zw {
    return true
  }
  if lcls == lb_sp {
    let j = back_skip_sp(tokens, k - 1)
    if j >= 0 && tokens[j].cls == lb_zw {
      return true
    }
  }
  // LB8.1
  if lcls == lb_zwj {
    return false
  }
  if left.zwj {
    return false
  }
  // LB11
  if rcls == lb_wj {
    return false
  }
  if lcls == lb_wj {
    return false
  }
  // LB12 / LB12a
  if lcls == lb_gl {
    return false
  }
  if rcls == lb_gl && lcls != lb_sp && lcls != lb_ba && lcls != lb_hy &&
    lcls != lb_hh {
    return false
  }
  // LB15.3: space + infix separator before a digit overrides LB13.
  if lcls == lb_sp && rcls == lb_is && nxt == lb_nu {
    return true
  }
  // LB13
  if rcls == lb_ex || rcls == lb_cl || rcls == lb_cp || rcls == lb_sy ||
    rcls == lb_is {
    return false
  }
  // LB14
  if lcls == lb_op {
    return false
  }
  if lcls == lb_sp {
    let j = back_skip_sp(tokens, k - 1)
    if j >= 0 && tokens[j].cls == lb_op {
      return false
    }
  }
  // LB15a: do not break after an opening quote.
  if rcls != lb_sp {
    let mut j = k - 1
    while j >= 0 && tokens[j].cls == lb_sp {
      j -= 1
    }
    if j >= 0 && tokens[j].cls == lb_qu && tokens[j].pi {
      let p = j - 1
      if p < 0 || before_quote(tokens[p].cls) {
        return false
      }
    }
  }
  // LB15b: do not break before a closing quote followed by a context class.
  if rcls == lb_qu && right.pf {
    if k + 1 >= tokens.length() || after_close(nxt) {
      return false
    }
  }
  // LB16
  if rcls == lb_ns {
    let j = back_skip_sp(tokens, k - 1)
    if j >= 0 && (tokens[j].cls == lb_cl || tokens[j].cls == lb_cp) {
      return false
    }
  }
  // LB17
  if rcls == lb_b2 {
    let j = back_skip_sp(tokens, k)
    if j >= 0 && tokens[j].cls == lb_b2 {
      return false
    }
  }
  // LB18
  if lcls == lb_sp {
    return true
  }
  // LB19 + LB19a
  if rcls == lb_qu && !right.pi {
    return false
  }
  if lcls == lb_qu && !left.pf {
    return false
  }
  if rcls == lb_qu && !is_ea_char(lcls, left.cp) {
    return false
  }
  if rcls == lb_qu {
    let after = if k + 1 < tokens.length() { Some(tokens[k + 1]) } else { None }
    match after {
      Some(a) => if !is_ea_char(a.cls, a.cp) { return false }
      None => return false
    }
  }
  if lcls == lb_qu && !is_ea_char(rcls, right.cp) {
    return false
  }
  if lcls == lb_qu {
    let prev = if k - 2 >= 0 { Some(tokens[k - 2]) } else { None }
    match prev {
      Some(p) => if !is_ea_char(p.cls, p.cp) { return false }
      None => return false
    }
  }
  // LB20
  if lcls == lb_cb || rcls == lb_cb {
    return true
  }
  // LB20a
  if (lcls == lb_hy || lcls == lb_hh) && (rcls == lb_al || rcls == lb_hl) {
    if k - 2 < 0 || ctx_before(tokens[k - 2].cls) {
      return false
    }
  }
  // LB21
  if rcls == lb_ba || rcls == lb_hy || rcls == lb_ns || rcls == lb_hh {
    return false
  }
  if lcls == lb_bb {
    return false
  }
  // LB21a: HL (HY | HH) × [^HL]
  if (lcls == lb_hy || lcls == lb_hh) && rcls != lb_hl {
    let mut p = k - 2
    while p >= 0 && tokens[p].cls == lb_sp {
      p -= 1
    }
    if p >= 0 && tokens[p].cls == lb_hl {
      return false
    }
  }
  // LB21b
  if lcls == lb_sy && rcls == lb_hl {
    return false
  }
  // LB22
  if rcls == lb_in_ {
    return false
  }
  // LB23
  if (lcls == lb_al || lcls == lb_hl) && rcls == lb_nu {
    return false
  }
  if lcls == lb_nu && (rcls == lb_al || rcls == lb_hl) {
    return false
  }
  // LB23a
  if lcls == lb_pr && (rcls == lb_id || rcls == lb_eb || rcls == lb_em) {
    return false
  }
  if (lcls == lb_id || lcls == lb_eb || lcls == lb_em) && rcls == lb_po {
    return false
  }
  // LB24
  if (lcls == lb_pr || lcls == lb_po) && (rcls == lb_al || rcls == lb_hl) {
    return false
  }
  if (lcls == lb_al || lcls == lb_hl) && (rcls == lb_pr || rcls == lb_po) {
    return false
  }
  // LB25
  let ctx = num_ctx(tokens, k)
  if rcls == lb_po && (ctx == 1 || ctx == 2 || ctx == 3) {
    return false
  }
  if rcls == lb_pr && (ctx == 1 || ctx == 2 || ctx == 3) {
    return false
  }
  if (lcls == lb_po || lcls == lb_pr) && rcls == lb_op &&
    op_followed_by_nu(tokens, k) {
    return false
  }
  if (lcls == lb_po || lcls == lb_pr) && rcls == lb_op &&
    op_followed_by_is_nu(tokens, k) {
    return false
  }
  if rcls == lb_nu {
    if ctx == 1 || ctx == 2 || ctx == 3 {
      return false
    }
    if lcls == lb_pr || lcls == lb_po {
      return false
    }
    if lcls == lb_hy {
      return false
    }
    if lcls == lb_is {
      return false
    }
  }
  // LB26
  if lcls == lb_jl &&
    (rcls == lb_jl || rcls == lb_jv || rcls == lb_h2 || rcls == lb_h3) {
    return false
  }
  if (lcls == lb_jv || lcls == lb_h2) && (rcls == lb_jv || rcls == lb_jt) {
    return false
  }
  if (lcls == lb_jt || lcls == lb_h3) && rcls == lb_jt {
    return false
  }
  // LB27
  if (lcls == lb_jl || lcls == lb_jv || lcls == lb_jt || lcls == lb_h2 ||
    lcls == lb_h3) && rcls == lb_po {
    return false
  }
  if lcls == lb_pr &&
    (rcls == lb_jl || rcls == lb_jv || rcls == lb_jt || rcls == lb_h2 ||
      rcls == lb_h3) {
    return false
  }
  // LB28
  if (lcls == lb_al || lcls == lb_hl) && (rcls == lb_al || rcls == lb_hl) {
    return false
  }
  // LB28a
  if lcls == lb_ap && is_ako(rcls, right.cp) {
    return false
  }
  if is_ako(lcls, left.cp) && (rcls == lb_vf || rcls == lb_vi) {
    return false
  }
  if lcls == lb_vi && is_ako(rcls, right.cp) {
    if k - 2 >= 0 && is_ako(tokens[k - 2].cls, tokens[k - 2].cp) {
      return false
    }
  }
  if is_ako(lcls, left.cp) && is_ako(rcls, right.cp) && nxt == lb_vf {
    return false
  }
  // LB29
  if lcls == lb_is && (rcls == lb_al || rcls == lb_hl) {
    return false
  }
  // LB30
  if (lcls == lb_al || lcls == lb_hl || lcls == lb_nu) && rcls == lb_op {
    if right.cp != 0x2329 && right.cp != 0x232A && !ea_wide(right.cp) {
      return false
    }
  }
  if (rcls == lb_al || rcls == lb_hl || rcls == lb_nu) && lcls == lb_cp {
    if left.cp != 0x2329 && left.cp != 0x232A && !ea_wide(left.cp) {
      return false
    }
  }
  // LB30a
  if lcls == lb_ri && rcls == lb_ri {
    let mut count = 0
    let mut t = 0
    while t < k - 1 {
      if tokens[t].cls == lb_ri {
        count += 1
      }
      t += 1
    }
    if count % 2 == 0 {
      return false
    }
  }
  // LB30b
  if lcls == lb_eb && rcls == lb_em {
    return false
  }
  if rcls == lb_em && (left.gc == gc_cn || left.gc == gc_unassigned) &&
    is_ext_pict(left.cp) {
    return false
  }
  // LB31
  true
}

///|
/// The line-break boundaries of a code point sequence: `result[i]` is true when
/// a break opportunity falls between `cps[i]` and `cps[i + 1]`, following UAX #14.
pub fn linebreak_boundaries(cps : Array[Int]) -> Array[Bool] {
  let lb : Array[Int32] = []
  let gc : Array[Int32] = []
  for i = 0; i < cps.length(); i = i + 1 {
    lb.push(lb_lookup(cps[i]))
    gc.push(gc_lookup(cps[i]))
  }
  let (tokens, absorbed) = build_tokens(lb, cps, gc)
  let n = cps.length()
  let result : Array[Bool] = []
  let tok_of_orig : Array[Int] = []
  for k = 0; k < n; k = k + 1 {
    tok_of_orig.push(-1)
  }
  for ti = 0; ti < tokens.length(); ti = ti + 1 {
    tok_of_orig[tokens[ti].idx] = ti
  }
  for i = 1; i < n; i = i + 1 {
    if absorbed[i] {
      result.push(false)
    } else {
      let ti = tok_of_orig[i]
      if ti <= 0 {
        result.push(false)
      } else {
        result.push(break_at(tokens, ti))
      }
    }
  }
  result
}

///|
fn cps_of(s : StringView) -> Array[Int] {
  let out : Array[Int] = []
  for ch in s {
    out.push(ch.to_int())
  }
  out
}

///|
fn split_by(cps : Array[Int], bounds : Array[Bool]) -> Array[String] {
  let out : Array[String] = []
  if cps.length() == 0 {
    return out
  }
  let mut sb = StringBuilder()
  for i = 0; i < cps.length(); i = i + 1 {
    if i > 0 && bounds[i - 1] {
      out.push(sb.to_string())
      sb = StringBuilder()
    }
    sb.write_char(cps[i].unsafe_to_char())
  }
  out.push(sb.to_string())
  out
}

///|
/// The line-break opportunities of a string.
pub fn linebreaks(s : StringView) -> Array[String] {
  let cps = cps_of(s)
  split_by(cps, linebreak_boundaries(cps))
}

///|
/// The version of the Unicode Character Database the tables come from.
pub fn version() -> String {
  ucd_version
}
'''


def emit_linebreak_mbt():
    lines = ucd.header("gen_linebreak.py", VERSION)
    lines.append(emit_enums())
    lines.append(LINEBREAK_MBT.strip())
    return "\n".join(lines)


def emit_tests():
    """The conformance vectors, straight from auxiliary/LineBreakTest.txt."""
    lines = ucd.header("gen_linebreak.py", VERSION)
    text = ""
    expected = ""
    bounds = [0]
    for cps, exp in parse_test(fetch("auxiliary/LineBreakTest.txt")):
        for cp in cps:
            text += chr(cp)
        expected += "".join("1" if b else "0" for b in exp)
        bounds.append(bounds[-1] + len(cps))
    n = len(bounds) - 1
    lines.append("///|")
    lines.append(f"/// Code points of the {n} LineBreakTest cases.")
    lines.append(ucd.mbt_string_pool(
        "lb_text", text, width=60, escaper=ucd.quote_full))
    lines.append("///|")
    lines.append("/// Code point offset of each LineBreakTest case.")
    lines.append(ucd.mbt_ints("lb_bounds", bounds, per_line=12, typ="Int"))
    lines.append("///|")
    lines.append("/// Expected boundaries, one '1'/'0' per internal position.")
    lines.append(ucd.mbt_string_pool(
        "lb_expected", expected, width=60, escaper=ucd.quote_raw))
    return "\n".join(lines)


LINEBREAK_TEST_MBT = r'''
///|
/// Replay the official line break test file against the boundary function.
fn replay(
  name : String,
  text : String,
  bounds : FixedArray[Int],
  expected : String,
  boundaries : (Array[Int]) -> Array[Bool],
) -> Unit raise {
  let cps : Array[Int] = []
  for ch in text {
    cps.push(ch.to_int())
  }
  let exp : Array[Bool] = []
  for ch in expected {
    exp.push(ch == '1')
  }
  let count = bounds.length() - 1
  let mut pos = 0
  for i = 0; i < count; i = i + 1 {
    let case : Array[Int] = []
    for k = bounds[i]; k < bounds[i + 1]; k = k + 1 {
      case.push(cps[k])
    }
    let got = boundaries(case)
    for k = 0; k < case.length() - 1; k = k + 1 {
      if got[k] != exp[pos + k] {
        fail(
          "\{name} case \{i}, boundary \{k}: got \{got[k]}, want \{exp[pos + k]}",
        )
      }
    }
    pos += case.length() - 1
  }
}

///|
test "line break boundaries (LineBreakTest.txt)" {
  replay(
    "linebreak",
    lb_text,
    lb_bounds,
    lb_expected,
    @linebreak.linebreak_boundaries,
  )
}

///|
test "version" {
  assert_eq(@linebreak.version(), "17.0.0")
}

///|
test "linebreaks" {
  // LB7 keeps a space with what precedes it; LB18 breaks after it.
  assert_eq(@linebreak.linebreaks("a b"), ["a ", "b"])
  // A hyphen keeps with the letter before it (LB21).
  assert_eq(@linebreak.linebreaks("foo-bar"), ["foo-", "bar"])
  // An em dash (B2) is a break opportunity before; nothing prohibits the
  // break after it, so both sides are break opportunities.
  assert_eq(@linebreak.linebreaks("a—b"), ["a", "—", "b"])
  // An empty string has no boundaries.
  assert_eq(@linebreak.linebreaks("").length(), 0)
}

///|
test "property" {
  assert_eq(@linebreak.lb_property('a') == @linebreak.AL, true)
  assert_eq(@linebreak.lb_property('1') == @linebreak.NU, true)
}
'''


def emit_linebreak_test_mbt():
    lines = ucd.header("gen_linebreak.py", VERSION)
    lines.append(LINEBREAK_TEST_MBT.strip())
    return "\n".join(lines)


def emit_moon_pkg():
    return 'import {\n  "moonbitstack/moonucd/linebreak",\n} for "test"\n'


def generate():
    SRC.mkdir(parents=True, exist_ok=True)
    for path, body in (
        ("tables.mbt", emit_tables()),
        ("linebreak.mbt", emit_linebreak_mbt()),
        ("moon.pkg", emit_moon_pkg()),
        ("linebreak_vectors_test.mbt", emit_tests()),
        ("linebreak_test.mbt", emit_linebreak_test_mbt()),
    ):
        ucd.write(SRC / path, body.split("\n"))
    print("generated the linebreak package")


if __name__ == "__main__":
    if "--check" in sys.argv:
        sys.exit(1 if validate() else 0)
    generate()
