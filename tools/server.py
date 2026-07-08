#!/usr/bin/env python
"""server.py — a small read-only HTTP server behind the live pipeline dashboard.

It never touches the data directories directly: every response is built from
`tools/repo.py`, the same data-access layer the offline views use. So the numbers
on the live dashboard are, by construction, the same projection the PRISMA view and
the HTML report render — there is one definition of the pipeline, and this just
serves it over HTTP, read fresh on each request.

Routes
    GET /                                  → index: the reviews, linking to dashboards
    GET /dashboard/<slug>                  → the live review view (report.template.html, served live)
    GET /api/reviews                       → [{slug, title, totals}]  (list)
    GET /api/reviews/<slug>                → {protocol, records}      (full review)
    GET /api/reviews/<slug>/pipeline       → the canonical funnel projection (polled live)
    GET /health                            → {ok: true}

Usage
    python tools/server.py [--host 127.0.0.1] [--port 8765]

Stdlib only — no framework, no build step, consistent with the rest of the workspace.
"""
import argparse
import html as htmllib
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse

import build_report
import repo

INDEX_TEMPLATE = repo.ROOT / "views" / "index.template.html"


def _reviews_index():
    """Every review that has at least a protocol — so a review shows up the instant Claude
    creates it, before any records exist. Resilient: one malformed review never blanks the
    whole index."""
    out = []
    for slug in repo.list_reviews():
        if not repo.has_protocol(slug):
            continue
        try:
            p = repo.pipeline(slug)
        except Exception:
            is_ex = bool(repo.load_protocol(slug).get("example")) if repo.has_protocol(slug) else False
            out.append({"slug": slug, "title": slug, "question": "", "example": is_ex,
                        "totals": {"included": 0, "unique": 0, "needs_adjudication": 0},
                        "phase_label": "starting", "blocked": False, "complete": False,
                        "eval_status": "pending"})
            continue
        wf = p.get("workflow", {})
        out.append({"slug": slug, "title": p["title"], "question": p["question"],
                    "example": bool(repo.load_protocol(slug).get("example")),
                    "totals": p["totals"],
                    "phase_label": wf.get("phase_label", ""),
                    "blocked": wf.get("blocked", False),
                    "complete": wf.get("complete", False),
                    # the evaluation gate's verdict: "pending" until it runs, then
                    # "pass" or "paused" — the signal behind the index's eval-ready alert.
                    "eval_status": wf.get("evaluation", {}).get("status", "pending")})
    return out


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *a):  # quiet; the dashboard polls frequently
        pass

    def _send(self, code, body, ctype="application/json; charset=utf-8", download=None):
        if isinstance(body, (dict, list)):
            body = json.dumps(body, ensure_ascii=False)
        data = body.encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        if download:  # force a file download rather than in-tab render
            self.send_header("Content-Disposition", f'attachment; filename="{download}"')
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(data)

    def _err(self, code, msg):
        self._send(code, {"error": msg})

    def _missing_html(self, slug):
        """A friendly 404 for the HTML routes — a review that was deleted (or a stale bookmark)
        should land on a readable page with a way back, not a raw JSON error blob."""
        safe = htmllib.escape(slug)
        page = (
            '<!doctype html><meta charset="utf-8">'
            '<meta name="viewport" content="width=device-width,initial-scale=1">'
            "<title>Review not found — openreview</title><style>"
            "body{margin:0;min-height:100vh;display:grid;place-items:center;padding:24px;background:#e9eded;"
            "color:#1b2529;font-family:system-ui,-apple-system,'Segoe UI',Roboto,sans-serif;}"
            "@media(prefers-color-scheme:dark){body{background:#10161a;color:#e9eeef;}}"
            ".card{max-width:460px;padding:34px;text-align:center;background:#fff;border:1px solid #d7dedf;"
            "border-radius:16px;box-shadow:0 8px 30px rgba(20,40,48,.12);}"
            "@media(prefers-color-scheme:dark){.card{background:#192126;border-color:#2b373d;}}"
            "h1{font-family:Georgia,serif;font-size:22px;margin:0 0 10px;}"
            "p{color:#4c595f;line-height:1.55;margin:0 0 20px;}"
            "@media(prefers-color-scheme:dark){p{color:#aab7bc;}}"
            "code{font-family:ui-monospace,Consolas,monospace;}"
            "a{display:inline-block;background:#2f6377;color:#fff;text-decoration:none;padding:10px 18px;"
            "border-radius:10px;font-weight:600;font-size:14px;}</style>"
            '<div class="card"><h1>This review no longer exists</h1>'
            f"<p>There's no review <code>{safe}</code> in this workspace — its folder under "
            "<code>data/reviews/</code> may have been deleted or renamed.</p>"
            '<a href="/">← Back to all reviews</a></div>'
        )
        return self._send(404, page, "text/html; charset=utf-8")

    def do_HEAD(self):
        self.do_GET()

    def do_GET(self):
        path = urlparse(self.path).path.rstrip("/") or "/"
        parts = [p for p in path.split("/") if p]
        try:
            if path == "/":
                html = INDEX_TEMPLATE.read_text(encoding="utf-8")
                return self._send(200, html, "text/html; charset=utf-8")
            if path == "/health":
                return self._send(200, {"ok": True})

            # the review view (docs/dashboard-spec.md): flow nav Protocol · Search & screening ·
            # Findings (+ Records); Search & screening = the bar + the PRISMA flow, every count drilling
            # into Records; the quality gate sits at the top of Findings. Served live here; the same
            # template frozen is the export (/report).
            if parts[0] in ("dashboard", "pipeline") and len(parts) == 2:
                slug = parts[1]
                if not repo.has_protocol(slug):
                    return self._missing_html(slug)
                html = build_report.render(slug, live=True)
                return self._send(200, html, "text/html; charset=utf-8")

            # export: regenerate the frozen snapshot and send it as a file DOWNLOAD (not an in-tab render)
            if parts[0] == "report" and len(parts) == 2:
                slug = parts[1]
                if not repo.has_protocol(slug):
                    return self._missing_html(slug)
                build_report.write(slug)                 # refresh the on-disk snapshot too
                html = build_report.render(slug)         # live=False → frozen, self-contained
                return self._send(200, html, "text/html; charset=utf-8", download=f"{slug}-report.html")

            if parts[0] == "api" and len(parts) >= 2 and parts[1] == "reviews":
                if len(parts) == 2:
                    return self._send(200, _reviews_index())
                slug = parts[2]
                if not repo.has_protocol(slug):
                    return self._err(404, f"no review '{slug}'")
                if len(parts) == 3:
                    return self._send(200, repo.load_review(slug))
                if len(parts) == 4 and parts[3] == "pipeline":
                    return self._send(200, repo.pipeline(slug))
                return self._err(404, "unknown review sub-resource")

            return self._err(404, f"no route for {path}")
        except Exception as e:  # never leak a stack trace to the client
            return self._err(500, f"{type(e).__name__}: {e}")


def main():
    ap = argparse.ArgumentParser(description="Live pipeline dashboard server.")
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=8765)
    args = ap.parse_args()
    srv = ThreadingHTTPServer((args.host, args.port), Handler)
    base = f"http://{args.host}:{args.port}"
    reviews = [s for s in repo.list_reviews() if repo.has_protocol(s)]
    print(f"serving on {base}  (Ctrl-C to stop)")
    print(f"  ▶ open this →  {base}/     (your reviews; new ones appear live)")
    if reviews:
        for slug in reviews:
            print(f"      dashboard  {base}/dashboard/{slug}")
    else:
        print("      (no reviews yet — the page will tell you how to start one)")
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        print("\nstopped")


if __name__ == "__main__":
    main()
