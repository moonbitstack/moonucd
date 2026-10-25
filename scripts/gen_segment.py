#!/usr/bin/env python3
"""Generate the `segment` sub-package (UAX #29 text segmentation): grapheme
clusters, words, and sentences. Tables come from the UCD 17.0.0 break-property
files; conformance is checked by replaying the official GraphemeBreakTest,
WordBreakTest and SentenceBreakTest files.

Run `python3 scripts/gen_segment.py --check` to validate the rule engine
against the test files before emitting anything.
"""

import pathlib
import sys

import ucd

VERSION = "17.0.0"
SRC = pathlib.Path(__file__).resolve().parent.parent / "src" / "segment"

UCD = "https://www.unicode.org/Public/{v}/ucd/{f}"
AUX = "https://www.unicode.org/Public/{v}/ucd/auxiliary/{f}"
EMOJI = "https://www.unicode.org/Public/{v}/ucd/emoji/{f}"


def fetch(name, where=UCD):
    return ucd.fetch(VERSION, name)


def load_property_file(text, default):
    values = {}
    for line in text.splitlines():
        line = line.split("#", 1)[0].strip()
        if not line or ";" not in line:
            continue
        field, value = line.split(";", 1)
        field = field.strip()
        value = value.strip()
        if ".." in field:
            a, b = field.split("..")
            for cp in range(int(a, 16), int(b, 16) + 1):
                values[cp] = value
        else:
            values[int(field, 16)] = value
    return values


# ---------------------------------------------------------------------------
# Property loading
# ---------------------------------------------------------------------------

def load():
    gcb_raw = load_property_file(fetch("auxiliary/GraphemeBreakProperty.txt", AUX), "Other")
    wb_raw = load_property_file(fetch("auxiliary/WordBreakProperty.txt", AUX), "Other")
    sb_raw = load_property_file(fetch("auxiliary/SentenceBreakProperty.txt", AUX), "Other")

    emoji = fetch("emoji/emoji-data.txt", EMOJI)
    ep = set()
    for line in emoji.splitlines():
        line = line.split("#", 1)[0].strip()
        if not line or ";" not in line:
            continue
        field, value = line.split(";", 1)
        value = value.strip()
        if ".." in field:
            a, b = field.split("..")
            cps = range(int(a.strip(), 16), int(b.strip(), 16) + 1)
        else:
            cps = [int(field.strip(), 16)]
        if value == "Extended_Pictographic":
            for cp in cps:
                ep.add(cp)

    incb_raw = {}
    for line in fetch("DerivedCoreProperties.txt").splitlines():
        line = line.split("#", 1)[0].strip()
        if "; InCB;" not in line:
            continue
        field, rest = line.split(";", 1)
        value = rest.split(";")[1].strip()
        field = field.strip()
        if ".." in field:
            a, b = field.split("..")
            for cp in range(int(a, 16), int(b, 16) + 1):
                incb_raw[cp] = value
        else:
            incb_raw[int(field, 16)] = value

    return gcb_raw, wb_raw, sb_raw, ep, incb_raw


# ---------------------------------------------------------------------------
# Shared value names
# ---------------------------------------------------------------------------

CR = "CR"
LF = "LF"
CONTROL = "Control"
L = "L"
V = "V"
T = "T"
LV = "LV"
LVT = "LVT"
EXTEND = "Extend"
ZWJ = "ZWJ"
SPACINGMARK = "SpacingMark"
PREPEND = "Prepend"
RI = "Regional_Indicator"
OTHER = "Other"
E_BASE = "E_Base"
E_BASE_GAZ = "E_Base_GAZ"
E_MOD = "E_Modifier"
EP = "Extended_Pictographic"

NEWLINE = "Newline"
FORMAT = "Format"
KATAKANA = "Katakana"
ALETTER = "ALetter"
HEBREW = "Hebrew_Letter"
NUMERIC = "Numeric"
MIDNUMLET = "MidNumLet"
MIDLETTER = "MidLetter"
MIDNUM = "MidNum"
EXTENDNUMLET = "ExtendNumLet"
WSEGSPACE = "WSegSpace"
DOUBLE_QUOTE = "Double_Quote"
SINGLE_QUOTE = "Single_Quote"

SEP = "Sep"
SP = "Sp"
LOWER = "Lower"
UPPER = "Upper"
OLETTER = "OLetter"
ATERM = "ATerm"
SCONTINUE = "SContinue"
STERM = "STerm"
CLOSE = "Close"
SATERM = "SATerm"


# ---------------------------------------------------------------------------
# Grapheme cluster break
# ---------------------------------------------------------------------------

def gb9c(incb, cps, g):
    # GB9c (UAX #29, Unicode 17.0.0):
    #   InCB=Consonant [InCB=Extend InCB=Linker]* InCB=Linker
    #   [InCB=Extend InCB=Linker]* × InCB=Consonant
    if incb.get(cps[g + 1], "None") != "Consonant":
        return None
    j = g
    seen_linker = False
    while j >= 0:
        p = incb.get(cps[j], "None")
        if p == "Linker":
            seen_linker = True
            j -= 1
            continue
        if p == "Extend":
            j -= 1
            continue
        break
    if j >= 0 and incb.get(cps[j], "None") == "Consonant" and seen_linker:
        return False
    return None


def ri_pair(prop_dict, cps, g, ri_val, transparent):
    # GB12/13 and WB15/16: do not break between two Regional_Indicators when an
    # odd number of RI precede the break point. Extend/Format/ZWJ are transparent
    # to the run (GB9 / WB4 already make the gaps they sit in non-breaks).
    def eff_at(i):
        p = prop_dict.get(cps[i], OTHER)
        j = i
        while p in transparent and j > 0:
            j -= 1
            p = prop_dict.get(cps[j], OTHER)
        return p

    el = eff_at(g)
    er = eff_at(g + 1)
    if el != ri_val or er != ri_val:
        return None
    count = 0
    k = g
    while k >= 0:
        p = prop_dict.get(cps[k], OTHER)
        if p == ri_val:
            count += 1
            k -= 1
        elif p in transparent:
            k -= 1
        else:
            break
    if count % 2 == 1:
        return False
    return None


def gb11_left(gcb, ep, cps, g):
    if g < 1:
        return False
    if gcb.get(cps[g], OTHER) != ZWJ:
        return False
    j = g - 1
    while j >= 0 and gcb.get(cps[j], OTHER) == EXTEND:
        j -= 1
    return j >= 0 and cps[j] in ep


def gcb_break(gcb, incb, ep, cps, g):
    left = cps[g]
    right = cps[g + 1]
    pl = gcb.get(left, OTHER)
    pr = gcb.get(right, OTHER)

    if pl == CR and pr == LF:
        return False
    if pl in (CONTROL, CR, LF):
        return True
    if pr in (CONTROL, CR, LF):
        return True
    if pl == L and pr in (L, V, LV, LVT):
        return False
    if pl in (LV, V) and pr in (V, T):
        return False
    if pl in (LVT, T) and pr == T:
        return False
    if pr in (EXTEND, ZWJ):
        return False
    if pr == SPACINGMARK:
        return False
    if pl == PREPEND:
        return False
    r = gb9c(incb, cps, g)
    if r is not None:
        return r
    if right in ep and gb11_left(gcb, ep, cps, g):
        return False
    r = ri_pair(gcb, cps, g, RI, ())
    if r is not None:
        return r
    return True


# ---------------------------------------------------------------------------
# Word break
# ---------------------------------------------------------------------------

def wb_break(wb, ep, cps, g):
    # Word boundaries (UAX #29). Extend/Format/ZWJ are ignored (WB4): the break
    # before such a character is always a non-break, and they are removed from the
    # sequence the remaining rules operate on.
    left = cps[g]
    right = cps[g + 1]
    pl = wb.get(left, OTHER)
    pr = wb.get(right, OTHER)
    # WB3
    if pl == CR and pr == LF:
        return False
    # WB3a
    if pl in (NEWLINE, CR, LF):
        return True
    # WB3b
    if pr in (NEWLINE, CR, LF):
        return True
    # WB3c
    if pl == ZWJ and right in ep:
        return False
    # WB3d
    if pl == WSEGSPACE and pr == WSEGSPACE:
        return False
    # WB4
    if pr in (EXTEND, FORMAT, ZWJ):
        return False

    seq = []  # (original_index, word_break_property)
    for i, c in enumerate(cps):
        p = wb.get(c, OTHER)
        if p in (EXTEND, FORMAT, ZWJ):
            continue
        seq.append((i, p))

    j = None
    for k in range(len(seq)):
        if seq[k][0] == g + 1:
            j = k
            break
    if j is None or j == 0:
        return True

    pl = seq[j - 1][1]
    pr = seq[j][1]
    right_cp = cps[seq[j][0]]
    re_ = right_cp in ep
    ah = (ALETTER, HEBREW)
    midq = (MIDLETTER, MIDNUMLET, SINGLE_QUOTE)
    midn = (MIDNUM, MIDNUMLET, SINGLE_QUOTE)
    group = (ALETTER, HEBREW, NUMERIC, KATAKANA, EXTENDNUMLET)

    def at(k):
        return seq[k][1] if 0 <= k < len(seq) else OTHER

    # WB3
    if pl == CR and pr == LF:
        return False
    # WB3a
    if pl in (NEWLINE, CR, LF):
        return True
    # WB3b
    if pr in (NEWLINE, CR, LF):
        return True
    # WB3c
    if pl == ZWJ and re_:
        return False
    # WB5
    if pl in ah and pr in ah:
        return False
    # WB6
    if pl in ah and pr in midq and j + 1 < len(seq) and at(j + 1) in ah:
        return False
    # WB7
    if pl in midq and pr in ah and j - 2 >= 0 and at(j - 2) in ah:
        return False
    # WB7a
    if pl == HEBREW and pr == SINGLE_QUOTE:
        return False
    # WB7b
    if pl == HEBREW and pr == DOUBLE_QUOTE and j + 1 < len(seq) and at(j + 1) == HEBREW:
        return False
    # WB7c
    if pl == DOUBLE_QUOTE and pr == HEBREW and j - 2 >= 0 and at(j - 2) == HEBREW:
        return False
    # WB8
    if pl == NUMERIC and pr == NUMERIC:
        return False
    # WB9
    if pl in ah and pr == NUMERIC:
        return False
    # WB10
    if pl == NUMERIC and pr in ah:
        return False
    # WB11: Numeric (MidNum | MidNumLetQ) × Numeric
    if pl in midn and pr == NUMERIC and j - 2 >= 0 and at(j - 2) == NUMERIC:
        return False
    # WB12: Numeric × (MidNum | MidNumLetQ) Numeric
    if pl == NUMERIC and pr in midn and j + 1 < len(seq) and at(j + 1) == NUMERIC:
        return False
    # WB13
    if pl == KATAKANA and pr == KATAKANA:
        return False
    # WB13a
    if pl in group and pr == EXTENDNUMLET:
        return False
    # WB13b
    if pl == EXTENDNUMLET and pr in (ALETTER, HEBREW, NUMERIC, KATAKANA):
        return False
    # WB15 / WB16: Regional_Indicator pairing.
    if pl == RI and pr == RI:
        count = 0
        k = j - 1
        while k >= 0 and at(k) == RI:
            count += 1
            k -= 1
        if count % 2 == 1:
            return False
    return True


# ---------------------------------------------------------------------------
# Sentence break (SB rules; see UAX #29)
# ---------------------------------------------------------------------------

def sb_break(sb, cps, g):
    left = cps[g]
    right = cps[g + 1]
    pl = sb.get(left, OTHER)
    pr = sb.get(right, OTHER)
    parasep = (SEP, CR, LF)

    # SB3
    if pl == CR and pr == LF:
        return False
    # SB4
    if pl in parasep:
        return True
    # SB5: Extend/Format are ignored (handled by the reduced sequence below).
    if pr in (EXTEND, FORMAT):
        return False

    # Build the reduced sequence: drop Extend/Format, which SB5 ignores.
    seq = []  # (original_index, sentence_break_property)
    for i, c in enumerate(cps):
        p = sb.get(c, OTHER)
        if p in (EXTEND, FORMAT):
            continue
        seq.append((i, p))

    j = None
    for k in range(len(seq)):
        if seq[k][0] == g + 1:
            j = k
            break
    if j is None or j == 0:
        return False

    pl = seq[j - 1][1]
    pr = seq[j][1]
    saterm = (STERM, ATERM)
    close_sp = (CLOSE, SP, SEP, CR, LF)

    # SB6
    if pl == ATERM and pr == NUMERIC:
        return False
    # SB7: (Upper | Lower) ATerm × Upper
    if pl == ATERM and pr == UPPER and j - 2 >= 0 and seq[j - 2][1] in (UPPER, LOWER):
        return False
    # Left-run helpers. The pattern before the boundary is written left to right
    # as "SATerm Close* Sp*", so scanning right to left we skip Sp* first and
    # then Close*. The scan never steps over a paragraph separator: after a
    # ParaSep a new sentence begins, so a terminator from the previous sentence
    # must not be visible (SB4 has already produced the break there).
    def run_close(j):
        k = j - 1
        while k >= 0 and seq[k][1] == CLOSE:
            k -= 1
        return k >= 0 and seq[k][1] in saterm

    def run_close_sp(j):
        k = j - 1
        while k >= 0 and seq[k][1] == SP:
            k -= 1
        while k >= 0 and seq[k][1] == CLOSE:
            k -= 1
        return k >= 0 and seq[k][1] in saterm

    if run_close_sp(j):
        k = j - 1
        while k >= 0 and seq[k][1] == SP:
            k -= 1
        while k >= 0 and seq[k][1] == CLOSE:
            k -= 1
        term_prop = seq[k][1]
        # SB8: ATerm Close* Sp* × (¬(OLetter|Upper|Lower|ParaSep|SATerm))* Lower
        if term_prop == ATERM:
            m = j
            while m < len(seq) and seq[m][1] not in (
                OLETTER, UPPER, LOWER, SEP, CR, LF, STERM, ATERM
            ):
                m += 1
            if m < len(seq) and seq[m][1] == LOWER:
                return False
        # SB8a: SATerm Close* Sp* × (SContinue | SATerm)
        if pr in (SCONTINUE, STERM, ATERM):
            return False
        # SB9: SATerm Close* × (Close | Sp | ParaSep)
        if run_close(j) and pr in (CLOSE, SP, SEP, CR, LF):
            return False
        # SB10: SATerm Close* Sp* × (Sp | ParaSep)
        if pr in (SP, SEP, CR, LF):
            return False
        # SB11: SATerm Close* Sp* ParaSep? ÷  (break after the terminator run)
        return True
    # SB998: otherwise do not break
    return False


# ---------------------------------------------------------------------------
# Test-file parsing and validation
# ---------------------------------------------------------------------------

def parse_test(text):
    out = []
    for line in text.splitlines():
        line = line.split("#", 1)[0].strip()
        if not line or "÷" not in line:
            continue
        codepoints = []
        marks = []
        toks = line.split()
        i = 1  # toks[0] is the leading '÷' (sot)
        while i < len(toks):
            codepoints.append(int(toks[i], 16))
            i += 1
            if i < len(toks):
                marks.append(toks[i] == "÷")
                i += 1
        # `marks` has one entry per code point: n-1 internal boundaries plus the
        # final (always-true) end-of-text boundary. Drop that last one.
        expected = marks[:-1]
        out.append((codepoints, expected))
    return out


def check_algorithm(name, file, fn):
    text = fetch(file, AUX)
    total = 0
    errors = 0
    for cps, expected in parse_test(text):
        got = [fn(cps, g) for g in range(len(cps) - 1)]
        total += 1
        if got != expected:
            errors += 1
            if errors <= 15:
                exp_s = " ".join("÷" if b else "×" for b in expected)
                got_s = " ".join("÷" if b else "×" for b in got)
                print(f"  {name} #{total}: exp[{exp_s}] got[{got_s}] :: " + " ".join(f"{c:04X}" for c in cps))
    print(f"  {name}: {total} lines, {errors} errors")
    return errors


def validate():
    gcb, wb, sb, ep, incb = load()
    print("validating grapheme cluster breaks...")
    e1 = check_algorithm("grapheme", "auxiliary/GraphemeBreakTest.txt",
                         lambda cps, g: gcb_break(gcb, incb, ep, cps, g))
    print("validating word breaks...")
    e2 = check_algorithm("word", "auxiliary/WordBreakTest.txt",
                         lambda cps, g: wb_break(wb, ep, cps, g))
    print("validating sentence breaks...")
    e3 = check_algorithm("sentence", "auxiliary/SentenceBreakTest.txt",
                         lambda cps, g: sb_break(sb, cps, g))
    return e1 + e2 + e3


# ---------------------------------------------------------------------------
# Property value orderings (the stored Int32 codes follow these lists)
# ---------------------------------------------------------------------------

GCB_VALUES = [
    "Other", "CR", "LF", "Control", "Extend", "ZWJ", "Regional_Indicator",
    "Prepend", "SpacingMark", "L", "V", "T", "LV", "LVT",
]
WB_VALUES = [
    "Other", "CR", "LF", "Newline", "Extend", "ZWJ", "Format",
    "Regional_Indicator", "Katakana", "ALetter", "Hebrew_Letter", "MidLetter",
    "MidNumLet", "MidNum", "Numeric", "ExtendNumLet", "WSegSpace",
    "Double_Quote", "Single_Quote",
]
SB_VALUES = [
    "Other", "CR", "LF", "Sep", "Extend", "Format", "Sp", "Lower", "Upper",
    "OLetter", "Numeric", "ATerm", "STerm", "SContinue", "Close",
]
INCB_VALUES = ["None", "Consonant", "Extend", "Linker"]


def codes(values):
    return {v: i for i, v in enumerate(values)}


# ---------------------------------------------------------------------------
# The `segment` package sources
# ---------------------------------------------------------------------------

SEGMENT_MBT = r'''
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
    if starts[mid] <= cp {
      a = mid + 1
    } else {
      b = mid
    }
  }
  if a > 0 {
    let i = a - 1
    if ends[i] >= cp {
      return Some(i)
    }
  }
  None
}

///|
/// Look up the stored Grapheme_Cluster_Break code of a code point.
fn gcb_lookup(cp : Int) -> Int32 {
  match find_run(gcb_starts, gcb_ends, cp) {
    Some(i) => gcb_values[i]
    None => 0
  }
}

///|
fn wb_lookup(cp : Int) -> Int32 {
  match find_run(wb_starts, wb_ends, cp) {
    Some(i) => wb_values[i]
    None => 0
  }
}

///|
fn sb_lookup(cp : Int) -> Int32 {
  match find_run(sb_starts, sb_ends, cp) {
    Some(i) => sb_values[i]
    None => 0
  }
}

///|
fn incb_lookup(cp : Int) -> Int32 {
  match find_run(incb_starts, incb_ends, cp) {
    Some(i) => incb_values[i]
    None => 0
  }
}

///|
fn is_ext_pict(cp : Int) -> Bool {
  match find_run(ep_starts, ep_ends, cp) {
    Some(_) => true
    None => false
  }
}

// GB9c: InCB=Consonant [InCB=Extend InCB=Linker]* InCB=Linker
// [InCB=Extend InCB=Linker]* x InCB=Consonant
///|
fn gcb_gb9c(iv : Array[Int32], g : Int) -> Bool? {
  if iv[g + 1] != incb_consonant {
    None
  } else {
    let mut j = g
    let mut seen_linker = false
    let mut scanning = true
    while scanning && j >= 0 {
      let p = iv[j]
      if p == incb_linker {
        seen_linker = true
        j -= 1
      } else if p == incb_extend {
        j -= 1
      } else {
        scanning = false
      }
    }
    if j >= 0 && iv[j] == incb_consonant && seen_linker {
      Some(false)
    } else {
      None
    }
  }
}

// GB11: Extended_Pictographic Extend* ZWJ x Extended_Pictographic
///|
fn gcb_gb11_left(pv : Array[Int32], ev : Array[Bool], g : Int) -> Bool {
  if g < 1 || pv[g] != gcb_zwj {
    false
  } else {
    let mut j = g - 1
    while j >= 0 && pv[j] == gcb_extend {
      j -= 1
    }
    j >= 0 && ev[j]
  }
}

// GB12/GB13: keep Regional_Indicator pairs together.
///|
fn gcb_ri_pair(pv : Array[Int32], g : Int) -> Bool? {
  if pv[g] != gcb_ri || pv[g + 1] != gcb_ri {
    None
  } else {
    let mut count = 0
    let mut k = g
    while k >= 0 && pv[k] == gcb_ri {
      count += 1
      k -= 1
    }
    if count % 2 == 1 {
      Some(false)
    } else {
      None
    }
  }
}

///|
fn gcb_break(
  pv : Array[Int32],
  iv : Array[Int32],
  ev : Array[Bool],
  g : Int,
) -> Bool {
  let pl = pv[g]
  let pr = pv[g + 1]
  // GB3
  if pl == gcb_cr && pr == gcb_lf {
    return false
  }
  // GB4
  if pl == gcb_control || pl == gcb_cr || pl == gcb_lf {
    return true
  }
  // GB5
  if pr == gcb_control || pr == gcb_cr || pr == gcb_lf {
    return true
  }
  // GB6
  if pl == gcb_l && (pr == gcb_l || pr == gcb_v || pr == gcb_lv || pr == gcb_lvt) {
    return false
  }
  // GB7
  if (pl == gcb_lv || pl == gcb_v) && (pr == gcb_v || pr == gcb_t) {
    return false
  }
  // GB8
  if (pl == gcb_lvt || pl == gcb_t) && pr == gcb_t {
    return false
  }
  // GB9
  if pr == gcb_extend || pr == gcb_zwj {
    return false
  }
  // GB9a
  if pr == gcb_spacingmark {
    return false
  }
  // GB9b
  if pl == gcb_prepend {
    return false
  }
  // GB9c
  match gcb_gb9c(iv, g) {
    Some(v) => return v
    None => ()
  }
  // GB11
  if ev[g + 1] && gcb_gb11_left(pv, ev, g) {
    return false
  }
  // GB12 / GB13
  match gcb_ri_pair(pv, g) {
    Some(v) => return v
    None => ()
  }
  true
}

///|
fn wb_is_ah(p : Int32) -> Bool {
  p == wb_aletter || p == wb_hebrew
}

///|
fn wb_is_midq(p : Int32) -> Bool {
  p == wb_midletter || p == wb_midnumlet || p == wb_single_quote
}

///|
fn wb_is_midn(p : Int32) -> Bool {
  p == wb_midnum || p == wb_midnumlet || p == wb_single_quote
}

///|
fn wb_is_group(p : Int32) -> Bool {
  p == wb_aletter || p == wb_hebrew || p == wb_numeric || p == wb_katakana ||
  p == wb_extendnumlet
}

///|
fn wb_is_letterish(p : Int32) -> Bool {
  p == wb_aletter || p == wb_hebrew || p == wb_numeric || p == wb_katakana
}

///|
fn wb_at(seq_prop : Array[Int32], k : Int) -> Int32 {
  if k >= 0 && k < seq_prop.length() {
    seq_prop[k]
  } else {
    0
  }
}

// Extend/Format/ZWJ are ignored (WB4), so the rules run over the sequence with
// those characters dropped. Boundary `g` maps to the gap before the first
// surviving character at or after `g + 1`.
///|
fn wb_break(
  pv : Array[Int32],
  ev : Array[Bool],
  cps : Array[Int],
  g : Int,
) -> Bool {
  let pl = pv[g]
  let pr = pv[g + 1]
  // WB3
  if pl == wb_cr && pr == wb_lf {
    return false
  }
  // WB3a
  if pl == wb_newline || pl == wb_cr || pl == wb_lf {
    return true
  }
  // WB3b
  if pr == wb_newline || pr == wb_cr || pr == wb_lf {
    return true
  }
  // WB3c
  if pl == wb_zwj && ev[g + 1] {
    return false
  }
  // WB3d
  if pl == wb_wsegspace && pr == wb_wsegspace {
    return false
  }
  // WB4
  if pr == wb_extend || pr == wb_format || pr == wb_zwj {
    return false
  }
  let seq_idx : Array[Int] = []
  let seq_prop : Array[Int32] = []
  for i = 0; i < cps.length(); i = i + 1 {
    let p = pv[i]
    if p != wb_extend && p != wb_format && p != wb_zwj {
      seq_idx.push(i)
      seq_prop.push(p)
    }
  }
  let mut j = -1
  for k = 0; k < seq_idx.length(); k = k + 1 {
    if j < 0 && seq_idx[k] == g + 1 {
      j = k
    }
  }
  if j <= 0 {
    return true
  }
  let el = seq_prop[j - 1]
  let er = seq_prop[j]
  // WB5
  if wb_is_ah(el) && wb_is_ah(er) {
    return false
  }
  // WB6
  if wb_is_ah(el) && wb_is_midq(er) && wb_is_ah(wb_at(seq_prop, j + 1)) {
    return false
  }
  // WB7
  if wb_is_midq(el) && wb_is_ah(er) && j >= 2 && wb_is_ah(seq_prop[j - 2]) {
    return false
  }
  // WB7a
  if el == wb_hebrew && er == wb_single_quote {
    return false
  }
  // WB7b
  if el == wb_hebrew && er == wb_double_quote &&
    wb_at(seq_prop, j + 1) == wb_hebrew {
    return false
  }
  // WB7c
  if el == wb_double_quote && er == wb_hebrew && j >= 2 &&
    seq_prop[j - 2] == wb_hebrew {
    return false
  }
  // WB8
  if el == wb_numeric && er == wb_numeric {
    return false
  }
  // WB9
  if wb_is_ah(el) && er == wb_numeric {
    return false
  }
  // WB10
  if el == wb_numeric && wb_is_ah(er) {
    return false
  }
  // WB11: Numeric (MidNum | MidNumLetQ) x Numeric
  if wb_is_midn(el) && er == wb_numeric && j >= 2 &&
    seq_prop[j - 2] == wb_numeric {
    return false
  }
  // WB12: Numeric x (MidNum | MidNumLetQ) Numeric
  if el == wb_numeric && wb_is_midn(er) && wb_at(seq_prop, j + 1) == wb_numeric {
    return false
  }
  // WB13
  if el == wb_katakana && er == wb_katakana {
    return false
  }
  // WB13a
  if wb_is_group(el) && er == wb_extendnumlet {
    return false
  }
  // WB13b
  if el == wb_extendnumlet && wb_is_letterish(er) {
    return false
  }
  // WB15 / WB16
  if el == wb_ri && er == wb_ri {
    let mut count = 0
    let mut k = j - 1
    while k >= 0 && seq_prop[k] == wb_ri {
      count += 1
      k -= 1
    }
    if count % 2 == 1 {
      return false
    }
  }
  true
}

// Index of the SATerm of the run "SATerm Close* Sp*" ending at the boundary,
// or -1 when the left side is not such a run. The scan never steps over a
// paragraph separator, so a terminator from a previous sentence stays hidden.
///|
fn sb_term_index(seq_prop : Array[Int32], j : Int) -> Int {
  let mut k = j - 1
  while k >= 0 && seq_prop[k] == sb_sp {
    k -= 1
  }
  while k >= 0 && seq_prop[k] == sb_close {
    k -= 1
  }
  if k >= 0 && (seq_prop[k] == sb_sterm || seq_prop[k] == sb_aterm) {
    k
  } else {
    -1
  }
}

///|
fn sb_term_index_close(seq_prop : Array[Int32], j : Int) -> Int {
  let mut k = j - 1
  while k >= 0 && seq_prop[k] == sb_close {
    k -= 1
  }
  if k >= 0 && (seq_prop[k] == sb_sterm || seq_prop[k] == sb_aterm) {
    k
  } else {
    -1
  }
}

///|
fn sb_break(pv : Array[Int32], cps : Array[Int], g : Int) -> Bool {
  let pl = pv[g]
  let pr = pv[g + 1]
  // SB3
  if pl == sb_cr && pr == sb_lf {
    return false
  }
  // SB4
  if pl == sb_sep || pl == sb_cr || pl == sb_lf {
    return true
  }
  // SB5
  if pr == sb_extend || pr == sb_format {
    return false
  }
  let seq_idx : Array[Int] = []
  let seq_prop : Array[Int32] = []
  for i = 0; i < cps.length(); i = i + 1 {
    let p = pv[i]
    if p != sb_extend && p != sb_format {
      seq_idx.push(i)
      seq_prop.push(p)
    }
  }
  let mut j = -1
  for k = 0; k < seq_idx.length(); k = k + 1 {
    if j < 0 && seq_idx[k] == g + 1 {
      j = k
    }
  }
  if j <= 0 {
    return false
  }
  let el = seq_prop[j - 1]
  let er = seq_prop[j]
  // SB6
  if el == sb_aterm && er == sb_numeric {
    return false
  }
  // SB7
  if el == sb_aterm && er == sb_upper && j >= 2 &&
    (seq_prop[j - 2] == sb_upper || seq_prop[j - 2] == sb_lower) {
    return false
  }
  let ti = sb_term_index(seq_prop, j)
  if ti >= 0 {
    let term_prop = seq_prop[ti]
    // SB8
    if term_prop == sb_aterm {
      let mut m = j
      let mut scanning = true
      while scanning && m < seq_prop.length() {
        let p = seq_prop[m]
        if p == sb_oletter || p == sb_upper || p == sb_lower || p == sb_sep ||
          p == sb_cr || p == sb_lf || p == sb_sterm || p == sb_aterm {
          scanning = false
        } else {
          m += 1
        }
      }
      if m < seq_prop.length() && seq_prop[m] == sb_lower {
        return false
      }
    }
    // SB8a
    if er == sb_scontinue || er == sb_sterm || er == sb_aterm {
      return false
    }
    // SB9
    if sb_term_index_close(seq_prop, j) >= 0 &&
      (er == sb_close || er == sb_sp || er == sb_sep || er == sb_cr ||
        er == sb_lf) {
      return false
    }
    // SB10
    if er == sb_sp || er == sb_sep || er == sb_cr || er == sb_lf {
      return false
    }
    // SB11
    return true
  }
  false
}

///|
/// The code points of a string.
fn cps_of(s : StringView) -> Array[Int] {
  let out : Array[Int] = []
  for ch in s {
    out.push(ch.to_int())
  }
  out
}

///|
/// Cut a code point sequence at the flagged boundaries.
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
/// Grapheme cluster boundaries: `result[i]` is true when a boundary falls
/// between `cps[i]` and `cps[i + 1]`, following UAX #29.
pub fn grapheme_boundaries(cps : Array[Int]) -> Array[Bool] {
  let pv : Array[Int32] = []
  let iv : Array[Int32] = []
  let ev : Array[Bool] = []
  for i = 0; i < cps.length(); i = i + 1 {
    pv.push(gcb_lookup(cps[i]))
    iv.push(incb_lookup(cps[i]))
    ev.push(is_ext_pict(cps[i]))
  }
  let out : Array[Bool] = []
  for g = 0; g + 1 < cps.length(); g = g + 1 {
    out.push(gcb_break(pv, iv, ev, g))
  }
  out
}

///|
/// Word boundaries, following UAX #29.
pub fn word_boundaries(cps : Array[Int]) -> Array[Bool] {
  let pv : Array[Int32] = []
  let ev : Array[Bool] = []
  for i = 0; i < cps.length(); i = i + 1 {
    pv.push(wb_lookup(cps[i]))
    ev.push(is_ext_pict(cps[i]))
  }
  let out : Array[Bool] = []
  for g = 0; g + 1 < cps.length(); g = g + 1 {
    out.push(wb_break(pv, ev, cps, g))
  }
  out
}

///|
/// Sentence boundaries, following UAX #29.
pub fn sentence_boundaries(cps : Array[Int]) -> Array[Bool] {
  let pv : Array[Int32] = []
  for i = 0; i < cps.length(); i = i + 1 {
    pv.push(sb_lookup(cps[i]))
  }
  let out : Array[Bool] = []
  for g = 0; g + 1 < cps.length(); g = g + 1 {
    out.push(sb_break(pv, cps, g))
  }
  out
}

///|
/// The extended grapheme clusters of a string.
pub fn grapheme_clusters(s : StringView) -> Array[String] {
  let cps = cps_of(s)
  split_by(cps, grapheme_boundaries(cps))
}

///|
/// The words of a string.
pub fn words(s : StringView) -> Array[String] {
  let cps = cps_of(s)
  split_by(cps, word_boundaries(cps))
}

///|
/// The sentences of a string.
pub fn sentences(s : StringView) -> Array[String] {
  let cps = cps_of(s)
  split_by(cps, sentence_boundaries(cps))
}
'''


# Canonical value -> the short internal alias the rule code refers to.
GCB_ALIAS = {
    "Other": "gcb_other", "CR": "gcb_cr", "LF": "gcb_lf", "Control": "gcb_control",
    "Extend": "gcb_extend", "ZWJ": "gcb_zwj", "Regional_Indicator": "gcb_ri",
    "Prepend": "gcb_prepend", "SpacingMark": "gcb_spacingmark", "L": "gcb_l",
    "V": "gcb_v", "T": "gcb_t", "LV": "gcb_lv", "LVT": "gcb_lvt",
}
WB_ALIAS = {
    "Other": "wb_other", "CR": "wb_cr", "LF": "wb_lf", "Newline": "wb_newline",
    "Extend": "wb_extend", "ZWJ": "wb_zwj", "Format": "wb_format",
    "Regional_Indicator": "wb_ri", "Katakana": "wb_katakana",
    "ALetter": "wb_aletter", "Hebrew_Letter": "wb_hebrew",
    "MidLetter": "wb_midletter", "MidNumLet": "wb_midnumlet",
    "MidNum": "wb_midnum", "Numeric": "wb_numeric",
    "ExtendNumLet": "wb_extendnumlet", "WSegSpace": "wb_wsegspace",
    "Double_Quote": "wb_double_quote", "Single_Quote": "wb_single_quote",
}
SB_ALIAS = {
    "Other": "sb_other", "CR": "sb_cr", "LF": "sb_lf", "Sep": "sb_sep",
    "Extend": "sb_extend", "Format": "sb_format", "Sp": "sb_sp",
    "Lower": "sb_lower", "Upper": "sb_upper", "OLetter": "sb_oletter",
    "Numeric": "sb_numeric", "ATerm": "sb_aterm", "STerm": "sb_sterm",
    "SContinue": "sb_scontinue", "Close": "sb_close",
}
INCB_ALIAS = {
    "None": "incb_none", "Consonant": "incb_consonant", "Extend": "incb_extend",
    "Linker": "incb_linker",
}


def emit_enums():
    """The public property-value enums plus the internal Int32 code aliases."""
    out = []
    for kind, values, alias, name, label in (
        ("gcb", GCB_VALUES, GCB_ALIAS, "Gcb", "Grapheme_Cluster_Break"),
        ("wb", WB_VALUES, WB_ALIAS, "Wb", "Word_Break"),
        ("sb", SB_VALUES, SB_ALIAS, "Sb", "Sentence_Break"),
    ):
        out.append(f"///|\n/// A {label} property value.")
        out.append(f"pub(all) enum {name} {{")
        for v in values:
            out.append(f"  {v}")
        out.append("} derive(Eq)")
        out.append("///|")
        out.append(f"pub extend {name} with Eq::{{equal, not_equal}}")
        out.append("///|")
        out.append(f"/// The {name} value of a stored {label} code.")
        out.append(f"pub fn {kind}_of_code(code : Int32) -> {name} {{")
        out.append("  match code {")
        for i, v in enumerate(values):
            out.append(f"    {i} => {v}")
        out.append(f"    _ => {values[0]}")
        out.append("  }")
        out.append("}")
        out.append("///|")
        out.append(f"/// The {label} property value of a character.")
        out.append(f"pub fn {kind}_property(ch : Char) -> {name} {{")
        out.append(f"  {kind}_of_code({kind}_lookup(ch.to_int()))")
        out.append("}")
        out.append("///|")
        out.append(f"// {label} codes, matching {kind}_values.")
        for i, v in enumerate(values):
            if v != "Other":
                out.append(f"let {alias[v]} : Int32 = {i}")
    out.append("///|")
    out.append("// Indic_Conjunct_Break codes, matching incb_values.")
    for i, v in enumerate(INCB_VALUES):
        if v != "None":
            out.append(f"let {INCB_ALIAS[v]} : Int32 = {i}")
    return "\n".join(out)


def emit_tables(gcb, wb, sb, ep, incb):
    """tables.mbt: the property runs the rules look up."""
    lines = ucd.header("gen_segment.py", VERSION)
    lines.append("///|")
    lines.append('let ucd_version : String = "17.0.0"')

    def emit_prop(key, prop, values, label):
        order = codes(values)
        lookup = {cp: order.get(v, 0) for cp, v in prop.items()}
        rs = ucd.runs(lookup, 0)
        lines.append("///|")
        lines.append(f"/// {label} runs over the code space: code point ranges with a "
                     "property other than the default.")
        lines.append(ucd.mbt_ints(f"{key}_starts", [r[0] for r in rs], per_line=12))
        lines.append("///|")
        lines.append(ucd.mbt_ints(f"{key}_ends", [r[1] for r in rs], per_line=12))
        lines.append("///|")
        lines.append(ucd.mbt_ints(f"{key}_values", [r[2] for r in rs], per_line=12))

    emit_prop("gcb", gcb, GCB_VALUES, "Grapheme_Cluster_Break")
    emit_prop("wb", wb, WB_VALUES, "Word_Break")
    emit_prop("sb", sb, SB_VALUES, "Sentence_Break")
    emit_prop("incb", incb, INCB_VALUES, "Indic_Conjunct_Break")

    # Extended_Pictographic is a plain set, so only starts and ends.
    rs = ucd.merge([(cp, cp) for cp in sorted(ep)])
    lines.append("///|")
    lines.append("/// Extended_Pictographic ranges (GB11).")
    lines.append(ucd.mbt_ints("ep_starts", [r[0] for r in rs], per_line=12))
    lines.append("///|")
    lines.append(ucd.mbt_ints("ep_ends", [r[1] for r in rs], per_line=12))
    return "\n".join(lines)


def emit_tests(cases_by_name):
    """The conformance test vectors, taken straight from the UCD test files.

    Every case is stored as a run of code points inside one pool string plus a
    parallel string of '0'/'1' expected-boundary flags, so the test replays the
    official files without needing to slice strings containing supplementary
    characters (which this compiler handles incorrectly)."""
    lines = ucd.header("gen_segment.py", VERSION)
    for name, cases in cases_by_name:
        text = ""
        expected = ""
        bounds = [0]
        for cps, exp in cases:
            for cp in cps:
                text += chr(cp)
            expected += "".join("1" if b else "0" for b in exp)
            bounds.append(bounds[-1] + len(cps))
        lines.append("///|")
        lines.append(f"/// Code points of the {len(cases)} {name} test cases.")
        lines.append(ucd.mbt_string_pool(
            f"{name}_text", text, width=60, escaper=ucd.quote_full))
        lines.append("///|")
        lines.append(f"/// Code point offset of each {name} test case.")
        lines.append(ucd.mbt_ints(f"{name}_bounds", bounds, per_line=12, typ="Int"))
        lines.append("///|")
        lines.append(f"/// Expected boundaries of every {name} test case, one "
                     "'1'/'0' per internal position.")
        lines.append(ucd.mbt_string_pool(
            f"{name}_expected", expected, width=60, escaper=ucd.quote_raw))
    return "\n".join(lines)


def emit_moon_pkg():
    return 'import {\n  "moonbitstack/moonucd/segment",\n} for "test"\n'


def emit_segment_mbt():
    lines = ucd.header("gen_segment.py", VERSION)
    lines.append("///|")
    lines.append("/// The version of the Unicode Character Database the tables come from.")
    lines.append("pub fn version() -> String {\n  ucd_version\n}")
    lines.append(emit_enums())
    lines.append(SEGMENT_MBT.strip())
    return "\n".join(lines)


def generate():
    gcb, wb, sb, ep, incb = load()
    SRC.mkdir(parents=True, exist_ok=True)
    cases = [
        ("grapheme", "auxiliary/GraphemeBreakTest.txt"),
        ("word", "auxiliary/WordBreakTest.txt"),
        ("sentence", "auxiliary/SentenceBreakTest.txt"),
    ]
    for path, body in (
        ("tables.mbt", emit_tables(gcb, wb, sb, ep, incb)),
        ("segment.mbt", emit_segment_mbt()),
        ("moon.pkg", emit_moon_pkg()),
        ("segment_vectors_test.mbt",
         emit_tests([(n, parse_test(fetch(f, AUX))) for n, f in cases])),
    ):
        ucd.write(SRC / path, body.split("\n"))
    print("generated the segment package")


if __name__ == "__main__":
    if "--check" in sys.argv:
        sys.exit(1 if validate() else 0)
    generate()
