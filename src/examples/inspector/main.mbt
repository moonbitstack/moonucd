///|
/// Everything the documentation site's inspector shows for the code point
/// `cp`, as a JSON object; `null` when `cp` is not a Unicode scalar value.
pub fn inspect(cp : Int32) -> String {
  guard cp.to_char() is Some(ch) else { return "null" }
  facts(ch).stringify()
}

///|
/// The grapheme clusters, words, sentences and line-break pieces of `s`, as a
/// JSON object of four string arrays.
pub fn pieces(s : String) -> String {
  let json : Json = {
    "grapheme": Json(@segment.grapheme_clusters(s)),
    "words": Json(@segment.words(s)),
    "sentences": Json(@segment.sentences(s)),
    "linebreaks": Json(@linebreak.linebreaks(s)),
  }
  json.stringify()
}

///|
fn facts(ch : Char) -> Json {
  let cp = ch.to_int()
  let s = ch.to_string()
  let optional = fn(v : String?) {
    match v {
      Some(v) => Json(v)
      None => Json::null()
    }
  }
  {
    "char": Json(if cp < 0x20 || cp == 0x7F { "<control>" } else { s }),
    "codepoint": Json("U+" + hex(cp, if cp <= 0xFFFF { 4 } else { 6 })),
    "utf8": Json(@utf8.encode(s).iter().map(b => hex(b.to_int(), 2)).join(" ")),
    "utf16": Json(utf16(cp)),
    "category": Json(@moonucd.category(ch).to_string()),
    "categoryName": Json(category_name(@moonucd.category(ch))),
    "bidi": Json(@moonucd.bidi(ch).to_string()),
    "numeric": optional(
      @moonucd.numeric(ch).map(n => {
        match n {
          Decimal => "Decimal"
          Digit => "Digit"
          Numeric => "Numeric"
        }
      }),
    ),
    "emoji": Json(@moonucd.has(ch, Emoji)),
    "extPict": Json(@moonucd.has(ch, ExtendedPictographic)),
    "age": optional(@age.age(ch).map(v => "\{v.0}.\{v.1}")),
    "block": optional(@block.block(ch)),
    "name": optional(@name.name(ch)),
    "script": Json(@script.script(ch).to_string()),
    "extensions": Json(
      @script.extensions(ch).iter().map(x => x.to_string()).join(", "),
    ),
    "eaw": Json(@width.east_asian_width(ch).to_string()),
    "width": Json(@width.width(ch)),
    "nfc": Json(@normalize.normalize(NFC, s)),
    "nfd": Json(@normalize.normalize(NFD, s)),
    "nfkc": Json(@normalize.normalize(NFKC, s)),
    "nfkd": Json(@normalize.normalize(NFKD, s)),
    "isNFC": Json(@normalize.is_normalized(NFC, s)),
    "lb": Json(@linebreak.lb_property(ch).to_string()),
  }
}

///|
fn hex(v : Int32, digits : Int32) -> String {
  v.to_string(radix=16).to_upper().pad_start(digits, '0')
}

///|
fn utf16(cp : Int32) -> String {
  if cp < 0x10000 {
    return hex(cp, 4)
  }
  let c = cp - 0x10000
  hex(0xD800 | (c >> 10), 4) + " " + hex(0xDC00 | (c & 0x3FF), 4)
}

///|
fn category_name(c : @moonucd.Category) -> String {
  match c {
    Lu => "Letter, uppercase"
    Ll => "Letter, lowercase"
    Lt => "Letter, titlecase"
    Lm => "Letter, modifier"
    Lo => "Letter, other"
    Mn => "Mark, nonspacing"
    Mc => "Mark, spacing combining"
    Me => "Mark, enclosing"
    Nd => "Number, decimal digit"
    Nl => "Number, letter"
    No => "Number, other"
    Pc => "Punctuation, connector"
    Pd => "Punctuation, dash"
    Ps => "Punctuation, open"
    Pe => "Punctuation, close"
    Pi => "Punctuation, initial quote"
    Pf => "Punctuation, final quote"
    Po => "Punctuation, other"
    Sm => "Symbol, math"
    Sc => "Symbol, currency"
    Sk => "Symbol, modifier"
    So => "Symbol, other"
    Zs => "Separator, space"
    Zl => "Separator, line"
    Zp => "Separator, paragraph"
    Cc => "Other, control"
    Cf => "Other, format"
    Cs => "Other, surrogate"
    Co => "Other, private use"
    Cn => "Other, not assigned"
  }
}
