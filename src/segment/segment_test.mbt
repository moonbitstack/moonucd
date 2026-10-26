///|
/// Replay one official break test file against a boundary function.
fn replay(
  name : String,
  text : String,
  bounds : FixedArray[Int32],
  expected : String,
  boundaries : (Array[Int32]) -> Array[Bool],
) -> Unit raise {
  let cps : Array[Int32] = []
  for ch in text {
    cps.push(ch.to_int())
  }
  let exp : Array[Bool] = []
  for ch in expected {
    exp.push(ch == '1')
  }
  let count = bounds.length() - 1
  let mut pos = 0
  for i = 0; i < count; i = i + 1 {
    let case : Array[Int32] = []
    for k = bounds[i]; k < bounds[i + 1]; k = k + 1 {
      case.push(cps[k])
    }
    let got = boundaries(case)
    for k = 0; k < case.length() - 1; k = k + 1 {
      if got[k] != exp[pos + k] {
        fail(
          "\{name} case \{i}, boundary \{k}: got \{got[k]}, want \{exp[pos + k]}",
        )
      }
    }
    pos += case.length() - 1
  }
}

///|
test "grapheme cluster boundaries (GraphemeBreakTest.txt)" {
  replay(
    "grapheme", grapheme_text, grapheme_bounds, grapheme_expected, @segment.grapheme_boundaries,
  )
}

///|
test "word boundaries (WordBreakTest.txt)" {
  replay(
    "word", word_text, word_bounds, word_expected, @segment.word_boundaries,
  )
}

///|
test "sentence boundaries (SentenceBreakTest.txt)" {
  replay(
    "sentence", sentence_text, sentence_bounds, sentence_expected, @segment.sentence_boundaries,
  )
}

///|
test "version" {
  assert_eq(@segment.version(), "17.0.0")
}

///|
test "grapheme clusters" {
  // A combining acute accent stays with the letter it follows.
  assert_eq(@segment.grapheme_clusters("A\u{0301}b"), ["A\u{0301}", "b"])
  // CRLF is a single cluster.
  assert_eq(@segment.grapheme_clusters("a\r\nb"), ["a", "\r\n", "b"])
  // A regional indicator pair is one cluster, so three leave one on its own.
  assert_eq(@segment.grapheme_clusters("\u{1F1E6}\u{1F1E7}\u{1F1E8}"), [
    "\u{1F1E6}\u{1F1E7}", "\u{1F1E8}",
  ])
  assert_eq(@segment.grapheme_clusters("").length(), 0)
}

///|
test "words" {
  assert_eq(@segment.words("Hello, world!"), ["Hello", ",", " ", "world", "!"])
  // A number keeps its internal separator.
  assert_eq(@segment.words("3.14"), ["3.14"])
  // A full stop between letters only joins them when a letter follows directly,
  // so "Mr." splits when a space comes next.
  assert_eq(@segment.words("Mr. Smith"), ["Mr", ".", " ", "Smith"])
  assert_eq(@segment.words("e.g. this"), ["e.g", ".", " ", "this"])
  assert_eq(@segment.words("").length(), 0)
}

///|
test "sentences" {
  assert_eq(@segment.sentences("One. Two!"), ["One. ", "Two!"])
  // A lowercase word after a full stop continues the sentence.
  assert_eq(@segment.sentences("etc. more"), ["etc. more"])
  assert_eq(@segment.sentences("").length(), 0)
}

///|
test "property values" {
  assert_eq(@segment.gcb_property('\u{0301}') == @segment.Extend, true)
  assert_eq(@segment.wb_property('a') == @segment.ALetter, true)
  assert_eq(@segment.sb_property('.') == @segment.ATerm, true)
}

///|
test "the cluster and the word at an offset" {
  let s = "e\u{0301}x 🇯🇵!"
  assert_eq(@segment.grapheme_at(s, 0), (0, 2))
  assert_eq(@segment.grapheme_at(s, 1), (0, 2))
  assert_eq(@segment.grapheme_at(s, 4), (4, 8))
  assert_eq(@segment.grapheme_at(s, 99), (99, 99))
  let words = "hello, world"
  assert_eq(@segment.word_at(words, 2), (0, 5))
  assert_eq(@segment.word_at(words, 9), (7, 12))
  assert_eq(@segment.word_at(words, 5), (5, 6))
}
