<div align="center">

<h1>moonucd</h1>

<p><b>The Unicode Character Database for MoonBit.</b><br>
What a character is, how it changes case and normalizes, how wide it is, and where text breaks into
graphemes, words, sentences and lines, for every code point of Unicode 17.0.0.</p>

<p>
<a href="https://moonbitstack.github.io/moonucd/">Home</a> ·
<a href="https://moonbitstack.github.io/moonucd/guide.html">Guide</a> ·
<a href="https://moonbitstack.github.io/moonucd/api.html">API</a> ·
<a href="https://mooncakes.io/docs/moonbitstack/moonucd">mooncakes</a>
</p>

</div>

```
moon add moonbitstack/moonucd
```

```moonbit
@moonucd.category('ǅ')                 // Lt
@moonucd.upper("straße")               // "STRASSE"
@moonucd.fold("Straße") == @moonucd.fold("STRASSE")   // true
@name.name('中')                       // Some("CJK UNIFIED IDEOGRAPH-4E2D")
@width.text_width("Hello 世界")         // 10
@segment.grapheme_clusters("🇨🇳e\u{301}!")   // ["🇨🇳", "é", "!"]
@linebreak.linebreaks("The quick 中文 fox")   // ["The ", "quick ", "中", "文 ", "fox"]
```

## Packages

The root package holds the general character facts. The other eight carry their own tables, so a program links only the tables of the packages it imports.

<table>
<tr><th>Import</th><th>Answers</th><th>Main calls</th></tr>
<tr><td><code>moonbitstack/moonucd</code></td><td>what a character is, how it changes case, the ranges a category or property covers</td><td><code>category</code> <code>bidi</code> <code>numeric</code> <code>has</code> <code>upper</code> <code>lower</code> <code>title</code> <code>fold</code> <code>simple_fold</code> <code>fold_orbit</code> <code>ranges</code></td></tr>
<tr><td><code>…/moonucd/age</code></td><td>the version that first assigned a code point</td><td><code>age</code></td></tr>
<tr><td><code>…/moonucd/block</code></td><td>the block of a code point, the range of a block</td><td><code>block</code> <code>range</code></td></tr>
<tr><td><code>…/moonucd/name</code></td><td>the name of a code point, the code point of a name</td><td><code>name</code> <code>lookup</code></td></tr>
<tr><td><code>…/moonucd/script</code></td><td>the script of a code point, the scripts it is shared with, the ranges of a script</td><td><code>script</code> <code>extensions</code> <code>Script::of</code> <code>Script::ranges</code> <code>Script::extended_ranges</code></td></tr>
<tr><td><code>…/moonucd/normalize</code></td><td>NFC, NFD, NFKC, NFKD</td><td><code>normalize</code> <code>is_normalized</code> <code>combining</code> <code>decomposition</code></td></tr>
<tr><td><code>…/moonucd/width</code></td><td>terminal cells, East Asian Width</td><td><code>width</code> <code>text_width</code> <code>east_asian_width</code></td></tr>
<tr><td><code>…/moonucd/segment</code></td><td>grapheme clusters, words, sentences (UAX #29)</td><td><code>grapheme_clusters</code> <code>words</code> <code>sentences</code> <code>grapheme_at</code> <code>word_at</code></td></tr>
<tr><td><code>…/moonucd/linebreak</code></td><td>line-break opportunities (UAX #14)</td><td><code>linebreaks</code> <code>breaks</code> <code>lb_property</code></td></tr>
</table>

Every function is pure and runs on native, wasm, wasm-gc and js. Offsets into strings are UTF-16 code units, the index MoonBit strings use.

## A few more

```moonbit
@moonucd.has('_', XidContinue)                 // true
@moonucd.lower("ΣΟΦΟΣ ΣΟΦΟΣ")                  // "σοφος σοφος"
@age.age('€')                                  // Some((2, 1))
@block.range("Greek")                          // Some(('\u{370}', '\u{3FF}'))
@name.lookup("copyright sign")                 // Some('©')
@script.extensions('ー')                       // [Hiragana, Katakana]
@normalize.normalize(NFKC, "ｈｅｌｌｏ")         // "hello"
@normalize.decomposition('½')                  // "<fraction> 0031 2044 0032"
@width.width('α', ambiguous=2)                 // 2
@segment.word_at("hello, world", 9)            // (7, 12)
@linebreak.breaks("one two\nthree")            // [(4, false), (8, true)]
```

The [guide](https://moonbitstack.github.io/moonucd/guide.html) walks through every package; the [API reference](https://moonbitstack.github.io/moonucd/api.html) lists every function and type.

## Ranges and simple folding

A set of characters is easier to work with as intervals than as a predicate: a pattern engine, a
tokenizer or a character map all keep `(start, end)` pairs. Every category, every binary property
and every script answers with its ranges — closed, ascending, neighbours already joined, so two
sets meet by walking them once.

```moonbit
@moonucd.Nd.ranges()[0]                      // (0x30, 0x39)
@moonucd.Dash.ranges().length()              // 24
@moonucd.simple_fold('ς')                    // 'σ'
@moonucd.fold_orbit('K')                     // ['K', 'k', '\u{212A}']
@script.Greek.ranges()[0]                    // (0x370, 0x373)
@script.Katakana.extended_ranges().length()  // 22
```

`simple_fold` is the C and S classes of CaseFolding.txt: one character in, one character out, which
is what a match that ignores case character by character needs. `fold_orbit` gives the whole class a
character folds with, so a set closes under case without a walk of the code space.
`Script::ranges` follows the script a character is listed under; `Script::extended_ranges` follows
Script_Extensions, the scripts it is shared with.

## Examples

| Example | Shows |
|:--:|:--|
| `01-tour` | category, numeric type, binary properties, case, ranges |
| `02-scripts` | `script`, `extensions`, `Script::of` |
| `03-width` | `width`, `east_asian_width`, `text_width` |
| `04-normalize` | `normalize`, `is_normalized`, `decomposition` |
| `05-segment` | `grapheme_clusters`, `words`, `sentences` |
| `06-linebreak` | `linebreaks`, `lb_property` |
| `07-terminal` | wrapping and truncating text by terminal cells |

```
moon run src/examples/07-terminal
```

## Tables

Every table is generated from the Unicode Character Database by the scripts in `scripts/tables`. Every package reports the version in `version()`, and a new Unicode version is a regeneration that leaves the interfaces as they are.

## Licence

Apache-2.0.
