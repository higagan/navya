"""Round 3: ask the expert what the parts of the page actually are.

Rounds 1 and 2 checked words. This one checks structure, which matters more
for the project's goal — tracing a topic through its commentary layers is
worthless if the layers are labelled wrong.

They are currently labelled wrong, and the cause was ours: the layer names
were hardcoded into the model's prompt, and they were the names from a
different volume. So the model reported a Bāladevī section in a book that
has none and never once labelled the Dīdhiti the expert says is present.

Rather than guess again, this page shows him each block we split out and
asks him to name it. The candidate names are taken from the volume's own
title page, not invented, and there's an "something else" option so the
list can't quietly constrain his answer the way the prompt did.
"""

import base64
import io
import json
import sys
from pathlib import Path

from PIL import Image

HERE = Path(__file__).parent
BASE = HERE.parent / "ocr-pipeline"
sys.path.insert(0, str(BASE))

PAGES = [17, 18]
OUT = HERE / "dist" / "round3.html"

# Names printed on this volume's own title page, plus the one the expert
# named unprompted (Dīdhiti). Deliberately no guess about which is which.
CANDIDATES = [
    {"dev": "मूल", "rom": "Mūla — the root text"},
    {"dev": "दीधिति", "rom": "Dīdhiti"},
    {"dev": "गादाधरी", "rom": "Gādādharī"},
    {"dev": "विलासिनी", "rom": "Vilāsinī"},
    {"dev": "टिप्पणी", "rom": "Footnote"},
    {"dev": "शीर्षक", "rom": "Running header"},
]

pages = {}
with open(BASE / "output/jsonl/avayavaprakaranam/structured_pages.jsonl") as f:
    for line in f:
        if line.strip():
            d = json.loads(line)
            pages[d["pdf_page"]] = d

data = []
for n in PAGES:
    p = pages[n]
    img = Image.open(BASE / f"output/pages/avayavaprakaranam/page-{n:03d}.png").convert("RGB")
    img.thumbnail((1100, 3200), Image.LANCZOS)
    buf = io.BytesIO()
    img.save(buf, "JPEG", quality=74, optimize=True)
    data.append(
        {
            "page": p.get("printed_page"),
            "image": "data:image/jpeg;base64," + base64.b64encode(buf.getvalue()).decode(),
            "blocks": [
                {"text": s["text"], "chars": len(s["text"])} for s in p.get("sections", [])
            ],
        }
    )

payload = json.dumps({"pages": data, "candidates": CANDIDATES}, ensure_ascii=False)
total_blocks = sum(len(d["blocks"]) for d in data)

html = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<meta name="robots" content="noindex, nofollow">
<meta name="theme-color" content="#17140F">
<title>Navya — what are these parts called?</title>
<style>
  *, *::before, *::after { box-sizing:border-box; }
  body { margin:0; }
  img { max-width:100%; }
  :root {
    --ink:#17140F; --paper:#FAF8F4; --panel:#FFF; --rule:#DDD6CA; --muted:#6B6255;
    --vermilion:#A8321E; --vermilion-wash:#F7EBE7; --sage:#2F6B4F;
    --sans: ui-sans-serif, system-ui, "Segoe UI", Roboto, sans-serif;
    --serif: Georgia, "Iowan Old Style", "Times New Roman", serif;
    --deva: "Noto Serif Devanagari","Noto Sans Devanagari","Devanagari Sangam MN",
            "Nirmala UI","Kohinoor Devanagari",serif;
  }
  body { background:var(--paper); color:var(--ink); font-family:var(--serif);
         line-height:1.6; -webkit-text-size-adjust:100%; }
  .wrap { max-width:680px; margin:0 auto; padding:0 18px 140px; }
  .masthead { padding:30px 0 18px; border-bottom:2px solid var(--ink); }
  .eyebrow { font-family:var(--sans); font-size:11px; letter-spacing:.14em;
             text-transform:uppercase; color:var(--vermilion); margin:0 0 9px;
             font-weight:600; }
  h1 { font-size:clamp(25px,6vw,32px); line-height:1.22; margin:0; font-weight:400;
       text-wrap:balance; }
  .intro { margin:20px 0 0; font-size:17px; }
  .intro p { margin:0 0 13px; }
  .intro p:last-child { margin-bottom:0; }
  .steps { margin:20px 0 0; padding:17px 19px; background:var(--vermilion-wash);
           border-left:3px solid var(--vermilion); font-size:16.5px; }
  .steps p { margin:0 0 9px; } .steps p:last-child { margin-bottom:0; }

  .page-card { margin:38px 0 0; padding-top:22px; border-top:1px solid var(--rule); }
  .page-head { display:flex; align-items:baseline; gap:11px; }
  .folio { font-family:var(--deva); font-size:32px; line-height:1; color:var(--vermilion); }
  .page-meta { font-family:var(--sans); font-size:12.5px; color:var(--muted); }
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

  .block { border:1px solid var(--rule); background:var(--panel); margin:18px 0 0; }
  .block-head { display:flex; align-items:baseline; gap:9px; padding:13px 15px 0; }
  .where { font-family:var(--sans); font-size:11px; letter-spacing:.1em;
           text-transform:uppercase; color:var(--muted); }
  .snippet { font-family:var(--deva); font-size:18px; line-height:1.95;
             margin:7px 0 0; padding:0 15px 12px; overflow-wrap:break-word; }
  .snippet .rest { display:none; }
  .block.open .snippet .rest { display:inline; }
  .more-btn { font-family:var(--sans); font-size:11.5px; color:var(--muted);
              background:none; border:none; padding:0 15px 11px; text-decoration:underline;
              cursor:pointer; }
  .ask { font-family:var(--sans); font-size:12px; letter-spacing:.08em;
         text-transform:uppercase; color:var(--muted); padding:0 15px 9px; }
  .chips { display:flex; flex-wrap:wrap; gap:8px; padding:0 15px 15px; }
  .chip { font-family:var(--deva); font-size:17px; background:none;
          border:1px solid var(--rule); color:var(--ink); padding:9px 14px;
          min-height:46px; cursor:pointer; line-height:1.5; }
  .chip .rom { font-family:var(--sans); font-size:10.5px; color:var(--muted);
               display:block; letter-spacing:.03em; text-transform:none; }
  .chip:hover { border-color:var(--ink); }
  .chip:focus-visible { outline:2px solid var(--ink); outline-offset:2px; }
  .chip.on { background:var(--sage); border-color:var(--sage); color:#fff; }
  .chip.on .rom { color:rgba(255,255,255,.8); }
  .block[data-named] { border-color:var(--sage); }

  .freeform { margin:38px 0 0; padding-top:22px; border-top:1px solid var(--rule); }
  label { display:block; font-size:16.5px; margin-bottom:10px; }
  textarea { width:100%; min-height:110px; font-family:var(--serif); font-size:16px;
             padding:12px 13px; border:1px solid var(--rule); background:var(--panel);
             color:var(--ink); line-height:1.6; resize:vertical; }
  textarea:focus-visible { outline:2px solid var(--ink); outline-offset:1px; }

  .tally { position:fixed; left:0; right:0; bottom:0; background:var(--ink);
           color:var(--paper); padding:11px 18px calc(11px + env(safe-area-inset-bottom));
           display:flex; align-items:center; gap:14px; justify-content:space-between;
           z-index:20; }
  .counts { font-family:var(--sans); font-size:13.5px; font-variant-numeric:tabular-nums;
            line-height:1.35; }
  .counts b { font-weight:700; color:#8FCFAE; }
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
    <p class="eyebrow">Avayavaprakaraṇam · round 3</p>
    <h1>What are these parts of the page called?</h1>
  </header>

  <div class="intro">
    <p>
      You told us the गादाधरी is the upper portion, not the lower one, and that
      the दीधिति is the part sometimes set in smaller type. You were right, and
      we had it wrong.
    </p>
    <p>
      The mistake was ours: we gave the computer a list of commentary names
      taken from the <em>other</em> book — the Sāmānyanirukti — so it was never
      able to name the parts of this one correctly.
    </p>
    <p>
      Rather than guess again, we would like you to tell us.
    </p>
  </div>

  <div class="steps">
    <p>The computer split each page into parts. For each part below,
       <strong>tap the name it should have.</strong></p>
    <p>If a part shouldn't be split like that at all, or the right name isn't
       offered, say so in the box at the bottom.</p>
  </div>

  <div id="pages"></div>

  <section class="freeform">
    <label for="how">
      Last thing, and the most useful: <strong>how do you tell these parts apart
      when you look at a page?</strong> Type size, indentation, where it sits,
      the words it opens with — whatever you actually go by.
    </label>
    <textarea id="how" placeholder="However you'd explain it to a student…"></textarea>
  </section>

  <footer>
    Avayavaprakaraṇam, ed. Jvālāprasād Gauḍ with the Vilāsinī commentary,
    Lok Sangam Prakashan, Varanasi, 1964. The names offered are taken from the
    volume's own title page.
  </footer>
</div>

<div class="tally">
  <div class="counts">
    <span><b id="n-done">0</b>/__TOTAL__ parts named</span>
    <span class="c-sub" id="sub">tap a name under each part</span>
  </div>
  <button class="copy-btn" id="copy">Copy answers</button>
</div>

<script type="application/json" id="data">__DATA__</script>
<script>
(function(){
  var D=JSON.parse(document.getElementById('data').textContent);
  function el(t,c,x){var n=document.createElement(t); if(c)n.className=c;
    if(x!==undefined)n.textContent=x; return n;}
  var ordinals=['1st','2nd','3rd','4th','5th','6th','7th','8th'];
  var root=document.getElementById('pages');

  D.pages.forEach(function(p,pi){
    var card=el('section','page-card');
    var head=el('div','page-head');
    head.appendChild(el('span','folio',p.page));
    head.appendChild(el('span','page-meta','page '+p.page+' of the book'));
    card.appendChild(head);

    var frame=el('div','scan-frame');
    var im=el('img'); im.src=p.image; im.alt='Photograph of page '+p.page;
    im.loading = pi===0 ? 'eager':'lazy';
    frame.appendChild(im); card.appendChild(frame);
    var bar=el('div','scan-bar');
    bar.appendChild(el('span',null,'Tap Enlarge, then drag sideways'));
    var zb=el('button','plain-btn','Enlarge'); zb.type='button';
    zb.addEventListener('click',function(){
      var on=frame.classList.toggle('zoomed');
      zb.textContent=on?'Fit page':'Enlarge';
    });
    bar.appendChild(zb); card.appendChild(bar);

    p.blocks.forEach(function(b,bi){
      var box=el('div','block');
      box.dataset.page=p.page; box.dataset.bi=bi+1;

      var bh=el('div','block-head');
      bh.appendChild(el('span','where',
        (ordinals[bi]||(bi+1)+'th')+' part from the top · '+b.chars+' letters'));
      box.appendChild(bh);

      var head160=b.text.slice(0,160), rest=b.text.slice(160);
      var sn=el('p','snippet'); sn.appendChild(document.createTextNode(head160));
      if(rest){
        var r=el('span','rest',rest); sn.appendChild(r);
      }
      box.appendChild(sn);
      if(rest){
        var mb=el('button','more-btn','Show all of it'); mb.type='button';
        mb.addEventListener('click',function(){
          var on=box.classList.toggle('open');
          mb.textContent=on?'Show less':'Show all of it';
        });
        box.appendChild(mb);
      }

      box.appendChild(el('p','ask','This part is —'));
      var chips=el('div','chips');
      D.candidates.forEach(function(c){
        var b2=el('button','chip'); b2.type='button';
        b2.appendChild(document.createTextNode(c.dev));
        b2.appendChild(el('span','rom',c.rom));
        b2.addEventListener('click',function(){
          var already = box.dataset.named===c.dev;
          chips.querySelectorAll('.chip').forEach(function(x){x.classList.remove('on');});
          if(already){ delete box.dataset.named; }
          else { b2.classList.add('on'); box.dataset.named=c.dev; }
          recount();
        });
        chips.appendChild(b2);
      });
      box.appendChild(chips);
      card.appendChild(box);
    });

    root.appendChild(card);
  });

  var nDone=document.getElementById('n-done'), sub=document.getElementById('sub');
  var total=document.querySelectorAll('.block').length;
  function recount(){
    var done=document.querySelectorAll('.block[data-named]').length;
    nDone.textContent=done;
    sub.textContent = done<total ? (total-done)+' still to name'
                                 : 'done — please copy the answers';
  }

  document.getElementById('copy').addEventListener('click',function(){
    var lines=['Avayavaprakaranam - round 3: what the parts are',''];
    var cur=null;
    document.querySelectorAll('.block').forEach(function(b){
      if(b.dataset.page!==cur){ cur=b.dataset.page; lines.push('Page '+cur+':'); }
      lines.push('  part '+b.dataset.bi+' = '+(b.dataset.named||'(not named)'));
    });
    var how=document.getElementById('how').value.trim();
    lines.push('','How to tell them apart:');
    lines.push(how? '  '+how.replace(/\\n/g,'\\n  ') : '  (not answered)');
    var out=lines.join('\\n');
    var btn=document.getElementById('copy');
    function done(){ btn.textContent='Copied';
      setTimeout(function(){btn.textContent='Copy answers';},1800); }
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

html = html.replace("__DATA__", payload).replace("__TOTAL__", str(total_blocks))
OUT.write_text(html, encoding="utf-8")
print(f"wrote {OUT} — {round(len(html) / 1024 / 1024, 2)} MB")
print(f"{len(data)} pages, {total_blocks} blocks to name, {len(CANDIDATES)} candidate names")
