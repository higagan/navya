"""Round 4: resolve the specific blocks where consensus voting was close.

Rounds 1-2 checked words, round 3 asked for the book's layer vocabulary
in general. This one is narrower and more useful: consensus structuring
(5 independent readings per page, majority vote per block) came back with
a handful of blocks where the vote wasn't unanimous. A close vote can mean
the model is genuinely torn between two readings that only someone who
knows the text can settle — plain majority can't tell "close and right"
from "close and wrong" apart.

Shows exactly those blocks, with the scan and the vote tally in plain
language, and asks for one tap per block.
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

import books  # noqa: E402

OUT = HERE / "dist" / "round4.html"
BOOK = books.get("avayavaprakaranam")

pages = {}
with open(BASE / "output/jsonl/avayavaprakaranam/structured_pages.jsonl") as f:
    for line in f:
        if line.strip():
            d = json.loads(line)
            pages[d["pdf_page"]] = d

CANDIDATES = [
    {"dev": layer.name, "rom": layer.roman} for layer in BOOK.layers if layer.depth is not None
]

# Parse "section N: samples disagreed on layer — {...}" notes back into
# (section_index, vote_dict) so the page can show the real tally rather than
# just the winning label.
import ast
import re

VOTE_RE = re.compile(r"section (\d+): samples disagreed on layer — (\{.*?\})")

contested = []
for pdf_page, page in sorted(pages.items()):
    for note in page.get("review_notes", []):
        m = VOTE_RE.search(note)
        if not m:
            continue
        idx = int(m.group(1))
        votes = ast.literal_eval(m.group(2))
        if idx >= len(page["sections"]):
            continue
        contested.append(
            {
                "pdf_page": pdf_page,
                "printed_page": page.get("printed_page"),
                "section_index": idx,
                "current_layer": page["sections"][idx]["layer"],
                "text": page["sections"][idx]["text"],
                "votes": votes,
            }
        )

img_cache = {}


def scan_data_uri(pdf_page: int) -> str:
    if pdf_page not in img_cache:
        img = Image.open(BASE / f"output/pages/avayavaprakaranam/page-{pdf_page:03d}.png")
        img = img.convert("RGB")
        img.thumbnail((1000, 3000), Image.LANCZOS)
        buf = io.BytesIO()
        img.save(buf, "JPEG", quality=72, optimize=True)
        img_cache[pdf_page] = "data:image/jpeg;base64," + base64.b64encode(
            buf.getvalue()
        ).decode()
    return img_cache[pdf_page]


data = []
for c in contested:
    data.append(
        {
            "page": c["printed_page"],
            "image": scan_data_uri(c["pdf_page"]),
            "current": c["current_layer"],
            "text": c["text"],
            "votes": [{"layer": k, "n": v} for k, v in sorted(c["votes"].items(), key=lambda x: -x[1])],
        }
    )

payload = json.dumps({"blocks": data, "candidates": CANDIDATES}, ensure_ascii=False)
total = len(data)

html = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<meta name="robots" content="noindex, nofollow">
<meta name="theme-color" content="#17140F">
<title>Navya — close calls</title>
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
  .steps p { margin:0; }

  .block-card { margin:38px 0 0; padding-top:22px; border-top:1px solid var(--rule); }
  .b-head { display:flex; align-items:baseline; gap:11px; margin-bottom:6px; }
  .folio { font-family:var(--deva); font-size:26px; line-height:1; color:var(--vermilion); }
  .b-meta { font-family:var(--sans); font-size:12px; color:var(--muted); }

  .tally { display:flex; gap:8px; flex-wrap:wrap; margin:12px 0 0; }
  .tvote { font-family:var(--sans); font-size:12.5px; border:1px solid var(--rule);
           padding:6px 10px; display:flex; align-items:center; gap:6px; }
  .tvote .n { font-variant-numeric:tabular-nums; font-weight:700; }
  .tvote .l { font-family:var(--deva); font-size:15px; }
  .tvote.leader { border-color:var(--muted); background:#F2EFE9; }

  .scan-frame { margin-top:14px; overflow:auto; background:var(--panel);
                border:1px solid var(--rule); -webkit-overflow-scrolling:touch; }
  .scan-frame img { display:block; width:100%; height:auto; }
  .scan-frame.zoomed img { width:265%; max-width:none; }
  .scan-bar { display:flex; justify-content:space-between; align-items:center;
              gap:10px; margin-top:7px; }
  .scan-bar span { font-family:var(--sans); font-size:12px; color:var(--muted); }
  .plain-btn { font-family:var(--sans); font-size:12px; letter-spacing:.06em;
               text-transform:uppercase; background:none; border:1px solid var(--rule);
               color:var(--ink); padding:7px 11px; min-height:36px; cursor:pointer; }
  .plain-btn:hover { border-color:var(--ink); }
  .plain-btn:focus-visible { outline:2px solid var(--ink); outline-offset:2px; }

  .text-block { font-family:var(--deva); font-size:18px; line-height:2.0; margin:14px 0 0;
                padding:13px 15px; background:var(--panel); border:1px solid var(--rule);
                overflow-wrap:break-word; }
  .text-block .rest { display:none; }
  .block-card.open .text-block .rest { display:inline; }
  .more-btn { font-family:var(--sans); font-size:11.5px; color:var(--muted);
              background:none; border:none; padding:8px 0 0; text-decoration:underline;
              cursor:pointer; }

  .ask { font-family:var(--sans); font-size:11px; letter-spacing:.1em;
         text-transform:uppercase; color:var(--muted); margin:16px 0 9px; }
  .chips { display:flex; flex-wrap:wrap; gap:8px; }
  .chip { font-family:var(--deva); font-size:17px; background:none;
          border:1px solid var(--rule); color:var(--ink); padding:9px 14px;
          min-height:46px; cursor:pointer; line-height:1.5; }
  .chip .rom { font-family:var(--sans); font-size:10.5px; color:var(--muted);
               display:block; letter-spacing:.03em; text-transform:none; }
  .chip:hover { border-color:var(--ink); }
  .chip:focus-visible { outline:2px solid var(--ink); outline-offset:2px; }
  .chip.on { background:var(--sage); border-color:var(--sage); color:#fff; }
  .chip.on .rom { color:rgba(255,255,255,.8); }
  .block-card[data-answered] { border-top-color: var(--sage); }

  .tally2 { position:fixed; left:0; right:0; bottom:0; background:var(--ink);
            color:var(--paper); padding:11px 18px calc(11px + env(safe-area-inset-bottom));
            display:flex; align-items:center; gap:14px; justify-content:space-between;
            z-index:20; }
  .counts { font-family:var(--sans); font-size:13.5px; font-variant-numeric:tabular-nums; }
  .counts b { color:#8FCFAE; font-weight:700; }
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
    <p class="eyebrow">Avayavaprakaraṇam · round 4</p>
    <h1>The votes that were close</h1>
  </header>

  <div class="intro">
    <p>
      We now read each page five separate times and go with whichever label
      most of those readings agree on. That fixed pages coming back labelled
      differently every time we ran it.
    </p>
    <p>
      But on <strong>__TOTAL__ passages</strong>, the five readings didn't
      agree — sometimes only barely. When most readings agree, they can
      still all be making the same mistake, and there's no way for us to
      tell the difference from the vote alone.
    </p>
  </div>

  <div class="steps">
    <p>For each passage below, the count shows how the five readings split.
       <strong>Tap the name it should actually have</strong> — whichever
       label won the vote, or a different one if the vote got it wrong.</p>
  </div>

  <div id="blocks"></div>

  <footer>
    Avayavaprakaraṇam, ed. Jvālāprasād Gauḍ with the Vilāsinī commentary,
    Lok Sangam Prakashan, Varanasi, 1964.
  </footer>
</div>

<div class="tally2">
  <div class="counts">
    <span><b id="n-done">0</b>/__TOTAL__ resolved</span>
    <span class="c-sub" id="sub">tap a name under each passage</span>
  </div>
  <button class="copy-btn" id="copy">Copy answers</button>
</div>

<script type="application/json" id="data">__DATA__</script>
<script>
(function(){
  var D=JSON.parse(document.getElementById('data').textContent);
  var root=document.getElementById('blocks');
  function el(t,c,x){var n=document.createElement(t); if(c)n.className=c;
    if(x!==undefined)n.textContent=x; return n;}

  D.blocks.forEach(function(b, bi){
    var card=el('div','block-card');
    card.dataset.idx=bi;

    var head=el('div','b-head');
    head.appendChild(el('span','folio', b.page || '—'));
    head.appendChild(el('span','b-meta','page '+(b.page||'')+' of the book · currently labelled '+b.current));
    card.appendChild(head);

    var tally=el('div','tally');
    var maxN=Math.max.apply(null, b.votes.map(function(v){return v.n;}));
    var totalVotes=b.votes.reduce(function(s,v){return s+v.n;},0);
    b.votes.forEach(function(v){
      var t=el('span','tvote'+(v.n===maxN?' leader':''));
      t.appendChild(el('span','n', v.n+'/'+totalVotes));
      t.appendChild(el('span','l', v.layer));
      tally.appendChild(t);
    });
    card.appendChild(tally);

    var frame=el('div','scan-frame');
    var im=el('img'); im.src=b.image; im.alt='Scan of page '+(b.page||'');
    im.loading = bi===0 ? 'eager':'lazy';
    frame.appendChild(im); card.appendChild(frame);
    var bar=el('div','scan-bar');
    bar.appendChild(el('span',null,'Tap Enlarge, then drag sideways'));
    var zb=el('button','plain-btn','Enlarge'); zb.type='button';
    zb.addEventListener('click',function(){
      var on=frame.classList.toggle('zoomed');
      zb.textContent=on?'Fit page':'Enlarge';
    });
    bar.appendChild(zb); card.appendChild(bar);

    var head160=b.text.slice(0,220), rest=b.text.slice(220);
    var tb=el('div','text-block');
    tb.appendChild(document.createTextNode(head160));
    if(rest){ tb.appendChild(el('span','rest',rest)); }
    card.appendChild(tb);
    if(rest){
      var mb=el('button','more-btn','Show all of it'); mb.type='button';
      mb.addEventListener('click',function(){
        var on=card.classList.toggle('open');
        mb.textContent=on?'Show less':'Show all of it';
      });
      card.appendChild(mb);
    }

    card.appendChild(el('p','ask','This passage really is —'));
    var chips=el('div','chips');
    D.candidates.forEach(function(c){
      var cb=el('button','chip'); cb.type='button';
      cb.appendChild(document.createTextNode(c.dev));
      cb.appendChild(el('span','rom',c.rom));
      cb.addEventListener('click',function(){
        var already = card.dataset.answered===c.dev;
        chips.querySelectorAll('.chip').forEach(function(x){x.classList.remove('on');});
        if(already){ delete card.dataset.answered; }
        else { cb.classList.add('on'); card.dataset.answered=c.dev; }
        recount();
      });
      chips.appendChild(cb);
    });
    card.appendChild(chips);

    root.appendChild(card);
  });

  var nDone=document.getElementById('n-done'), sub=document.getElementById('sub');
  var total=D.blocks.length;
  function recount(){
    var done=document.querySelectorAll('.block-card[data-answered]').length;
    nDone.textContent=done;
    sub.textContent = done<total ? (total-done)+' still to resolve'
                                 : 'done — please copy the answers';
  }

  document.getElementById('copy').addEventListener('click',function(){
    var lines=['Avayavaprakaranam - round 4: close votes resolved',''];
    document.querySelectorAll('.block-card').forEach(function(c,i){
      var b=D.blocks[i];
      lines.push('page '+(b.page||'?')+' (was '+b.current+', vote '+
        b.votes.map(function(v){return v.layer+':'+v.n;}).join(' vs ')+
        ') -> '+(c.dataset.answered||'(not answered)'));
    });
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

html = html.replace("__DATA__", payload).replace("__TOTAL__", str(total))
OUT.write_text(html, encoding="utf-8")
print(f"wrote {OUT} — {round(len(html) / 1024 / 1024, 2)} MB, {total} contested blocks")
for c in contested:
    print(f"  p{c['pdf_page']} (printed {c['printed_page']}) sec{c['section_index']}: {c['votes']}")
