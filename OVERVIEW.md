# System Overview

## Purpose

This workspace conducts **systematic literature reviews** and keeps every review as a
durable, auditable record. Its purpose is **exhaustive, defensible coverage** of the literature
on a question — finding every relevant study and proving it — not a quick scan to get up to
speed on a topic (general search tools serve that better). It optimizes for completeness and
auditability over speed. It is not a one-off report generator: each review is a first-class
object with a protocol, a search log, a set of candidate records, screening decisions with
reasons, and structured data extraction — assembled so the whole thing is reproducible and so
future reviews reuse the same machinery. The first review it runs asks how genetic mutations
in mice affect susceptibility to malignant mesothelioma after asbestos exposure.

## Two modes

The workspace offers two research capabilities; each study is one or the other (`skills/modes.md`):

- **SLR** — the systematic review described above: exhaustive, auditable, PRISMA-shaped. Defined by
  `protocol.json` (`mode: slr`).
- **Deep research** — a faster, cited-answer mode: gather sources, extract findings that each cite a
  source, verify them, synthesise. For getting up to speed or briefing a decision, not exhaustive
  coverage. Defined by `brief.json` (`mode: research`); its things are the *brief*, *sources*, and
  *findings* (the analogs of protocol, records, extraction). See `schemas/` and `skills/deep-research.md`.

The two share one shell (dashboard, the `tools/repo.py` projection, validation, the rule that every
count is a link); they differ in data shape, quality gate, and rendered view. The entities below
describe the SLR mode.

## The things

- **Review** — one systematic-review project: a question, its protocol, and everything found for it.
- **Protocol** — the review's definition: question (PICO), inclusion/exclusion criteria, search strategy.
- **Search run** — one executed query against one database on one date, and the record IDs it returned.
- **Record** — one candidate study surfaced by a search: identifiers, bibliographic data, abstract.
- **Screening decision** — for a record, include/exclude at a stage (title-abstract, full-text) with a reason.
- **Extraction** — for an included study, the structured fields pulled out for synthesis.

## The rules

- Every record traces to at least one search run (no records appear from nowhere).
- A record's `status` reflects the furthest screening stage it reached; exclusions carry a reason.
- Data extraction fields are populated only for records with `status: included`.
- Nothing enters `data/` except in conformance with `schemas/`; validate after every write.
- Views (PRISMA flow, extraction table) are regenerated from data, never hand-edited.

## Where the data lives today

- **PubMed / MEDLINE** via NCBI E-utilities (esearch + efetch), free, no key required — supplies
  records and abstracts.
- **Full text** for the full-text screening pass via **PubMed Central** (open-access article XML,
  fetched and PMID-verified) with **Unpaywall** as an open-access fallback and the abstract when
  neither yields text. Each record records which source was used.
- SLR reviews are stored per-project under `data/reviews/<slug>/`, with fetched full text cached
  under `<slug>/fulltext/`. Deep-research briefs live under `data/deep-research/<slug>/`.

## What you'll ask of it

- Run a systematic search for a question and capture every candidate record.
- Screen records against inclusion/exclusion criteria, recording reasons.
- Extract structured data from included studies into a comparison table.
- Produce a PRISMA flow account and a synthesis of findings.
- Re-run or extend a search later and fold in only the genuinely new records.
