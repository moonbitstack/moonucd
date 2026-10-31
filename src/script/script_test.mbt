///|
/// FNV-1a over the results for every scalar value, the digest the same walk
/// over Scripts.txt and ScriptExtensions.txt gives.
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
/// Whether a list of ranges holds `cp` — the question a matcher asks of the
/// answer, and the one a test has to ask too.
fn holds(ranges : Array[(Int32, Int32)], cp : Int32) -> Bool {
  for (a, b) in ranges {
    if a <= cp && cp <= b {
      return true
    }
  }
  false
}

///|
test "script agrees with Scripts.txt on every code point" {
  let d = digest((ch, out) => spelled(@script.script(ch).to_string(), out))
  assert_eq(d, script_digest)
}

///|
test "extensions agree with ScriptExtensions.txt on every code point" {
  let d = digest((ch, out) => {
    let exts = @script.extensions(ch)
    out.push(exts.length())
    for s in exts {
      spelled(s.to_string(), out)
    }
  })
  assert_eq(d, extensions_digest)
}

///|
test "Script::of reads every long name and code" {
  for i, key in of_keys {
    match @script.Script::of(key) {
      Some(s) => assert_eq(s.to_string(), of_names[i])
      None => fail("\{key} not found")
    }
  }
}

///|
test "Script::of ignores case, spaces, underscores, hyphens and a leading is" {
  assert_true(@script.Script::of("Latin") == Some(@script.Latin))
  assert_true(@script.Script::of("latn") == Some(@script.Latin))
  assert_true(@script.Script::of("LATN") == Some(@script.Latin))
  assert_true(@script.Script::of("old italic") == Some(@script.OldItalic))
  assert_true(@script.Script::of("Old_Italic") == Some(@script.OldItalic))
  assert_true(@script.Script::of("isGreek") == Some(@script.Greek))
  assert_true(@script.Script::of("  Greek  ") == Some(@script.Greek))
  assert_true(@script.Script::of("nonsense") == None)
  assert_true(@script.Script::of("") == None)
}

///|
test "Show writes the long name" {
  assert_eq(@script.Latin.to_string(), "Latin")
  assert_eq(@script.OldItalic.to_string(), "Old_Italic")
  assert_eq(@script.Han.to_string(), "Han")
  assert_eq(@script.Unknown.to_string(), "Unknown")
}

///|
test "scripts and extensions on the usual suspects" {
  assert_true(@script.script('a') == @script.Latin)
  assert_true(@script.script('中') == @script.Han)
  assert_true(@script.script('あ') == @script.Hiragana)
  assert_true(@script.script(' ') == @script.Common)
  assert_true(@script.script('\u{0300}') == @script.Inherited)
  assert_true(@script.script('\u{0E33}') == @script.Thai)
  assert_true(@script.script('\u{0378}') == @script.Unknown)
  assert_true(@script.script('\u{0870}') == @script.Arabic)
  assert_true(@script.script('\u{10FFFF}') == @script.Unknown)
  let middle_dot = @script.extensions('\u{00B7}')
  assert_true(middle_dot.length() > 1)
  assert_true(middle_dot.contains(@script.Latin))
  assert_true(middle_dot.contains(@script.Han))
  assert_true(!middle_dot.contains(@script.Common))
  assert_true(@script.extensions('a') == [@script.Latin])
}

///|
test "version" {
  assert_true(@script.version() == "17.0.0")
}

///|
test "script ranges agree with Scripts.txt on every code point" {
  let mut h : UInt32 = 0x811C9DC5
  for s in script_ranges_order {
    for (a, b) in s.ranges() {
      h = (h ^ a.reinterpret_as_uint()) * 0x01000193
      h = (h ^ b.reinterpret_as_uint()) * 0x01000193
    }
  }
  assert_eq(h, script_ranges_digest)
}

///|
test "script extension ranges agree with ScriptExtensions.txt" {
  let mut h : UInt32 = 0x811C9DC5
  for s in script_ranges_order {
    for (a, b) in s.extended_ranges() {
      h = (h ^ a.reinterpret_as_uint()) * 0x01000193
      h = (h ^ b.reinterpret_as_uint()) * 0x01000193
    }
  }
  assert_eq(h, scx_ranges_digest)
}

///|
test "every script's ranges are in order, apart, and within the code space" {
  for s in script_ranges_order {
    let ranges = s.ranges()
    let mut prev : Int32 = -2
    for (a, b) in ranges {
      assert_true(a <= b)
      assert_true(b <= 0x10FFFF)
      assert_true(a > prev + 1)
      prev = b
    }
  }
}

///|
test "the scripts between them account for every code point once" {
  let mut covered : Int32 = 0
  for s in script_ranges_order {
    for (a, b) in s.ranges() {
      covered += b - a + 1
    }
  }
  assert_eq(covered, 0x110000)
}

///|
test "a range holds characters of its script at both ends" {
  for s in script_ranges_order {
    for (a, b) in s.ranges() {
      assert_true(@script.script(a.unsafe_to_char()) == s)
      assert_true(@script.script(b.unsafe_to_char()) == s)
    }
  }
}

///|
test "an extension range lists its script among the scripts of both ends" {
  for s in script_ranges_order {
    for (a, b) in s.extended_ranges() {
      assert_true(@script.extensions(a.unsafe_to_char()).contains(s))
      assert_true(@script.extensions(b.unsafe_to_char()).contains(s))
    }
  }
}

///|
/// The plain table and the shared one are two answers to the same question, so
/// between them the extension ranges hold a character exactly as often as its
/// extensions list it.
test "the extension ranges cover each character as often as its extensions" {
  let mut shared : Int32 = 0
  for s in script_ranges_order {
    for (a, b) in s.extended_ranges() {
      shared += b - a + 1
    }
  }
  let mut expected : Int32 = 0
  for cp in 0..<0x110000 {
    for _ in @script.extensions(cp.unsafe_to_char()) {
      expected += 1
    }
  }
  assert_eq(shared, expected)
}

///|
test "ranges on the usual suspects" {
  assert_eq(@script.Latin.ranges()[0], (0x41, 0x5A))
  assert_true(@script.Greek.ranges().length() > 30)
  assert_true(@script.Han.ranges().contains((0x4E00, 0x9FFF)))
}

///|
test "a script shared with another one shows in both extension tables" {
  let mark = '\u{30FC}'
  let hiragana = @script.Hiragana.extended_ranges()
  let katakana = @script.Katakana.extended_ranges()
  assert_true(holds(katakana, 0x30FC))
  assert_true(holds(hiragana, 0x30FC))
  assert_true(!holds(@script.Katakana.ranges(), 0x30FC))
  assert_true(@script.script(mark) == @script.Common)
}
