# openreview

A transparent, agent-operated workspace for **systematic literature reviews** — where every
record considered, every screening decision, and every number reported traces back to its
source and can be re-derived by someone who does not take your word for it.

> **Status: scaffolding.** This repo is being stood up. The engine (schemas, tools, skills,
> screening agent) and a worked example are landing shortly from active development. Watch or
> star to follow along.

## What kind of thing is this

It's a **Git repo you operate through a coding agent** — you clone it, open it in
[Claude Code](https://claude.com/claude-code), and *talk to it* to run a review. That's the
whole interface. There's no app to install, no server to host, no plugin to register, no web
UI. The repo is the application.

If that sounds strange, the closest familiar thing is a spreadsheet template — except instead
of formulas waiting for input, it holds the *tools, rules, and instructions* an agent needs to
do the work, and instead of clicking cells you describe what you want. A file called
`CLAUDE.md` at the root tells the agent how to drive everything; you say "search PubMed for X
and screen it against these criteria," and it runs the tools, records the decisions, and
regenerates the report — all as plain files that stay in the repo.

- **You use it, you don't deploy it.** Each review accretes inside the repo as durable files.
  Your evidence, decisions, and report are yours, in a folder you own — not rows in someone's
  database.
- **Built and tested with Claude Code.** In principle any capable coding agent that can read
  `CLAUDE.md` and run Python could operate it; Claude Code is what it's designed around and
  proven on. Start there.
- **Not a Claude Code plugin.** You don't install it into your agent; you point your agent at
  it. The novelty is exactly this: a repository that behaves like an application when an agent
  is holding it.

You need: [Claude Code](https://claude.com/claude-code) (or a comparable agent) and Python.
That's it — PubMed access needs no API key.

## The idea

A systematic review is only worth as much as it can be trusted, and it can only be trusted to the
extent it can be *seen*. So this workspace keeps no hidden state: records, criteria, decisions, and
extracted data are plain files you can open; every view and report is a projection regenerated from
those files by a script, never typed by hand; and every decision carries its provenance. To make the
review visible, it makes the system itself visible.

## What's coming

- **PubMed search** via NCBI E-utilities (no API key) — every query logged verbatim, results deduped
  by PMID with full traceability.
- **Dual-independent screening** — two independent agent reviewers per record, Cohen's κ reported,
  disagreements and low-confidence calls routed to a human adjudication queue.
- **Structured extraction** into a per-review profile, validated against the protocol.
- **PRISMA flow + an interactive, self-contained audit report** where every count is drillable back
  to the records behind it.

## Layout

| Path | What lives here |
|---|---|
| `schemas/` | The structure and validity rules for all review data |
| `tools/` | Deterministic operations: search, validate, screen, render |
| `skills/` | The written procedures — the review workflow, screening, extraction |
| `.claude/agents/` | The versioned screening agent (its fixed, auditable standard) |
| `views/` | Reusable view templates (rendered output lives with each review's data) |
| `data/reviews/<slug>/` | One review's system of record: protocol, records, screening trail, views |

## Honest about its limits

LLM-assisted screening is a rigorous *aid*, not a drop-in replacement for dual **human** screening
under a registered PRISMA protocol. This tool instruments and records the process so it can be
audited; it does not absolve the reviewer of accountability for the included set.

## License

[MIT](LICENSE) © Orchestrator Studios

---

Feedback and issues welcome — that is the point. Open a GitHub issue.
