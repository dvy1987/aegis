import json
from collections import Counter, defaultdict
from pathlib import Path

root = Path(__file__).resolve().parents[1] / "eval" / "cases" / "drafts"


def load_case(n: int) -> dict | None:
    matches = sorted(root.glob(f"case_{n}_*.json"))
    if not matches:
        return None
    return json.loads(matches[0].read_text(encoding="utf-8"))


def appeal_difficulty_score(data: dict) -> tuple[int | None, str]:
    prov = data.get("synthetic_provenance", {}) or {}

    # Primary: top-level in synthetic_provenance
    diff = prov.get("appeal_difficulty") or {}
    if isinstance(diff.get("score"), int):
        return diff["score"], "synthetic_provenance.appeal_difficulty"

    # Secondary: final_critics block
    critics = prov.get("final_critics") or {}
    cdiff = critics.get("appeal_difficulty") or {}
    if isinstance(cdiff.get("score"), int):
        return cdiff["score"], "synthetic_provenance.final_critics.appeal_difficulty"

    # Tertiary: per-critic dimensions map
    dims = prov.get("critic_dimensions") or prov.get("dimensions") or {}
    if isinstance(dims, dict):
        ad = dims.get("appeal_difficulty") or {}
        if isinstance(ad.get("score"), int):
            return ad["score"], "synthetic_provenance.critic_dimensions.appeal_difficulty"

    return None, "missing"


rows = []
for n in range(101, 201):
    data = load_case(n)
    if not data:
        continue
    score, source = appeal_difficulty_score(data)
    rows.append(
        {
            "num": n,
            "case_id": data.get("case_id"),
            "insurer": data.get("insurer"),
            "denial_type": data.get("denial_type"),
            "score": score,
            "source": source,
            "treatment": (data.get("patient_profile") or {}).get("treatment_requested", "")[:55],
        }
    )

print(f"Cases loaded: {len(rows)}")
print("Overall difficulty distribution:", Counter(r["score"] for r in rows))
print("Missing scores:", sum(1 for r in rows if r["score"] is None))
print()

# By slice
by_slice: dict[tuple, list] = defaultdict(list)
for r in rows:
    by_slice[(r["insurer"], r["denial_type"])].append(r)

print("=== Per slice (insurer + denial_type) ===")
for key in sorted(by_slice):
    cohort = by_slice[key]
    dist = Counter(r["score"] for r in cohort)
    med = [r for r in cohort if r["score"] == 3]
    print(f"{key[0]:6} {key[1]:22} n={len(cohort):2}  scores={dict(dist)}  medium={len(med)}")

print()
print("=== ALL medium (score==3) in 101-200 ===")
medium = [r for r in rows if r["score"] == 3]
for r in sorted(medium, key=lambda x: x["num"]):
    print(f"  {r['case_id']:30} {r['insurer']:6} {r['denial_type']:22}  {r['treatment']}")

print()
print("=== Cigna Medical Necessity medium only ===")
cigna_med = [r for r in medium if r["insurer"] == "Cigna" and r["denial_type"] == "Medical Necessity"]
for r in cigna_med:
    print(f"  {r['case_id']}")

# Also dump raw appeal_difficulty from a few cases that looked score 5 before
print()
print("=== Sample raw appeal_difficulty blocks (Cigna mednec) ===")
for n in [101, 126, 131, 134]:
    data = load_case(n)
    if not data:
        continue
    prov = data.get("synthetic_provenance", {})
    ad = prov.get("appeal_difficulty")
    fc = (prov.get("final_critics") or {}).get("appeal_difficulty")
    print(f"case_{n}: top-level={ad!r:.120}" if False else f"case_{n}:")
    print(f"  top-level score: {(ad or {}).get('score')}")
    print(f"  final_critics score: {(fc or {}).get('score')}")
