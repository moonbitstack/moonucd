///|
/// FNV-1a over the code points of `s`, the same fold the generator used.
fn fold_form(h : UInt32, s : String) -> UInt32 {
  let prime : UInt32 = 0x01000193
  let mut hh = h
  for ch in s {
    let u = ch.to_int().reinterpret_as_uint()
    hh = (hh ^ u) * prime
  }
  hh
}

///|
test "normalize matches unicodedata on every code point" {
  let mut h : UInt32 = 0x811C9DC5
  for cp in 0..<0x110000 {
    if 0xD800 <= cp && cp <= 0xDFFF {
      continue
    }
    let s = cp.unsafe_to_char().to_string()
    h = fold_form(h, @normalize.normalize(NFC, s))
    h = fold_form(h, @normalize.normalize(NFD, s))
    h = fold_form(h, @normalize.normalize(NFKC, s))
    h = fold_form(h, @normalize.normalize(NFKD, s))
  }
  assert_eq(h, cp_norm_digest)
}

///|
test "normalize matches unicodedata on the NormalizationTest sources" {
  let mut h : UInt32 = 0x811C9DC5
  let n = nt_source_bounds.length() - 1
  // The concatenated pool contains supplementary-plane characters; string
  // slicing is unreliable for such constants in this MoonBit version, so we
  // expand it to a code-point array once and slice that by code-point offset.
  let cps : Array[Int] = []
  for ch in nt_sources_concat {
    cps.push(ch.to_int())
  }
  for i in 0..<n {
    let sb = StringBuilder()
    for k in nt_source_bounds[i]..<nt_source_bounds[i + 1] {
      sb.write_char(cps[k].unsafe_to_char())
    }
    let s = sb.to_string()
    h = fold_form(h, @normalize.normalize(NFC, s))
    h = fold_form(h, @normalize.normalize(NFD, s))
    h = fold_form(h, @normalize.normalize(NFKC, s))
    h = fold_form(h, @normalize.normalize(NFKD, s))
    assert_eq(h, nt_norm_checkpoints[i])
  }
  assert_eq(h, nt_norm_digest)
}

///|
test "combining matches unicodedata on every code point" {
  let prime : UInt32 = 0x01000193
  let mut h : UInt32 = 0x811C9DC5
  for cp in 0..<0x110000 {
    if 0xD800 <= cp && cp <= 0xDFFF {
      continue
    }
    let v = @normalize.combining(cp.unsafe_to_char())
    h = (h ^ v.reinterpret_as_uint()) * prime
  }
  assert_eq(h, combining_digest)
}

///|
test "decomposition matches unicodedata on every code point" {
  let mut h : UInt32 = 0x811C9DC5
  for cp in 0..<0x110000 {
    if 0xD800 <= cp && cp <= 0xDFFF {
      continue
    }
    h = fold_form(h, @normalize.decomposition(cp.unsafe_to_char()))
  }
  assert_eq(h, decomposition_digest)
}

///|
test "NFC / NFD of precomposed and decomposed Latin" {
  assert_eq(@normalize.normalize(NFD, "A\u{030A}"), "A\u{030A}")
  assert_eq(@normalize.normalize(NFD, "\u{00C5}"), "A\u{030A}")
  assert_eq(@normalize.normalize(NFC, "A\u{030A}"), "\u{00C5}")
  assert_eq(@normalize.normalize(NFD, "\u{00E9}"), "e\u{0301}")
  assert_eq(@normalize.normalize(NFC, "e\u{0301}"), "\u{00E9}")
  assert_eq(@normalize.normalize(NFD, "\u{00C0}"), "A\u{0300}")
  assert_eq(@normalize.decomposition('\u{00C0}'), "0041 0300")
  assert_eq(@normalize.decomposition('A'), "")
}

///|
test "combining class of known marks" {
  assert_eq(@normalize.combining('A'), 0)
  assert_eq(@normalize.combining('\u{0301}'), 230)
  assert_eq(@normalize.combining('\u{0323}'), 220)
  assert_eq(@normalize.combining('\u{0483}'), 230)
}

///|
test "Hangul composition and decomposition" {
  assert_eq(@normalize.normalize(NFC, "\u{1100}\u{1161}"), "\u{AC00}")
  assert_eq(@normalize.normalize(NFD, "\u{AC00}"), "\u{1100}\u{1161}")
  // The trailing filler U+11A7 does not compose; it survives unchanged.
  assert_eq(@normalize.normalize(NFC, "\u{1100}\u{1161}\u{11A7}"), "\u{AC00}\u{11A7}")
  assert_eq(@normalize.normalize(NFD, "\u{AC01}"), "\u{1100}\u{1161}\u{11A8}")
}

///|
test "is_normalized" {
  assert_true(@normalize.is_normalized(NFC, "\u{00C5}"))
  assert_true(@normalize.is_normalized(NFD, "A\u{030A}"))
  assert_true(!@normalize.is_normalized(NFC, "A\u{030A}"))
  assert_true(!@normalize.is_normalized(NFD, "\u{00C5}"))
  // U+00BC (VULGAR FRACTION ONE QUARTER) is not NFKC-normalized: it expands
  // to "1⁄4".
  assert_true(!@normalize.is_normalized(NFKC, "\u{00BC}"))
}
