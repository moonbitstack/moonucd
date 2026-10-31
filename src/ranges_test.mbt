///|
/// FNV-1a over the ranges of every category, in the order the enum declares
/// them, the digest the ranges `unicodedata` gives produce.
test "category ranges agree with unicodedata on every code point" {
  let mut h : UInt32 = 0x811C9DC5
  for c in category_ranges_order {
    for (a, b) in c.ranges() {
      h = (h ^ a.reinterpret_as_uint()) * 0x01000193
      h = (h ^ b.reinterpret_as_uint()) * 0x01000193
    }
  }
  assert_eq(h, category_ranges_digest)
}

///|
test "the same over every binary property" {
  let mut h : UInt32 = 0x811C9DC5
  for p in property_ranges_order {
    for (a, b) in p.ranges() {
      h = (h ^ a.reinterpret_as_uint()) * 0x01000193
      h = (h ^ b.reinterpret_as_uint()) * 0x01000193
    }
  }
  assert_eq(h, property_ranges_digest)
}

///|
/// Closed, ascending, disjoint and not touching: the shape a caller can merge
/// against another set without sorting it first.
test "every category's ranges are in order, apart, and within the code space" {
  for c in category_ranges_order {
    let ranges = c.ranges()
    let mut prev : Int32 = -2
    for (a, b) in ranges {
      assert_true(a <= b)
      assert_true(a >= 0 && b <= 0x10FFFF)
      assert_true(a > prev)
      assert_true(a > prev + 1)
      prev = b
    }
  }
}

///|
test "the categories between them account for every code point once" {
  let mut covered : Int32 = 0
  for c in category_ranges_order {
    for (a, b) in c.ranges() {
      covered += b - a + 1
    }
  }
  assert_eq(covered, 0x110000)
}

///|
test "a range holds characters of its category at both ends" {
  for c in category_ranges_order {
    for (a, b) in c.ranges() {
      assert_true(@moonucd.category(a.unsafe_to_char()) == c)
      assert_true(@moonucd.category(b.unsafe_to_char()) == c)
    }
  }
}

///|
test "a range holds characters of its property at both ends, and none follows the end" {
  for p in property_ranges_order {
    for (a, b) in p.ranges() {
      assert_true(@moonucd.has(a.unsafe_to_char(), p))
      assert_true(@moonucd.has(b.unsafe_to_char(), p))
      if a > 0 {
        assert_true(!@moonucd.has((a - 1).unsafe_to_char(), p))
      }
      if b < 0x10FFFF {
        assert_true(!@moonucd.has((b + 1).unsafe_to_char(), p))
      }
    }
  }
}

///|
test "ranges on the usual suspects" {
  assert_eq(@moonucd.Nd.ranges()[0], (0x30, 0x39))
  assert_eq(@moonucd.Lu.ranges()[0], (0x41, 0x5A))
  assert_true(@moonucd.Dash.ranges().contains((0x2010, 0x2015)))
  let private_use = @moonucd.Co.ranges()
  assert_eq(private_use[0], (0xE000, 0xF8FF))
  assert_true(@moonucd.WhiteSpace.ranges().contains((0x20, 0x20)))
  assert_eq(@moonucd.Cn.ranges()[0], (0x378, 0x379))
}

///|
test "a code point inside a range and one in the gap between two" {
  let digits = @moonucd.Nd.ranges()
  let in_range = fn(cp : Int32) -> Bool {
    for (a, b) in digits {
      if a <= cp && cp <= b {
        return true
      }
    }
    false
  }
  assert_true(in_range('5'.to_int()))
  assert_true(!in_range(' '.to_int()))
}

///|
test "every call hands out a fresh array" {
  let ranges = @moonucd.Nd.ranges()
  ranges.clear()
  assert_true(@moonucd.Nd.ranges().length() > 0)
}
