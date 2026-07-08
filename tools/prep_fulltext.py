#!/usr/bin/env python
"""Prepare full-text screening batches that carry the fetched full text.

The generic screening harness (screen.py) batches only pmid/title/abstract. Full-text
screening must show the reviewer the actual paper where we have it. This adjunct builds
the full-text stage's criteria + batches so each record carries either its fetched full
text (PMC hits, from tools/fetch_fulltext.py) or, failing that, its abstract — and marks
which. It writes into the same screening/full-text/ layout screen.py expects, so
`screen.py merge --stage full-text` reconciles the reviewers' decisions unchanged.

Records with real full text are placed in small batches (full text is long); abstract-only
records are placed in larger batches. Full text is truncated to keep agent inputs bounded —
eligibility (population, exposure, design, memory measure) is decided from the abstract +
front/methods, which the head of the article retains.

Usage:
    python tools/prep_fulltext.py <slug> [--ft-batch 4] [--abs-batch 40] [--ft-cap 24000]
"""
import argparse
import json

import repo
import screen  # reuse render_criteria + records_to_screen


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("slug")
    ap.add_argument("--ft-batch", type=int, default=4, help="records per full-text batch")
    ap.add_argument("--abs-batch", type=int, default=40, help="records per abstract-only batch")
    ap.add_argument("--ft-cap", type=int, default=24000, help="max chars of full text per record")
    args = ap.parse_args()

    revdir = repo.review_dir(args.slug)
    protocol = repo.load_protocol(args.slug)
    records = repo.load_records(args.slug)
    ftdir = revdir / "fulltext"
    manifest = json.loads((ftdir / "_manifest.json").read_text(encoding="utf-8")) if (ftdir / "_manifest.json").exists() else {}

    pool = screen.records_to_screen(records, "full-text")
    if not pool:
        print("nothing to screen at full-text"); return

    with_ft, abstract_only = [], []
    for r in pool:
        m = manifest.get(r["pmid"], {})
        (with_ft if m.get("has_fulltext") else abstract_only).append(r)

    sd = revdir / "screening" / "full-text"
    (sd / "batches").mkdir(parents=True, exist_ok=True)
    (sd / "A").mkdir(exist_ok=True)
    (sd / "B").mkdir(exist_ok=True)
    (sd / "criteria.md").write_text(screen.render_criteria(protocol, "full-text"), encoding="utf-8")

    def slim(r, use_ft):
        rec = {"pmid": r["pmid"], "title": r["title"], "year": r.get("year"),
               "abstract": r.get("abstract", ""), "basis": "full-text" if use_ft else "abstract"}
        if use_ft:
            txt = (ftdir / f"{r['pmid']}.txt").read_text(encoding="utf-8")
            rec["fulltext"] = txt[:args.ft_cap]
            rec["fulltext_truncated"] = len(txt) > args.ft_cap
        return rec

    n = 0
    plan = []
    for i in range(0, len(with_ft), args.ft_batch):
        n += 1
        chunk = with_ft[i:i + args.ft_batch]
        (sd / "batches" / f"batch_{n}.json").write_text(
            json.dumps([slim(r, True) for r in chunk], indent=2, ensure_ascii=False), encoding="utf-8")
        plan.append((n, "full-text", len(chunk)))
    for i in range(0, len(abstract_only), args.abs_batch):
        n += 1
        chunk = abstract_only[i:i + args.abs_batch]
        (sd / "batches" / f"batch_{n}.json").write_text(
            json.dumps([slim(r, False) for r in chunk], indent=2, ensure_ascii=False), encoding="utf-8")
        plan.append((n, "abstract", len(chunk)))

    ft_batches = sum(1 for _, k, _ in plan if k == "full-text")
    print(f"pool={len(pool)}  with_full_text={len(with_ft)} ({ft_batches} batches of <= {args.ft_batch})"
          f"  abstract_only={len(abstract_only)} ({n - ft_batches} batches of <= {args.abs_batch})")
    print(f"total {n} batch(es) under {sd.relative_to(repo.ROOT)}")
    print("Batches with full text carry a 'fulltext' field; screen those on the full text. "
          "Abstract-only batches carry 'basis':'abstract'. Then run two slr-screener passes per "
          "batch and: python tools/screen.py merge %s --stage full-text" % args.slug)


if __name__ == "__main__":
    main()
