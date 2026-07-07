# Skill: the evaluation gate

The **evaluation** is the last step of a pass: a checklist run once the analysis of what we have is
complete (screening done, included studies extracted). It exists so a review does not silently declare
itself finished — it must clear a quality/completeness bar, and where it can't, it **pauses and recruits
the human with a reason** instead of proceeding.

## How it behaves

- **Optimistic.** The review is assumed good; the evaluation *passes* unless a check fails.
- **Blocking checks** (a failure pauses the whole state machine and is surfaced as the next action):
  - `screening-complete` — no record is still awaiting title/abstract or full-text screening.
  - `no-open-conflicts` — nothing is waiting on human adjudication.
  - `included-extracted` — every included study has extracted data.
  - `traceability` — every record has `found_by` provenance.
  - `exclusion-reasons` — every exclusion uses a reason from the protocol's vocabulary.
  - `has-included` — the search actually yielded includable studies (0 included → verify the search,
    don't conclude "empty").
- **Advisory checks** (surfaced, but do *not* pause):
  - `dual-review` — the corpus was screened by two independent reviewers rather than single-pass.

## Where it lives

The checklist is computed in `tools/repo.py` (`_evaluation`), so it is **derived from the data on every
read** — the dashboard, the pipeline projection, and any tool see the same verdict, live. It is deliberately
not a stored flag that could drift from the evidence.

## Growing the checklist

Add a check by appending to the `checks` list in `_evaluation`: give it a `key`, `label`, `severity`
(`block` or `advisory`), an `ok` predicate over the records/protocol, and a `detail` string that reads well
both when it passes and when it fails (the failing `detail` becomes the explanation shown to the user).
Reach for a check whenever a rule is stated about what "good enough to compile" means — the same
*do-it-or-grow-it* move as adding a tool or a view.

## What a pause looks like

When a blocking check fails, the state machine's phase becomes **Evaluation (paused)**, `blocked` is true,
the next action is `Review needed — <first failure>`, and the dashboard shows the full checklist with the
failing items called out. The human resolves the underlying data (screens the stragglers, adjudicates,
extracts, or re-runs the search), and because the gate is derived, it clears itself on the next read.
