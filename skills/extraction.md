# Skill: extracting data from included studies

Fill `extraction.arms[]` for each included study (schema: `records.schema.json`). One arm per
distinct genotype × exposure condition the study reports as a mesothelioma-susceptibility result.

## Per-arm fields
- `gene` — the gene/locus manipulated (e.g. Nf2, Cdkn2a, Trp53, Bap1). Use the mouse symbol.
- `modification` — heterozygous KO, homozygous KO, conditional deletion, knock-in, transgenic, point mutant.
- `mouse_model` — strain / background / allele detail as reported.
- `asbestos_type` — crocidolite, amosite, chrysotile, or other fibre (and dose if given, in notes).
- `route` — intraperitoneal (i.p.), intrapleural, inhalation, intratracheal.
- `comparator` — the control group (usually wild-type littermates, same exposure).
- `incidence` — mesothelioma incidence, mutant vs comparator (quote the numbers/percentages).
- `latency` — time-to-tumor or survival difference (quote it).
- `effect_direction` — one of: increased-susceptibility, decreased-susceptibility, no-effect, mixed, unclear.
  Judge relative to the comparator: faster/more tumors in the mutant = increased-susceptibility.
- `notes` — dose, cohort size, statistics, caveats.

## Rules
- Quote the study's own numbers; don't infer incidence that isn't reported.
- If a study crosses two mutations (e.g. Nf2;Cdkn2a double mutant), that's its own arm with
  `gene: "Nf2;Cdkn2a"`.
- `effect_direction` is about susceptibility to asbestos-induced mesothelioma vs the control —
  not about whether the gene is a tumor suppressor in the abstract.
- Keep extraction faithful to the paper; the synthesis view interprets across papers.
