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
