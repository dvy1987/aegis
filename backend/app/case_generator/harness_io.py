"""State-machine helper for manual AlphaEval case generation.

Enforces the staged generator-evaluator architecture of llm_pipeline.py
without requiring Vertex AI / Gemini API calls.
"""

from __future__ import annotations

import argparse
import json
import random
import sys
from pathlib import Path
from typing import Any
import uuid
from datetime import UTC, datetime

from . import clinical_kb, config, flaw_verifier, stats_evaluator
from .prompts import load_prompt
from .safety import banned_topic_briefs, scan_banned, scan_phi
from .text_metrics import fit_letter_word_budget, repair_denial_letter_artifacts
from .manual_assemble import assemble_case

from .manual_assemble import assemble_case

RUN_DIR = Path("/tmp/harness")
DRAFTS = config.REPO_ROOT / "eval" / "cases" / "drafts"
STATE_FILE = RUN_DIR / "state.json"
ENVELOPE = load_prompt("_critic_envelope")

def load_state() -> dict[str, Any]:
    if STATE_FILE.exists():
        return json.loads(STATE_FILE.read_text(encoding="utf-8"))
    return {"scenario_retries": 0, "stage1_retries": 0, "stage2_retries": 0, "stage3_retries": 0, "p4_retries": 0, "seed": 0}

def save_state(st: dict[str, Any]) -> None:
    STATE_FILE.write_text(json.dumps(st, indent=2), encoding="utf-8")

def _fmt(template: str, **kw: Any) -> str:
    for k, v in kw.items():
        template = template.replace(f"{{{k}}}", str(v))
    return template

def _sample(seed: int) -> tuple[dict[str, str], list[dict[str, Any]]]:
    accepted_cells = set()
    for p in DRAFTS.glob("case_*.json"):
        try:
            c = json.loads(p.read_text(encoding="utf-8"))
            mc = c.get("synthetic_provenance", {}).get("matrix_cell", {})
            if mc:
                accepted_cells.add((mc.get("insurer"), mc.get("denial_type"), mc.get("specialty"), mc.get("sub_tactic")))
        except Exception:
            continue
            
    rng = random.Random(seed)
    cell = config.sample_matrix_cell(rng, forbid_cells=accepted_cells)
    patterns = config.sample_denial_patterns(rng, cell["insurer"], cell["specialty"])
    return cell, patterns

def _neighbour_summaries(specialty: str, limit: int = 12) -> list[str]:
    rows = []
    for p in sorted(DRAFTS.glob("case_*.json")):
        try:
            c = json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            continue
        mc = (c.get("synthetic_provenance", {}) or {}).get("matrix_cell", {}) or {}
        if mc.get("specialty") != specialty:
            continue
        pp = c.get("patient_profile", {})
        rows.append(f"- [{c.get('insurer')} / {c.get('denial_type')} / {specialty} / "
                    f"{mc.get('sub_tactic')}] dx={pp.get('diagnosis')}; tx={pp.get('treatment_requested')}")
    return rows[-limit:]

def write_prompts(stage_name: str, prompts: dict[str, str]) -> None:
    cdir = RUN_DIR / "critics" / stage_name
    cdir.mkdir(parents=True, exist_ok=True)
    for name, content in prompts.items():
        (cdir / f"{name}.txt").write_text(content, encoding="utf-8")
    print(f"[{stage_name}] Wrote {len(prompts)} critic prompts to {cdir}/")

# --- STAGE COMMANDS ---

def cmd_stage1_prep(index: int, seed: int, is_retry: bool = False) -> None:
    RUN_DIR.mkdir(parents=True, exist_ok=True)
    st = load_state() if is_retry else {"scenario_retries": 0, "stage1_retries": 0, "stage2_retries": 0, "stage3_retries": 0, "p4_retries": 0, "seed": seed}
    
    if st["scenario_retries"] >= 4:
        print("HARD FAIL: Max scenario retries (4) exceeded. Giving up on this case entirely.")
        sys.exit(1)
        
    actual_seed = st["seed"] + st["scenario_retries"]
    cell, patterns = _sample(actual_seed)
    
    neighbours = _neighbour_summaries(cell["specialty"])
    inputs = {
        "index": index, "seed": seed, "cell": cell,
        "patterns": [{"id": p.get("id"), "description": p.get("description"),
                      "appeal_vector": p.get("appeal_vector")} for p in patterns],
        "neighbour_summaries": neighbours,
        "sub_tactic_definition": config.sub_tactic_definition(cell["denial_type"], cell["sub_tactic"]),
        "rationale_seed": clinical_kb.rationale_seed(cell["sub_tactic"]),
        "grounding_block": clinical_kb.grounding_block(cell["specialty"]),
        "specialty_examples": config.specialty_examples(cell["specialty"]),
        "joint_constraints": config.joint_constraints_text()
    }
    (RUN_DIR / "inputs.json").write_text(json.dumps(inputs, indent=2), encoding="utf-8")
    save_state(st)
    print(f"=== PREP case_{index} (seed={actual_seed}, attempt={st['scenario_retries']+1}/4) ===\nInputs written to {RUN_DIR}/inputs.json\nAgent should now run P1.")

def cmd_stage1_verify(critics_path: str) -> None:
    critics = json.loads(Path(critics_path).read_text(encoding="utf-8"))
    st = load_state()
    inputs = json.loads((RUN_DIR / "inputs.json").read_text(encoding="utf-8"))
    
    s_mc = critics.get("matrix_coverage", {}).get("score")
    s_sr = critics.get("scenario_realism", {}).get("score")
    
    if s_mc == 1 or s_sr == 1:
        st["stage1_retries"] += 1
        if st["stage1_retries"] >= 2:
            print("STAGE 1 FAILED 2 RETRIES. Discarding scenario and re-rolling Phase 0...")
            st["scenario_retries"] += 1
            st["stage1_retries"] = 0
            save_state(st)
            cmd_stage1_prep(inputs["index"], st["seed"], is_retry=True)
            sys.exit(2)
        else:
            save_state(st)
            print(f"STAGE 1 CRITIC FAILED (Score 1). Retry {st['stage1_retries']}/2. Agent must re-draft P1.")
            sys.exit(3)
    
    print("STAGE 1 PASS. Proceed to P2.")

def cmd_stage1_eval(brief_path: str) -> None:
    inputs = json.loads((RUN_DIR / "inputs.json").read_text(encoding="utf-8"))
    brief = json.loads(Path(brief_path).read_text(encoding="utf-8"))
    
    # Enforce sex guard deterministic check
    req_sex = clinical_kb.required_sex(brief.get("diagnosis", ""), brief.get("treatment_requested", ""))
    if req_sex and brief.get("patient_gender") != req_sex:
        print(f"WARNING: Deterministic Sex Guard triggered! Overriding gender to {req_sex}.")
        brief["patient_gender"] = req_sex
        Path(brief_path).write_text(json.dumps(brief, indent=2), encoding="utf-8")
        
    prompts = {
        "matrix_coverage": _fmt(load_prompt("c_matrix_coverage"), envelope=ENVELOPE, 
                                assigned_matrix_cell_json=json.dumps(inputs["cell"], indent=2), 
                                scenario_brief_json=json.dumps(brief, indent=2)),
        "scenario_realism": _fmt(load_prompt("c_scenario_realism"), envelope=ENVELOPE, 
                                 scenario_brief_json=json.dumps(brief, indent=2))
    }
    write_prompts("stage1", prompts)

def cmd_stage2_eval(brief_path: str, letter_path: str) -> None:
    inputs = json.loads((RUN_DIR / "inputs.json").read_text(encoding="utf-8"))
    brief = json.loads(Path(brief_path).read_text(encoding="utf-8"))
    letter = json.loads(Path(letter_path).read_text(encoding="utf-8"))["denial_letter_text"]
    prompts = {
        "insurer_voice": _fmt(load_prompt("c_insurer_voice"), envelope=ENVELOPE, 
                              insurer=inputs["cell"]["insurer"], denial_letter_text=letter),
        "denial_logic": _fmt(load_prompt("c_denial_logic"), envelope=ENVELOPE, 
                             sub_tactic=inputs["cell"]["sub_tactic"], 
                             sub_tactic_definition=inputs["sub_tactic_definition"], 
                             denial_letter_text=letter)
    }
    write_prompts("stage2", prompts)

def cmd_stage2_verify(critics_path: str) -> None:
    critics = json.loads(Path(critics_path).read_text(encoding="utf-8"))
    st = load_state()
    
    s_iv = critics.get("insurer_voice", {}).get("score")
    s_dl = critics.get("denial_logic", {}).get("score")
    
    if s_iv == 1 or s_dl == 1:
        st["stage2_retries"] += 1
        save_state(st)
        if st["stage2_retries"] >= 2:
            print("STAGE 2 FAILED 2 RETRIES. Reached max revisions, proceeding anyway (per pipeline rules). Proceed to P3.")
            sys.exit(0)
        else:
            print(f"STAGE 2 CRITIC FAILED (Score 1). Retry {st['stage2_retries']}/2. Agent must re-draft P2.")
            sys.exit(3)
            
    print("STAGE 2 PASS. Proceed to P3.")

def cmd_stage3_eval(brief_path: str, context_path: str) -> None:
    brief = json.loads(Path(brief_path).read_text(encoding="utf-8"))
    ctx = json.loads(Path(context_path).read_text(encoding="utf-8"))["clinical_context"]
    prompts = {
        "clinical_realism": _fmt(load_prompt("c_clinical_realism"), envelope=ENVELOPE, 
                                 diagnosis=brief["diagnosis"], treatment_requested=brief["treatment_requested"], 
                                 clinical_context=ctx),
        "diagnosis_treatment_match": _fmt(load_prompt("c_diagnosis_treatment_match"), envelope=ENVELOPE, 
                                          diagnosis=brief["diagnosis"], treatment_requested=brief["treatment_requested"])
    }
    write_prompts("stage3", prompts)

def cmd_stage3_verify(critics_path: str) -> None:
    critics = json.loads(Path(critics_path).read_text(encoding="utf-8"))
    st = load_state()
    
    s_cr = critics.get("clinical_realism", {}).get("score")
    s_dtm = critics.get("diagnosis_treatment_match", {}).get("score")
    
    if s_cr == 1 or s_dtm == "FAIL":
        st["stage3_retries"] += 1
        save_state(st)
        if st["stage3_retries"] >= 2:
            print("STAGE 3 FAILED 2 RETRIES. Reached max revisions, proceeding anyway (per pipeline rules). Proceed to P4.")
            sys.exit(0)
        else:
            print(f"STAGE 3 CRITIC FAILED (Score 1 / FAIL). Retry {st['stage3_retries']}/2. Agent must re-draft P3.")
            sys.exit(3)
            
    print("STAGE 3 PASS. Proceed to P4.")

def cmd_stage4_det_check(brief_path: str, p4_path: str) -> None:
    inputs = json.loads((RUN_DIR / "inputs.json").read_text(encoding="utf-8"))
    brief = json.loads(Path(brief_path).read_text(encoding="utf-8"))
    p4 = json.loads(Path(p4_path).read_text(encoding="utf-8"))
    pattern_ids = [p["id"] for p in inputs["patterns"]]
    
    fv = flaw_verifier.verify_flaws(
        denial_letter_text=p4["denial_letter_text"],
        clinical_context=p4["clinical_context"],
        pattern_ids=pattern_ids,
        submission_timestamp=p4.get("submission_timestamp"),
        denial_timestamp=p4.get("denial_timestamp"),
        specialty=inputs["cell"]["specialty"],
        plan_funding_type=brief.get("plan_funding_type")
    )
    
    print(f"=== STAGE 4 DETERMINISTIC CHECK ===")
    print(f"Present: {fv['present']}")
    print(f"Needs LLM: {fv['needs_llm']}")
    print(f"Absent: {fv['absent']}")
    if fv["absent"]:
        st = load_state()
        st["p4_retries"] += 1
        if st["p4_retries"] >= 2:
            print("HARD FAIL: P4 failed 2 targeted re-injections. Discarding scenario and re-rolling Phase 0...")
            st["scenario_retries"] += 1
            st["p4_retries"] = 0
            save_state(st)
            cmd_stage1_prep(inputs["index"], st["seed"], is_retry=True)
            sys.exit(2)
        else:
            save_state(st)
            print(f"\nHARD FAIL: Flaws are absent deterministically. Retry {st['p4_retries']}/2. Agent MUST re-run P4 injection.")
            sys.exit(3)
    else:
        print("\nPASS: No deterministic flaws absent. Proceed to P5.")

def cmd_stage5_eval(brief_path: str, final_path: str) -> None:
    inputs = json.loads((RUN_DIR / "inputs.json").read_text(encoding="utf-8"))
    brief = json.loads(Path(brief_path).read_text(encoding="utf-8"))
    final = json.loads(Path(final_path).read_text(encoding="utf-8"))
    
    # Text Metrics Deterministic Guard
    original_len = len(final["denial_letter_text"].split())
    repaired = repair_denial_letter_artifacts(final["denial_letter_text"])
    fitted = fit_letter_word_budget(repaired)
    final["denial_letter_text"] = fitted
    if original_len != len(fitted.split()):
        print("NOTE: Applied text_metrics budget/trimming to denial letter.")
        Path(final_path).write_text(json.dumps(final, indent=2), encoding="utf-8")
        
    # Safety and PHI Deterministic Guard
    banned_hits = scan_banned(final["denial_letter_text"] + "\n" + final["clinical_context"])
    phi_hits = scan_phi(final["denial_letter_text"] + "\n" + final["clinical_context"])
    if banned_hits or phi_hits:
        print("HARD FAIL: Deterministic Safety/PHI check failed. Discarding scenario and re-rolling Phase 0...")
        st = load_state()
        st["scenario_retries"] += 1
        save_state(st)
        cmd_stage1_prep(inputs["index"], st["seed"], is_retry=True)
        sys.exit(2)
        
    # Statistical Diversity Guard
    short = "mednec" if inputs["cell"]["denial_type"] == "Medical Necessity" else "priorauth"
    case_id = f"case_{inputs['index']:02d}_{inputs['cell']['insurer'].lower()}_{short}"
    
    neighbour_texts = []
    for p in DRAFTS.glob("case_*.json"):
        try:
            c = json.loads(p.read_text(encoding="utf-8"))
            if c.get("case_id") != case_id:
                neighbour_texts.append(c.get("denial_letter_text", "") + "\n" + c.get("clinical_context", ""))
        except Exception:
            continue

    div_metrics = stats_evaluator.diversity_metrics(
        denial_letter_text=final["denial_letter_text"],
        clinical_context=final["clinical_context"],
        neighbour_texts=neighbour_texts,
        corpus=stats_evaluator.corpus_trigrams(DRAFTS),
        exclude_case_id=case_id
    )
    div_verdict = stats_evaluator.diversity_verdict(div_metrics)
    if div_verdict["score"] == 1:
        print("HARD FAIL: Statistical Diversity check failed (duplicate case). Discarding scenario and re-rolling Phase 0...")
        st = load_state()
        st["scenario_retries"] += 1
        save_state(st)
        cmd_stage1_prep(inputs["index"], st["seed"], is_retry=True)
        sys.exit(2)
    
    summary = f"- [{inputs['cell']['insurer']} / {inputs['cell']['denial_type']} / {inputs['cell']['specialty']} / {inputs['cell']['sub_tactic']}] dx={final.get('diagnosis', brief['diagnosis'])}; tx={final.get('treatment_requested', brief['treatment_requested'])}"
    
    # Flaw Verifier (mid-pipeline target: only needs_llm)
    pattern_ids = [p["id"] for p in inputs["patterns"]]
    fv = flaw_verifier.verify_flaws(
        denial_letter_text=final["denial_letter_text"],
        clinical_context=final["clinical_context"],
        pattern_ids=pattern_ids,
        submission_timestamp=final.get("submission_timestamp"),
        denial_timestamp=final.get("denial_timestamp"),
        specialty=inputs["cell"]["specialty"],
        plan_funding_type=brief.get("plan_funding_type")
    )
    needs_llm_patterns = [p for p in inputs["patterns"] if p["id"] in fv["needs_llm"]]
    
    prompts = {
        "diversity_delta": _fmt(load_prompt("c_diversity_delta"), envelope=ENVELOPE, 
                                this_case_summary=summary, 
                                neighbour_summaries="\n".join(inputs.get("neighbour_summaries", [])) or "(none)"),
        "safety_redactor": _fmt(load_prompt("c_safety_redactor"), envelope=ENVELOPE, 
                                banned_topic_briefs=banned_topic_briefs(), 
                                denial_letter_text=final["denial_letter_text"], 
                                clinical_context=final["clinical_context"]),
        "flaw_injection_verifier_mid": _fmt(load_prompt("c_flaw_injection_verifier"), envelope=ENVELOPE, 
                                        denial_letter_text=final["denial_letter_text"], 
                                        clinical_context=final["clinical_context"], 
                                        patterns_to_check=json.dumps(needs_llm_patterns, indent=2), 
                                        submission_timestamp=final.get("submission_timestamp", "null"), 
                                        denial_timestamp=final.get("denial_timestamp", "null"))
    }
    write_prompts("stage5", prompts)

def cmd_stage5_verify(brief_path: str, final_path: str, critics_path: str) -> None:
    inputs = json.loads((RUN_DIR / "inputs.json").read_text(encoding="utf-8"))
    brief = json.loads(Path(brief_path).read_text(encoding="utf-8"))
    final = json.loads(Path(final_path).read_text(encoding="utf-8"))
    critics = json.loads(Path(critics_path).read_text(encoding="utf-8"))
    st = load_state()
    
    # 1. Semantic Safety Check
    if critics.get("safety_redactor", {}).get("score") == 1:
        print("HARD FAIL: Semantic Safety check failed. Discarding scenario and re-rolling Phase 0...")
        st["scenario_retries"] += 1
        save_state(st)
        cmd_stage1_prep(inputs["index"], st["seed"], is_retry=True)
        sys.exit(2)
        
    # 2. Phase 7 Flaw Injection Check (Union of deterministic absent + LLM absent)
    fv = flaw_verifier.verify_flaws(
        denial_letter_text=final["denial_letter_text"],
        clinical_context=final["clinical_context"],
        pattern_ids=[p["id"] for p in inputs["patterns"]],
        submission_timestamp=final.get("submission_timestamp"),
        denial_timestamp=final.get("denial_timestamp"),
        specialty=inputs["cell"]["specialty"],
        plan_funding_type=brief.get("plan_funding_type")
    )
    
    fv_mid = critics.get("flaw_injection_verifier_mid", {})
    llm_absent = [r["pattern_id"] for r in fv_mid.get("verification_results", []) if r.get("status") == "ABSENT"]
    final_absent = sorted(set(fv["absent"]) | set(llm_absent))
    
    if final_absent:
        st["stage5_retries"] = st.get("stage5_retries", 0) + 1
        if st["stage5_retries"] >= 2:
            print(f"HARD FAIL: Stage 5 Flaw Injection failed 2 retries (Absent: {final_absent}). Discarding scenario...")
            st["scenario_retries"] += 1
            st["stage5_retries"] = 0
            save_state(st)
            cmd_stage1_prep(inputs["index"], st["seed"], is_retry=True)
            sys.exit(2)
        else:
            save_state(st)
            print(f"STAGE 5 FLAW VERIFIER FAILED. Absent: {final_absent}. Retry {st['stage5_retries']}/2. Agent must re-inject flaws and re-run P5.")
            sys.exit(3)
            
    print("STAGE 5 PASS (Flaw Integrity + Safety Verified). Proceed to Final Panel.")

def cmd_final_panel(brief_path: str, final_path: str) -> None:
    inputs = json.loads((RUN_DIR / "inputs.json").read_text(encoding="utf-8"))
    brief = json.loads(Path(brief_path).read_text(encoding="utf-8"))
    final = json.loads(Path(final_path).read_text(encoding="utf-8"))
    
    pp = {
        "age": brief["patient_age"], "gender": brief["patient_gender"],
        "diagnosis": final.get("diagnosis", brief["diagnosis"]),
        "treatment_requested": final.get("treatment_requested", brief["treatment_requested"]),
        "plan_funding_type": brief.get("plan_funding_type", "self_funded"),
    }
    
    prompts = {
        "contradiction_hunter": _fmt(load_prompt("c_contradiction_hunter"), envelope=ENVELOPE, patient_profile_json=json.dumps(pp, indent=2), diagnosis=pp["diagnosis"], treatment_requested=pp["treatment_requested"], denial_letter_text=final["denial_letter_text"], clinical_context=final["clinical_context"]),
        "llm_tell_detector": _fmt(load_prompt("c_llm_tell_detector"), envelope=ENVELOPE, denial_letter_text=final["denial_letter_text"], clinical_context=final["clinical_context"]),
        "overall_tone": _fmt(load_prompt("c_overall_tone"), envelope=ENVELOPE, denial_letter_text=final["denial_letter_text"], clinical_context=final["clinical_context"]),
        "financial_auditor": _fmt(load_prompt("c_financial_auditor"), envelope=ENVELOPE, denial_letter_text=final["denial_letter_text"], clinical_context=final["clinical_context"]),
        "legal_auditor": _fmt(load_prompt("c_legal_auditor"), envelope=ENVELOPE, denial_letter_text=final["denial_letter_text"], clinical_context=final["clinical_context"]),
        "demographic_validator": _fmt(load_prompt("c_demographic_validator"), envelope=ENVELOPE, patient_profile_json=json.dumps(pp, indent=2), denial_letter_text=final["denial_letter_text"], clinical_context=final["clinical_context"]),
        "scope_guard": _fmt(load_prompt("c_scope_guard"), envelope=ENVELOPE, patient_profile_json=json.dumps(pp, indent=2), insurer=inputs["cell"]["insurer"], denial_type=inputs["cell"]["denial_type"], denial_letter_text=final["denial_letter_text"], clinical_context=final["clinical_context"]),
        "date_sanity": _fmt(load_prompt("c_date_sanity"), envelope=ENVELOPE, denial_letter_text=final["denial_letter_text"], clinical_context=final["clinical_context"]),
        "citation_traceability": _fmt(load_prompt("c_citation_traceability"), envelope=ENVELOPE, denial_letter_text=final["denial_letter_text"]),
        "appeal_difficulty": _fmt(load_prompt("c_appeal_difficulty"), envelope=ENVELOPE, denial_letter_text=final["denial_letter_text"], clinical_context=final["clinical_context"]),
        
        # FINAL flaw integrity (llm_all=True): LLM independently rechecks ALL flaws at the end
        "flaw_injection_verifier_final": _fmt(load_prompt("c_flaw_injection_verifier"), envelope=ENVELOPE, 
                                              denial_letter_text=final["denial_letter_text"], 
                                              clinical_context=final["clinical_context"], 
                                              patterns_to_check=json.dumps(inputs["patterns"], indent=2), 
                                              submission_timestamp=final.get("submission_timestamp", "null"), 
                                              denial_timestamp=final.get("denial_timestamp", "null"))
    }
    write_prompts("final_panel", prompts)

def cmd_assemble(index: int, brief_path: str, final_path: str, all_critics_path: str) -> None:
    inputs = json.loads((RUN_DIR / "inputs.json").read_text(encoding="utf-8"))
    brief = json.loads(Path(brief_path).read_text(encoding="utf-8"))
    final = json.loads(Path(final_path).read_text(encoding="utf-8"))
    critics = json.loads(Path(all_critics_path).read_text(encoding="utf-8"))
    
    pp = {
        "age": brief["patient_age"], "gender": brief["patient_gender"],
        "diagnosis": final.get("diagnosis", brief["diagnosis"]),
        "treatment_requested": final.get("treatment_requested", brief["treatment_requested"]),
        "plan_funding_type": brief.get("plan_funding_type", "self_funded"),
    }
    
    stamp = datetime.now(UTC).strftime("%Y%m%d-%H%M%S")
    run_id = f"manual-harness-{stamp}-{uuid.uuid4().hex[:5]}"
    
    # Flaw verification translation (Final LLM check + Det check)
    fv_mid = critics.get("flaw_injection_verifier_mid", {})
    fv_final = critics.get("flaw_injection_verifier_final", {})
    
    pattern_ids = [p["id"] for p in inputs["patterns"]]
    det_fv = flaw_verifier.verify_flaws(
        denial_letter_text=final["denial_letter_text"],
        clinical_context=final["clinical_context"],
        pattern_ids=pattern_ids,
        submission_timestamp=final.get("submission_timestamp"),
        denial_timestamp=final.get("denial_timestamp"),
        specialty=inputs["cell"]["specialty"],
        plan_funding_type=brief.get("plan_funding_type")
    )
    
    llm_absent = [r["pattern_id"] for r in fv_final.get("verification_results", []) if r.get("status") == "ABSENT"]
    final_absent = sorted(set(det_fv["absent"]) | set(llm_absent))
    
    critics["final_flaw_integrity"] = {
        "method": "deterministic+llm(all)",
        "expected_flaws": pattern_ids,
        "deterministic_present": det_fv["present"],
        "llm_absent": llm_absent,
        "absent": final_absent,
        "aligned": not final_absent
    }

    try:
        final_case = assemble_case(
            index=index,
            matrix_cell=inputs["cell"],
            patient_profile=pp,
            denial_letter_text=final["denial_letter_text"],
            clinical_context=final["clinical_context"],
            denial_pattern_sources=flaw_verifier.format_pattern_sources(inputs["patterns"]),
            critic_verdicts=critics,
            run_id=run_id,
            submission_timestamp=final.get("submission_timestamp"),
            denial_timestamp=final.get("denial_timestamp")
        )
    except Exception as e:
        print(f"Validation failed: {e}")
        sys.exit(1)
        
    if final_absent:
        print(f"HARD FAIL: Final flaw integrity failed! Missing flaws: {final_absent}. Discarding scenario and re-rolling Phase 0...")
        st = load_state()
        st["scenario_retries"] += 1
        save_state(st)
        cmd_stage1_prep(inputs["index"], st["seed"], is_retry=True)
        sys.exit(2)
        
    out_path = DRAFTS / f"{final_case['case_id']}.json"
    out_path.write_text(json.dumps(final_case, indent=2), encoding="utf-8")
    print(f"SUCCESS: Case {final_case['case_id']} assembled and validated!")

def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    
    p = sub.add_parser("stage1_prep")
    p.add_argument("--index", type=int, required=True)
    p.add_argument("--seed", type=int, required=True)
    
    s1 = sub.add_parser("stage1_eval")
    s1.add_argument("--brief", required=True)
    
    s1v = sub.add_parser("stage1_verify")
    s1v.add_argument("--critics", required=True)
    
    s2 = sub.add_parser("stage2_eval")
    s2.add_argument("--brief", required=True)
    s2.add_argument("--letter", required=True)
    
    s2v = sub.add_parser("stage2_verify")
    s2v.add_argument("--critics", required=True)
    
    s3 = sub.add_parser("stage3_eval")
    s3.add_argument("--brief", required=True)
    s3.add_argument("--context", required=True)
    
    s3v = sub.add_parser("stage3_verify")
    s3v.add_argument("--critics", required=True)
    
    s4_chk = sub.add_parser("stage4_det_check")
    s4_chk.add_argument("--brief", required=True)
    s4_chk.add_argument("--p4", required=True)
    
    s5 = sub.add_parser("stage5_eval")
    s5.add_argument("--brief", required=True)
    s5.add_argument("--final", required=True)
    
    s5v = sub.add_parser("stage5_verify")
    s5v.add_argument("--brief", required=True)
    s5v.add_argument("--final", required=True)
    s5v.add_argument("--critics", required=True)
    
    fp = sub.add_parser("final_panel")
    fp.add_argument("--brief", required=True)
    fp.add_argument("--final", required=True)
    
    a = sub.add_parser("assemble")
    a.add_argument("--index", type=int, required=True)
    a.add_argument("--brief", required=True)
    a.add_argument("--final", required=True)
    a.add_argument("--critics", required=True)
    
    args = ap.parse_args(argv)
    if args.cmd == "stage1_prep": cmd_stage1_prep(args.index, args.seed)
    elif args.cmd == "stage1_eval": cmd_stage1_eval(args.brief)
    elif args.cmd == "stage1_verify": cmd_stage1_verify(args.critics)
    elif args.cmd == "stage2_eval": cmd_stage2_eval(args.brief, args.letter)
    elif args.cmd == "stage2_verify": cmd_stage2_verify(args.critics)
    elif args.cmd == "stage3_eval": cmd_stage3_eval(args.brief, args.context)
    elif args.cmd == "stage3_verify": cmd_stage3_verify(args.critics)
    elif args.cmd == "stage4_det_check": cmd_stage4_det_check(args.brief, args.p4)
    elif args.cmd == "stage5_eval": cmd_stage5_eval(args.brief, args.final)
    elif args.cmd == "stage5_verify": cmd_stage5_verify(args.brief, args.final, args.critics)
    elif args.cmd == "final_panel": cmd_final_panel(args.brief, args.final)
    elif args.cmd == "assemble": cmd_assemble(args.index, args.brief, args.final, args.critics)
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
