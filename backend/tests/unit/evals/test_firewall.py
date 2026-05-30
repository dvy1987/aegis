from app.evals.part_a.evaluated_run import run_evaluated_case
from app.evals.part_a.recorder import InMemoryPhoenixRecorder
from app.evals.part_a.teacher_packet import build_student_case_packet
from app.aegis_v1.drafter_client import StubDrafterClient
from app.evals.part_a.llm_judges import OfflineHeuristicJudgeClient

SECRET = "SECRET_EXPECTED_VECTOR_attack_the_peer_to_peer_failure"


def _case_with_answer_key():
    return {
        "case_id": "fw1", "insurer": "Cigna", "denial_type": "Medical Necessity",
        "denial_letter_text": "Denied: not medically necessary.",
        "clinical_context": "Failed two SSRIs.",
        "patient_profile": {"plan_funding_type": "fully_insured"},
        "denial_pattern_sources": [],
        "synthetic_provenance": {"appeal_difficulty": {
            "exploitable_weaknesses": [SECRET], "strong_defenses": [SECRET]}},
    }


def test_student_packet_excludes_answer_key():
    case = _case_with_answer_key()
    student = build_student_case_packet(case).model_dump()
    assert SECRET not in str(student)


def test_laundered_annotation_never_leaks_answer_key():
    rec = InMemoryPhoenixRecorder()
    run_evaluated_case(_case_with_answer_key(), recorder=rec,
                       drafter_client=StubDrafterClient(),
                       judge_client=OfflineHeuristicJudgeClient(),
                       run_simulator=False)
    ref = "mem-trace-1"
    assert SECRET not in str(rec.get(ref)["annotations"])   # firewall holds
