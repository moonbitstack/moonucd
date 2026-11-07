---
name: moonucd
description: "Answer Unicode questions in MoonBit with moonbitstack/moonucd, on Unicode 17.0.0: general category and binary properties, full and simple case mapping and folding, names, ages, blocks and scripts, NFC, NFD, NFKC and NFKD, terminal cell width, grapheme, word and sentence boundaries (UAX #29) and line-break opportunities (UAX #14). Use when comparing text without regard to case, measuring or cutting text for a terminal, normalising before storing or comparing, wrapping lines, or classifying characters in a tokenizer."
---

# moonucd

```bash
moon add moonbitstack/moonucd
```

Each package carries its own tables, so import only what you use:

```moonbit
// moon.pkg
import {
  "moonbitstack/moonucd",           // categories, properties, case
  "moonbitstack/moonucd/normalize", // NFC, NFD, NFKC, NFKD
  "moonbitstack/moonucd/width",     // terminal cells
  "moonbitstack/moonucd/segment",   // graphemes, words, sentences
}
```

The others are `age`, `block`, `name`, `script` and `linebreak`.

## Compare without case

```moonbit
fn same_ignoring_case(a : String, b : String) -> Bool {
  @moonucd.fold(a) == @moonucd.fold(b) // "Straße" and "STRASSE" are the same
}
```

`fold` is full case folding; `upper` and `lower` are full case mapping with the special cases (`ß` to `SS`, final sigma). `simple_fold` maps one character to one character, for a matcher that ignores case character by character.

## Normalise before storing or comparing

```moonbit
fn canonical(text : String) -> String {
  @normalize.normalize(NFC, text) // NFKC also folds compatibility forms: "ｈｅｌｌｏ" to "hello"
}
```

## Fit text into terminal cells

```moonbit
fn cut_to(text : String, cells : Int) -> String {
  let out = StringBuilder()
  let mut used = 0
  for cluster in @segment.grapheme_clusters(text) {
    let w = @width.text_width(cluster).max(0) // -1 for a control character
    if used + w > cells {
      break
    }
    out.write_string(cluster)
    used = used + w
  }
  out.to_string()
}
```

Cut by grapheme cluster, never by code point: an emoji sequence or a letter with its accents is one cluster, and `text_width` measures it the way terminals draw it.

## Things that catch people out

- Offsets into strings are UTF-16 code units, the index MoonBit strings use: `word_at`, `grapheme_at` and `breaks` answer in them.
- `width` answers -1 for a control character and 0 for a combining mark; East Asian Ambiguous characters are one cell unless you pass `ambiguous=2`, as a CJK terminal draws them.
- `linebreaks` gives the pieces a line may break after, and `breaks` the offsets with whether each break is mandatory.
- Every category, binary property and script answers `ranges()`: closed, ascending intervals with neighbours joined, which is what a pattern engine or a tokenizer wants.
