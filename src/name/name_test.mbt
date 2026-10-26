///|
/// FNV-1a over `name` for every scalar value, the digest the same walk over
/// Python's unicodedata gives. This is the strongest conformance check: a
/// single mis-named code point, or one wrong Hangul/CJK formula, changes it.
fn name_digest_walk() -> UInt32 {
  let mut h : UInt32 = 0x811C9DC5
  for cp in 0..<0x110000 {
    if cp >= 0xD800 && cp <= 0xDFFF {
      continue
    }
    match @name.name(cp.unsafe_to_char()) {
      None => h = h * 0x01000193
      Some(s) => {
        h = (h ^ s.length().reinterpret_as_uint()) * 0x01000193
        for ch in s {
          h = (h ^ ch.to_int().reinterpret_as_uint()) * 0x01000193
        }
      }
    }
  }
  h
}

///|
/// FNV-1a over `lookup` for the probe names, the digest the same walk over
/// Python's unicodedata name resolution gives.
fn lookup_digest_walk() -> UInt32 {
  let mut h : UInt32 = 0x811C9DC5
  for i in 0..<lookup_probes.length() {
    match @name.lookup(lookup_probes[i]) {
      None => h = h * 0x01000193
      Some(ch) => h = (h ^ ch.to_int().reinterpret_as_uint()) * 0x01000193
    }
  }
  h
}

///|
test "name agrees with unicodedata on every code point" {
  assert_eq(name_digest_walk(), name_digest)
}

///|
test "lookup agrees with unicodedata on the probe set" {
  assert_eq(lookup_digest_walk(), lookup_digest)
}

///|
test "version is the Unicode 17.0.0 database" {
  assert_eq(@name.version(), "17.0.0")
}

///|
test "name on the usual suspects" {
  assert_eq(@name.name('a'), Some("LATIN SMALL LETTER A"))
  assert_eq(@name.name('A'), Some("LATIN CAPITAL LETTER A"))
  assert_eq(@name.name('€'), Some("EURO SIGN"))
  assert_eq(@name.name('\u{1F514}'), Some("BELL"))
  assert_eq(@name.name('\u{4E00}'), Some("CJK UNIFIED IDEOGRAPH-4E00"))
  assert_eq(@name.name('\u{20000}'), Some("CJK UNIFIED IDEOGRAPH-20000"))
}

///|
test "name spells the ideograph-like scripts by rule NR2" {
  assert_eq(@name.name('\u{17000}'), Some("TANGUT IDEOGRAPH-17000"))
  assert_eq(@name.name('\u{18D00}'), Some("TANGUT IDEOGRAPH-18D00"))
  assert_eq(
    @name.name('\u{18B00}'),
    Some("KHITAN SMALL SCRIPT CHARACTER-18B00"),
  )
  assert_eq(@name.name('\u{1B170}'), Some("NUSHU CHARACTER-1B170"))
  assert_eq(@name.name('\u{F900}'), Some("CJK COMPATIBILITY IDEOGRAPH-F900"))
  assert_eq(@name.name('\u{13460}'), Some("EGYPTIAN HIEROGLYPH-13460"))
  assert_eq(@name.name('\u{18800}'), Some("TANGUT COMPONENT-001"))
}

///|
test "name gives no name to unassigned and private-use code points" {
  assert_eq(@name.name('\u{0378}'), None)
  assert_eq(@name.name('\u{E000}'), None)
  assert_eq(@name.name('\u{10FFFD}'), None)
}

///|
test "name spells Hangul syllables with their Latin transliteration" {
  assert_eq(@name.name('\u{AC00}'), Some("HANGUL SYLLABLE GA"))
  assert_eq(@name.name('\u{AC01}'), Some("HANGUL SYLLABLE GAG"))
  assert_eq(@name.name('\u{D7A3}'), Some("HANGUL SYLLABLE HIH"))
}

///|
test "lookup resolves canonical names, aliases, and loose variants" {
  assert_eq(@name.lookup("LATIN CAPITAL LETTER A"), Some('A'))
  assert_eq(@name.lookup("latin capital letter a"), Some('A'))
  assert_eq(@name.lookup("LATIN-CAPITAL_LETTER A"), Some('A'))
  assert_eq(@name.lookup("BELL"), Some('\u{1F514}'))
  assert_eq(@name.lookup("CR"), Some('\u{D}'))
  assert_eq(@name.lookup("LF"), Some('\u{A}'))
  assert_eq(@name.lookup("CJK UNIFIED IDEOGRAPH-4E00"), Some('\u{4E00}'))
  assert_eq(@name.lookup("HANGUL SYLLABLE GA"), Some('\u{AC00}'))
  assert_eq(@name.lookup("TANGUT COMPONENT-001"), Some('\u{18800}'))
  assert_eq(@name.lookup("NUSHU CHARACTER-1B170"), Some('\u{1B170}'))
  assert_eq(
    @name.lookup("KHITAN SMALL SCRIPT CHARACTER-18B00"),
    Some('\u{18B00}'),
  )
  assert_eq(@name.lookup("tangut ideograph-17000"), Some('\u{17000}'))
  assert_eq(@name.lookup("NULL"), Some('\u{0}'))
}

///|
test "lookup refuses derived names outside their runs or badly spelled" {
  assert_eq(@name.lookup("CJK UNIFIED IDEOGRAPH-04E00"), None)
  assert_eq(@name.lookup("CJK UNIFIED IDEOGRAPH-9FFF0"), None)
  assert_eq(@name.lookup("TANGUT IDEOGRAPH-18800"), None)
  assert_eq(@name.lookup("HANGUL SYLLABLE GAX"), None)
  assert_eq(@name.lookup("HANGUL SYLLABLE"), None)
}

///|
test "lookup reads back every name name gives" {
  for cp in 0..<0x110000 {
    if cp >= 0xD800 && cp <= 0xDFFF {
      continue
    }
    let ch = cp.unsafe_to_char()
    if @name.name(ch) is Some(n) {
      assert_eq(@name.lookup(n), Some(ch))
    }
  }
}

///|
test "lookup keeps the significant hyphen in U+1180's name" {
  assert_eq(@name.lookup("HANGUL JUNGSEONG O-E"), Some('\u{1180}'))
  assert_eq(@name.lookup("HANGUL JUNGSEONG OE"), Some('\u{116C}'))
  assert_eq(@name.lookup("HANGUL JUNGSEONG O E"), Some('\u{116C}'))
}

///|
test "lookup keeps a hyphen that is not between two letters" {
  assert_eq(@name.lookup("TIBETAN LETTER -A"), Some('\u{0F60}'))
  assert_eq(@name.lookup("TIBETAN LETTER A"), Some('\u{0F68}'))
  assert_eq(
    @name.lookup("TIBETAN MARK BKA- SHOG GI MGO RGYAN"),
    Some('\u{0FD0}'),
  )
}

///|
test "lookup fails on unknown and empty names" {
  assert_eq(@name.lookup("nonexistent name"), None)
  assert_eq(@name.lookup(""), None)
  assert_eq(@name.lookup("GREEK SMALL LETTER ALPHA X"), None)
}
