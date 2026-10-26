///|
/// The version of the Unicode Character Database the tables come from.
pub fn version() -> String {
  ucd_version
}

///|
/// A Unicode normalization form. NFC and NFKC are the composed forms; NFD and
/// NFKD are the decomposed forms.
pub(all) enum Form {
  NFC
  NFD
  NFKC
  NFKD
} derive(Eq)

///|
pub extend Form with Eq::{equal, not_equal}

///|
pub impl Show for Form with fn output(self, logger) {
  match self {
    NFC => logger.write_string("NFC")
    NFD => logger.write_string("NFD")
    NFKC => logger.write_string("NFKC")
    NFKD => logger.write_string("NFKD")
  }
}

///|
pub extend Form with Show::{to_string, output}

///|
/// Hangul algorithmic constants (UAX #15, derived from the SBase math).
let hangul_sbase : Int32 = 0xAC00

///|
let hangul_lbase : Int32 = 0x1100

///|
let hangul_vbase : Int32 = 0x1161

///|
let hangul_tbase : Int32 = 0x11A7

///|
let hangul_lcount : Int32 = 19

///|
let hangul_vcount : Int32 = 21

///|
let hangul_tcount : Int32 = 28

///|
let hangul_ncount : Int32 = 588 // vcount * tcount

///|
let hangul_scount : Int32 = 11172 // lcount * ncount

///|
priv struct CC {
  cp : Int32
  ccc : Int32
}

///|
/// `s` in `form` — NFC, NFD, NFKC or NFKD — exactly as Unicode defines it:
/// decompose recursively, put the sequence in canonical order, then compose the
/// decomposed form when `form` is a composed one.
pub fn normalize(form : Form, s : StringView) -> String {
  let compat = form == NFKC || form == NFKD
  let buf : Array[CC] = []
  for ch in s {
    decompose(ch.to_int(), compat, buf)
  }
  canonical_order(buf)
  match form {
    NFC | NFKC => compose(buf)
    NFD | NFKD => buf_to_string(buf)
  }
}

///|
/// True when `s` is already in `form` (no change under `normalize`).
pub fn is_normalized(form : Form, s : StringView) -> Bool {
  normalize(form, s) == s.to_owned()
}

///|
/// Recursively expand `cp` into `(code point, ccc)` pairs, appending to `out`.
/// A Hangul syllable is expanded algorithmically; everything else is looked up
/// in the decomposed forms table.
fn decompose(cp : Int32, compat : Bool, out : Array[CC]) -> Unit {
  if hangul_sbase <= cp && cp < hangul_sbase + hangul_scount {
    let sindex = cp - hangul_sbase
    let l = hangul_lbase + sindex / hangul_ncount
    let v = hangul_vbase + sindex % hangul_ncount / hangul_tcount
    let t = sindex % hangul_tcount
    out.push(CC::{ cp: l, ccc: 0, })
    out.push(CC::{ cp: v, ccc: 0, })
    if t > 0 {
      out.push(CC::{ cp: hangul_tbase + t, ccc: 0, })
    }
    return
  }
  match find_decomp(cp) {
    None => out.push(CC::{ cp, ccc: ccc_of(cp), })
    Some((tag_idx, start, len)) =>
      if !compat && tag_idx != 0 {
        out.push(CC::{ cp, ccc: ccc_of(cp), })
      } else {
        for i in 0..<len {
          decompose(dec_targets[start + i], compat, out)
        }
      }
  }
}

///|
/// The canonical ordering: bubble-sort only the non-starter runs by their
/// combining class, leaving starters (ccc 0) where they are.
fn canonical_order(buf : Array[CC]) -> Unit {
  let n = buf.length()
  let mut changed = true
  while changed {
    changed = false
    for i in 1..<n {
      let a = buf[i - 1]
      let b = buf[i]
      if a.ccc > 0 && b.ccc > 0 && a.ccc > b.ccc {
        buf[i - 1] = b
        buf[i] = a
        changed = true
      }
    }
  }
}

///|
/// The canonical composition over the (already decomposed, canonically ordered)
/// sequence: compose each character with the last starter when nothing between
/// them blocks — a blocker is a starter or a character of equal-or-higher
/// combining class. Hangul L+V and LV+T are composed here too.
fn compose(buf : Array[CC]) -> String {
  let out : Array[CC] = []
  let mut starter_idx = -1
  for i in 0..<buf.length() {
    let c = buf[i]
    let mut placed = false
    if starter_idx >= 0 {
      if c.ccc == 0 {
        // A starter composes with the previous starter only when adjacent.
        if out.length() - 1 == starter_idx {
          match compose_pair(out[starter_idx].cp, c.cp) {
            Some(comp) => {
              out[starter_idx] = CC::{ cp: comp, ccc: 0, }
              placed = true
            }
            None => ()
          }
        }
      } else if out[out.length() - 1].ccc < c.ccc {
        // A non-starter composes unless a higher-or-equal class blocks it.
        match compose_pair(out[starter_idx].cp, c.cp) {
          Some(comp) => {
            out[starter_idx] = CC::{ cp: comp, ccc: 0, }
            placed = true
          }
          None => ()
        }
      }
    }
    if !placed {
      out.push(c)
      if c.ccc == 0 {
        starter_idx = out.length() - 1
      }
    }
  }
  buf_to_string(out)
}

///|
fn buf_to_string(buf : Array[CC]) -> String {
  let sb = StringBuilder()
  for c in buf {
    sb.write_char(c.cp.unsafe_to_char())
  }
  sb.to_string()
}

///|
/// The composite of `a` and `b`: the Hangul rules first, then the stored
/// canonical composition pairs.
fn compose_pair(a : Int32, b : Int32) -> Int32? {
  if hangul_lbase <= a &&
    a < hangul_lbase + hangul_lcount &&
    hangul_vbase <= b &&
    b < hangul_vbase + hangul_vcount {
    let lv = hangul_sbase +
      (a - hangul_lbase) * hangul_ncount +
      (b - hangul_vbase) * hangul_tcount
    return Some(lv)
  }
  if hangul_sbase <= a &&
    a < hangul_sbase + hangul_scount &&
    (a - hangul_sbase) % hangul_tcount == 0 &&
    hangul_tbase < b &&
    b < hangul_tbase + hangul_tcount {
    return Some(a + (b - hangul_tbase))
  }
  find_compose(a, b)
}

///|
/// The stored composition pair (A, B) -> C, or `None`.
fn find_compose(a : Int32, b : Int32) -> Int32? {
  let n = comp_a.length()
  let mut lo = 0
  let mut hi = n
  while lo < hi {
    let mid = (lo + hi) / 2
    if comp_a[mid] < a {
      lo = mid + 1
    } else {
      hi = mid
    }
  }
  while lo < n && comp_a[lo] == a {
    if comp_b[lo] == b {
      return Some(comp_c[lo])
    }
    lo += 1
  }
  None
}

///|
/// The Canonical_Combining_Class of `ch` (0 when it has none).
pub fn combining(ch : Char) -> Int32 {
  ccc_of(ch.to_int())
}

///|
/// The first-level decomposition mapping of `ch`, as the UCD lists it: a space
/// separated, upper-case, four-digit-hex sequence, or `""` when `ch` has none.
pub fn decomposition(ch : Char) -> String {
  let cp = ch.to_int()
  match find_decomp(cp) {
    None => ""
    Some((tag_idx, start, len)) => {
      let sb = StringBuilder()
      sb.write_string(dec_tags[tag_idx])
      for i in 0..<len {
        if i > 0 {
          sb.write_char(' ')
        }
        sb.write_string(hex4(dec_targets[start + i]))
      }
      sb.to_string()
    }
  }
}

///|
fn hex4(v : Int32) -> String {
  let mut x = v
  let mut digits = ""
  if x == 0 {
    digits = "0"
  } else {
    while x > 0 {
      let d = x % 16
      digits = hex_digit(d) + digits
      x = x / 16
    }
  }
  while digits.length() < 4 {
    digits = "0" + digits
  }
  digits
}

///|
fn hex_digit(d : Int32) -> String {
  match d {
    0 => "0"
    1 => "1"
    2 => "2"
    3 => "3"
    4 => "4"
    5 => "5"
    6 => "6"
    7 => "7"
    8 => "8"
    9 => "9"
    10 => "A"
    11 => "B"
    12 => "C"
    13 => "D"
    14 => "E"
    _ => "F"
  }
}

///|
fn find_decomp(cp : Int32) -> (Int32, Int32, Int32)? {
  let mut a = 0
  let mut b = dec_keys.length()
  while a < b {
    let mid = (a + b) / 2
    if dec_keys[mid] < cp {
      a = mid + 1
    } else if dec_keys[mid] > cp {
      b = mid
    } else {
      return Some(
        (
          dec_tag[mid],
          dec_offsets[mid],
          dec_offsets[mid + 1] - dec_offsets[mid],
        ),
      )
    }
  }
  None
}

///|
fn ccc_of(cp : Int32) -> Int32 {
  let mut a = 0
  let mut b = ccc_starts.length()
  while a < b {
    let mid = (a + b) / 2
    if ccc_ends[mid] < cp {
      a = mid + 1
    } else {
      b = mid
    }
  }
  if a < ccc_starts.length() && ccc_starts[a] <= cp {
    return ccc_values[a]
  }
  0
}
