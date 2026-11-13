///|
/// Everything the documentation site's inspector shows for the code point
/// `cp`, as a JSON object; `null` when `cp` is not a Unicode scalar value.
pub fn inspect(cp : Int32) -> String {
  guard cp.to_char() is Some(ch) else { return "null" }
  facts(ch).stringify()
}

///|
/// Everything the pages draw for `text`, as one JSON object: the grapheme
/// clusters, words and sentences with their offsets and widths, where a line
/// may break and between which classes, the four normalization forms, and the
/// case forms of every character.
pub fn analyse(text : String) -> String {
  let json : Json = {
    "codepoints": Json(text.iter().count()),
    "utf16": Json(text.length()),
    "graphemes": graphemes(text),
    "words": pieces(text, @segment.words),
    "sentences": pieces(text, @segment.sentences),
    "narrow": Json(@width.text_width(text)),
    "wide": Json(@width.text_width(text, ambiguous=2)),
    "breaks": breaks(text),
    "nfc": spell(@normalize.normalize(NFC, text)),
    "nfd": spell(@normalize.normalize(NFD, text)),
    "nfkc": spell(@normalize.normalize(NFKC, text)),
    "nfkd": spell(@normalize.normalize(NFKD, text)),
    "isNFC": Json(@normalize.is_normalized(NFC, text)),
    "isNFD": Json(@normalize.is_normalized(NFD, text)),
    "chars": spell(text),
    "case": cases(text),
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
    "value": optional(@moonucd.numeric_value(ch).map(v => v.to_string())),
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
/// The grapheme clusters of `text`, each with the UTF-16 range it covers and
/// the cells a terminal gives it.
fn graphemes(text : String) -> Json {
  let out : Array[Json] = []
  let mut at = 0
  for cluster in @segment.grapheme_clusters(text) {
    let end = at + cluster.length()
    let first = cluster.iter().next()
    out.push({
      "text": Json(cluster),
      "start": Json(at),
      "end": Json(end),
      "gcb": Json(
        first
        .map(ch => @segment.gcb_property(ch).to_string())
        .unwrap_or("Other"),
      ),
      "width": Json(@width.text_width(cluster)),
      "wide": Json(@width.text_width(cluster, ambiguous=2)),
    })
    at = end
  }
  Json(out)
}

///|
/// The pieces `split` finds in `text`, each with the UTF-16 range it covers.
fn pieces(text : String, split : (StringView) -> Array[String]) -> Json {
  let out : Array[Json] = []
  let mut at = 0
  for piece in split(text) {
    let end = at + piece.length()
    out.push({ "text": Json(piece), "start": Json(at), "end": Json(end) })
    at = end
  }
  Json(out)
}

///|
/// Where `text` may break, with the line-break class on each side of the break
/// and whether the rule that allows it makes the break mandatory.
fn breaks(text : String) -> Json {
  let out : Array[Json] = []
  let chars = text.iter().collect()
  let offsets : Array[Int32] = []
  let mut at = 0
  for ch in chars {
    offsets.push(at)
    at += if ch.to_int() < 0x10000 { 1 } else { 2 }
  }
  for pair in @linebreak.breaks(text) {
    let (offset, mandatory) = pair
    let i = place(offsets, offset)
    out.push({
      "at": Json(offset),
      "mandatory": Json(mandatory),
      "before": Json(
        if i > 0 {
          @linebreak.lb_property(chars[i - 1]).to_string()
        } else {
          ""
        },
      ),
      "after": Json(
        if i < chars.length() {
          @linebreak.lb_property(chars[i]).to_string()
        } else {
          ""
        },
      ),
    })
  }
  Json(out)
}

///|
/// The first index of `offsets` whose offset is `at` or past it.
fn place(offsets : Array[Int32], at : Int32) -> Int32 {
  let mut i = 0
  while i < offsets.length() && offsets[i] < at {
    i += 1
  }
  i
}

///|
/// What the press reads for every character of `text`: the code point, its
/// combining class, and the decomposition the UCD lists.
fn spell(text : String) -> Json {
  let out : Array[Json] = []
  for ch in text {
    let cp = ch.to_int()
    out.push({
      "char": Json(
        if cp < 0x20 || cp == 0x7F {
          "<control>"
        } else {
          ch.to_string()
        },
      ),
      "cp": Json(cp),
      "hex": Json("U+" + hex(cp, if cp <= 0xFFFF { 4 } else { 6 })),
      "ccc": Json(@normalize.combining(ch)),
      "dec": Json(@normalize.decomposition(ch)),
      "hangul": Json(0xAC00 <= cp && cp <= 0xD7A3),
      "name": Json(
        match @name.name(ch) {
          Some(n) => n
          None => ""
        },
      ),
    })
  }
  Json(out)
}

///|
/// The case forms of every character of `text`, one character at a time: the
/// full mappings, the simple ones, and the class the simple fold joins.
fn cases(text : String) -> Json {
  let out : Array[Json] = []
  for ch in text {
    let s = ch.to_string()
    out.push({
      "char": Json(s),
      "upper": Json(@moonucd.upper(s)),
      "lower": Json(@moonucd.lower(s)),
      "title": Json(@moonucd.title(s)),
      "fold": Json(@moonucd.fold(s)),
      "simpleUpper": Json(@moonucd.simple_upper(ch).to_string()),
      "simpleLower": Json(@moonucd.simple_lower(ch).to_string()),
      "simpleTitle": Json(@moonucd.simple_title(ch).to_string()),
      "orbit": Json(
        @moonucd.fold_orbit(ch).iter().map(c => c.to_string()).collect(),
      ),
    })
  }
  Json(out)
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
