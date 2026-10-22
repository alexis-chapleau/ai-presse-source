"""Add full-paper reading time and citation metrics to papers_raw.json.

For each paper:
- OpenAlex (CC0, free): citations, field-weighted citation impact, citation percentile, reference count, PMC location.
- Europe PMC full-text XML (open-access subset): body word count, figures and tables -> full-paper reading time.
Reading time = body words / 150 wpm (careful scientific reading) + 1.5 min per figure or table,
rounded to the nearest 5 minutes. If no full text is available, a typical length for the article type is used.

Usage: python enrich.py   (rewrites papers_raw.json in place)
"""
import json
import re
import time
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
UA = {"User-Agent": "LeQuotidienMedical-demo/0.1 (mailto:quotidien-ia@users.noreply.github.com)"}
WPM = 150
TYPICAL_MIN = 30   # typical original investigation (~3,500 words + 4-5 exhibits)
JOURNALS = {}      # OpenAlex source id -> journal-level stats (cached per run)


def get(url, timeout=40):
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=timeout) as r:
        return r.read()


def openalex(doi):
    d = json.loads(get(f"https://api.openalex.org/works/doi:{doi}?mailto=quotidien-ia@users.noreply.github.com"))
    pmcid = ""
    for loc in d.get("locations") or []:
        m = re.search(r"/(PMC\d+)", loc.get("landing_page_url") or "")
        if m:
            pmcid = m.group(1)
            break
    pct = d.get("citation_normalized_percentile") or {}
    journal = {}
    src = ((d.get("primary_location") or {}).get("source") or {}).get("id")
    if src:
        sid = src.rsplit("/", 1)[-1]
        if sid not in JOURNALS:
            s = json.loads(get(f"https://api.openalex.org/sources/{sid}?mailto=quotidien-ia@users.noreply.github.com"))
            st = s.get("summary_stats") or {}
            JOURNALS[sid] = {"journal_2yr_mean_citedness": round(st.get("2yr_mean_citedness") or 0, 1),
                             "journal_h_index": st.get("h_index")}
        journal = JOURNALS[sid]
    return {
        **journal,
        "openalex_id": d.get("id"),
        "cited_by": d.get("cited_by_count") or 0,
        "fwci": d.get("fwci"),
        "citation_percentile": round(pct["value"] * 100) if pct.get("value") is not None else None,
        "top10": bool(pct.get("is_in_top_10_percent")),
        "references": d.get("referenced_works_count"),
        "pmcid": pmcid,
    }


def fulltext_stats(pmcid):
    xml = get(f"https://www.ebi.ac.uk/europepmc/webservices/rest/{pmcid}/fullTextXML").decode("utf-8", "ignore")
    body = re.search(r"<body[^>]*>(.*)</body>", xml, flags=re.S)
    if not body:
        return None
    b = body.group(1)
    figs = len(re.findall(r"<fig[\s>]", b))
    tables = len(re.findall(r"<table-wrap[\s>]", b))
    text = re.sub(r"<table-wrap.*?</table-wrap>", " ", b, flags=re.S)   # tables are counted separately
    text = re.sub(r"<[^>]+>", " ", text)
    return {"body_words": len(text.split()), "figures": figs, "tables": tables}


def main():
    path = HERE / "papers_raw.json"
    papers = json.loads(path.read_text(encoding="utf-8"))
    for p in papers:
        try:
            p["metrics"] = openalex(p["doi"])
        except Exception as ex:
            p["metrics"] = {"error": str(ex)}
        stats = None
        pmcid = p.get("pmcid") or p["metrics"].get("pmcid")
        if pmcid:
            try:
                stats = fulltext_stats(pmcid)
            except Exception:
                stats = None
        if stats and stats["body_words"] > 500:
            raw = stats["body_words"] / WPM + 1.5 * (stats["figures"] + stats["tables"])
            p["full_read"] = {**stats, "minutes": max(10, 5 * round(raw / 5)), "basis": "full text"}
        else:
            p["full_read"] = {"minutes": TYPICAL_MIN, "basis": "typical length for an original investigation"}
        p["metrics"]["fetched"] = time.strftime("%Y-%m-%d")
        print(p["doi"], "|", p["full_read"], "| cited", p["metrics"].get("cited_by"), "pct", p["metrics"].get("citation_percentile"))
        time.sleep(0.3)
    path.write_text(json.dumps(papers, indent=1, ensure_ascii=False), encoding="utf-8")


if __name__ == "__main__":
    main()
