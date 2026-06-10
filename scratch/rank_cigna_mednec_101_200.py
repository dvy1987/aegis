import json
from pathlib import Path

root = Path(__file__).resolve().parents[1] / "eval" / "cases" / "drafts"

rows = []
for n in range(101, 201):
    matches = sorted(root.glob(f"case_{n}_cigna_mednec.json"))
    if not matches:
        continue
    data = json.loads(matches[0].read_text(encoding="utf-8"))
    prov = data.get("synthetic_provenance", {}) or {}
    ad = prov.get("appeal_difficulty") or {}
    fc = (prov.get("final_critics") or {}).get("appeal_difficulty") or {}
    block = fc if fc.get("score") is not None else ad
    rows.append(
        {
            "case_id": data["case_id"],
            "score": block.get("score"),
            "confidence": block.get("confidence"),
            "reasoning": block.get("reasoning", ""),
            "strong_defenses": len(block.get("strong_defenses") or []),
            "exploitable": len(block.get("exploitable_weaknesses") or []),
        }
    )

# Proxy "closest to medium" among score-5: lower confidence, more strong_defenses, reasoning hints
def medium_proxy(r):
    text = r["reasoning"].lower()
    hint = sum(
        kw in text
        for kw in (
            "not guaranteed",
            "genuine",
            "procedurally clean",
            "arguable",
            "medium",
            "harder",
        )
    )
    conf = r["confidence"] if r["confidence"] is not None else 1.0
    return (r["score"], conf, -r["strong_defenses"], -hint, r["exploitable"])

rows.sort(key=medium_proxy)
print("Cigna mednec 101-200 — closest-to-medium proxy (lower = harder appeal):")
for r in rows[:10]:
    print(
        f"  {r['case_id']:28} score={r['score']} conf={r['confidence']} "
        f"defenses={r['strong_defenses']} exploit={r['exploitable']}"
    )
    print(f"    {r['reasoning'][:140]}...")
