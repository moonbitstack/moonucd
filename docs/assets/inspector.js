const ucd = await import("../engine/moonucd.js").catch(() => null);
if (ucd) {
  start();
} else {
  document.getElementById("ticket")?.insertAdjacentHTML("beforebegin",
    '<div class="warn">The compiled library did not load, so the live inspector is off. ' +
    'Everything else on this page still describes the package.</div>');
}

function start() {
  function esc(s){return String(s).replace(/[&<>]/g,function(c){return c==="&"?"&amp;":c==="<"?"&lt;":">";});}

  var charIn = document.getElementById("charIn");

  function inspect(ch){
    var cp = ch.codePointAt(0);
    try { return JSON.parse(ucd.inspect(cp)); }
    catch(e){ return null; }
  }

  function renderChar(){
    var raw = charIn.value;
    var ch = (Array.from(raw)[0]) || " ";
    var d = inspect(ch);
    if(!d){ return; }
    set("tGlyph", d.char);
    set("tCp", d.codepoint);
    set("tCat", d.category);
    set("tCatName", d.categoryName);
    set("tAge", d.age ? "Unicode " + d.age : "unassigned");
    set("tBlock", d.block || "no block");
    set("tScript", d.script);
    set("tBidi", d.bidi);
    set("tSerial", "UTF-8 · " + d.utf8);
    set("sCp", d.codepoint);
    set("sU8", d.utf8);
    set("sU16", d.utf16);
    set("sEaw", d.eaw);
    set("sWidth", d.width + (d.width===1?" cell":" cells"));
    set("sNum", d.numeric || "—");
    set("sEmoji", (d.emoji?"emoji":"not emoji") + (d.extPict?" · ext. pictographic":""));
    set("sName", d.name || "no name");
    set("sNorm", d.nfc + " / " + d.nfd);
    set("sIsNfc", d.isNFC?"yes":"no");
    set("sLb", d.lb);
  }
  function set(id,v){var el=document.getElementById(id); if(el) el.textContent=v;}

  charIn.addEventListener("input", renderChar);

  // gallery — each tile is a small luggage tag
  var picks = [
    ["中","Han ideograph"],["A","Latin capital"],["🚀","rocket"],["é","e acute"],
    ["Å","A ring"],["ǅ","DZ digraph"],["٣","Arabic-Indic 3"],["あ","Hiragana"],
    ["⚠","warning sign"],["🇨🇳","CN flag"],["—","em dash"],["©","copyright"]
  ];
  var gal = document.getElementById("gallery");
  picks.forEach(function(p){
    var cp = p[0].codePointAt(0).toString(16).toUpperCase();
    var a = document.createElement("div");
    a.className = "gal";
    a.innerHTML = '<div class="g">'+esc(p[0])+'</div>' +
                 '<div class="meta"><div class="lab">'+esc(p[1])+'</div>' +
                 '<div class="n">U+'+cp+'</div></div>';
    a.addEventListener("click", function(){
      charIn.value = p[0]; renderChar();
      document.getElementById("tour").scrollIntoView({behavior:"smooth"});
    });
    gal.appendChild(a);
  });

  // string tools
  var strIn = document.getElementById("strIn");
  function chip(text,cls){var c=document.createElement("span");c.className="chip"+(cls?" "+cls:"");c.textContent=text;return c;}
  function renderStr(){
    var s = strIn.value;
    var seg = JSON.parse(ucd.pieces(s));
    var gc = document.getElementById("grafChips"); gc.innerHTML="";
    seg.grapheme.forEach(function(g){gc.appendChild(chip(g,"g"));});
    var wc = document.getElementById("wordChips"); wc.innerHTML="";
    seg.words.forEach(function(w){wc.appendChild(chip(JSON.stringify(w)));});
    var so = document.getElementById("sentOut"); so.innerHTML="";
    seg.sentences.forEach(function(sn){var d=document.createElement("div");d.className="sent";d.textContent=sn;so.appendChild(d);});
    var lbc = document.getElementById("lbChips"); lbc.innerHTML="";
    seg.linebreaks.forEach(function(l){lbc.appendChild(chip(l,"b"));});
  }
  strIn.addEventListener("input", renderStr);

  // initial paint
  renderChar();
  renderStr();
}
