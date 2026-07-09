# Skill: deep research (the fast, cited-answer mode)

Deep research answers a question across many sources and produces a **verified, fully-cited
synthesis** — without the exhaustive search-and-screen of an SLR. Use it to get up to speed or
brief a decision. For exhaustive, defensible coverage, use `skills/systematic-review.md` instead
(see `skills/modes.md` to choose).

Each study is a folder under `data/reviews/<slug>/`, marked by `brief.json` (`mode: research`).

## 1. Brief first
Write `brief.json` (schema: `schemas/brief.schema.json`): the `question`, and a set of
`sub_questions` (each `{id, text}`) that decompose it. Findings are tracked against these
sub-questions, and the quality gate requires every one of them to be answered. Optionally set
`scope` (recency window, source types). This is the audit anchor — what you set out to answer.

## 2. Gather sources
Cast broadly across the web and literature. Record each in `sources.json`
(schema: `schemas/sources.schema.json`): `id`, `title`, `type`, `url`/`citation`, and
`found_by` (which sub-question or query surfaced it — the same traceability rule as SLR).
New sources start `status: gathered`. The `deep-research` harness skill is the fan-out engine;
this mode's job is to **persist** what it finds as auditable objects next to your reviews.

## 3. Read & triage
Read each source and move it off `gathered`: `read` (useful), `cited` (a finding rests on it),
or `discarded` (not useful). Fetch full text where you can and mark `basis`
(`fulltext` / `abstract` / `snippet`) so the depth of each read is visible on the record.

## 4. Draft findings
Write `findings.json` (schema: `schemas/findings.schema.json`). A finding is one claim:
its `statement`, the `answers` it addresses (sub-question ids), and the `cites` (source ids it
rests on — **every finding must cite at least one source**). This is the audit spine of the
mode: claim → source, the way an SLR record traces to a search.

## 5. Verify
Set each finding's `verification`: `corroborated` (≥2 independent sources agree),
`single-source` (rests on one — an advisory flag, not a failure), or `disputed` (sources
conflict — resolve it or report the conflict). Never leave a finding `unverified`. Verify
independently of drafting — a second pass, or the `claim-verifier` agent, keeps it honest.

## 6. Synthesise
Write `synthesis.md`: the narrative answer, organised by sub-question, with every claim
traceable to a finding and its sources. Assert nothing that isn't backed by a verified finding.

## 7. Validate, then regenerate views
After ANY write to data:

    python tools/validate.py <slug>
    python tools/build_views.py <slug>
    python tools/build_report.py <slug>

Views are projections — never hand-edit them; change the data and regenerate.

## The quality gate
Derived live in `repo.py` (exactly like the SLR gate — never a stored flag). It **pauses for a
human** when a finding cites no source, a sub-question is unanswered, or a finding is still
unverified; it **advises** when a finding rests on a single source. Passing means every
sub-question is answered and every finding is cited and verified.

## Extending later
Re-gather with new sources at any time; triage and draft findings for the new arrivals, then
rebuild. The gate re-derives itself on the next read.
