///|
/// The version of the Unicode Character Database the tables come from.
pub fn version() -> String {
  ucd_version
}

///|
/// Script, the writing system a character belongs to. The long name is what
/// `Show` writes; `Script::of` reads both it and the four-letter code.
pub(all) enum Script {
  Adlam
  Ahom
  AnatolianHieroglyphs
  Arabic
  Armenian
  Avestan
  Balinese
  Bamum
  BassaVah
  Batak
  Bengali
  BeriaErfe
  Bhaiksuki
  Bopomofo
  Brahmi
  Braille
  Buginese
  Buhid
  CanadianAboriginal
  Carian
  CaucasianAlbanian
  Chakma
  Cham
  Cherokee
  Chorasmian
  Common
  Coptic
  Cuneiform
  Cypriot
  CyproMinoan
  Cyrillic
  Deseret
  Devanagari
  DivesAkuru
  Dogra
  Duployan
  EgyptianHieroglyphs
  Elbasan
  Elymaic
  Ethiopic
  Garay
  Georgian
  Glagolitic
  Gothic
  Grantha
  Greek
  Gujarati
  GunjalaGondi
  Gurmukhi
  GurungKhema
  Han
  Hangul
  HanifiRohingya
  Hanunoo
  Hatran
  Hebrew
  Hiragana
  ImperialAramaic
  Inherited
  InscriptionalPahlavi
  InscriptionalParthian
  Javanese
  Kaithi
  Kannada
  Katakana
  KatakanaOrHiragana
  Kawi
  KayahLi
  Kharoshthi
  KhitanSmallScript
  Khmer
  Khojki
  Khudawadi
  KiratRai
  Lao
  Latin
  Lepcha
  Limbu
  LinearA
  LinearB
  Lisu
  Lycian
  Lydian
  Mahajani
  Makasar
  Malayalam
  Mandaic
  Manichaean
  Marchen
  MasaramGondi
  Medefaidrin
  MeeteiMayek
  MendeKikakui
  MeroiticCursive
  MeroiticHieroglyphs
  Miao
  Modi
  Mongolian
  Mro
  Multani
  Myanmar
  Nabataean
  NagMundari
  Nandinagari
  NewTaiLue
  Newa
  Nko
  Nushu
  NyiakengPuachueHmong
  Ogham
  OlChiki
  OlOnal
  OldHungarian
  OldItalic
  OldNorthArabian
  OldPermic
  OldPersian
  OldSogdian
  OldSouthArabian
  OldTurkic
  OldUyghur
  Oriya
  Osage
  Osmanya
  PahawhHmong
  Palmyrene
  PauCinHau
  PhagsPa
  Phoenician
  PsalterPahlavi
  Rejang
  Runic
  Samaritan
  Saurashtra
  Sharada
  Shavian
  Siddham
  Sidetic
  SignWriting
  Sinhala
  Sogdian
  SoraSompeng
  Soyombo
  Sundanese
  Sunuwar
  SylotiNagri
  Syriac
  Tagalog
  Tagbanwa
  TaiLe
  TaiTham
  TaiViet
  TaiYo
  Takri
  Tamil
  Tangsa
  Tangut
  Telugu
  Thaana
  Thai
  Tibetan
  Tifinagh
  Tirhuta
  Todhri
  TolongSiki
  Toto
  TuluTigalari
  Ugaritic
  Unknown
  Vai
  Vithkuqi
  Wancho
  WarangCiti
  Yezidi
  Yi
  ZanabazarSquare
} derive(Eq)

///|
pub extend Script with Eq::{equal, not_equal}

///|
pub extend Script with Show::{output, to_string}

///|
pub impl Show for Script with fn output(self, logger) {
  for i, s in scripts {
    if s == self {
      logger.write_string(script_names[i])
      return
    }
  }
}

///|
/// The script of `ch`; unassigned and unknown code points are `Unknown`.
pub fn script(ch : Char) -> Script {
  match find_run(script_starts, script_ends, ch.to_int()) {
    Some(i) => scripts[script_values[i]]
    None => Unknown
  }
}

///|
/// The scripts `ch` can belong to: the ScriptExtensions.txt list when it has
/// one, and `[script(ch)]` when it does not.
pub fn extensions(ch : Char) -> Array[Script] {
  match find_run(ext_starts, ext_ends, ch.to_int()) {
    Some(i) => {
      let out = []
      for k in ext_offsets[i]..<ext_offsets[i + 1] {
        out.push(scripts[ext_values[k]])
      }
      out
    }
    None => [script(ch)]
  }
}

///|
/// The script called `name` — a long name ("Latin", "Old Italic") or a
/// four-letter code ("Latn", "Ital"), matched the loose way of UAX #44
/// (LM3): case, spaces, underscores, hyphens and a leading "is" are ignored.
pub fn Script::of(name : StringView) -> Script? {
  match find_key(name) {
    Some(i) => Some(scripts[loose_values[i]])
    None => None
  }
}

///|
/// The loose key of `name`: UAX #44 LM3 without the leading "is", which is
/// only ever stripped from what a caller asks for, never from the table.
fn loose_key(name : StringView) -> String {
  let out = StringBuilder()
  for ch in name {
    if ch != ' ' && ch != '\t' && ch != '_' && ch != '-' {
      out.write_char(ch.to_ascii_lowercase())
    }
  }
  let key = out.to_string()
  if key.has_prefix("is") {
    key[2:].to_owned()
  } else {
    key
  }
}

///|
fn find_key(name : StringView) -> Int32? {
  let key = loose_key(name)
  let mut a = 0
  let mut b = loose_keys.length()
  while a < b {
    let mid = (a + b) / 2
    if compare_key(loose_keys[mid], key) < 0 {
      a = mid + 1
    } else {
      b = mid
    }
  }
  if a < loose_keys.length() && compare_key(loose_keys[a], key) == 0 {
    Some(a)
  } else {
    None
  }
}

///|
/// Lexicographic by code unit — the dictionary order the keys are stored in.
/// (String's own Compare is shortlex, which would not match.)
fn compare_key(a : String, b : String) -> Int32 {
  let n = if a.length() < b.length() { a.length() } else { b.length() }
  for i in 0..<n {
    let x = a.unsafe_get(i)
    let y = b.unsafe_get(i)
    if x != y {
      return if x < y { -1 } else { 1 }
    }
  }
  if a.length() < b.length() {
    -1
  } else if a.length() > b.length() {
    1
  } else {
    0
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
