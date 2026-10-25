///|
/// The version of the Unicode Character Database the tables come from.
pub fn version() -> String {
  ucd_version
}

///|
/// When `ch` was first assigned, as the (major, minor) Unicode version —
/// `(1, 1)` for the original repertoire, `(17, 0)` for the newest — or
/// `None` for code points that are still unassigned.
pub fn age(ch : Char) -> (Int32, Int32)? {
  match find_run(age_starts, age_ends, ch.to_int()) {
    Some(i) => Some((age_major[i], age_minor[i]))
    None => None
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
