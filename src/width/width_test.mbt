///|
/// FNV-1a over `width` for every code point, the same walk over wcwidth 0.2.14.
fn width_digest_walk() -> UInt32 {
  let mut h : UInt32 = 0x811C9DC5
  for cp in 0..<0x110000 {
    let w = @width.width(cp.unsafe_to_char())
    let uw = w.reinterpret_as_uint()
    h = (h ^ uw) * 0x01000193
  }
  h
}

///|
/// FNV-1a over `east_asian_width` for every code point, the same walk over
/// unicodedata's `ea` property.
fn eaw_digest_walk() -> UInt32 {
  let mut h : UInt32 = 0x811C9DC5
  for cp in 0..<0x110000 {
    let e = eaw_digest_code(@width.east_asian_width(cp.unsafe_to_char()))
    h = (h ^ e) * 0x01000193
  }
  h
}

///|
/// The digest folds the `ea` letter as A=0 F=1 H=2 N=3 Na=4 W=5.
fn eaw_digest_code(e : @width.Eaw) -> UInt32 {
  match e {
    @width.Eaw::A => 0
    @width.Eaw::F => 1
    @width.Eaw::H => 2
    @width.Eaw::N => 3
    @width.Eaw::Na => 4
    @width.Eaw::W => 5
  }
}

///|
test "width matches wcwidth 0.2.14 on every code point" {
  assert_eq(width_digest_walk(), width_digest)
}

///|
test "east_asian_width matches unicodedata on every code point" {
  assert_eq(eaw_digest_walk(), eaw_digest)
}

///|
test "version is the Unicode 17.0.0 database" {
  assert_eq(@width.version(), "17.0.0")
}

///|
test "width on the usual suspects" {
  assert_eq(@width.width('A'), 1)
  assert_eq(@width.width('一'), 2)
  assert_eq(@width.width('\u{200D}'), 0)
  assert_eq(@width.width('\u{0301}'), 0)
  assert_eq(@width.width('\u{0001}'), -1)
  assert_eq(@width.width('\u{007F}'), -1)
  assert_eq(@width.width('\u{00A0}'), 1)
  assert_eq(@width.width('\u{2E80}'), 2)
}

///|
test "east_asian_width on the usual suspects" {
  assert_true(@width.east_asian_width('A') == @width.Eaw::Na)
  assert_true(@width.east_asian_width('一') == @width.Eaw::W)
  assert_true(@width.east_asian_width('\u{00A1}') == @width.Eaw::A)
  assert_true(@width.east_asian_width(' ') == @width.Eaw::Na)
  assert_true(@width.east_asian_width('\u{0378}') == @width.Eaw::N)
  assert_true(@width.east_asian_width('\u{2E80}') == @width.Eaw::W)
  assert_true(@width.east_asian_width('\u{1F600}') == @width.Eaw::W)
  assert_true(@width.east_asian_width('\u{FF01}') == @width.Eaw::F)
  assert_true(@width.east_asian_width('\u{1100}') == @width.Eaw::W)
}

///|
test "text_width matches wcswidth on the probe set" {
  for i in 0..<text_width_probes.length() {
    assert_eq(@width.text_width(text_width_probes[i]), text_width_expect[i])
  }
}

///|
test "text_width on hand-picked strings" {
  assert_eq(@width.text_width("hello"), 5)
  assert_eq(@width.text_width("世界"), 4)
  assert_eq(@width.text_width("1\u{FE0F}"), 2)
  assert_eq(@width.text_width("A\u{200D}"), 1)
  assert_eq(@width.text_width("🍵"), 2)
}

///|
test "ambiguous characters take the width asked for" {
  assert_eq(@width.width('α'), 1)
  assert_eq(@width.width('α', ambiguous=2), 2)
  assert_eq(@width.width('中', ambiguous=1), 2)
  assert_eq(@width.text_width("α中", ambiguous=2), 4)
  assert_eq(@width.text_width("α中"), 3)
}
