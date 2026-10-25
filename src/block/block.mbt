///|
/// The version of the Unicode Character Database the tables come from.
pub fn version() -> String {
  ucd_version
}

///|
/// The block `ch` belongs to, or `None` for the code points that sit in no
/// block at all.
pub fn block(ch : Char) -> String? {
  match find_run(block_starts, block_ends, ch.to_int()) {
    Some(i) => Some(block_names[i])
    None => None
  }
}

///|
/// The first and last code point of the block called `name`, matched the
/// loose way of UAX #44 (LM3): case, spaces, underscores, hyphens and a
/// leading "is" are ignored.
pub fn range(name : StringView) -> (Char, Char)? {
  match find_key(name) {
    Some(i) => {
      let a = block_starts[loose_values[i]]
      let b = block_ends[loose_values[i]]
      Some((a.unsafe_to_char(), b.unsafe_to_char()))
    }
    None => None
  }
}

///|
/// The loose key of `name`: UAX #44 LM3 without the leading "is", which is
/// only ever stripped from what a caller asks for, never from the table.
fn loose_key(name : StringView) -> String {
  let out = StringBuilder()
  for ch in name {
    if ch != ' ' && ch != '\t' && ch != '_' && ch != '-' {
      out.write_char(ch.to_ascii_lowercase())
    }
  }
  let key = out.to_string()
  if key.has_prefix("is") {
    key[2:].to_owned()
  } else {
    key
  }
}

///|
fn find_key(name : StringView) -> Int32? {
  let key = loose_key(name)
  let mut a = 0
  let mut b = loose_keys.length()
  while a < b {
    let mid = (a + b) / 2
    if compare_key(loose_keys[mid], key) < 0 {
      a = mid + 1
    } else {
      b = mid
    }
  }
  if a < loose_keys.length() && compare_key(loose_keys[a], key) == 0 {
    Some(a)
  } else {
    None
  }
}

///|
/// Lexicographic by code unit — the dictionary order the keys are stored in.
/// (String's own Compare is shortlex, which would not match.)
fn compare_key(a : String, b : String) -> Int32 {
  let n = if a.length() < b.length() { a.length() } else { b.length() }
  for i in 0..<n {
    let x = a.unsafe_get(i)
    let y = b.unsafe_get(i)
    if x != y {
      return if x < y { -1 } else { 1 }
    }
  }
  if a.length() < b.length() {
    -1
  } else if a.length() > b.length() {
    1
  } else {
    0
  }
}

///|
/// The run holding `cp`, by binary search over sorted, disjoint runs: the last
/// run that starts at or before `cp`, then a check that it also ends at or
/// after `cp`.
fn find_run(
  starts : FixedArray[Int32],
  ends : FixedArray[Int32],
  cp : Int32,
) -> Int32? {
  let mut a = 0
  let mut b = starts.length()
  while a < b {
    let mid = (a + b) / 2
    if starts[mid] <= cp {
      a = mid + 1
    } else {
      b = mid
    }
  }
  if a > 0 {
    let i = a - 1
    if ends[i] >= cp {
      return Some(i)
    }
  }
  None
}
