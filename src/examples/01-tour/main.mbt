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
  let digits = @moonucd.Nd.ranges()
  let (lo, hi) = digits[0]
  println("decimal digits in \{digits.length()} ranges, the first \{lo}..\{hi}")
  println("K folds with \{@moonucd.fold_orbit('K').length()} characters")
  println("Unicode \{@moonucd.version()}")
}
