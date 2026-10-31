///|
/// The ranges the category covers: closed intervals, ascending by their
/// start, neighbours joined, so that a matcher can hold a set of characters
/// as a list instead of a predicate.
///
/// ```mbt check
/// test {
///   let digits = @moonucd.Nd.ranges()
///   assert_eq(digits[0], (0x30, 0x39))
///   assert_eq(digits[1], (0x660, 0x669))
/// }
/// ```
pub fn Category::ranges(self : Category) -> Array[(Int32, Int32)] {
  let mut i = 0
  while categories[i] != self {
    i += 1
  }
  slice_ranges(category_ranges, category_ranges_offsets, i)
}

///|
/// The ranges the binary property covers: closed intervals, ascending by their
/// start, neighbours joined.
///
/// ```mbt check
/// test {
///   let dashes = @moonucd.Dash.ranges()
///   assert_eq(dashes[0], (0x2D, 0x2D))
///   assert_true(dashes.contains((0x2010, 0x2015)))
/// }
/// ```
pub fn Property::ranges(self : Property) -> Array[(Int32, Int32)] {
  let mut i = 0
  while properties[i] != self {
    i += 1
  }
  slice_ranges(property_ranges, property_ranges_offsets, i)
}

///|
/// The ranges a table keeps for entry `i`, from the flat start-and-end list the
/// generator writes and the offsets that cut it.
fn slice_ranges(
  table : FixedArray[Int32],
  offsets : FixedArray[Int32],
  i : Int32,
) -> Array[(Int32, Int32)] {
  let out = []
  let mut k = offsets[i]
  let stop = offsets[i + 1]
  while k < stop {
    out.push((table[k], table[k + 1]))
    k += 2
  }
  out
}
