# views/ — view logic (templates)

This folder holds the **presentation logic** for views: the templates. It does **not** hold rendered
output.

Every view — static or live — is built from four separable parts:

| Part | Lives in |
|---|---|
| **Data access** — reads the directories, defines the projections | `tools/repo.py` (the one data-access layer) |
| **Code** — binds a projection into a rendering | `tools/` (`build_report.py`, `build_views.py`, `server.py`) |
| **Template** — the presentation markup | **here**, `views/` (`report.template.html`, `dashboard.template.html`) |
| **Instance** — the rendered result | static: `data/reviews/<slug>/views/`; live: served on demand |

## The data-access layer (`tools/repo.py`)

Nothing else opens `protocol.json` / `records.json`, hardcodes the `data/reviews` path, or re-derives the
pipeline funnel. `repo.py` is the single source of truth for **where** data lives, **how** it is read and
written, and **what the canonical projections are** (`repo.pipeline(slug)` — the funnel counts, exclusion
breakdowns, and per-query retrieval). `validate.py`, `screen.py`, `build_views.py`, `build_report.py`, and
the dashboard `server.py` all go through it, so every surface renders the *same* numbers from one definition.

## Two kinds of view

**Static views** are rendered to files and committed next to the data they project. Regenerate (never
hand-edit) after any data change:

```bash
python tools/build_views.py  <slug>     # → data/reviews/<slug>/views/<slug>-prisma.md, -extraction.md
python tools/build_report.py <slug>     # → data/reviews/<slug>/views/<slug>-report.html
```

`report.template.html` is a self-contained page body with three placeholders the tool substitutes:
`__DATA__` (the review's `{protocol, records}`), `__SLUG__`, `__DATE__`.

**The live dashboard** is server-backed: it renders nothing to disk. `tools/server.py` (stdlib only)
serves `dashboard.template.html` and a small read-only JSON API drawn from `repo.py`; the page polls
`/api/reviews/<slug>/pipeline` and animates the funnel as screening decisions land in `records.json`.

```bash
python tools/server.py                                  # http://127.0.0.1:8765
#   /                                  index of reviews
#   /dashboard/<slug>                  the live pipeline dashboard
#   /api/reviews[/<slug>[/pipeline]]   the JSON the dashboard polls
```

Because the server reads through `repo.py` on every request, the dashboard is real-time by construction:
no rebuild step, no direct directory reads — same projection as the static views, served fresh.
