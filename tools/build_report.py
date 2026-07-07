#!/usr/bin/env python
"""Render a review's interactive HTML report by binding its data into the shared template.

Separation of concerns:
- the presentation *logic* (the template) lives in `views/report.template.html`;
- the *code* that binds a review's data into it lives here in `tools/`;
- the rendered *instance* is written into the study folder: `data/reviews/<slug>/views/`.

Usage:
    python tools/build_report.py <slug> [--date YYYY-MM-DD]

Re-run after any data change. The output is a projection — never hand-edit it.
"""
import argparse
import json

import repo

TEMPLATE_PATH = repo.ROOT / "views" / "report.template.html"


def render(slug, date=""):
    """Bind a review's data into the shared template and return the self-contained HTML.

    Pure — reads through `repo`, touches no files. Used by the CLI (which then writes it)
    and by the dashboard server's export route (which serves it live)."""
    review = repo.load_review(slug)
    date = date or (review["protocol"].get("searches", [{}])[-1].get("date", ""))
    template = TEMPLATE_PATH.read_text(encoding="utf-8")
    blob = json.dumps(review, ensure_ascii=False).replace("</", "<\\/")
    return (template
            .replace("__DATA__", blob)
            .replace("__SLUG__", slug)
            .replace("__DATE__", date))


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
