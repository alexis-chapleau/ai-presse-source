"""Render a Le Quotidien IA edition (JSON) into a La Presse-style HTML page.

Usage: python render.py editions/YYYY-MM-DD.json

Writes editions/YYYY-MM-DD.html next to the JSON and copies it to latest.html.
The page is a single file: the front page plus one article page per story and
per dossier, switched with #anchors (like clicking an article on lapresse.ca).
See SCHEMA.md for the input format.
"""
import html
import json
import math
import re
import shutil
import sys
import urllib.parse
import urllib.request
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent
CACHE = ROOT / ".cache" / "og-images.json"
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130 Safari/537.36"

# name, colour (La Presse section palette), decorative glyph for image-less panels
SECTIONS = {
    "models":   ("New Models",  "#FFAF00", "LLM"),
    "safety":   ("AI Safety",   "#5A79A0", "AI"),
    "cyber":    ("Cyber",       "#D25F68", "</>"),
    "doom":     ("Doom Watch",  "#840132", "p(doom)"),
    "hardware": ("Hardware",    "#207FB7", "GPU"),
    "bench":    ("Benchmarks",  "#14A574", "%"),
    "math":     ("Mathematics", "#A05FA8", "∑"),
    "physics":  ("Physics",     "#FF6C00", "Ψ"),
    "science":  ("AI Science",  "#6B9500", "DNA"),
}
ORDER = list(SECTIONS)

e = lambda s: html.escape(str(s or ""), quote=True)

# og:images that are site logos or placeholders rather than photos
NOT_A_PHOTO = re.compile(r"logo|default|placeholder|gravatar|blavatar|favicon|icon|avatar", re.I)


def usable(img_url):
    return bool(img_url) and img_url.startswith("http") and not NOT_A_PHOTO.search(img_url)


# ---------------------------------------------------------------- images
def load_cache():
    try:
        return json.loads(CACHE.read_text(encoding="utf-8"))
    except Exception:
        return {}


def og_image(url, cache):
    """Return the og:image of a page (cached), or '' if none/unreachable."""
    if not url or not url.startswith("http"):
        return ""
    if url in cache:
        return cache[url]
    found = ""
    try:
        req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "text/html"})
        with urllib.request.urlopen(req, timeout=8) as r:
            page = r.read(400_000).decode("utf-8", "ignore")
        for pat in (r'<meta[^>]+(?:property|name)=["\'](?:og:image(?::secure_url)?|twitter:image(?::src)?)["\'][^>]*>',):
            for tag in re.findall(pat, page, flags=re.I):
                m = re.search(r'content=["\']([^"\']+)', tag, flags=re.I)
                if m:
                    found = urllib.parse.urljoin(url, html.unescape(m.group(1).strip()))
                    break
            if found:
                break
    except Exception:
        found = ""
    cache[url] = found
    return found


def weather():
    try:
        req = urllib.request.Request("https://wttr.in/Montreal?format=%c|%t", headers={"User-Agent": "curl/8"})
        with urllib.request.urlopen(req, timeout=6) as r:
            icon, temp = r.read().decode("utf-8").strip().split("|")
        return icon.strip(), temp.replace("+", "").strip()
    except Exception:
        return None


# ---------------------------------------------------------------- pieces
def sec(s):
    return SECTIONS.get(s.get("section"), ("AI", "#777", "AI"))


def badge(section_key, extra=""):
    name, color, _ = SECTIONS.get(section_key, ("AI", "#777", ""))
    return f'<span class="badge" style="background:{color}">{e(name)}</span>{extra}'


def dossier_badge(n):
    return f'<span class="badge badge--dossier"><b>Dossier</b>{n} updates</span>'


def visual(item, cls="vis", big=False):
    """Image block with a typographic fallback underneath (shown if the image fails)."""
    name, color, glyph = SECTIONS.get(item.get("section"), ("AI", "#777", "AI"))
    img = (item.get("image") or {}).get("url", "")
    fallback = f'<span class="vis__glyph">{e(glyph)}</span><span class="vis__name">{e(name)}</span>'
    tag = ""
    if img:
        tag = (f'<img src="{e(img)}" alt="" loading="lazy" referrerpolicy="no-referrer" '
               f'onerror="this.parentNode.classList.add(\'vis--none\');this.remove()">')
    none = "" if img else " vis--none"
    return f'<div class="{cls}{none}" style="--c:{color}">{fallback}{tag}</div>'


def card(s, size="md"):
    """Front-page story card: image, badges, italic suptitle, headline, source line."""
    title_cls = "card__title card__title--slab" if s.get("opinion") else "card__title"
    lead = f'<p class="card__lead">{e(s.get("standfirst"))}</p>' if size == "lg" else ""
    src = s.get("source") or {}
    return f'''<article class="card card--{size}">
  <a class="card__link" href="#{e(s["id"])}">{visual(s)}</a>
  <div class="card__badges">{badge(s.get("section"))}</div>
  {f'<p class="card__sup">{e(s.get("suptitle"))}</p>' if s.get("suptitle") else ""}
  <h3 class="{title_cls}"><a href="#{e(s["id"])}">{e(s.get("title"))}</a></h3>
  {lead}
  <p class="date">{e(src.get("name"))}{" · " + e(src.get("date")) if src.get("date") else ""}</p>
</article>'''


def row_item(s):
    """Compact horizontal card used in section lists."""
    src = s.get("source") or {}
    title_cls = "row__title card__title--slab" if s.get("opinion") else "row__title"
    return f'''<article class="row">
  <a class="row__thumb" href="#{e(s["id"])}">{visual(s)}</a>
  <div>
    {f'<p class="card__sup">{e(s.get("suptitle"))}</p>' if s.get("suptitle") else ""}
    <h4 class="{title_cls}"><a href="#{e(s["id"])}">{e(s.get("title"))}</a></h4>
    <p class="date">{e(src.get("name"))}{" · " + e(src.get("date")) if src.get("date") else ""}</p>
  </div>
</article>'''


def dossier_row(d):
    status = ('<span class="status status--new">New today</span>' if d.get("status") == "new"
              else '<span class="status">No change</span>')
    return f'''<article class="row row--dossier">
  <a class="row__thumb" href="#{e(d["id"])}">{visual(d)}</a>
  <div>
    <div class="card__badges">{dossier_badge(len(d.get("timeline", [])))}</div>
    <h4 class="row__title"><a href="#{e(d["id"])}">{e(d.get("title"))}</a></h4>
    <p class="date">{status}</p>
  </div>
</article>'''


# ---------------------------------------------------------------- front page
def front(data, stories, dossiers, wx):
    lead = next((s for s in stories if s.get("lead")), stories[0])
    featured = [s for s in stories if s.get("featured") and s is not lead][:3]
    if len(featured) < 3:
        for k in ORDER:
            cand = next((s for s in stories if s.get("section") == k and s is not lead and s not in featured), None)
            if cand and len(featured) < 3:
                featured.append(cand)
    briefs = [s for s in stories if s.get("brief")][:7]
    lname, lcolor, _ = sec(lead)
    limg = (lead.get("image") or {}).get("url", "")
    blur = f' style="--bg:url(&quot;{e(limg)}&quot;)"' if limg else ""
    num, quote = data.get("number") or {}, data.get("quote") or {}

    out = ['<div class="d-only">']
    # hero row: big story + sidebar
    out.append(f'''<section class="wrap hero-row">
<div class="hero-main">
  <article class="hero" style="--c:{lcolor}">
    <a class="hero__img" href="#{e(lead["id"])}">{visual(lead, "vis vis--hero")}</a>
    <div class="hero__panel"{blur}>
      <div class="hero__panelInner">
        <div class="card__badges">{badge(lead.get("section"))}</div>
        <p class="hero__sup">{e(lead.get("suptitle") or lead.get("kicker"))}</p>
        <h1 class="hero__title"><a href="#{e(lead["id"])}">{e(lead.get("title"))}</a></h1>
        <p class="hero__lead">{e(lead.get("standfirst"))}</p>
        <p class="date">Published at {e(data.get("generated_at"))}</p>
      </div>
    </div>
  </article>
  <div class="trio">{"".join(card(s) for s in featured)}</div>
</div>
<aside class="side">
  <div class="adlabel">The number</div>
  <div class="numbox">
    <div class="numbox__value">{e(num.get("value"))}</div>
    <p>{e(num.get("text"))}</p>
    {f'<a class="pill pill--dark" href="{e(num.get("url"))}" target="_blank" rel="noopener">See the source</a>' if num.get("url") else ""}
  </div>
  <div class="essentials">
    <h2>Today's essentials<br><span>{len(briefs)} must-reads</span></h2>
    {"".join(f'<a class="brief" href="#{e(s["id"])}"><span class="brief__dot" style="background:{sec(s)[1]}"></span><span><small style="color:{sec(s)[1]}">{e(sec(s)[0])}</small>{e(s["brief"] if isinstance(s.get("brief"), str) else s.get("title"))}</span></a>' for s in briefs)}
  </div>
</aside>
</section>''')

    # dossiers band (La Presse black "grouped" row)
    if dossiers:
        out.append('<section class="band"><div class="wrap"><h2 class="band__title">Dossiers · Ongoing stories</h2><div class="band__grid">')
        for d in dossiers:
            status = ('<span class="status status--new">New today</span>' if d.get("status") == "new"
                      else '<span class="status">No change</span>')
            out.append(f'''<article class="dcard">
  <a class="dcard__img" href="#{e(d["id"])}">{visual(d)}</a>
  <div class="dcard__body">
    <div class="card__badges">{dossier_badge(len(d.get("timeline", [])))}{badge(d.get("section"))}</div>
    <h3><a href="#{e(d["id"])}">{e(d.get("title"))}</a></h3>
    <p>{status}{e(d.get("update"))}</p>
  </div>
</article>''')
        out.append('</div></div></section>')

    # quote
    if quote.get("text"):
        out.append(f'''<section class="wrap quote">
  <div class="quote__label">The quote</div>
  <blockquote>{e(quote.get("text"))}</blockquote>
  <p class="quote__who"><b>{e(quote.get("speaker"))}</b>{", " + e(quote.get("context")) if quote.get("context") else ""}
  {f' · <a href="{e(quote.get("url"))}" target="_blank" rel="noopener">source</a>' if quote.get("url") else ""}</p>
</section>''')

    # one block per section
    for k in ORDER:
        items = [s for s in stories if s.get("section") == k and s is not lead]
        ds = [d for d in dossiers if d.get("section") == k]
        if not items and not ds:
            continue
        name, color, _ = SECTIONS[k]
        # lead each section with its first story that has a photo
        big = next((s for s in items if (s.get("image") or {}).get("url")), items[0] if items else None)
        rest = [s for s in items if s is not big]
        out.append(f'''<section class="wrap secblock" id="sec-{k}" style="--c:{color}">
  <h2 class="sechead"><a href="#sec-{k}">{e(name)}</a></h2>
  <div class="secgrid">
    <div>{card(big, "lg") if big else ""}</div>
    <div class="seclist">{"".join(dossier_row(d) for d in ds)}{"".join(row_item(s) for s in rest)}</div>
  </div>
</section>''')
    out.append('</div>')
    return "\n".join(out)


# ---------------------------------------------------------------- article pages
def subnav(section_key, stories, dossiers, current_id):
    name, color, _ = SECTIONS[section_key]
    links = [(d["id"], "Dossier") for d in dossiers if d.get("section") == section_key]
    links += [(s["id"], s.get("suptitle") or s.get("kicker") or "Story")
              for s in stories if s.get("section") == section_key]
    li = "".join(f'<li><a href="#{e(i)}"{" class=on" if i == current_id else ""}>{e(t)}</a></li>' for i, t in links)
    return (f'<nav class="subnav" style="background:{color}"><ul class="wrap"><li><a class="subnav__back" href="#top">‹ Front page</a></li>'
            f'<li><a href="#sec-{section_key}"><b>{e(name)}</b></a></li>{li}</ul></nav>')


def sidebar(data, stories, current_id):
    picks = [s for s in stories if s.get("lead") or s.get("featured")]
    picks = [s for s in picks if s["id"] != current_id][:4]
    items = "".join(f'''<a class="mini" href="#{e(s["id"])}">{visual(s, "vis mini__img")}<span><small style="color:{sec(s)[1]}">{e(sec(s)[0])}</small>{e(s.get("title"))}</span></a>''' for s in picks)
    return f'''<aside class="aside">
  <div class="promo">
    <div class="promo__logo"><span>Le Quotidien</span><b>IA.</b></div>
    <h3>Also in today's edition</h3>
    {items}
    <a class="pill pill--outline" href="#top">Back to the front page</a>
  </div>
</aside>'''


def byline(data, src):
    return f'''<div class="byline">
  <div class="byline__logo">IA.</div>
  <div><b>Le Quotidien IA</b><span>Published {e(data.get("date_long"))} at {e(data.get("generated_at"))}</span>
  {f'<span>From {e(src.get("name"))}{", " + e(src.get("date")) if src.get("date") else ""}</span>' if src else ""}</div>
</div>'''


# ---------------------------------------------------------------- phone ("app") pieces
PATHS = {
    "home": "M3 10.5 12 3l9 7.5V20a1 1 0 0 1-1 1h-5v-6h-6v6H4a1 1 0 0 1-1-1z",
    "bookmark": "M6 3h12v18l-6-4.5L6 21z",
    "share": "M12 15V3M8 7l4-4 4 4M7 11H5v10h14V11h-2",
    "stack": "M12 3 3 8l9 5 9-5zM3 13l9 5 9-5",
    "grid": "M4 4h7v7H4zM13 4h7v7h-7zM4 13h7v7H4zM13 13h7v7h-7z",
    "calendar": "M4 6h16v15H4zM4 10h16M8 3v4M16 3v4",
    "book": "M12 6.5C10 5 7 4.5 3 5v14c4-.5 7 0 9 1.5 2-1.5 5-2 9-1.5V5c-4-.5-7 0-9 1.5zM12 6.5V20",
}


def icon(name, size=22):
    return (f'<svg viewBox="0 0 24 24" width="{size}" height="{size}" fill="none" stroke="currentColor" stroke-width="1.8" '
            f'stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="{PATHS[name]}"/></svg>')


def shortdate(s):
    for fmt in ("%B %d, %Y", "%b %d, %Y", "%Y-%m-%d"):
        try:
            d = datetime.strptime(str(s).strip(), fmt)
            return f"{d:%b} {d.day}"
        except ValueError:
            pass
    return str(s or "")


def read_time(item):
    text = [item.get("standfirst") or item.get("update") or ""] + list(item.get("body") or item.get("background") or [])
    return max(1, math.ceil(sum(len(str(p).split()) for p in text) / 200))


def actions(item):
    """Bookmark + share buttons (wired up in JS; share opens the iPhone share sheet with the source link)."""
    name, color, _ = sec(item)
    url = (item.get("source") or {}).get("url") or next((t.get("url") for t in item.get("timeline", []) if t.get("url")), "")
    img = (item.get("image") or {}).get("url", "")
    return (f'<span class="acts"><button class="bm" type="button" aria-label="Save" data-id="{e(item["id"])}" data-title="{e(item.get("title"))}" '
            f'data-sec="{e(name)}" data-color="{color}" data-img="{e(img)}">{icon("bookmark", 21)}</button>'
            f'<button class="sh" type="button" aria-label="Share" data-title="{e(item.get("title"))}" data-url="{e(url)}">{icon("share", 21)}</button></span>')


def mcard(s, compact=False):
    """La Presse app feed card: rounded white card, photo with section badge, headline, time + actions."""
    name, color, _ = sec(s)
    when = shortdate((s.get("source") or {}).get("date"))
    bdg = f'<span class="badge mbadge" style="background:{color}">{e(name)}</span>'
    img = f'<a class="mcard__img" href="#{e(s["id"])}">{visual(s)}{"" if compact else bdg}</a>'
    title_cls = "mcard__title mcard__title--slab" if s.get("opinion") else "mcard__title"
    return f'''<article class="mcard{" mcard--row" if compact else ""}">
  {"" if compact else img}
  <div class="mcard__body">
    {bdg if compact else ""}
    {f'<p class="mcard__sup">{e(s.get("suptitle"))}</p>' if s.get("suptitle") else ""}
    <h3 class="{title_cls}"><a href="#{e(s["id"])}">{e(s.get("title"))}</a></h3>
    {"" if compact else f'<p class="mcard__lead">{e(s.get("standfirst"))}</p>'}
    <div class="mcard__foot"><i class="mdot"></i>{e(when)}{actions(s)}</div>
  </div>
  {img if compact else ""}
</article>'''


def mdossier(d):
    status = ('<span class="status status--new">New today</span>' if d.get("status") == "new"
              else '<span class="status">No change</span>')
    return f'''<article class="mcard mcard--dossier">
  <a class="mcard__img" href="#{e(d["id"])}">{visual(d)}<span class="mbadge">{dossier_badge(len(d.get("timeline", [])))}</span></a>
  <div class="mcard__body">
    <p class="mcard__sup">{e(sec(d)[0])} · Ongoing story</p>
    <h3 class="mcard__title"><a href="#{e(d["id"])}">{e(d.get("title"))}</a></h3>
    <p class="mcard__lead">{status}{e(d.get("update"))}</p>
    <div class="mcard__foot"><i class="mdot"></i>{len(d.get("timeline", []))} events{actions(d)}</div>
  </div>
</article>'''


def mobile_feed(data, stories, dossiers):
    lead = next((s for s in stories if s.get("lead")), stories[0])
    featured = [s for s in stories if s.get("featured") and s is not lead][:3]
    top = [lead] + featured
    num, quote = data.get("number") or {}, data.get("quote") or {}
    out = ['<div class="m-only mfeed">',
           '<h2 class="mhead" id="m-head">The headlines<span>What you need to know this morning.</span></h2>',
           "".join(mcard(s) for s in top)]
    if dossiers:
        out.append('<h2 class="mhead" id="m-dossiers">Dossiers<span>The stories we are following.</span></h2>')
        out.append("".join(mdossier(d) for d in dossiers))
    if quote.get("text"):
        out.append(f'''<div class="mcard mquote"><div class="quote__label">The quote</div><blockquote>{e(quote.get("text"))}</blockquote>
<p class="quote__who"><b>{e(quote.get("speaker"))}</b>{", " + e(quote.get("context")) if quote.get("context") else ""}</p></div>''')
    if num.get("value"):
        out.append(f'''<div class="mcard mnum"><div class="quote__label">The number</div><div class="numbox__value">{e(num.get("value"))}</div><p>{e(num.get("text"))}</p></div>''')
    shown = [k for k in ORDER if any(s.get("section") == k and s not in top for s in stories)]
    chips = "".join(f'<a href="#m-sec-{k}" style="--c:{SECTIONS[k][1]}">{e(SECTIONS[k][0])}</a>' for k in shown)
    out.append(f'<h2 class="mhead" id="m-sections">By section<span>Everything else in today\'s edition.</span></h2><div class="mchips">{chips}</div>')
    for k in ORDER:
        items = [s for s in stories if s.get("section") == k and s not in top]
        if not items:
            continue
        name, color, _ = SECTIONS[k]
        big = next((s for s in items if (s.get("image") or {}).get("url")), None)
        out.append(f'<h3 class="msec" id="m-sec-{k}" style="--c:{color}">{e(name)}</h3>')
        out.append("".join(mcard(s, compact=s is not big) for s in ([big] if big else []) + [s for s in items if s is not big]))
    srcs = "".join(f'<li><a href="{e(x.get("url"))}" target="_blank" rel="noopener">{e(x.get("title"))}</a> — {e(x.get("outlet"))}</li>' for x in data.get("sources", []))
    out.append(f'<details class="mcard msources"><summary>Sources for this edition ({len(data.get("sources", []))})</summary><ol>{srcs}</ol></details>')
    out.append(f'<p class="mcolophon">Le Quotidien IA · No. {e(data.get("issue"))} · {e(data.get("date_long"))}<br>Compiled by Claude from public sources. Images belong to their sources.</p>')
    out.append('</div>')
    return "\n".join(out)


def sheet_bar(item, label=None):
    name, color, _ = sec(item)
    return (f'<div class="msheet__bar m-only" style="background:{color}"><a class="msheet__grab" href="#top" data-close aria-label="Close"></a>'
            f'<span>{e(label or name)}</span>{actions(item)}</div>')


def mobile_meta(item, src_name):
    when = shortdate((item.get("source") or {}).get("date")) or "Today"
    return (f'<div class="mmeta m-only"><span><i class="mdot"></i>{e(when)}</span><span>{icon("book", 17)} {read_time(item)} min</span></div>'
            + (f'<div class="msrc m-only">{e(src_name)}</div>' if src_name else ""))


def story_page(s, data, stories, dossiers):
    name, color, _ = sec(s)
    src = s.get("source") or {}
    credit = (s.get("image") or {}).get("credit") or src.get("name") or ""
    paras = s.get("body") or [s.get("standfirst", "")]
    facts = s.get("facts") or []
    extra = s.get("extra_sources") or []
    related = [x for x in stories if x.get("section") == s.get("section") and x["id"] != s["id"]][:3]
    h1_cls = "art__title art__title--slab" if s.get("opinion") else "art__title"
    return f'''<div class="page" id="{e(s["id"])}" hidden>
{subnav(s.get("section"), stories, dossiers, s["id"])}
<div class="wrap artgrid" style="--c:{color}">
  <article class="art">
    {sheet_bar(s)}
    <div class="card__badges">{badge(s.get("section"))}{'<span class="badge badge--opinion">Analysis</span>' if s.get("opinion") else ""}</div>
    {f'<p class="art__kicker">{e(s.get("kicker"))}</p>' if s.get("kicker") else ""}
    <h1 class="{h1_cls}">{e(s.get("title"))}</h1>
    {mobile_meta(s, src.get("name"))}
    <figure class="art__fig">{visual(s, "vis vis--art")}
      <figcaption><span class="credit">Photo: {e(credit)}</span><span class="cap">{e(s.get("suptitle"))}</span></figcaption>
    </figure>
    {byline(data, src)}
    <p class="art__lead">{e(s.get("standfirst"))}</p>
    {"".join(f"<p>{e(p)}</p>" for p in paras)}
    {f'<div class="why"><div class="why__label">Why it matters</div><p>{e(s.get("why"))}</p></div>' if s.get("why") else ""}
    {('<div class="facts"><div class="why__label">Key facts</div><ol>' + "".join(f"<li>{e(f)}</li>" for f in facts) + "</ol></div>") if facts else ""}
    <div class="srcbox">
      <div><div class="why__label">Source</div><b>{e(src.get("name"))}</b>{" · " + e(src.get("date")) if src.get("date") else ""}
      {"".join(f'<br><a href="{e(x.get("url"))}" target="_blank" rel="noopener">Also: {e(x.get("name"))}</a>' for x in extra)}</div>
      {f'<a class="pill pill--dark" href="{e(src.get("url"))}" target="_blank" rel="noopener">Read the original ›</a>' if src.get("url") else ""}
    </div>
    {('<section class="related"><h2 class="sechead">More in ' + e(name) + '</h2><div class="trio">' + "".join(card(r) for r in related) + '</div></section>') if related else ""}
  </article>
  {sidebar(data, stories, s["id"])}
</div>
</div>'''


def timeline_item(t):
    link = f' <a href="{e(t.get("url"))}" target="_blank" rel="noopener">source ›</a>' if t.get("url") else ""
    return f'<li><time>{e(t.get("date"))}</time><p>{e(t.get("text"))}{link}</p></li>'


def dossier_page(d, data, stories, dossiers):
    name, color, _ = sec(d)
    tl = d.get("timeline") or []
    status = ('<span class="status status--new">New today</span>' if d.get("status") == "new"
              else '<span class="status">No change</span>')
    return f'''<div class="page" id="{e(d["id"])}" hidden>
{subnav(d.get("section"), stories, dossiers, d["id"])}
<div class="wrap artgrid" style="--c:{color}">
  <article class="art">
    {sheet_bar(d, "Dossier · " + name)}
    <div class="card__badges">{dossier_badge(len(tl))}{badge(d.get("section"))}</div>
    <p class="art__kicker">Ongoing story</p>
    <h1 class="art__title">{e(d.get("title"))}</h1>
    {mobile_meta(d, None)}
    <figure class="art__fig">{visual(d, "vis vis--art")}
      {f'<figcaption><span class="credit">Photo: {e((d.get("image") or {}).get("credit"))}</span></figcaption>' if d.get("image") else ""}
    </figure>
    {byline(data, None)}
    <div class="why why--update"><div class="why__label">{status} Today</div><p>{e(d.get("update"))}</p></div>
    {"".join(f"<p>{e(p)}</p>" for p in d.get("background") or [])}
    <h2 class="sechead">Timeline</h2>
    <ol class="timeline">{"".join(timeline_item(t) for t in tl)}</ol>
  </article>
  {sidebar(data, stories, d["id"])}
</div>
</div>'''


# ---------------------------------------------------------------- page shell
CSS = r"""
:root{--red:#e12929;--ink:#000;--ink2:#232325;--text:#131313;--grey:#686868;--grey2:#8d8d8d;--rule:#dcdcdc;--bg:#f8f8f8;
--head:"Figtree","Verlag",Arial,sans-serif;--ui:"Rubik","rubrik",Arial,sans-serif;--slab:"Roboto Slab","Sentinel",Georgia,serif;--serif:"Roboto Serif",Georgia,serif}
*{box-sizing:border-box}html{scroll-behavior:smooth}
body{margin:0;background:var(--bg);color:var(--text);font-family:var(--head);-webkit-font-smoothing:antialiased}
a{color:inherit;text-decoration:none}[hidden]{display:none!important}
.wrap{max-width:1320px;margin:0 auto;padding:0 15px}
/* --- top utility + header --- */
.util{background:#fff;border-bottom:1px solid #ececec;font:400 13px var(--ui);color:#777}
.util ul{display:flex;justify-content:center;list-style:none;margin:0;padding:6px 0}
.util li+li{border-left:1px solid #ddd}.util a{padding:0 20px}.util a:hover{color:#000}
.mast{background:#fff}.mast .wrap{display:flex;align-items:center;height:130px;gap:24px}
.logo{display:flex;flex-direction:column;justify-content:center;background:var(--red);color:#fff;width:100px;height:100px;padding:10px 8px;line-height:.95;flex:none}
.logo span{font:900 13px var(--head);text-transform:uppercase;letter-spacing:.01em}
.logo b{font:900 48px var(--head);letter-spacing:-.03em}
.mast__date{font:400 15px var(--ui);color:#555;margin-top:44px}
.mast__mid{margin-left:auto;display:flex;align-items:center;gap:10px;font:400 13px var(--ui);color:#555}
.mast__mid .t{font:300 24px var(--ui);color:#333}
.mast__issue{margin-left:56px;text-align:center;font:400 12.5px var(--ui);color:#666;line-height:1.6}
.mast__issue b{display:block;font:700 14px var(--head);color:#232325;letter-spacing:.04em;text-transform:uppercase}
.mast__cta{background:#f1f1f1;align-self:stretch;margin:10px 0;padding:14px 38px;display:flex;flex-direction:column;align-items:center;justify-content:center;gap:10px;font:400 14px var(--ui);color:#333}
.pill{display:inline-flex;align-items:center;gap:8px;border-radius:30px;padding:9px 20px;font:500 15px var(--ui);cursor:pointer;white-space:nowrap}
.pill--yellow{background:#fff200;border:2px solid #000;color:#000}.pill--yellow:hover{background:#ffe600}
.pill--dark{background:#000;color:#fff}.pill--dark:hover{background:#333}
.pill--outline{border:2px solid #000;color:#000;justify-content:center}
.pill .heart{display:inline-grid;place-items:center;width:22px;height:22px;border:2px solid #000;border-radius:50%;font-size:11px}
/* --- black section nav --- */
.nav{background:#000;position:sticky;top:0;z-index:20}
.nav ul{display:flex;list-style:none;margin:0 auto;max-width:1320px;padding:0 15px;height:60px;align-items:stretch;overflow-x:auto;scrollbar-width:none}.nav li{flex:none}
.nav li:first-child a{padding-left:0}
.nav li a{display:flex;align-items:center;height:100%;padding:0 13px;color:#fff;font:500 14px var(--head);text-transform:uppercase;letter-spacing:.07em;border-bottom:5px solid transparent;border-top:5px solid transparent}
.nav li a:hover,.nav li a.on{border-bottom-color:var(--c)}
.nav .nav__home{margin-left:auto;font:400 13px var(--ui);letter-spacing:.02em;text-transform:none;color:#bbb}
.subnav{color:#fff}.subnav ul{display:flex;flex-wrap:wrap;list-style:none;margin:0 auto;padding:0 15px;gap:0 26px}
.subnav a{display:block;padding:7px 0;font:500 14px var(--ui);letter-spacing:.03em}.subnav a:hover,.subnav a.on{text-decoration:underline;text-underline-offset:4px}
/* --- badges, dates, image blocks --- */
.card__badges{display:flex;gap:6px;flex-wrap:wrap;margin:14px 0 10px}
.badge{display:inline-block;border-radius:5px;padding:6px;font:500 12.5px var(--head);line-height:1;color:#fff;text-transform:uppercase;white-space:nowrap}
.badge--dossier{background:#1e2a44;padding:0 6px 0 0;display:inline-flex;align-items:center;text-transform:none}
.badge--dossier b{background:#2b3a5c;text-transform:uppercase;padding:6px;border-radius:5px 0 0 5px;margin-right:6px}
.badge--opinion{background:#232325}
.date{font:400 12.5px var(--ui);color:var(--grey2);margin:8px 0 0}
.vis{position:relative;overflow:hidden;background:linear-gradient(135deg,#232325 0%,#3a3a40 45%,var(--c) 160%);aspect-ratio:3/2}
.vis img{position:absolute;inset:0;width:100%;height:100%;object-fit:cover;transition:transform .4s}
a:hover>.vis img{transform:scale(1.03)}
.vis__glyph{position:absolute;right:6%;bottom:-.12em;font:900 clamp(40px,9vw,140px)/1 var(--head);color:rgba(255,255,255,.1);letter-spacing:-.04em}
.vis__name{position:absolute;left:14px;bottom:12px;font:700 11px var(--ui);color:#fff;text-transform:uppercase;letter-spacing:.14em;border-left:4px solid var(--red);padding-left:8px}
.vis:not(.vis--none) .vis__name,.vis:not(.vis--none) .vis__glyph{display:none}
/* --- hero row --- */
.hero-row{display:grid;grid-template-columns:minmax(0,1fr) 300px;gap:30px;padding-top:16px;border-top:1px solid #e3e3e3;margin-top:16px}
.hero{display:grid;grid-template-columns:66% 34%;background:#2d2d2d;min-height:420px;color:#fff}
.hero__img .vis{height:100%;aspect-ratio:auto;min-height:420px}
.hero__panel{position:relative;overflow:hidden;background:#2d2d2d}
.hero__panel::before{content:"";position:absolute;inset:-40px;background:var(--bg,none) center/cover;filter:blur(30px);opacity:.55}
.hero__panel::after{content:"";position:absolute;inset:0;background:linear-gradient(180deg,rgba(30,30,32,.55),rgba(30,30,32,.92))}
.hero__panelInner{position:relative;z-index:1;padding:14px 22px 22px}
.hero__sup{font:300 17px var(--head);color:#e6e6e6;margin:0 0 10px}
.hero__title{font:800 34px/1.3 var(--head);margin:0 0 14px;letter-spacing:-.005em}.hero__title a:hover{text-decoration:underline;text-decoration-thickness:2px}
.hero__lead{font:300 16px/1.6 var(--head);color:#eee;margin:0;display:-webkit-box;-webkit-line-clamp:6;-webkit-box-orient:vertical;overflow:hidden}
.trio{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:30px;margin-top:32px}
.card__sup{font:italic 300 15px var(--serif);color:var(--grey);margin:0 0 6px}
.card__title{font:800 21px/1.32 var(--head);color:#000;margin:0;letter-spacing:-.003em}
.card__title--slab{font-family:var(--slab);font-weight:700;letter-spacing:0}
.card__title a:hover,.row__title a:hover{color:var(--c,#5A79A0)}
.card--lg .card__title{font-size:30px;line-height:1.25}
.card--lg .vis--none{aspect-ratio:16/7}
.card__lead{font:300 16.5px/1.55 var(--head);color:var(--ink2);margin:10px 0 0}
/* --- sidebar --- */
.adlabel{background:#ddd;color:#666;text-align:center;font:600 12px var(--serif);text-transform:uppercase;letter-spacing:.04em;padding:7px}
.numbox{background:#fdeeee;padding:26px 22px 24px;text-align:center}
.numbox__value{font:900 64px/1 var(--head);color:#1d1a4a;letter-spacing:-.03em}
.numbox p{font:500 16px/1.45 var(--head);color:#1d1a4a;margin:14px 0 18px}
.essentials{border-top:4px solid var(--red);margin-top:30px;background:#fff;padding:2px 0}
.essentials h2{font:400 22px/1.2 var(--ui);color:#111;margin:14px 14px 10px}.essentials h2 span{font-weight:700;color:var(--red)}
.brief{display:flex;gap:10px;padding:12px 14px;border-top:1px solid #eee;font:600 15px/1.35 var(--head);color:#111}
.brief small{display:block;font:700 10.5px var(--ui);text-transform:uppercase;letter-spacing:.08em;margin-bottom:3px}
.brief__dot{flex:none;width:8px;height:8px;margin-top:4px}.brief:hover{background:#fafafa}
/* --- dossier band --- */
.band{background:#000;color:#fff;margin-top:50px;padding:28px 0 34px}
.band__title{font:700 22px var(--ui);text-transform:uppercase;margin:0 0 20px;letter-spacing:.01em}
.band__grid{display:grid;grid-template-columns:1fr 1fr;gap:30px}
.dcard{display:grid;grid-template-columns:42% 1fr;gap:20px;border-top:1px solid #4f4a4a;padding-top:18px}
.dcard__body h3{font:800 22px/1.3 var(--head);margin:0 0 10px}.dcard__body h3 a:hover{text-decoration:underline}
.dcard__body p{font:300 15px/1.55 var(--head);color:#d4d4d4;margin:0;display:-webkit-box;-webkit-line-clamp:5;-webkit-box-orient:vertical;overflow:hidden}
.dcard .card__badges{margin-top:0}
.status{display:inline-block;background:#555;color:#fff;font:700 10.5px var(--ui);text-transform:uppercase;letter-spacing:.08em;padding:4px 7px;border-radius:3px;margin-right:8px;vertical-align:1px}
.status--new{background:var(--red)}
/* --- quote --- */
.quote{text-align:center;padding:56px 15px 40px;max-width:900px}
.quote__label{display:inline-block;font:700 12px var(--ui);text-transform:uppercase;letter-spacing:.14em;color:var(--red);margin-bottom:16px}
.quote blockquote{margin:0;font:italic 500 30px/1.4 var(--slab);color:#111}
.quote blockquote::before{content:"«\00a0";color:var(--red);font-style:normal;font-weight:800}
.quote blockquote::after{content:"\00a0»";color:var(--red);font-style:normal;font-weight:800}
.quote__who{font:400 14px var(--ui);color:#666;margin-top:16px}.quote__who a{text-decoration:underline}
/* --- section blocks --- */
.secblock{margin-top:44px}
.sechead{font:700 24px var(--ui);text-transform:uppercase;color:var(--ink2);margin:0 0 18px;padding-bottom:12px;border-bottom:1px solid var(--rule);position:relative}
.sechead::after{content:"";position:absolute;left:0;bottom:-1px;width:60px;height:4px;background:var(--c,var(--red))}
.sechead a::after{content:" ›";font-weight:400;color:#999}
.secgrid{display:grid;grid-template-columns:minmax(0,7fr) minmax(0,5fr);gap:30px}
.seclist{display:flex;flex-direction:column}
.row{display:grid;grid-template-columns:150px 1fr;gap:16px;padding:16px 0;border-top:1px solid var(--rule)}
.row:first-child{border-top:0;padding-top:0}
.row .card__badges{margin:0 0 6px}
.row__title{font:700 17.5px/1.33 var(--head);margin:0;color:#000}
.row__thumb .vis{aspect-ratio:3/2}
.row .vis__glyph{font-size:44px}.row .vis__name{display:none}
/* --- article page --- */
.artgrid{display:grid;grid-template-columns:minmax(0,1fr) minmax(0,740px) 300px;gap:30px;padding-top:34px}
.artgrid::before{content:""}
.art__kicker{font:300 22px var(--head);color:#555;margin:6px 0 14px}
.art__title{font:800 46px/1.18 var(--head);color:#000;margin:0 0 30px;letter-spacing:-.01em}
.art__title--slab{font-family:var(--slab);font-weight:700}
.art__fig{margin:0}.vis--art{aspect-ratio:3/2}
.art__fig figcaption{font:400 14px/1.45 var(--head);color:var(--ink2);margin-top:10px}
.credit{display:block;font:500 12px var(--head);text-transform:uppercase;color:var(--grey2);margin-bottom:5px;letter-spacing:.02em}
.byline{display:flex;gap:12px;align-items:center;border-top:1px solid var(--rule);border-bottom:1px solid var(--rule);padding:14px 0;margin:24px 0 26px;font:400 13px var(--ui);color:#777}
.byline b{display:block;font:700 15px var(--head);color:#000}.byline span{display:block}
.byline__logo{flex:none;width:46px;height:46px;border-radius:50%;background:var(--red);color:#fff;display:grid;place-items:center;font:900 16px var(--head)}
.art p{font:400 18px/1.72 var(--serif);color:var(--text);margin:0 0 22px}
.art .art__lead{font-weight:700;font-size:18.5px}
.why{background:#fff;border-left:5px solid var(--c);padding:18px 22px;margin:30px 0}
.why p{margin:0!important;font-size:17px!important}
.why__label{font:700 12px var(--ui);text-transform:uppercase;letter-spacing:.12em;color:var(--c);margin-bottom:8px}
.facts{margin:30px 0}.facts ol{list-style:none;counter-reset:f;margin:0;padding:0}
.facts li{counter-increment:f;position:relative;padding:12px 0 12px 46px;border-top:1px solid var(--rule);font:500 16px/1.5 var(--head)}
.facts li::before{content:counter(f);position:absolute;left:0;top:10px;width:30px;height:30px;background:var(--c);color:#fff;display:grid;place-items:center;font:800 14px var(--head);border-radius:4px}
.srcbox{display:flex;justify-content:space-between;align-items:center;gap:20px;background:#efefef;padding:20px 22px;margin:34px 0;font:400 15px/1.6 var(--head)}
.srcbox a:not(.pill){text-decoration:underline;color:#444;font-size:14px}
.related{margin-top:50px}.related .trio{margin-top:0}
.timeline{list-style:none;margin:0;padding:0;border-left:3px solid var(--c);margin-left:8px}
.timeline li{position:relative;padding:0 0 22px 26px}
.timeline li::before{content:"";position:absolute;left:-9px;top:4px;width:15px;height:15px;border-radius:50%;background:#fff;border:3px solid var(--c)}
.timeline time{font:800 15px var(--head);text-transform:uppercase;letter-spacing:.04em;color:var(--c)}
.timeline p{margin:4px 0 0!important;font-size:16.5px!important}.timeline a{font:600 13px var(--ui);color:var(--c);white-space:nowrap}
.aside{position:relative}
.promo{position:sticky;top:84px;border:1px solid #d9d9d9;background:#fff;padding:22px}
.promo__logo{display:inline-flex;flex-direction:column;background:var(--red);color:#fff;padding:7px 8px;line-height:.95;margin-bottom:12px}
.promo__logo span{font:900 9px var(--head);text-transform:uppercase}.promo__logo b{font:900 26px var(--head)}
.promo h3{font:400 22px/1.25 var(--slab);margin:0 0 12px}
.mini{display:grid;grid-template-columns:96px 1fr;gap:12px;padding:12px 0;border-top:1px solid #eee;font:600 14.5px/1.35 var(--head)}
.mini small{display:block;font:700 10px var(--ui);text-transform:uppercase;letter-spacing:.08em;margin-bottom:3px}
.mini .vis__glyph{font-size:30px}.mini .vis__name{display:none}
.mini:hover span{text-decoration:underline}.promo .pill{width:100%;margin-top:14px}
/* --- footer --- */
footer{background:#000;color:#cfcfcf;margin-top:70px;font:400 13.5px/1.6 var(--ui)}
footer .wrap{padding:40px 15px 30px}
.foot__top{display:flex;gap:24px;align-items:flex-start;margin-bottom:26px}
.foot__top h4{font:700 15px var(--ui);text-transform:uppercase;color:#fff;margin:6px 0 4px;letter-spacing:.06em}
footer ol{columns:3;column-gap:40px;margin:0;padding-left:20px}
footer li{break-inside:avoid;margin-bottom:6px}footer li a{color:#eee}footer li a:hover{text-decoration:underline}
.colophon{border-top:1px solid #333;margin-top:26px;padding-top:16px;color:#888;font-size:12.5px}
@media (max-width:1100px){.artgrid{grid-template-columns:minmax(0,1fr) 300px}.artgrid::before{display:none}.mast__issue{display:none}}
.subnav__back{opacity:.85}
html,body{overflow-x:hidden}
@media (max-width:900px){
.hero-row,.artgrid,.secgrid,.band__grid{grid-template-columns:minmax(0,1fr)}
.hero{grid-template-columns:minmax(0,1fr)}.hero__img .vis{min-height:0;aspect-ratio:16/10}
.trio{grid-template-columns:repeat(2,minmax(0,1fr))}
.mast__cta,.mast__mid,.mast__issue{display:none}
.nav ul{overflow-x:auto;scrollbar-width:none}.nav ul::-webkit-scrollbar{display:none}.nav li a{white-space:nowrap}
.art__title{font-size:34px}footer ol{columns:1}.aside .promo{position:static}}
/* ================= phone app (La Presse app look) ================= */
.m-only{display:none}
.appbar{position:sticky;top:0;z-index:30;background:var(--red);color:#fff;align-items:center;justify-content:space-between;padding:calc(env(safe-area-inset-top) + 9px) 14px 9px}
.appbar__logo{font:900 19px/1 var(--head);letter-spacing:.01em;text-transform:uppercase}
.appbar__heart{width:30px;height:30px;border-radius:50%;background:#fff200;color:#000;display:grid;place-items:center;font-size:15px;box-shadow:inset 0 0 0 2px #000}
.appbar__me{display:grid;place-items:center;width:30px;height:30px;color:#fff}
.mfeed{padding:0 12px}
.mhead{text-align:center;font:900 22px/1.15 var(--head);text-transform:uppercase;margin:22px 0 14px;color:#111;scroll-margin-top:70px}
.mhead span{display:block;font:400 13.5px var(--ui);text-transform:none;color:#555;margin-top:5px}
.mcard{display:block;background:#fff;border-radius:10px;overflow:hidden;box-shadow:0 1px 3px rgba(0,0,0,.12),0 6px 16px rgba(0,0,0,.05);margin-bottom:14px;color:#111}
.mcard__img{display:block;position:relative}.mcard__img .vis{aspect-ratio:16/10}
.mbadge{position:absolute;left:10px;bottom:10px;z-index:2}
.mcard__body{padding:12px 14px 12px}
.mcard__body>.badge{margin-bottom:8px}
.mcard__sup{font:500 13.5px var(--head);color:#232325;margin:0 0 4px}
.mcard__title{font:800 21px/1.25 var(--head);margin:0 0 8px;color:#000}
.mcard__title--slab{font-family:var(--slab);font-weight:700}
.mcard__lead{font:400 14px/1.45 var(--head);color:#333;margin:0 0 10px;display:-webkit-box;-webkit-line-clamp:3;-webkit-box-orient:vertical;overflow:hidden}
.mcard__foot{display:flex;align-items:center;gap:6px;font:400 12.5px var(--ui);color:#555}
.mdot{display:inline-block;width:10px;height:10px;border-radius:50%;background:#1eaefd;flex:none}
.acts{margin-left:auto;display:flex;gap:14px}
.acts button{background:none;border:0;padding:2px;margin:0;color:inherit;cursor:pointer;-webkit-tap-highlight-color:transparent}
.bm.on svg{fill:currentColor}
/* whole card is tappable: the headline link is stretched over the card; bookmark/share stay on top */
.mcard,.card,.row,.dcard{position:relative}
.mcard__title a::after,.card__title a::after,.row__title a::after,.dcard h3 a::after{content:"";position:absolute;inset:0;z-index:1}
.acts{position:relative;z-index:2}
.mbadge{pointer-events:none}.mcard--row .mbadge{position:static;display:inline-block}
.mcard--row{display:grid;grid-template-columns:minmax(0,1fr) 104px;gap:12px;padding:12px}
.mcard--row .mcard__body{padding:0}.mcard--row .mcard__img .vis{aspect-ratio:1;border-radius:6px}
.mcard--row .mcard__title{font-size:17px;line-height:1.3}
.mcard--row .vis__name{display:none}.mcard--row .vis__glyph{font-size:36px}
.mcard--dossier{background:#1b1b1d;color:#fff}
.mcard--dossier .mcard__title,.mcard--dossier .mcard__sup{color:#fff}.mcard--dossier .mcard__lead{color:#ccc}.mcard--dossier .mcard__foot{color:#aaa}
.mquote{padding:22px 18px;text-align:center}.mquote blockquote{margin:0;font:italic 500 20px/1.4 var(--slab)}
.mquote blockquote::before{content:"«\00a0";color:var(--red);font-style:normal}.mquote blockquote::after{content:"\00a0»";color:var(--red);font-style:normal}
.mnum{padding:22px 18px;text-align:center;background:#fdeeee}.mnum .numbox__value{font-size:54px}.mnum p{font:500 15px/1.45 var(--head);color:#1d1a4a;margin:10px 0 0}
.mchips{display:flex;gap:8px;overflow-x:auto;margin:0 -12px 6px;padding:2px 12px;scrollbar-width:none}.mchips::-webkit-scrollbar{display:none}
.mchips a{flex:none;border-radius:16px;padding:7px 13px;font:500 13px var(--ui);color:#fff;background:var(--c)}
.msec{display:flex;align-items:center;gap:8px;font:700 18px var(--ui);text-transform:uppercase;margin:26px 2px 12px;color:#232325;scroll-margin-top:70px}
.msec::before{content:"";width:10px;height:10px;background:var(--c)}
.msources{padding:14px 16px;font:400 13px/1.5 var(--ui)}.msources summary{font:700 14px var(--ui);cursor:pointer}
.msources ol{padding-left:18px;margin:10px 0 0}.msources li{margin-bottom:6px}.msources a{text-decoration:underline}
.mcolophon{font:400 11.5px/1.5 var(--ui);color:#888;text-align:center;margin:8px 0 24px}
.tabbar{position:fixed;left:12px;right:12px;bottom:calc(10px + env(safe-area-inset-bottom));z-index:40;justify-content:space-around;background:rgba(246,246,246,.8);-webkit-backdrop-filter:blur(18px) saturate(1.8);backdrop-filter:blur(18px) saturate(1.8);border-radius:30px;box-shadow:0 6px 24px rgba(0,0,0,.18);padding:6px;border:1px solid rgba(255,255,255,.7)}
.tabbar a{display:flex;flex-direction:column;align-items:center;gap:2px;font:500 10px var(--ui);color:#333;padding:5px 6px;border-radius:22px;flex:1}
.tabbar a.on{background:rgba(0,0,0,.08);color:#000;font-weight:700}
.scrim{position:fixed;inset:0;background:rgba(0,0,0,.4);z-index:45;opacity:0;pointer-events:none;transition:opacity .5s cubic-bezier(.32,.72,0,1)}
#stage{display:contents}
a,button{-webkit-tap-highlight-color:transparent}
.msheet__bar{display:none}
@media (max-width:700px){
.d-only,.util,.mast,.nav,footer{display:none!important}
.m-only{display:block}.appbar.m-only,.tabbar.m-only{display:flex}
body{background:#f1f1f1;transition:background-color .5s}
#stage{display:block;background:#f1f1f1;min-height:100vh;padding-bottom:calc(84px + env(safe-area-inset-bottom));transition:transform .5s cubic-bezier(.32,.72,0,1),border-radius .5s cubic-bezier(.32,.72,0,1);will-change:transform}
body.sheet{overflow:hidden;background:#000}body.sheet .scrim{opacity:1;pointer-events:auto}
body.sheet #stage{transform:translate3d(0,calc((env(safe-area-inset-top) + 10px) * var(--k,1)),0) scale(calc(1 - .07 * var(--k,1)));border-radius:14px}
.mcard{transition:transform .35s cubic-bezier(.32,.72,0,1)}.mcard:active{transform:scale(.97)}
.page{position:fixed;left:0;right:0;bottom:0;top:calc(env(safe-area-inset-top) + 30px);z-index:50;background:#fff;border-radius:12px 12px 0 0;overflow-y:auto;-webkit-overflow-scrolling:touch;overscroll-behavior:contain;transform:translate3d(0,102%,0);transition:transform .5s cubic-bezier(.32,.72,0,1);will-change:transform;box-shadow:0 -4px 24px rgba(0,0,0,.18)}
.page.is-open{transform:none}
.page .subnav,.page .aside,.page .byline,.page .related,.art>.card__badges{display:none!important}
.artgrid{display:block;padding:0;max-width:none}
.art{display:flex;flex-direction:column;padding:0 16px calc(110px + env(safe-area-inset-bottom))}
.msheet__bar.m-only{order:-2;position:sticky;top:0;z-index:5;margin:0 -16px;display:flex;align-items:center;color:#fff;padding:16px 16px 11px;font:700 12.5px var(--ui);text-transform:uppercase;letter-spacing:.06em}
.msheet__grab{position:absolute;left:50%;top:0;width:90px;height:16px;margin-left:-45px}
.msheet__grab::before{content:"";position:absolute;left:25px;right:25px;top:6px;height:4px;border-radius:3px;background:rgba(255,255,255,.75)}
.art__fig{order:-1;margin:0 -16px;position:relative}.vis--art{aspect-ratio:16/10}
.art__fig figcaption{position:absolute;left:0;right:0;bottom:0;margin:0;padding:26px 16px 8px;background:linear-gradient(transparent,rgba(0,0,0,.7));z-index:2}
.art__fig .credit{color:#eee;margin:0;font-size:11px}.art__fig .cap{display:none}
.art__kicker{font:400 15px var(--head);color:#232325;margin:20px 0 8px}
.art__title{font:800 29px/1.18 var(--head);margin:0 0 12px}
.mmeta.m-only{display:flex;justify-content:space-between;align-items:center;font:400 13px var(--ui);color:#555;margin-bottom:14px}
.mmeta span{display:flex;align-items:center;gap:6px}
.msrc{background:#e9e9e9;font:400 12.5px var(--head);padding:8px 10px;margin-bottom:18px;color:#232325}
.art p{font-size:17px;line-height:1.62;-webkit-hyphens:auto;hyphens:auto}
.art .art__lead{font-family:var(--head);font-weight:700;font-size:17px;line-height:1.5}
.why,.facts{margin:22px 0}.srcbox{flex-direction:column;align-items:flex-start;margin:26px 0}
.timeline p{font-size:16px!important}.sechead{font-size:19px}}
/* past editions page */
.archive .m-only{display:block}.archive .appbar.m-only,.archive .tabbar.m-only{display:flex}
.archive{padding-bottom:110px}.archive .tabbar{max-width:616px;margin:0 auto}
.archive main{max-width:640px;margin:0 auto;padding:0 12px 40px}
"""

JS = r"""
(function(){
  var home=document.getElementById('home'),stage=document.getElementById('stage'),scrim=document.querySelector('.scrim');
  var body=document.body,mq=matchMedia('(max-width:700px)');
  var KEY='qia-saved',ed=body.dataset.edition||location.pathname,depth=0,openPage=null,MS=520;
  function esc(s){return String(s||'').replace(/[&<>"]/g,function(c){return{'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]})}
  function saved(){try{return JSON.parse(localStorage.getItem(KEY))||[]}catch(x){return[]}}
  function paintBm(){var keys=saved().map(function(x){return x.key});
    document.querySelectorAll('.bm').forEach(function(b){b.classList.toggle('on',keys.indexOf(ed+'#'+b.dataset.id)>=0)})}
  function renderSaved(){var box=document.getElementById('savedList');if(!box)return;var l=saved().slice().reverse();
    box.innerHTML=l.length?'':'<p>No saved stories yet. Tap the bookmark icon on any story to keep it here.</p>';
    l.forEach(function(x){var a=document.createElement('a');a.className='mcard mcard--row';
      a.href=x.key.split('#')[0]===ed?'#'+x.id:x.key;
      a.innerHTML='<div class="mcard__body"><p class="mcard__sup" style="color:'+esc(x.color)+'">'+esc(x.sec)+'</p><h3 class="mcard__title">'+esc(x.title)+'</h3><div class="mcard__foot"><i class="mdot"></i>'+esc(x.date)+'</div></div>'+
        (x.img?'<div class="mcard__img"><div class="vis"><img src="'+esc(x.img)+'" alt="" referrerpolicy="no-referrer"></div></div>':'');
      box.appendChild(a)})}

  // ---- iOS-style sheet: slides up over the feed, which recedes behind it
  function showSheet(p){
    clearTimeout(p._t);p._t=null;p.hidden=false;p.scrollTop=0;
    stage.style.transformOrigin='50% '+window.scrollY+'px';
    p.getBoundingClientRect();                       // start the transition from off-screen
    body.classList.add('sheet');p.classList.add('is-open');openPage=p;
  }
  function hideSheet(p){
    p.classList.remove('is-open');body.classList.remove('sheet');if(openPage===p)openPage=null;
    clearTimeout(p._t);p._t=setTimeout(function(){p._t=null;if(!p.classList.contains('is-open'))p.hidden=true},MS);
  }
  function close(){
    if(openPage&&mq.matches)hideSheet(openPage);
    if(depth>0){history.back()}else{history.replaceState(null,'',location.pathname+location.search);route()}
  }

  document.addEventListener('click',function(ev){
    var b=ev.target.closest('.bm');
    if(b){ev.preventDefault();var k=ed+'#'+b.dataset.id,l=saved(),i=-1;
      l.forEach(function(x,j){if(x.key===k)i=j});
      if(i>=0)l.splice(i,1);else l.push({key:k,id:b.dataset.id,title:b.dataset.title,sec:b.dataset.sec,color:b.dataset.color,img:b.dataset.img,date:body.dataset.date});
      localStorage.setItem(KEY,JSON.stringify(l));paintBm();renderSaved();
      if(navigator.vibrate)navigator.vibrate(8);return}
    var s=ev.target.closest('.sh');
    if(s){ev.preventDefault();var d={title:s.dataset.title,url:s.dataset.url};
      if(navigator.share){navigator.share(d).catch(function(){})}else if(navigator.clipboard){navigator.clipboard.writeText(d.url)}return}
    if(ev.target.closest('[data-close]')||ev.target===scrim){ev.preventDefault();close()}
  });

  // ---- drag the sheet down to dismiss; it follows the finger, then closes or springs back
  var drag=null;
  function setT(v){if(!openPage)return;openPage.style.transition=v;stage.style.transition=v;scrim.style.transition=v}
  document.addEventListener('touchstart',function(e){
    if(!mq.matches||!openPage||e.touches.length>1)return;
    var p=e.target.closest('.page');if(p!==openPage)return;
    drag={y0:e.touches[0].clientY,x0:e.touches[0].clientX,t:Date.now(),y:e.touches[0].clientY,v:0,dy:0,on:false,top:p.scrollTop<=0};
  },{passive:true});
  document.addEventListener('touchmove',function(e){
    if(!drag)return;
    var y=e.touches[0].clientY,dy=y-drag.y0,dx=e.touches[0].clientX-drag.x0,now=Date.now();
    if(!drag.on){
      if(!drag.top||dy<0||Math.abs(dx)>Math.abs(dy)+4){drag=null;return}
      if(e.cancelable)e.preventDefault();             // keep iOS from rubber-banding the content
      if(dy<6)return;
      drag.on=true;setT('none');
    }
    if(e.cancelable)e.preventDefault();
    drag.v=(y-drag.y)/Math.max(1,now-drag.t);drag.y=y;drag.t=now;
    drag.dy=Math.max(0,dy);
    var k=1-Math.min(1,drag.dy/(window.innerHeight*.85));
    openPage.style.transform='translate3d(0,'+drag.dy+'px,0)';
    scrim.style.opacity=String(k);stage.style.setProperty('--k',k);
  },{passive:false});
  function endDrag(){
    if(!drag)return;var d=drag;drag=null;if(!d.on||!openPage)return;
    var p=openPage;setT('');p.style.transform='';scrim.style.opacity='';stage.style.removeProperty('--k');
    if(d.dy>window.innerHeight*.25||(d.v>1&&d.dy>40))close();
  }
  document.addEventListener('touchend',endDrag,{passive:true});
  document.addEventListener('touchcancel',endDrag,{passive:true});
  scrim.addEventListener('touchmove',function(e){if(e.cancelable)e.preventDefault()},{passive:false});

  function route(){
    var id=decodeURIComponent(location.hash.slice(1)),t=id&&document.getElementById(id);
    var page=t&&t.classList.contains('page')?t:null,mobile=mq.matches;
    if(mobile){
      document.querySelectorAll('.page').forEach(function(p){
        if(p===page)return;
        if(p.classList.contains('is-open'))hideSheet(p);else if(!p._t)p.hidden=true});
      if(page&&!page.classList.contains('is-open'))showSheet(page);
      home.hidden=false;
    }else{
      document.querySelectorAll('.page').forEach(function(p){p.hidden=p!==page;p.classList.remove('is-open')});
      body.classList.remove('sheet');openPage=null;home.hidden=!!page;
    }
    if(page&&page.id==='saved')renderSaved();
    var cur=page?page.dataset.section||'':(id.indexOf('sec-')===0?id.slice(4):'');
    document.querySelectorAll('.nav a[data-s]').forEach(function(a){a.classList.toggle('on',a.dataset.s===cur)});
    var tab=page?(page.id==='saved'?'saved':''):(id==='m-dossiers'?'dossiers':(id==='m-sections'||id.indexOf('m-sec-')===0)?'sections':'home');
    document.querySelectorAll('.tabbar a').forEach(function(a){a.classList.toggle('on',a.dataset.tab===tab)});
    if(page){if(!mobile)window.scrollTo(0,0)}
    else if(id==='top'){window.scrollTo({top:0,behavior:mobile?'smooth':'auto'})}
    else if(t){t.scrollIntoView({behavior:mobile?'smooth':'auto'})}
    else if(!mobile){window.scrollTo(0,0)}
  }
  if('scrollRestoration' in history){history.scrollRestoration='manual'}
  window.addEventListener('hashchange',function(){var id=location.hash.slice(1),t=id&&document.getElementById(id);
    depth=t&&t.classList.contains('page')?depth+1:0;route()});
  if(mq.addEventListener)mq.addEventListener('change',route);
  paintBm();route();
})();
"""


SAVED_PAGE = ('<div class="page" id="saved" hidden><div class="wrap artgrid"><article class="art">'
              '<div class="msheet__bar m-only" style="background:#232325"><a class="msheet__grab" href="#top" data-close aria-label="Close"></a><span>Saved stories</span></div>'
              '<h1 class="art__title" style="margin-top:18px">Saved stories</h1><div id="savedList"></div></article></div></div>')


def appbar(lead_id_item=None, home="#top"):
    lead = f"#{e(lead_id_item['id'])}" if lead_id_item else "/"
    return (f'<header class="appbar m-only"><a class="appbar__heart" href="{lead}" aria-label="Lead story">★</a>'
            f'<a class="appbar__logo" href="{home}">Le Quotidien IA</a>'
            f'<a class="appbar__me" href="/archive.html" aria-label="Past editions">{icon("calendar", 24)}</a></header>')


def tabbar(prefix="", active=""):
    tabs = [("home", "#top" if not prefix else "/", "home", "Front page"),
            ("dossiers", prefix + "#m-dossiers", "stack", "Dossiers"),
            ("saved", prefix + "#saved", "bookmark", "Saved"),
            ("sections", prefix + "#m-sections", "grid", "Sections"),
            ("archive", "/archive.html", "calendar", "Archive")]
    return '<nav class="tabbar m-only">' + "".join(
        f'<a href="{href}" data-tab="{t}"{" class=on" if t == active else ""}>{icon(ic, 22)}<span>{label}</span></a>'
        for t, href, ic, label in tabs) + "</nav>"


# ---------------------------------------------------------------- website (Cloudflare Pages)
SITE = ROOT / "site"
FONTS = ('<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>'
         '<link href="https://fonts.googleapis.com/css2?family=Figtree:ital,wght@0,300;0,400;0,500;0,600;0,700;0,800;0,900;1,400&family=Rubik:wght@300;400;500;700&family=Roboto+Slab:wght@400;500;700;800&family=Roboto+Serif:ital,opsz,wght@0,8..144,400;0,8..144,700;1,8..144,300;1,8..144,500&display=swap" rel="stylesheet">')
APP_META = ('<meta name="theme-color" content="#e12929"><meta name="apple-mobile-web-app-capable" content="yes"><meta name="mobile-web-app-capable" content="yes">'
            '<meta name="apple-mobile-web-app-status-bar-style" content="black-translucent"><meta name="apple-mobile-web-app-title" content="Quotidien IA">'
            '<link rel="manifest" href="/manifest.webmanifest"><link rel="apple-touch-icon" href="/icons/apple-touch-icon.png">'
            '<link rel="icon" type="image/png" sizes="192x192" href="/icons/icon-192.png"><meta name="robots" content="noindex,nofollow">')


def make_icons(folder):
    """Red La Presse-style square with the IA. wordmark (needs Pillow; skipped if missing)."""
    try:
        from PIL import Image, ImageDraw, ImageFont
    except ImportError:
        print("Pillow not installed: skipping app icons")
        return
    folder.mkdir(parents=True, exist_ok=True)
    fontfile = next((f for f in (r"C:\Windows\Fonts\ariblk.ttf", r"C:\Windows\Fonts\seguibl.ttf", r"C:\Windows\Fonts\arialbd.ttf") if Path(f).exists()), None)
    for name, n in (("apple-touch-icon.png", 180), ("icon-192.png", 192), ("icon-512.png", 512)):
        im = Image.new("RGB", (n, n), "#e12929")
        d = ImageDraw.Draw(im)
        small = ImageFont.truetype(fontfile, int(n * 0.105)) if fontfile else ImageFont.load_default()
        big = ImageFont.truetype(fontfile, int(n * 0.47)) if fontfile else ImageFont.load_default()
        d.text((n * 0.13, n * 0.17), "LE QUOTIDIEN", font=small, fill="white")
        d.text((n * 0.1, n * 0.33), "IA.", font=big, fill="white")
        im.save(folder / name)


def edition_card(json_file, cache):
    data = json.loads(json_file.read_text(encoding="utf-8"))
    stories = data.get("stories") or []
    if not stories:
        return ""
    lead = dict(next((s for s in stories if s.get("lead")), stories[0]))
    if not usable((lead.get("image") or {}).get("url")):
        img = cache.get((lead.get("source") or {}).get("url", ""), "")
        lead["image"] = {"url": img} if usable(img) else None
    name, color, _ = sec(lead)
    href = f"/editions/{e(data.get('date'))}.html"
    return f'''<a class="mcard" href="{href}">
  <div class="mcard__img">{visual(lead)}<span class="badge mbadge" style="background:#232325">No. {e(data.get("issue"))}</span></div>
  <div class="mcard__body"><p class="mcard__sup">{e(data.get("date_long"))}</p>
  <h3 class="mcard__title">{e(lead.get("title"))}</h3>
  <div class="mcard__foot"><i class="mdot"></i>{len(stories)} stories · lead in {e(name)}</div></div>
</a>'''


def build_site():
    """Assemble the publishable site/ folder: newest edition as index, all editions, archive, app files."""
    eds = SITE / "editions"
    eds.mkdir(parents=True, exist_ok=True)
    for h in (ROOT / "editions").glob("*.html"):
        shutil.copyfile(h, eds / h.name)
    newest = sorted(eds.glob("*.html"))[-1]
    shutil.copyfile(newest, SITE / "index.html")

    cache = load_cache()
    cards = "".join(edition_card(j, cache) for j in sorted((ROOT / "editions").glob("*.json"), reverse=True))
    (SITE / "archive.html").write_text(f'''<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<title>Le Quotidien IA — Past editions</title>{APP_META}{FONTS}<style>{CSS}</style></head>
<body class="archive">{appbar(None, "/")}
<main><h2 class="mhead">Past editions<span>Every morning edition of Le Quotidien IA.</span></h2>{cards}</main>
{tabbar("/", "archive")}
</body></html>''', encoding="utf-8")

    if not (SITE / "icons" / "icon-512.png").exists():
        make_icons(SITE / "icons")
    (SITE / "manifest.webmanifest").write_text(json.dumps({
        "name": "Le Quotidien IA", "short_name": "Quotidien IA", "start_url": "/", "scope": "/",
        "display": "standalone", "background_color": "#e12929", "theme_color": "#e12929",
        "icons": [{"src": "/icons/icon-192.png", "sizes": "192x192", "type": "image/png"},
                  {"src": "/icons/icon-512.png", "sizes": "512x512", "type": "image/png", "purpose": "any maskable"}],
    }, indent=1), encoding="utf-8")
    # Cloudflare Pages headers: always fetch the latest HTML, keep it out of search engines
    (SITE / "_headers").write_text("/*\n  X-Robots-Tag: noindex, nofollow\n  Cache-Control: no-cache\n/icons/*\n  Cache-Control: public, max-age=604800\n", encoding="utf-8")
    (SITE / "robots.txt").write_text("User-agent: *\nDisallow: /\n", encoding="utf-8")
    print(f"Site updated: {SITE} (index = {newest.name})")


def render(json_path):
    json_path = Path(json_path).resolve()
    data = json.loads(json_path.read_text(encoding="utf-8"))
    stories = [s for s in data.get("stories", []) if s.get("section") in SECTIONS]
    dossiers = [d for d in data.get("dossiers", []) if d.get("section") in SECTIONS]

    cache = load_cache()
    for item in stories + dossiers:
        if "image" in item and item["image"] is None:   # explicitly "no image": use the typographic panel
            continue
        if not usable((item.get("image") or {}).get("url")):
            item.pop("image", None)
            url = (item.get("source") or {}).get("url") or next((t.get("url") for t in item.get("timeline", []) if t.get("url")), "")
            img = og_image(url, cache)
            if usable(img):
                item["image"] = {"url": img, "credit": ((item.get("source") or {}).get("name") or urllib.parse.urlparse(url).netloc).upper()}
    CACHE.parent.mkdir(exist_ok=True)
    CACHE.write_text(json.dumps(cache, indent=1), encoding="utf-8")

    wx = weather()
    lead = next((s for s in stories if s.get("lead")), stories[0])
    present = {i.get("section") for i in stories + dossiers if i is not lead}
    nav = "".join(f'<li><a href="#sec-{k}" data-s="{k}" style="--c:{c}">{e(n)}</a></li>' for k, (n, c, _) in SECTIONS.items() if k in present)
    pages = "".join(story_page(s, data, stories, dossiers).replace('class="page"', f'class="page" data-section="{e(s["section"])}"', 1) for s in stories)
    pages += "".join(dossier_page(d, data, stories, dossiers).replace('class="page"', f'class="page" data-section="{e(d["section"])}"', 1) for d in dossiers)
    sources = "".join(f'<li><a href="{e(x.get("url"))}" target="_blank" rel="noopener">{e(x.get("title"))}</a> — {e(x.get("outlet"))}</li>' for x in data.get("sources", []))
    wx_html = f'<span>Montréal</span><span style="font-size:22px">{e(wx[0])}</span><span class="t">{e(wx[1])}</span>' if wx else ""

    doc = f'''<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<title>Le Quotidien IA — {e(data.get("date_long"))}</title>
<meta name="theme-color" content="#e12929">
<meta name="apple-mobile-web-app-capable" content="yes"><meta name="mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
<meta name="apple-mobile-web-app-title" content="Quotidien IA">
<link rel="manifest" href="/manifest.webmanifest"><link rel="apple-touch-icon" href="/icons/apple-touch-icon.png">
<link rel="icon" type="image/png" sizes="192x192" href="/icons/icon-192.png">
<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Figtree:ital,wght@0,300;0,400;0,500;0,600;0,700;0,800;0,900;1,400&family=Rubik:wght@300;400;500;700&family=Roboto+Slab:wght@400;500;700;800&family=Roboto+Serif:ital,opsz,wght@0,8..144,400;0,8..144,700;1,8..144,300;1,8..144,500&display=swap" rel="stylesheet">
<style>{CSS}</style></head>
<body data-edition="/editions/{e(data.get("date"))}.html" data-date="{e(data.get("date_long"))}">
<div id="stage">
{appbar(lead)}
<div id="top" class="util"><ul><li><a href="#top">Today's edition</a></li><li><a href="#{e(lead["id"])}">Lead story</a></li><li><a href="#sources">Sources</a></li><li><a href="/archive.html">Past editions</a></li></ul></div>
<header class="mast"><div class="wrap">
  <a class="logo" href="#top"><span>Le Quotidien</span><b>IA.</b></a>
  <div class="mast__date">Le Quotidien IA, {e(data.get("date_long"))}</div>
  <div class="mast__mid">{wx_html}</div>
  <div class="mast__issue"><b>No. {e(data.get("issue"))}</b>{len(stories)} stories · {len(data.get("sources", []))} sources</div>
  <div class="mast__cta">Your morning AI briefing<a class="pill pill--yellow" href="#{e(lead["id"])}"><span class="heart">★</span>Read today's lead</a></div>
</div></header>
<nav class="nav"><ul>{nav}<li style="margin-left:auto"><a class="nav__home" href="#top">Front page</a></li></ul></nav>
<main>
<div id="home">{front(data, stories, dossiers, wx)}{mobile_feed(data, stories, dossiers)}</div>
</main>
</div>
<div id="sheets">{pages}{SAVED_PAGE}</div>
<footer id="sources"><div class="wrap">
  <div class="foot__top"><a class="logo" href="#top"><span>Le Quotidien</span><b>IA.</b></a><div><h4>Sources for this edition</h4>Every story links to its original source. Follow the links to verify.</div></div>
  <ol>{sources}</ol>
  <div class="colophon">Le Quotidien IA · No. {e(data.get("issue"))} · Compiled automatically by Claude on {e(data.get("date_long"))} at {e(data.get("generated_at"))} from public web sources. Summaries may contain errors. Layout inspired by La Presse; images belong to their respective sources.</div>
</div></footer>
{tabbar()}<div class="scrim"></div>
<script>{JS}</script>
</body></html>'''

    out = json_path.with_suffix(".html")
    out.write_text(doc, encoding="utf-8")
    shutil.copyfile(out, ROOT / "latest.html")
    build_site()
    missing = [i["id"] for i in stories + dossiers if not (i.get("image") or {}).get("url")]
    print(f"Wrote {out} ({len(stories)} stories, {len(dossiers)} dossiers; no image for: {', '.join(missing) or 'none'})")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    render(sys.argv[1])
