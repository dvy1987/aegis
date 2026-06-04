#!/usr/bin/env python3
"""Apply verified fixer-workflow output to draft case files via targeted raw edits.

Preserves each file's existing formatting (incl. compact critic_verdicts blocks) by
replacing only the changed field values, not re-serializing the whole document.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
DRAFTS = REPO / "eval" / "cases" / "drafts"


def esc(value: str) -> str:
    return json.dumps(value, ensure_ascii=True)[1:-1]


def replace_string_field(raw: str, old: str, new: str, field: str) -> str:
    if old == new:
        return raw
    eo, en = esc(old), esc(new)
    if eo not in raw:
        raise RuntimeError(f"{field}: old value not found for raw replace")
    return raw.replace(eo, en, 1)


def replace_scalar(raw: str, key: str, old, new) -> str:
    if old == new:
        return raw
    pat = re.compile(r'("' + re.escape(key) + r'":\s*)' + re.escape(json.dumps(old)))
    if not pat.search(raw):
        raise RuntimeError(f"{key}: scalar pattern not found")
    return pat.sub(lambda m: m.group(1) + json.dumps(new), raw, count=1)


def apply_one(case_id: str, fix: dict) -> list[str]:
    path = DRAFTS / f"{case_id}.json"
    raw = path.read_text(encoding="utf-8")
    cur = json.loads(raw)
    changed: list[str] = []

    # big string fields
    for field in ("denial_letter_text", "clinical_context"):
        old, new = cur.get(field, ""), fix[field]
        if old != new:
            raw = replace_string_field(raw, old, new, field)
            changed.append(field)

    # patient_profile scalar/string members
    cur_pp, new_pp = cur.get("patient_profile", {}), fix["patient_profile"]
    for k in ("age", "gender", "diagnosis", "treatment_requested", "plan_funding_type"):
        if k not in new_pp:
            continue
        old, new = cur_pp.get(k), new_pp[k]
        if old == new:
            continue
        if isinstance(new, str):
            # replace within patient_profile block to avoid hitting critic evidence quotes
            raw = replace_scalar(raw, k, old, new) if k in ("plan_funding_type",) else _replace_pp_string(raw, k, old, new)
        else:
            raw = replace_scalar(raw, k, old, new)
        changed.append(f"patient_profile.{k}")
        # keep matrix_cell in sync for gender
        if k == "gender":
            try:
                raw = replace_scalar(raw, "patient_gender", old, new)
                changed.append("matrix_cell.patient_gender")
            except RuntimeError:
                pass

    # timestamps
    for field in ("submission_timestamp", "denial_timestamp"):
        old, new = cur.get(field), fix.get(field)
        if old != new:
            raw = replace_scalar(raw, field, old, new)
            changed.append(field)

    path.write_text(raw, encoding="utf-8")
    return changed


def _replace_pp_string(raw: str, key: str, old: str, new: str) -> str:
    # scoped replace: only the occurrence that is the patient_profile member
    pat = re.compile(r'("' + re.escape(key) + r'":\s*)"' + re.escape(esc(old)) + r'"')
    if not pat.search(raw):
        raise RuntimeError(f"patient_profile.{key}: not found")
    return pat.sub(lambda m: m.group(1) + '"' + esc(new) + '"', raw, count=1)


def main() -> None:
    data = json.loads(Path(sys.argv[1]).read_text())
    passed = data["passed"]
    report = []
    for fix in passed:
        cid = fix["case_id"]
        try:
            changed = apply_one(cid, fix)
            report.append((cid, "OK", changed))
        except Exception as e:  # noqa: BLE001
            report.append((cid, f"ERROR: {e}", []))

    ok = [r for r in report if r[1] == "OK"]
    err = [r for r in report if r[1] != "OK"]
    print(f"applied {len(ok)}/{len(passed)} passed fixes")
    from collections import Counter
    fc: Counter = Counter()
    for _, _, ch in ok:
        for c in ch:
            fc[c.split(".")[0] if c.startswith("patient") or c.startswith("matrix") else c] += 1
    print("field change counts:")
    for k, v in fc.most_common():
        print(f"  {v:3d}  {k}")
    if err:
        print("\nERRORS:")
        for cid, msg, _ in err:
            print(f"  {cid}: {msg}")


if __name__ == "__main__":
    main()
