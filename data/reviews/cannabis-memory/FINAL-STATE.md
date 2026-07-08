# Final state — Cannabis use & human memory function review

## The question

In humans, is cannabis use — whether acute administration, chronic/regular use, or
medicinal THC/CBD formulations — associated with changes in memory function (working
memory, verbal or episodic memory, or memory consolidation), as measured by validated
neuropsychological tests or neuroimaging in experimental, observational, or longitudinal
studies?

- **Population**: humans (any age; healthy volunteers or clinical/patient samples).
- **Exposure**: cannabis or a defined cannabinoid — acute administration (THC/CBD
  challenge, smoked / vaporized / oral), chronic or regular recreational use, or a
  medicinal THC/CBD formulation (nabiximols, dronabinol, prescribed cannabis).
- **Comparator**: non-users, placebo, or the participants' own pre-exposure / baseline.
- **Outcome**: memory function — working memory, verbal memory, episodic memory, or
  memory consolidation — quantified with a validated neuropsychological test or with
  neuroimaging of a memory process.

## Inclusion criteria (all must hold)

1. **Human** participants (not animal, not in-vitro / cell work).
2. A **cannabis or cannabinoid exposure** is characterized (acute, chronic/regular, or
   medicinal THC/CBD).
3. A **memory outcome** (working, verbal, episodic, or consolidation) is measured with a
   **validated neuropsychological test or neuroimaging**.
4. **Primary empirical study** — experimental, observational, or longitudinal — not a
   review, meta-analysis, commentary, or protocol.

## Exclusion reasons (controlled vocabulary)

`not-human`, `no-cannabis-exposure`, `no-memory-outcome`, `not-validated-measure`,
`in-vitro-or-animal`, `review-or-commentary`, `not-primary-research`,
`memory-not-isolable`, `wrong-language`, `duplicate`.

## What will exist when this is done

- `protocol.json` — the above, machine-readable and schema-valid.
- `records.json` — every candidate PubMed record, each with a screening decision and
  reason, and full extraction fields for the included studies.
- A PRISMA account: identified → deduplicated → title/abstract screened → full-text →
  included.
- `views/cannabis-memory-extraction.md` — the extraction table: sample · exposure type ·
  cannabinoid · study design · memory domain · measure · comparator · effect direction ·
  PMID/citation.
- `views/cannabis-memory-synthesis.md` — narrative grouped by exposure type (acute /
  chronic / medicinal) and memory domain, with an overall conclusion.

## Route (coarse)

1. **Protocol & search** — write the schema-valid protocol, run complementary PubMed
   searches (broad + measure-anchored + acute-experimental), dedupe.
2. **Screen** — dual-independent title/abstract screening, then full-text on survivors,
   with reasons; adjudicate conflicts; reach a frozen included set.
3. **Extract & synthesize** — pull structured per-arm fields from included studies,
   generate the extraction table, PRISMA account, and narrative synthesis.
