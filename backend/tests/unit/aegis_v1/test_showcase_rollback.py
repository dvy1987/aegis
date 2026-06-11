from __future__ import annotations

import json
from pathlib import Path

from app.aegis_v1.geo_playbook import US_PLAYBOOK_COMPONENT_ID, US_PLAYBOOK_PATH
from app.aegis_v1.showcase_rollback import PromotionStack
from app.learning.fs_store import _playbook_path
from app.learning.models import Candidate, Component

_SLICE_PLAYBOOK_ID = "playbook:Cigna:medical_necessity:not_evidence_based"


def test_promotion_stack_snapshots_and_restores_changed_files(tmp_path: Path) -> None:
    prompts_dir = tmp_path / "prompts"
    playbooks_dir = tmp_path / "playbooks"
    ledger_dir = tmp_path / "ledger"
    prompts_dir.mkdir()
    playbooks_dir.mkdir()

    (prompts_dir / "drafter_v1.md").write_text("day zero prompt", encoding="utf-8")
    (prompts_dir / "active_drafter_prompt.txt").write_text("drafter_v1", encoding="utf-8")
    playbook_path = _playbook_path(playbooks_dir, _SLICE_PLAYBOOK_ID)
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
            _SLICE_PLAYBOOK_ID: Component(
                component_id=_SLICE_PLAYBOOK_ID,
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


def test_promotion_stack_handles_us_geo_playbook(tmp_path: Path) -> None:
    ledger_dir = tmp_path / "ledger"
    US_PLAYBOOK_PATH.parent.mkdir(parents=True, exist_ok=True)
    US_PLAYBOOK_PATH.write_text(
        json.dumps({"version": "day_zero", "rules": []}),
        encoding="utf-8",
    )
    candidate = Candidate(
        candidate_id="c_geo",
        components={
            US_PLAYBOOK_COMPONENT_ID: Component(
                component_id=US_PLAYBOOK_COMPONENT_ID,
                kind="playbook",
                version="day_zero+1",
                playbook={"version": "day_zero+1", "rules": [{"rule_id": "us_004"}]},
            ),
        },
        origin="reflect",
    )
    stack = PromotionStack(ledger_dir=ledger_dir)
    entry = stack.push_checkpoint(run_type="quick", session_id="gp1", candidate=candidate)
    paths = {snapshot.path for snapshot in entry.files}
    assert str(US_PLAYBOOK_PATH) in paths
