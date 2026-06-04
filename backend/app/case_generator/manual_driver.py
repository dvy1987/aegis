"""Manual driver for the LLM case-generation pipeline (no Vertex/Gemini needed).

There is no Gemini in this environment, so generation is split faithfully:

  * PRODUCERS (P1-P5) are authored by the orchestrating agent (Claude) — the generator.
  * EVALUATORS (every critic + the flaw-injection verifier) run as ISOLATED SUBAGENTS that
    see ONLY the filled critic prompt (artifact + rubric) — never the generator's intent or
    reasoning. This preserves AlphaEval's independent-judge rule (no self-enhancement /
    contamination — the exact failure that made the old aplus "critics" rubber-stamp).

The driver fills each critic prompt EXACTLY as ``llm_agents._run_critic`` would (same
placeholders), so each subagent judges precisely what Gemini would have. Their verdicts are
then fed — in place of the Gemini calls — into the REAL ``llm_pipeline.generate_one_case``,
so every deterministic step (sex guard, per-stage gates, post-P4 checkpoint, P5, text_metrics,
statistical near-dup vs the existing corpus, safety/PHI, full panel, schema, final det+LLM
flaw-integrity) executes faithfully.

Steps (driven by /run-case-generate):
  1. prep    --index N --seed S                     → sample cell+patterns+grounding; inputs.json
  2. (agent authors producers.json: P1-P5 outputs, following prompts/p1..p5)
  3. bundles --producers producers.json            → fill every critic prompt → critics/<dim>.txt
  4. (agent dispatches ONE isolated subagent per critics/<dim>.txt → collects critics.json
      {dim: verdict} and flaws.json {pattern_id: PRESENT|ABSENT})
  5. run     --producers ... --critics ... --flaws ... → real pipeline writes the case (or
      reports exactly which gate failed so the agent fixes its producer outputs and re-judges).
"""
from __future__ import annotations

import argparse
import json
import random
import sys
from pathlib import Path
from typing import Any

from . import clinical_kb, config, llm_pipeline
from .prompts import load_prompt
from .safety import banned_topic_briefs

RUN_DIR = Path("/tmp/manual_run")
DRAFTS = config.REPO_ROOT / "eval" / "cases" / "drafts"
ENVELOPE = load_prompt("_critic_envelope")

PRODUCERS = [
    "run_scenario_planner", "run_denial_drafter", "run_clinical_writer",
    "run_realistic_flaw_injector", "run_stylistic_diversifier",
]
# critic dim -> (prompt_id, [placeholder kwargs it needs]); mirrors llm_agents.critic_* calls.
CRITIC_SPECS: dict[str, tuple[str, list[str]]] = {
    "matrix_coverage": ("c_matrix_coverage", ["assigned_matrix_cell_json", "scenario_brief_json"]),
    "scenario_realism": ("c_scenario_realism", ["scenario_brief_json"]),
    "insurer_voice": ("c_insurer_voice", ["insurer", "denial_letter_text"]),
    "denial_logic": ("c_denial_logic", ["sub_tactic", "sub_tactic_definition", "denial_letter_text"]),
    "clinical_realism": ("c_clinical_realism", ["diagnosis", "treatment_requested", "clinical_context"]),
    "diagnosis_treatment_match": ("c_diagnosis_treatment_match", ["diagnosis", "treatment_requested"]),
    "diversity_delta": ("c_diversity_delta", ["this_case_summary", "neighbour_summaries"]),
    "safety_redactor": ("c_safety_redactor", ["banned_topic_briefs", "denial_letter_text", "clinical_context"]),
    "contradiction_hunter": ("c_contradiction_hunter", ["patient_profile_json", "diagnosis", "treatment_requested", "denial_letter_text", "clinical_context"]),
    "llm_tell_detector": ("c_llm_tell_detector", ["denial_letter_text", "clinical_context"]),
    "overall_tone": ("c_overall_tone", ["denial_letter_text", "clinical_context"]),
    "financial_auditor": ("c_financial_auditor", ["denial_letter_text", "clinical_context"]),
    "legal_auditor": ("c_legal_auditor", ["denial_letter_text", "clinical_context"]),
    "demographic_validator": ("c_demographic_validator", ["patient_profile_json", "denial_letter_text", "clinical_context"]),
    "scope_guard": ("c_scope_guard", ["patient_profile_json", "insurer", "denial_type", "denial_letter_text", "clinical_context"]),
    "date_sanity": ("c_date_sanity", ["denial_letter_text", "clinical_context"]),
    "citation_traceability": ("c_citation_traceability", ["denial_letter_text"]),
    "appeal_difficulty": ("c_appeal_difficulty", ["denial_letter_text", "clinical_context"]),
}


def _fmt(template: str, **kw: Any) -> str:
    for k, v in kw.items():
        template = template.replace(f"{{{k}}}", str(v))
    return template


def _sample(seed: int) -> tuple[dict[str, str], list[dict[str, Any]]]:
    rng = random.Random(seed)
    cell = config.sample_matrix_cell(rng, forbid_cells=set())
    patterns = config.sample_denial_patterns(rng, cell["insurer"], cell["specialty"])
    return cell, patterns


def _neighbour_summaries(specialty: str, limit: int = 12) -> list[str]:
    rows = []
    for p in sorted(DRAFTS.glob("case_*.json")):
        try:
            c = json.loads(p.read_text(encoding="utf-8"))
        except Exception:  # noqa: BLE001
            continue
        mc = (c.get("synthetic_provenance", {}) or {}).get("matrix_cell", {}) or {}
        if mc.get("specialty") != specialty:
            continue
        pp = c.get("patient_profile", {})
        rows.append(f"- [{c.get('insurer')} / {c.get('denial_type')} / {specialty} / "
                    f"{mc.get('sub_tactic')}] dx={pp.get('diagnosis')}; tx={pp.get('treatment_requested')}")
    return rows[-limit:]


def cmd_prep(index: int, seed: int) -> None:
    cell, patterns = _sample(seed)
    RUN_DIR.mkdir(parents=True, exist_ok=True)
    neighbours = _neighbour_summaries(cell["specialty"])
    inputs = {
        "index": index, "seed": seed, "cell": cell,
        "patterns": [{"id": p.get("id"), "description": p.get("description"),
                      "appeal_vector": p.get("appeal_vector"), "source": p.get("source"),
                      "realistic_flaws": p.get("realistic_flaws", [])} for p in patterns],
        "neighbour_summaries": neighbours,
        "sub_tactic_definition": config.sub_tactic_definition(cell["denial_type"], cell["sub_tactic"]),
        "rationale_seed": clinical_kb.rationale_seed(cell["sub_tactic"]),
    }
    (RUN_DIR / "inputs.json").write_text(json.dumps(inputs, indent=2), encoding="utf-8")
    print(f"=== PREP case_{index} (seed={seed}) — inputs.json written ===")
    print(f"MATRIX CELL: {json.dumps(cell)}")
    print(f"\nINTENDED FLAWS ({len(patterns)}) — every one MUST be discoverable in the finished letter/clinical:")
    for p in inputs["patterns"]:
        print(f"  - {p['id']}: {p['description']}\n      appeal_vector: {p['appeal_vector']}")
    print(f"\nSUB-TACTIC: {inputs['sub_tactic_definition']}")
    if inputs["rationale_seed"]:
        print(f"SEED: {inputs['rationale_seed']}")
    print(f"\nCLINICAL-KB GROUNDING (prefer one; respect [sex] tags):\n{clinical_kb.grounding_block(cell['specialty'])}")
    print(f"\nEXISTING {cell['specialty']} CASES — DIVERSIFY AWAY FROM THESE:")
    for n in neighbours:
        print(f"  {n}")
    print("\nNEXT: author /tmp/manual_run/producers.json with keys:", PRODUCERS,
          "\n(follow prompts/p1_scenario_planner..p5_stylistic_diversifier faithfully).")


def _artifacts(producers: dict, inputs: dict) -> dict[str, str]:
    cell = inputs["cell"]
    brief = producers["run_scenario_planner"]
    final = producers["run_stylistic_diversifier"]
    pp = {
        "age": brief["patient_age"], "gender": brief["patient_gender"],
        "diagnosis": final.get("diagnosis", brief["diagnosis"]),
        "treatment_requested": final.get("treatment_requested", brief["treatment_requested"]),
        "plan_funding_type": brief.get("plan_funding_type", "self_funded"),
    }
    summary = (f"- [{cell['insurer']} / {cell['denial_type']} / {cell['specialty']} / "
               f"{cell['sub_tactic']}] dx={pp['diagnosis']}; tx={pp['treatment_requested']}")
    return {
        "assigned_matrix_cell_json": json.dumps(cell, indent=2),
        "scenario_brief_json": json.dumps(brief, indent=2),
        "insurer": cell["insurer"], "denial_type": cell["denial_type"],
        "sub_tactic": cell["sub_tactic"], "sub_tactic_definition": inputs["sub_tactic_definition"],
        "diagnosis": pp["diagnosis"], "treatment_requested": pp["treatment_requested"],
        "patient_profile_json": json.dumps(pp, indent=2),
        "denial_letter_text": final["denial_letter_text"], "clinical_context": final["clinical_context"],
        "this_case_summary": summary,
        "neighbour_summaries": "\n".join(inputs.get("neighbour_summaries", [])) or "(none)",
        "banned_topic_briefs": banned_topic_briefs(),
    }


def cmd_bundles(producers_path: str) -> None:
    inputs = json.loads((RUN_DIR / "inputs.json").read_text(encoding="utf-8"))
    producers = json.loads(Path(producers_path).read_text(encoding="utf-8"))
    art = _artifacts(producers, inputs)
    cdir = RUN_DIR / "critics"
    cdir.mkdir(parents=True, exist_ok=True)
    for dim, (prompt_id, keys) in CRITIC_SPECS.items():
        filled = _fmt(load_prompt(prompt_id), envelope=ENVELOPE, **{k: art[k] for k in keys})
        (cdir / f"{dim}.txt").write_text(filled, encoding="utf-8")
    # flaw-injection verifier — judges ALL intended flaws against the finished prose
    final = producers["run_stylistic_diversifier"]
    to_check = [{"id": p["id"], "description": p["description"], "appeal_vector": p["appeal_vector"]}
                for p in inputs["patterns"]]
    fiv = _fmt(load_prompt("c_flaw_injection_verifier"),
               denial_letter_text=final["denial_letter_text"], clinical_context=final["clinical_context"],
               patterns_to_check=json.dumps(to_check, indent=2),
               submission_timestamp=final.get("submission_timestamp") or "null",
               denial_timestamp=final.get("denial_timestamp") or "null")
    (cdir / "flaw_injection_verifier.txt").write_text(fiv, encoding="utf-8")
    print(f"Wrote {len(CRITIC_SPECS)+1} isolated evaluator prompts to {cdir}/")
    print("Dispatch ONE subagent per file (it must see ONLY that file's content + return the JSON verdict).")
    print("Collect → /tmp/manual_run/critics.json {dim: verdict}  and  flaws.json {pattern_id: PRESENT|ABSENT}")


class _FileBackedAgents:
    """Feeds producer outputs + isolated-subagent critic verdicts into the real pipeline."""

    def __init__(self, producers: dict, critics: dict, flaws: dict):
        self._p, self._c, self._f = producers, critics, flaws

    def __getattr__(self, name: str):
        if name in PRODUCERS:
            if name not in self._p:
                raise KeyError(f"producers.json missing '{name}'")
            return lambda *a, **k: self._p[name]
        if name == "critic_flaw_injection_verifier":
            def _verify(letter, clinical, to_check, **k):
                return {"verification_results": [
                    {"pattern_id": t["id"], "status": self._f.get(t["id"], "PRESENT"),
                     "evidence": "isolated subagent"} for t in to_check]}
            return _verify
        if name.startswith("critic_"):
            dim = name[len("critic_"):]
            def _crit(*a, **k):
                if dim not in self._c:
                    raise KeyError(f"critics.json missing '{dim}'")
                return self._c[dim]
            return _crit
        raise AttributeError(name)


def cmd_run(index: int, seed: int, producers_p: str, critics_p: str, flaws_p: str) -> int:
    producers = json.loads(Path(producers_p).read_text(encoding="utf-8"))
    critics = json.loads(Path(critics_p).read_text(encoding="utf-8"))
    flaws = json.loads(Path(flaws_p).read_text(encoding="utf-8"))
    inputs = json.loads((RUN_DIR / "inputs.json").read_text(encoding="utf-8"))

    llm_pipeline.agents = _FileBackedAgents(producers, critics, flaws)
    case = llm_pipeline.generate_one_case(
        index=index, rng=random.Random(seed), accepted_cells=set(),
        neighbour_summaries=list(inputs.get("neighbour_summaries", [])),
        run_id=llm_pipeline.new_run_id(),
    )
    if case is None:
        print("FAILED: pipeline returned None — a hard gate failed (see warnings above) or it "
              "re-rolled to a new cell the stub can't serve. Fix producers.json / re-judge the "
              "affected critic, then re-run.")
        return 1
    out = DRAFTS / f"{case['case_id']}.json"
    out.write_text(json.dumps(case, indent=2), encoding="utf-8")
    fi = case["synthetic_provenance"]["final_flaw_integrity"]
    div = case["synthetic_provenance"]["critic_verdicts"]["diversity_statistical"]
    print(f"WROTE {out.relative_to(config.REPO_ROOT)}")
    print(f"final_flaw_integrity: aligned={fi['aligned']} method={fi['method']} "
          f"expected={fi['expected_flaws']} absent={fi['absent']}")
    print(f"diversity_statistical: score={div['score']} | {div['reasoning']}")
    return 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="manual_driver")
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("prep"); p.add_argument("--index", type=int, required=True); p.add_argument("--seed", type=int, required=True)
    b = sub.add_parser("bundles"); b.add_argument("--producers", required=True)
    r = sub.add_parser("run")
    r.add_argument("--index", type=int, required=True); r.add_argument("--seed", type=int, required=True)
    r.add_argument("--producers", required=True); r.add_argument("--critics", required=True); r.add_argument("--flaws", required=True)
    args = ap.parse_args(argv)
    if args.cmd == "prep":
        cmd_prep(args.index, args.seed); return 0
    if args.cmd == "bundles":
        cmd_bundles(args.producers); return 0
    return cmd_run(args.index, args.seed, args.producers, args.critics, args.flaws)


if __name__ == "__main__":
    sys.exit(main())
