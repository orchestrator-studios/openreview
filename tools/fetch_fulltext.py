#!/usr/bin/env python
"""Fetch open-access full text for a review's records, with abstract fallback.

Standard systematic-review practice screens on full text, not abstracts. The PubMed
search tool only retrieves abstracts, so this tool acquires the actual papers where they
are openly available and records, per record, exactly which source was used — so the
full-text screen and the final report can state honestly what each decision was based on.

Resolution order per record (records that passed title/abstract screening):
  1. PubMed Central (PMC) — elink pubmed->pmc, then efetch the full article XML and
     extract the body text. This yields real, machine-readable full text.
  2. Unpaywall (by DOI) — if PMC has no full text, flag whether an open-access copy
     exists elsewhere and record its URL (PDF text is not parsed here — no PDF dependency).
  3. Otherwise — abstract only.

Writes:
  data/reviews/<slug>/fulltext/<pmid>.txt        the fetched body text (PMC hits only)
  data/reviews/<slug>/fulltext/_manifest.json    per-pmid provenance:
      {pmid: {source: pmc|unpaywall-oa|abstract-only, has_fulltext: bool,
              chars: int, pmcid: str|None, url: str|None}}

Usage:
    python tools/fetch_fulltext.py <slug> [--limit N] [--pmids a,b,c] [--refetch]

No API key required. Polite: <=3 requests/sec.
"""
import argparse
import json
import sys
import time
import urllib.parse
import urllib.request
import urllib.error
import xml.etree.ElementTree as ET
from pathlib import Path

import repo

EUTILS = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"
UNPAYWALL = "https://api.unpaywall.org/v2"
EMAIL = "cliff.rosen@gmail.com"        # NCBI/Unpaywall politeness contact
PACE = 0.34                             # seconds between network calls (~3/sec)


def _get(url, timeout=60):
    req = urllib.request.Request(url, headers={"User-Agent": f"openreview-slr ({EMAIL})"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()


def _passed_ta(r):
    sc = (r.get("screening") or {}).get("title-abstract") or {}
    return sc.get("outcome", {}).get("decision") == "include"


def pmc_id_for(pmid):
    """Resolve a PubMed id to *its own* PMC id via elink, or None.

    Only the `pubmed_pmc` linkname is the article's own PMC full-text record. Other
    dbto=pmc linksets (e.g. `pubmed_pmc_refs`) are the papers this one cites — following
    those would fetch the wrong article, so they are ignored. A missing `pubmed_pmc`
    link means the article is not in PMC (no open full text)."""
    q = urllib.parse.urlencode({"dbfrom": "pubmed", "db": "pmc", "id": pmid,
                                "retmode": "json", "email": EMAIL})
    try:
        data = json.loads(_get(f"{EUTILS}/elink.fcgi?{q}"))
    except Exception:
        return None
    for ls in data.get("linksets", []):
        for db in ls.get("linksetdbs", []):
            if db.get("linkname") == "pubmed_pmc":
                links = db.get("links") or []
                if links:
                    return str(links[0])
    return None


def _node_text(el):
    return "".join(el.itertext())


def pmc_fulltext(pmcid, expect_pmid):
    """Fetch and flatten the body text of a PMC article, or '' if unavailable/mismatched.

    Guard: the fetched article's own PMID (from article-meta) must equal expect_pmid.
    If it carries a different PMID, the link was wrong and the text is rejected —
    a wrong-paper full text is worse than none."""
    q = urllib.parse.urlencode({"db": "pmc", "id": pmcid, "retmode": "xml", "email": EMAIL})
    try:
        xml = _get(f"{EUTILS}/efetch.fcgi?{q}")
        root = ET.fromstring(xml)
    except Exception:
        return ""
    got = root.find(".//article-meta//article-id[@pub-id-type='pmid']")
    if got is not None and (got.text or "").strip() and (got.text or "").strip() != str(expect_pmid):
        return ""
    body = root.find(".//body")
    if body is None:
        return ""
    parts = []
    for el in body.iter():
        tag = el.tag.lower()
        if tag in ("title", "p"):
            t = " ".join(_node_text(el).split())
            if t:
                parts.append(t)
    # de-dupe consecutive repeats (iter can revisit nested), keep order
    out, prev = [], None
    for p in parts:
        if p != prev:
            out.append(p)
        prev = p
    return "\n".join(out).strip()


def unpaywall_oa(doi):
    """Return (is_oa, url) for a DOI via Unpaywall, or (False, None)."""
    if not doi:
        return False, None
    q = urllib.parse.urlencode({"email": EMAIL})
    try:
        data = json.loads(_get(f"{UNPAYWALL}/{urllib.parse.quote(doi)}?{q}"))
    except Exception:
        return False, None
    if not data.get("is_oa"):
        return False, None
    loc = data.get("best_oa_location") or {}
    return True, (loc.get("url_for_pdf") or loc.get("url"))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("slug")
    ap.add_argument("--limit", type=int, help="cap number of records processed (for testing)")
    ap.add_argument("--pmids", help="comma-separated subset")
    ap.add_argument("--refetch", action="store_true", help="re-process records already in the manifest")
    args = ap.parse_args()

    revdir = repo.study_dir(args.slug)
    records = repo.load_records(args.slug)
    ftdir = revdir / "fulltext"
    ftdir.mkdir(parents=True, exist_ok=True)
    man_path = ftdir / "_manifest.json"
    manifest = json.loads(man_path.read_text(encoding="utf-8")) if man_path.exists() else {}

    pool = [r for r in records if _passed_ta(r)]
    if args.pmids:
        want = set(args.pmids.split(","))
        pool = [r for r in pool if r["pmid"] in want]
    if not args.refetch:
        pool = [r for r in pool if r["pmid"] not in manifest]
    if args.limit:
        pool = pool[:args.limit]

    print(f"{len(pool)} record(s) to fetch (of {sum(1 for r in records if _passed_ta(r))} that passed title/abstract)")
    counts = {"pmc": 0, "unpaywall-oa": 0, "abstract-only": 0}
    for i, r in enumerate(pool, 1):
        pmid = r["pmid"]
        source, has_ft, chars, pmcid, url = "abstract-only", False, 0, None, None

        pmcid = pmc_id_for(pmid)
        time.sleep(PACE)
        if pmcid:
            text = pmc_fulltext(pmcid, pmid)
            time.sleep(PACE)
            if len(text) >= 500:                       # a real body, not just front matter
                (ftdir / f"{pmid}.txt").write_text(text, encoding="utf-8")
                source, has_ft, chars = "pmc", True, len(text)
        if not has_ft:
            is_oa, oa_url = unpaywall_oa(r.get("doi"))
            time.sleep(PACE)
            if is_oa:
                source, url = "unpaywall-oa", oa_url

        counts[source] += 1
        manifest[pmid] = {"source": source, "has_fulltext": has_ft, "chars": chars,
                          "pmcid": pmcid, "url": url}
        if i % 25 == 0 or i == len(pool):
            man_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
            print(f"  {i}/{len(pool)}  pmc={counts['pmc']} unpaywall-oa={counts['unpaywall-oa']} abstract-only={counts['abstract-only']}")

    man_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"done. sources: {counts}")
    print(f"manifest: {man_path.relative_to(repo.ROOT)}")


if __name__ == "__main__":
    main()
