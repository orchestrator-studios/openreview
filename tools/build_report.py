#!/usr/bin/env python
"""Render a review's interactive HTML report by binding its data into the shared template.

Separation of concerns:
- the presentation *logic* (the template) lives in `views/report.template.html`;
- the *code* that binds a review's data into it lives here in `tools/`;
- the rendered *instance* is written into the study's own `views/` folder (under its mode
  root, e.g. `data/reviews/<slug>/views/` or `data/deep-research/<slug>/views/`).

Usage:
    python tools/build_report.py <slug> [--date YYYY-MM-DD]

Re-run after any data change. The output is a projection — never hand-edit it.
"""
import argparse
import json

import repo

TEMPLATE_PATH = repo.ROOT / "views" / "report.template.html"
RESEARCH_TEMPLATE_PATH = repo.ROOT / "views" / "research.template.html"


def _bind(template_path, payload, slug, date, live):
    """Bake a study's data + projection into a template's placeholders. Shared by both modes."""
    template = template_path.read_text(encoding="utf-8")
    blob = json.dumps(payload, ensure_ascii=False).replace("</", "<\\/")
    return (template
            .replace("__DATA__", blob)
            .replace("__LIVE__", "true" if live else "false")
            .replace("__SLUG__", slug)
            .replace("__DATE__", date))


def render(slug, date="", live=False):
    """Bind a study's data into its view and return self-contained HTML, dispatched by mode.

    Pure — reads through `repo`, touches no files. Each mode has its own template
    (`report.template.html` for SLR, `research.template.html` for deep research), both bound
    the same way and serving as both the live dashboard (`live=True`) and the frozen export."""
    if repo.mode(slug) == "research":
        return render_research(slug, live=live)
    review = repo.load_review(slug)
    # Bake the canonical projection (the same funnel repo.py serves the pipeline view) into the
    # payload, so the report renders the corpus accounting from the one source of truth rather than
    # recomputing it — correct at any stage, including in-progress reviews.
    review["projection"] = repo.pipeline_from(review["protocol"], review["records"], slug)
    date = date or ((review["protocol"].get("searches") or [{}])[-1].get("date", ""))
    return _bind(TEMPLATE_PATH, review, slug, date, live)


def render_research(slug, live=False):
    """Bind a deep-research study into research.template.html — the peer of the SLR report.

    Bakes {brief, sources, findings, projection} into the template; the projection is the same
    canonical shape repo.py serves the live pipeline, so the dashboard and the frozen export
    render identically from one source of truth."""
    study = repo.load_review(slug)   # {brief, sources, findings}
    study["projection"] = repo.research_pipeline_from(
        study["brief"], study["sources"], study["findings"],
        repo.synthesis_path(slug).exists(), slug)
    searches = study["brief"].get("searches") or []
    date = (searches[-1].get("date", "") if searches else "")
    return _bind(RESEARCH_TEMPLATE_PATH, study, slug, date, live)


def write(slug, date=""):
    """Render and write the report into the study's views/ folder; return the path."""
    html = render(slug, date)
    outdir = repo.views_dir(slug)
    outdir.mkdir(parents=True, exist_ok=True)
    out = outdir / f"{slug}-report.html"
    out.write_text(html, encoding="utf-8")
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("slug")
    ap.add_argument("--date", default="")
    args = ap.parse_args()
    out = write(args.slug, args.date)
    kb = out.stat().st_size // 1024
    print(f"wrote {out.relative_to(repo.ROOT)} ({kb} KB)")


if __name__ == "__main__":
    main()
