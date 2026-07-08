# openreview

*Do a thorough, defensible PubMed search the way a systematic review would — without the heavyweight process.
Light enough for a Tuesday-afternoon question, rigorous enough to publish.*

> **Not affiliated with openreview.net** (the conference peer-review platform). Different project.

## What it is

openreview helps you search PubMed, screen what comes back against your own criteria, and pull out what
matters — and it records every step, so the result is auditable end to end: every paper you included, every
one you excluded and why, every count tracing back to the records behind it. You run it by **talking to an AI
assistant** (Claude): you say what you want, it does the searching and screening, and it keeps everything as
plain files you own. Think of it as a research assistant that shows all of its work.

Use it for a formal systematic review, or for any question where you want to search thoroughly and be able to
show — to a reviewer, a co-author, or yourself in six months — exactly how you reached your answer.

**Who it's for:** researchers who live in PubMed and care about defensible results — clinicians, grad students
and postdocs, research librarians, epidemiologists, evidence-synthesis teams — and who are comfortable working
through a coding agent. That's the one real cost of entry: you operate openreview through Claude Code, so you
(or someone on your team) need to be willing to get set up with it. If you've used a coding agent before,
you're past the hard part.

## How you use it

There's no app to install and no website to log into. openreview is a **folder you keep on your computer**,
operated through [Claude Code](https://claude.com/claude-code) — an AI assistant that can read files and run
programs. You open the folder in Claude Code and talk to it: *"search PubMed for remote monitoring and
heart-failure readmissions,"* *"screen the results against these criteria,"* *"why was this one excluded?"* It
does the work and writes everything down. (It's built and tested with Claude Code; in principle any capable
coding agent could operate it, but start there.)

While you work, you see the review in three places, and they always agree:

- **The conversation** — you and Claude, in plain language. This is how you drive everything: you ask, it
  acts, and it tells you what it did and what it needs you to decide.
- **A live dashboard** — a page in your browser that shows the review taking shape: the search funnel, what
  was excluded and why, what's included so far. It updates on its own as Claude works. (One command to start
  it — see Quickstart.)
- **The files** — every record, decision, and criterion is a plain file in the folder, yours to open, read,
  and keep. Nothing is hidden in a database you can't see.

The conversation is where you *act*, the dashboard is where you *watch*, the files are the *ground truth*
under both.

## Why you can trust it

Anyone can produce a list of papers. What makes a review worth something is that you can *check* it — follow
any claim back to the record it rests on, and re-derive every number yourself. openreview is built so you can:

- **Every number traces to its records.** The dashboard is a live **PRISMA flow** — the identification →
  screening → included funnel every reviewer knows — and every count is a link. Click *excluded at
  title/abstract*, a single exclusion reason, or *included*, and the exact papers behind it open. No number is
  a dead end.
- **Nothing is written by hand.** Every view and the exported report is generated from the underlying files by
  a script, so nothing can drift from the evidence. Rebuild it and it is identical.
- **Screening is instrumented, not improvised.** Records can be screened by *two independent* AI passes; the
  tool reports their agreement (Cohen's κ) and routes every disagreement or low-confidence call to *you* to
  decide. Each decision — who judged, how, and how a conflict was resolved — is recorded on the record.
- **Every decision carries its reason.** An exclusion without a reason from your protocol's list is invalid
  data, not just bad practice — the tools refuse it.

If you want to distrust a conclusion, the system is arranged so you can.

## Quickstart

You need [Claude Code](https://claude.com/claude-code), Python 3, and one library
(`pip install -r requirements.txt`). PubMed needs no account and no API key.

**1. Open the dashboard — your home base.**

```bash
python tools/server.py
# → open http://127.0.0.1:8765/
```

It ships with one finished example inside — a real PubMed review on how genetic mutations affect mice's
susceptibility to asbestos-induced mesothelioma — so there is something to explore from the first minute.
Because you haven't started your own review yet, the page also shows you how to begin.

**2. Open the folder in Claude Code and just ask.** *"Start a review: does remote monitoring reduce
heart-failure readmissions after discharge?"* Claude interviews you for the criteria, writes the protocol,
runs the PubMed search — and a card for your review appears on the dashboard on its own.

**3. Watch it work, then check anything.** As Claude screens, the funnel fills. Click any number to see the
papers behind it. Open the files in `data/reviews/<your-review>/` whenever you want the raw truth.

## What you see

A review opens as a single view with four stops, left to right — the shape of a review:

- **Protocol** — your question, criteria, and search strategy (the queries in plain text; the exact commands
  are one toggle away, for anyone who wants to reproduce them from a terminal).
- **Pipeline activity** — where the work is. A snapshot bar (*retrieved − duplicates = unique*, green included
  / red excluded / neutral in-screening) above the live **PRISMA flow**. Every count opens the records behind
  it.
- **Findings** — the included studies and the structured data extracted from them.
- **Eval** — a quality gate: completeness and integrity checks that either pass, or pause the review and tell
  you exactly what needs a human.

The full **records list** is one click from any number — search it, filter it, and see each paper's
provenance and screening trail. And one **Export** button freezes the whole view to a single self-contained
HTML file you can email or attach to a submission — same numbers, no server needed.

## Honest about its limits

- **LLM-assisted screening is a rigorous _aid_, not a replacement for dual _human_ screening under a
  registered protocol.** It instruments and records the process so it can be audited; it does not take
  responsibility for your included set off your shoulders.
- **Screening reads titles and abstracts, not full text.** PubMed gives us those; true full-text retrieval
  (PMC, publisher PDFs) isn't built yet. The bundled example's extracted data is drawn from abstracts too —
  treat it as a demonstration of shape, not a clinical dataset.
- **Conflicts and low-confidence calls in the bundled example were adjudicated with a light touch** — the
  agreed decisions accepted and borderline title/abstract cases carried to full text — rather than
  hand-reviewed one by one. It's a demonstration of the mechanism working end to end, not a clinical result.

## Under the hood

For the curious — the design that makes the guarantees hold.

- **A reusable engine, per-review data.** The engine (`schemas/`, `tools/`, `skills/`, and the versioned
  screening agent) knows nothing about any topic; each review supplies its own question, criteria, and the
  shape of the data it extracts, all under `data/reviews/<slug>/`. Same machinery, any subject.
- **One source of truth.** Every surface — the dashboard, the export, the files — reads the same projection
  from `tools/repo.py`. There is one definition of the funnel; nothing recomputes it, so nothing can disagree.
- **The rules are enforced, not aspirational** (`tools/validate.py` fails otherwise): schemas are law; views
  are regenerated, never hand-edited; every record traces to a search; exclusions carry a reason and conflicts
  carry an adjudication; provenance is never backfilled.

Start with `OVERVIEW.md` (what the system is), `CLAUDE.md` (how the agent operates inside it), and
`docs/dashboard-spec.md` (the review view's layout).

## License

[MIT](LICENSE) © Orchestrator Studios

---

Feedback and issues welcome — that's the point. Open a GitHub issue.
