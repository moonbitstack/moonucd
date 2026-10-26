///|
fn main {
  println("Segmentation — grapheme clusters, words, sentences (UAX #29).")
  let flag = "🇯🇵"
  println("  grapheme_clusters(\"\{flag}a\"):")
  for g in @segment.grapheme_clusters("\{flag}a") {
    println("    [\{g}]")
  }
  println("  words(\"Mr. Smith said hi.\"):")
  for w in @segment.words("Mr. Smith said hi.") {
    println("    [\{w}]")
  }
  println("  sentences(\"Hello world. Goodbye!\"):")
  for s in @segment.sentences("Hello world. Goodbye!") {
    println("    [\{s}]")
  }
}
