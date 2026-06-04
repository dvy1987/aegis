"""Known-bad gate tests (AlphaEval 'test your tests').

Each deterministic evaluator in the generation pipeline is fed a KNOWN-BAD input that it
MUST catch, plus a known-good input it must pass. This validates the evaluators themselves
— per the eval-pipeline skill, an eval suite is only trustworthy if its checks demonstrably
catch real failures. (LLM-judge critics are exercised separately via the live pipeline.)
"""
from __future__ import annotations

from app.case_generator import clinical_kb, flaw_verifier, safety, stats_evaluator
from app.case_generator.validator import validate_case


# --- flaw verifier (J6 contract) ---------------------------------------------

def test_flaw_verifier_catches_absent_iro_flaw():
    # KNOWN-BAD: missing_iro_notice intended, but the letter DOES mention external review.
    bad = flaw_verifier.verify_flaws(
        denial_letter_text="You may request an independent external review of this decision.",
        clinical_context="x",
        pattern_ids=["missing_iro_notice"],
    )
    assert "missing_iro_notice" in bad["absent"]
    assert not bad["aligned"]


def test_flaw_verifier_passes_present_iro_flaw():
    good = flaw_verifier.verify_flaws(
        denial_letter_text="You may appeal through our internal appeals process only.",
        clinical_context="x",
        pattern_ids=["missing_iro_notice"],
    )
    assert good["by_pattern"]["missing_iro_notice"] == "present"
    assert good["aligned"]


def test_flaw_verifier_algo_time_delta_requires_prose_visibility():
    # KNOWN-BAD: timestamps fine (3 min) but prose shows no fast turnaround -> absent.
    bad = flaw_verifier.verify_flaws(
        denial_letter_text="We are unable to approve this request under plan criteria.",
        clinical_context="x", pattern_ids=["algo_time_delta"],
        submission_timestamp="2026-02-01T09:00:00Z",
        denial_timestamp="2026-02-01T09:03:00Z",
    )
    assert "algo_time_delta" in bad["absent"]
    good = flaw_verifier.verify_flaws(
        denial_letter_text="Clinical review was completed within minutes of receipt.",
        clinical_context="x", pattern_ids=["algo_time_delta"],
        submission_timestamp="2026-02-01T09:00:00Z",
        denial_timestamp="2026-02-01T09:03:00Z",
    )
    assert good["by_pattern"]["algo_time_delta"] == "present"


def test_pattern_sources_are_teacher_packet_parseable():
    srcs = flaw_verifier.format_pattern_sources(
        [{"id": "missing_iro_notice", "source": "ACA 2719"}]
    )
    assert srcs == ["missing_iro_notice: ACA 2719"]
    # the teacher packet keys off the id before ':'
    from app.evals.part_a.teacher_packet import _pattern_matches_source  # noqa: PLC0415
    assert _pattern_matches_source({"id": "missing_iro_notice"}, srcs[0])


def test_final_check_llm_all_catches_deterministic_false_positive(monkeypatch):
    # The deterministic check naively marks contraindication 'present' (word match on the
    # negated "no contraindication documented"). The FINAL gate's llm_all=True must still
    # catch it as absent so a judge-facing flaw can never slip through the finished case.
    from app.case_generator import llm_pipeline as P  # noqa: PLC0415

    def fake_llm_verifier(letter, clinical, to_check, **kw):
        return {"verification_results": [
            {"pattern_id": t["id"],
             "status": "ABSENT" if t["id"] == "contraindication_to_step_therapy" else "PRESENT",
             "evidence": "e"} for t in to_check]}

    monkeypatch.setattr(P.agents, "critic_flaw_injection_verifier", fake_llm_verifier, raising=False)
    absent, det, llm_absent = P._verify_flaws_full(
        denial_letter_text="You may appeal through our internal appeals process only.",
        clinical_context="No contraindication documented; patient tolerated therapy.",
        pattern_ids=["contraindication_to_step_therapy"],
        submission_timestamp=None, denial_timestamp=None,
        specialty="endocrine", plan_funding_type="self_funded",
        patterns=[{"id": "contraindication_to_step_therapy", "description": "d", "appeal_vector": "a"}],
        llm_all=True,
    )
    assert "contraindication_to_step_therapy" in det["present"]   # deterministic false-positive
    assert "contraindication_to_step_therapy" in absent           # but final gate catches it


# --- sex guard (demographic root-cause) --------------------------------------

def test_sex_guard_catches_sex_specific_diagnoses():
    assert clinical_kb.required_sex("Ovarian cyst, persistent 6 cm (N83.202)") == "F"
    assert clinical_kb.required_sex("Gynecomastia, persistent adolescent (N62)") == "M"
    # cervical SPINE is not sex-specific (regression guard for the earlier false positive)
    assert clinical_kb.required_sex("Cervical spondylosis with radiculopathy (M47.22)") is None
    assert clinical_kb.required_sex("Major depressive disorder (F33.1)") is None


# --- statistical near-duplicate ----------------------------------------------

def test_stats_evaluator_flags_near_duplicate():
    text = ("NOTICE OF ADVERSE BENEFIT DETERMINATION. We are unable to approve the requested "
            "service under the applicable utilization-management criteria for this member.")
    corpus = (("case_existing", stats_evaluator._trigrams(text + " extra tail words here")),)
    m = stats_evaluator.diversity_metrics(
        denial_letter_text=text, clinical_context="same facts here",
        neighbour_texts=[], corpus=corpus)
    assert m["near_duplicate"] is True
    assert stats_evaluator.diversity_verdict(m)["score"] == 1


def test_stats_evaluator_passes_novel_case():
    corpus = (("c", stats_evaluator._trigrams("totally unrelated boilerplate about widgets")),)
    m = stats_evaluator.diversity_metrics(
        denial_letter_text="A bespoke denial for an experimental prion therapy with unique phrasing.",
        clinical_context="Rare genetic disorder, novel trajectory.",
        neighbour_texts=[], corpus=corpus)
    assert m["near_duplicate"] is False
    assert stats_evaluator.diversity_verdict(m)["score"] == 5


# --- safety / PHI deterministic gates ----------------------------------------

def test_phi_gate_catches_ssn():
    assert safety.scan_phi("Member SSN 123-45-6789 on file")
    assert not safety.scan_phi("Member ID W100000007; fax (877) 555-0199")


def test_safety_gate_catches_banned_topic():
    assert safety.scan_banned("the member expressed suicidal ideation")
    assert not safety.scan_banned("the member has moderate Crohn's disease")


# --- schema gate -------------------------------------------------------------

def test_schema_gate_rejects_too_short_letter():
    bad_case = {
        "case_id": "case_99_uhc_mednec", "insurer": "UHC", "denial_type": "Medical Necessity",
        "patient_profile": {"age": 40, "gender": "F", "diagnosis": "x", "treatment_requested": "y",
                            "plan_funding_type": "self_funded"},
        "denial_pattern_sources": ["missing_iro_notice: ACA"],
        "denial_letter_text": "too short", "clinical_context": "too short",
        "synthetic_provenance": {},
    }
    assert validate_case(bad_case).ok is False
