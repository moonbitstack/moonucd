///|
/// Every answer the library gives about a code point, one line each, for a
/// second implementation to read back: the differential run in CI compares
/// this table with Python's unicodedata2 and with unicode-js, and the counts
/// land in the README's conformance table. Fields are tab separated, in this
/// order:
///
///   code point, category, combining class, bidi class, East Asian Width,
///   terminal cells, numeric type, numeric value, script, block, the four
///   single-character case forms, line-break class, name, and the four
///   normalization forms of the character.
///
/// An empty field means the character has none. The case forms and the
/// normalization forms are written as upper-case hexadecimal code points, one
/// after another separated by spaces, so that a tab or a newline in the data
/// cannot be mistaken for a field boundary. `*` in a normalization column
/// means the character is unassigned, where the four forms are the character
/// itself and there is nothing to compare.
fn main {
  let mut chunk = StringBuilder()
  let mut count = 0
  let mut fresh = true
  for cp in 0..<0x110000 {
    if cp >= 0xD800 && cp <= 0xDFFF {
      continue
    }
    let ch = cp.unsafe_to_char()
    let unassigned = @moonucd.category(ch) is Cn
    let fields : Array[String] = [
      cp.to_string(),
      @moonucd.category(ch).to_string(),
      @normalize.combining(ch).to_string(),
      @moonucd.bidi(ch).to_string(),
      @width.east_asian_width(ch).to_string(),
      @width.width(ch).to_string(),
      match @moonucd.numeric(ch) {
        Some(Decimal) => "Decimal"
        Some(Digit) => "Digit"
        Some(Numeric) => "Numeric"
        None => ""
      },
      match @moonucd.numeric_value(ch) {
        Some(v) => v.to_string()
        None => ""
      },
      @script.script(ch).to_string(),
      match @block.block(ch) {
        Some(b) => b
        None => ""
      },
      hex(@moonucd.simple_upper(ch).to_int()),
      hex(@moonucd.simple_lower(ch).to_int()),
      hex(@moonucd.simple_title(ch).to_int()),
      hex(@moonucd.simple_fold(ch).to_int()),
      @linebreak.lb_property(ch).to_string(),
      match @name.name(ch) {
        Some(n) => n
        None => ""
      },
      if unassigned {
        "*"
      } else {
        spell(@normalize.normalize(NFC, ch.to_string()))
      },
      if unassigned {
        "*"
      } else {
        spell(@normalize.normalize(NFD, ch.to_string()))
      },
      if unassigned {
        "*"
      } else {
        spell(@normalize.normalize(NFKC, ch.to_string()))
      },
      if unassigned {
        "*"
      } else {
        spell(@normalize.normalize(NFKD, ch.to_string()))
      },
    ]
    if !fresh {
      chunk.write_char('\n')
    }
    fresh = false
    for i, field in fields {
      if i > 0 {
        chunk.write_char('\t')
      }
      chunk.write_string(field)
    }
    count += 1
    if count % 4096 == 0 {
      println(chunk.to_string())
      chunk = StringBuilder()
      fresh = true
    }
  }
  if !fresh {
    println(chunk.to_string())
  }
}

///|
/// A code point as upper-case hexadecimal, at least four digits.
fn hex(cp : Int32) -> String {
  cp.to_string(radix=16).to_upper().pad_start(4, '0')
}

///|
/// A string as its code points in hexadecimal, separated by spaces.
fn spell(text : String) -> String {
  let parts = []
  for ch in text {
    parts.push(hex(ch.to_int()))
  }
  parts.join(" ")
}
