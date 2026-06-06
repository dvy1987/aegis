from __future__ import annotations

import json
from pathlib import Path

from app.learning.fs_store import FileSystemPhoenixLearningStore
from app.learning.models import Candidate, Component, PromotionAudit
from app.learning.phoenix_live import LivePhoenixLearningStore


def _audit() -> PromotionAudit:
    return PromotionAudit(
        candidate_id="c1",
        experiment_id="exp1",
        before_composite=0.4,
        after_composite=0.7,
        per_dimension_deltas={"grounding": 0.1},
        diff_summary="Changed: writing approach",
        approver="pm",
        vetoes=[],
    )


def test_prompt_promotion_writes_runtime_loadable_filename(tmp_path: Path) -> None:
    prompts_dir = tmp_path / "prompts"
    store = FileSystemPhoenixLearningStore(
        playbooks_dir=tmp_path / "playbooks",
        prompts_dir=prompts_dir,
    )
    candidate = Candidate(
        candidate_id="c1",
        components={
            "drafter_system_prompt": Component(
                component_id="drafter_system_prompt",
                kind="prompt",
                version="drafter_v3",
                text="New promoted drafter prompt.",
            )
        },
        origin="reflect",
    )

    store.register_promotion(candidate, _audit())

    assert (prompts_dir / "drafter_v3.md").read_text() == "New promoted drafter prompt."
    assert (prompts_dir / "active_drafter_prompt.txt").read_text() == "drafter_v3"
    assert not (prompts_dir / "drafter_system_prompt__drafter_v3.md").exists()


def test_playbook_promotion_writes_runtime_loadable_filename(tmp_path: Path) -> None:
    playbooks_dir = tmp_path / "playbooks"
    store = FileSystemPhoenixLearningStore(
        playbooks_dir=playbooks_dir,
        prompts_dir=tmp_path / "prompts",
    )
    candidate = Candidate(
        candidate_id="c1",
        components={
            "playbook:Cigna:medical_necessity": Component(
                component_id="playbook:Cigna:medical_necessity",
                kind="playbook",
                version="cigna_mednec_v2",
                playbook={
                    "tactics": ["Quote the clinical criteria directly."],
                    "required_evidence": ["physician letter"],
                    "risk_flags": [],
                },
            )
        },
        origin="reflect",
    )

    store.register_promotion(candidate, _audit())

    payload = json.loads((playbooks_dir / "cigna__medical_necessity.json").read_text())
    assert payload["version"] == "cigna_mednec_v2"
    assert payload["tactics"] == ["Quote the clinical criteria directly."]


def test_live_store_default_playbook_dir_matches_v1_runtime() -> None:
    from app.aegis_v1.tools import PLAYBOOK_DIR

    store = LivePhoenixLearningStore()

    assert store._fs._playbooks_dir == PLAYBOOK_DIR  # type: ignore[attr-defined]
