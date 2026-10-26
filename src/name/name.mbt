///|
/// The version of the Unicode Character Database the tables come from.
pub fn version() -> String {
  ucd_version
}

///|
/// The name of `ch`, or `None` when the code point has none: unassigned code
/// points, surrogates, private use and noncharacters. Hangul syllables and the
/// ideograph-like scripts named `PREFIX-XXXX` (CJK, Tangut, Khitan, Nushu,
/// Egyptian hieroglyphs) are spelled by the Standard's rules NR1 and NR2.
pub fn name(ch : Char) -> String? {
  let cp = ch.to_int()
  if cp >= hangul_first && cp <= hangul_last {
    return Some(hangul(cp))
  }
  if find_rule(cp) is Some(r) {
    return Some(prefixes[rule_prefix[r]] + hex(cp))
  }
  match find_cp(cp) {
    Some(i) => Some(explicit(i))
    None => None
  }
}

///|
/// The code point named `name`, matched the loose way of UAX #44 (LM2): case,
/// spaces, underscores and medial hyphens ignored, except the hyphen in
/// U+1180's name. Formal names and every NameAliases alias resolve; a formal
/// name wins over an alias spelled the same.
pub fn lookup(name : StringView) -> Char? {
  let key = lm2(name)
  match derived(key) {
    Some(cp) => Some(cp.unsafe_to_char())
    None => find_key(key)
  }
}

///|
let hangul_first = 0xAC00

///|
let hangul_last = 0xD7A3

///|
fn hangul(cp : Int32) -> String {
  let s = cp - hangul_first
  let tails = jamo_tails.length()
  let vowels = jamo_vowels.length()
  "HANGUL SYLLABLE " +
  jamo_leads[s / (vowels * tails)] +
  jamo_vowels[s % (vowels * tails) / tails] +
  jamo_tails[s % tails]
}

///|
fn explicit(i : Int32) -> String {
  name_pool
  .view(start_offset=name_offsets[i], end_offset=name_offsets[i + 1])
  .to_owned()
}

///|
fn hex(cp : Int32) -> String {
  cp.to_string(radix=16).to_upper().pad_start(4, '0')
}

///|
/// The code point a derived name spells: a Hangul syllable read back through
/// rule NR1, or `PREFIX-XXXX` whose code point sits in a run of that prefix.
fn derived(key : String) -> Int32? {
  if key.has_prefix("HANGULSYLLABLE") {
    return syllable(key.view(start_offset=14))
  }
  for r in 0..<rule_starts.length() {
    let prefix = prefixes[rule_prefix[r]]
    let head = lm2(prefix.view(end_offset=prefix.length() - 1))
    if !key.has_prefix(head) {
      continue
    }
    let tail = key.view(start_offset=head.length())
    guard parse_hex(tail) is Some(cp) && hex(cp).view() == tail else {
      continue
    }
    for i in 0..<rule_starts.length() {
      if rule_prefix[i] == rule_prefix[r] &&
        rule_starts[i] <= cp &&
        cp <= rule_ends[i] {
        return Some(cp)
      }
    }
  }
  None
}

///|
/// Rule NR1 read backwards: the longest lead, then the longest vowel, then a
/// tail that ends the name.
fn syllable(rest : StringView) -> Int32? {
  guard longest(rest, jamo_leads) is Some(l) else { return None }
  let rest = rest.view(start_offset=jamo_leads[l].length())
  guard longest(rest, jamo_vowels) is Some(v) else { return None }
  let rest = rest.view(start_offset=jamo_vowels[v].length())
  for t, tail in jamo_tails {
    if rest == tail {
      return Some(
        hangul_first + (l * jamo_vowels.length() + v) * jamo_tails.length() + t,
      )
    }
  }
  None
}

///|
fn longest(s : StringView, table : FixedArray[String]) -> Int32? {
  let mut best = None
  for i, jamo in table {
    if s.has_prefix(jamo) &&
      (best is None || jamo.length() > table[best.unwrap()].length()) {
      best = Some(i)
    }
  }
  best
}

///|
fn find_rule(cp : Int32) -> Int32? {
  let mut a = 0
  let mut b = rule_starts.length()
  while a < b {
    let mid = (a + b) / 2
    if rule_ends[mid] < cp {
      a = mid + 1
    } else if rule_starts[mid] > cp {
      b = mid
    } else {
      return Some(mid)
    }
  }
  None
}

///|
fn find_cp(cp : Int32) -> Int32? {
  let mut a = 0
  let mut b = name_cps.length()
  while a < b {
    let mid = (a + b) / 2
    if name_cps[mid] < cp {
      a = mid + 1
    } else if name_cps[mid] > cp {
      b = mid
    } else {
      return Some(mid)
    }
  }
  None
}

///|
/// Binary search the LM2 keys of every name and alias, in the order
/// `lookup_order` lists them.
fn find_key(key : String) -> Char? {
  let mut a = 0
  let mut b = lookup_order.length()
  while a < b {
    let mid = (a + b) / 2
    let e = lookup_order[mid]
    let c = key_cmp(
      lm2(if e >= 0 { explicit(e) } else { alias_names[-1 - e] }),
      key,
    )
    if c < 0 {
      a = mid + 1
    } else if c > 0 {
      b = mid
    } else {
      let cp = if e >= 0 { name_cps[e] } else { alias_cps[-1 - e] }
      return Some(cp.unsafe_to_char())
    }
  }
  None
}

///|
/// UAX #44 LM2: upper case, then ignore spaces, underscores and medial
/// hyphens (a hyphen between two letters or digits), save the hyphen in
/// U+1180's name.
fn lm2(name : StringView) -> String {
  let up = name.to_upper()
  let keep_hyphen = up == "HANGUL JUNGSEONG O-E"
  let out = StringBuilder()
  for i in 0..<up.length() {
    match up.unsafe_get(i).to_int().unsafe_to_char() {
      ' ' | '_' => ()
      '-' if !keep_hyphen &&
        i > 0 &&
        i + 1 < up.length() &&
        alnum(up.unsafe_get(i - 1)) &&
        alnum(up.unsafe_get(i + 1)) => ()
      ch => out.write_char(ch)
    }
  }
  out.to_string()
}

///|
fn alnum(unit : UInt16) -> Bool {
  let c = unit.to_int()
  (c >= 'A'.to_int() && c <= 'Z'.to_int()) ||
  (c >= '0'.to_int() && c <= '9'.to_int())
}

///|
/// Code point order, which the generator sorted the keys by; `String`'s own
/// `compare` is shortlex.
fn key_cmp(a : String, b : String) -> Int32 {
  let n = if a.length() < b.length() { a.length() } else { b.length() }
  for i in 0..<n {
    let x = a.unsafe_get(i)
    let y = b.unsafe_get(i)
    if x != y {
      return if x < y { -1 } else { 1 }
    }
  }
  a.length() - b.length()
}

///|
fn parse_hex(s : StringView) -> Int32? {
  if s.length() == 0 || s.length() > 6 {
    return None
  }
  let mut v = 0
  for ch in s {
    let d = match ch {
      '0'..<='9' => ch.to_int() - '0'.to_int()
      'A'..<='F' => ch.to_int() - 'A'.to_int() + 10
      _ => return None
    }
    v = v * 16 + d
  }
  Some(v)
}
