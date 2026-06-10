import json
from pathlib import Path

root = Path(__file__).resolve().parents[1] / "eval" / "cases" / "drafts"
train = [
    "case_101_cigna_mednec",
    "case_116_cigna_mednec",
    "case_132_cigna_mednec",
    "case_145_cigna_mednec",
    "case_184_cigna_mednec",
]
holdout = ["case_126_cigna_mednec", "case_131_cigna_mednec"]

for role, ids in [("TRAIN", train), ("HOLDOUT", holdout)]:
    print(f"\n=== {role} ===")
    for cid in ids:
        data = json.loads((root / f"{cid}.json").read_text(encoding="utf-8"))
        dp = data.get("denial_pattern") or {}
        prof = data.get("patient_profile") or {}
        print(
            f"  {cid}\n"
            f"    insurer:      {data.get('insurer')}\n"
            f"    denial_type:  {data.get('denial_type')}\n"
            f"    sub_tactic:   {dp.get('sub_tactic', '?')}\n"
            f"    specialty:    {dp.get('specialty', prof.get('specialty', '?'))}\n"
            f"    treatment:    {(prof.get('treatment_requested') or '')[:70]}"
        )
