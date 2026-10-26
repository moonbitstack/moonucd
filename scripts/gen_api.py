"""Write docs/api.html from each package's interface file and the `///`
comments in its sources, so the reference follows the code. Usage:
python scripts/gen_api.py, from the repository root."""
import html
import pathlib
import re

ROOT = pathlib.Path(__file__).resolve().parent.parent
PACKAGES = [
    ("moonucd", "src", "What a character is and how it changes case."),
    ("age", "src/age", "The Unicode version that first assigned a code point."),
    ("block", "src/block", "The block a code point sits in, and the range of a block."),
    ("name", "src/name", "The name of a code point, and the code point a name names."),
    ("script", "src/script", "The script of a code point, and the scripts it is shared with."),
    ("normalize", "src/normalize", "The four normalization forms of UAX #15, combining classes and decompositions."),
    ("width", "src/width", "Terminal cells and East Asian Width."),
    ("segment", "src/segment", "Grapheme clusters, words and sentences, by UAX #29."),
    ("linebreak", "src/linebreak", "Line-break opportunities, by UAX #14."),
]
DECL = re.compile(r"^pub(?:\((?:all|open)\))?\s+(fn|let|struct|enum|suberror|trait|type)\s+([A-Za-z_]\w*(?:::[A-Za-z_]\w*)?)")
TRAIT_METHODS = re.compile(r"::(equal|not_equal|output|to_string|to_repr|hash|hash_combine|compare)\(")


def sources(folder):
    for path in sorted((ROOT / folder).glob("*.mbt")):
        if not path.name.endswith("_test.mbt"):
            yield path.read_text(encoding="utf-8").splitlines()


def docs_of(folder):
    """Doc comments by declared name, and inline `//` notes by `Enum.Variant`."""
    out = {}
    for lines in sources(folder):
        pending, owner = [], None
        for line in lines:
            stripped = line.strip()
            if stripped == "///|":
                pending = []
                continue
            if stripped.startswith("///"):
                pending.append(stripped[3:].strip())
                continue
            m = DECL.match(line)
            if m:
                if pending:
                    out[m.group(2)] = " ".join(pending)
                owner = m.group(2) if m.group(1) == "enum" and line.rstrip().endswith("{") else None
                pending = []
                continue
            if owner:
                if line.startswith("}"):
                    owner = None
                else:
                    v = re.match(r"\s+([A-Z]\w*)\s*(?://\s*(.*))?$", line)
                    if v and v.group(2):
                        out[owner + "." + v.group(1)] = v.group(2)
            pending = []
    return out


def items_of(folder):
    """Declarations from the interface file, in the order it lists them."""
    lines = (ROOT / folder / "pkg.generated.mbti").read_text(encoding="utf-8").splitlines()
    items, block = [], None
    for line in lines:
        if block is not None:
            if line.startswith("}"):
                items.append(block)
                block = None
            else:
                block["variants"].append(line.strip())
            continue
        m = re.match(r"pub(?:\((?:all|open)\))?\s+(enum|struct|suberror)\s+(\w+)", line)
        if m:
            block = {"kind": m.group(1), "name": m.group(2), "sig": line.rstrip(" {"), "variants": []}
            if not line.rstrip().endswith("{"):
                items.append(block)
                block = None
            continue
        m = re.match(r"pub fn (\w+)::(\w+)", line)
        if m:
            items.append({"kind": "method", "name": m.group(1) + "::" + m.group(2), "sig": line, "owner": m.group(1)})
            continue
        m = re.match(r"pub fn (\w+)", line)
        if m:
            items.append({"kind": "fn", "name": m.group(1), "sig": line})
            continue
        m = re.match(r"pub impl (\w+) for (\w+)", line)
        if m:
            items.append({"kind": "impl", "name": m.group(1), "sig": line, "owner": m.group(2)})
    return items


def prose(text):
    if not text:
        return ""
    text = re.sub(r"`([^`]+)`", r"<code>\1</code>", html.escape(text, quote=False))
    return f"<p>{text}</p>"


def sig(text):
    return f'<pre class="sig">{html.escape(text.strip(), quote=False)}</pre>'


def anchor(pkg, name):
    return f"{pkg}-{name}".replace("::", "-").lower()


def render():
    nav, body = [], []
    for pkg, folder, intro in PACKAGES:
        docs, items = docs_of(folder), items_of(folder)
        route = "moonbitstack/moonucd" if pkg == "moonucd" else f"moonbitstack/moonucd/{pkg}"
        types = [i for i in items if i["kind"] in ("enum", "struct", "suberror")]
        fns = [i for i in items if i["kind"] == "fn"]
        methods, impls = {}, {}
        for i in items:
            if i["kind"] == "method" and not TRAIT_METHODS.search(i["sig"]):
                methods.setdefault(i["owner"], []).append(i)
            if i["kind"] == "impl":
                impls.setdefault(i["owner"], []).append(i["name"])
        nav.append(f'<li><a href="#{anchor(pkg, "top")}">{pkg}</a><ol class="sub">')
        nav += [f'<li><a href="#{anchor(pkg, i["name"])}">{i["name"]}</a></li>' for i in fns + types]
        nav.append("</ol></li>")
        body.append(f'<section id="{anchor(pkg, "top")}">')
        body.append(f'<div class="band-head"><h2>{pkg}</h2><span class="route">{route}</span></div>')
        body.append(prose(intro))
        for f in fns:
            body.append(f'<div class="entry" id="{anchor(pkg, f["name"])}">')
            body.append(f'<h3><span class="kind">fn</span>{f["name"]}</h3>')
            body.append(sig(f["sig"]) + prose(docs.get(f["name"], "")) + "</div>")
        for t in types:
            body.append(f'<div class="entry" id="{anchor(pkg, t["name"])}">')
            body.append(f'<h3><span class="kind">{t["kind"]}</span>{t["name"]}</h3>')
            body.append(prose(docs.get(t["name"], "")))
            body.append(sig(t["sig"] + (" {" if t["variants"] else "")))
            if t["variants"]:
                chips = []
                for v in t["variants"]:
                    note = docs.get(f'{t["name"]}.{v}', "")
                    chips.append(f"<li>{html.escape(v)}" + (f"<small>{html.escape(note)}</small>" if note else "") + "</li>")
                body.append(f'<ul class="variants">{"".join(chips)}</ul>')
            if impls.get(t["name"]):
                body.append(prose("Implements " + ", ".join(f"`{n}`" for n in impls[t["name"]]) + "."))
            for m in methods.get(t["name"], []):
                body.append(f'<div class="member" id="{anchor(pkg, m["name"])}">{sig(m["sig"])}{prose(docs.get(m["name"], ""))}</div>')
            body.append("</div>")
        body.append("</section>")
    page = (ROOT / "docs" / "api.template.html").read_text(encoding="utf-8")
    page = page.replace("<!-- nav -->", "\n".join(nav)).replace("<!-- body -->", "\n".join(body))
    (ROOT / "docs" / "api.html").write_text(page, encoding="utf-8", newline="\n")


render()
