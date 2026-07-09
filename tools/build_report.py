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
import html as htmllib
import json

import repo

TEMPLATE_PATH = repo.ROOT / "views" / "report.template.html"


def render(slug, date="", live=False):
    """Bind a study's data into its view and return self-contained HTML, dispatched by mode.

    Pure — reads through `repo`, touches no files. For SLR, the same template is both the
    exported static report (`live=False`) and the live dashboard (`live=True`). For deep
    research, a compact self-contained page rendered from the research projection."""
    if repo.mode(slug) == "research":
        return render_research(slug)
    review = repo.load_review(slug)
    # Bake the canonical projection (the same funnel repo.py serves the pipeline view) into the
    # payload, so the report renders the corpus accounting from the one source of truth rather than
    # recomputing it — correct at any stage, including in-progress reviews.
    review["projection"] = repo.pipeline_from(review["protocol"], review["records"], slug)
    date = date or ((review["protocol"].get("searches") or [{}])[-1].get("date", ""))
    template = TEMPLATE_PATH.read_text(encoding="utf-8")
    blob = json.dumps(review, ensure_ascii=False).replace("</", "<\\/")
    return (template
            .replace("__DATA__", blob)
            .replace("__LIVE__", "true" if live else "false")
            .replace("__SLUG__", slug)
            .replace("__DATE__", date))


_VERIF_TONE = {"corroborated": "pos", "single-source": "warn",
               "disputed": "neg", "unverified": "neutral"}


def render_research(slug):
    """A compact, self-contained deep-research report: brief, coverage, gate, findings, sources.

    First-cut view for the research mode (the rich, live-polling dashboard is the SLR template's
    counterpart, still to come). Renders the same projection repo.py serves everywhere."""
    p = repo.research_pipeline(slug)
    wf = p["workflow"]
    ev = wf["evaluation"]
    esc = htmllib.escape

    def chip(text, tone):
        return f'<span class="chip {tone}">{esc(text)}</span>'

    src_by_id = {s["id"]: s for s in p["sources"]}
    gate_tone = {"pass": "pos", "paused": "neg", "pending": "neutral"}.get(ev["status"], "neutral")

    parts = [
        "<!doctype html><meta charset='utf-8'>",
        "<meta name='viewport' content='width=device-width,initial-scale=1'>",
        f"<title>{esc(p['title'])} — deep research</title>",
        "<style>",
        ":root{--bg:#f3f5f5;--card:#fff;--ink:#1b2529;--mut:#54616a;--line:#dde3e4;--accent:#2f6377;}",
        "@media(prefers-color-scheme:dark){:root{--bg:#10161a;--card:#192126;--ink:#e9eeef;--mut:#9fb0b6;--line:#2b373d;--accent:#7fb2c6;}}",
        "*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);"
        "font-family:system-ui,-apple-system,'Segoe UI',Roboto,sans-serif;line-height:1.5;padding:28px;}",
        ".wrap{max-width:900px;margin:0 auto;}",
        "h1{font-family:Georgia,serif;font-size:26px;margin:0 0 4px;}",
        ".mode{font-size:12px;letter-spacing:.08em;text-transform:uppercase;color:var(--accent);font-weight:700;}",
        ".q{color:var(--mut);margin:6px 0 20px;}",
        ".card{background:var(--card);border:1px solid var(--line);border-radius:14px;padding:18px 20px;margin:14px 0;}",
        "h2{font-size:15px;margin:0 0 10px;text-transform:uppercase;letter-spacing:.05em;color:var(--mut);}",
        ".chip{display:inline-block;font-size:12px;font-weight:600;padding:2px 9px;border-radius:20px;border:1px solid var(--line);}",
        ".chip.pos{background:#e6f4ea;color:#1a7f37;border-color:#bfe3c9;}",
        ".chip.neg{background:#fdeaea;color:#b3261e;border-color:#f4c7c3;}",
        ".chip.warn{background:#fdf4e3;color:#8a5a00;border-color:#f0dfb8;}",
        ".chip.neutral{background:#eef1f2;color:#54616a;border-color:#dde3e4;}",
        "@media(prefers-color-scheme:dark){.chip.pos{background:#123522;color:#7fdca0;border-color:#1f5236;}"
        ".chip.neg{background:#3a1614;color:#f3a9a2;border-color:#5a221e;}"
        ".chip.warn{background:#3a2e12;color:#e8c67a;border-color:#5a4620;}"
        ".chip.neutral{background:#222c31;color:#9fb0b6;border-color:#31404a;}}",
        ".next{font-weight:600;}",
        ".sq{margin:0 0 6px;font-weight:600;}",
        "ul{margin:6px 0 16px;padding-left:20px;}li{margin:4px 0;}",
        ".src{font-size:13px;color:var(--mut);}",
        ".gate-row{display:flex;justify-content:space-between;gap:12px;padding:6px 0;border-top:1px solid var(--line);}",
        ".gate-row:first-of-type{border-top:none;}",
        "a{color:var(--accent);}",
        "</style>",
        "<div class='wrap'>",
        "<div class='mode'>Deep research</div>",
        f"<h1>{esc(p['title'])}</h1>",
        f"<div class='q'>{esc(p['question'])}</div>",
    ]

    # status
    parts.append("<div class='card'>")
    parts.append(f"<div>{chip(wf['phase_label'], 'neg' if wf['blocked'] else ('pos' if wf['complete'] else 'neutral'))} "
                 f"{chip('gate: ' + ev['status'], gate_tone)}</div>")
    parts.append(f"<p class='next'>Next: {esc(wf['next_action'])}</p>")
    parts.append(f"<p class='src'>{esc(wf['goal'])}</p>")
    parts.append("</div>")

    # quality gate
    parts.append("<div class='card'><h2>Quality gate</h2>")
    for c in ev["checks"]:
        tone = "pos" if c["ok"] else ("neg" if c["severity"] == "block" else "warn")
        mark = "pass" if c["ok"] else ("blocking" if c["severity"] == "block" else "advisory")
        parts.append(f"<div class='gate-row'><span>{esc(c['label'])} — <span class='src'>{esc(c['detail'])}</span></span>{chip(mark, tone)}</div>")
    parts.append("</div>")

    # findings by sub-question
    parts.append("<div class='card'><h2>Findings by sub-question</h2>")
    for q in p["sub_questions"]:
        parts.append(f"<div class='sq'>{esc(q['text'])} <span class='src'>({q['findings']} finding(s))</span></div>")
        hits = [f for f in p["findings"] if q["id"] in f["answers"]]
        if not hits:
            parts.append("<p class='src'>— no findings yet</p>")
            continue
        parts.append("<ul>")
        for f in hits:
            cites = ", ".join(esc(src_by_id.get(c, {}).get("citation", c)) for c in f["cites"])
            parts.append(f"<li>{esc(f['statement'])} {chip(f['verification'], _VERIF_TONE.get(f['verification'], 'neutral'))}"
                         f"<div class='src'>{cites}</div></li>")
        parts.append("</ul>")
    parts.append("</div>")

    # sources
    parts.append(f"<div class='card'><h2>Sources ({p['totals']['sources']})</h2><ul>")
    for s in p["sources"]:
        link = f" — <a href='{esc(s['url'])}'>link</a>" if s.get("url") else ""
        parts.append(f"<li>{esc(s['citation'])} <span class='src'>[{esc(s['type'] or 'source')} · {esc(s['status'])}]</span>{link}</li>")
    parts.append("</ul></div>")

    parts.append("</div>")
    return "".join(parts)


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
