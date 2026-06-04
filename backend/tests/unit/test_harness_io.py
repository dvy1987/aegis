import json
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock
from app.case_generator import harness_io

@pytest.fixture
def mock_run_dir(tmp_path, monkeypatch):
    monkeypatch.setattr(harness_io, "RUN_DIR", tmp_path)
    monkeypatch.setattr(harness_io, "DRAFTS", tmp_path / "drafts")
    (tmp_path / "drafts").mkdir()
    return tmp_path

def test_harness_io_state_machine(mock_run_dir):
    # Mock the deterministic helpers that would otherwise need actual patterns or corpuses
    with patch("app.case_generator.harness_io.flaw_verifier") as mock_fv, \
         patch("app.case_generator.harness_io.stats_evaluator") as mock_stats, \
         patch("app.case_generator.harness_io.scan_banned") as mock_banned, \
         patch("app.case_generator.harness_io.scan_phi") as mock_phi:
             
        mock_fv.verify_flaws.return_value = {"present": ["test_pattern"], "needs_llm": [], "absent": []}
        mock_stats.diversity_verdict.return_value = {"score": 5}
        mock_banned.return_value = []
        mock_phi.return_value = []

        # 1. Test prep
        harness_io.cmd_stage1_prep(index=999, seed=42)
        inputs_file = mock_run_dir / "inputs.json"
        assert inputs_file.exists()
        
        inputs_data = json.loads(inputs_file.read_text())
        
        # Create dummy P1 brief
        brief = {
            "matrix_cell": inputs_data["cell"],
            "diagnosis": "Test Diagnosis",
            "treatment_requested": "Test Treatment",
            "patient_age": 45,
            "patient_gender": "M",
            "plan_funding_type": "self_funded"
        }
        brief_file = mock_run_dir / "brief.json"
        brief_file.write_text(json.dumps(brief))

        # 2. Test stage1_eval
        harness_io.cmd_stage1_eval(str(brief_file))
        stage1_dir = mock_run_dir / "critics" / "stage1"
        assert (stage1_dir / "matrix_coverage.txt").exists()
        assert (stage1_dir / "scenario_realism.txt").exists()

        # Create dummy P2 letter
        letter = {"denial_letter_text": "This is a mock denial letter."}
        letter_file = mock_run_dir / "letter.json"
        letter_file.write_text(json.dumps(letter))

        # 3. Test stage2_eval
        harness_io.cmd_stage2_eval(str(brief_file), str(letter_file))
        stage2_dir = mock_run_dir / "critics" / "stage2"
        assert (stage2_dir / "insurer_voice.txt").exists()

        # Create dummy P3 context
        context = {"clinical_context": "This is the mock clinical context."}
        context_file = mock_run_dir / "context.json"
        context_file.write_text(json.dumps(context))

        # 4. Test stage3_eval
        harness_io.cmd_stage3_eval(str(brief_file), str(context_file))
        stage3_dir = mock_run_dir / "critics" / "stage3"
        assert (stage3_dir / "clinical_realism.txt").exists()

        # Create dummy P4 injection
        p4 = {
            "denial_letter_text": letter["denial_letter_text"],
            "clinical_context": context["clinical_context"],
            "submission_timestamp": "2026-06-01T10:00:00Z",
            "denial_timestamp": "2026-06-02T10:00:00Z"
        }
        p4_file = mock_run_dir / "p4.json"
        p4_file.write_text(json.dumps(p4))

        # 5. Test stage4_det_check
        harness_io.cmd_stage4_det_check(str(brief_file), str(p4_file))
        
        # 6. Test stage4_5_eval
        harness_io.cmd_stage5_eval(str(brief_file), str(p4_file))
        stage5_dir = mock_run_dir / "critics" / "stage5"
        assert (stage5_dir / "diversity_delta.txt").exists()
        assert (stage5_dir / "flaw_injection_verifier_mid.txt").exists()

        # 7. Test final panel
        harness_io.cmd_final_panel(str(brief_file), str(p4_file))
        final_panel_dir = mock_run_dir / "critics" / "final_panel"
        assert len(list(final_panel_dir.glob("*.txt"))) == 11 # 10 critics + final flaw verifier

        # Create dummy critics results
        critics = {
            "matrix_coverage": {"score": "PASS"},
            "flaw_injection_verifier_mid": {
                "verification_results": [{"pattern_id": "test_pattern", "status": "PRESENT"}]
            },
            "flaw_injection_verifier_final": {
                "verification_results": [{"pattern_id": "test_pattern", "status": "PRESENT"}]
            }
        }
        critics_file = mock_run_dir / "critics.json"
        critics_file.write_text(json.dumps(critics))

        # 8. Test assemble
        with patch("app.case_generator.harness_io.assemble_case") as mock_assemble:
            mock_assemble.return_value = {"case_id": "case_999_mock_mock"}
            harness_io.cmd_assemble(999, str(brief_file), str(p4_file), str(critics_file))
            
        assert (mock_run_dir / "drafts" / "case_999_mock_mock.json").exists()
