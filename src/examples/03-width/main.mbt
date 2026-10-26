///|
fn main {
  println("Width — how many terminal cells a character occupies.")
  for ch in ['A', '中', '🚀', '　'] {
    println(
      "  \{ch.escape()}: width \{@width.width(ch)}, east_asian_width \{@width.east_asian_width(ch)}",
    )
  }
  let line = "Hello 世界 🚀"
  println("  text_width(\"\{line}\") = \{@width.text_width(line)}")
}
