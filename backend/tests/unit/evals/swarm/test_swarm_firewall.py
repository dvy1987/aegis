from app.aegis_swarm.client import StubSwarmClient
from app.evals.part_a.llm_judges import OfflineHeuristicJudgeClient
from app.evals.part_a.recorder import InMemoryPhoenixRecorder
from app.evals.part_a.teacher_packet import build_student_case_packet
from app.evals.swarm.evaluated_swarm_run import run_evaluated_swarm_case

SECRET = "SECRET_EXPECTED_VECTOR_attack_the_peer_to_peer_failure"


def _case_with_answer_key() -> dict:
    return {
        "case_id": "fw_swarm_1",
        "insurer": "Cigna",
        "denial_type": "Medical Necessity",
        "denial_letter_text": "Denied: not medically necessary.",
        "clinical_context": "Failed two SSRIs.",
        "patient_profile": {"plan_funding_type": "fully_insured"},
        "denial_pattern_sources": [],
        "synthetic_provenance": {
            "appeal_difficulty": {
                "exploitable_weaknesses": [SECRET],
                "strong_defenses": [SECRET],
            }
        },
    }


def test_student_packet_excludes_answer_key() -> None:
    student = build_student_case_packet(_case_with_answer_key()).model_dump()
    assert SECRET not in str(student)


def test_swarm_laundered_annotation_never_leaks_answer_key() -> None:
    rec = InMemoryPhoenixRecorder()
    run_evaluated_swarm_case(
        _case_with_answer_key(),
        rec,
        swarm_client=StubSwarmClient(),
        judge_client=OfflineHeuristicJudgeClient(),
        run_simulator=False,
    )
    assert SECRET not in str(rec.get("mem-trace-1")["annotations"])
