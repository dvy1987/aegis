import json
from collections import Counter
from pathlib import Path

root = Path(__file__).resolve().parents[1] / "eval" / "cases" / "drafts"
rows = []
for n in range(101, 201):
    matches = sorted(root.glob(f"case_{n}_*.json"))
    if not matches:
        matches = sorted(root.glob(f"case_{n:02d}_*.json"))
    if not matches:
        continue
    p = matches[0]
    data = json.loads(p.read_text(encoding="utf-8"))
    prov = data.get("synthetic_provenance", {}) or {}
    diff = prov.get("appeal_difficulty", {}) or {}
    score = diff.get("score")
    if score is None:
        diff2 = (prov.get("final_critics") or {}).get("appeal_difficulty") or {}
        score = diff2.get("score")
    rows.append(
        {
            "case_id": data.get("case_id", p.stem),
            "num": n,
            "insurer": data.get("insurer"),
            "denial_type": data.get("denial_type"),
            "difficulty": score,
            "treatment": (data.get("patient_profile") or {}).get("treatment_requested", ""),
            "diagnosis": (data.get("patient_profile") or {}).get("diagnosis", ""),
        }
    )

print(f"Total cases found in 101-200: {len(rows)}")
print()

slices = Counter((r["insurer"], r["denial_type"]) for r in rows)
print("Slice counts:")
for k, v in sorted(slices.items()):
    print(f"  {k[0]:12} {k[1]:22} -> {v}")
print()

cigna = [r for r in rows if r["insurer"] == "Cigna" and r["denial_type"] == "Medical Necessity"]
print(f"Cigna Medical Necessity: {len(cigna)}")
print("Difficulty distribution:", Counter(r["difficulty"] for r in cigna))
print()
print("All Cigna mednec (sorted by difficulty, then case num):")
for r in sorted(cigna, key=lambda x: (x["difficulty"] if x["difficulty"] is not None else 99, x["num"])):
    print(f"  {r['case_id']:28} diff={r['difficulty']}  {r['treatment'][:55]}")

medium = [r for r in cigna if r["difficulty"] == 3]
print(f"\nMedium (score==3) Cigna mednec: {len(medium)}")
for r in sorted(medium, key=lambda x: x["num"]):
    print(f"  {r['case_id']:28} {r['treatment'][:50]}")

print("\n=== Slice analysis for 10-case preview cohorts ===")
for insurer in ("Aetna", "Cigna", "UHC"):
    for denial in ("Medical Necessity", "Prior Authorization"):
        cohort = [r for r in rows if r["insurer"] == insurer and r["denial_type"] == denial]
        if not cohort:
            continue
        med = [r for r in cohort if r["difficulty"] == 3]
        easy = [r for r in cohort if r["difficulty"] == 5]
        hard = [r for r in cohort if r["difficulty"] == 1]
        print(
            f"{insurer:6} {denial:22} total={len(cohort):2}  med={len(med):2} easy={len(easy):2} hard={len(hard):2}"
            + ("  **CAN DO 10**" if len(cohort) >= 10 and len(med) >= 2 else "")
        )

print("\n=== Best single-slice cohorts (>=10 cases, >=2 medium holdout candidates) ===")
for insurer in ("Aetna", "Cigna", "UHC"):
    for denial in ("Medical Necessity", "Prior Authorization"):
        cohort = [r for r in rows if r["insurer"] == insurer and r["denial_type"] == denial]
        med = sorted([r for r in cohort if r["difficulty"] == 3], key=lambda x: x["num"])
        if len(cohort) < 10 or len(med) < 2:
            continue
        train_pool = sorted([r for r in cohort if r["difficulty"] != 3], key=lambda x: x["num"])
        if len(train_pool) < 8:
            train_pool = sorted(cohort, key=lambda x: x["num"])
            holdout = med[:2]
            train = [r for r in train_pool if r["case_id"] not in {h["case_id"] for h in holdout}][:8]
        else:
            holdout = med[:2]
            train = train_pool[:8]
        print(f"\n{insurer} + {denial}:")
        print("  holdout:", ", ".join(h["case_id"] for h in holdout))
        print("  train:  ", ", ".join(t["case_id"] for t in train))
