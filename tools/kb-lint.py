#!/usr/bin/env python3
"""kb-lint.py — check the KB against the rules in CLAUDE.md §4–§6, §9 and §11.

Must pass before commit. Errors make the exit code 1; warnings are review
candidates (§10) and do not fail the run.

Errors:
  - front matter missing, or id / title / status / platform missing
  - status or platform not one of the documented values
  - file name does not start with the document's id
  - duplicate ids
  - a related: target, or an id cited in the body, that does not exist
  - related: links that are not reciprocated
  - status source/manual without sources:
  - status tested without a valid verified_on
  - status disputed without a CF- document in related: (CF- documents excepted)

Warnings:
  - status assumed (actively needs validation, §6)
  - status tested with verified_on older than twelve months (§10)
  - linked to an open CF- document (one still disputed) without being disputed
    itself (§9: a conflict is marked everywhere it appears). A closed conflict
    records its outcome and keeps its status from the evidence, e.g. tested.

The front matter parser is kb-index.py's, so both tools read the same thing.

Usage:  python3 tools/kb-lint.py [kb-root]      (default: the repo root)
"""

import datetime
import importlib.util
import os
import re
import sys

sys.dont_write_bytecode = True

HERE = os.path.dirname(os.path.abspath(__file__))
_spec = importlib.util.spec_from_file_location("kb_index", os.path.join(HERE, "kb-index.py"))
kb_index = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(kb_index)

as_list = kb_index.as_list

PLATFORMS = {"mvs38j", "zos", "both"}
STATUSES = set(kb_index.STATUS_ORDER)
STALE_DAYS = 365

# Document ids as defined in CLAUDE.md §5. SRC- ids live in sources/ and are
# checked separately against the catalogue.
ID_RE = re.compile(r"\b(MVS-[A-Z]+-\d{4}|[A-Z]+-ADR-\d{4}|ECO-\d{4}|PB-\d{3,4}"
                   r"|PM-\d{4}-\d{3}|CF-\d{4}-\d{3})\b")
SRC_RE = re.compile(r"\bSRC-\d{3,4}\b")


def source_ids(root):
    ids = set()
    src = os.path.join(root, "sources")
    if os.path.isdir(src):
        for name in os.listdir(src):
            if name.endswith(".md"):
                with open(os.path.join(src, name), encoding="utf-8") as fh:
                    ids.update(re.findall(r"^#{2,3}\s+(SRC-\d+)", fh.read(), re.M))
    return ids


def parse_date(value):
    try:
        return datetime.date.fromisoformat(str(value))
    except ValueError:
        return None


def lint(root, today):
    docs, errors = kb_index.collect(root)
    kb_index.check_links(docs, errors)
    warnings = []
    by_id = {d.get("id"): d for d in docs if d.get("id")}
    src_ids = source_ids(root)

    for d in docs:
        path, did, status = d["_path"], d.get("id"), d.get("status")
        related = as_list(d.get("related"))

        if did and not os.path.basename(path).startswith(did):
            errors.append(f"{path}: file name does not start with id {did}")
        if status and status not in STATUSES:
            errors.append(f"{path}: unknown status '{status}'")
        for plat in as_list(d.get("platform")):
            if plat not in PLATFORMS:
                errors.append(f"{path}: unknown platform '{plat}'")

        if status in ("source", "manual") and not as_list(d.get("sources")):
            errors.append(f"{path}: status {status} without sources:")

        verified = parse_date(d.get("verified_on", ""))
        if status == "tested":
            if verified is None:
                errors.append(f"{path}: status tested without a valid verified_on")
            elif (today - verified).days > STALE_DAYS:
                warnings.append(f"{path}: tested, verified_on {verified} is over "
                                f"twelve months old")

        is_cf = bool(did) and did.startswith("CF-")
        cf_links = [r for r in related if r.startswith("CF-")]
        if status == "disputed" and not is_cf and not any(r in by_id for r in cf_links):
            errors.append(f"{path}: disputed without an existing CF- document in related:")
        open_cfs = [r for r in cf_links if by_id.get(r, {}).get("status") == "disputed"]
        if open_cfs and status != "disputed" and not is_cf:
            warnings.append(f"{path}: linked to open {', '.join(open_cfs)} but status is "
                            f"{status}, not disputed")
        if status == "assumed":
            warnings.append(f"{path}: status assumed — needs validation")

        with open(os.path.join(root, path), encoding="utf-8") as fh:
            body = fh.read()
        for ref in sorted(set(ID_RE.findall(body)) - set(by_id)):
            errors.append(f"{path}: cites {ref}, which does not exist")
        for ref in sorted(set(SRC_RE.findall(body)) - src_ids):
            errors.append(f"{path}: cites {ref}, which is not in sources/")

    return docs, errors, warnings


def main():
    root = sys.argv[1] if len(sys.argv) > 1 else "."
    docs, errors, warnings = lint(root, datetime.date.today())

    print(f"kb-lint: {len(docs)} documents, {len(errors)} error(s), "
          f"{len(warnings)} warning(s)")
    for e in errors:
        print(f"  ERROR    {e}")
    for w in warnings:
        print(f"  warning  {w}")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
