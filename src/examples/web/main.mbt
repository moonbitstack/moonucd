///|
/// Inspect a single character and return its facts as a JSON object. The page
/// calls this to fill the character inspector.
pub fn inspect(ch : Char) -> String {
  let cp = ch.to_int()
  let sb = StringBuilder()
  let mut first = true
  let field = fn(k : String, v : String) {
    if !first {
      sb.write_char(',')
    }
    first = false
    sb.write_char('"')
    sb.write_string(k)
    sb.write_string("\":")
    sb.write_string(v)
  }
  let strf = fn(k : String, v : String) {
    field(k, "\"" + json_escape(v) + "\"")
  }
  sb.write_char('{')
  strf("char", char_display(ch))
  strf("codepoint", "U+" + hexn(cp, if cp <= 0xFFFF { 4 } else { 6 }))
  strf("utf8", utf8(cp))
  strf("utf16", utf16(cp))
  let cat = @moonucd.category(ch)
  strf("category", cat.to_string())
  strf("categoryName", category_name(cat))
  strf("bidi", @moonucd.bidi(ch).to_string())
  match @moonucd.numeric(ch) {
    Some(@moonucd.Decimal) => strf("numeric", "Decimal")
    Some(@moonucd.Digit) => strf("numeric", "Digit")
    Some(@moonucd.Numeric) => strf("numeric", "Numeric")
    None => field("numeric", "null")
  }
  field(
    "emoji",
    if @moonucd.has(ch, @moonucd.Emoji) {
      "true"
    } else {
      "false"
    },
  )
  field(
    "extPict",
    if @moonucd.has(ch, @moonucd.ExtendedPictographic) {
      "true"
    } else {
      "false"
    },
  )
  match @age.age(ch) {
    Some((ma, mi)) => strf("age", ma.to_string() + "." + mi.to_string())
    None => field("age", "null")
  }
  match @block.block(ch) {
    Some(b) => strf("block", b)
    None => field("block", "null")
  }
  match @name.name(ch) {
    Some(n) => strf("name", n)
    None => field("name", "null")
  }
  let sc = @script.script(ch)
  strf("script", sc.to_string())
  strf("extensions", join_scripts(@script.extensions(ch)))
  strf("eaw", @width.east_asian_width(ch).to_string())
  field("width", @width.width(ch).to_string())
  let s = ch.to_string()
  strf("nfc", @normalize.normalize(@normalize.NFC, s))
  strf("nfd", @normalize.normalize(@normalize.NFD, s))
  strf("nfkc", @normalize.normalize(@normalize.NFKC, s))
  strf("nfkd", @normalize.normalize(@normalize.NFKD, s))
  field(
    "isNFC",
    if @normalize.is_normalized(@normalize.NFC, s) {
      "true"
    } else {
      "false"
    },
  )
  strf("lb", @linebreak.lb_property(ch).to_string())
  strf("linebreaks", @linebreak.linebreaks(s).join(" | "))
  sb.write_char('}')
  sb.to_string()
}

///|
/// Segment a string and return grapheme clusters, words and sentences as JSON.
pub fn seg(s : String) -> String {
  let sb = StringBuilder()
  sb.write_char('{')
  sb.write_string("\"grapheme\":")
  json_array(sb, @segment.grapheme_clusters(s))
  sb.write_string(",\"words\":")
  json_array(sb, @segment.words(s))
  sb.write_string(",\"sentences\":")
  json_array(sb, @segment.sentences(s))
  sb.write_char('}')
  sb.to_string()
}

///|
/// Break a string into lines and return the segments as a JSON array.
pub fn lb(s : String) -> String {
  let sb = StringBuilder()
  sb.write_string("{\"linebreaks\":")
  json_array(sb, @linebreak.linebreaks(s))
  sb.write_char('}')
  sb.to_string()
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

///|
fn json_array(sb : StringBuilder, items : Array[String]) -> Unit {
  sb.write_char('[')
  for i, it in items {
    if i > 0 {
      sb.write_string(",")
    }
    sb.write_char('"')
    sb.write_string(json_escape(it))
    sb.write_char('"')
  }
  sb.write_char(']')
}

///|
fn char_display(ch : Char) -> String {
  let c = ch.to_int()
  if c < 0x20 || c == 0x7F {
    "<control>"
  } else {
    ch.to_string()
  }
}

///|
fn category_name(c : @moonucd.Category) -> String {
  match c {
    @moonucd.Lu => "Letter, uppercase"
    @moonucd.Ll => "Letter, lowercase"
    @moonucd.Lt => "Letter, titlecase"
    @moonucd.Lm => "Letter, modifier"
    @moonucd.Lo => "Letter, other"
    @moonucd.Mn => "Mark, nonspacing"
    @moonucd.Mc => "Mark, spacing combining"
    @moonucd.Me => "Mark, enclosing"
    @moonucd.Nd => "Number, decimal digit"
    @moonucd.Nl => "Number, letter"
    @moonucd.No => "Number, other"
    @moonucd.Pc => "Punctuation, connector"
    @moonucd.Pd => "Punctuation, dash"
    @moonucd.Ps => "Punctuation, open"
    @moonucd.Pe => "Punctuation, close"
    @moonucd.Pi => "Punctuation, initial quote"
    @moonucd.Pf => "Punctuation, final quote"
    @moonucd.Po => "Punctuation, other"
    @moonucd.Sm => "Symbol, math"
    @moonucd.Sc => "Symbol, currency"
    @moonucd.Sk => "Symbol, modifier"
    @moonucd.So => "Symbol, other"
    @moonucd.Zs => "Separator, space"
    @moonucd.Zl => "Separator, line"
    @moonucd.Zp => "Separator, paragraph"
    @moonucd.Cc => "Other, control"
    @moonucd.Cf => "Other, format"
    @moonucd.Cs => "Other, surrogate"
    @moonucd.Co => "Other, private use"
    @moonucd.Cn => "Other, not assigned"
  }
}

///|
fn json_escape(s : String) -> String {
  let sb = StringBuilder()
  for ch in s {
    let c = ch.to_int()
    if ch == '"' {
      sb.write_string("\\\"")
    } else if ch == '\\' {
      sb.write_string("\\\\")
    } else if ch == '\n' {
      sb.write_string("\\n")
    } else if ch == '\r' {
      sb.write_string("\\r")
    } else if ch == '\t' {
      sb.write_string("\\t")
    } else if c < 0x20 {
      sb.write_string("\\u00" + hexn(c, 2))
    } else {
      sb.write_char(ch)
    }
  }
  sb.to_string()
}

///|
fn hexn(v : Int32, n : Int32) -> String {
  let d : Array[Char] = [
    '0', '1', '2', '3', '4', '5', '6', '7', '8', '9', 'A', 'B', 'C', 'D', 'E', 'F',
  ]
  let sb = StringBuilder()
  let mut i = n - 1
  while i >= 0 {
    sb.write_char(d[(v >> (i * 4)) & 0xF])
    i = i - 1
  }
  sb.to_string()
}

///|
fn utf8(cp : Int32) -> String {
  let parts : Array[String] = []
  if cp < 0x80 {
    parts.push(hexn(cp, 2))
  } else if cp < 0x800 {
    parts.push(hexn(0xC0 | (cp >> 6), 2))
    parts.push(hexn(0x80 | (cp & 0x3F), 2))
  } else if cp < 0x10000 {
    parts.push(hexn(0xE0 | (cp >> 12), 2))
    parts.push(hexn(0x80 | ((cp >> 6) & 0x3F), 2))
    parts.push(hexn(0x80 | (cp & 0x3F), 2))
  } else {
    parts.push(hexn(0xF0 | (cp >> 18), 2))
    parts.push(hexn(0x80 | ((cp >> 12) & 0x3F), 2))
    parts.push(hexn(0x80 | ((cp >> 6) & 0x3F), 2))
    parts.push(hexn(0x80 | (cp & 0x3F), 2))
  }
  join_hex(parts)
}

///|
fn join_hex(parts : Array[String]) -> String {
  let sb = StringBuilder()
  for i, p in parts {
    if i > 0 {
      sb.write_char(' ')
    }
    sb.write_string(p)
  }
  sb.to_string()
}

///|
fn utf16(cp : Int32) -> String {
  if cp < 0x10000 {
    hexn(cp, 4)
  } else {
    let c = cp - 0x10000
    hexn(0xD800 | (c >> 10), 4) + " " + hexn(0xDC00 | (c & 0x3FF), 4)
  }
}

///|
/// Keep the inspector functions linked and reachable from the page's script.
fn main {
  reg_char_fn("moonucd_inspect", inspect)
  reg_str_fn("moonucd_seg", seg)
  reg_str_fn("moonucd_lb", lb)
}
