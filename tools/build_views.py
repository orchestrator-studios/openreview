#!/usr/bin/env python
"""Regenerate a review's Markdown views from its data: PRISMA account + extraction table.

This is the *code* half of the view logic (the templating is trivial here, so it lives inline);
the rendered *instances* are written into the study folder, next to the data they project:
    data/reviews/<slug>/views/<slug>-prisma.md       PRISMA-style flow + exclusion-reason breakdown
    data/reviews/<slug>/views/<slug>-extraction.md   one row per (study, arm)

Data access and the pipeline funnel are NOT computed here — they come from `tools/repo.py`,
the shared data-access layer, so this view, the HTML report, and the live dashboard all render
the same numbers. This file only turns that projection into Markdown.

Usage:
    python tools/build_views.py <slug>

Views are projections. Never hand-edit them; re-run this after any data change.
"""
import sys
from collections import Counter

import repo


def build_prisma(slug):
    p = repo.pipeline(slug)
    t = p["totals"]
    lines = [f"# PRISMA account — {p['title']}", ""]
    lines.append("_Generated from data by `tools/build_views.py` — do not edit by hand._\n")
    lines.append("## Search")
    for q in p["queries"]:
        lines.append(f"- **{q['database']}** ({q['date']}): {q['returned']} hits — `{q['query']}`")
    lines.append("")
    lines.append("## Flow")
    lines.append(f"- Records after de-duplication: **{t['unique']}**")
    lines.append(f"- Excluded at title/abstract: **{t['ta_excluded']}**")
    lines.append(f"- Excluded at full-text: **{t['ft_excluded']}**")
    if t["unscreened"]:
        lines.append(f"- Still unscreened: **{t['unscreened']}**")
    if t["needs_adjudication"]:
        lines.append(f"- Awaiting adjudication: **{t['needs_adjudication']}**")
    lines.append(f"- **Included: {t['included']}**")
    lines.append("")
    lines.append("## Exclusion reasons")
    lines.append("| Reason | n |")
    lines.append("|---|---|")
    combined = Counter()
    for stage in ("title-abstract", "full-text"):
        for reason, n in p["exclusions"][stage]:
            combined[reason] += n
    for reason, n in combined.most_common():
        lines.append(f"| {reason} | {n} |")
    lines.append("")
    lines.append("## Included studies")
    for s in p["included_studies"]:
        lines.append(f"- {s['citation']} — {s['title']} (PMID {s['pmid']})")
    return "\n".join(lines) + "\n"


def build_extraction(slug):
    protocol = repo.load_protocol(slug)
    records = repo.load_records(slug)
    included = [r for r in records if r.get("status") == "included"]
    profile = protocol.get("extraction_profile") or {"fields": []}
    table_fields = [f for f in profile["fields"] if f.get("in_table", True)]
    keys = [f["key"] for f in table_fields]
    sort_key = profile.get("summary_field") or (keys[0] if keys else None)

    lines = [f"# Extraction table — {protocol.get('title', slug)}", ""]
    lines.append("_Generated from data by `tools/build_views.py` — do not edit by hand._\n")
    cols = ["Study (PMID)"] + [f["label"] for f in table_fields]
    lines.append("| " + " | ".join(cols) + " |")
    lines.append("|" + "|".join(["---"] * len(cols)) + "|")

    def first_arm_key(r):
        arms = r.get("extraction", {}).get("arms", [{}])
        return (arms[0].get(sort_key, "") if arms else "") or ""

    for r in sorted(included, key=first_arm_key):
        cite = f"{repo.citation(r)} ({r['pmid']})"
        for arm in r.get("extraction", {}).get("arms", []):
            def c(k):
                return str(arm.get(k, "") or "").replace("|", "\\|").replace("\n", " ")
            lines.append("| " + " | ".join([cite] + [c(k) for k in keys]) + " |")
    return "\n".join(lines) + "\n"


def main():
    if len(sys.argv) < 2:
        print("usage: python tools/build_views.py <slug>")
        sys.exit(2)
    slug = sys.argv[1]
    outdir = repo.views_dir(slug)
    outdir.mkdir(parents=True, exist_ok=True)
    (outdir / f"{slug}-prisma.md").write_text(build_prisma(slug), encoding="utf-8")
    (outdir / f"{slug}-extraction.md").write_text(build_extraction(slug), encoding="utf-8")
    print(f"wrote {(outdir / f'{slug}-prisma.md').relative_to(repo.ROOT)} and {slug}-extraction.md")


if __name__ == "__main__":
    main()
