#!/usr/bin/env python
"""Dual-independent screening harness for a review, with human-adjudicated conflicts.

The judgment is done by two independent `slr-screener` agents; this tool only prepares
their inputs and reconciles their outputs, so the rigorous parts (independence, provenance,
adjudication) are enforced deterministically.

Lifecycle (per stage: title-abstract | full-text):

  1. prep      — render the criteria file and batch the records to screen; print how to
                 invoke the two reviewers.
       python tools/screen.py prep <slug> --stage title-abstract [--sample N] [--seed S] [--batch-size 30]

  2. (run the slr-screener agent twice per batch — reviewer A and reviewer B —
      writing decisions to screening/<stage>/A/decisions_<n>.json and .../B/decisions_<n>.json)

  3. merge     — reconcile A vs B, write provenance into records.json, compute Cohen's kappa,
                 auto-resolve agreements, route conflicts + low-confidence to the queue.
       python tools/screen.py merge <slug> --stage title-abstract

  4. queue     — list records awaiting human adjudication.
       python tools/screen.py queue <slug> [--stage title-abstract]

  5. adjudicate — record a human decision on a queued record.
       python tools/screen.py adjudicate <slug> --stage title-abstract --pmid 123 --decision exclude --reason not-mouse

  6. stats     — agreement rate, kappa, confidence and outcome counts.
       python tools/screen.py stats <slug> [--stage title-abstract]

After adjudication, run tools/validate.py then regenerate views.
"""
import argparse
import random
import sys

import repo

ROOT = repo.ROOT
STAGES = ["title-abstract", "full-text"]


def load(p):
    return repo._read_json(p)


def save(p, obj):
    repo._write_json(p, obj)


def revdir(slug):
    return repo.review_dir(slug)


def stagedir(slug, stage):
    return revdir(slug) / "screening" / stage


def render_criteria(protocol, stage):
    L = [f"# Screening criteria — {protocol.get('title','')}", ""]
    L.append(f"**Stage:** {stage}")
    L.append(f"\n**Review question.** {protocol.get('question','')}\n")
    L.append("## Inclusion criteria (ALL must plausibly hold to include)")
    for i, c in enumerate(protocol.get("inclusion_criteria", []), 1):
        L.append(f"{i}. {c}")
    L.append("\n## Exclusion reasons (controlled vocabulary — use exact strings)")
    for r in protocol.get("exclusion_reasons", []):
        L.append(f"- `{r}`")
    L.append("\nApply the conservative rule: if a record cannot be confidently ruled out, "
             "**include** it with `low` confidence.")
    return "\n".join(L) + "\n"


def records_to_screen(records, stage):
    """Which records this stage screens."""
    if stage == "title-abstract":
        return [r for r in records if r.get("status") == "unscreened" and not (r.get("screening", {}) or {}).get("title-abstract")]
    # full-text: records that passed title-abstract and have no full-text screen yet
    out = []
    for r in records:
        ta = (r.get("screening", {}) or {}).get("title-abstract", {})
        if ta.get("outcome", {}).get("decision") == "include" and not (r.get("screening", {}) or {}).get("full-text"):
            out.append(r)
    return out


def cmd_prep(args):
    protocol = load(revdir(args.slug) / "protocol.json")
    records = load(revdir(args.slug) / "records.json")
    pool = records_to_screen(records, args.stage)
    if args.pmids:
        want = set(args.pmids.split(","))
        pool = [r for r in pool if r["pmid"] in want]
    elif args.sample:
        rng = random.Random(args.seed)
        pool = rng.sample(pool, min(args.sample, len(pool)))
    if not pool:
        print(f"nothing to screen at stage '{args.stage}'"); return

    sd = stagedir(args.slug, args.stage)
    (sd / "batches").mkdir(parents=True, exist_ok=True)
    (sd / "A").mkdir(exist_ok=True)
    (sd / "B").mkdir(exist_ok=True)
    (sd / "criteria.md").write_text(render_criteria(protocol, args.stage), encoding="utf-8")

    bs = args.batch_size
    nb = 0
    for i in range(0, len(pool), bs):
        nb += 1
        slim = [{"pmid": r["pmid"], "title": r["title"], "year": r.get("year"),
                 "abstract": r.get("abstract", "")} for r in pool[i:i + bs]]
        save(sd / "batches" / f"batch_{nb}.json", slim)

    print(f"prepared {len(pool)} record(s) in {nb} batch(es) under {sd.relative_to(ROOT)}")
    print("\nInvoke the slr-screener agent TWICE per batch (two independent reviewers). For each batch n:")
    print(f"  reviewer A -> read {sd.relative_to(ROOT)}/criteria.md and batches/batch_n.json,")
    print(f"              write decisions to {sd.relative_to(ROOT)}/A/decisions_n.json (reviewer id 'screener-A')")
    print(f"  reviewer B -> same batch, write to {sd.relative_to(ROOT)}/B/decisions_n.json (reviewer id 'screener-B')")
    print("Then: python tools/screen.py merge %s --stage %s" % (args.slug, args.stage))


def _read_decisions(sd, who):
    out = {}
    d = sd / who
    for f in sorted(d.glob("decisions_*.json")):
        for rec in load(f):
            out[str(rec["pmid"])] = rec
    return out


def kappa(a_dec, b_dec, pmids):
    n = len(pmids)
    if not n:
        return None
    both_in = sum(1 for p in pmids if a_dec[p]["decision"] == "include" and b_dec[p]["decision"] == "include")
    both_ex = sum(1 for p in pmids if a_dec[p]["decision"] == "exclude" and b_dec[p]["decision"] == "exclude")
    po = (both_in + both_ex) / n
    ai = sum(1 for p in pmids if a_dec[p]["decision"] == "include") / n
    bi = sum(1 for p in pmids if b_dec[p]["decision"] == "include") / n
    pe = ai * bi + (1 - ai) * (1 - bi)
    return 1.0 if pe == 1 else round((po - pe) / (1 - pe), 3), round(po, 3)


def cmd_merge(args):
    rp = revdir(args.slug) / "records.json"
    records = load(rp)
    by = {r["pmid"]: r for r in records}
    sd = stagedir(args.slug, args.stage)
    A = _read_decisions(sd, "A")
    B = _read_decisions(sd, "B")
    common = [p for p in A if p in B]
    if not common:
        print("no reviewer decisions found — did both reviewers write their files?"); sys.exit(1)

    resolved = conflicts = lowconf = 0
    for p in common:
        a, b = A[p], B[p]
        rec = by.get(p)
        if not rec:
            continue
        agree = a["decision"] == b["decision"]
        low = a.get("confidence") == "low" or b.get("confidence") == "low"
        needs_human = (not agree) or low
        passes = []
        for who, d in (("screener-A", a), ("screener-B", b)):
            passes.append({k: v for k, v in {
                "reviewer": who, "decision": d["decision"], "reason": d.get("reason"),
                "confidence": d.get("confidence"), "justification": d.get("justification"),
                "model": d.get("model"),
            }.items() if v})
        stage_obj = {"method": "dual-independent", "passes": passes,
                     "agreement": "agree" if agree else "conflict"}
        if needs_human:
            stage_obj["outcome"] = {"decision": "needs-adjudication"}
            conflicts += 1 if not agree else 0
            lowconf += 1 if (agree and low) else 0
            rec["status"] = "needs-adjudication"
            rec.pop("exclusion_reason", None)
        else:
            dec = a["decision"]
            reason = a.get("reason") or b.get("reason")
            stage_obj["outcome"] = {"decision": dec, **({"reason": reason} if dec == "exclude" and reason else {})}
            resolved += 1
            _apply_outcome(rec, args.stage, dec, reason)
        rec.setdefault("screening", {})[args.stage] = stage_obj

    save(rp, records)
    k = kappa(A, B, common)
    print(f"merged {len(common)} record(s) at stage '{args.stage}':")
    print(f"  auto-resolved (agreed, confident): {resolved}")
    print(f"  routed to queue — conflicts: {conflicts}, agreed-but-low-confidence: {lowconf}")
    if k:
        kv, po = k
        print(f"  observed agreement: {po}   Cohen's kappa: {kv}")
    print(f"  -> python tools/screen.py queue {args.slug} --stage {args.stage}")


def _apply_outcome(rec, stage, decision, reason):
    """Reflect a resolved stage decision in the top-level record status."""
    if decision == "exclude":
        rec["status"] = "excluded"
        rec["screening_stage"] = stage
        if reason:
            rec["exclusion_reason"] = reason
    else:  # include
        if stage == "title-abstract":
            rec["status"] = "unscreened"  # passed TA, now awaiting full-text
            rec.pop("exclusion_reason", None)
        else:
            rec["status"] = "included"  # extraction added separately
            rec.pop("exclusion_reason", None)


def _queued(records, stage=None):
    out = []
    for r in records:
        for st, sc in (r.get("screening") or {}).items():
            if stage and st != stage:
                continue
            if sc.get("outcome", {}).get("decision") == "needs-adjudication":
                out.append((r, st, sc))
    return out


def cmd_queue(args):
    records = load(revdir(args.slug) / "records.json")
    q = _queued(records, args.stage)
    if not q:
        print("adjudication queue is empty."); return
    print(f"{len(q)} record(s) awaiting human adjudication:\n")
    for r, st, sc in q:
        a, b = sc["passes"][0], sc["passes"][1]
        why = "CONFLICT" if sc.get("agreement") == "conflict" else "low-confidence"
        print(f"[{why}] PMID {r['pmid']} ({st}) — {r['title'][:80]}")
        print(f"    A: {a['decision']}{'/'+a.get('reason','') if a.get('reason') else ''} "
              f"({a.get('confidence','?')}) — {a.get('justification','')}")
        print(f"    B: {b['decision']}{'/'+b.get('reason','') if b.get('reason') else ''} "
              f"({b.get('confidence','?')}) — {b.get('justification','')}")
        print(f"    adjudicate: python tools/screen.py adjudicate {args.slug} --stage {st} --pmid {r['pmid']} --decision <include|exclude> [--reason R]\n")


def cmd_adjudicate(args):
    rp = revdir(args.slug) / "records.json"
    records = load(rp)
    rec = next((r for r in records if r["pmid"] == args.pmid), None)
    if not rec:
        print(f"no record {args.pmid}"); sys.exit(1)
    sc = (rec.get("screening") or {}).get(args.stage)
    if not sc:
        print(f"record {args.pmid} has no {args.stage} screening to adjudicate"); sys.exit(1)
    sc["adjudication"] = {k: v for k, v in {
        "by": args.by, "decision": args.decision, "reason": args.reason, "note": args.note}.items() if v}
    sc["outcome"] = {"decision": args.decision, **({"reason": args.reason} if args.decision == "exclude" and args.reason else {})}
    _apply_outcome(rec, args.stage, args.decision, args.reason)
    save(rp, records)
    print(f"adjudicated PMID {args.pmid} ({args.stage}) -> {args.decision}"
          + (f" / {args.reason}" if args.reason else "") + f" (by {args.by})")


def cmd_stats(args):
    records = load(revdir(args.slug) / "records.json")
    for stage in ([args.stage] if args.stage else STAGES):
        scs = [(r, r["screening"][stage]) for r in records if (r.get("screening") or {}).get(stage)]
        dual = [(r, s) for r, s in scs if s.get("method") == "dual-independent"]
        if not scs:
            continue
        print(f"\nStage: {stage}  ({len(scs)} screened; {len(dual)} dual-independent)")
        if dual:
            agree = sum(1 for _, s in dual if s.get("agreement") == "agree")
            A = {r["pmid"]: {"decision": s["passes"][0]["decision"]} for r, s in dual}
            B = {r["pmid"]: {"decision": s["passes"][1]["decision"]} for r, s in dual}
            k = kappa(A, B, list(A))
            print(f"  agreement: {agree}/{len(dual)}" + (f"   kappa: {k[0]}" if k else ""))
        pend = sum(1 for _, s in scs if s.get("outcome", {}).get("decision") == "needs-adjudication")
        print(f"  awaiting adjudication: {pend}")


def main():
    ap = argparse.ArgumentParser(description="Dual-independent screening harness.")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("prep"); p.add_argument("slug"); p.add_argument("--stage", choices=STAGES, required=True)
    p.add_argument("--sample", type=int); p.add_argument("--seed", type=int, default=7)
    p.add_argument("--pmids"); p.add_argument("--batch-size", type=int, default=30); p.set_defaults(fn=cmd_prep)

    p = sub.add_parser("merge"); p.add_argument("slug"); p.add_argument("--stage", choices=STAGES, required=True); p.set_defaults(fn=cmd_merge)
    p = sub.add_parser("queue"); p.add_argument("slug"); p.add_argument("--stage", choices=STAGES); p.set_defaults(fn=cmd_queue)
    p = sub.add_parser("adjudicate"); p.add_argument("slug"); p.add_argument("--stage", choices=STAGES, required=True)
    p.add_argument("--pmid", required=True); p.add_argument("--decision", choices=["include", "exclude"], required=True)
    p.add_argument("--reason"); p.add_argument("--note"); p.add_argument("--by", default="human"); p.set_defaults(fn=cmd_adjudicate)
    p = sub.add_parser("stats"); p.add_argument("slug"); p.add_argument("--stage", choices=STAGES); p.set_defaults(fn=cmd_stats)

    args = ap.parse_args()
    args.fn(args)


if __name__ == "__main__":
    main()
