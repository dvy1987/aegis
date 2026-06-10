from __future__ import annotations

import json
from pathlib import Path

from app.aegis_v1.showcase_rollback import PromotionStack
from app.learning.models import Candidate, Component


def test_promotion_stack_snapshots_and_restores_changed_files(tmp_path: Path) -> None:
    prompts_dir = tmp_path / "prompts"
    playbooks_dir = tmp_path / "playbooks"
    ledger_dir = tmp_path / "ledger"
    prompts_dir.mkdir()
    playbooks_dir.mkdir()

    (prompts_dir / "drafter_v1.md").write_text("day zero prompt", encoding="utf-8")
    (prompts_dir / "active_drafter_prompt.txt").write_text("drafter_v1", encoding="utf-8")
    playbook_path = playbooks_dir / "cigna__medical_necessity.json"
    playbook_path.write_text(
        json.dumps(
            {
                "insurer": "Cigna",
                "denial_type": "medical_necessity",
                "version": "day_zero",
                "tactics": ["Write a polite appeal letter."],
                "required_evidence": [],
                "risk_flags": [],
            }
        ),
        encoding="utf-8",
    )
    candidate = Candidate(
        candidate_id="c1",
        components={
            "drafter_system_prompt": Component(
                component_id="drafter_system_prompt",
                kind="prompt",
                version="drafter_v3",
                text="candidate prompt",
            ),
            "playbook:Cigna:medical_necessity:not_evidence_based": Component(
                component_id="playbook:Cigna:medical_necessity:not_evidence_based",
                kind="playbook",
                version="cigna_mednec_v3",
                playbook={"tactics": ["Use criteria."]},
            ),
        },
        origin="reflect",
    )
    stack = PromotionStack(
        ledger_dir=ledger_dir,
        prompts_dir=prompts_dir,
        playbooks_dir=playbooks_dir,
    )

    stack.push_checkpoint(run_type="quick", session_id="quick_1", candidate=candidate)
    (prompts_dir / "active_drafter_prompt.txt").write_text("drafter_v3", encoding="utf-8")
    (prompts_dir / "drafter_v3.md").write_text("candidate prompt", encoding="utf-8")
    playbook_path.write_text(
        json.dumps(
            {
                "insurer": "Cigna",
                "denial_type": "medical_necessity",
                "version": "cigna_mednec_v3",
                "tactics": ["Use criteria."],
                "required_evidence": [],
                "risk_flags": [],
            }
        ),
        encoding="utf-8",
    )

    target = stack.rollback_target()
    assert target is not None
    assert target.session_id == "quick_1"

    restored = stack.rollback_latest()

    assert restored.session_id == "quick_1"
    assert (prompts_dir / "active_drafter_prompt.txt").read_text(encoding="utf-8") == "drafter_v1"
    assert (prompts_dir / "drafter_v1.md").read_text(encoding="utf-8") == "day zero prompt"
    assert json.loads(playbook_path.read_text(encoding="utf-8"))["version"] == "day_zero"
    assert stack.rollback_target() is None
