"""The reader: pick a passage, see its commentary stack.

This is the thing the project exists for. A student reading Navya Nyāya
has to trace a topic up and down through layers of commentary, and the
tracing is the part that normally needs a guru. Here: tap a passage, see
what it is glossing above it and who glosses it below, each with the
printed page it came from and the scan to check against.

The links are machine-made and an adversarial audit found roughly a third
of an earlier version wrong, so this page states plainly which passages
were linked automatically and which the machine could not place. A reader
that presents a guess as a citation would be worse than no reader.
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
from export_reader import build  # noqa: E402

OUT = HERE / "dist" / "reader.html"
BOOK = books.get("avayavaprakaranam")

data = build(BASE / "output/jsonl/avayavaprakaranam/structured_pages.jsonl")

# Scans, one per page that has passages.
scans = {}
for pdf_page in sorted({p["pdf_page"] for p in data["passages"]}):
    img = Image.open(BASE / f"output/pages/avayavaprakaranam/page-{pdf_page:03d}.png")
    img = img.convert("RGB")
    img.thumbnail((950, 2800), Image.LANCZOS)
    buf = io.BytesIO()
    img.save(buf, "JPEG", quality=70, optimize=True)
    scans[str(pdf_page)] = "data:image/jpeg;base64," + base64.b64encode(buf.getvalue()).decode()

roman = {layer.name: layer.roman for layer in BOOK.layers}
depths = {k: v for k, v in BOOK.depths.items()}

payload = json.dumps(
    {
        "passages": data["passages"],
        "glosses": data["glosses"],
        "stats": data["stats"],
        "scans": scans,
        "roman": roman,
        "depths": depths,
        "title": BOOK.title,
        "edition": BOOK.edition,
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
<title>Navya — commentary reader</title>
<style>
  *, *::before, *::after { box-sizing:border-box; }
  body { margin:0; }
  img { max-width:100%; }
  :root {
    --ink:#17140F; --paper:#FAF8F4; --panel:#FFF; --rule:#DDD6CA; --muted:#6B6255;
    --vermilion:#A8321E; --vermilion-wash:#F7EBE7; --sage:#2F6B4F; --sage-wash:#E9F0EB;
    --amber:#8A6D1F; --amber-wash:#F7F0DC;
    --sans: ui-sans-serif, system-ui, "Segoe UI", Roboto, sans-serif;
    --serif: Georgia, "Iowan Old Style", "Times New Roman", serif;
    --deva: "Noto Serif Devanagari","Noto Sans Devanagari","Devanagari Sangam MN",
            "Nirmala UI","Kohinoor Devanagari",serif;
  }
  body { background:var(--paper); color:var(--ink); font-family:var(--serif);
         line-height:1.6; -webkit-text-size-adjust:100%; }
  .wrap { max-width:760px; margin:0 auto; padding:0 18px 40px; }

  header.top { padding:26px 0 16px; border-bottom:2px solid var(--ink); }
  .eyebrow { font-family:var(--sans); font-size:11px; letter-spacing:.14em;
             text-transform:uppercase; color:var(--vermilion); margin:0 0 8px;
             font-weight:600; }
  h1 { font-size:clamp(23px,5.4vw,29px); line-height:1.22; margin:0 0 8px;
       font-weight:400; text-wrap:balance; }
  .sub { font-family:var(--sans); font-size:12.5px; color:var(--muted); margin:0; }

  .howto { margin:16px 0 0; padding:14px 17px; background:var(--vermilion-wash);
           border-left:3px solid var(--vermilion); font-size:16px; }
  .howto p { margin:0; }

  .pagebar { display:flex; gap:6px; flex-wrap:wrap; margin:22px 0 0;
             padding-bottom:14px; border-bottom:1px solid var(--rule); }
  .pagebar button { font-family:var(--deva); font-size:17px; background:none;
                    border:1px solid var(--rule); color:var(--ink);
                    min-width:44px; min-height:42px; cursor:pointer; }
  .pagebar button:hover { border-color:var(--ink); }
  .pagebar button:focus-visible { outline:2px solid var(--ink); outline-offset:2px; }
  .pagebar button.on { background:var(--ink); border-color:var(--ink); color:var(--paper); }

  .layout { display:grid; gap:20px; margin-top:20px; }
  @media (min-width:860px) { .layout { grid-template-columns:1fr 300px;
                                       align-items:start; } }

  .passage { border:1px solid var(--rule); background:var(--panel);
             margin:0 0 12px; cursor:pointer; }
  .passage:hover { border-color:var(--muted); }
  .passage.sel { border-color:var(--ink); border-width:2px; }
  .p-head { display:flex; align-items:baseline; gap:9px; flex-wrap:wrap;
            padding:11px 14px 0; }
  .p-layer { font-family:var(--deva); font-size:16px; color:var(--vermilion); }
  .p-roman { font-family:var(--sans); font-size:10.5px; letter-spacing:.09em;
             text-transform:uppercase; color:var(--muted); }
  .p-cite { font-family:var(--sans); font-size:11.5px; color:var(--muted);
            margin-left:auto; }
  .p-text { font-family:var(--deva); font-size:18px; line-height:2.0;
            margin:6px 0 0; padding:0 14px 13px; overflow-wrap:break-word; }
  .passage.collapsed .p-text { display:-webkit-box; -webkit-line-clamp:3;
                               -webkit-box-orient:vertical; overflow:hidden; }
  mark { background:var(--amber-wash); color:inherit;
         box-shadow:inset 0 -2px 0 var(--amber); }
  mark.target { background:var(--sage-wash); box-shadow:inset 0 -2px 0 var(--sage); }

  aside { position:sticky; top:14px; }
  .stack { border:1px solid var(--rule); background:var(--panel); }
  .stack h2 { font-family:var(--sans); font-size:11px; letter-spacing:.13em;
              text-transform:uppercase; color:var(--muted); margin:0;
              padding:13px 15px 10px; border-bottom:1px solid var(--rule); }
  .stack-body { padding:13px 15px 15px; }
  .empty { font-family:var(--sans); font-size:13.5px; color:var(--muted); margin:0;
           line-height:1.6; }
  .rel { margin:0 0 14px; }
  .rel:last-child { margin-bottom:0; }
  .rel-h { font-family:var(--sans); font-size:11px; letter-spacing:.1em;
           text-transform:uppercase; color:var(--muted); margin:0 0 7px; }
  .rel-item { border-left:2px solid var(--rule); padding:2px 0 2px 11px;
              margin:0 0 9px; cursor:pointer; }
  .rel-item:hover { border-left-color:var(--ink); }
  .rel-item .q { font-family:var(--deva); font-size:16px; line-height:1.7; }
  .rel-item .m { font-family:var(--sans); font-size:11.5px; color:var(--muted);
                 display:block; margin-top:2px; }
  .rel-item.up { border-left-color:var(--sage); }
  .rel-item.down { border-left-color:var(--vermilion); }

  .unplaced { margin-top:13px; padding-top:12px; border-top:1px dashed var(--rule); }
  .unplaced .rel-h { color:var(--amber); }
  .unplaced .q { font-family:var(--deva); font-size:15px; }

  .scanbox { margin-top:16px; }
  .scan-frame { overflow:auto; border:1px solid var(--rule); background:var(--panel);
                -webkit-overflow-scrolling:touch; }
  .scan-frame img { display:block; width:100%; height:auto; }
  .scan-frame.zoomed img { width:250%; max-width:none; }
  .scan-bar { display:flex; justify-content:space-between; align-items:center;
              gap:10px; margin-top:7px; }
  .scan-bar span { font-family:var(--sans); font-size:12px; color:var(--muted); }
  .plain-btn { font-family:var(--sans); font-size:12px; letter-spacing:.06em;
               text-transform:uppercase; background:none; border:1px solid var(--rule);
               color:var(--ink); padding:7px 11px; min-height:36px; cursor:pointer; }
  .plain-btn:hover { border-color:var(--ink); }
  .plain-btn:focus-visible { outline:2px solid var(--ink); outline-offset:2px; }

  footer { margin-top:34px; padding-top:16px; border-top:1px solid var(--rule);
           font-family:var(--sans); font-size:12px; color:var(--muted); line-height:1.7; }
  footer b { color:var(--ink); font-weight:600; }
</style>
</head>
<body>
<div class="wrap">
  <header class="top">
    <p class="eyebrow">Navya · commentary reader</p>
    <h1 id="title"></h1>
    <p class="sub" id="edition"></p>
  </header>

  <div class="howto">
    <p><strong>Tap any passage</strong> to see what it is explaining, and who
       explains it in turn.</p>
  </div>

  <div class="pagebar" id="pagebar"></div>

  <div class="layout">
    <main id="page"></main>
    <aside>
      <div class="stack">
        <h2>Commentary stack</h2>
        <div class="stack-body" id="stack">
          <p class="empty">Tap a passage on the left.</p>
        </div>
      </div>
      <div class="scanbox">
        <div class="scan-frame" id="frame"><img id="scan" alt="Scan of this page"></div>
        <div class="scan-bar">
          <span>The printed page</span>
          <button class="plain-btn" id="zoom" type="button">Enlarge</button>
        </div>
      </div>
    </aside>
  </div>

  <footer id="foot"></footer>
</div>

<script type="application/json" id="data">__DATA__</script>
<script>
(function(){
  var D=JSON.parse(document.getElementById('data').textContent);
  var byId={}; D.passages.forEach(function(p){ byId[p.id]=p; });
  var pages=[]; D.passages.forEach(function(p){
    if(pages.indexOf(p.pdf_page)===-1) pages.push(p.pdf_page); });
  pages.sort(function(a,b){return a-b;});

  var glossesFrom={}, glossesTo={};
  D.glosses.forEach(function(g){
    (glossesFrom[g.from_id]=glossesFrom[g.from_id]||[]).push(g);
    if(g.to_id) (glossesTo[g.to_id]=glossesTo[g.to_id]||[]).push(g);
  });

  function el(t,c,x){var n=document.createElement(t); if(c)n.className=c;
    if(x!==undefined)n.textContent=x; return n;}

  document.getElementById('title').textContent=D.title;
  document.getElementById('edition').textContent=D.edition;

  var s=D.stats;
  var foot=document.getElementById('foot');
  foot.innerHTML='<b>'+s.pages+' pages, '+s.passages+' passages.</b> '+
    'Of '+s.quotations+' quotations the machine found, it could place <b>'+
    s.resolved+'</b>; the rest are shown but marked unplaced. Layer labels '+
    '(which commentary a passage belongs to) are now voted from five '+
    'independent readings of each page rather than one, which fixed pages '+
    'coming back labelled differently between runs — but on the handful of '+
    'genuinely ambiguous passages the vote can still settle on the wrong '+
    'side, just consistently instead of randomly. If your argument depends '+
    'on who said something, verify the label against the printed page, not '+
    'just the text. Nothing here has been checked by a scholar, and the '+
    'text is raw OCR, uncorrected.';

  var current=pages[0], selected=null;

  var bar=document.getElementById('pagebar');
  pages.forEach(function(n){
    var first=D.passages.filter(function(p){return p.pdf_page===n;})[0];
    var b=el('button',null,first&&first.printed_page?first.printed_page:String(n));
    b.type='button';
    b.addEventListener('click',function(){ current=n; selected=null; render(); });
    b.dataset.page=n;
    bar.appendChild(b);
  });

  function esc(t){ var d=document.createElement('div'); d.textContent=t;
    return d.innerHTML; }

  function marked(p){
    // Highlight this passage's own quotations, and — when it is the selected
    // passage's source — the words being quoted.
    var spans=[];
    (glossesFrom[p.id]||[]).forEach(function(g){
      spans.push({a:g.from_offset,b:g.from_offset+g.stem.length,cls:''});
    });
    if(selected){
      (glossesFrom[selected]||[]).forEach(function(g){
        if(g.to_id===p.id && g.to_offset!=null)
          spans.push({a:g.to_offset,b:g.to_offset+g.stem.length,cls:'target'});
      });
    }
    spans.sort(function(x,y){return x.a-y.a;});
    var out='', at=0;
    spans.forEach(function(sp){
      if(sp.a<at) return;
      out+=esc(p.text.slice(at,sp.a))+'<mark class="'+sp.cls+'">'+
           esc(p.text.slice(sp.a,sp.b))+'</mark>';
      at=sp.b;
    });
    return out+esc(p.text.slice(at));
  }

  function render(){
    [].forEach.call(bar.children,function(b){
      b.classList.toggle('on', +b.dataset.page===current); });

    var main=document.getElementById('page');
    main.innerHTML='';
    D.passages.filter(function(p){return p.pdf_page===current;}).forEach(function(p){
      var box=el('div','passage'+(p.id===selected?' sel':' collapsed'));
      box.tabIndex=0; box.setAttribute('role','button');
      var h=el('div','p-head');
      h.appendChild(el('span','p-layer',p.layer));
      h.appendChild(el('span','p-roman',D.roman[p.layer]||''));
      h.appendChild(el('span','p-cite','page '+(p.printed_page||'?')));
      box.appendChild(h);
      var t=el('p','p-text'); t.innerHTML=marked(p);
      box.appendChild(t);
      function pick(){ selected=(selected===p.id?null:p.id); render(); }
      box.addEventListener('click',pick);
      box.addEventListener('keydown',function(e){
        if(e.key==='Enter'||e.key===' '){ e.preventDefault(); pick(); } });
      main.appendChild(box);
    });

    var scan=document.getElementById('scan');
    if(D.scans[current]) scan.src=D.scans[current];

    renderStack();
  }

  function citeOf(id){ var p=byId[id];
    return p.layer+' · page '+(p.printed_page||'?'); }

  function jump(id){
    var p=byId[id];
    current=p.pdf_page; selected=id; render();
    var sel=document.querySelector('.passage.sel');
    if(sel) sel.scrollIntoView({block:'center'});
  }

  function relItem(cls, quoted, caption, targetId){
    var d=el('div','rel-item '+cls);
    d.appendChild(el('span','q',quoted));
    d.appendChild(el('span','m',caption));
    if(targetId){
      d.tabIndex=0; d.setAttribute('role','button');
      d.addEventListener('click',function(){ jump(targetId); });
      d.addEventListener('keydown',function(e){
        if(e.key==='Enter'||e.key===' '){ e.preventDefault(); jump(targetId); } });
    }
    return d;
  }

  function renderStack(){
    var box=document.getElementById('stack');
    box.innerHTML='';
    if(!selected){
      box.appendChild(el('p','empty','Tap a passage on the left.'));
      return;
    }
    var p=byId[selected];
    var head=el('p','rel-h','Selected · '+citeOf(p.id));
    box.appendChild(head);

    var up=(glossesFrom[selected]||[]).filter(function(g){return g.to_id;});
    var unplaced=(glossesFrom[selected]||[]).filter(function(g){return !g.to_id;});
    var down=(glossesTo[selected]||[]);

    if(up.length){
      var s1=el('div','rel');
      s1.appendChild(el('p','rel-h','This passage explains'));
      up.forEach(function(g){
        s1.appendChild(relItem('up', g.stem, '→ '+citeOf(g.to_id), g.to_id)); });
      box.appendChild(s1);
    }

    if(down.length){
      var s2=el('div','rel');
      s2.appendChild(el('p','rel-h','Explained here by'));
      down.forEach(function(g){
        s2.appendChild(relItem('down', g.stem, '← '+citeOf(g.from_id), g.from_id)); });
      box.appendChild(s2);
    }

    if(!up.length && !down.length){
      box.appendChild(el('p','empty',
        'Nothing linked to this passage. It may quote a page outside this '+
        'sample, or the machine could not place its quotations.'));
    }

    if(unplaced.length){
      var s3=el('div','rel unplaced');
      s3.appendChild(el('p','rel-h',
        unplaced.length+' quotation'+(unplaced.length>1?'s':'')+' not placed'));
      unplaced.forEach(function(g){
        s3.appendChild(relItem('', g.stem,
          'quoted here, but the passage it refers to was not found', null)); });
      box.appendChild(s3);
    }
  }

  var frame=document.getElementById('frame'), zb=document.getElementById('zoom');
  zb.addEventListener('click',function(){
    var on=frame.classList.toggle('zoomed');
    zb.textContent=on?'Fit page':'Enlarge';
  });

  render();
})();
</script>
</body>
</html>
"""

html = html.replace("__DATA__", payload)
OUT.write_text(html, encoding="utf-8")
print(f"wrote {OUT} — {round(len(html) / 1024 / 1024, 2)} MB")
print(f"stats: {data['stats']}")
