import json
from pathlib import Path

from app.learning.judge_adapter import PanelJudgeAdapter

REPO = Path(__file__).resolve().parents[4]
CASE = json.loads((REPO / "eval" / "cases" / "drafts" / "case_01_cigna_mednec.json").read_text())
LETTER = ("I am appealing the denial of the Intensive Outpatient Program. The denial states the "
          "member is medically stable, yet the record documents six months of failed weekly therapy "
          "and daily compulsions causing job loss. Requested action: overturn the denial. "
          "Not legal or medical advice. Draft assistance only.")


def test_adapter_returns_score_dict_with_five_dims_and_hard_gate():
    out = PanelJudgeAdapter().score(case=CASE, appeal_letter=LETTER)  # default offline heuristic judge
    assert set(out["dimension_scores"]) >= {
        "grounding", "appeal_vector_capture", "case_specific_clinical_rebuttal",
        "evidence_completeness", "persuasive_coherence"}
    assert isinstance(out["hard_gate_pass"], bool)
    assert all(v in (1, 3, 5) for v in out["dimension_scores"].values())


def test_adapter_hard_gate_fails_without_disclaimer():
    out = PanelJudgeAdapter().score(case=CASE, appeal_letter="Overturn this denial.")
    assert out["hard_gate_pass"] is False   # missing canonical disclaimer -> j1 FAIL


def test_adapter_uses_private_teacher_case_for_judges(monkeypatch):
    from app.evals.part_a import teacher_packet

    real_build = teacher_packet.build_teacher_grading_packet
    seen: dict = {}

    def fake_build(case, appeal_package=None):
        seen["case"] = case
        return real_build(CASE, appeal_package)

    monkeypatch.setattr(teacher_packet, "build_teacher_grading_packet", fake_build)

    student_case = {
        "case_id": "student-only",
        "denial_letter_text": "student denial",
        "clinical_context": "student context",
        "_teacher_case": CASE,
    }
    PanelJudgeAdapter().score(case=student_case, appeal_letter=LETTER)

    assert seen["case"] is CASE
    assert "synthetic_provenance" in seen["case"]
