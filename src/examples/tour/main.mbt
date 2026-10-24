///|
fn main {
  let word = "Straße"
  println("\{word}: upper \{@moonucd.upper(word)}, fold \{@moonucd.fold(word)}")
  println("ΟΔΟΣ lowered: \{@moonucd.lower("ΟΔΟΣ")}")
  for ch in ['A', 'ǅ', '٣', '中', ' ', '€'] {
    let num = match @moonucd.numeric(ch) {
      Some(Decimal) => ", decimal digit"
      Some(_) => ", numeric"
      None => ""
    }
    let alpha = if @moonucd.has(ch, Alphabetic) { ", alphabetic" } else { "" }
    println("\{ch.escape()}: \{@moonucd.category(ch)}\{alpha}\{num}")
  }
  println("Unicode \{@moonucd.version()}")
}
