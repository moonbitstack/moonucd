// Compare the dump of src/tools/dump_ucd with unicode-js, a second
// implementation that ships the Unicode 17.0.0 tables as data files of its
// own: the script of every code point, the block, and the simple case
// mappings and foldings. Run it after building the dump:
//
//   node scripts/differential/compare.mjs ucd.tsv
//
// The package it reads is pinned in CI (`@unicode/unicode-17.0.0`), and the
// counts it prints are the ones the README table reports.

import { createReadStream, readdirSync, existsSync } from "node:fs";
import { createRequire } from "node:module";
import { dirname, join } from "node:path";
import { pathToFileURL } from "node:url";
import readline from "node:readline";

const require = createRequire(import.meta.url);
const pkg = join(dirname(require.resolve("@unicode/unicode-17.0.0/package.json")));
const SIZE = 0x110000;

// Names in the two sources differ only in punctuation and case: "Old_Italic"
// against "Old Italic", "CJK_Unified_Ideographs" against "CJK Unified
// Ideographs".
const fold = (s) => s.toLowerCase().replace(/[^a-z0-9]/g, "");

async function valueTable(kind, dir, { ranges = true } = {}) {
  const index = new Int16Array(SIZE).fill(-1);
  const names = [];
  const files = readdirSync(join(pkg, kind))
    .filter((name) => existsSync(join(pkg, kind, name, ranges ? "ranges.mjs" : "code-points.mjs")))
    .sort();
  for (const name of files) {
    const at = names.push(name) - 1;
    const mod = await import(pathToFileURL(join(pkg, kind, name, ranges ? "ranges.mjs" : "code-points.mjs")).href);
    if (ranges) {
      for (const range of mod.default) {
        for (let cp = range.begin; cp < range.end; cp += 1) index[cp] = at;
      }
    } else {
      for (const cp of mod.default) index[cp] = at;
    }
  }
  return { index, names };
}

async function caseMap(which) {
  const mod = await import(pathToFileURL(join(pkg, "Simple_Case_Mapping", which, "code-points.mjs")).href);
  return mod.default;
}

async function foldMap() {
  const out = new Map();
  for (const which of ["C", "S"]) {
    const mod = await import(pathToFileURL(join(pkg, "Case_Folding", which, "code-points.mjs")).href);
    for (const [from, to] of mod.default) out.set(from, to);
  }
  return out;
}

const fields = {
  CP: 0, CATEGORY: 1, CCC: 2, BIDI: 3, EAW: 4, CELLS: 5, NUMERIC_TYPE: 6,
  NUMERIC_VALUE: 7, SCRIPT: 8, BLOCK: 9, UPPER: 10, LOWER: 11, TITLE: 12,
  FOLD: 13, LINE_BREAK: 14, NAME: 15,
};

const script = await valueTable("Script", "");
const block = await valueTable("Block", "");
const maps = {
  script: script,
  block: block,
  upper: await caseMap("Uppercase"),
  lower: await caseMap("Lowercase"),
  title: await caseMap("Titlecase"),
  fold: await foldMap(),
};

const counted = { script: 0, block: 0, "simple uppercase": 0, "simple lowercase": 0, "simple titlecase": 0, "simple fold": 0 };
const bad = [];
let compared = 0;

const hex = (cp) => cp.toString(16).toUpperCase().padStart(4, "0");

function mismatch(what, cp, mine, want) {
  counted[what] += 1;
  if (bad.length < 8) bad.push(`U+${hex(cp)} ${what}: we say ${mine}, unicode-js says ${want}`);
}

const lines = readline.createInterface({ input: createReadStream(process.argv[2]), crlfDelay: Infinity });
for await (const line of lines) {
  const f = line.split("\t");
  if (f.length !== 20) {
    console.error(`a line has ${f.length} fields, not 20: ${line.slice(0, 80)}`);
    process.exit(2);
  }
  const cp = Number(f[fields.CP]);
  compared += 1;

  const scriptAt = script.index[cp];
  const scriptName = scriptAt < 0 ? "Unknown" : script.names[scriptAt];
  if (fold(scriptName) !== fold(f[fields.SCRIPT])) {
    mismatch("script", cp, f[fields.SCRIPT], scriptName);
  }

  // unicode-js keeps `No_Block` as a value of its own; this library answers
  // `None` for a code point in no block, which is the same fact.
  const blockAt = block.index[cp];
  const raw = blockAt < 0 ? "" : block.names[blockAt];
  const blockName = raw === "No_Block" ? "" : raw;
  if (fold(blockName) !== fold(f[fields.BLOCK])) {
    mismatch("block", cp, f[fields.BLOCK] || "-", blockName || "-");
  }

  for (const [what, field, map] of [
    ["simple uppercase", fields.UPPER, maps.upper],
    ["simple lowercase", fields.LOWER, maps.lower],
    ["simple titlecase", fields.TITLE, maps.title],
    ["simple fold", fields.FOLD, maps.fold],
  ]) {
    const mine = Number.parseInt(f[field], 16);
    const want = map.get(cp) ?? cp;
    if (mine !== want) mismatch(what, cp, `U+${hex(mine)}`, `U+${hex(want)}`);
  }
}

console.log(`compared ${compared} code points with unicode-js ${require("@unicode/unicode-17.0.0/package.json").version}`);
for (const [what, n] of Object.entries(counted)) {
  console.log(`  ${what.padEnd(18)} ${String(n).padStart(6)} different`);
}
for (const row of bad) console.log(`  ${row}`);
process.exit(Object.values(counted).some((n) => n > 0) ? 1 : 0);
