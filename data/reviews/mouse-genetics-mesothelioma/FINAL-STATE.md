# Final state — Mouse genetics & asbestos mesothelioma review

## The question

In mice, how do genetic mutations (germline or engineered) affect susceptibility to
malignant mesothelioma following asbestos exposure?

- **Population**: mice (in-vivo), any strain, carrying a defined genetic modification
  (knockout, knock-in, transgenic, conditional, or spontaneous mutant).
- **Exposure**: asbestos (crocidolite, amosite, chrysotile) or comparable mineral fibre,
  by any route (typically intraperitoneal or intrapleural).
- **Comparator**: wild-type / genetically unmodified littermates under the same exposure.
- **Outcome**: malignant mesothelioma incidence, latency, or tumor burden.

## Inclusion criteria (all must hold)

1. In-vivo **mouse** study (not solely cell line / in-vitro, not rat/human as the primary model).
2. A **defined genetic modification** whose effect is the object of study.
3. **Asbestos (or mineral fibre) exposure** is administered.
4. **Mesothelioma** is a measured outcome (incidence, latency, or burden).

## Exclusion reasons (controlled vocabulary)

`not-mouse`, `no-genetic-modification`, `no-asbestos-exposure`, `no-mesothelioma-outcome`,
`in-vitro-only`, `review-or-commentary`, `not-primary-research`, `not-susceptibility-focus`,
`wrong-language`, `duplicate`.

## What will exist when this is done

- `protocol.json` — the above, machine-readable and schema-valid.
- `records.json` — every candidate PubMed record, each with a screening decision and reason,
  and full extraction fields for the included studies.
- A PRISMA account: identified → deduplicated → title/abstract screened → full-text → included.
- `views/mouse-genetics-mesothelioma-extraction.md` — the extraction table:
  gene/mutation · model · asbestos type & route · comparator · mesothelioma incidence ·
  latency · effect direction · PMID/citation.
- `views/mouse-genetics-mesothelioma-synthesis.md` — narrative grouped by gene/pathway
  (e.g. Nf2, Cdkn2a/p16-Arf, Trp53, Bap1) with an overall conclusion.

## Route (coarse)

1. **Build the machinery** — schemas, PubMed search tool, validate, view generators.
2. **Gather & screen** — run searches, dedupe, screen every record with reasons, reach a
   frozen included set.
3. **Extract & synthesize** — pull structured fields from included studies, generate the
   extraction table, PRISMA account, and narrative synthesis.
