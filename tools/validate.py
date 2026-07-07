#!/usr/bin/env python
"""Validate every review's protocol.json and records.json against schemas/.

Usage:
    python tools/validate.py            # validate all reviews
    python tools/validate.py <slug>     # validate one review

Also enforces cross-field invariants that JSON Schema can't express cleanly:
- every record's exclusion_reason (when excluded) is in the protocol's exclusion_reasons list
- every record has at least one found_by entry (traceability)
Exit code is non-zero if anything fails.
"""
import sys

from jsonschema import Draft7Validator

import repo


def load(p):
    return repo._read_json(p)


def validate_review(slug, errors):
    revdir = repo.review_dir(slug)
    protocol = records = None

    proto_schema = Draft7Validator(load(repo.SCHEMAS / "protocol.schema.json"))
    rec_schema = Draft7Validator(load(repo.SCHEMAS / "records.schema.json"))

    pp = revdir / "protocol.json"
    if pp.exists():
        protocol = load(pp)
        for e in proto_schema.iter_errors(protocol):
            errors.append(f"[{slug}] protocol.json: {list(e.path)}: {e.message}")

    rp = revdir / "records.json"
    if rp.exists():
        records = load(rp)
        for e in rec_schema.iter_errors(records):
            errors.append(f"[{slug}] records.json: {list(e.path)}: {e.message}")

        allowed = set(protocol.get("exclusion_reasons", [])) if protocol else set()
        profile = (protocol or {}).get("extraction_profile")
        fields = {f["key"]: f for f in profile["fields"]} if profile else {}
        required_fields = [k for k, f in fields.items() if f.get("required")]
        cat_allowed = {k: set(f["categorical"]["values"]) for k, f in fields.items() if f.get("categorical")}

        seen = set()
        for i, r in enumerate(records if isinstance(records, list) else []):
            pmid = r.get("pmid", f"#{i}")
            if pmid in seen:
                errors.append(f"[{slug}] records.json: duplicate pmid {pmid}")
            seen.add(pmid)
            if not r.get("found_by"):
                errors.append(f"[{slug}] records.json: pmid {pmid} has no found_by (traceability)")
            if r.get("status") == "excluded" and allowed:
                reason = r.get("exclusion_reason")
                if reason not in allowed:
                    errors.append(f"[{slug}] records.json: pmid {pmid} exclusion_reason '{reason}' not in protocol list")
            # profile-driven extraction checks (domain fields live in the review, not the engine)
            if r.get("status") == "included" and profile:
                for j, arm in enumerate(r.get("extraction", {}).get("arms", [])):
                    for k in required_fields:
                        if not str(arm.get(k, "")).strip():
                            errors.append(f"[{slug}] records.json: pmid {pmid} arm {j} missing required field '{k}'")
                    for k, vals in cat_allowed.items():
                        if k in arm and arm[k] not in vals:
                            errors.append(f"[{slug}] records.json: pmid {pmid} arm {j} field '{k}'='{arm[k]}' not in profile values {sorted(vals)}")
                    unknown = [k for k in arm if k not in fields]
                    if unknown:
                        errors.append(f"[{slug}] records.json: pmid {pmid} arm {j} has fields not in extraction_profile: {unknown}")
            if r.get("status") == "included" and not profile:
                errors.append(f"[{slug}] protocol.json: has included records but no extraction_profile to validate them against")
            # screening provenance consistency (only when present)
            for st, sc in (r.get("screening") or {}).items():
                out = sc.get("outcome", {}).get("decision")
                if out == "needs-adjudication" and r.get("status") != "needs-adjudication":
                    errors.append(f"[{slug}] records.json: pmid {pmid} {st} outcome is needs-adjudication but status is '{r.get('status')}'")
                if sc.get("agreement") == "conflict" and "adjudication" not in sc and out != "needs-adjudication":
                    errors.append(f"[{slug}] records.json: pmid {pmid} {st} is a conflict resolved without an adjudication record")
            if r.get("status") == "needs-adjudication":
                q = [st for st, sc in (r.get("screening") or {}).items() if sc.get("outcome", {}).get("decision") == "needs-adjudication"]
                if not q:
                    errors.append(f"[{slug}] records.json: pmid {pmid} status needs-adjudication but no stage is awaiting it")


def main():
    slugs = [sys.argv[1]] if len(sys.argv) > 1 else repo.list_reviews()
    if not slugs:
        print("no reviews found")
        return
    errors = []
    for slug in slugs:
        validate_review(slug, errors)
    if errors:
        print(f"FAIL — {len(errors)} problem(s):")
        for e in errors:
            print("  " + e)
        sys.exit(1)
    print(f"OK — validated {len(slugs)} review(s): {', '.join(slugs)}")


if __name__ == "__main__":
    main()
