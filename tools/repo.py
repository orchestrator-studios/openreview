#!/usr/bin/env python
"""repo.py — the data-access layer for reviews.

Single source of truth for *where* review data lives, *how* it is read and written,
and *what the canonical projections are*. Every tool (validate, screen, build_views,
build_report) and the dashboard server go through here. Nothing else should open
`protocol.json` / `records.json`, hardcode a study-root path, or re-derive the
pipeline funnel — if two callers need the same number, it is defined once, here.

Three layers, low to high:
  1. paths + raw json     — study_dir, list_studies, load_protocol/records, save_records
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
import sys
from collections import Counter
from pathlib import Path

# Windows consoles default to a legacy codepage (cp1252) that can't encode the
# box-drawing glyphs, arrows, and check marks these tools print, which would crash
# an otherwise-successful run on a UnicodeEncodeError. Force UTF-8 for every tool
# that goes through this module (all of them do). Runs once at import.
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
SCHEMAS = ROOT / "schemas"

# Each research mode has its own top-level study root — nothing is privileged, and both are
# defined here symmetrically. mode(slug) is derived from which root holds the slug's folder,
# so the directory *is* the type. Adding a third mode is one entry in this map.
STUDY_ROOTS = {
    "slr":      DATA / "reviews",
    "research": DATA / "deep-research",
}


# ----------------------------------------------------------------------------
# 1. paths + raw json
# ----------------------------------------------------------------------------
def _root_of(slug):
    """The study root that holds this slug, or None if it lives nowhere yet."""
    for root in STUDY_ROOTS.values():
        if (root / slug).exists():
            return root
    return None


def study_dir(slug, for_mode=None):
    """The folder for a study. For an existing study, wherever it already lives; for a new
    one, pass `for_mode` to place it under that mode's root."""
    if for_mode is not None:
        return STUDY_ROOTS[for_mode] / slug
    return (_root_of(slug) or STUDY_ROOTS["slr"]) / slug


def views_dir(slug):
    return study_dir(slug) / "views"


def list_studies():
    """Every study across all mode roots, by slug (slugs are unique across roots)."""
    names = set()
    for root in STUDY_ROOTS.values():
        if root.exists():
            names.update(p.name for p in root.iterdir() if p.is_dir())
    return sorted(names)


def _read_json(p):
    return json.loads(Path(p).read_text(encoding="utf-8"))


def _write_json(p, obj):
    Path(p).write_text(json.dumps(obj, indent=2, ensure_ascii=False), encoding="utf-8")


def mode(slug):
    """The run type of a study, derived from which root directory holds it."""
    for m, root in STUDY_ROOTS.items():
        if (root / slug).exists():
            return m
    return "slr"


def has_protocol(slug):
    return (study_dir(slug) / "protocol.json").exists()


def has_brief(slug):
    return (study_dir(slug) / "brief.json").exists()


def has_study(slug):
    """A folder is a study once it carries either a protocol (SLR) or a brief (research)."""
    return has_protocol(slug) or has_brief(slug)


def load_protocol(slug):
    return _read_json(study_dir(slug) / "protocol.json")


def load_records(slug):
    p = study_dir(slug) / "records.json"
    return _read_json(p) if p.exists() else []


def save_records(slug, records):
    _write_json(study_dir(slug) / "records.json", records)


def load_brief(slug):
    return _read_json(study_dir(slug) / "brief.json")


def load_sources(slug):
    p = study_dir(slug) / "sources.json"
    return _read_json(p) if p.exists() else []


def load_findings(slug):
    p = study_dir(slug) / "findings.json"
    return _read_json(p) if p.exists() else []


def synthesis_path(slug):
    return study_dir(slug) / "synthesis.md"


def study_meta(slug):
    """The definition file for a study, whichever mode it is: brief or protocol."""
    return load_brief(slug) if mode(slug) == "research" else load_protocol(slug)


def load_review(slug):
    """The whole study as the views bind it — shape depends on mode."""
    if mode(slug) == "research":
        return {"brief": load_brief(slug), "sources": load_sources(slug),
                "findings": load_findings(slug)}
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
        if active_idx is not None and i > active_idx:
            status = "pending"          # a later phase is never "done" while an earlier one is still active
        elif done:
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
    """Read a study live and return its canonical projection, dispatched by mode.

    Both modes return the same top-level envelope keys — slug, mode, title, question,
    workflow (goal/phase/blocked/complete/next_action/phases/evaluation), and totals —
    so the dashboard server and index render either without knowing the mode. Only the
    mode-specific body (the SLR funnel vs. the research findings) differs."""
    if mode(slug) == "research":
        return research_pipeline(slug)
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
        "mode": "slr",
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


# ----------------------------------------------------------------------------
# 3b. projections — deep-research mode (the alternate run type)
#
# Mirrors the SLR engine above: a derived state machine (`_research_workflow`) and a
# derived quality gate (`_research_evaluation`), both recomputed from the data on every
# read — never a stored flag. The research audit spine is claim -> source: every finding
# cites at least one source (the analog of a record's found_by), and every finding is
# verified before the gate passes (the analog of screening).
# ----------------------------------------------------------------------------
_SRC_TRIAGED = {"read", "cited", "discarded"}


def _research_evaluation(findings, *, reached, coverage_gaps, uncited, unverified, n_findings,
                         synthesis_exists):
    """The research gate — same optimistic, block-vs-advisory design as `_evaluation`.

    Includes a `synthesis-compiled` block check: a brief cannot read "pass" until step 6
    (the synthesis) is written, so the gate agrees with the state machine's `complete`."""
    single = [f for f in findings if f.get("verification") == "single-source"]
    disputed = [f for f in findings if f.get("verification") == "disputed"]
    checks = [
        {"key": "has-findings", "label": "The research produced findings", "severity": "block",
         "ok": n_findings > 0,
         "detail": ("no findings drafted yet — nothing to synthesise" if n_findings == 0
                    else f"{n_findings} finding{_plural(n_findings)} drafted")},
        {"key": "every-finding-cited", "label": "Every finding cites a source", "severity": "block",
         "ok": not uncited,
         "detail": (f"{len(uncited)} finding(s) cite no source" if uncited
                    else "all findings trace to a source")},
        {"key": "sub-question-coverage", "label": "Every sub-question is answered", "severity": "block",
         "ok": not coverage_gaps,
         "detail": (f"{len(coverage_gaps)} sub-question(s) have no finding" if coverage_gaps
                    else "all sub-questions covered")},
        {"key": "findings-verified", "label": "No unverified findings", "severity": "block",
         "ok": not unverified,
         "detail": (f"{len(unverified)} finding(s) still unverified" if unverified
                    else "every finding checked")},
        {"key": "synthesis-compiled", "label": "The synthesis is compiled", "severity": "block",
         "ok": synthesis_exists,
         "detail": ("synthesis.md not written yet — compile it to finish the brief"
                    if not synthesis_exists else "synthesis compiled")},
        {"key": "no-disputes-open", "label": "No unresolved source conflicts", "severity": "advisory",
         "ok": not disputed,
         "detail": (f"{len(disputed)} finding(s) rest on disputed sources" if disputed
                    else "no open conflicts")},
        {"key": "corroboration", "label": "Findings corroborated across sources", "severity": "advisory",
         "ok": not single,
         "detail": (f"{len(single)} finding(s) rest on a single source" if single
                    else "corroborated across sources")},
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


def _research_workflow(brief, sources, findings, *, synthesis_exists, coverage_gaps,
                       uncited, unverified):
    """The research state machine, DERIVED from brief + sources + findings."""
    subqs = brief.get("sub_questions", [])
    n_src = len(sources)
    n_find = len(findings)
    untriaged = [s for s in sources if s.get("status", "gathered") not in _SRC_TRIAGED]

    p_brief = bool(subqs)
    p_gather = n_src > 0
    p_read = n_src > 0 and not untriaged
    p_findings = n_find > 0
    p_verify = p_findings and not unverified
    p_synth = synthesis_exists
    # the gate runs once findings exist and are verified (the analysis of what we have is done)
    ev_reached = p_findings and p_verify

    ev = _research_evaluation(findings, reached=ev_reached, coverage_gaps=coverage_gaps,
                              uncited=uncited, unverified=unverified, n_findings=n_find,
                              synthesis_exists=synthesis_exists)
    ev_paused = ev["status"] == "paused"
    blocked = ev_paused

    specs = [
        ("brief", "Brief", p_brief,
         f"{len(subqs)} sub-question{_plural(len(subqs))}" if p_brief else "not framed"),
        ("gather", "Sources gathered", p_gather,
         f"{n_src} source{_plural(n_src)}" if p_gather else "none yet"),
        ("read", "Sources read", p_read,
         f"{len(untriaged)} to read" if untriaged else (f"{n_src} triaged" if n_src else "—")),
        ("findings", "Findings drafted", p_findings,
         f"{n_find} finding{_plural(n_find)}" if p_findings else "none yet"),
        ("verify", "Findings verified", p_verify,
         f"{len(unverified)} to verify" if unverified else ("verified" if n_find else "—")),
        ("synthesis", "Synthesis", p_synth, "compiled" if p_synth else "not compiled"),
        ("evaluation", "Evaluation", ev["status"] == "pass",
         "pending" if not ev_reached
         else (f"{len(ev['failures'])} to resolve" if ev_paused
               else "passed" + (f" · {len(ev['advisories'])} advisory" if ev["advisories"] else ""))),
    ]

    active_idx = next((i for i, (_, _, done, _) in enumerate(specs) if not done), None)
    phases = []
    for i, (key, label, done, detail) in enumerate(specs):
        if active_idx is not None and i > active_idx:
            status = "pending"          # a later phase is never "done" while an earlier one is still active
        elif done:
            status = "done"
        elif i == active_idx:
            status = "blocked" if blocked else "active"
        else:
            status = "pending"
        phases.append({"key": key, "label": label, "status": status, "detail": detail})

    complete = active_idx is None
    active = specs[active_idx] if active_idx is not None else None

    if not p_brief:
        nxt = "Frame the brief: define the sub-questions"
    elif not p_gather:
        nxt = "Gather sources for the sub-questions"
    elif untriaged:
        nxt = f"Read and triage {len(untriaged)} source{_plural(len(untriaged))}"
    elif not p_findings:
        nxt = "Draft findings from the sources"
    elif unverified:
        nxt = f"Verify {len(unverified)} finding{_plural(len(unverified))}"
    elif uncited:
        nxt = f"Cite a source for {len(uncited)} finding{_plural(len(uncited))}"
    elif coverage_gaps:
        nxt = f"Answer {len(coverage_gaps)} uncovered sub-question{_plural(len(coverage_gaps))}"
    elif not p_synth:
        nxt = "Compile the synthesis"
    elif ev_paused:
        nxt = "Review needed — " + ev["failures"][0]["detail"]
    else:
        nxt = "Synthesis compiled — ready to export, or extend with more sources"

    if complete and not ev_paused:
        goal = "Synthesis compiled — a verified, cited answer across every sub-question."
    elif ev_paused:
        goal = (f"Paused for your review — {len(ev['failures'])} check(s) to resolve "
                f"before this pass is done.")
    else:
        goal = (f"Running toward a verified, fully-cited answer — {n_find} finding{_plural(n_find)} so far.")

    return {
        "goal": goal,
        "phase": active[0] if active else "complete",
        "phase_label": active[1] if active else "Complete",
        "blocked": blocked,
        "complete": complete,
        "next_action": nxt,
        "phases": phases,
        "state": {
            "awaiting_read": len(untriaged),
            "awaiting_verification": len(unverified),
            "uncited": len(uncited),
            "coverage_gaps": len(coverage_gaps),
        },
        "evaluation": ev,
    }


def research_pipeline(slug):
    """Read a deep-research study live and return its canonical projection."""
    return research_pipeline_from(load_brief(slug), load_sources(slug),
                                  load_findings(slug), synthesis_path(slug).exists(), slug)


def research_pipeline_from(brief, sources, findings, synthesis_exists, slug=None):
    """The research projection derived from an in-memory (brief, sources, findings).

    The 'research' analog of pipeline_from — one definition of the study's shape that the
    view, the report, and the live dashboard all render."""
    subqs = brief.get("sub_questions", [])
    subq_ids = [q["id"] for q in subqs]

    n_src = len(sources)
    n_find = len(findings)

    coverage = {q["id"]: sum(1 for f in findings if q["id"] in (f.get("answers") or []))
                for q in subqs}
    coverage_gaps = [qid for qid in subq_ids if coverage.get(qid, 0) == 0]
    uncited = [f for f in findings if not f.get("cites")]
    unverified = [f for f in findings if f.get("verification", "unverified") == "unverified"]
    n_read = sum(1 for s in sources if s.get("status", "gathered") in _SRC_TRIAGED)

    wf = _research_workflow(brief, sources, findings, synthesis_exists=synthesis_exists,
                            coverage_gaps=coverage_gaps, uncited=uncited, unverified=unverified)

    verif_break = Counter(f.get("verification", "unverified") for f in findings).most_common()
    type_break = Counter(s.get("type", "unspecified") for s in sources).most_common()

    return {
        "slug": slug,
        "mode": "research",
        "title": brief.get("title", slug),
        "question": brief.get("question", ""),
        "source": f"data/deep-research/{slug}" if slug else None,
        "workflow": wf,
        "totals": {
            "sources": n_src,
            "read": n_read,
            "findings": n_find,
            "unverified": len(unverified),
            "sub_questions": len(subqs),
            "covered": len(subq_ids) - len(coverage_gaps),
            # aliases so the SLR-shaped index keeps rendering research cards without branching
            "included": n_find,
            "unique": n_src,
            "needs_adjudication": len(unverified),
        },
        "sub_questions": [
            {"id": q["id"], "text": q["text"], "findings": coverage.get(q["id"], 0)}
            for q in subqs
        ],
        "coverage": coverage,
        "verification": verif_break,
        "source_types": type_break,
        "findings": [
            {"id": f["id"], "statement": f["statement"], "answers": f.get("answers", []),
             "cites": f.get("cites", []), "verification": f.get("verification", "unverified"),
             "confidence": f.get("confidence")}
            for f in findings
        ],
        "sources": [
            {"id": s["id"], "title": s.get("title", ""), "type": s.get("type", ""),
             "citation": s.get("citation") or s.get("title", ""), "url": s.get("url", ""),
             "status": s.get("status", "gathered"), "found_by": s.get("found_by", [])}
            for s in sources
        ],
    }
