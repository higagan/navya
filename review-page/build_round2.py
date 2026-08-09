"""Round 2 of expert review.

Round 1 measured flag *precision* (6 of 20 flagged words were real errors).
It could not measure *recall*, because the expert only ever saw passages the
model had already doubted. This page closes both gaps:

  A. Confirm the systematic confusion rules. Each is one decision that
     corrects every occurrence in the book, so this is where the leverage is.
  B. Proofread one page in full, tapping every wrong word whether or not the
     model flagged it. Comparing that against what was flagged gives us the
     recall number we're missing.
"""

import base64
import io
import json
import re
import sys
from pathlib import Path

from PIL import Image

HERE = Path(__file__).parent
BASE = HERE.parent / "ocr-pipeline"
sys.path.insert(0, str(BASE))
from normalize import CONFUSIONS  # noqa: E402

PROOFREAD_PDF_PAGE = 20  # printed page ६
OUT = HERE / "dist" / "round2.html"

LAYER_DEV = {
    "mūla": "मूल",
    "gādādharī": "गादाधरी",
    "bāladevī": "बलदेवी",
    "vimalaprabhā": "विमलप्रभा",
    "footnote": "टिप्पणी",
    "header": "शीर्षक",
    "invocation": "मङ्गलाचरण",
}

pages = {}
with open(BASE / "output/jsonl/avayavaprakaranam/structured_pages.jsonl") as f:
    for line in f:
        if line.strip():
            d = json.loads(line)
            pages[d["pdf_page"]] = d

all_text = "".join(
    json.loads(line)["text"]
    for line in open(BASE / "output/jsonl/avayavaprakaranam/pages.jsonl")
    if line.strip()
)

rules = [
    {
        "wrong": c.wrong,
        "right": c.right,
        "note": c.note,
        "count": len(re.findall(re.escape(c.wrong), all_text)),
    }
    for c in CONFUSIONS
]

page = pages[PROOFREAD_PDF_PAGE]
img = Image.open(BASE / f"output/pages/avayavaprakaranam/page-{PROOFREAD_PDF_PAGE:03d}.png")
img = img.convert("RGB")
img.thumbnail((1100, 3200), Image.LANCZOS)
buf = io.BytesIO()
img.save(buf, "JPEG", quality=74, optimize=True)

# Which words did round 1 already flag? Used only to report recall afterwards —
# deliberately NOT surfaced in the UI, so his reading isn't anchored by it.
flagged_words = set()
for note in page.get("review_notes", []):
    for tok in re.findall(r"[ऀ-ॿ]{2,}", note):
        flagged_words.add(tok)

sections = [
    {
        "dev": LAYER_DEV.get(s["layer"], s["layer"]),
        "words": [w for w in s["text"].split() if w],
    }
    for s in page.get("sections", [])
]
total_words = sum(len(s["words"]) for s in sections)

payload = json.dumps(
    {
        "rules": rules,
        "page": page.get("printed_page"),
        "image": "data:image/jpeg;base64," + base64.b64encode(buf.getvalue()).decode(),
        "sections": sections,
        "flaggedWords": sorted(flagged_words),
    },
    ensure_ascii=False,
)

html = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<meta name="robots" content="noindex, nofollow">
<meta name="theme-color" content="#17140F">
<title>Navya — round 2</title>
<style>
  *, *::before, *::after { box-sizing: border-box; }
  body { margin: 0; }
  img { max-width: 100%; }
  :root {
    --ink:#17140F; --paper:#FAF8F4; --panel:#FFF; --rule:#DDD6CA; --muted:#6B6255;
    --vermilion:#A8321E; --vermilion-wash:#F7EBE7; --sage:#2F6B4F; --sage-wash:#E8F0EB;
    --sans: ui-sans-serif, system-ui, "Segoe UI", Roboto, sans-serif;
    --serif: Georgia, "Iowan Old Style", "Times New Roman", serif;
    --deva: "Noto Serif Devanagari","Noto Sans Devanagari","Devanagari Sangam MN",
            "Nirmala UI","Kohinoor Devanagari",serif;
  }
  body { background:var(--paper); color:var(--ink); font-family:var(--serif);
         line-height:1.6; -webkit-text-size-adjust:100%; }
  .wrap { max-width:680px; margin:0 auto; padding:0 18px 132px; }
  .masthead { padding:30px 0 18px; border-bottom:2px solid var(--ink); }
  .eyebrow { font-family:var(--sans); font-size:11px; letter-spacing:.14em;
             text-transform:uppercase; color:var(--vermilion); margin:0 0 9px; font-weight:600; }
  h1 { font-size:clamp(25px,6vw,32px); line-height:1.22; margin:0; font-weight:400;
       text-wrap:balance; }
  .intro { margin:20px 0 0; font-size:17px; }
  .intro p { margin:0 0 13px; }
  .part { margin:38px 0 0; padding-top:22px; border-top:1px solid var(--rule); }
  .part-no { font-family:var(--sans); font-size:11px; letter-spacing:.14em;
             text-transform:uppercase; color:var(--vermilion); font-weight:600;
             margin:0 0 8px; }
  h2 { font-size:23px; font-weight:400; margin:0 0 12px; line-height:1.3; }
  .lede { margin:0 0 6px; font-size:16.5px; }
  .steps { margin:16px 0 0; padding:16px 18px; background:var(--vermilion-wash);
           border-left:3px solid var(--vermilion); font-size:16px; }
  .steps p { margin:0; }

  .rule { border:1px solid var(--rule); background:var(--panel); margin:16px 0 0; }
  .rule-body { padding:15px 16px 12px; }
  .swap { display:flex; align-items:center; gap:12px; flex-wrap:wrap; }
  .word { font-family:var(--deva); font-size:25px; line-height:1.7; }
  .word.bad { color:var(--vermilion); }
  .word.good { color:var(--sage); }
  .arrow { font-family:var(--sans); color:var(--muted); font-size:17px; }
  .count { font-family:var(--sans); font-size:12.5px; color:var(--muted);
           margin:9px 0 0; }
  .why { font-family:var(--sans); font-size:13px; color:var(--muted);
         line-height:1.55; margin:9px 0 0; display:none; }
  .rule.open .why { display:block; }
  .why-btn { font-family:var(--sans); font-size:11.5px; color:var(--muted);
             background:none; border:none; padding:6px 0 0; text-decoration:underline;
             cursor:pointer; }
  .verdict { display:flex; border-top:1px solid var(--rule); }
  .verdict button { flex:1; font-family:var(--sans); font-size:13px; background:none;
                    border:none; border-right:1px solid var(--rule); padding:14px 6px;
                    min-height:50px; color:var(--muted); cursor:pointer; }
  .verdict button:last-child { border-right:none; }
  .verdict button:hover { background:#F2EFE9; color:var(--ink); }
  .verdict button:focus-visible { outline:2px solid var(--ink); outline-offset:-3px; }
  .rule[data-v="yes"] { border-color:var(--sage); }
  .rule[data-v="yes"] .v-yes { background:var(--sage); color:#fff; font-weight:700; }
  .rule[data-v="no"] { border-color:var(--vermilion); }
  .rule[data-v="no"] .v-no { background:var(--vermilion); color:#fff; font-weight:700; }

  .scan-frame { margin-top:15px; overflow:auto; background:var(--panel);
                border:1px solid var(--rule); -webkit-overflow-scrolling:touch; }
  .scan-frame img { display:block; width:100%; height:auto; }
  .scan-frame.zoomed img { width:265%; max-width:none; }
  .scan-bar { display:flex; justify-content:space-between; align-items:center;
              gap:10px; margin-top:7px; }
  .scan-bar span { font-family:var(--sans); font-size:12.5px; color:var(--muted); }
  .plain-btn { font-family:var(--sans); font-size:12px; letter-spacing:.06em;
               text-transform:uppercase; background:none; border:1px solid var(--rule);
               color:var(--ink); padding:8px 12px; min-height:38px; cursor:pointer; }
  .plain-btn:hover { border-color:var(--ink); }
  .plain-btn:focus-visible { outline:2px solid var(--ink); outline-offset:2px; }

  .layer { margin:22px 0 0; }
  .layer-dev { font-family:var(--deva); font-size:16px; color:var(--vermilion);
               margin-bottom:6px; }
  .text-block { font-family:var(--deva); font-size:20px; line-height:2.15;
                background:var(--panel); border:1px solid var(--rule);
                padding:14px 15px; }
  .tok { cursor:pointer; padding:1px 2px; border-radius:2px;
         border-bottom:1px dotted transparent; }
  .tok:hover { background:#F0EDE6; border-bottom-color:var(--muted); }
  .tok.wrong { background:var(--vermilion); color:#fff; }
  .tok:focus-visible { outline:2px solid var(--ink); outline-offset:1px; }

  .tally { position:fixed; left:0; right:0; bottom:0; background:var(--ink);
           color:var(--paper); padding:11px 18px calc(11px + env(safe-area-inset-bottom));
           display:flex; align-items:center; gap:14px; justify-content:space-between;
           z-index:20; }
  .counts { font-family:var(--sans); font-size:13.5px; font-variant-numeric:tabular-nums;
            line-height:1.35; }
  .counts b { font-weight:700; } .c-a { color:#8FCFAE; } .c-b { color:#F0907C; }
  .c-sub { opacity:.6; display:block; font-size:11.5px; }
  .copy-btn { font-family:var(--sans); font-size:12px; letter-spacing:.07em;
              text-transform:uppercase; background:none;
              border:1px solid rgba(250,248,244,.45); color:var(--paper);
              padding:11px 15px; min-height:44px; white-space:nowrap; cursor:pointer; }
  .copy-btn:hover { background:rgba(250,248,244,.12); }
  footer { margin-top:42px; padding-top:17px; border-top:1px solid var(--rule);
           font-family:var(--sans); font-size:12.5px; color:var(--muted); line-height:1.65; }
</style>
</head>
<body>
<div class="wrap">
  <header class="masthead">
    <p class="eyebrow">Avayavaprakaraṇam · round 2</p>
    <h1>Two things, and the first one is quick</h1>
  </header>

  <div class="intro">
    <p>
      Thank you — your last answers told us the transcription is in better
      shape than we feared. Fourteen of the twenty words you checked were fine.
    </p>
    <p>
      Looking at the six you marked wrong, most turned out to be the
      <em>same few mistakes</em> repeating. That's good news, and it's what
      the first part below is about.
    </p>
  </div>

  <section class="part">
    <p class="part-no">Part 1 · five questions</p>
    <h2>Is the computer always getting these wrong?</h2>
    <p class="lede">
      Each of these appears many times across the book. If you tell us one is
      always a mistake, we can correct every occurrence at once.
    </p>
    <div id="rules"></div>
  </section>

  <section class="part">
    <p class="part-no">Part 2 · one page, read properly</p>
    <h2>Please find the mistakes we didn't spot</h2>
    <p class="lede">
      Last time you only saw words the computer already doubted. So we still
      don't know what it gets wrong <em>without</em> realising.
    </p>
    <div class="steps">
      <p>
        Read this one page against the photo and <strong>tap every word that
        doesn't match</strong> — including any we never asked about. Tap again
        to undo.
      </p>
    </div>
    <div id="proof"></div>
  </section>

  <footer>
    Avayavaprakaraṇam, ed. Jvālāprasād Gauḍ with the Vilāsinī commentary,
    Lok Sangam Prakashan, Varanasi, 1964. Text exactly as the computer
    produced it — nothing corrected by hand.
  </footer>
</div>

<div class="tally">
  <div class="counts">
    <span><b class="c-a" id="n-rules">0</b>/__NRULES__ answered ·
          <b class="c-b" id="n-words">0</b> words marked</span>
    <span class="c-sub" id="sub">start with the five questions</span>
  </div>
  <button class="copy-btn" id="copy">Copy summary</button>
</div>

<script type="application/json" id="data">__DATA__</script>
<script>
(function(){
  var D=JSON.parse(document.getElementById('data').textContent);
  function el(t,c,x){var n=document.createElement(t); if(c)n.className=c;
    if(x!==undefined)n.textContent=x; return n;}

  var rulesRoot=document.getElementById('rules');
  D.rules.forEach(function(r,i){
    var box=el('div','rule'); box.dataset.i=i; box.dataset.wrong=r.wrong;
    var body=el('div','rule-body');
    var swap=el('div','swap');
    swap.appendChild(el('span','word bad',r.wrong));
    swap.appendChild(el('span','arrow','should be'));
    swap.appendChild(el('span','word good',r.right));
    body.appendChild(swap);
    body.appendChild(el('p','count','Appears '+r.count+
      (r.count===1?' time':' times')+' in the pages we have so far.'));
    var why=el('p','why',r.note);
    var wb=el('button','why-btn','Why we think so'); wb.type='button';
    wb.addEventListener('click',function(){
      var on=box.classList.toggle('open');
      wb.textContent=on?'Hide':'Why we think so';
    });
    body.appendChild(wb); body.appendChild(why);
    box.appendChild(body);
    var v=el('div','verdict');
    [['yes','Always wrong'],['no','Leave it alone']].forEach(function(p){
      var b=el('button','v-'+p[0],p[1]); b.type='button';
      b.addEventListener('click',function(){
        box.dataset.v = box.dataset.v===p[0] ? '' : p[0]; recount();
      });
      v.appendChild(b);
    });
    box.appendChild(v);
    rulesRoot.appendChild(box);
  });

  var proof=document.getElementById('proof');
  var head=el('div','swap');
  head.appendChild(el('span','word bad',D.page));
  head.appendChild(el('span','arrow','page '+D.page+' of the book'));
  proof.appendChild(head);

  var frame=el('div','scan-frame');
  var im=el('img'); im.src=D.image; im.alt='Photograph of page '+D.page;
  frame.appendChild(im); proof.appendChild(frame);
  var bar=el('div','scan-bar');
  bar.appendChild(el('span',null,'Tap Enlarge, then drag sideways'));
  var zb=el('button','plain-btn','Enlarge'); zb.type='button';
  zb.addEventListener('click',function(){
    var on=frame.classList.toggle('zoomed');
    zb.textContent=on?'Fit page':'Enlarge';
  });
  bar.appendChild(zb); proof.appendChild(bar);

  D.sections.forEach(function(s){
    var l=el('div','layer');
    l.appendChild(el('div','layer-dev',s.dev));
    var tb=el('div','text-block');
    s.words.forEach(function(w){
      var t=el('span','tok',w);
      t.tabIndex=0; t.setAttribute('role','button');
      function toggle(){ t.classList.toggle('wrong'); recount(); }
      t.addEventListener('click',toggle);
      t.addEventListener('keydown',function(e){
        if(e.key==='Enter'||e.key===' '){ e.preventDefault(); toggle(); }
      });
      tb.appendChild(t); tb.appendChild(document.createTextNode(' '));
    });
    l.appendChild(tb); proof.appendChild(l);
  });

  var nR=document.getElementById('n-rules'), nW=document.getElementById('n-words'),
      sub=document.getElementById('sub');
  function recount(){
    var answered=[].filter.call(document.querySelectorAll('.rule'),
                                function(b){return b.dataset.v;}).length;
    var marked=document.querySelectorAll('.tok.wrong').length;
    nR.textContent=answered; nW.textContent=marked;
    sub.textContent = answered<D.rules.length
      ? (D.rules.length-answered)+' question(s) left'
      : (marked===0 ? 'now read the page below' : 'done — please copy the summary');
  }

  document.getElementById('copy').addEventListener('click',function(){
    var lines=['Avayavaprakaranam - round 2',''],
        yes=[],no=[],un=[];
    document.querySelectorAll('.rule').forEach(function(b){
      var r=D.rules[+b.dataset.i];
      var line='  '+r.wrong+' -> '+r.right;
      if(b.dataset.v==='yes') yes.push(line);
      else if(b.dataset.v==='no') no.push(line);
      else un.push(line);
    });
    lines.push('ALWAYS WRONG, safe to fix everywhere ('+yes.length+'):');
    lines=lines.concat(yes.length?yes:['  (none)']);
    if(no.length){ lines.push('','LEAVE ALONE ('+no.length+'):'); lines=lines.concat(no); }
    if(un.length){ lines.push('','NOT ANSWERED ('+un.length+'):'); lines=lines.concat(un); }

    var marked=[].map.call(document.querySelectorAll('.tok.wrong'),
                           function(t){return t.textContent;});
    lines.push('','PAGE '+D.page+' - wrong words found by reading in full ('+marked.length+'):');
    lines=lines.concat(marked.length?marked.map(function(w){return '  '+w;}):['  (none found)']);

    var out=lines.join('\\n');
    var btn=document.getElementById('copy');
    function done(){ btn.textContent='Copied';
      setTimeout(function(){btn.textContent='Copy summary';},1800); }
    if(navigator.clipboard&&navigator.clipboard.writeText){
      navigator.clipboard.writeText(out).then(done,fb);
    } else fb();
    function fb(){
      var ta=document.createElement('textarea'); ta.value=out;
      ta.style.position='fixed'; ta.style.opacity='0';
      document.body.appendChild(ta); ta.select();
      try{ document.execCommand('copy'); done(); }
      catch(e){ btn.textContent='Select & copy'; ta.style.opacity='1'; }
      setTimeout(function(){ta.remove();},100);
    }
  });

  recount();
})();
</script>
</body>
</html>
"""

html = html.replace("__DATA__", payload).replace("__NRULES__", str(len(rules)))
OUT.write_text(html, encoding="utf-8")
print(f"wrote {OUT} — {round(len(html) / 1024 / 1024, 2)} MB")
print(f"{len(rules)} rules; proofread page {page.get('printed_page')} with {total_words} words")
print(f"({len(flagged_words)} words were flagged in round 1 — held back for recall scoring)")
