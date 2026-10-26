# moonucd

The Unicode Character Database for MoonBit: what a character is, which
properties it carries, how it changes case and normalizes, and how it breaks
into graphemes, words, sentences and lines — for every code point of Unicode
17.0.0.

```
moon add moonbitstack/moonucd
```

```moonbit
@moonucd.category('ǅ')                       // Lt
@moonucd.has('中', Alphabetic)                // true
@moonucd.numeric('٣')                         // Some(Decimal)
@moonucd.upper("straße")                      // "STRASSE"
@moonucd.lower("ΟΔΟΣ")                        // "οδος"
@moonucd.fold("Straße") == @moonucd.fold("STRASSE")   // true
```

Everything runs on every MoonBit backend — native, wasm, wasm-gc and js — and
the tables are generated from the UCD, so a new Unicode release is a
regeneration, not a code change.

## Packages

The library is a set of small packages. The root package `moonucd` holds the
general character facts; the rest are opt-in sub-packages you import only when
you need them.

| Package | What it answers |
|:--|:--|
| `moonucd` | category, bidi class, numeric type, binary properties, case mapping |
| `moonbitstack/moonucd/age` | the Unicode version that first assigned a code point |
| `moonbitstack/moonucd/block` | the block a code point sits in, and a block's range |
| `moonbitstack/moonucd/name` | a code point's name, and the code point a name names |
| `moonbitstack/moonucd/normalize` | NFC / NFD / NFKC / NFKD, and decomposition facts |
| `moonbitstack/moonucd/script` | the script of a code point and its script extensions |
| `moonbitstack/moonucd/segment` | grapheme clusters, words and sentences (UAX #29) |
| `moonbitstack/moonucd/width` | terminal-cell width and East Asian Width |
| `moonbitstack/moonucd/linebreak` | line-break opportunities (UAX #14) |

## What a character is

| Call | Answers |
|:--|:--|
| `category(ch)` | its `General_Category`, one of 30 two-letter values; unassigned code points are `Cn` |
| `bidi(ch)` | its `Bidi_Class`, with the defaults Unicode gives unassigned code points |
| `numeric(ch)` | `Decimal`, `Digit` or `Numeric` for characters with a numeric value, else `None` |
| `has(ch, property)` | whether it has one of 50 binary properties: `Alphabetic`, `Uppercase`, `Lowercase`, `Cased`, `CaseIgnorable`, `WhiteSpace`, `XidStart`, `XidContinue`, `Math`, `Dash`, `Ideographic`, `RegionalIndicator`, `Emoji`, `EmojiPresentation`, `ExtendedPictographic`… |

```moonbit
@moonucd.category('中')                  // Lo
@moonucd.bidi('א')                       // R
@moonucd.numeric('٣')                    // Some(Decimal)
@moonucd.has('é', Alphabetic)            // true
```

## Changing case

All four take a string and return a new one, because one character can become
several.

| Call | Does |
|:--|:--|
| `upper(text)` | full uppercase mapping: `ß` becomes `SS`, `ﬃ` becomes `FFI` |
| `lower(text)` | full lowercase mapping; a capital sigma ending a word becomes `ς` |
| `title(text)` | each character to its titlecase form: `ǆ` becomes `ǅ`; which characters start a word is the caller's call |
| `fold(text)` | full case folding, for comparing text without regard to case |

The mappings are the ones that hold in every language. Turkish and Lithuanian
rules that depend on a locale are left to the caller.

## Age, blocks and names

```moonbit
@age.age('中')                 // Some((1, 1))
@age.age('🚀')         // Some((6, 0))
@block.block('中')             // Some("CJK Unified Ideographs")
@block.range("basic latin")   // Some((' ', '~'))
@name.name('中')               // Some("CJK UNIFIED IDEOGRAPH-4E2D")
@name.lookup("copyright sign") // Some('©')
```

| Call | Answers |
|:--|:--|
| `age(ch)` | the `(major, minor)` Unicode version that first assigned `ch`, or `None` for still-unassigned code points |
| `block(ch)` | the name of the block `ch` sits in, or `None` for code points in no block |
| `range(name)` | the first and last code point of the block `name`, matched loosely (case, spaces, hyphens, leading "is" ignored) |
| `name(ch)` | the UCD name of `ch`, or `None` for unassigned, surrogate and similar code points |
| `lookup(name)` | the code point named `name`, matched loosely; CJK ideograph names and NameAliases entries resolve |

## Normalization (UAX #15)

```moonbit
@normalize.normalize(@normalize.NFD, "Å")          // "A" followed by combining ring
@normalize.normalize(@normalize.NFC, "A\u{030A}")  // "Å"
@normalize.normalize(@normalize.NFKC, "①")         // "1"
@normalize.is_normalized(@normalize.NFC, "Å")      // true
@normalize.combining('\u{0301}')                  // 230 (the combining class)
@normalize.decomposition('Å')                      // "0041 030A"
```

| Call | Does |
|:--|:--|
| `normalize(form, text)` | `text` in `NFC`, `NFD`, `NFKC` or `NFKD` — decompose, canonical-order, compose when the form is a composed one |
| `is_normalized(form, text)` | whether `text` is already in `form` |
| `combining(ch)` | the Canonical_Combining_Class of `ch` (0 when it has none) |
| `decomposition(ch)` | the first-level mapping of `ch` as the UCD lists it: a space-separated, upper-case, four-digit-hex sequence |

## Scripts

```moonbit
@script.script('中')                 // Han
@script.extensions('ゝ')             // [Hiragana, Katakana]
@script.Script::of("Latin")          // Some(Latin)
```

| Call | Answers |
|:--|:--|
| `script(ch)` | the `Script` of `ch`; code points with no dedicated script are `Common` or `Inherited` |
| `extensions(ch)` | the script extensions of `ch` — the other scripts it can appear in |
| `Script::of(name)` | the `Script` named `name`, or `None` |

## Segmentation (UAX #29)

```moonbit
@segment.grapheme_clusters("🇯🇵a")   // ["🇯🇵", "a"]   — the flag is one cluster
@segment.words("Mr. Smith said hi.") // ["Mr", ".", " ", "Smith", " ", "said", " ", "hi", "."]
@segment.sentences("Hello. Bye!")     // ["Hello. ", "Bye!"]
```

| Call | Does |
|:--|:--|
| `grapheme_clusters(text)` | the user-perceived characters — a flag emoji, or a letter with its accents, is one cluster |
| `words(text)` | the words, keeping the spaces and punctuation that separate them |
| `sentences(text)` | the sentence breaks, keeping the trailing whitespace |
| `gcb_property` / `wb_property` / `sb_property` | the raw Grapheme / Word / Sentence break properties of a character |

## Width

```moonbit
@width.width('中')                  // 2
@width.width('A')                   // 1
@width.east_asian_width('中')        // W
@width.text_width("Hello 世界")      // 11
```

| Call | Answers |
|:--|:--|
| `east_asian_width(ch)` | the `Eaw` of `ch`: `A`, `F`, `H`, `N`, `Na` or `W` |
| `width(ch)` | how many terminal cells `ch` occupies (0, 1 or 2) |
| `text_width(text)` | the total cell width of `text` |

The widths follow `wcwidth` 0.2.14: East Asian Wide and Fullwidth characters
take two cells; everything else takes one (or zero, for non-spacing marks).

## Line breaking (UAX #14)

```moonbit
@linebreak.linebreaks("The quick 日本 fox")
// ["The ", "quick ", "日", "本 ", "fox"]
@linebreak.lb_property('中')         // ID
```

| Call | Does |
|:--|:--|
| `lb_property(ch)` | the `Lb` line-break class of `ch` |
| `linebreaks(text)` | `text` split at every allowed line-break opportunity |
| `linebreak_boundaries(cps)` | the per-gap break flags for an array of code points |

The implementation is validated against the full `LineBreakTest.txt` — 19,338
cases — at zero conformance errors.

## Examples

The `src/examples` directory holds small, runnable programs, one per package:

| Example | Shows |
|:--|:--|
| `01-tour` | the core `moonucd` API |
| `02-scripts` | `script`, `extensions`, `Script::of` |
| `03-width` | `width`, `east_asian_width`, `text_width` |
| `04-normalize` | `normalize`, `is_normalized`, `decomposition` |
| `05-segment` | `grapheme_clusters`, `words`, `sentences` |
| `06-linebreak` | `linebreaks`, `lb_property` |

Run one with `moon run src/examples/01-tour` (any of the four backends).

## How the tables are made

Every table is generated from the UCD 17.0.0 by the scripts in `scripts/`
(`gen_age.py`, `gen_block.py`, `gen_name.py`, `gen_normalize.py`,
`gen_script.py`, `gen_segment.py`, `gen_width.py`, `gen_linebreak.py`). They
turn `LineBreak.txt`, `EastAsianWidth.txt`, `UnicodeData.txt`, `Scripts.txt`,
`emoji-data.txt`, `NormalizationTest.txt`, `GraphemeBreakTest.txt` and the rest
into the run-length tables the library searches at runtime. A new Unicode
version is a regeneration; the algorithm code does not change.

`version()` returns `"17.0.0"` from every package.

## Licence

Apache-2.0.
