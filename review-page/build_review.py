import base64
import io
import json
import sys
from pathlib import Path

from PIL import Image

sys.path.insert(0, str(Path(__file__).parent))
from simplify import simplify  # noqa: E402

HERE = Path(__file__).parent
BASE = HERE.parent / "ocr-pipeline"
SELECTED = [17, 18, 20, 22, 24]
OUT = HERE / "dist" / "index.html"
OUT.parent.mkdir(parents=True, exist_ok=True)

pages_by_num = {}
with open(BASE / "output/jsonl/avayavaprakaranam/structured_pages.jsonl") as f:
    for line in f:
        if line.strip():
            d = json.loads(line)
            pages_by_num[d["pdf_page"]] = d

LAYER_DEV = {
    "mūla": "मूल",
    "gādādharī": "गादाधरी",
    "bāladevī": "बलदेवी",
    "vimalaprabhā": "विमलप्रभा",
    "footnote": "टिप्पणी",
    "header": "शीर्षक",
    "invocation": "मङ्गलाचरण",
}

data = []
for n in SELECTED:
    p = pages_by_num[n]
    img = Image.open(BASE / f"output/pages/avayavaprakaranam/page-{n:03d}.png").convert("RGB")
    img.thumbnail((1000, 3000), Image.LANCZOS)
    buf = io.BytesIO()
    img.save(buf, "JPEG", quality=72, optimize=True)

    checks, minor = [], []
    for note in p.get("review_notes", []):
        s = simplify(note)
        (checks if s["kind"] == "word" else minor).append(s)

    data.append(
        {
            "page": p.get("printed_page"),
            "ocr_disagreed": p.get("printed_page_ocr_disagreed"),
            "image": "data:image/jpeg;base64," + base64.b64encode(buf.getvalue()).decode(),
            "sections": [
                {"dev": LAYER_DEV.get(s["layer"], s["layer"]), "text": s["text"]}
                for s in p.get("sections", [])
            ],
            "checks": checks,
            "minor": [m["raw"] for m in minor],
        }
    )

payload = json.dumps(data, ensure_ascii=False)
total_checks = sum(len(d["checks"]) for d in data)

html = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<meta name="robots" content="noindex, nofollow">
<meta name="theme-color" content="#17140F">
<title>Navya — please check these words</title>
<style>
  /* minimal reset — the Artifact host provides one, a bare page does not */
  *, *::before, *::after { box-sizing: border-box; }
  body { margin: 0; }
  img { max-width: 100%; }
</style>
<style>
  :root {
    --ink: #17140F;
    --paper: #FAF8F4;
    --panel: #FFFFFF;
    --rule: #DDD6CA;
    --muted: #6B6255;
    --vermilion: #A8321E;
    --vermilion-wash: #F7EBE7;
    --sage: #2F6B4F;
    --sans: ui-sans-serif, system-ui, "Segoe UI", Roboto, sans-serif;
    --serif: Georgia, "Iowan Old Style", "Times New Roman", serif;
    --deva: "Noto Serif Devanagari", "Noto Sans Devanagari", "Devanagari Sangam MN",
            "Nirmala UI", "Kohinoor Devanagari", serif;
  }
  * { box-sizing: border-box; }
  body {
    margin: 0; background: var(--paper); color: var(--ink);
    font-family: var(--serif); line-height: 1.6; -webkit-text-size-adjust: 100%;
  }
  .wrap { max-width: 680px; margin: 0 auto; padding: 0 18px 132px; }

  .masthead { padding: 30px 0 18px; border-bottom: 2px solid var(--ink); }
  .eyebrow {
    font-family: var(--sans); font-size: 11px; letter-spacing: 0.14em;
    text-transform: uppercase; color: var(--vermilion); margin: 0 0 9px; font-weight: 600;
  }
  .masthead h1 {
    font-size: clamp(25px, 6vw, 32px); line-height: 1.22; margin: 0;
    font-weight: 400; text-wrap: balance;
  }

  .intro { margin: 20px 0 0; font-size: 17px; }
  .intro p { margin: 0 0 13px; }
  .intro p:last-child { margin-bottom: 0; }

  .steps {
    margin: 20px 0 0; padding: 17px 19px;
    background: var(--vermilion-wash); border-left: 3px solid var(--vermilion);
  }
  .steps ol { margin: 0; padding-left: 20px; font-size: 16px; }
  .steps li { margin-bottom: 8px; }
  .steps li:last-child { margin-bottom: 0; }

  .page-card { margin: 38px 0 0; border-top: 1px solid var(--rule); padding-top: 20px; }
  .page-head { display: flex; align-items: baseline; gap: 11px; }
  .folio { font-family: var(--deva); font-size: 32px; line-height: 1; color: var(--vermilion); }
  .page-meta {
    font-family: var(--sans); font-size: 12.5px; color: var(--muted); letter-spacing: 0.03em;
  }
  .confirm-no {
    font-family: var(--sans); font-size: 13.5px; color: var(--vermilion);
    margin: 11px 0 0; line-height: 1.5;
  }

  .scan-frame {
    margin-top: 15px; overflow: auto; background: var(--panel);
    border: 1px solid var(--rule); -webkit-overflow-scrolling: touch;
  }
  /* No transition on width: animating it relayouts every frame, which janks
     on a phone and can silently fail to settle. The zoom is instant. */
  .scan-frame img { display: block; width: 100%; height: auto; }
  .scan-frame.zoomed img { width: 265%; max-width: none; }
  .scan-bar {
    display: flex; justify-content: space-between; align-items: center;
    gap: 10px; margin-top: 7px;
  }
  .scan-bar span { font-family: var(--sans); font-size: 12.5px; color: var(--muted); }

  button { font-family: var(--sans); cursor: pointer; }
  .plain-btn {
    font-size: 12px; letter-spacing: .06em; text-transform: uppercase;
    background: none; border: 1px solid var(--rule); color: var(--ink);
    padding: 8px 12px; min-height: 38px;
  }
  .plain-btn:hover { border-color: var(--ink); }
  .plain-btn:focus-visible { outline: 2px solid var(--ink); outline-offset: 2px; }

  .sec-label {
    font-family: var(--sans); font-size: 11.5px; letter-spacing: .13em;
    text-transform: uppercase; color: var(--muted);
    margin: 28px 0 13px; padding-bottom: 7px; border-bottom: 1px solid var(--rule);
  }

  .check { border: 1px solid var(--rule); background: var(--panel); margin: 0 0 12px; }
  .check-body { padding: 14px 16px 12px; }
  .k-label {
    font-family: var(--sans); font-size: 11px; letter-spacing: .1em;
    text-transform: uppercase; color: var(--muted); display: block; margin-bottom: 3px;
  }
  .k-read {
    font-family: var(--deva); font-size: 24px; line-height: 1.75;
    margin: 0; overflow-wrap: break-word;
  }
  .k-alt { margin: 12px 0 0; padding-top: 11px; border-top: 1px dashed var(--rule); }
  .k-alt .k-read { color: var(--sage); }
  .k-raw {
    font-family: var(--sans); font-size: 12.5px; color: var(--muted);
    line-height: 1.55; margin: 11px 0 0; display: none; overflow-wrap: break-word;
  }
  .check.showraw .k-raw { display: block; }
  .k-more {
    font-family: var(--sans); font-size: 11.5px; color: var(--muted);
    background: none; border: none; padding: 6px 0 0; text-decoration: underline;
  }

  .verdict { display: flex; border-top: 1px solid var(--rule); }
  .verdict button {
    flex: 1; font-size: 13px; letter-spacing: .05em; background: none; border: none;
    padding: 14px 6px; min-height: 50px; color: var(--muted);
    border-right: 1px solid var(--rule);
  }
  .verdict button:last-child { border-right: none; }
  .verdict button:hover { background: #F2EFE9; color: var(--ink); }
  .verdict button:focus-visible { outline: 2px solid var(--ink); outline-offset: -3px; }
  .check[data-verdict="ok"] { border-color: var(--sage); }
  .check[data-verdict="ok"] .v-ok { background: var(--sage); color: #fff; font-weight: 700; }
  .check[data-verdict="bad"] { border-color: var(--vermilion); }
  .check[data-verdict="bad"] .v-bad { background: var(--vermilion); color: #fff; font-weight: 700; }

  details { margin-top: 16px; border-top: 1px solid var(--rule); padding-top: 13px; }
  summary {
    font-family: var(--sans); font-size: 12.5px; color: var(--muted);
    cursor: pointer; padding: 5px 0; min-height: 30px;
  }
  summary:focus-visible { outline: 2px solid var(--ink); outline-offset: 2px; }
  .layer { margin: 15px 0 0; }
  .layer-dev {
    font-family: var(--deva); font-size: 16px; color: var(--vermilion); margin-bottom: 4px;
  }
  .layer-text {
    font-family: var(--deva); font-size: 18px; line-height: 1.95; margin: 0;
    padding: 12px 14px; background: var(--panel); border: 1px solid var(--rule);
    overflow-wrap: break-word;
  }
  .minor-list {
    margin: 13px 0 0; padding-left: 19px; font-family: var(--sans);
    font-size: 13px; color: var(--muted); line-height: 1.6;
  }
  .minor-list li { margin-bottom: 8px; overflow-wrap: break-word; }

  .tally {
    position: fixed; left: 0; right: 0; bottom: 0; background: var(--ink);
    color: var(--paper); padding: 11px 18px calc(11px + env(safe-area-inset-bottom));
    display: flex; align-items: center; gap: 14px; justify-content: space-between; z-index: 20;
  }
  .counts {
    font-family: var(--sans); font-size: 13.5px; font-variant-numeric: tabular-nums;
    line-height: 1.35;
  }
  .counts b { font-weight: 700; }
  .c-bad { color: #F0907C; } .c-ok { color: #8FCFAE; }
  .c-left { opacity: .6; display: block; font-size: 11.5px; }
  .copy-btn {
    font-size: 12px; letter-spacing: .07em; text-transform: uppercase; background: none;
    border: 1px solid rgba(250,248,244,.45); color: var(--paper);
    padding: 11px 15px; min-height: 44px; white-space: nowrap;
  }
  .copy-btn:hover { background: rgba(250,248,244,.12); }

  footer {
    margin-top: 42px; padding-top: 17px; border-top: 1px solid var(--rule);
    font-family: var(--sans); font-size: 12.5px; color: var(--muted); line-height: 1.65;
  }
  @media (prefers-reduced-motion: reduce) { * { transition: none !important; } }
</style>
</head>
<body>

<div class="wrap">
  <header class="masthead">
    <p class="eyebrow">Avayavaprakaraṇam · Varanasi 1964</p>
    <h1>Did the computer read these words correctly?</h1>
  </header>

  <div class="intro">
    <p>
      We had a computer read five pages of this book. It managed most of it, but
      there are <strong>__TOTAL__ words</strong> it was unsure about.
    </p>
    <p>
      You are the only one who can tell us whether it actually got them wrong.
    </p>
  </div>

  <div class="steps">
    <ol>
      <li>Look at the photo of the page.</li>
      <li>For each word below it, check the photo and tap <strong>Correct</strong>
          or <strong>Wrong</strong>.</li>
      <li>If you aren't sure about one, just skip it.</li>
      <li>At the end, tap <strong>Copy summary</strong> and send it back.</li>
    </ol>
  </div>

  <div id="pages"></div>

  <footer>
    Avayavaprakaraṇam, ed. Jvālāprasād Gauḍ with the Vilāsinī commentary,
    Lok Sangam Prakashan, Varanasi, 1964. None of this text has been corrected
    by hand — it is exactly what the computer produced.
  </footer>
</div>

<div class="tally">
  <div class="counts">
    <span><b class="c-ok" id="n-ok">0</b> correct · <b class="c-bad" id="n-bad">0</b> wrong</span>
    <span class="c-left" id="n-left">__TOTAL__ left</span>
  </div>
  <button class="copy-btn" id="copy">Copy summary</button>
</div>

<script type="application/json" id="data">__DATA__</script>
<script>
(function () {
  var pages = JSON.parse(document.getElementById('data').textContent);
  var root = document.getElementById('pages');
  var total = 0;

  function el(tag, cls, txt) {
    var n = document.createElement(tag);
    if (cls) n.className = cls;
    if (txt !== undefined) n.textContent = txt;
    return n;
  }

  pages.forEach(function (p, pi) {
    total += p.checks.length;
    var card = el('section', 'page-card');

    var head = el('div', 'page-head');
    head.appendChild(el('span', 'folio', p.page || '—'));
    head.appendChild(el('span', 'page-meta', 'page ' + (p.page || '') + ' of the book'));
    card.appendChild(head);

    if (p.ocr_disagreed) {
      card.appendChild(el('p', 'confirm-no',
        'The computer thought this page was numbered “' + p.ocr_disagreed +
        '”. Please confirm the printed number really is ' + p.page + '.'));
    }

    var frame = el('div', 'scan-frame');
    var img = el('img');
    img.src = p.image;
    img.alt = 'Photograph of page ' + (p.page || '');
    img.loading = pi === 0 ? 'eager' : 'lazy';
    frame.appendChild(img);
    card.appendChild(frame);

    var bar = el('div', 'scan-bar');
    bar.appendChild(el('span', null, 'Tap Enlarge, then drag sideways'));
    var zb = el('button', 'plain-btn', 'Enlarge');
    zb.type = 'button';
    zb.addEventListener('click', function () {
      var on = frame.classList.toggle('zoomed');
      zb.textContent = on ? 'Fit page' : 'Enlarge';
    });
    bar.appendChild(zb);
    card.appendChild(bar);

    card.appendChild(el('p', 'sec-label',
      p.checks.length + ' word' + (p.checks.length === 1 ? '' : 's') + ' to check'));

    p.checks.forEach(function (c, ci) {
      var k = el('div', 'check');
      k.dataset.page = p.page;
      k.dataset.idx = ci + 1;

      var body = el('div', 'check-body');
      body.appendChild(el('span', 'k-label', 'The computer read'));
      body.appendChild(el('p', 'k-read', c.read));

      if (c.suggested) {
        var alt = el('div', 'k-alt');
        alt.appendChild(el('span', 'k-label', 'It thinks the book may actually say'));
        alt.appendChild(el('p', 'k-read', c.suggested));
        body.appendChild(alt);
      }

      var raw = el('p', 'k-raw', c.raw);
      var more = el('button', 'k-more', "Show the computer's own note");
      more.type = 'button';
      more.addEventListener('click', function () {
        var on = k.classList.toggle('showraw');
        more.textContent = on ? 'Hide note' : "Show the computer's own note";
      });
      body.appendChild(more);
      body.appendChild(raw);
      k.appendChild(body);

      var v = el('div', 'verdict');
      [['ok', 'Correct'], ['bad', 'Wrong']].forEach(function (pair) {
        var b = el('button', 'v-' + pair[0], pair[1]);
        b.type = 'button';
        b.addEventListener('click', function () {
          k.dataset.verdict = k.dataset.verdict === pair[0] ? '' : pair[0];
          recount();
        });
        v.appendChild(b);
      });
      k.appendChild(v);
      card.appendChild(k);
    });

    var dt = el('details');
    dt.appendChild(el('summary', null, 'See everything the computer read on this page'));
    p.sections.forEach(function (s) {
      var l = el('div', 'layer');
      l.appendChild(el('div', 'layer-dev', s.dev));
      l.appendChild(el('p', 'layer-text', s.text));
      dt.appendChild(l);
    });
    card.appendChild(dt);

    if (p.minor.length) {
      var dm = el('details');
      dm.appendChild(el('summary', null,
        p.minor.length + ' smaller notes (stray marks, spacing) — safe to skip'));
      var ul = el('ul', 'minor-list');
      p.minor.forEach(function (t) { ul.appendChild(el('li', null, t)); });
      dm.appendChild(ul);
      card.appendChild(dm);
    }

    root.appendChild(card);
  });

  var elOk = document.getElementById('n-ok');
  var elBad = document.getElementById('n-bad');
  var elLeft = document.getElementById('n-left');

  function recount() {
    var ok = 0, bad = 0;
    document.querySelectorAll('.check').forEach(function (k) {
      if (k.dataset.verdict === 'ok') ok++;
      else if (k.dataset.verdict === 'bad') bad++;
    });
    elOk.textContent = ok;
    elBad.textContent = bad;
    var left = total - ok - bad;
    elLeft.textContent = left === 0 ? 'all done — please copy' : left + ' left';
  }

  document.getElementById('copy').addEventListener('click', function () {
    var ok = 0, bad = 0, skip = 0, wrongs = [];
    document.querySelectorAll('.check').forEach(function (k) {
      var v = k.dataset.verdict;
      if (v === 'ok') ok++;
      else if (v === 'bad') {
        bad++;
        wrongs.push('  page ' + k.dataset.page + ' — read as: ' +
                    k.querySelector('.k-read').textContent);
      } else skip++;
    });
    var lines = ['Avayavaprakaranam - 5 pages checked',
                 'Correct: ' + ok + '   Wrong: ' + bad + '   Skipped: ' + skip];
    if (wrongs.length) { lines.push('', 'Words it got wrong:'); lines = lines.concat(wrongs); }
    var out = lines.join('\\n');
    var btn = document.getElementById('copy');
    function done() {
      btn.textContent = 'Copied';
      setTimeout(function () { btn.textContent = 'Copy summary'; }, 1800);
    }
    if (navigator.clipboard && navigator.clipboard.writeText) {
      navigator.clipboard.writeText(out).then(done, fallback);
    } else fallback();
    function fallback() {
      var ta = document.createElement('textarea');
      ta.value = out; ta.style.position = 'fixed'; ta.style.opacity = '0';
      document.body.appendChild(ta); ta.select();
      try { document.execCommand('copy'); done(); }
      catch (e) { btn.textContent = 'Select & copy'; ta.style.opacity = '1'; }
      setTimeout(function () { ta.remove(); }, 100);
    }
  });

  recount();
})();
</script>
</body>
</html>
"""

html = html.replace("__DATA__", payload).replace("__TOTAL__", str(total_checks))
OUT.write_text(html, encoding="utf-8")

# Deploy from dist/ itself, so the folder is self-contained. An empty
# .vercelignore matters: Vercel falls back to .gitignore when it's absent,
# and dist/ is gitignored (it embeds page scans), which would silently
# upload a deployment with no files in it.
(OUT.parent / ".vercelignore").write_text("", encoding="utf-8")
(OUT.parent / "vercel.json").write_text(
    json.dumps(
        {
            "$schema": "https://openapi.vercel.sh/vercel.json",
            "headers": [
                {
                    "source": "/(.*)",
                    "headers": [{"key": "X-Robots-Tag", "value": "noindex, nofollow"}],
                }
            ],
        },
        indent=2,
    )
    + "\n",
    encoding="utf-8",
)

print(f"wrote {OUT} — {round(len(html) / 1024 / 1024, 2)} MB")
print(f"{total_checks} word checks, {sum(len(d['minor']) for d in data)} minor notes")
print(f"deploy with:  cd {OUT.parent} && npx vercel deploy --prod --yes")
