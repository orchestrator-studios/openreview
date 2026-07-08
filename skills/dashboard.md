# Skill: keeping the live dashboard up for the user

The dashboard (`tools/server.py` → http://127.0.0.1:8765/) is the user's window into a review:
the funnel filling, the drill-downs, the "your review is ready" and "evaluation passed / paused"
alerts. **It is the whole visual payoff.** A Claude Code user working in one terminal will not
start a second long-running server on their own — so *you* keep it up for them. Treat a running
dashboard as a precondition for review work, the way validation is a postcondition for it.

## The rule

At the **first review-touching action of a session** — the user asks to start, resume, search,
or screen a review — make sure the dashboard is running **before** you kick off the slow work, and
hand the user the link. Do it once per session; don't re-announce on every subsequent action.

Bring it up *first* so the live magic lands: the user should have the page open before the search
runs, so they watch the card appear and the funnel fill — not discover a finished review after the
fact.

## The recipe

1. **Probe — never assume, never double-launch.** The server has a health endpoint, so a check is
   cheap and idempotent. The user (or a previous action) may already have it running:

       python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8765/health', timeout=1)"

   Exit 0 → it's already up; skip to step 3 and just give the link. Non-zero (connection refused) →
   it's not running; launch it.

2. **Launch in the background** from the repo root (the server is CWD-independent — `repo.ROOT` is
   derived from `__file__`), as a background process so it outlives the turn:

       python tools/server.py

   Then re-probe the health endpoint a few times until it answers (it binds in well under a second).
   If port 8765 is held by a *foreign* process (health check returns something that isn't our
   `{"ok": true}`, or the bind fails), relaunch on another port — `python tools/server.py --port 8766`
   — and use that port in the link you give the user.

3. **Tell the user, once.** A single clear line with the URL, framed as "watch it live," e.g.
   *"Your dashboard is live at http://127.0.0.1:8765/ — open it and you'll see this review appear and
   fill in as I work."* If it was already running, still surface the link the first time this session.

## Lifecycle — be honest, don't leak

The background server is tied to the session; when the session ends it stops. That's fine: next
session, the probe finds it down and you relaunch. Never spawn a second server when the probe says
one is already up — that's the whole point of checking first. Do not offer to "shut it down"
unless the user asks; it's a harmless read-only local server.

## What the user sees, and how to narrate it

Two milestones raise a **pop-up modal** on whatever dashboard page the user has open, so they never
miss the moment: (1) when you finish writing the protocol, the reviews page pops a modal summarizing
it — the user clicks through into the review, which opens on **Search & screening** so they watch the
funnel fill; (2) when the review is done, a modal announces **the report is ready** (or that it's
paused for a decision), landing them on **Findings**. So the beat you're playing into is: write the
protocol (→ the protocol modal fires on its own), then run the search (→ they're watching the funnel
fill). Don't tell the user to go hunt for the Protocol tab — the modal already showed it to them. There
are three stops: **Protocol**, **Search & screening**, and **Findings** (which carries the quality gate
at its top — there's no separate Eval tab). The review view otherwise opens on the stop that matches its
phase (Search & screening in progress, Findings when paused or complete).
