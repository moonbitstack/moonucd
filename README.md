# moonucd

The Unicode Character Database, queried from MoonBit: what kind of character
something is, which properties it has, and how it changes case — for every
code point of Unicode 17.0.0.

```moonbit
@moonucd.category('ǅ')                 // Lt
@moonucd.has('中', Alphabetic)          // true
@moonucd.numeric('٣')                  // Some(Decimal)
@moonucd.upper("straße")               // "STRASSE"
@moonucd.lower("ΟΔΟΣ")                 // "οδος"
@moonucd.fold("Straße") == @moonucd.fold("STRASSE")   // true
```

```
moon add moonbitstack/moonucd
```

## What a character is

| Call | Answers |
|:--|:--|
| `category(ch)` | its General_Category, one of 30 two-letter values; unassigned code points are `Cn` |
| `bidi(ch)` | its Bidi_Class, with the defaults Unicode gives unassigned code points |
| `numeric(ch)` | `Decimal`, `Digit` or `Numeric` for characters with a numeric value, else `None` |
| `has(ch, property)` | whether it has one of 44 binary properties: `Alphabetic`, `Uppercase`, `Lowercase`, `Cased`, `CaseIgnorable`, `WhiteSpace`, `XidStart`, `XidContinue`, `Math`, `Dash`, `Ideographic`, `RegionalIndicator`… |

## Changing case

All four take a string and return a new one, because one character can
become several.

| Call | Does |
|:--|:--|
| `upper(text)` | full uppercase mapping: `ß` becomes `SS`, `ﬃ` becomes `FFI` |
| `lower(text)` | full lowercase mapping; a capital sigma ending a word becomes `ς` |
| `title(text)` | each character to its titlecase form: `ǆ` becomes `ǅ`; which characters start a word is the caller's call |
| `fold(text)` | full case folding, for comparing text without regard to case |

The mappings are the ones that hold in every language. Turkish and
Lithuanian rules that depend on a locale are left to the caller.

## Version

`version()` returns `"17.0.0"`. The tables are generated from the Unicode
Character Database by `scripts/gen_tables.py`; a new Unicode release is a
regeneration, not a code change.

Runs on every MoonBit backend: native, wasm, wasm-gc and js.

## Licence

Apache-2.0.
