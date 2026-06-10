import json
from collections import Counter, defaultdict
from pathlib import Path

root = Path(__file__).resolve().parents[1] / "eval" / "cases" / "drafts"

current_train = [
    "case_101_cigna_mednec",
    "case_116_cigna_mednec",
    "case_132_cigna_mednec",
    "case_145_cigna_mednec",
    "case_184_cigna_mednec",
]
current_holdout = ["case_126_cigna_mednec", "case_131_cigna_mednec"]


def load(cid: str) -> dict:
    return json.loads((root / f"{cid}.json").read_text(encoding="utf-8"))


def matrix_cell(data: dict) -> dict:
    return (data.get("synthetic_provenance") or {}).get("matrix_cell") or {}


rows = []
for n in range(101, 201):
    matches = sorted(root.glob(f"case_{n}_cigna_mednec.json"))
    if not matches:
        continue
    data = json.loads(matches[0].read_text(encoding="utf-8"))
    cell = matrix_cell(data)
    rows.append(
        {
            "case_id": data["case_id"],
            "n": n,
            "sub_tactic": cell.get("sub_tactic", "?"),
            "specialty": cell.get("specialty", "?"),
        }
    )

by_tactic = defaultdict(list)
for r in rows:
    by_tactic[r["sub_tactic"]].append(r)

print("=== Cigna mednec 101-200: sub_tactic counts ===")
for tactic, cohort in sorted(by_tactic.items(), key=lambda x: (-len(x[1]), x[0])):
    print(f"  {tactic:28} n={len(cohort):2}  {', '.join(c['case_id'].replace('_cigna_mednec','') for c in cohort[:8])}{'...' if len(cohort)>8 else ''}")

print("\n=== Current holdout coverage in training ===")
for hid in current_holdout:
    h = load(hid)
    ht = matrix_cell(h).get("sub_tactic")
    matches = [c for c in current_train if matrix_cell(load(c)).get("sub_tactic") == ht]
    print(f"  {hid} sub_tactic={ht}")
    print(f"    training matches ({len(matches)}): {matches}")

print("\n=== Holdout candidates with >=2 train partners in pool (excluding holdout) ===")
for tactic, cohort in sorted(by_tactic.items()):
    if len(cohort) >= 3:  # 2 train + 1 holdout possible
        print(f"  {tactic}: {len(cohort)} cases total — can pick 2 train + 1 holdout")
