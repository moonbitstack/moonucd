///|
fn main {
  println("Line breaking — where a line may wrap (UAX #14).")
  let text = "The quick 日本 fox"
  println("  linebreaks(\"\{text}\"):")
  for seg in @linebreak.linebreaks(text) {
    println("    [\{seg}]")
  }
  println("  lb_property(' ') = \{@linebreak.lb_property(' ')}")
  println("  lb_property('中') = \{@linebreak.lb_property('中')}")
}
