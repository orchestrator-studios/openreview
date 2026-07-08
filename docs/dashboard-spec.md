# Review view — locked layout spec

The agreed structure for the per-review view. Build to this; don't deviate without re-agreeing.

## Navigation — a top-level flow, plus Records

```
   Protocol  →  Pipeline activity  →  Findings  →  Eval        [ Records ]
```

- The four arrowed stops are the review's flow (left → right), current stop highlighted.
- **Records** is not a flow step — it's always reachable, and it's where every drill-down lands.

## The stops

**① Protocol** — the definition, read-only: question / PICO, inclusion criteria, exclusion-reason
vocabulary, search strategy (queries), extraction profile. Reference, not execution.

**② Pipeline activity** — two views, stacked, both fully clickable:

- **Bar (top)** — the corpus *right now*, one reconciling snapshot: `Retrieved − Duplicates =
  Unique`, then a stacked bar of the unique records split Included (green) / Excluded (red) /
  In-screening (neutral). Answers *"what's the current disposition?"* Each segment → Records, filtered.
- **PRISMA flow (below)** — the stage-by-stage funnel (SLR-standard), top line → bottom line:
  - Identification: records identified (n) · − duplicates removed (n)
  - Screening: unique to screen (n) · excluded at title/abstract (n, by reason) · still to screen (n)
    · assessed at full text (n) · excluded at full text (n, by reason)
  - Included: studies included (n)
  - Answers *"how did we get from everything to the included set, stage by stage?"* Every count → Records, filtered.

The bar and the flow are **different lenses on the same numbers** (state vs. funnel) — both live, neither replaces the other.

**③ Findings** — the results: included studies + extracted data (extraction table / synthesis).
Any article group → Records.

**④ Eval** — the quality gate: the evaluation checklist (blocking vs. advisory), pass / paused status.

**Records** — one screen: the article list, opened **pre-filtered** by whatever group was clicked
(all retrieved · duplicates · unique · excluded-at-T/A · a specific reason · passed-T/A ·
excluded-at-full-text · included · a given query). Each record shows its provenance and screening trail.

## The one rule

**Every count that stands for a group of articles is a link → Records, filtered to that group.**
No group is ever a dead number.
