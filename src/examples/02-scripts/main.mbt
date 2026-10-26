///|
fn main {
  println("Scripts — which writing system a character belongs to.")
  for ch in ['A', '中', 'あ', 'ﷺ'] {
    let s = @script.script(ch)
    let exts = join_scripts(@script.extensions(ch))
    println("  \{ch.escape()}: \{s}  (extensions: \{exts})")
  }
  match @script.Script::of("Hiragana") {
    Some(s) => println("  Script::of(\"Hiragana\") = \{s}")
    None => println("  Script::of(\"Hiragana\") = none")
  }
}

///|
fn join_scripts(scripts : Array[@script.Script]) -> String {
  let out = StringBuilder()
  for i, s in scripts {
    if i > 0 {
      out.write_string(", ")
    }
    out.write_string(s.to_string())
  }
  out.to_string()
}
