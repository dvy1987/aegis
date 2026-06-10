import json
from pathlib import Path

root = Path(__file__).resolve().parents[1] / "eval" / "cases" / "drafts"


def load_case(n: int) -> dict:
    matches = sorted(root.glob(f"case_{n}_*.json"))
    if not matches:
        raise FileNotFoundError(n)
    return json.loads(matches[0].read_text(encoding="utf-8"))


def difficulty(data: dict) -> int | None:
    prov = data.get("synthetic_provenance", {}) or {}
    diff = prov.get("appeal_difficulty", {}) or {}
    score = diff.get("score")
    if score is None:
        score = ((prov.get("final_critics") or {}).get("appeal_difficulty") or {}).get("score")
    return score


def weakness_count(data: dict) -> int:
    prov = data.get("synthetic_provenance", {}) or {}
    diff = prov.get("appeal_difficulty", {}) or {}
    ws = diff.get("exploitable_weaknesses") or []
    return len(ws)


rows = []
for n in range(101, 201):
    try:
        data = load_case(n)
    except FileNotFoundError:
        continue
    if data.get("insurer") != "Cigna" or data.get("denial_type") != "Medical Necessity":
        continue
    rows.append(
        {
            "num": n,
            "case_id": data["case_id"],
            "difficulty": difficulty(data),
            "weaknesses": weakness_count(data),
            "treatment": (data.get("patient_profile") or {}).get("treatment_requested", ""),
        }
    )

# Proxy "closest to medium" among score-5: fewer exploitable weaknesses + higher case number spread
rows_sorted = sorted(rows, key=lambda r: (r["weaknesses"], r["num"]))

holdout = rows_sorted[:2]  # fewest weaknesses among easy-rated cases
holdout_ids = {h["case_id"] for h in holdout}
train = [r for r in rows if r["case_id"] not in holdout_ids][:8]

print("RECOMMENDED PREVIEW COHORT (Cigna + Medical Necessity, cases 101-200)")
print("NOTE: No score==3 medium cases exist in this slice; holdout uses closest-to-medium proxy.")
print()
print("quick_holdout (proxy medium):")
for h in holdout:
    print(f"  {h['case_id']}  diff={h['difficulty']}  weaknesses={h['weaknesses']}  {h['treatment'][:60]}")
print()
print("quick_train:")
for t in train:
    print(f"  {t['case_id']}  diff={t['difficulty']}  weaknesses={t['weaknesses']}")
