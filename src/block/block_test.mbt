///|
/// FNV-1a over the results for every scalar value, the digest the same walk
/// over Blocks.txt gives.
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
test "block agrees with Blocks.txt on every code point" {
  let d = digest((ch, out) => {
    match @block.block(ch) {
      Some(name) => spelled(name, out)
      None => out.push(0)
    }
  })
  assert_eq(d, block_digest)
}

///|
test "range reads every block name back" {
  for name in block_names_all {
    let (first, last) = @block.range(name).unwrap()
    assert_eq(@block.block(first), Some(name))
    assert_eq(@block.block(last), Some(name))
    if first.to_int() > 0 {
      let before = (first.to_int() - 1).unsafe_to_char()
      assert_true(@block.block(before) != Some(name))
    }
  }
}

///|
test "range ignores case, spaces, underscores, hyphens and a leading is" {
  assert_true(@block.range("basic latin") == Some(('\u{0000}', '\u{007F}')))
  assert_true(@block.range("Basic_Latin") == Some(('\u{0000}', '\u{007F}')))
  assert_true(@block.range("BASIC LATIN") == Some(('\u{0000}', '\u{007F}')))
  assert_true(@block.range("isBasic Latin") == Some(('\u{0000}', '\u{007F}')))
  assert_true(
    @block.range("Cyrillic Supplement") == Some(('\u{0500}', '\u{052F}')),
  )
  assert_true(@block.range("no such block") == None)
  assert_true(@block.range("") == None)
}

///|
test "block on the usual suspects" {
  assert_eq(@block.block('a'), Some("Basic Latin"))
  assert_eq(@block.block('中'), Some("CJK Unified Ideographs"))
  assert_eq(@block.block('\u{1F600}'), Some("Emoticons"))
  assert_eq(@block.block('\u{2FE0}'), None)
  assert_eq(
    @block.block('\u{10FFFF}'),
    Some("Supplementary Private Use Area-B"),
  )
}

///|
test "version" {
  assert_true(@block.version() == "17.0.0")
}
