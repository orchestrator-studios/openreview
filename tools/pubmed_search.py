#!/usr/bin/env python
"""Run a PubMed search and merge results into a review's records.json.

Usage:
    python tools/pubmed_search.py <slug> --query "<pubmed query>" [--label L] [--retmax N] [--date YYYY-MM-DD]

- esearch to get PMIDs, efetch to pull title/abstract/authors/year/journal/doi.
- New records are added as status=unscreened. Existing records (by PMID) get the
  search label appended to found_by (traceability rule) but are otherwise untouched.
- The search run is appended to protocol.json's `searches` log.

No API key required. Be polite: <=3 requests/sec.
"""
import argparse
import json
import sys
import time
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path

EUTILS = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"
ROOT = Path(__file__).resolve().parent.parent
REVIEWS = ROOT / "data" / "reviews"


def _get(url):
    with urllib.request.urlopen(url, timeout=60) as r:
        return r.read()


def esearch(query, retmax):
    q = urllib.parse.urlencode({"db": "pubmed", "term": query, "retmax": retmax, "retmode": "json"})
    data = json.loads(_get(f"{EUTILS}/esearch.fcgi?{q}"))
    return data["esearchresult"].get("idlist", []), int(data["esearchresult"].get("count", 0))


def efetch(pmids):
    """Fetch details for a list of PMIDs, in chunks."""
    out = {}
    for i in range(0, len(pmids), 200):
        chunk = pmids[i:i + 200]
        q = urllib.parse.urlencode({"db": "pubmed", "id": ",".join(chunk), "retmode": "xml"})
        xml = _get(f"{EUTILS}/efetch.fcgi?{q}")
        root = ET.fromstring(xml)
        for art in root.findall(".//PubmedArticle"):
            rec = _parse_article(art)
            if rec:
                out[rec["pmid"]] = rec
        time.sleep(0.4)
    return out


def _text(el):
    return "".join(el.itertext()).strip() if el is not None else ""


def _parse_article(art):
    pmid_el = art.find(".//PMID")
    if pmid_el is None:
        return None
    pmid = pmid_el.text.strip()
    title = _text(art.find(".//ArticleTitle"))
    abstract = " ".join(_text(a) for a in art.findall(".//Abstract/AbstractText")).strip()
    authors = []
    for a in art.findall(".//AuthorList/Author"):
        last = _text(a.find("LastName"))
        init = _text(a.find("Initials"))
        if last:
            authors.append(f"{last} {init}".strip())
    year = None
    y = art.find(".//JournalIssue/PubDate/Year")
    if y is not None and y.text and y.text.isdigit():
        year = int(y.text)
    else:
        md = art.find(".//JournalIssue/PubDate/MedlineDate")
        if md is not None and md.text:
            for tok in md.text.split():
                if tok[:4].isdigit():
                    year = int(tok[:4])
                    break
    journal = _text(art.find(".//Journal/Title"))
    doi = ""
    for eid in art.findall(".//ELocationID"):
        if eid.get("EIdType") == "doi":
            doi = _text(eid)
            break
    rec = {"pmid": pmid, "title": title, "abstract": abstract,
           "authors": authors, "found_by": [], "status": "unscreened"}
    if year:
        rec["year"] = year
    if journal:
        rec["journal"] = journal
    if doi:
        rec["doi"] = doi
    return rec


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("slug")
    ap.add_argument("--query", required=True)
    ap.add_argument("--label", help="short label for found_by (defaults to the query)")
    ap.add_argument("--retmax", type=int, default=500)
    ap.add_argument("--date", required=True, help="run date YYYY-MM-DD (Date.now is unavailable to the agent)")
    args = ap.parse_args()

    label = args.label or args.query
    revdir = REVIEWS / args.slug
    revdir.mkdir(parents=True, exist_ok=True)
    records_path = revdir / "records.json"
    protocol_path = revdir / "protocol.json"

    pmids, count = esearch(args.query, args.retmax)
    print(f"esearch: {count} total hits, fetching {len(pmids)} (retmax={args.retmax})")
    fetched = efetch(pmids) if pmids else {}

    records = json.loads(records_path.read_text(encoding="utf-8")) if records_path.exists() else []
    by_pmid = {r["pmid"]: r for r in records}

    added = updated = 0
    for pmid, rec in fetched.items():
        if pmid in by_pmid:
            if label not in by_pmid[pmid].get("found_by", []):
                by_pmid[pmid].setdefault("found_by", []).append(label)
                updated += 1
        else:
            rec["found_by"] = [label]
            by_pmid[pmid] = rec
            added += 1

    merged = sorted(by_pmid.values(), key=lambda r: -(r.get("year") or 0))
    records_path.write_text(json.dumps(merged, indent=2, ensure_ascii=False), encoding="utf-8")

    # append to protocol search log
    if protocol_path.exists():
        protocol = json.loads(protocol_path.read_text(encoding="utf-8"))
        protocol.setdefault("searches", []).append(
            {"database": "PubMed", "query": args.query, "date": args.date, "count": count,
             "note": f"label={label}; fetched={len(pmids)}; added={added}"})
        protocol_path.write_text(json.dumps(protocol, indent=2, ensure_ascii=False), encoding="utf-8")

    print(f"records.json: +{added} new, {updated} tagged, {len(merged)} total")


if __name__ == "__main__":
    main()
