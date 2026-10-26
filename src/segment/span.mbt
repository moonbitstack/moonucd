///|
/// The span `[start, end)` of the piece holding the UTF-16 offset `at`, given
/// the boundaries between code points; `(at, at)` when `at` is outside `s`.
fn span_at(
  s : StringView,
  at : Int32,
  bounds : (Array[Int32]) -> Array[Bool],
) -> (Int32, Int32) {
  if at < 0 || at >= s.length() {
    return (at, at)
  }
  let cps : Array[Int32] = []
  let offsets : Array[Int32] = []
  let mut offset = 0
  for ch in s {
    cps.push(ch.to_int())
    offsets.push(offset)
    offset += ch.utf16_len()
  }
  offsets.push(offset)
  let breaks = bounds(cps)
  let mut start = 0
  for i in 0..<cps.length() {
    let end = if i + 1 < cps.length() && !breaks[i] {
      -1
    } else {
      offsets[i + 1]
    }
    if end < 0 {
      continue
    }
    if at < end {
      return (offsets[start], end)
    }
    start = i + 1
  }
  (at, at)
}

///|
/// The grapheme cluster holding the UTF-16 offset `at`, as `(start, end)`:
/// where a cursor lands when it moves one user-perceived character.
pub fn grapheme_at(s : StringView, at : Int32) -> (Int32, Int32) {
  span_at(s, at, grapheme_boundaries)
}

///|
/// The word, or run of spaces or punctuation, holding the UTF-16 offset
/// `at`, as `(start, end)`: what a double click selects.
pub fn word_at(s : StringView, at : Int32) -> (Int32, Int32) {
  span_at(s, at, word_boundaries)
}
