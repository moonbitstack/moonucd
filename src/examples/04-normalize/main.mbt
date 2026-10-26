///|
fn main {
  println("Normalization — the four forms of UAX #15.")
  println("  \"Å\"")
  println("    NFD  = \{@normalize.normalize(@normalize.NFD, "Å")}")
  println("    NFC  = \{@normalize.normalize(@normalize.NFC, "Å")}")
  println("  \"①\" (circled digit one)")
  println("    NFKC = \{@normalize.normalize(@normalize.NFKC, "①")}")
  println(
    "  is_normalized(NFC, \"Å\") = \{@normalize.is_normalized(@normalize.NFC, "Å")}",
  )
  println("  decomposition('Å')      = \{@normalize.decomposition('Å')}")
}
