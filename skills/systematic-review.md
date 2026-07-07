# Skill: running a systematic review

The workflow, end to end. Each review is a folder under `data/reviews/<slug>/`.

## 1. Protocol first
Write `protocol.json` (schema: `schemas/protocol.schema.json`) before searching: the question,
PICO, inclusion criteria, the controlled list of exclusion reasons, and the planned queries.
This is the audit anchor — it says what you set out to do before you saw the results.

## 2. Search
Run each query with the search tool; it fetches records, dedupes by PMID, tags each record's
`found_by`, and appends to the protocol's search log:

    python tools/pubmed_search.py <slug> --query "<pubmed query>" --label <short> --date <YYYY-MM-DD>

Run several complementary queries (a broad one, plus gene-specific ones) rather than one
clever query — recall matters more than precision at this stage. Deduplication is automatic.

## 3. Screen  (see `skills/screening.md`)
Every record ends at `status` = `included` or `excluded`. Excluded records carry a
`screening_stage` and an `exclusion_reason` from the protocol's list. Screen in two passes:
title/abstract first (cheap, catches most exclusions), then full-text for survivors.

## 4. Extract  (see `skills/extraction.md`)
For each included study, fill `extraction.arms[]`. A study reporting several genotypes gets
several arms. Only included records may carry extraction (schema-enforced).

## 5. Validate, then regenerate views
After ANY write to data:

    python tools/validate.py <slug>
    python tools/build_views.py <slug>
    python tools/build_report.py <slug>

Rendered views are written into the study's own folder, `data/reviews/<slug>/views/`, next to the
data they project (the reusable templates live in the top-level `views/`). They are projections —
never hand-edit them; change the data and regenerate.

## Re-running later
Re-run a search with a new `--date`; only genuinely new PMIDs are added (as `unscreened`),
existing ones just get the label appended to `found_by`. Screen the new arrivals and rebuild.
