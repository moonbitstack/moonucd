///|
/// The version of the Unicode Character Database the tables come from.
pub fn version() -> String {
  ucd_version
}

///|
/// General_Category.
pub(all) enum Category {
  Lu
  Ll
  Lt
  Lm
  Lo
  Mn
  Mc
  Me
  Nd
  Nl
  No
  Pc
  Pd
  Ps
  Pe
  Pi
  Pf
  Po
  Sm
  Sc
  Sk
  So
  Zs
  Zl
  Zp
  Cc
  Cf
  Cs
  Co
  Cn
} derive(Eq)

///|
pub extend Category with Eq::{equal, not_equal}

///|
pub extend Category with Show::{output, to_string}

///|
let categories : FixedArray[Category] = [
  Lu,
  Ll,
  Lt,
  Lm,
  Lo,
  Mn,
  Mc,
  Me,
  Nd,
  Nl,
  No,
  Pc,
  Pd,
  Ps,
  Pe,
  Pi,
  Pf,
  Po,
  Sm,
  Sc,
  Sk,
  So,
  Zs,
  Zl,
  Zp,
  Cc,
  Cf,
  Cs,
  Co,
  Cn,
]

///|
let category_names : FixedArray[String] = [
  "Lu", "Ll", "Lt", "Lm", "Lo", "Mn", "Mc", "Me", "Nd", "Nl", "No", "Pc", "Pd", "Ps",
  "Pe", "Pi", "Pf", "Po", "Sm", "Sc", "Sk", "So", "Zs", "Zl", "Zp", "Cc", "Cf", "Cs",
  "Co", "Cn",
]

///|
/// The two-letter abbreviation, as the UCD writes it.
pub impl Show for Category with fn output(self, logger) {
  for i, c in categories {
    if c == self {
      logger.write_string(category_names[i])
      return
    }
  }
}

///|
/// The category of `ch`; unassigned code points are `Cn`.
pub fn category(ch : Char) -> Category {
  match find_run(category_starts, category_ends, ch.to_int()) {
    Some(i) => categories[category_values[i]]
    None => Cn
  }
}

///|
/// Bidi_Class.
pub(all) enum Bidi {
  L
  R
  AL
  EN
  ES
  ET
  AN
  CS
  NSM
  BN
  B
  S
  WS
  ON
  LRE
  LRO
  RLE
  RLO
  PDF
  LRI
  RLI
  FSI
  PDI
} derive(Eq)

///|
pub extend Bidi with Eq::{equal, not_equal}

///|
let bidis : FixedArray[Bidi] = [
  L,
  R,
  AL,
  EN,
  ES,
  ET,
  AN,
  CS,
  NSM,
  BN,
  B,
  S,
  WS,
  ON,
  LRE,
  LRO,
  RLE,
  RLO,
  PDF,
  LRI,
  RLI,
  FSI,
  PDI,
]

///|
/// The bidirectional class of `ch`, with the defaults the UCD assigns to
/// unassigned code points.
pub fn bidi(ch : Char) -> Bidi {
  match find_run(bidi_starts, bidi_ends, ch.to_int()) {
    Some(i) => bidis[bidi_values[i]]
    None => L
  }
}

///|
/// Numeric_Type, for characters that have one.
pub(all) enum Numeric {
  Decimal
  Digit
  Numeric
} derive(Eq)

///|
pub extend Numeric with Eq::{equal, not_equal}

///|
/// The numeric type of `ch`; `None` for characters without a numeric value.
pub fn numeric(ch : Char) -> Numeric? {
  match find_run(numeric_starts, numeric_ends, ch.to_int()) {
    Some(i) =>
      Some(
        match numeric_values[i] {
          0 => Decimal
          1 => Digit
          _ => Numeric
        },
      )
    None => None
  }
}

///|
/// A binary property from PropList and DerivedCoreProperties.
pub(all) enum Property {
  Alphabetic
  Lowercase
  Uppercase
  Cased
  CaseIgnorable
  ChangesWhenLowercased
  ChangesWhenUppercased
  ChangesWhenTitlecased
  ChangesWhenCasefolded
  ChangesWhenCasemapped
  IdStart
  IdContinue
  XidStart
  XidContinue
  DefaultIgnorableCodePoint
  GraphemeExtend
  GraphemeBase
  Math
  WhiteSpace
  BidiControl
  JoinControl
  Dash
  Hyphen
  QuotationMark
  TerminalPunctuation
  HexDigit
  AsciiHexDigit
  Ideographic
  Diacritic
  Extender
  NoncharacterCodePoint
  IdsBinaryOperator
  IdsTrinaryOperator
  Radical
  UnifiedIdeograph
  Deprecated
  SoftDotted
  LogicalOrderException
  SentenceTerminal
  VariationSelector
  PatternWhiteSpace
  PatternSyntax
  PrependedConcatenationMark
  RegionalIndicator
} derive(Eq)

///|
pub extend Property with Eq::{equal, not_equal}

///|
let properties : FixedArray[Property] = [
  Alphabetic,
  Lowercase,
  Uppercase,
  Cased,
  CaseIgnorable,
  ChangesWhenLowercased,
  ChangesWhenUppercased,
  ChangesWhenTitlecased,
  ChangesWhenCasefolded,
  ChangesWhenCasemapped,
  IdStart,
  IdContinue,
  XidStart,
  XidContinue,
  DefaultIgnorableCodePoint,
  GraphemeExtend,
  GraphemeBase,
  Math,
  WhiteSpace,
  BidiControl,
  JoinControl,
  Dash,
  Hyphen,
  QuotationMark,
  TerminalPunctuation,
  HexDigit,
  AsciiHexDigit,
  Ideographic,
  Diacritic,
  Extender,
  NoncharacterCodePoint,
  IdsBinaryOperator,
  IdsTrinaryOperator,
  Radical,
  UnifiedIdeograph,
  Deprecated,
  SoftDotted,
  LogicalOrderException,
  SentenceTerminal,
  VariationSelector,
  PatternWhiteSpace,
  PatternSyntax,
  PrependedConcatenationMark,
  RegionalIndicator,
]

///|
/// Whether `ch` has `property`.
pub fn has(ch : Char, property : Property) -> Bool {
  let mut index = 0
  while properties[index] != property {
    index += 1
  }
  let lo = property_offsets[index] / 2
  let hi = property_offsets[index + 1] / 2
  let cp = ch.to_int()
  let mut a = lo
  let mut b = hi
  while a < b {
    let mid = (a + b) / 2
    if property_ranges[mid * 2 + 1] < cp {
      a = mid + 1
    } else {
      b = mid
    }
  }
  a < hi && property_ranges[a * 2] <= cp
}

///|
/// `text` in uppercase, with the full mappings: `ß` becomes `SS`.
pub fn upper(text : StringView) -> String {
  let out = StringBuilder()
  for ch in text {
    map_into(out, ch, upper_keys, upper_offsets, upper_values)
  }
  out.to_string()
}

///|
/// `text` in lowercase, with the full mappings; a capital sigma at the end
/// of a word becomes `ς`.
pub fn lower(text : StringView) -> String {
  let chars = text.iter().collect()
  let out = StringBuilder()
  for i, ch in chars {
    if ch == 'Σ' && final_sigma(chars, i) {
      out.write_char('ς')
    } else {
      map_into(out, ch, lower_keys, lower_offsets, lower_values)
    }
  }
  out.to_string()
}

///|
/// Every character of `text` mapped to its titlecase form. Words are not
/// found here: callers decide which characters start one.
pub fn title(text : StringView) -> String {
  let out = StringBuilder()
  for ch in text {
    map_into(out, ch, title_keys, title_offsets, title_values)
  }
  out.to_string()
}

///|
/// `text` case-folded with the full foldings, for caseless comparison.
pub fn fold(text : StringView) -> String {
  let out = StringBuilder()
  for ch in text {
    map_into(out, ch, fold_keys, fold_offsets, fold_values)
  }
  out.to_string()
}

///|
/// The Final_Sigma condition: a cased letter before, skipping case-ignorable
/// ones, and none after.
fn final_sigma(chars : Array[Char], at : Int32) -> Bool {
  let mut i = at - 1
  while i >= 0 && has(chars[i], CaseIgnorable) {
    i -= 1
  }
  if i < 0 || !has(chars[i], Cased) {
    return false
  }
  let mut j = at + 1
  while j < chars.length() && has(chars[j], CaseIgnorable) {
    j += 1
  }
  j >= chars.length() || !has(chars[j], Cased)
}

///|
fn map_into(
  out : StringBuilder,
  ch : Char,
  keys : FixedArray[Int32],
  offsets : FixedArray[Int32],
  values : FixedArray[Int32],
) -> Unit {
  let cp = ch.to_int()
  let mut a = 0
  let mut b = keys.length()
  while a < b {
    let mid = (a + b) / 2
    if keys[mid] < cp {
      a = mid + 1
    } else {
      b = mid
    }
  }
  if a < keys.length() && keys[a] == cp {
    for k in offsets[a]..<offsets[a + 1] {
      out.write_char(values[k].unsafe_to_char())
    }
  } else {
    out.write_char(ch)
  }
}

///|
/// The run holding `cp`, by binary search over sorted, disjoint runs.
fn find_run(
  starts : FixedArray[Int32],
  ends : FixedArray[Int32],
  cp : Int32,
) -> Int32? {
  let mut a = 0
  let mut b = starts.length()
  while a < b {
    let mid = (a + b) / 2
    if ends[mid] < cp {
      a = mid + 1
    } else {
      b = mid
    }
  }
  if a < starts.length() && starts[a] <= cp {
    Some(a)
  } else {
    None
  }
}
