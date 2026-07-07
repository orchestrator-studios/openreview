# openreview

*Rigorous PubMed research with almost none of the overhead — light enough for a quick question,
structured enough to trust and to show your work.*

> **Not affiliated with openreview.net** (the conference peer-review platform). Different project.

## What this is

This is a **workspace for thorough PubMed research** — from a formal systematic review down to a
careful afternoon literature search. It brings the rigorous method — search, screen every candidate
study against fixed criteria, extract structured data from the ones that qualify, and account for every
record dropped along the way — but with so little friction you'd use it for casual questions too. You
run it **by talking to Claude** — you say what you want ("search PubMed for X," "screen the new
records," "why was this one excluded?") and Claude does the work through versioned tools, keeping every
study, decision, and reason as a plain file.

You see the review three ways at once: **the chat** (Claude tells you what it did), a **live dashboard** (the
pipeline updates as the work lands), and **the files themselves** (the ground truth, always openable). The
result is a review whose every number can be traced back to its source and re-derived by someone who does
not take your word for it.

It ships with one finished review already inside — a study of how genetic mutations affect mice's
susceptibility to asbestos-induced mesothelioma — so there is something real to look at from the first minute.

## What kind of thing is this

It's a **Git repo you operate through a coding agent** — you clone it, open it in
[Claude Code](https://claude.com/claude-code), and *talk to it* to run a review. That's the whole
interface. There's no app to install, no server to host, no plugin to register, no web UI to log into.
The repo is the application.

If that sounds strange, the closest familiar thing is a spreadsheet template — except instead of
formulas waiting for input, it holds the *tools, rules, and instructions* an agent needs to do the
work, and instead of clicking cells you describe what you want. A file called `CLAUDE.md` at the root
tells the agent how to drive everything.

- **You use it, you don't deploy it.** Each review accretes inside the repo as durable files you own —
  not rows in someone else's database.
- **Built and tested with Claude Code.** In principle any capable coding agent that can read `CLAUDE.md`
  and run Python could operate it; Claude Code is what it's designed around and proven on. Start there.
- **Not a Claude Code plugin.** You don't install it into your agent; you point your agent at it. The
  novelty is exactly this: a repository that behaves like an application when an agent is holding it.

## Getting started — open the dashboard first

**You need:** [Claude Code](https://claude.com/claude-code) (or a comparable coding agent), Python 3, and
the one library the tools depend on — `pip install -r requirements.txt` (just `jsonschema`). PubMed access
needs no API key.

**1. Fire up the dashboard. This is the front door — every path in starts here.**

```bash
python tools/server.py
# → open http://127.0.0.1:8765/
```

That page is home. On a brand-new, empty workspace it greets you and shows you how to begin — there are no
reviews yet, so it tells you to talk to Claude and then *waits, live*, for your first one to appear. In this
repo it isn't empty: it already lists the bundled review. Click it and you drop into a finished pipeline —
532 retrievals → 324 unique → 33 full-text → 23 included, every exclusion reason and included study, all
drillable.

**2. Talk to Claude — and keep the dashboard in the corner of your eye.** Everything is driven by
conversation:

- "Walk me through how this review reached its 23 included studies."
- "Start a new review: does remote monitoring reduce heart-failure readmissions after discharge?"
- "Screen the unscreened records and show me any conflicts to adjudicate."

The moment Claude writes a new review's protocol, a card for it **appears on the dashboard on its own** —
no refresh, no build step. As screening runs, that review's funnel fills while you watch. The page is not
something you generate at the end; it is the live picture of the repo changing under the agent's hands.

**3. Drop to the files whenever you want the ground truth.** Everything the dashboard shows is a projection
of plain files in `data/reviews/<slug>/` — open the JSON and read it yourself. Chat, dashboard, files: three
views of one system, always in agreement.

**Starting your own review?** Just ask Claude. It interviews you for the question and criteria, writes the
protocol, runs the first search — and a new `data/reviews/<your-slug>/` appears, and lights up on the
dashboard, as it happens. (`CLAUDE.md` describes how the agent operates inside this workspace.)

---

The rest of this README is the *why* — the commitments that make a review here trustworthy, and where each
one lives in the system.

## Why it is built this way

A systematic review is only worth as much as it can be trusted, and it can only be trusted to the
extent it can be **seen**. Its authority does not come from the conclusion; it comes from the fact
that every record considered, every decision made, and every number reported can be traced back to
its source and re-derived by someone who does not take your word for it. Transparency is not a
section you write at the end. It is the product.

This workspace is built so that visibility is a property of the system the whole way through — from
the first search query to the final included study. And because you cannot trust a review produced
by a machine you cannot see into, **providing that visibility requires making the system itself
visible.** So the sections below show you how the thing is built, so that nothing about how a result
was reached is hidden from you.

---

## The principle: to make the review visible, make the system visible

Everything here follows from one commitment — no hidden state.

- **Every fact is a plain file you can open.** Records, decisions, criteria, and extracted data are
  JSON and Markdown, not rows in a database you have to query through us.
- **Every number is re-derivable.** The views and the report are *projections* of the data,
  regenerated by a script. Nothing is typed into a report by hand, so nothing can drift from the
  evidence. Delete a view and rebuild it and it is byte-for-byte the same.
- **Every decision carries its provenance.** A record remembers which searches surfaced it, how each
  reviewer judged it, where they disagreed, and who resolved it.
- **Every operation is deterministic and inspectable.** The judgment (screening) is delegated to
  agents whose instructions are versioned in the repo; the reconciliation, validation, and rendering
  are ordinary scripts you can read.

If you want to distrust a conclusion, the system is arranged so you can — by following it back to the
record it rests on.

---

## The experience: a repo that is alive because something is working inside it

A normal repo is inert — a pile of files that only changes when a person edits it. This one is different
while you use it, because there is an **agent moving through it**: reading the protocol, running searches,
writing records, screening, reconciling, regenerating views. The folder is in motion. Files appear, counts
change, decisions get written — not on a deploy, but continuously, as the work happens. The repo is alive
because the agent is dancing around inside it.

The **dashboard is what brings that life to your eyes.** Without it, the aliveness is real but invisible —
buried in JSON diffs you'd have to watch by hand. Open the dashboard and it surfaces: a new review card
blinks into the index the instant its protocol is written; a funnel fills segment by segment as records are
screened; the "where we are" pointer steps forward on its own. You are not looking at a report of work that
finished. You are watching the work move.

You operate it by **talking to Claude** — "run the susceptibility search," "screen the new records," "why
was this one excluded?" — and the answer arrives in three places at once, always in agreement:

- **In the chat**, in words — what it did, what it found, what it needs you to decide.
- **On the live dashboard**, in motion — the index of reviews, the pipeline funnel, the exclusions, the
  included studies, all updating as the work lands. Start it with `python tools/server.py`, open `/`, and
  leave it up beside the chat; it moves as the review moves.
- **In the files themselves** — the ground truth, always openable, never sealed off. Drop to
  `data/reviews/<slug>/` any moment to check what the chat and the dashboard just told you.

The dashboard is not a report you generate at the end. It is served live from the same data-access layer
the review is built on (`tools/repo.py`), reading the same files Claude writes — so it is always current,
never a stale snapshot, and shows exactly the numbers the static views would. Chat is the dialogue, the
dashboard is the life made visible, the files are the truth beneath both.

---

## The state machine: one linear sweep, ending in an evaluation

Under the conversation there is a simple, explicit process, and the dashboard puts it front and centre.
A review moves through one **linear sweep** of phases:

```
Protocol → Queries written → Queries run → De-duplicated → Title/abstract screen → Full-text screen → Extraction → Evaluation
```

**Title/abstract screen** and **Full-text screen** are *filters*: each judges records against the criteria
and drops the ones that fail. Those exclusions are not lost — they accumulate under **Excluded** in the
corpus account, which always reconciles: *retrieved − duplicates = unique*, and every unique record is
Included (green), Excluded (red), or still In-screening. The **Evaluation** at the end is a different thing —
a quality gate on the whole review, not a per-record filter.

The dashboard renders the sweep as a pronounced stepper: filled nodes are done, the highlighted node is where
the review is *now*, and one plain sentence states the single next action. None of this is a stored status that
could drift — it is **derived from the data on every read**, exactly like the counts. The furthest-along
incomplete phase *is* where you are; there is nothing else to trust.

The sweep ends at an **evaluation** — a checklist run once the analysis of what we have is complete. It is
**optimistic**: the review is assumed good and the evaluation passes unless a check fails. Completeness and
integrity checks — every record screened, every conflict resolved, every included study extracted, every
record traceable, every exclusion reason valid, the search actually yielded studies — are *blocking*: if one
fails, the machine **pauses and recruits you, carrying the reason**. Quality concerns that are not hard
failures (for example a corpus screened single-pass rather than dual-independent) are surfaced as *advisories*
that do not pause. So the branch every pass reaches — good to compile, or needs a human — is expressed as
visible, data-derived checks, never a hidden decision.

When the evaluation passes, one action remains: **export**. The dashboard's Export button regenerates the
self-contained HTML report from the same data-access layer and opens it — the deep, drillable view (full
records explorer, methodology trace, extraction table, protocol) travels as a single file, while the dashboard
stays live. The dashboard is where you *work*; the report is what you *ship*.

---

## Anatomy — and what each part lets you see

The workspace separates a reusable **engine** (topic-agnostic) from **reviews** (data instances). The
engine knows nothing about mice or asbestos; a review supplies its own question, criteria, and the
shape of the data it extracts.

| Part | What it is | What it makes visible |
|---|---|---|
| `OVERVIEW.md` | What this system is and the rules it holds to | The intent, before any data exists |
| `schemas/` | The structure and validity rules for all data (`protocol`, `records`) | *What is allowed* — the law every record is checked against |
| `tools/` | Deterministic operations: search, validate, screen; the shared data-access layer (`repo.py`); the code that renders views; and the dashboard `server.py` | *How* every transformation happens — nothing is done off the record |
| `tools/repo.py` | The one data-access layer: where data lives, how it is read/written, and the canonical projections | *That every surface reads the same numbers* — chat, dashboard, and static views all draw from here |
| `skills/` | The written procedures: the review workflow, screening, extraction, the evaluation gate | The method, in words, so it can be audited and repeated |
| `.claude/agents/` | The versioned `slr-screener` — the reviewer's fixed instructions | *How articles are judged* — the exact standard, not an improvised prompt |
| `views/` | View *logic*: the reusable templates — static `report.template.html` and live `dashboard.template.html` | *How* the evidence is rendered — one set of templates, every review |
| `data/reviews/<slug>/` | One review's system of record — `protocol.json`, `records.json`, the screening trail, and its rendered `views/` | The evidence, every decision on it, and the evidence made legible |

The domain lives in the review, not the engine. A review's `protocol.json` declares its
`extraction_profile` — the exact fields it pulls from each study — and the tools read columns and
category colours from it. So the same machinery serves any subject, and what is specific to *this*
review is all in one visible place.

---

## The pipeline is the audit trail

Each stage deposits provenance in place; there is no separate log to trust. The numbers reconcile at
every hand-off, so the funnel can be checked, not just believed. From the live review as it stands:

```
search        3 PubMed queries, run and recorded verbatim         532 retrievals
  ↓           (every query string + date is kept in protocol.json)
de-duplicate  by PMID; each record remembers all queries          324 unique   (208 dupes removed)
  ↓
screen        title/abstract, against 4 inclusion criteria        291 excluded ┐
  ↓           each exclusion carries one reason from a vocabulary   33 retained ┘ = 324 ✓
full-text     assess the survivors                                 10 excluded ┐
  ↓                                                                 23 included ┘ = 33 ✓
extract       structured fields per study → 27 gene arms
  ↓
views         PRISMA account · extraction table · synthesis · interactive report
```

You watch this funnel fill on the **live dashboard** as screening runs, and every count is a link in the
static HTML report: click it and you land on exactly the records behind it. `291 + 10 + 23 = 324` is shown
reconciling, not asserted — in both places, because both read the one projection in `tools/repo.py`.

---

## How articles are evaluated — visibly, and not by one judge

Screening is where a review is most easily biased, so it is the most instrumented step.

- **Two independent reviewers.** For each record, the `slr-screener` agent is run twice, without
  shared context. Each returns a decision, a reason from the controlled vocabulary, a **confidence**,
  and a one-line justification — all recorded.
- **Agreement is measured, not assumed.** The merge reports observed agreement and **Cohen's κ**. In
  the demonstration pilot, κ = 0.875 across 16 records.
- **Disagreements and low-confidence calls go to a human.** They do not get quietly auto-resolved;
  they collect in a queue you clear, and your adjudication is written into the record.
- **You can read the trail.** Open any record in the report and you see both reviewers' calls, whether
  they agreed, and how a conflict was settled.

The judgment is an agent's; the standard it applies (`.claude/agents/slr-screener.md`) and the
criteria it reads (`protocol.json`) are both fixed and versioned, so the same inputs reproduce the
same screening.

---

## Operating it (reproducibility is a form of visibility)

Anyone can re-run these and see the same result — that is the point.

```bash
# search (repeatable verbatim; adds only genuinely new records on re-run)
python tools/pubmed_search.py <slug> --label broad --date YYYY-MM-DD --query "<pubmed boolean>"

# dual-independent screening
python tools/screen.py prep  <slug> --stage title-abstract      # batch records + render criteria
#   → run the slr-screener agent twice per batch (reviewer A and B)
python tools/screen.py merge <slug> --stage title-abstract      # reconcile, report κ, route conflicts
python tools/screen.py queue <slug>                             # what awaits your adjudication
python tools/screen.py adjudicate <slug> --stage title-abstract --pmid <id> --decision include|exclude

# watch it live while you work — open / (the index of reviews), your front door
python tools/server.py                  # /                 — every review, live; new ones appear on their own
#                                        # /dashboard/<slug> — one review's state machine + pipeline, live
#                                        # /report/<slug>    — Export: regenerate the report and open it

# always, after any change to data
python tools/validate.py  <slug>        # schemas are law; provenance and reasons are checked
python tools/build_views.py  <slug>     # regenerate PRISMA + extraction table
python tools/build_report.py <slug>     # regenerate the interactive audit report
```

The **live dashboard** (`python tools/server.py`, then open `/`) is the everyday view: the index lists every
review and lights up the moment Claude creates a new one; each review's page polls the data-access layer and
moves as records are screened, so you keep it open beside the chat. The **static
report** at `data/reviews/<slug>/views/<slug>-report.html` is the self-contained, shareable snapshot — a
single file with tabs for **Methodology** (the reconciling trace, every count drillable), **Records** (the
full corpus at any filter point, each with its provenance), **Findings**, and **Protocol** (the criteria and
the exact, copy-pasteable search commands). Both render the same projection; the dashboard is live, the
report travels.

---

## The rules that keep it honest

These are enforced, not aspirational (`validate.py` fails the build otherwise):

1. **Schemas are law.** Nothing enters `data/` that does not conform; validate after every write.
2. **Views are regenerated, never hand-edited.** A projection that can drift from its source is a lie
   waiting to happen.
3. **Every record traces to a search.** No record appears from nowhere (`found_by` is required).
4. **Exclusions carry a reason from the protocol's vocabulary; conflicts carry an adjudication.**
5. **Provenance is never backfilled.** A confidence or justification a reviewer did not give is not
   invented to fill a field.

---

## What the system is honest about not yet doing

Visibility includes being visible about limits. And a general one first: **LLM-assisted screening is a
rigorous _aid_, not a drop-in replacement for dual _human_ screening under a registered protocol.** This
tool instruments and records the process so it can be audited; it does not absolve the reviewer of
accountability for the included set.

- **The bundled corpus was screened single-pass** (labelled `single-pass-legacy` in the data, and the
  report says so). The engine now does dual-review; re-screening the full corpus to that bar is a
  re-run, not yet done.
- **Screening reads abstracts, not full text.** PubMed E-utilities give us titles and abstracts;
  true full-text retrieval (PMC / publisher PDFs) is a capability we do not have yet. Extraction on the
  bundled review draws from abstracts too — treat its extracted fields as a demonstration of shape, not a
  clinical dataset.
- **The `slr-screener` agent is versioned here but not yet auto-discovered** as a first-class agent
  type from this subdirectory; the pilot ran it via general-purpose agents reading its spec.

---

## Where to look next

- `OVERVIEW.md` — the system's own statement of purpose and rules.
- `CLAUDE.md` — how the agent operates inside this workspace (the operating manual).
- `python tools/server.py` → open `/` — the front door: your reviews, live, new ones appearing on their
  own. Keep it beside the chat and watch the repo move.
- `data/reviews/mouse-genetics-mesothelioma/` — the live review: protocol, records, screening trail, views.
- `data/reviews/mouse-genetics-mesothelioma/views/mouse-genetics-mesothelioma-report.html` — the shareable
  snapshot; open it and start distrusting a number until you have followed it home.
- `tools/repo.py` — the data-access layer every surface reads from; `views/report.template.html` and
  `views/dashboard.template.html` — the templates it feeds, reused by every review.

## License

[MIT](LICENSE) © Orchestrator Studios

---

Feedback and issues welcome — that is the point. Open a GitHub issue.
