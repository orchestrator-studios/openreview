# System Overview

## Purpose

This workspace conducts **systematic literature reviews** and keeps every review as a
durable, auditable record. It is not a one-off report generator: each review is a first-class
object with a protocol, a search log, a set of candidate records, screening decisions with
reasons, and structured data extraction — assembled so the whole thing is reproducible and so
future reviews reuse the same machinery. The first review it runs asks how genetic mutations
in mice affect susceptibility to malignant mesothelioma after asbestos exposure.

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

- **PubMed / MEDLINE** via NCBI E-utilities (esearch + efetch), free, no key required.
- Reviews are stored per-project under `data/reviews/<slug>/`.

## What you'll ask of it

- Run a systematic search for a question and capture every candidate record.
- Screen records against inclusion/exclusion criteria, recording reasons.
- Extract structured data from included studies into a comparison table.
- Produce a PRISMA flow account and a synthesis of findings.
- Re-run or extend a search later and fold in only the genuinely new records.
