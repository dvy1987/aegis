from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from app.learning.models import (
    Candidate,
    Component,
    ComponentVersion,
    PromotionAudit,
    ScoredRun,
)

# Mirror the same helper used by playbook_loader so filenames are identical.
_SLUG_RE = re.compile(r"[^a-z0-9]+")


def _slug(value: str) -> str:
    return _SLUG_RE.sub("_", value.lower()).strip("_")


def _playbook_path(playbooks_dir: Path, component_id: str) -> Path:
    """Derive the on-disk filename from a component_id like 'playbook:Cigna:medical_necessity'.

    Mirrors playbook_loader's convention:
        PLAYBOOK_DIR / f"{_slug(insurer)}__{normalized_type}.json"

    component_id format:  "playbook:<insurer>:<denial_type>"
                    e.g.  "playbook:Cigna:medical_necessity"
                          "playbook:Aetna:prior_authorization"
    """
    without_prefix = component_id.removeprefix("playbook:")
    parts = without_prefix.split(":", 1)
    if len(parts) != 2:
        raise ValueError(
            f"Cannot derive playbook filename from component_id {component_id!r}. "
            "Expected format: 'playbook:<insurer>:<denial_type>'"
        )
    insurer, denial_type = parts
    filename = f"{_slug(insurer)}__{_slug(denial_type)}.json"
    return playbooks_dir / filename


def _playbook_json(comp: Component) -> dict[str, Any]:
    """Produce the JSON dict that playbook_loader deserialises.

    playbook_loader reads these keys:
        insurer, denial_type, version, tactics, required_evidence, risk_flags
    We write exactly those keys plus nothing else.
    """
    raw: dict[str, Any] = comp.playbook or {}
    without_prefix = comp.component_id.removeprefix("playbook:")
    parts = without_prefix.split(":", 1)
    insurer = parts[0] if parts else "unknown"
    denial_type = parts[1] if len(parts) > 1 else "unknown"
    return {
        "insurer": raw.get("insurer", insurer),
        "denial_type": raw.get("denial_type", denial_type),
        "version": comp.version,
        "tactics": raw.get("tactics", []),
        "required_evidence": raw.get("required_evidence", []),
        "risk_flags": raw.get("risk_flags", []),
    }


def _panel_result_to_scored_run(result: dict[str, Any]) -> ScoredRun | None:
    """Convert one entry from panel_report.json['results'] into a ScoredRun.

    panel_report result shape (written by cli.py / evaluated_run.py):
      {
        "case_path": "...",
        "appeal_package": {
          "parsed_case": {"case_id": ..., "insurer": ..., "denial_type": ...},
          "trace_metadata": {"prompt_version": ..., "playbook_version": ...},
          ...
        },
        "panel_report": {
          "verdict": "PASS"|"FAIL",
          "weighted_quality": 0.72,
          "dimension_scores": {"grounding": 3, ...},
          "judge_results": {
            "grounding": {"improvement": "...", ...},
            ...
          },
          ...
        }
      }
    """
    try:
        pkg = result.get("appeal_package", {})
        report = result.get("panel_report", {})
        parsed = pkg.get("parsed_case", {})
        meta = pkg.get("trace_metadata", {})

        case_id: str = parsed.get("case_id", "") or result.get("case_path", "unknown")
        insurer: str = parsed.get("insurer", "unknown")
        denial_type: str = parsed.get("denial_type", "unknown")
        slice_key = f"{insurer}:{denial_type}"

        dimension_scores: dict[str, int] = {
            k: int(v) for k, v in (report.get("dimension_scores") or {}).items()
        }
        hard_gate_pass: bool = report.get("verdict", "FAIL") == "PASS"
        weighted_quality: float = float(report.get("weighted_quality") or 0.0)
        prompt_version: str = str(meta.get("prompt_version", ""))
        playbook_version: str = str(meta.get("playbook_version", ""))

        # Collect laundered improvement notes from judge results (safe strings only).
        improvement_notes: dict[str, str] = {}
        for dim, jr in (report.get("judge_results") or {}).items():
            note = (jr or {}).get("improvement", "")
            if note and isinstance(note, str):
                improvement_notes[dim] = note

        simulator_verdict = pkg.get("simulator_result", {})
        if isinstance(simulator_verdict, dict):
            sim_v = simulator_verdict.get("verdict")
        else:
            sim_v = None

        return ScoredRun(
            case_id=case_id,
            slice=slice_key,
            dimension_scores=dimension_scores,
            hard_gate_pass=hard_gate_pass,
            weighted_quality=weighted_quality,
            improvement_notes=improvement_notes,
            simulator_verdict=sim_v,
            prompt_version=prompt_version,
            playbook_version=playbook_version,
        )
    except Exception:
        return None


class FileSystemPhoenixLearningStore:
    """Production PhoenixLearningStore that persists promoted artefacts to disk.

    Playbooks are written to ``playbooks_dir`` using the same naming convention
    as playbook_loader so they are picked up automatically on the next request.

    Scored runs are loaded from panel_report.json files written by the eval CLI
    via ``load_panel_runs()``.  Call that once after each eval run before handing
    the store to the LearningCoordinator.
    """

    name = "filesystem_learning_store"

    def __init__(
        self,
        playbooks_dir: Path,
        prompts_dir: Path | None = None,
    ) -> None:
        self._playbooks_dir = playbooks_dir
        self._prompts_dir = prompts_dir
        self._runs: dict[str, list[ScoredRun]] = {}
        self._versions: dict[str, list[ComponentVersion]] = {}
        self.audits: list[PromotionAudit] = []
        playbooks_dir.mkdir(parents=True, exist_ok=True)
        if prompts_dir is not None:
            prompts_dir.mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------------
    # Load eval output into the store so the coordinator can read it
    # ------------------------------------------------------------------

    def load_panel_runs(self, panel_report_path: Path, dataset_split: str) -> int:
        """Read a panel_report.json produced by the eval CLI and populate
        ``_runs[dataset_split]`` with the resulting ScoredRun objects.

        Returns the number of runs successfully loaded.

        Call this once after each eval run, before passing the store to
        LearningCoordinator.optimize():

            store = FileSystemPhoenixLearningStore(playbooks_dir=PLAYBOOK_DIR)
            store.load_panel_runs(panel_report_path, dataset_split="benchmark_train")
            proposal = coordinator.optimize()
        """
        raw = json.loads(panel_report_path.read_text(encoding="utf-8"))
        loaded = 0
        for result in raw.get("results", []):
            run = _panel_result_to_scored_run(result)
            if run is not None:
                self._runs.setdefault(dataset_split, []).append(run)
                loaded += 1
        return loaded

    # ------------------------------------------------------------------
    # PhoenixLearningStore protocol — read side
    # ------------------------------------------------------------------

    def read_scored_runs(
        self,
        *,
        dataset_split: str,
        prompt_version: str | None = None,
        playbook_version: str | None = None,
    ) -> list[ScoredRun]:
        runs = self._runs.get(dataset_split, [])
        if prompt_version is not None:
            runs = [r for r in runs if r.prompt_version == prompt_version]
        if playbook_version is not None:
            runs = [r for r in runs if r.playbook_version == playbook_version]
        return list(runs)

    def read_prompt_version(
        self, component_id: str, version: str | None = None
    ) -> ComponentVersion:
        versions = self._versions[component_id]
        if version is None:
            return versions[-1]
        return next(v for v in versions if v.version == version)

    def list_prompt_versions(self, component_id: str) -> list[ComponentVersion]:
        return list(self._versions.get(component_id, []))

    # ------------------------------------------------------------------
    # PhoenixLearningStore protocol — write side
    # ------------------------------------------------------------------

    def register_promotion(self, candidate: Candidate, audit: PromotionAudit) -> None:
        """Persist promoted components to disk and record the audit."""
        for comp in candidate.components.values():
            existing = self._versions.setdefault(comp.component_id, [])
            if not existing or existing[-1].version != comp.version:
                existing.append(
                    ComponentVersion(
                        component_id=comp.component_id,
                        version=comp.version,
                        text=comp.text,
                        playbook=comp.playbook,
                    )
                )

            if comp.kind == "playbook" and comp.playbook is not None:
                self._write_playbook(comp)

            elif comp.kind == "prompt" and comp.text is not None:
                self._write_prompt(comp)

        self.audits.append(audit)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _write_playbook(self, comp: Component) -> None:
        path = _playbook_path(self._playbooks_dir, comp.component_id)
        payload = _playbook_json(comp)
        path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")

    def _write_prompt(self, comp: Component) -> None:
        if self._prompts_dir is None:
            return
        safe_id = _slug(comp.component_id)
        safe_version = _slug(comp.version)
        path = self._prompts_dir / f"{safe_id}__{safe_version}.md"
        path.write_text(comp.text or "", encoding="utf-8")

    # ------------------------------------------------------------------
    # Test / seed helpers (mirrors InMemoryPhoenixLearningStore API)
    # ------------------------------------------------------------------

    def add_run(self, dataset_split: str, run: ScoredRun) -> None:
        self._runs.setdefault(dataset_split, []).append(run)

    def seed_component(self, component: Component) -> None:
        self._versions.setdefault(component.component_id, []).append(
            ComponentVersion(
                component_id=component.component_id,
                version=component.version,
                text=component.text,
                playbook=component.playbook,
            )
        )
