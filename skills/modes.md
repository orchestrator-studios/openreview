# Skill: choosing a run type (the two research modes)

This workspace does research **two ways**. Every study under `data/reviews/<slug>/` is one or
the other, marked by which definition file it carries:

| Mode | Marker file | For | Skill |
|---|---|---|---|
| **SLR** (systematic review) | `protocol.json` (`mode: slr`) | Exhaustive, defensible coverage of a question — find *every* relevant study and be able to prove it. | `skills/systematic-review.md` |
| **Deep research** | `brief.json` (`mode: research`) | A fast, verified, cited answer across sources — get up to speed or brief a decision, without exhaustive screening. | `skills/deep-research.md` |

## Which to use
- Completeness is the point and the result must be auditable/citable to a reviewer → **SLR**.
- Speed and a synthesised answer are the point, and "did I miss one?" is *not* the bar → **Deep research**.
- When it isn't obvious from the request, ask the user which they want **before** creating the study.

## What's shared vs. what differs
- **Shared shell:** the dashboard/server, the `tools/repo.py` projection interface, `validate.py`,
  the live-dashboard rule, and the one law — *every count that stands for a group is a link*.
- **Differs by mode:** the definition file and data shape, the state machine + quality gate
  (`repo.py` dispatches on mode), the skill, and the rendered view.

Both modes are first-class. Adding a third later is the same move: a new marker file + schema,
a `*_pipeline` in `repo.py`, and a skill — behind the same shell.
