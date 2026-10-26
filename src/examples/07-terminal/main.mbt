///|
/// `text` cut into lines no wider than `columns` terminal cells, breaking where
/// UAX #14 allows and always where it requires. A piece wider than `columns`
/// on its own stays whole.
fn wrap(text : String, columns : Int32) -> Array[String] {
  let lines = []
  let mut start = 0
  let mut fit = 0
  let line = fn(a, b) { text.view(start_offset=a, end_offset=b).trim_end() }
  for brk in [..@linebreak.breaks(text), (text.length(), true)] {
    let (at, must) = brk
    if fit > start && @width.text_width(line(start, at)) > columns {
      lines.push(line(start, fit).to_owned())
      start = fit
    }
    fit = at
    if must {
      lines.push(line(start, at).to_owned())
      start = at
    }
  }
  lines
}

///|
/// `text` cut down to `columns` cells with a trailing ellipsis, never splitting
/// a user-perceived character.
fn truncate(text : String, columns : Int32) -> String {
  if @width.text_width(text) <= columns {
    return text
  }
  let out = StringBuilder()
  let mut used = 1
  for g in @segment.grapheme_clusters(text) {
    used += @width.text_width(g)
    if used > columns {
      break
    }
    out.write_string(g)
  }
  out.write_string("…")
  out.to_string()
}

///|
/// `text` padded with spaces to `columns` cells.
fn pad(text : String, columns : Int32) -> String {
  text + " ".repeat(columns - @width.text_width(text))
}

///|
fn main {
  let text = "MoonBit 把 Unicode 的断行规则用在终端里：English words wrap at spaces, 中文在字与字之间断开。"
  println("wrap at 24 cells")
  println("+" + "-".repeat(24) + "+")
  for l in wrap(text, 24) {
    println("|" + pad(l, 24) + "|")
  }
  println("+" + "-".repeat(24) + "+")
  println("")
  println("truncate to 12 cells")
  for
    s in [
      "Hello, world!", "你好，世界！欢迎光临", "🇨🇳🇬🇧🇫🇷🇩🇪🇯🇵🇺🇸🇮🇳",
      "e\u{301}e\u{301}e\u{301}e\u{301}e\u{301}e\u{301}e\u{301}e\u{301}e\u{301}e\u{301}e\u{301}e\u{301}e\u{301}",
    ] {
    println("  [" + pad(truncate(s, 12), 12) + "]")
  }
}
