# Skill: screening records (dual independent + human adjudication)

Screening decides each record against the protocol's inclusion criteria. It is the step most
prone to error and bias, so it is done rigorously: **two independent reviewers per record, with
disagreements and low-confidence calls resolved by a human.** The judgment is delegated to the
`slr-screener` agent (versioned in `.claude/agents/`); the reconciliation is deterministic
(`tools/screen.py`). Every decision is recorded with full provenance in each record's `screening`
block, so the audit trail shows exactly how each inclusion was reached.

## Why dual review
A single screener — human or model — misses and misclassifies. The systematic-review standard is
two independent reviewers who never see each other's calls, with a third party (here, you) resolving
conflicts. Two independent agent passes are cheap and catch each other's errors; the human stays
accountable for the final included set.

## The loop (per stage: `title-abstract`, then `full-text`)

1. **Prep.** `python tools/screen.py prep <slug> --stage title-abstract`
   Renders the criteria file from `protocol.json` and batches the records still needing this stage.
   (Use `--sample N --seed S` for a calibration run, or `--pmids a,b,c` for specific records.)

2. **Two independent passes.** For each batch, invoke the `slr-screener` agent **twice** — reviewer
   A and reviewer B — each reading `screening/<stage>/criteria.md` and `batches/batch_n.json`, each
   writing to `.../A/decisions_n.json` and `.../B/decisions_n.json`. They must not share context.
   Each pass returns, per record: `decision`, `reason` (from the vocabulary), `confidence`, and a
   one-line `justification`.

3. **Merge.** `python tools/screen.py merge <slug> --stage title-abstract`
   Reconciles A vs B, writes provenance, reports observed agreement and **Cohen's kappa**, and:
   - **agree + both confident** → auto-resolved (its decision becomes the outcome);
   - **disagree, or either reviewer low-confidence** → `needs-adjudication`, routed to the queue.

4. **Adjudicate the queue.** `python tools/screen.py queue <slug>` lists every record awaiting you,
   showing both reviewers' calls and reasons. Resolve each:
   `python tools/screen.py adjudicate <slug> --stage title-abstract --pmid <id> --decision include|exclude [--reason R]`

5. **Validate & regenerate.** `python tools/validate.py <slug>` then rebuild views/report.

## Calibration (recommended before trusting a run)
Screen a small `--sample` that you also judge yourself; compare the reviewers' outcomes to yours to
estimate precision/recall. Report the figure in the review's methodology — that is what turns "an
agent screened it" into "an agent screened it, and here is how accurate it is."

## Reason vocabulary and outcomes
The exclusion vocabulary lives per-review in `protocol.json` (`exclusion_reasons`) — the engine and
the screener read it from there, so it is never hard-coded. A record's top-level `status` is derived
from its resolved screening outcomes: `excluded` (with stage + reason), `needs-adjudication`
(awaiting you), `unscreened` (not yet screened, or passed title/abstract and awaiting full-text), or
`included` (passed all stages; then extract per `skills/extraction.md`).

## Honesty
Independence is real only if the two passes don't share context — always two separate agent
invocations. Never backfill confidence or a justification a reviewer didn't give. Records the
reviewers couldn't resolve are *supposed* to reach you; do not auto-resolve them to clear the queue.
