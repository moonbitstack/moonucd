///|
/// FNV-1a over the results for every scalar value, the digest the same
/// walk over Python 3.15's `unicodedata` and `str` (Unicode 17.0.0) gives.
fn digest(each : (Char, Array[Int32]) -> Unit) -> UInt32 {
  let mut h : UInt32 = 0x811C9DC5
  let buf = []
  for cp in 0..<0x110000 {
    if cp >= 0xD800 && cp <= 0xDFFF {
      continue
    }
    buf.clear()
    each(cp.unsafe_to_char(), buf)
    for x in buf {
      h = (h ^ x.reinterpret_as_uint()) * 0x01000193
    }
  }
  h
}

///|
fn spelled(s : String, out : Array[Int32]) -> Unit {
  let chars = s.iter().collect()
  out.push(chars.length())
  for ch in chars {
    out.push(ch.to_int())
  }
}

///|
let category_order : Array[String] = [
  "Lu", "Ll", "Lt", "Lm", "Lo", "Mn", "Mc", "Me", "Nd", "Nl", "No", "Pc", "Pd", "Ps",
  "Pe", "Pi", "Pf", "Po", "Sm", "Sc", "Sk", "So", "Zs", "Zl", "Zp", "Cc", "Cf", "Cs",
  "Co", "Cn",
]

///|
test "category agrees with Python on every code point" {
  let d = digest((ch, out) => {
    let name = @moonucd.category(ch).to_string()
    out.push(category_order.search(name).unwrap())
  })
  assert_eq(d, 3386982449)
}

///|
test "numeric type agrees with Python on every code point" {
  let d = digest((ch, out) => {
    out.push(
      match @moonucd.numeric(ch) {
        Some(Decimal) => 1
        Some(Digit) => 2
        Some(Numeric) => 3
        None => 0
      },
    )
  })
  assert_eq(d, 1227254506)
}

///|
test "upper agrees with str.upper on every code point" {
  let d = digest((ch, out) => spelled(@moonucd.upper(ch.to_string()), out))
  assert_eq(d, 622818959)
}

///|
test "lower agrees with str.lower on every code point" {
  let d = digest((ch, out) => spelled(@moonucd.lower(ch.to_string()), out))
  assert_eq(d, 2431480720)
}

///|
test "title agrees with str.title on every code point" {
  let d = digest((ch, out) => spelled(@moonucd.title(ch.to_string()), out))
  assert_eq(d, 1720932071)
}

///|
test "fold agrees with str.casefold on every code point" {
  let d = digest((ch, out) => spelled(@moonucd.fold(ch.to_string()), out))
  assert_eq(d, 2760943162)
}

///|
test "emoji properties agree with emoji-data.txt on every code point" {
  let d = digest((ch, out) => {
    out.push(if @moonucd.has(ch, Emoji) { 1 } else { 0 })
    out.push(if @moonucd.has(ch, EmojiPresentation) { 1 } else { 0 })
    out.push(if @moonucd.has(ch, EmojiModifier) { 1 } else { 0 })
    out.push(if @moonucd.has(ch, EmojiModifierBase) { 1 } else { 0 })
    out.push(if @moonucd.has(ch, EmojiComponent) { 1 } else { 0 })
    out.push(if @moonucd.has(ch, ExtendedPictographic) { 1 } else { 0 })
  })
  assert_eq(d, 3592936711)
}

///|
test "emoji properties on the usual suspects" {
  assert_true(@moonucd.has('#', Emoji))
  assert_true(!@moonucd.has('#', EmojiPresentation))
  assert_true(@moonucd.has('\u{1F600}', EmojiPresentation))
  assert_true(@moonucd.has('\u{1F3FB}', EmojiModifier))
  assert_true(@moonucd.has('☝', EmojiModifierBase))
  assert_true(@moonucd.has('#', EmojiComponent))
  assert_true(!@moonucd.has('a', EmojiComponent))
  assert_true(@moonucd.has('©', ExtendedPictographic))
}

///|
test "full mappings change length" {
  assert_eq(@moonucd.upper("straße"), "STRASSE")
  assert_eq(@moonucd.fold("Straße"), "strasse")
  assert_eq(@moonucd.lower("İ"), "i̇")
  assert_eq(@moonucd.title("ǆ"), "ǅ")
  assert_eq(@moonucd.upper("ﬃ"), "FFI")
}

///|
test "final sigma" {
  assert_eq(@moonucd.lower("ΟΔΟΣ"), "οδος")
  assert_eq(@moonucd.lower("ΟΔΟΣ ΟΔΟΣ"), "οδος οδος")
  assert_eq(@moonucd.lower("Σ"), "σ")
  assert_eq(@moonucd.lower("ΣΑ"), "σα")
  assert_eq(@moonucd.lower("Α.Σ'"), "α.ς'")
}

///|
test "properties" {
  assert_true(@moonucd.has('a', Alphabetic))
  assert_true(@moonucd.has('中', Alphabetic))
  assert_true(!@moonucd.has('1', Alphabetic))
  assert_true(@moonucd.has('A', Uppercase))
  assert_true(@moonucd.has('ª', Lowercase))
  assert_true(@moonucd.has('\u{3000}', WhiteSpace))
  assert_true(!@moonucd.has('\u{1C}', WhiteSpace))
  assert_true(@moonucd.has('_', XidContinue))
  assert_true(!@moonucd.has('_', XidStart))
  assert_true(@moonucd.has('\u{10FFFF}', NoncharacterCodePoint))
}

///|
test "bidi and category" {
  assert_true(@moonucd.bidi('\u{1C}') == B)
  assert_true(@moonucd.bidi(' ') == WS)
  assert_true(@moonucd.bidi('א') == R)
  assert_eq(@moonucd.category('\u{E000}').to_string(), "Co")
  assert_eq(@moonucd.category('\u{10FFFF}').to_string(), "Cn")
  assert_eq(@moonucd.category('ǅ').to_string(), "Lt")
  assert_true(@moonucd.version() == "17.0.0")
}
