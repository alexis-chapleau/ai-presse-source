"""Build the internal-medicine demo: a phone-app page with real abstracts, labelled AI summaries,
and a CPD log that prepares Royal College My MOC entries.

Usage: python build_demo.py            -> writes demo-md/index.html
Inputs: papers_raw.json (Europe PMC records), summaries.json (AI summaries keyed by DOI).
"""
import html
import json
import math
import re
from datetime import datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
e = lambda s: html.escape(str(s or ""), quote=True)

SECTIONS = {
    "gim":    ("General internal medicine", "#484E58"),
    "cardio": ("Cardiology", "#C2414B"),
    "endo":   ("Endocrinology", "#207FB7"),
    "obs":    ("Obstetric medicine", "#840132"),
    "nephro": ("Nephrology", "#5A79A0"),
    "hepato": ("Hepatology", "#6B9500"),
    "id":     ("Infectious diseases", "#14A574"),
    "resp":   ("Respirology", "#A05FA8"),
}
LICENSES = {
    "cc by": ("CC BY 4.0", "https://creativecommons.org/licenses/by/4.0/"),
    "cc by-nc": ("CC BY-NC 4.0", "https://creativecommons.org/licenses/by-nc/4.0/"),
    "cc by-nc-nd": ("CC BY-NC-ND 4.0", "https://creativecommons.org/licenses/by-nc-nd/4.0/"),
}
# Europe PMC lower-cases some journal titles
JOURNAL_NAMES = {"jama network open": "JAMA Network Open", "bmj open": "BMJ Open",
                 "hypertension (dallas, tex. : 1979)": "Hypertension"}
PATHS = {
    "home": "M3 10.5 12 3l9 7.5V20a1 1 0 0 1-1 1h-5v-6h-6v6H4a1 1 0 0 1-1-1z",
    "bookmark": "M6 3h12v18l-6-4.5L6 21z",
    "share": "M12 15V3M8 7l4-4 4 4M7 11H5v10h14V11h-2",
    "grid": "M4 4h7v7H4zM13 4h7v7h-7zM4 13h7v7H4zM13 13h7v7h-7z",
    "book": "M12 6.5C10 5 7 4.5 3 5v14c4-.5 7 0 9 1.5 2-1.5 5-2 9-1.5V5c-4-.5-7 0-9 1.5zM12 6.5V20",
    "award": "M12 15a6 6 0 1 0 0-12 6 6 0 0 0 0 12zM8.5 14 7 22l5-3 5 3-1.5-8",
    "ext": "M14 4h6v6M20 4l-9 9M18 14v6H4V6h6",
    "quote": "M7 7h4v4c0 3-2 5-4 6M15 7h4v4c0 3-2 5-4 6",
    "journal": "M4 21V8l8-5 8 5v13M9 21v-6h6v6M3 21h18",
    "unlock": "M7 11V7a5 5 0 0 1 9.6-2M5 11h14v10H5z",
}


def icon(name, size=22):
    return (f'<svg viewBox="0 0 24 24" width="{size}" height="{size}" fill="none" stroke="currentColor" stroke-width="1.8" '
            f'stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="{PATHS[name]}"/></svg>')


def nice_date(iso):
    d = datetime.strptime(iso, "%Y-%m-%d")
    return f"{d:%b} {d.day}, {d.year}"


def authors_short(names):
    return ", ".join(names[:3]) + (", et al." if len(names) > 3 else "")


def abstract_sections(raw):
    """Split Europe PMC abstract HTML ('<h4>Heading</h4>text...') into (heading, text) pairs."""
    parts = re.split(r"<h4>(.*?)</h4>", raw or "")
    out = []
    for i in range(1, len(parts), 2):
        text = re.sub(r"<[^>]+>", "", parts[i + 1]).strip()
        out.append((parts[i].strip(), html.unescape(text)))
    return out or [("", re.sub(r"<[^>]+>", "", raw or ""))]


def load_papers():
    raw = json.loads((HERE / "papers_raw.json").read_text(encoding="utf-8"))
    sums = json.loads((HERE / "summaries.json").read_text(encoding="utf-8"))
    papers = []
    for r in raw:
        s = sums.get(r["doi"])
        if not s:
            continue
        secs = abstract_sections(r["abstract"])
        words = sum(len(t.split()) for _, t in secs)
        papers.append({**s, **{
            "title": r["title"].rstrip("."), "doi": r["doi"], "pmid": r["pmid"],
            "journal": JOURNAL_NAMES.get((r["journal"] or "").lower(), r["journal"] or "JAMA Network Open"), "date": r["date"],
            "authors": r["authors"], "license": r["license"], "abstract": secs,
            "minutes": max(2, math.ceil(words / 200)),
            "metrics": r.get("metrics") or {}, "full_read": r.get("full_read") or {"minutes": 30, "basis": "typical length"},
        }})
    papers.sort(key=lambda p: (not p.get("lead"), not p.get("featured")))
    return papers


def short_date(iso):
    d = datetime.strptime(iso, "%Y-%m-%d")
    return f"{d:%b} {d.day}"


def paper_facts(p):
    """Subtle metadata block: full-paper length, citations, journal, licence."""
    fr, m = p["full_read"], p["metrics"]
    lic_label = LICENSES.get(p["license"], (p["license"] or "licence unknown", ""))[0]
    length = (f'{fr["body_words"]:,} words, {fr["figures"] + fr["tables"]} figures/tables'
              if fr.get("body_words") else fr.get("basis", ""))
    cited = m.get("cited_by") or 0
    if cited:
        pct = m.get("citation_percentile")
        cites = f"Cited {cited}×" + (f" · top {100 - pct}% for its field and age" if pct is not None else "")
    else:
        cites = "New · not yet cited"
    if m.get("references"):
        cites += f' · {m["references"]} references'
    jr = f'{e(p["journal"])}'
    if m.get("journal_2yr_mean_citedness"):
        jr += f' · journal averages {m["journal_2yr_mean_citedness"]} citations per paper (2 yr)'
    rows = [("book", f'Full paper ≈ <b>{fr["minutes"]} min</b> · {e(length)}'),
            ("quote", e(cites)), ("journal", jr), ("unlock", f"Open access · {e(lic_label)}")]
    return ('<ul class="facts">' + "".join(f'<li>{icon(i, 15)}<span>{t}</span></li>' for i, t in rows)
            + f'<li class="facts__src">Metrics: OpenAlex, {e(m.get("fetched", ""))}</li></ul>')


# ---------------------------------------------------------------- pieces
def actions(p):
    name, color = SECTIONS[p["section"]]
    return (f'<span class="acts"><button class="bm" type="button" aria-label="Save" data-id="{e(p["id"])}" data-title="{e(p["title"])}" '
            f'data-sec="{e(name)}" data-color="{color}">{icon("bookmark", 21)}</button>'
            f'<button class="sh" type="button" aria-label="Share" data-title="{e(p["title"])}" data-url="https://doi.org/{e(p["doi"])}">{icon("share", 21)}</button></span>')


def visual(p, cls="vis"):
    name, color = SECTIONS[p["section"]]
    return (f'<div class="{cls}" style="--c:{color}"><span class="vis__study">{e(p["study"])}</span>'
            f'<span class="vis__big">{e(p["big"])}</span><span class="vis__label">{e(p["big_label"])}</span></div>')


def card(p, compact=False):
    name, color = SECTIONS[p["section"]]
    bdg = f'<span class="badge" style="background:{color}">{e(name)}</span>'
    foot = (f'<div class="mcard__foot"><i class="mdot"></i>{e(short_date(p["date"]))} · paper {e(p["full_read"]["minutes"])} min'
            f'<span class="logged" data-logged="{e(p["id"])}"></span>{actions(p)}</div>')
    if compact:
        return f'''<article class="mcard mcard--row"><div class="mcard__body">{bdg}
  <p class="mcard__sup">{e(p["kicker"])} · {e(p["journal"])}</p>
  <h3 class="mcard__title"><a href="#{e(p["id"])}">{e(p["title"])}</a></h3>{foot}</div>
  <a class="mcard__img" href="#{e(p["id"])}" tabindex="-1">{visual(p, "vis vis--sq")}</a></article>'''
    return f'''<article class="mcard"><a class="mcard__img" href="#{e(p["id"])}" tabindex="-1">{visual(p)}<span class="mbadge">{bdg}</span></a>
  <div class="mcard__body"><p class="mcard__sup">{e(p["kicker"])} · {e(p["journal"])}</p>
  <h3 class="mcard__title"><a href="#{e(p["id"])}">{e(p["title"])}</a></h3>
  <p class="mcard__lead"><b class="ai-inline">AI summary</b> {e(p["summary"])}</p>{foot}</div></article>'''


def article_page(p):
    name, color = SECTIONS[p["section"]]
    lic_label, lic_url = LICENSES.get(p["license"], (p["license"] or "Licence unknown", ""))
    abstract = "".join((f"<h4>{e(h)}</h4>" if h else "") + f"<p>{e(t)}</p>" for h, t in p["abstract"])
    cite = (f'{e(authors_short(p["authors"]))} {e(p["title"])}. <i>{e(p["journal"])}</i>. {e(p["date"][:4])}. '
            f'doi:{e(p["doi"])}')
    return f'''<div class="page" id="{e(p["id"])}" hidden>
<article class="art" style="--c:{color}">
  <div class="sheetbar" style="background:{color}"><a class="grab" href="#top" data-close aria-label="Close"></a><span>{e(name)}</span>{actions(p)}</div>
  {visual(p, "vis vis--hero")}
  <p class="art__kicker">{e(p["kicker"])} · {e(p["journal"])}</p>
  <h1 class="art__title">{e(p["title"])}</h1>
  <p class="art__authors">{e(authors_short(p["authors"]))}</p>
  <div class="mmeta"><span><i class="mdot"></i>{e(nice_date(p["date"]))}</span><span>{icon("book", 17)} abstract {e(p["minutes"])} min</span></div>
  {paper_facts(p)}
  <section class="aisum">
    <div class="aisum__label">✦ AI summary</div>
    <p>{e(p["summary"])}</p>
    <p class="aisum__note">Written by AI from the abstract below. It may contain errors: the abstract is the reference.</p>
  </section>
  <section class="abs">
    <div class="abs__label"><span>Abstract</span><span>Verbatim from {e(p["journal"])}</span></div>
    {abstract}
    <p class="abs__lic">Reproduced under <a href="{e(lic_url)}" target="_blank" rel="noopener">{e(lic_label)}</a>. © The authors.</p>
  </section>
  <p class="cite">{cite}</p>
  <a class="pill pill--outline" href="https://doi.org/{e(p["doi"])}" target="_blank" rel="noopener" data-fullpaper="{e(p["id"])}">Read the full paper {icon("ext", 16)}</a>
  <div class="logbox" data-logbox="{e(p["id"])}">
    <div class="logbox__icon">{icon("award", 26)}</div>
    <div class="logbox__txt"><b>Earn MOC credit for this</b><span data-logstate="{e(p["id"])}">Section 2 · 0.5 credits/hour, or 2/hour if it answers a clinical question</span></div>
    <button class="pill pill--dark" type="button" data-log="{e(p["id"])}">Log to my CPD</button>
  </div>
</article>
</div>'''


CPD_PAGE = '''<div class="page" id="cpd" hidden>
<article class="art" style="--c:#232325">
  <div class="sheetbar" style="background:#232325"><a class="grab" href="#top" data-close aria-label="Close"></a><span>My CPD</span></div>
  <h1 class="art__title" style="margin-top:18px">My CPD record</h1>
  <div class="cpd-hero">
    <div><div class="cpd-hero__big" id="cpdYearBig">0.0</div><div class="cpd-hero__lbl">MOC credits logged in <span class="yr"></span></div></div>
    <div class="ring" id="cpdRing"><span id="cpdRingTxt">0%</span></div>
  </div>
  <p class="cpd-goal">Royal College minimum: <b>25 credits a year</b>, 250 per 5-year cycle.</p>
  <div class="cpd-split">
    <div><b id="cpdReview">0.0</b><span>Educational content review<br>0.5 cr/h · max 30/yr</span></div>
    <div><b id="cpdPrep">0.0</b><span>Activity preparation<br>clinical questions · 2 cr/h</span></div>
  </div>
  <h2 class="sub">This month</h2>
  <p class="cpd-month" id="cpdMonth">Nothing logged yet.</p>
  <button class="pill pill--dark wide" type="button" id="btnMoc">Prepare my My MOC entries</button>
  <div id="mocEntries"></div>
  <button class="pill pill--outline wide" type="button" id="btnTranscript">Download transcript (PDF)</button>
  <h2 class="sub">Logged activities</h2>
  <div id="cpdList"></div>
  <div class="demo-tools"><span>Demo:</span><button type="button" id="btnSample">Add a sample month</button><button type="button" id="btnClear">Clear</button></div>
  <p class="fine">Credits follow the Royal College's refreshed MOC framework (Section 2: educational content review at 0.5 credits/hour, capped at 30 credits/year; activity preparation at 2 credits/hour). Physicians self-report and remain responsible for what they claim. Quebec Fellows: My MOC activities transfer to the CMQ when you open your declaration. This demo is not affiliated with the Royal College or the CMQ.</p>
</article>
</div>'''

SAVED_PAGE = '''<div class="page" id="saved" hidden>
<article class="art" style="--c:#232325">
  <div class="sheetbar" style="background:#232325"><a class="grab" href="#top" data-close aria-label="Close"></a><span>Saved</span></div>
  <h1 class="art__title" style="margin-top:18px">Saved papers</h1>
  <div id="savedList"></div>
</article>
</div>'''

LOG_SHEET = '''<div class="logsheet" id="logSheet" aria-hidden="true">
  <div class="logsheet__grab"></div>
  <h3>Log to my CPD</h3>
  <p class="logsheet__title" id="lsTitle"></p>
  <div class="seg" role="radiogroup">
    <button type="button" class="on" data-type="review"><b>Reading</b><span>0.5 credits/hour</span></button>
    <button type="button" data-type="prep"><b>Clinical question</b><span>2 credits/hour</span></button>
  </div>
  <label class="fld" id="lsQWrap" hidden><span>Your clinical question</span><input id="lsQ" type="text" placeholder="e.g. Should my 86-year-old patient with AF stay on rivaroxaban?"></label>
  <div class="fld"><span>What did you read?</span>
    <div class="presets" id="lsPresets">
      <button type="button" data-preset="abstract"><b>Abstract</b><span id="pAbs"></span></button>
      <button type="button" data-preset="skim"><b>Skimmed</b><span id="pSkim"></span></button>
      <button type="button" data-preset="full"><b>Full paper</b><span id="pFull"></span></button>
    </div>
    <div class="stepper"><button type="button" id="lsMinus" aria-label="5 minutes less">−5</button>
      <label class="stepper__num"><input id="lsMin" type="number" inputmode="numeric" min="1" max="600" value="5"><span>min</span></label>
      <button type="button" id="lsPlus" aria-label="5 minutes more">+5</button></div>
    <p class="lsHint" id="lsHint"></p>
  </div>
  <label class="fld"><span>Key message learned</span><textarea id="lsMsg" rows="3" placeholder="One thing you'll remember or change"></textarea></label>
  <button type="button" class="chip" id="lsSuggest">Use suggested takeaway</button>
  <div class="lsCalc" id="lsCalc"></div>
  <div class="lsBtns"><button type="button" class="pill pill--outline" id="lsCancel">Cancel</button><button type="button" class="pill pill--dark" id="lsSave">Log it</button></div>
</div>'''


def build():
    papers = load_papers()
    lead = papers[0]
    top = [lead] + [p for p in papers[1:] if p.get("featured")][:3]
    more = [p for p in papers if p not in top]
    chips = "".join(f'<a href="#m-sec-{k}" style="--c:{c}">{e(n)}</a>' for k, (n, c) in SECTIONS.items()
                    if any(p["section"] == k for p in papers))
    by_sec = "".join(
        f'<h3 class="msec" id="m-sec-{k}" style="--c:{c}">{e(n)}</h3>' + "".join(card(p, True) for p in papers if p["section"] == k)
        for k, (n, c) in SECTIONS.items() if any(p["section"] == k for p in papers))
    meta = {p["id"]: {"title": p["title"], "doi": p["doi"], "journal": p["journal"], "minutes": p["minutes"],
                      "full": p["full_read"]["minutes"], "words": p["full_read"].get("body_words"),
                      "exhibits": (p["full_read"].get("figures") or 0) + (p["full_read"].get("tables") or 0),
                      "takeaway": p["takeaway"], "section": SECTIONS[p["section"]][0]} for p in papers}

    feed = f'''<main id="home">
  <a class="cpdpill" href="#cpd">{icon("award", 18)}<span><b id="cpdPill">0.0</b> MOC credits logged this year</span><em>›</em></a>
  <h2 class="mhead" id="m-head">The headlines<span>New in internal medicine this week.</span></h2>
  {"".join(card(p) for p in top)}
  <h2 class="mhead">More this week<span>Quick reads, each one loggable.</span></h2>
  {"".join(card(p, True) for p in more)}
  <h2 class="mhead" id="m-sections">By specialty<span>Every paper in this edition.</span></h2>
  <div class="mchips">{chips}</div>
  {by_sec}
  <p class="mcolophon">Le Quotidien Médical · demo edition · October 22, 2026<br>Abstracts reproduced verbatim under each paper's licence. AI summaries are labelled and may contain errors. Not medical advice.</p>
</main>'''

    doc = (TEMPLATE
           .replace("%%CSS%%", CSS).replace("%%JS%%", JS)
           .replace("%%META%%", json.dumps(meta, ensure_ascii=False).replace("</", "<\\/"))
           .replace("%%LEAD%%", e(lead["id"]))
           .replace("%%FEED%%", feed)
           .replace("%%PAGES%%", "".join(article_page(p) for p in papers) + CPD_PAGE + SAVED_PAGE)
           .replace("%%LOGSHEET%%", LOG_SHEET)
           .replace("%%ICON_HOME%%", icon("home")).replace("%%ICON_GRID%%", icon("grid"))
           .replace("%%ICON_AWARD%%", icon("award")).replace("%%ICON_BM%%", icon("bookmark")))
    out = HERE / "index.html"
    out.write_text(doc, encoding="utf-8")
    print(f"Wrote {out} ({len(papers)} papers)")


TEMPLATE = '''<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<title>Le Quotidien Médical (demo)</title>
<meta name="theme-color" content="#e12929"><meta name="robots" content="noindex,nofollow">
<meta name="apple-mobile-web-app-capable" content="yes"><meta name="mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-status-bar-style" content="black-translucent"><meta name="apple-mobile-web-app-title" content="Quotidien Méd">
<link rel="apple-touch-icon" href="/icons/apple-touch-icon.png">
<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Figtree:wght@300;400;500;600;700;800;900&family=Rubik:wght@400;500;700&family=Roboto+Serif:ital,opsz,wght@0,8..144,400;0,8..144,700;1,8..144,400&display=swap" rel="stylesheet">
<style>%%CSS%%</style></head>
<body>
<div id="stage">
  <header class="appbar" id="top"><a class="appbar__heart" href="#%%LEAD%%" aria-label="Lead paper">★</a>
    <a class="appbar__logo" href="#top">Le Quotidien Médical<small>DEMO</small></a>
    <a class="appbar__me" href="#cpd" aria-label="My CPD">%%ICON_AWARD%%</a></header>
  %%FEED%%
</div>
<div id="sheets">%%PAGES%%</div>
<div class="scrim"></div>
<div class="scrim2"></div>
%%LOGSHEET%%
<nav class="tabbar">
  <a href="#top" data-tab="home">%%ICON_HOME%%<span>Headlines</span></a>
  <a href="#m-sections" data-tab="sections">%%ICON_GRID%%<span>Specialties</span></a>
  <a href="#cpd" data-tab="cpd">%%ICON_AWARD%%<span>My CPD</span></a>
  <a href="#saved" data-tab="saved">%%ICON_BM%%<span>Saved</span></a>
</nav>
<div class="toast" id="toast"></div>
<div id="printArea"></div>
<script>var META=%%META%%;</script>
<script>%%JS%%</script>
</body></html>'''

CSS = r"""
:root{--red:#e12929;--ink:#111;--ink2:#232325;--grey:#555;--rule:#e3e3e3;--bg:#f1f1f1;--blue:#1eaefd;
--head:"Figtree",Arial,sans-serif;--ui:"Rubik",Arial,sans-serif;--serif:"Roboto Serif",Georgia,serif;--ease:cubic-bezier(.32,.72,0,1);
--w:min(100vw,480px);--side:max(0px,calc((100vw - 480px)/2))}
*{box-sizing:border-box}html,body{margin:0;overflow-x:hidden}
body{background:#2b2b2e;color:var(--ink);font-family:var(--head);-webkit-font-smoothing:antialiased;transition:background-color .5s}
a{color:inherit;text-decoration:none}a,button{-webkit-tap-highlight-color:transparent;font-family:inherit}[hidden]{display:none!important}
#stage{max-width:480px;margin:0 auto;background:var(--bg);min-height:100vh;padding-bottom:calc(96px + env(safe-area-inset-bottom));transition:transform .5s var(--ease),border-radius .5s var(--ease);will-change:transform}
body.sheet{overflow:hidden;background:#000}
body.sheet #stage{transform:translate3d(0,calc((env(safe-area-inset-top) + 10px) * var(--k,1)),0) scale(calc(1 - .07 * var(--k,1)));border-radius:14px}
/* app bar */
.appbar{position:sticky;top:0;z-index:30;background:var(--red);color:#fff;display:flex;align-items:center;justify-content:space-between;padding:calc(env(safe-area-inset-top) + 9px) 14px 9px}
.appbar__logo{font:900 18px/1 var(--head);text-transform:uppercase;letter-spacing:.01em;display:flex;align-items:center;gap:6px}
.appbar__logo small{font:700 9px var(--ui);letter-spacing:.1em;background:#fff;color:var(--red);padding:3px 5px;border-radius:3px}
.appbar__heart{width:30px;height:30px;border-radius:50%;background:#fff200;color:#000;display:grid;place-items:center;font-size:15px;box-shadow:inset 0 0 0 2px #000}
.appbar__me{display:grid;place-items:center;width:30px;height:30px}
main{padding:0 12px}
.cpdpill{display:flex;align-items:center;gap:8px;margin:12px 0 0;background:#fff;border-radius:12px;padding:10px 12px;font:400 13.5px var(--ui);color:#333;box-shadow:0 1px 3px rgba(0,0,0,.1)}
.cpdpill svg{color:var(--red);flex:none}.cpdpill b{font:800 15px var(--head);color:#000}.cpdpill em{margin-left:auto;font-style:normal;color:#999;font-size:20px;line-height:1}
.mhead{text-align:center;font:900 22px/1.15 var(--head);text-transform:uppercase;margin:24px 0 14px;scroll-margin-top:70px}
.mhead span{display:block;font:400 13.5px var(--ui);text-transform:none;color:var(--grey);margin-top:5px}
/* cards */
.mcard{display:block;background:#fff;border-radius:10px;overflow:hidden;box-shadow:0 1px 3px rgba(0,0,0,.12),0 6px 16px rgba(0,0,0,.05);margin-bottom:14px;transition:transform .35s var(--ease)}
.mcard:active{transform:scale(.97)}
.mcard__img{display:block;position:relative}
.mbadge{position:absolute;left:10px;bottom:10px;z-index:2}
.badge{display:inline-block;border-radius:5px;padding:5px 6px;font:600 11.5px var(--head);line-height:1;color:#fff;text-transform:uppercase;letter-spacing:.02em}
.mcard__body{padding:12px 14px}
.mcard__body>.badge{margin-bottom:8px}
.mcard__sup{font:500 13px var(--head);color:var(--ink2);margin:0 0 4px}
.mcard__title{font:800 20px/1.25 var(--head);margin:0 0 8px}
.mcard__lead{font:400 14px/1.45 var(--head);color:#333;margin:0 0 10px;display:-webkit-box;-webkit-line-clamp:4;-webkit-box-orient:vertical;overflow:hidden}
.ai-inline{font:700 10.5px var(--ui);text-transform:uppercase;letter-spacing:.06em;color:#6d28d9;background:#f1ebff;padding:2px 5px;border-radius:3px;margin-right:4px}
.mcard__foot{display:flex;align-items:center;gap:6px;font:400 12.5px var(--ui);color:var(--grey)}
.mdot{display:inline-block;width:10px;height:10px;border-radius:50%;background:var(--blue);flex:none}
.logged:not(:empty){color:#0a7d43;font-weight:500}
.acts{margin-left:auto;display:flex;gap:14px}.acts button{background:none;border:0;padding:2px;margin:0;color:inherit;cursor:pointer}
.bm.on svg{fill:currentColor}
.mcard--row{display:grid;grid-template-columns:minmax(0,1fr) 96px;gap:12px;padding:12px}
.mcard--row .mcard__body{padding:0}.mcard--row .mcard__title{font-size:16.5px;line-height:1.3}
/* key-number panels instead of photos */
.vis{position:relative;aspect-ratio:16/9;background:linear-gradient(135deg,#1f1f22 0%,#333338 50%,var(--c) 170%);color:#fff;display:flex;flex-direction:column;justify-content:flex-end;padding:16px 16px 44px;overflow:hidden}
.vis__study{position:absolute;top:12px;left:16px;font:600 11px var(--ui);text-transform:uppercase;letter-spacing:.1em;opacity:.8;border-left:3px solid var(--red);padding-left:7px}
.vis__big{font:900 46px/1 var(--head);letter-spacing:-.02em}.vis__label{font:500 14px var(--head);opacity:.85;margin-top:4px}
.vis--sq{aspect-ratio:1;border-radius:6px;padding:8px;justify-content:center}.vis--sq .vis__study,.vis--sq .vis__label{display:none}.vis--sq .vis__big{font-size:19px}
.vis--hero{margin:0 -16px;aspect-ratio:16/8;padding-bottom:22px}
.mchips{display:flex;gap:8px;overflow-x:auto;margin:0 -12px 6px;padding:2px 12px;scrollbar-width:none}.mchips::-webkit-scrollbar{display:none}
.mchips a{flex:none;border-radius:16px;padding:7px 13px;font:500 13px var(--ui);color:#fff;background:var(--c)}
.msec{display:flex;align-items:center;gap:8px;font:700 17px var(--ui);text-transform:uppercase;margin:24px 2px 12px;color:var(--ink2);scroll-margin-top:70px}
.msec::before{content:"";width:10px;height:10px;background:var(--c)}
.mcolophon{font:400 11.5px/1.5 var(--ui);color:#888;text-align:center;margin:12px 0 24px}
/* tab bar */
.tabbar{position:fixed;left:calc(var(--side) + 12px);right:calc(var(--side) + 12px);bottom:calc(10px + env(safe-area-inset-bottom));z-index:40;display:flex;justify-content:space-around;background:rgba(246,246,246,.82);-webkit-backdrop-filter:blur(18px) saturate(1.8);backdrop-filter:blur(18px) saturate(1.8);border-radius:30px;box-shadow:0 6px 24px rgba(0,0,0,.18);padding:6px;border:1px solid rgba(255,255,255,.7)}
.tabbar a{display:flex;flex-direction:column;align-items:center;gap:2px;font:500 10px var(--ui);color:#333;padding:5px 6px;border-radius:22px;flex:1}
.tabbar a.on{background:rgba(0,0,0,.08);color:#000;font-weight:700}
/* sheets */
.scrim,.scrim2{position:fixed;inset:0;background:rgba(0,0,0,.4);z-index:45;opacity:0;pointer-events:none;transition:opacity .5s var(--ease)}
.scrim2{z-index:58;background:rgba(0,0,0,.3)}
body.sheet .scrim{opacity:1;pointer-events:auto}body.logging .scrim2{opacity:1;pointer-events:auto}
.page{position:fixed;left:var(--side);right:var(--side);bottom:0;top:calc(env(safe-area-inset-top) + 30px);z-index:50;background:#fff;border-radius:12px 12px 0 0;overflow-y:auto;-webkit-overflow-scrolling:touch;overscroll-behavior:contain;transform:translate3d(0,102%,0);transition:transform .5s var(--ease);will-change:transform;box-shadow:0 -4px 24px rgba(0,0,0,.18)}
.page.is-open{transform:none}
.art{display:flex;flex-direction:column;padding:0 16px calc(120px + env(safe-area-inset-bottom))}
.sheetbar{position:sticky;top:0;z-index:5;margin:0 -16px;display:flex;align-items:center;color:#fff;padding:16px 16px 11px;font:700 12.5px var(--ui);text-transform:uppercase;letter-spacing:.06em}
.grab{position:absolute;left:50%;top:0;width:90px;height:16px;margin-left:-45px}
.grab::before{content:"";position:absolute;left:25px;right:25px;top:6px;height:4px;border-radius:3px;background:rgba(255,255,255,.75)}
.art__kicker{font:500 14px var(--head);color:var(--ink2);margin:18px 0 8px}
.art__title{font:800 27px/1.2 var(--head);margin:0 0 8px}
.art__authors{font:400 13.5px var(--head);color:var(--grey);margin:0 0 12px}
.mmeta{display:flex;justify-content:space-between;align-items:center;font:400 13px var(--ui);color:var(--grey);margin-bottom:16px}
.mmeta span{display:flex;align-items:center;gap:6px}
.facts{list-style:none;margin:-4px 0 18px;padding:0;font:400 12.5px/1.4 var(--ui);color:#6b6b6b}
.facts li{display:flex;gap:8px;align-items:flex-start;padding:3px 0}.facts li svg{flex:none;margin-top:1px;color:#9a9a9a}
.facts b{color:var(--ink2);font-weight:600}.facts .facts__src{font-size:11px;color:#aaa;padding-left:23px}
.aisum{background:#f6f2ff;border:1px solid #e3d8ff;border-radius:10px;padding:14px 14px 10px;margin-bottom:20px}
.aisum__label{font:700 11.5px var(--ui);text-transform:uppercase;letter-spacing:.1em;color:#6d28d9;margin-bottom:6px}
.aisum p{font:400 15.5px/1.55 var(--head);margin:0 0 8px;color:#1d1530}
.aisum .aisum__note{font:400 12px/1.4 var(--ui);color:#6b6480;margin:0}
.abs{border-top:3px solid var(--c);padding-top:12px}
.abs__label{display:flex;justify-content:space-between;align-items:baseline;font:700 12px var(--ui);text-transform:uppercase;letter-spacing:.1em;color:var(--c);margin-bottom:6px}
.abs__label span+span{font-weight:400;text-transform:none;letter-spacing:0;color:var(--grey)}
.abs h4{font:700 14px var(--head);text-transform:uppercase;letter-spacing:.04em;margin:16px 0 4px;color:var(--ink2)}
.abs p{font:400 16.5px/1.62 var(--serif);margin:0;-webkit-hyphens:auto;hyphens:auto;color:#131313}
.abs .abs__lic{font:400 12px var(--ui);color:var(--grey);margin-top:16px}.abs__lic a{text-decoration:underline}
.cite{font:400 12.5px/1.5 var(--ui);color:var(--grey);background:#f3f3f3;padding:10px 12px;border-radius:8px;margin:18px 0 12px}
.pill{display:inline-flex;align-items:center;justify-content:center;gap:8px;border-radius:30px;padding:11px 20px;font:500 15px var(--ui);cursor:pointer;border:0}
.pill--dark{background:#000;color:#fff}.pill--outline{background:#fff;border:2px solid #000;color:#000}.wide{width:100%;margin:8px 0}
.logbox{display:grid;grid-template-columns:auto 1fr;gap:6px 12px;align-items:center;background:#fff8e1;border:1px solid #ffe08a;border-radius:12px;padding:14px;margin:20px 0}
.logbox__icon{color:#b45309;grid-row:span 1}.logbox__txt b{display:block;font:800 16px var(--head)}.logbox__txt span{font:400 13px var(--ui);color:#6b5b2a}
.logbox .pill{grid-column:1/-1}.logbox.done{background:#ecfdf3;border-color:#a6e9c3}.logbox.done .logbox__icon{color:#0a7d43}
/* log sheet */
.logsheet{position:fixed;left:var(--side);right:var(--side);bottom:0;z-index:60;background:#fff;border-radius:16px 16px 0 0;padding:10px 18px calc(18px + env(safe-area-inset-bottom));transform:translate3d(0,105%,0);transition:transform .45s var(--ease);box-shadow:0 -6px 30px rgba(0,0,0,.25);max-height:92vh;overflow-y:auto}
body.logging .logsheet{transform:none}
.logsheet__grab{width:40px;height:4px;border-radius:3px;background:#ccc;margin:0 auto 10px}
.logsheet h3{font:800 20px var(--head);margin:0}.logsheet__title{font:400 13.5px var(--head);color:var(--grey);margin:4px 0 14px}
.seg{display:grid;grid-template-columns:1fr 1fr;gap:8px;margin-bottom:14px}
.seg button{background:#f3f3f3;border:2px solid transparent;border-radius:12px;padding:10px;text-align:left;cursor:pointer}
.seg button b{display:block;font:700 15px var(--head)}.seg button span{font:400 12.5px var(--ui);color:var(--grey)}
.seg button.on{background:#fff;border-color:#000}
.fld{display:block;margin-bottom:12px}.fld>span{display:block;font:600 12.5px var(--ui);text-transform:uppercase;letter-spacing:.06em;color:var(--grey);margin-bottom:6px}
.fld input[type=text],.fld textarea{width:100%;font:400 16px var(--head);border:1.5px solid #ddd;border-radius:10px;padding:10px 12px;outline:none}
.fld input:focus,.fld textarea:focus{border-color:#000}
.presets{display:grid;grid-template-columns:repeat(3,1fr);gap:8px;margin-bottom:10px}
.presets button{background:#f3f3f3;border:2px solid transparent;border-radius:12px;padding:9px 6px;cursor:pointer;text-align:center}
.presets button b{display:block;font:700 14px var(--head)}.presets button span{font:400 12.5px var(--ui);color:var(--grey)}
.presets button.on{background:#fff;border-color:#000}
.stepper{display:flex;align-items:center;justify-content:center;gap:12px}
.stepper>button{width:52px;height:44px;border-radius:22px;border:1.5px solid #ddd;background:#fff;font:600 15px var(--ui);cursor:pointer}
.stepper__num{display:flex;align-items:baseline;gap:6px;border-bottom:2px solid #000;padding:0 4px}
.stepper__num input{width:70px;border:0;outline:none;text-align:center;font:800 30px var(--head);background:none;-moz-appearance:textfield}
.stepper__num input::-webkit-outer-spin-button,.stepper__num input::-webkit-inner-spin-button{-webkit-appearance:none;margin:0}
.stepper__num span{font:400 14px var(--ui);color:var(--grey)}
.lsHint{font:400 12px/1.4 var(--ui);color:#888;margin:8px 0 0;text-align:center}
.toggle{display:flex;align-items:center;gap:10px;margin-top:10px;font:400 14.5px var(--head);cursor:pointer}.toggle em{color:var(--grey);font-style:normal}
.toggle input{display:none}.toggle i{width:44px;height:26px;border-radius:13px;background:#ddd;position:relative;transition:background .2s;flex:none}
.toggle i::after{content:"";position:absolute;left:3px;top:3px;width:20px;height:20px;border-radius:50%;background:#fff;box-shadow:0 1px 3px rgba(0,0,0,.3);transition:transform .25s var(--ease)}
.toggle input:checked+i{background:#0a7d43}.toggle input:checked+i::after{transform:translateX(18px)}
.chip{background:#f1ebff;color:#5b21b6;border:0;border-radius:16px;padding:7px 12px;font:500 13px var(--ui);cursor:pointer;margin:-4px 0 12px}
.lsCalc{font:400 14px var(--ui);color:var(--ink2);background:#f6f6f6;border-radius:10px;padding:10px 12px;margin-bottom:12px}.lsCalc b{font:800 18px var(--head)}
.lsBtns{display:grid;grid-template-columns:1fr 2fr;gap:10px}
/* My CPD */
.cpd-hero{display:flex;align-items:center;justify-content:space-between;background:#111;color:#fff;border-radius:14px;padding:18px}
.cpd-hero__big{font:900 44px/1 var(--head)}.cpd-hero__lbl{font:400 13px var(--ui);opacity:.8;margin-top:4px}
.ring{--p:0;width:74px;height:74px;border-radius:50%;background:conic-gradient(#fff200 calc(var(--p)*1%),#333 0);display:grid;place-items:center}
.ring span{width:58px;height:58px;border-radius:50%;background:#111;display:grid;place-items:center;font:800 15px var(--head)}
.cpd-goal{font:400 13.5px var(--ui);color:var(--grey);margin:10px 0 14px}
.cpd-split{display:grid;grid-template-columns:1fr 1fr;gap:10px}
.cpd-split div{background:#f5f5f5;border-radius:12px;padding:12px}.cpd-split b{display:block;font:800 24px var(--head)}.cpd-split span{font:400 12px/1.35 var(--ui);color:var(--grey)}
.sub{font:800 16px var(--ui);text-transform:uppercase;letter-spacing:.04em;margin:24px 0 8px;padding-bottom:8px;border-bottom:1px solid var(--rule)}
.cpd-month{font:400 15px/1.5 var(--head);margin:0 0 10px}
.entry{display:grid;grid-template-columns:1fr auto;gap:2px 10px;padding:12px 0;border-bottom:1px solid var(--rule);font:400 13px var(--ui);color:var(--grey)}
.entry b{color:var(--ink);font:600 14.5px/1.35 var(--head)}.entry .cr{font:800 15px var(--head);color:#000;text-align:right}
.entry .del{background:none;border:0;color:#b91c1c;font:500 12px var(--ui);cursor:pointer;padding:0;text-align:right}
.entry q{display:block;grid-column:1/-1;color:#333;font-style:italic;quotes:none;margin-top:3px}
.moc{border:2px solid #000;border-radius:14px;padding:14px;margin:12px 0}
.moc h4{font:800 15px var(--head);margin:0 0 2px}.moc>p{font:400 12.5px var(--ui);color:var(--grey);margin:0 0 10px}
.mocrow{display:grid;grid-template-columns:1fr auto;gap:8px;align-items:start;padding:8px 0;border-top:1px solid var(--rule)}
.mocrow small{display:block;font:600 11px var(--ui);text-transform:uppercase;letter-spacing:.06em;color:var(--grey);margin-bottom:2px}
.mocrow div{font:400 14px/1.45 var(--head);white-space:pre-wrap;word-break:break-word}
.copy{background:#f1f1f1;border:0;border-radius:8px;padding:6px 10px;font:500 12.5px var(--ui);cursor:pointer}.copy.ok{background:#dcfce7;color:#166534}
.mocopen{display:flex;justify-content:center;margin-top:10px;font:600 14px var(--ui);text-decoration:underline}
.demo-tools{display:flex;gap:8px;align-items:center;margin-top:18px;font:400 12.5px var(--ui);color:var(--grey)}
.demo-tools button{background:#f1f1f1;border:0;border-radius:14px;padding:6px 10px;font:500 12.5px var(--ui);cursor:pointer}
.fine{font:400 12px/1.5 var(--ui);color:#888;margin-top:18px}
.empty{font:400 14px var(--ui);color:var(--grey)}
.toast{position:fixed;left:50%;bottom:calc(96px + env(safe-area-inset-bottom));transform:translate(-50%,20px);background:#111;color:#fff;font:500 14px var(--ui);padding:10px 16px;border-radius:22px;opacity:0;pointer-events:none;transition:all .35s var(--ease);z-index:80;white-space:nowrap}
.toast.on{opacity:1;transform:translate(-50%,0)}
#printArea{display:none}
@media print{body>*:not(#printArea){display:none!important}#printArea{display:block;font:400 11pt var(--head);color:#000}
#printArea h1{font:800 20pt var(--head);margin:0}#printArea table{width:100%;border-collapse:collapse;margin-top:12pt}
#printArea th,#printArea td{border-bottom:1px solid #ccc;padding:5pt 4pt;text-align:left;vertical-align:top;font-size:9.5pt}
#printArea th{font:700 8.5pt var(--ui);text-transform:uppercase}.pr-meta{color:#444;margin:4pt 0 0}.pr-tot{margin-top:10pt;font-weight:700}.pr-note{margin-top:14pt;font-size:8.5pt;color:#555}}
"""

JS = r"""
(function(){
  var body=document.body,stage=document.getElementById('stage'),scrim=document.querySelector('.scrim'),scrim2=document.querySelector('.scrim2');
  var CPD='qmed-cpd',SAVED='qmed-saved',MS=520,depth=0,openPage=null,YEAR='2026';
  var TODAY=new Date(2026,9,22);   // demo edition date
  function $(id){return document.getElementById(id)}
  function esc(s){return String(s==null?'':s).replace(/[&<>"]/g,function(c){return{'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]})}
  function load(k){try{return JSON.parse(localStorage.getItem(k))||[]}catch(x){return[]}}
  function save(k,v){localStorage.setItem(k,JSON.stringify(v))}
  function toast(t){var el=$('toast');el.textContent=t;el.classList.add('on');clearTimeout(el._t);el._t=setTimeout(function(){el.classList.remove('on')},2200)}
  function credits(x){return x.minutes/60*(x.type==='prep'?2:0.5)}
  function fmt(n){return (Math.round(n*100)/100).toFixed(2).replace(/0$/,'')}
  function iso(d){return d.getFullYear()+'-'+String(d.getMonth()+1).padStart(2,'0')+'-'+String(d.getDate()).padStart(2,'0')}
  var MONTHS=['January','February','March','April','May','June','July','August','September','October','November','December'];
  function nice(isoS){var p=isoS.split('-');return MONTHS[+p[1]-1].slice(0,3)+' '+(+p[2])+', '+p[0]}

  // ---------- CPD totals
  function totals(){
    var l=load(CPD),y={review:0,prep:0},m={review:0,prep:0,min:0,n:0},ym=iso(TODAY).slice(0,7);
    l.forEach(function(x){if(x.date.slice(0,4)!==YEAR)return;y[x.type]+=credits(x);
      if(x.date.slice(0,7)===ym){m[x.type]+=credits(x);m.min+=x.minutes;m.n++}});
    var review=Math.min(30,y.review),total=review+y.prep;
    return {review:review,reviewRaw:y.review,prep:y.prep,total:total,month:m,list:l};
  }
  function paintCpd(){
    var t=totals();
    $('cpdPill').textContent=fmt(t.total);$('cpdYearBig').textContent=fmt(t.total);
    document.querySelectorAll('.yr').forEach(function(s){s.textContent=YEAR});
    var pct=Math.min(100,Math.round(t.total/25*100));$('cpdRing').style.setProperty('--p',pct);$('cpdRingTxt').textContent=pct+'%';
    $('cpdReview').textContent=fmt(t.review)+(t.reviewRaw>30?' (cap)':'');$('cpdPrep').textContent=fmt(t.prep);
    var m=t.month;
    $('cpdMonth').innerHTML=m.n?('<b>'+m.n+'</b> activities in '+MONTHS[TODAY.getMonth()]+' · <b>'+fmt(m.min/60)+' h</b> · <b>'+fmt(m.review+m.prep)+'</b> credits'):'Nothing logged yet this month.';
    var list=t.list.slice().sort(function(a,b){return a.date<b.date?1:-1});
    $('cpdList').innerHTML=list.length?list.map(function(x){
      return '<div class="entry"><b>'+esc(x.title)+'</b><span class="cr">'+fmt(credits(x))+' cr</span>'+
        '<span>'+nice(x.date)+' · '+x.minutes+' min · '+(x.type==='prep'?'Clinical question':'Reading')+'</span>'+
        '<button class="del" data-del="'+esc(x.key)+'">Remove</button>'+
        (x.type==='prep'&&x.question?'<q>Q: '+esc(x.question)+'</q>':'')+(x.message?'<q>'+esc(x.message)+'</q>':'')+'</div>'}).join('')
      :'<p class="empty">No activities yet. Open a paper and tap “Log to my CPD”, or use “Add a sample month” below.</p>';
    // logged badges on cards and articles
    document.querySelectorAll('[data-logged]').forEach(function(s){var id=s.dataset.logged;
      var mine=t.list.filter(function(x){return x.id===id});s.textContent=mine.length?'· ✓ logged':''});
    document.querySelectorAll('[data-logbox]').forEach(function(b){var id=b.dataset.logbox,
      mine=t.list.filter(function(x){return x.id===id}),st=b.querySelector('[data-logstate]'),btn=b.querySelector('[data-log]');
      b.classList.toggle('done',mine.length>0);
      if(mine.length){var c=mine.reduce(function(a,x){return a+credits(x)},0),mi=mine.reduce(function(a,x){return a+x.minutes},0);
        b.querySelector('b').textContent='Logged: '+mi+' min · '+fmt(c)+' credits';st.textContent='Saved to My CPD. Tap again to log more time.';btn.textContent='Log again'}
      else{b.querySelector('b').textContent='Earn MOC credit for this';btn.textContent='Log to my CPD'}});
    if($('mocEntries').childElementCount)renderMoc();
  }

  // ---------- log sheet
  var ls={id:null,type:'review',min:5};
  function skimOf(m){return Math.max(5,Math.round(m.full/3/5)*5)}
  function presetMin(k){var m=META[ls.id];return k==='full'?m.full:k==='skim'?skimOf(m):m.minutes}
  function openLog(id){
    var m=META[id];ls={id:id,type:'review',min:m.minutes};
    $('lsTitle').textContent=m.title;$('lsMsg').value='';$('lsQ').value='';
    $('pAbs').textContent=m.minutes+' min';$('pSkim').textContent='~'+skimOf(m)+' min';$('pFull').textContent='~'+m.full+' min';
    $('lsHint').textContent='Full-paper time is estimated from its length'+(m.words?' ('+m.words.toLocaleString('en-CA')+' words, '+m.exhibits+' figures/tables)':'')+'. Adjust it to the time you actually spent.';
    setType('review');
    // came back from the full paper? start from the full-paper estimate
    ls.min=presetMin(sessionStorage.getItem('full-'+id)==='1'?'full':'abstract');calc();
    body.classList.add('logging');$('logSheet').setAttribute('aria-hidden','false');
  }
  function closeLog(){body.classList.remove('logging');$('logSheet').setAttribute('aria-hidden','true');if(document.activeElement)document.activeElement.blur()}
  function setType(t){ls.type=t;document.querySelectorAll('.seg button').forEach(function(b){b.classList.toggle('on',b.dataset.type===t)});
    $('lsQWrap').hidden=t!=='prep';calc()}
  function mins(){return ls.min}
  function calc(){var inp=$('lsMin');if(document.activeElement!==inp)inp.value=ls.min;
    document.querySelectorAll('#lsPresets button').forEach(function(b){b.classList.toggle('on',presetMin(b.dataset.preset)===ls.min)});
    var c=mins()/60*(ls.type==='prep'?2:0.5);
    $('lsCalc').innerHTML='= <b>'+fmt(c)+'</b> MOC credits · Section 2 · '+(ls.type==='prep'?'Activity preparation (2/h)':'Educational content review (0.5/h)')}
  document.querySelectorAll('.seg button').forEach(function(b){b.addEventListener('click',function(){setType(b.dataset.type)})});
  document.querySelectorAll('#lsPresets button').forEach(function(b){b.addEventListener('click',function(){ls.min=presetMin(b.dataset.preset);calc()})});
  $('lsMinus').addEventListener('click',function(){ls.min=Math.max(1,ls.min-5);calc()});
  $('lsPlus').addEventListener('click',function(){ls.min=Math.min(600,ls.min+5);calc()});
  $('lsMin').addEventListener('input',function(){var v=parseInt(this.value,10);if(v>0){ls.min=Math.min(600,v);calc()}});
  $('lsMin').addEventListener('blur',function(){this.value=ls.min});
  $('lsSuggest').addEventListener('click',function(){$('lsMsg').value=META[ls.id].takeaway;$('lsMsg').focus()});
  $('lsCancel').addEventListener('click',closeLog);scrim2.addEventListener('click',closeLog);
  $('lsSave').addEventListener('click',function(){
    if(ls.type==='prep'&&!$('lsQ').value.trim()){$('lsQ').focus();toast('Add your clinical question');return}
    var m=META[ls.id],l=load(CPD),x={key:Date.now().toString(36),id:ls.id,title:m.title,doi:m.doi,journal:m.journal,
      date:iso(TODAY),minutes:mins(),type:ls.type,question:$('lsQ').value.trim(),message:$('lsMsg').value.trim()};
    l.push(x);save(CPD,l);closeLog();paintCpd();toast('Logged · +'+fmt(credits(x))+' MOC credits');
    if(navigator.vibrate)navigator.vibrate(10);
  });

  // ---------- My MOC entries (one per type per month; one per clinical question)
  function renderMoc(){
    var l=load(CPD),ym=iso(TODAY).slice(0,7),mm=l.filter(function(x){return x.date.slice(0,7)===ym});
    var box=$('mocEntries');
    if(!mm.length){box.innerHTML='<p class="empty">Log a few papers first, then come back here.</p>';return}
    var mName=MONTHS[TODAY.getMonth()]+' '+TODAY.getFullYear(),out=[];
    var rv=mm.filter(function(x){return x.type==='review'});
    if(rv.length){var mi=rv.reduce(function(a,x){return a+x.minutes},0),d=rv.map(function(x){return x.date}).sort();
      out.push(mocCard('Educational content review','One entry for this month’s journal reading',[
        ['Section','Section 2: Individual learning'],['Activity type','Educational content review (reading)'],
        ['Activity title','Journal reading: Le Quotidien Médical, '+mName+' ('+rv.length+' articles)'],
        ['Date',nice(d[0])+' to '+nice(d[d.length-1])],['Hours',fmt(mi/60)],
        ['Key message learned',rv.filter(function(x){return x.message}).map(function(x){return '• '+x.message}).join('\n')||'(add one key message)'],
        ['Articles',rv.map(function(x){return '• '+x.title+'. '+x.journal+'. doi:'+x.doi}).join('\n')]],fmt(mi/60*0.5)))}
    mm.filter(function(x){return x.type==='prep'}).forEach(function(x){
      out.push(mocCard('Activity preparation','Addressing a clinical question',[
        ['Section','Section 2: Individual learning'],['Activity type','Activity preparation: addressing a clinical question'],
        ['Activity title',x.question||x.title],['Date',nice(x.date)],['Hours',fmt(x.minutes/60)],
        ['Key message learned',x.message||'(add one key message)'],['Resource',x.title+'. '+x.journal+'. doi:'+x.doi]],fmt(x.minutes/60*2)))});
    box.innerHTML=out.join('')+'<a class="mocopen" href="https://www.royalcollege.ca/en/cpd/moc-program" target="_blank" rel="noopener">Open My MOC (Royal College) ↗</a>';
  }
  function mocCard(h,sub,rows,cr){return '<div class="moc"><h4>'+esc(h)+' · '+cr+' credits</h4><p>'+esc(sub)+'. Copy each field into My MOC.</p>'+
    rows.map(function(r){return '<div class="mocrow"><div><small>'+esc(r[0])+'</small>'+esc(r[1])+'</div><button class="copy" data-copy="'+esc(r[1])+'">Copy</button></div>'}).join('')+'</div>'}
  $('btnMoc').addEventListener('click',function(){renderMoc();$('mocEntries').scrollIntoView({behavior:'smooth',block:'start'})});

  // ---------- transcript (print to PDF)
  $('btnTranscript').addEventListener('click',function(){
    var l=load(CPD).slice().sort(function(a,b){return a.date<b.date?-1:1});
    if(!l.length){toast('Nothing logged yet');return}
    var name=localStorage.getItem('qmed-name')||prompt('Name to show on the transcript (optional)','')||'';
    localStorage.setItem('qmed-name',name);
    var tot=l.reduce(function(a,x){return a+credits(x)},0),mi=l.reduce(function(a,x){return a+x.minutes},0);
    $('printArea').innerHTML='<h1>CPD reading transcript</h1><p class="pr-meta">'+esc(name||'Physician')+' · Generated by Le Quotidien Médical (demo) on '+nice(iso(TODAY))+'</p>'+
      '<table><tr><th>Date</th><th>Article</th><th>Type</th><th>Min</th><th>Credits</th><th>Key message</th></tr>'+
      l.map(function(x){return '<tr><td>'+nice(x.date)+'</td><td>'+esc(x.title)+'<br><small>'+esc(x.journal)+' · doi:'+esc(x.doi)+'</small></td><td>'+(x.type==='prep'?'Activity preparation'+(x.question?': '+esc(x.question):''):'Educational content review')+'</td><td>'+x.minutes+'</td><td>'+fmt(credits(x))+'</td><td>'+esc(x.message)+'</td></tr>'}).join('')+
      '</table><p class="pr-tot">Total: '+l.length+' activities · '+fmt(mi/60)+' hours · '+fmt(tot)+' MOC credits (Section 2)</p>'+
      '<p class="pr-note">Self-reported by the physician. Credits calculated with the Royal College refreshed MOC framework (Section 2: educational content review 0.5 credits/hour, capped at 30/year; activity preparation 2 credits/hour). This is a record of learning, not an accredited certificate.</p>';
    window.print();
  });

  // ---------- demo data
  $('btnSample').addEventListener('click',function(){
    var ids=Object.keys(META),l=load(CPD),days=[2,3,6,8,9,13,15,16,20,21];
    days.forEach(function(d,i){var id=ids[i%ids.length],m=META[id],prep=(i===3||i===7);
      l.push({key:'s'+d+i,id:id,title:m.title,doi:m.doi,journal:m.journal,date:'2026-10-'+String(d).padStart(2,'0'),
        minutes:prep?35:(i%3===0?m.full:m.minutes),type:prep?'prep':'review',
        question:prep?(i===3?'Should my 86-year-old nursing home patient with AF and full ADL dependence stay on rivaroxaban?':'Is real-time CGM worth starting for my patient with T2D and HbA1c of 9.8%?'):'',
        message:m.takeaway})});
    save(CPD,l);paintCpd();toast('Sample month added');
  });
  $('btnClear').addEventListener('click',function(){if(confirm('Clear all logged activities?')){save(CPD,[]);$('mocEntries').innerHTML='';paintCpd()}});

  // ---------- saved
  function paintBm(){var ids=load(SAVED).map(function(x){return x.id});
    document.querySelectorAll('.bm').forEach(function(b){b.classList.toggle('on',ids.indexOf(b.dataset.id)>=0)})}
  function renderSaved(){var l=load(SAVED).slice().reverse();
    $('savedList').innerHTML=l.length?l.map(function(x){return '<a class="mcard mcard--row" href="#'+esc(x.id)+'"><div class="mcard__body"><p class="mcard__sup" style="color:'+esc(x.color)+'">'+esc(x.sec)+'</p><h3 class="mcard__title">'+esc(x.title)+'</h3></div></a>'}).join('')
      :'<p class="empty">No saved papers yet. Tap the bookmark icon on any paper.</p>'}

  // ---------- clicks
  document.addEventListener('click',function(ev){
    var t=ev.target;
    var b=t.closest('.bm');if(b){ev.preventDefault();var l=load(SAVED),i=-1;l.forEach(function(x,j){if(x.id===b.dataset.id)i=j});
      if(i>=0)l.splice(i,1);else l.push({id:b.dataset.id,title:b.dataset.title,sec:b.dataset.sec,color:b.dataset.color});save(SAVED,l);paintBm();renderSaved();
      toast(i>=0?'Removed from Saved':'Saved');return}
    var s=t.closest('.sh');if(s){ev.preventDefault();var d={title:s.dataset.title,url:s.dataset.url};
      if(navigator.share){navigator.share(d).catch(function(){})}else if(navigator.clipboard){navigator.clipboard.writeText(d.url);toast('Link copied')}return}
    var lg=t.closest('[data-log]');if(lg){ev.preventDefault();openLog(lg.dataset.log);return}
    var cp=t.closest('.copy');if(cp){ev.preventDefault();var v=cp.dataset.copy;
      (navigator.clipboard?navigator.clipboard.writeText(v):Promise.reject()).then(function(){cp.textContent='Copied';cp.classList.add('ok');
        setTimeout(function(){cp.textContent='Copy';cp.classList.remove('ok')},1500)}).catch(function(){prompt('Copy this:',v)});return}
    var dl=t.closest('[data-del]');if(dl){var l2=load(CPD).filter(function(x){return x.key!==dl.dataset.del});save(CPD,l2);paintCpd();return}
    var fp=t.closest('[data-fullpaper]');if(fp){sessionStorage.setItem('full-'+fp.dataset.fullpaper,'1')}
    if(t.closest('[data-close]')||t===scrim){ev.preventDefault();close();return}
    var a=t.closest('a[href^="#"]');
    if(a&&!t.closest('.mcard__img')&&t.closest('.mcard')===null){return}
  });
  // whole card taps open the article
  document.querySelectorAll('.mcard').forEach(function(c){c.addEventListener('click',function(ev){
    if(ev.target.closest('button,a'))return;var a=c.querySelector('.mcard__title a');if(a)location.hash=a.getAttribute('href')})});

  // ---------- iOS-style sheet
  function showSheet(p){clearTimeout(p._t);p._t=null;p.hidden=false;p.scrollTop=0;
    stage.style.transformOrigin='50% '+window.scrollY+'px';p.getBoundingClientRect();
    body.classList.add('sheet');p.classList.add('is-open');openPage=p;
    if(p.id==='cpd')paintCpd();if(p.id==='saved')renderSaved()}
  function hideSheet(p){p.classList.remove('is-open');body.classList.remove('sheet');if(openPage===p)openPage=null;
    clearTimeout(p._t);p._t=setTimeout(function(){p._t=null;if(!p.classList.contains('is-open'))p.hidden=true},MS)}
  function close(){closeLog();if(openPage)hideSheet(openPage);
    if(depth>0){history.back()}else{history.replaceState(null,'',location.pathname+location.search);route()}}
  var drag=null;
  function setT(v){if(!openPage)return;openPage.style.transition=v;stage.style.transition=v;scrim.style.transition=v}
  document.addEventListener('touchstart',function(e){if(!openPage||body.classList.contains('logging')||e.touches.length>1)return;
    var p=e.target.closest('.page');if(p!==openPage)return;
    drag={y0:e.touches[0].clientY,x0:e.touches[0].clientX,t:Date.now(),y:e.touches[0].clientY,v:0,dy:0,on:false,top:p.scrollTop<=0}},{passive:true});
  document.addEventListener('touchmove',function(e){if(!drag)return;
    var y=e.touches[0].clientY,dy=y-drag.y0,dx=e.touches[0].clientX-drag.x0,now=Date.now();
    if(!drag.on){if(!drag.top||dy<0||Math.abs(dx)>Math.abs(dy)+4){drag=null;return}
      if(e.cancelable)e.preventDefault();if(dy<6)return;drag.on=true;setT('none')}
    if(e.cancelable)e.preventDefault();
    drag.v=(y-drag.y)/Math.max(1,now-drag.t);drag.y=y;drag.t=now;drag.dy=Math.max(0,dy);
    var k=1-Math.min(1,drag.dy/(window.innerHeight*.85));
    openPage.style.transform='translate3d(0,'+drag.dy+'px,0)';scrim.style.opacity=String(k);stage.style.setProperty('--k',k)},{passive:false});
  function endDrag(){if(!drag)return;var d=drag;drag=null;if(!d.on||!openPage)return;
    setT('');openPage.style.transform='';scrim.style.opacity='';stage.style.removeProperty('--k');
    if(d.dy>window.innerHeight*.25||(d.v>1&&d.dy>40))close()}
  document.addEventListener('touchend',endDrag,{passive:true});document.addEventListener('touchcancel',endDrag,{passive:true});
  [scrim,scrim2].forEach(function(s){s.addEventListener('touchmove',function(e){if(e.cancelable)e.preventDefault()},{passive:false})});

  function route(){
    var id=decodeURIComponent(location.hash.slice(1)),t=id&&document.getElementById(id);
    var page=t&&t.classList.contains('page')?t:null;
    document.querySelectorAll('.page').forEach(function(p){if(p===page)return;
      if(p.classList.contains('is-open'))hideSheet(p);else if(!p._t)p.hidden=true});
    if(page&&!page.classList.contains('is-open'))showSheet(page);
    var tab=page?(page.id==='cpd'?'cpd':page.id==='saved'?'saved':''):((id==='m-sections'||id.indexOf('m-sec-')===0)?'sections':'home');
    document.querySelectorAll('.tabbar a').forEach(function(a){a.classList.toggle('on',a.dataset.tab===tab)});
    if(!page){if(id==='top')window.scrollTo({top:0,behavior:'smooth'});else if(t)t.scrollIntoView({behavior:'smooth'})}
  }
  if('scrollRestoration' in history){history.scrollRestoration='manual'}
  window.addEventListener('hashchange',function(){var id=location.hash.slice(1),t=id&&document.getElementById(id);
    depth=t&&t.classList.contains('page')?depth+1:0;route()});
  paintBm();paintCpd();route();
})();
"""

if __name__ == "__main__":
    build()
