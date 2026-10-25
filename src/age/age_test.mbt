///|

///|
/// FNV-1a over the results for every scalar value, the digest the same walk
/// over DerivedAge.txt gives.
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
test "age agrees with DerivedAge.txt on every code point" {
  let d = digest((ch, out) => {
    match @age.age(ch) {
      Some((major, minor)) => {
        out.push(major)
        out.push(minor)
      }
      None => {
        out.push(255)
        out.push(255)
      }
    }
  })
  assert_eq(d, age_digest)
}

///|
test "age on the usual suspects" {
  assert_eq(@age.age('a'), Some((1, 1)))
  assert_eq(@age.age('€'), Some((2, 1)))
  assert_eq(@age.age('😀'), Some((6, 1)))
  assert_eq(@age.age('\u{0870}'), Some((14, 0)))
  assert_eq(@age.age('\u{105C0}'), Some((16, 0)))
  assert_eq(@age.age('\u{0378}'), None)
  assert_eq(@age.age('\u{0E01}'), Some((1, 1)))
}

///|
test "version" {
  assert_true(@age.version() == "17.0.0")
}
