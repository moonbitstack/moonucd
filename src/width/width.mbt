///|
/// The version of the Unicode Character Database (and the wcwidth table) the
/// width data comes from.
pub fn version() -> String {
  ucd_version
}

///|
/// The East Asian Width of `ch`, the UCD `ea` property: a code point is Wide
/// (W) or Fullwidth (F) in two cells, Narrow (Na) or Halfwidth (H) in one,
/// Ambiguous (A) depends on context, and Neutral (N) defaults to one. Unassigned
/// code points and surrogates are Neutral, as unicodedata reports.
pub(all) enum Eaw {
  A // Ambiguous
  F // Fullwidth
  H // Halfwidth
  N // Neutral (the default)
  Na // Narrow
  W // Wide
} derive(Eq)

///|
pub extend Eaw with Eq::{equal, not_equal}

///|
/// Writes the UCD `ea` letter: the property's own short name.
pub impl Show for Eaw with fn output(self, logger) {
  match self {
    A => logger.write_string("A")
    F => logger.write_string("F")
    H => logger.write_string("H")
    N => logger.write_string("N")
    Na => logger.write_string("Na")
    W => logger.write_string("W")
  }
}

///|
pub extend Eaw with Show::{to_string, output}

///|
/// The East Asian Width of `ch` (see `Eaw`).
pub fn east_asian_width(ch : Char) -> Eaw {
  let cp = ch.to_int()
  match find_eaw(cp) {
    Some(i) => eaw_of(eaw_codes[i])
    None => Eaw::N
  }
}

///|
/// The number of terminal cells `ch` occupies, exactly wcwidth 0.2.14: -1 for
/// non-printable control characters, 0 for combining and other zero-width
/// marks, 2 for Wide and Fullwidth code points, and 1 otherwise.
pub fn width(ch : Char) -> Int32 {
  width_char(ch.to_int())
}

///|
/// The number of terminal cells `s` occupies, exactly wcwidth 0.2.14's
/// wcswidth: Zero Width Joiners are skipped, and a Variation Selector 16
/// (U+FE0F) following a character that gained an emoji presentation widens it
/// by one cell.
pub fn text_width(s : StringView) -> Int32 {
  let mut width = 0
  let mut last = -1
  let mut skip = false
  for ch in s {
    let ucs = ch.to_int()
    if skip {
      skip = false
      continue
    }
    if ucs == 0x200D {
      skip = true
      continue
    }
    if ucs == 0xFE0F && last >= 0 {
      if bisearch(last, vs16_starts, vs16_ends) {
        width = width + 1
      }
      last = -1
      continue
    }
    let w = width_char(ucs)
    if w < 0 {
      return w
    }
    if w > 0 {
      last = ucs
    }
    width = width + w
  }
  width
}

// ---- internals -----------------------------------------------------------

///|
/// wcwidth 0.2.14 for an ordinal value.
fn width_char(ucs : Int32) -> Int32 {
  if 32 <= ucs && ucs < 0x7F {
    return 1
  }
  if (ucs != 0 && ucs < 32) || (0x07F <= ucs && ucs < 0x0A0) {
    return -1
  }
  if bisearch(ucs, zero_starts, zero_ends) {
    return 0
  }
  if bisearch(ucs, wide_starts, wide_ends) {
    2
  } else {
    1
  }
}

///|
fn eaw_of(code : Int32) -> Eaw {
  match code {
    0 => Eaw::A
    1 => Eaw::F
    2 => Eaw::H
    3 => Eaw::N
    4 => Eaw::Na
    _ => Eaw::W
  }
}

///|
/// The index of the `ea` range holding `cp`, or `None` when it is Neutral.
fn find_eaw(cp : Int32) -> Int32? {
  let mut a = 0
  let mut b = eaw_starts.length()
  while a < b {
    let mid = (a + b) / 2
    if eaw_starts[mid] <= cp {
      a = mid + 1
    } else {
      b = mid
    }
  }
  if a > 0 {
    let i = a - 1
    if eaw_ends[i] >= cp {
      return Some(i)
    }
  }
  None
}

///|
/// Binary search a sorted, disjoint range table; true when `ucs` is inside any
/// range (Markus Kuhn's `_bisearch`, which assumes the table is ordered).
fn bisearch(
  ucs : Int32,
  starts : FixedArray[Int32],
  ends : FixedArray[Int32],
) -> Bool {
  let n = starts.length()
  if n == 0 {
    return false
  }
  let mut lbound = 0
  let mut ubound = n - 1
  if ucs < starts[0] || ucs > ends[ubound] {
    return false
  }
  while ubound >= lbound {
    let mid = (lbound + ubound) / 2
    if ucs > ends[mid] {
      lbound = mid + 1
    } else if ucs < starts[mid] {
      ubound = mid - 1
    } else {
      return true
    }
  }
  false
}
