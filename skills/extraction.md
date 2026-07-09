# Skill: extracting data from included studies

Extraction turns each *included* study into structured rows the synthesis can compare.
The fields are **not fixed by this skill** — they are declared per review in
`protocol.json → extraction_profile`. That is what makes the same engine work for any subject
(mesothelioma, sleep, cardiology, …): the tools read the profile and never hardcode a topic.
This skill explains the mechanism; the fields come from the review's protocol.

## The mechanism
- Each included record carries `extraction.arms[]` (schema: `records.schema.json`).
- **One arm per distinct condition the study reports** as a separate result — a genotype, a
  trial arm, a dose group, an exposure. A study reporting several conditions yields several
  arms; a study with one result yields one arm. (`extraction_profile.arm_noun` names what one
  arm *is* for this review.)
- The **keys** allowed in an arm are exactly the `key`s in the review's
  `extraction_profile.fields`. `validate.py` rejects arms with unknown keys, missing `required`
  fields, or categorical values outside the profile's declared set — so the **profile**, not
  this skill, is the source of truth for what a valid arm looks like.
- `extraction_profile.summary_field` names the categorical field the report groups and colours
  by; every arm should carry one of that field's declared values.

## Defining the profile (once per review)
Before extracting, make sure `protocol.json` has an `extraction_profile`: the per-arm `fields`
(each with `key`, `label`, optional `required` / `in_table` / `help`, and for categorical fields
a `values` map of `value → {label, tone}`), an `arm_noun`, and a `summary_field`. Adding a field
mid-review means adding it to the profile *first*, then extracting — validation keys off the
profile.

## Rules
- Quote the study's own numbers; don't infer values it doesn't report.
- Keep extraction faithful to the paper; the synthesis view interprets across papers.
- Only records with `status: included` may carry extraction (schema-enforced).
- Re-run `python tools/validate.py <slug>`, then rebuild the views, after extracting.

## Example profile (the bundled mesothelioma review)
For reference only — this is one review's profile, not the system's fields. It declares per-arm
fields like `gene`, `modification`, `mouse_model`, `asbestos_type`, `route`, `comparator`,
`incidence`, `latency`, and a categorical `effect_direction`
(increased / decreased / no-effect / mixed / unclear) as its `summary_field`, with `arm_noun`
"gene arm". A sleep or cardiology review would declare entirely different fields — same
machinery, different profile.
