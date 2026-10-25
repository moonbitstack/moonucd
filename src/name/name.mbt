///|
/// The version of the Unicode Character Database the tables come from.
pub fn version() -> String {
  ucd_version
}

///|
/// The name of `ch`, or `None` when the code point has none — unassigned code
/// points, surrogates and so on. Every name the database gives is stored
/// verbatim in the name pool; the code point's entry is found by binary search.
pub fn name(ch : Char) -> String? {
  let cp = ch.to_int()
  match find_cp(cp) {
    Some(i) => Some(name_pool[name_offsets[i]:name_offsets[i + 1]].to_owned())
    None => None
  }
}

///|
/// The code point named `name`, matched the loose way of UAX #44 (LM2): case,
/// spaces, underscores and medial hyphens ignored, except the hyphen in
/// U+1180's name. Formal names from the database and every NameAliases alias
/// resolve.
pub fn lookup(name : StringView) -> Char? {
  let pat = lm2(name)
  let cjk_len = 19
  if pat.length() >= cjk_len && pat[0:cjk_len] == "CJKUNIFIEDIDEOGRAPH" {
    let tail = pat[cjk_len:]
    match parse_hex(tail) {
      Some(cp) =>
        if in_cjk(cp) {
          return Some(cp.unsafe_to_char())
        } else {
          return None
        }
      None => ()
    }
  }
  find_key(pat)
}

///|
/// True when `cp` falls in a CJK Unified Ideograph range the Standard names.
fn in_cjk(cp : Int32) -> Bool {
  let mut i = 0
  while i < cjk_starts.length() {
    if cjk_starts[i] <= cp && cp <= cjk_ends[i] {
      return true
    }
    i += 1
  }
  false
}

///|
/// Binary search the sorted code points for `cp`; `None` when it is absent.
fn find_cp(cp : Int32) -> Int32? {
  let mut a = 0
  let mut b = name_cps.length()
  while a < b {
    let mid = (a + b) / 2
    let m = name_cps[mid]
    if m < cp {
      a = mid + 1
    } else if m > cp {
      b = mid
    } else {
      return Some(mid)
    }
  }
  None
}

///|
fn up_char(ch : Char) -> Char {
  if 'a' <= ch && ch <= 'z' {
    (ch.to_int() - 32).unsafe_to_char()
  } else {
    ch
  }
}

///|
/// UAX #44 LM2: upper case, then ignore spaces, underscores, and medial
/// hyphens — save the hyphen in U+1180's name, which is significant. MoonBit's
/// `String::replace` only touches the first match, so separators are dropped by
/// iterating the characters instead.
fn lm2(name : StringView) -> String {
  let up = StringBuilder()
  for ch in name {
    up.write_char(up_char(ch))
  }
  let ups = up.to_string()
  let keep_hyphen = ups == "HANGUL JUNGSEONG O-E"
  let out = StringBuilder()
  for ch in ups {
    if ch == ' ' || ch == '_' {
      continue
    }
    if ch == '-' && !keep_hyphen {
      continue
    }
    out.write_char(ch)
  }
  out.to_string()
}

///|
/// Code-point lexicographic order of two LM2 keys. MoonBit's `String` `<`
/// does not order by code point, so the lookup binary search needs this.
fn key_cmp(a : String, b : String) -> Int {
  let n = a.length()
  let m = b.length()
  let limit = if n < m { n } else { m }
  for i in 0..<limit {
    let ca = a[i].to_int()
    let cb = b[i].to_int()
    if ca != cb {
      return if ca < cb { -1 } else { 1 }
    }
  }
  if n < m { -1 } else if n > m { 1 } else { 0 }
}

///|
/// Binary search the sorted, normalised lookup keys for `pat`.
fn find_key(pat : String) -> Char? {
  let mut a = 0
  let mut b = lookup_values.length()
  while a < b {
    let mid = (a + b) / 2
    let key = lookup_pool[lookup_offsets[mid]:lookup_offsets[mid + 1]].to_owned()
    let c = key_cmp(key, pat)
    if c == 0 {
      return Some(lookup_values[mid].unsafe_to_char())
    } else if c < 0 {
      a = mid + 1
    } else {
      b = mid
    }
  }
  None
}

///|
fn parse_hex(s : StringView) -> Int32? {
  if s.length() == 0 {
    return None
  }
  let mut v = 0
  for ch in s {
    let d = if '0' <= ch && ch <= '9' {
      ch.to_int() - '0'.to_int()
    } else if 'A' <= ch && ch <= 'F' {
      ch.to_int() - 'A'.to_int() + 10
    } else if 'a' <= ch && ch <= 'f' {
      ch.to_int() - 'a'.to_int() + 10
    } else {
      return None
    }
    v = v * 16 + d
    if v > 0x10FFFF {
      return None
    }
  }
  Some(v)
}
