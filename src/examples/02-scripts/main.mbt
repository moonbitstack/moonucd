///|
fn main {
  println("Scripts — which writing system a character belongs to.")
  for ch in ['A', '中', 'あ', 'ﷺ'] {
    let s = @script.script(ch)
    let exts = @script.extensions(ch).map(x => x.to_string()).join(", ")
    println("  \{ch.escape()}: \{s}  (extensions: \{exts})")
  }
  match @script.Script::of("Hiragana") {
    Some(s) => println("  Script::of(\"Hiragana\") = \{s}")
    None => println("  Script::of(\"Hiragana\") = none")
  }
}
