// The sorting office: every panel below is drawn from one call into the
// compiled library, `analyse(text)`, which answers the clusters, offsets,
// widths, break classes, the four normalization forms and the case of each
// character. Nothing here re-implements Unicode.

const ucd = await import("../engine/moonucd.js").catch(() => null);

const $ = (sel, root = document) => root.querySelector(sel);
const $$ = (sel, root = document) => [...root.querySelectorAll(sel)];

const state = { text: "", form: "NFC", ambiguous: false, width: 20 };

let tip = null;
function showTip(target, x, y) {
  if (!tip) return;
  tip.textContent = target.dataset.tip;
  tip.classList.add("on");
  const box = tip.getBoundingClientRect();
  const left = Math.min(Math.max(8, x + 12), innerWidth - box.width - 8);
  const top = y + 18 + box.height > innerHeight ? y - box.height - 10 : y + 18;
  tip.style.left = `${left}px`;
  tip.style.top = `${top}px`;
}
function hideTip() {
  tip?.classList.remove("on");
}
function wireTips(root) {
  for (const el of $$("[data-tip]", root)) {
    el.addEventListener("pointerenter", (e) => showTip(el, e.clientX, e.clientY));
    el.addEventListener("pointermove", (e) => showTip(el, e.clientX, e.clientY));
    el.addEventListener("pointerleave", hideTip);
    el.addEventListener("focus", () => {
      const r = el.getBoundingClientRect();
      showTip(el, r.left, r.bottom);
    });
    el.addEventListener("blur", hideTip);
  }
}

const el = (tag, cls, text) => {
  const node = document.createElement(tag);
  if (cls) node.className = cls;
  if (text !== undefined) node.textContent = text;
  return node;
};

// A tile for one code point in the press: the glyph, its code point, and its
// combining class when it has one.
function tile(spec, { joined = false } = {}) {
  const node = el("div", "tile" + (joined ? " joined" : "") + (spec.hangul ? " hangul" : ""));
  node.append(el("span", "g", spec.char));
  node.append(el("span", "u", spec.hex));
  if (spec.ccc > 0) node.append(el("span", "ccc", String(spec.ccc)));
  const dec = spec.dec ? `decomposition ${spec.dec}` : "no decomposition";
  node.dataset.tip = `${spec.hex}  ccc ${spec.ccc}  ${spec.name || "unnamed"}\n${dec}`;
  return node;
}

function renderManifest(data) {
  const set = (key, value) => {
    const cell = $(`[data-m="${key}"]`);
    if (cell) cell.textContent = value;
  };
  set("codepoints", data.codepoints);
  set("utf16", data.utf16);
  set("clusters", data.graphemes.length);
  set("cells", state.ambiguous ? data.wide : data.narrow);
  set("breaks", data.breaks.length);
  set("words", data.words.length);
}

function renderPress(data) {
  const input = $('[data-tray="in"]');
  const nfd = $('[data-tray="nfd"]');
  const form = $('[data-tray="form"]');
  input.replaceChildren(...data.chars.map((spec) => tile(spec)));
  nfd.replaceChildren(...data.nfd.map((spec) => tile(spec)));

  const chosen = data[state.form.toLowerCase()];
  const nfdChars = new Set(data.nfd.map((s) => s.char));
  form.replaceChildren(...chosen.map((spec) => tile(spec, { joined: !nfdChars.has(spec.char) })));

  $("#form-name").textContent = state.form;
  $("#form-string").textContent = chosen.map((s) => s.char).join("");

  const marks = data.nfd.filter((s) => s.ccc > 0).length;
  $("#in-note").textContent = `${data.chars.length} cp`;
  $("#nfd-note").textContent =
    data.isNFD ? "already decomposed" : `${data.nfd.length} cp, ${marks} with a combining class`;
  const delta = data.nfd.length - chosen.length;
  $("#form-note").textContent = delta > 0 ? `${delta} composed` : "nothing to compose";

  const notes = [];
  notes.push(data.isNFC ? "The text is already in NFC." : "The text is not in NFC.");
  if (state.form === "NFKC" || state.form === "NFKD") {
    notes.push("Compatibility forms fold things like the fullwidth letters and the ligatures.");
  }
  if (data.nfd.length !== data.chars.length) {
    notes.push("Decomposition turned some characters into several.");
  }
  $("#press-note").textContent = notes.join(" ");
}

function renderBelt(data) {
  const cellsOf = (item) => Math.max(0, state.ambiguous ? item.wide : item.width);

  const lane = $('[data-lane="graphemes"]');
  lane.replaceChildren();
  for (const item of data.graphemes) {
    const cells = cellsOf(item);
    const unit = el("div", "unit");
    unit.style.setProperty("--cells", Math.max(cells, 1));
    if (item.width < 0) unit.classList.add("must");
    else if (cells === 0) unit.classList.add("zero");
    unit.append(el("span", "g", item.text === " " ? "·" : item.text.replace(/\n/g, "¶")));
    unit.append(el("span", "u", `${cells}`));
    unit.dataset.tip = `${JSON.stringify(item.text)}\n${item.start}..${item.end}  ${item.gcb}  ${item.width}/${item.wide} cells`;
    lane.append(unit);
  }
  if (!data.graphemes.length) lane.append(el("div", "unit", "—"));

  const words = $('[data-lane="words"]');
  words.replaceChildren();
  for (const item of data.words) {
    const chip = el("span", "chip" + (/^\s+$/.test(item.text) ? " space" : ""), item.text);
    chip.dataset.tip = `${item.start}..${item.end}`;
    words.append(chip);
  }
  if (!data.words.length) words.append(el("span", "chip", "—"));

  const sentences = $('[data-lane="sentences"]');
  sentences.replaceChildren();
  for (const item of data.sentences) {
    const block = el("div", "sent", item.text);
    block.dataset.tip = `${item.start}..${item.end}`;
    sentences.append(block);
  }
  if (!data.sentences.length) sentences.append(el("div", "sent", "—"));

  const total = state.ambiguous ? data.wide : data.narrow;
  $("#belt-total").textContent = `${total} cells`;
  wireTips(lane);
}

function renderStrip(data) {
  const strip = $("#strip");
  strip.replaceChildren();
  const cuts = new Map(data.breaks.map((b) => [b.at, b]));
  const chars = data.chars;
  let offset = 0;
  chars.forEach((spec, i) => {
    const node = el("div", "ch" + (spec.char === " " ? " space" : ""), spec.char === "<control>" ? "␀" : spec.char);
    node.dataset.tip = `${spec.hex}  ${spec.name || "unnamed"}`;
    strip.append(node);
    offset += spec.cp > 0xffff ? 2 : 1;
    if (i < chars.length - 1) {
      const cut = cuts.get(offset);
      const kind = cut ? (cut.mandatory ? "must" : "may") : "none";
      const mark = el("div", `cut ${kind}`);
      const label = cut ? `${cut.before} ${cut.mandatory ? "!" : "÷"} ${cut.after}` : "no break";
      mark.dataset.tip = `${label}  at ${offset}`;
      mark.setAttribute("aria-label", label);
      strip.append(mark);
    }
  });
  if (!chars.length) strip.append(el("div", "ch", "—"));
  wireTips(strip);
}

function wrap(data) {
  const cuts = new Map(data.breaks.map((b) => [b.at, b]));
  const cells = state.width;
  const lines = [];
  let line = [];
  let used = 0;
  const widthOf = (g) => Math.max(0, state.ambiguous ? g.wide : g.width);
  for (const g of data.graphemes) {
    const w = widthOf(g);
    const cut = cuts.get(g.start);
    if (cut?.mandatory && line.length) {
      lines.push(line);
      line = [];
      used = 0;
    }
    if (used + w > cells && line.length) {
      let at = -1;
      for (let i = line.length - 1; i >= 1; i -= 1) {
        if (cuts.has(line[i].start)) {
          at = i;
          break;
        }
      }
      if (at < 0) at = line.length;
      lines.push(line.slice(0, at));
      line = line.slice(at);
      used = line.reduce((sum, item) => sum + widthOf(item), 0);
    }
    line.push(g);
    used += w;
  }
  if (line.length || !lines.length) lines.push(line);
  return lines;
}

function renderPostcard(data) {
  const card = $("#postcard");
  card.replaceChildren();
  const lines = wrap(data);
  for (const line of lines) {
    const row = el("div", "postcard-line");
    for (const g of line) {
      const text = g.text.replace(/\n/g, "¶");
      const piece = el("span", "", text === " " ? "\u00a0" : text);
      piece.dataset.tip = `${g.start}..${g.end}  ${g.gcb}  ${g.width} cells`;
      row.append(piece);
    }
    if (!line.length) row.append(el("span", "empty", "—"));
    card.append(row);
  }
  wireTips(card);
  const total = state.ambiguous ? data.wide : data.narrow;
  $("#wrap-note").textContent =
    `${lines.length} line${lines.length === 1 ? "" : "s"} out of ${total} cells. Long words break where UAX #14 allows, or at the last chance before the edge.`;
}

const ROWS = [
  ["upper", "Upper"],
  ["lower", "Lower"],
  ["title", "Title"],
  ["fold", "Fold"],
  ["simpleUpper", "Simple U"],
  ["simpleLower", "Simple L"],
  ["simpleTitle", "Simple T"],
];

function renderRack(data) {
  const rack = $("#rack-cards");
  rack.replaceChildren();
  data.case.forEach((item, i) => {
    const card = el("div", "rack-card");
    const head = el("div", "rack-head");
    head.append(el("span", "g", item.char));
    const spec = data.chars[i];
    head.append(
      el("span", "u", spec ? `${spec.hex}${spec.ccc ? ` · ccc ${spec.ccc}` : ""}` : ""),
    );
    card.append(head);
    for (const [key, label] of ROWS) {
      const row = el("div", "rack-row");
      row.append(el("span", "k", label));
      const value = item[key];
      const same = value === item.char;
      row.append(el("span", "v" + (same ? " same" : ""), same ? "—" : value));
      card.append(row);
    }
    const orbit = el("div", "orbit");
    for (const member of item.orbit) {
      orbit.append(el("span", member === item.char ? "self" : "", member));
    }
    card.append(orbit);
    rack.append(card);
  });
  wireTips(rack);
}

let frame = 0;
function render() {
  if (!ucd) return;
  const text = [...state.text].slice(0, 80).join("");
  let data;
  try {
    data = JSON.parse(ucd.analyse(text));
  } catch (e) {
    return;
  }
  renderManifest(data);
  renderPress(data);
  renderBelt(data);
  renderStrip(data);
  renderPostcard(data);
  renderRack(data);
}

function update() {
  cancelAnimationFrame(frame);
  frame = requestAnimationFrame(render);
}

function start() {
  tip = $("#tip");
  const input = $("#text");
  state.text = input.value;
  state.width = Number($("#width").value);
  $("#width-out").textContent = `${state.width} cells`;

  input.addEventListener("input", () => {
    state.text = input.value;
    update();
  });

  for (const plate of $$(".plate")) {
    plate.addEventListener("click", () => {
      state.form = plate.dataset.form;
      for (const other of $$(".plate")) {
        const on = other === plate;
        other.classList.toggle("on", on);
        other.setAttribute("aria-selected", String(on));
      }
      update();
    });
  }

  for (const stamp of $$(".stamp")) {
    stamp.addEventListener("click", () => {
      input.value = stamp.dataset.text;
      state.text = input.value;
      update();
      input.focus();
    });
  }

  const ambiguous = $("#ambiguous");
  ambiguous.addEventListener("change", () => {
    state.ambiguous = ambiguous.checked;
    update();
  });

  const width = $("#width");
  width.addEventListener("input", () => {
    state.width = Number(width.value);
    $("#width-out").textContent = `${state.width} cells`;
    update();
  });

  update();
}

if (ucd) {
  start();
} else {
  $("#text")?.setAttribute("disabled", "disabled");
  $("#press")?.insertAdjacentHTML(
    "afterbegin",
    '<div class="warn">The compiled library did not load, so the desks are still. ' +
      "The pages are built with it in CI: the JavaScript target of src/examples/browser.</div>",
  );
}
