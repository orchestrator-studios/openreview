#!/usr/bin/env python
"""repo.py — the data-access layer for reviews.

Single source of truth for *where* review data lives, *how* it is read and written,
and *what the canonical projections are*. Every tool (validate, screen, build_views,
build_report) and the dashboard server go through here. Nothing else should open
`protocol.json` / `records.json`, hardcode the `data/reviews` path, or re-derive the
pipeline funnel — if two callers need the same number, it is defined once, here.

Three layers, low to high:
  1. paths + raw json     — review_dir, list_reviews, load_protocol/records, save_records
  2. shared helpers       — citation, query_labels
  3. projections          — pipeline(): the funnel counts, exclusion breakdowns, and
                            per-query retrieval that the PRISMA view, the HTML report,
                            and the live dashboard all render.

The projections read from disk on every call, so a dashboard that polls `pipeline()`
sees screening progress as it lands in `records.json` — that is the whole "real-time"
story: one projection, read live, rendered many ways.
"""
import json
import re
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
REVIEWS = DATA / "reviews"
SCHEMAS = ROOT / "schemas"


# ----------------------------------------------------------------------------
# 1. paths + raw json
# ----------------------------------------------------------------------------
def review_dir(slug):
    return REVIEWS / slug


def views_dir(slug):
    return review_dir(slug) / "views"


def list_reviews():
    if not REVIEWS.exists():
        return []
    return sorted(p.name for p in REVIEWS.iterdir() if p.is_dir())


def _read_json(p):
    return json.loads(Path(p).read_text(encoding="utf-8"))


def _write_json(p, obj):
    Path(p).write_text(json.dumps(obj, indent=2, ensure_ascii=False), encoding="utf-8")


def has_protocol(slug):
    return (review_dir(slug) / "protocol.json").exists()


def load_protocol(slug):
    return _read_json(review_dir(slug) / "protocol.json")


def load_records(slug):
    p = review_dir(slug) / "records.json"
    return _read_json(p) if p.exists() else []


def save_records(slug, records):
    _write_json(review_dir(slug) / "records.json", records)


def load_review(slug):
    """The whole review as the views bind it: {protocol, records}."""
    return {"protocol": load_protocol(slug), "records": load_records(slug)}


# ----------------------------------------------------------------------------
# 2. shared helpers (formerly copy-pasted per tool)
# ----------------------------------------------------------------------------
def citation(r):
    a = r.get("authors") or []
    lead = a[0].split()[0] if a else "?"
    etal = " et al." if len(a) > 1 else ""
    return f"{lead}{etal} {r.get('year', 'n.d.')}"


def query_labels(protocol):
    """Query labels in execution order, parsed from each search's `note` (label=...)."""
    out = []
    for s in protocol.get("searches", []):
        m = re.search(r"label=([^;]+)", s.get("note", "") or "")
        if m:
            out.append(m.group(1).strip())
    return out


def search_by_label(protocol):
    out = {}
    for s in protocol.get("searches", []):
        m = re.search(r"label=([^;]+)", s.get("note", "") or "")
        if m:
            out[m.group(1).strip()] = s
    return out


# ----------------------------------------------------------------------------
# 3. projections — the canonical pipeline funnel, defined once
# ----------------------------------------------------------------------------
def _is_ta_excluded(r):
    return r.get("status") == "excluded" and r.get("screening_stage") == "title-abstract"


def _is_ft_excluded(r):
    return r.get("status") == "excluded" and r.get("screening_stage") == "full-text"


def _ta_screened(r):
    return bool((r.get("screening") or {}).get("title-abstract"))


def _ta_included(r):
    sc = (r.get("screening") or {}).get("title-abstract") or {}
    return sc.get("outcome", {}).get("decision") == "include"


def _ft_screened(r):
    return bool((r.get("screening") or {}).get("full-text"))


def _plural(n, one="", many="s"):
    return one if n == 1 else many


def _evaluation(protocol, records, *, awaiting_ta, awaiting_ft, awaiting_ext,
                needs_adj, n_inc, n_arms, reached):
    """The evaluation gate: a checklist run after the analysis of what we have.

    Optimistic by design — the review is assumed good and passes unless a check fails.
    A failing *block* check pauses the machine for human review and carries the reason;
    *advisory* checks are surfaced but do not pause. This is the loop-or-compile branch
    the review needs, expressed as data-derived quality/completeness checks rather than a
    stored decision that could drift. The checklist is meant to grow (see skills/evaluation.md).
    """
    allowed = set(protocol.get("exclusion_reasons", []))
    missing_trace = [r for r in records if not r.get("found_by")]
    bad_reason = [r for r in records if r.get("status") == "excluded" and allowed
                  and r.get("exclusion_reason") not in allowed]
    methods = {(r.get("screening") or {}).get(st, {}).get("method")
               for r in records for st in ("title-abstract", "full-text")}
    methods.discard(None)
    single = bool(methods & {"single", "single-pass-legacy"})
    dual = "dual-independent" in methods

    checks = [
        {"key": "screening-complete", "label": "All records screened", "severity": "block",
         "ok": not awaiting_ta and not awaiting_ft,
         "detail": (f"{len(awaiting_ta) + len(awaiting_ft)} record(s) still to screen"
                    if (awaiting_ta or awaiting_ft) else "every record reached a decision")},
        {"key": "no-open-conflicts", "label": "No unresolved conflicts", "severity": "block",
         "ok": not needs_adj,
         "detail": (f"{len(needs_adj)} record(s) awaiting adjudication" if needs_adj
                    else "all conflicts resolved")},
        {"key": "included-extracted", "label": "Every included study has extracted data",
         "severity": "block", "ok": not awaiting_ext,
         "detail": (f"{len(awaiting_ext)} included stud{_plural(len(awaiting_ext), 'y', 'ies')} missing extraction"
                    if awaiting_ext
                    else f"{n_inc} stud{_plural(n_inc, 'y', 'ies')} extracted into {n_arms} arm{_plural(n_arms)}")},
        {"key": "traceability", "label": "Every record traces to a search", "severity": "block",
         "ok": not missing_trace,
         "detail": (f"{len(missing_trace)} record(s) have no found_by provenance"
                    if missing_trace else "all records trace to a query")},
        {"key": "exclusion-reasons", "label": "Exclusions carry a valid reason", "severity": "block",
         "ok": not bad_reason,
         "detail": (f"{len(bad_reason)} exclusion(s) use an off-vocabulary reason"
                    if bad_reason else "all from the controlled vocabulary")},
        {"key": "has-included", "label": "The search yielded includable studies", "severity": "block",
         "ok": n_inc > 0,
         "detail": ("no studies were included — verify the search before concluding empty"
                    if n_inc == 0 else f"{n_inc} stud{_plural(n_inc, 'y', 'ies')} included")},
        {"key": "dual-review", "label": "Screened by dual independent review", "severity": "advisory",
         "ok": dual and not single,
         "detail": ("two independent reviewers, conflicts adjudicated" if (dual and not single)
                    else ("screened single-pass; dual-independent review recommended" if single
                          else "screening method not recorded"))},
    ]

    block_fail = [c for c in checks if c["severity"] == "block" and not c["ok"]]
    advisory_fail = [c for c in checks if c["severity"] == "advisory" and not c["ok"]]
    if not reached:
        status = "pending"
    elif block_fail:
        status = "paused"
    else:
        status = "pass"
    explanation = ("Paused for review — " + "; ".join(c["detail"] for c in block_fail) + "."
                   if status == "paused" else "")
    return {"reached": reached, "status": status, "checks": checks,
            "failures": block_fail, "advisories": advisory_fail, "explanation": explanation}


def workflow_state(protocol, records, *, retrieved, included, ta_excluded, ft_excluded,
                   needs_adj, n_arms):
    """The review as an explicit state machine, DERIVED from protocol + records.

    Not a stored, mutable status that could drift from the evidence — it is recomputed
    from the same files every time, like the funnel. It answers three questions the raw
    counts do not: which phase of the pass we are in, what the single next action is, and
    what the whole thing is running toward. The `state` block groups the live process
    signals (what is waiting on screening, on you, on extraction) that would otherwise be
    scattered — the decomposed `unscreened` number is the heart of it.
    """
    n = len(records)
    n_inc = len(included)
    n_queries = len(protocol.get("searches", []))

    # the meaning of "unscreened", split into what it actually represents
    awaiting_ta = [r for r in records if r.get("status") == "unscreened" and not _ta_screened(r)]
    awaiting_ft = [r for r in records if _ta_included(r) and not _ft_screened(r)]
    awaiting_ext = [r for r in included if not (r.get("extraction") or {}).get("arms")]

    # per-phase completion predicates (the earliest incomplete one is "active")
    p_protocol = bool(protocol.get("inclusion_criteria"))
    p_written = n_queries > 0
    # records existing proves the queries ran; `retrieved` can read 0 when a review's
    # records carry no labeled-search provenance, and that must not stall the state machine.
    p_run = retrieved > 0 or n > 0
    p_dedup = n > 0
    p_ta = n > 0 and not awaiting_ta
    p_ft = p_ta and not awaiting_ft
    # extraction is complete when nothing included is missing data — vacuously true when
    # nothing was included at all (that case is caught by the evaluation gate, not here)
    p_ext = p_ft and not awaiting_ext

    # the evaluation gate runs once the analysis of what we have is complete
    ev_reached = p_ext
    ev = _evaluation(protocol, records, awaiting_ta=awaiting_ta, awaiting_ft=awaiting_ft,
                     awaiting_ext=awaiting_ext, needs_adj=needs_adj, n_inc=n_inc,
                     n_arms=n_arms, reached=ev_reached)
    ev_paused = ev["status"] == "paused"
    blocked = len(needs_adj) > 0 or ev_paused

    n_crit = len(protocol.get("inclusion_criteria", []))
    specs = [
        ("protocol", "Protocol", p_protocol,
         f"{n_crit} criteria" if p_protocol else "not defined"),
        ("queries-written", "Queries written", p_written,
         f"{n_queries} quer{'y' if n_queries == 1 else 'ies'}" if p_written else "none yet"),
        ("queries-run", "Queries run", p_run,
         f"{retrieved} retrievals" if retrieved else (f"{n} records" if n else "not run")),
        ("dedup", "De-duplicated", p_dedup,
         f"{n} unique" if p_dedup else "—"),
        ("title-abstract", "Title/abstract screen", p_ta,
         f"{len(ta_excluded)} excluded · {len(awaiting_ta)} to screen" if awaiting_ta
         else f"{len(ta_excluded)} excluded"),
        ("full-text", "Full-text screen", p_ft,
         f"{len(ft_excluded)} excluded · {len(awaiting_ft)} to assess" if awaiting_ft
         else f"{len(ft_excluded)} excluded"),
        ("extraction", "Extraction", p_ext,
         f"{len(awaiting_ext)} to extract" if awaiting_ext
         else (f"{n_arms} arms" if n_inc else "no studies")),
        ("evaluation", "Evaluation", ev["status"] == "pass",
         "pending" if not ev_reached
         else (f"{len(ev['failures'])} to resolve" if ev_paused
               else "passed" + (f" · {len(ev['advisories'])} advisory" if ev["advisories"] else ""))),
    ]

    active_idx = next((i for i, (_, _, done, _) in enumerate(specs) if not done), None)
    phases = []
    for i, (key, label, done, detail) in enumerate(specs):
        if done:
            status = "done"
        elif i == active_idx:
            status = "blocked" if blocked else "active"
        else:
            status = "pending"
        phases.append({"key": key, "label": label, "status": status, "detail": detail})

    complete = active_idx is None
    active = specs[active_idx] if active_idx is not None else None

    # the single next action, in priority order
    if not p_written:
        nxt = "Define and run the first search"
    elif not p_run:
        nxt = "Run the written queries"
    elif needs_adj:
        nxt = f"Adjudicate {len(needs_adj)} record(s) awaiting your decision"
    elif awaiting_ta:
        nxt = f"Screen {len(awaiting_ta)} record(s) at title / abstract"
    elif awaiting_ft:
        nxt = f"Assess {len(awaiting_ft)} record(s) at full text"
    elif awaiting_ext:
        nxt = f"Extract data from {len(awaiting_ext)} included stud{'y' if len(awaiting_ext) == 1 else 'ies'}"
    elif ev_paused:
        nxt = "Review needed — " + ev["failures"][0]["detail"]
    elif complete:
        nxt = "Evaluation passed — compile the report, or extend the search for new records"
    else:
        nxt = "Regenerate the views"

    if complete:
        goal = (f"Evaluation passed — {n_inc} included stud{'y' if n_inc == 1 else 'ies'}, "
                f"ready to compile the report or extend the search.")
    elif ev_paused:
        goal = (f"Paused for your review — {len(ev['failures'])} check(s) to resolve "
                f"before this pass is done.")
    else:
        goal = (f"Running toward a reconciled set of included studies with full extraction"
                f" — {n_inc} included so far.")

    return {
        "goal": goal,
        "phase": active[0] if active else "complete",
        "phase_label": active[1] if active else "Complete",
        "blocked": blocked,
        "complete": complete,
        "next_action": nxt,
        "phases": phases,
        "state": {
            "awaiting_title_abstract": len(awaiting_ta),
            "awaiting_full_text": len(awaiting_ft),
            "awaiting_adjudication": len(needs_adj),
            "awaiting_extraction": len(awaiting_ext),
        },
        "evaluation": ev,
    }


def workflow(slug):
    """The state machine for one review, read live."""
    return pipeline(slug)["workflow"]


def pipeline(slug):
    """Read a review live and return its canonical funnel projection."""
    return pipeline_from(load_protocol(slug), load_records(slug), slug)


def pipeline_from(protocol, records, slug=None):
    """The pipeline funnel derived from an in-memory (protocol, records).

    This is the single definition of the review's flow. The PRISMA markdown view,
    the HTML report, and the live dashboard all render *this* shape — they never
    recompute stage counts themselves.
    """
    labels = query_labels(protocol)
    by_label = search_by_label(protocol)

    N = len(records)
    included = [r for r in records if r.get("status") == "included"]
    ta_excluded = [r for r in records if _is_ta_excluded(r)]
    ft_excluded = [r for r in records if _is_ft_excluded(r)]
    unscreened = [r for r in records if r.get("status") == "unscreened"]
    needs_adj = [r for r in records if r.get("status") == "needs-adjudication"]

    # per-query retrieval, cumulative-new in execution order
    seen = set()
    raw_retrievals = 0
    queries = []
    for lbl in labels:
        ret = [r for r in records if lbl in (r.get("found_by") or [])]
        new = [r for r in ret if r["pmid"] not in seen]
        for r in ret:
            seen.add(r["pmid"])
        raw_retrievals += len(ret)
        s = by_label.get(lbl, {})
        queries.append({
            "label": lbl,
            "database": s.get("database", ""),
            "date": s.get("date", ""),
            "query": s.get("query", ""),
            "returned": len(ret),
            "added": len(new),
            "cumulative": len(seen),
            "included": sum(1 for r in ret if r.get("status") == "included"),
        })

    def reason_break(subset):
        return Counter(r.get("exclusion_reason", "unspecified") for r in subset).most_common()

    # records returned by exactly k queries (dedup overlap)
    overlap = Counter(len(r.get("found_by") or []) for r in records)

    n_arms = sum(len((r.get("extraction") or {}).get("arms", [])) for r in included)
    methods = {s.get("method") for r in records for s in (r.get("screening") or {}).values()}

    wf = workflow_state(protocol, records, retrieved=raw_retrievals, included=included,
                        ta_excluded=ta_excluded, ft_excluded=ft_excluded,
                        needs_adj=needs_adj, n_arms=n_arms)

    # accounting: every retrieved record placed in exactly one bucket, and the buckets
    # reconcile — retrieved - duplicates = unique, and unique = included + excluded + in-screening.
    # Defined here so the dashboard renders one authoritative breakdown, not two.
    st = wf["state"]
    in_screening = st["awaiting_title_abstract"] + st["awaiting_full_text"] + st["awaiting_adjudication"]
    accounting = {
        "retrieved": raw_retrievals,
        "duplicates": max(0, raw_retrievals - N),
        "unique": N,
        "segments": [
            {"key": "included", "label": "Included", "tone": "pos", "n": len(included), "split": []},
            {"key": "excluded", "label": "Excluded", "tone": "neg",
             "n": len(ta_excluded) + len(ft_excluded),
             "split": [{"label": "at title/abstract", "n": len(ta_excluded)},
                       {"label": "at full text", "n": len(ft_excluded)}]},
            {"key": "in-screening", "label": "In screening", "tone": "neutral", "n": in_screening,
             "split": [{"label": "awaiting title/abstract", "n": st["awaiting_title_abstract"]},
                       {"label": "awaiting full text", "n": st["awaiting_full_text"]},
                       {"label": "awaiting adjudication", "n": st["awaiting_adjudication"]}]},
        ],
    }

    return {
        "slug": slug,
        "title": protocol.get("title", slug),
        "question": protocol.get("question", ""),
        "source": f"data/reviews/{slug}" if slug else None,
        "workflow": wf,
        "accounting": accounting,
        "totals": {
            "retrieved": raw_retrievals,
            "unique": N,
            # floored: a review with records but no labeled-search provenance has
            # raw_retrievals=0, which would otherwise make this go negative.
            "duplicates_removed": max(0, raw_retrievals - N),
            "unscreened": len(unscreened),
            "ta_excluded": len(ta_excluded),
            "passed_ta": N - len(ta_excluded),
            "ft_excluded": len(ft_excluded),
            "included": len(included),
            "needs_adjudication": len(needs_adj),
            "extraction_arms": n_arms,
        },
        "exclusions": {
            "title-abstract": reason_break(ta_excluded),
            "full-text": reason_break(ft_excluded),
        },
        "queries": queries,
        "overlap": {str(k): overlap[k] for k in sorted(overlap)},
        "screening_methods": sorted(m for m in methods if m),
        "included_studies": [
            {"pmid": r["pmid"], "citation": citation(r), "title": r.get("title", ""),
             "year": r.get("year")}
            for r in sorted(included, key=lambda r: -(r.get("year") or 0))
        ],
    }
