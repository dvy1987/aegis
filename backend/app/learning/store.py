from __future__ import annotations

from typing import Protocol

from app.learning.models import (
    Candidate, Component, ComponentVersion, ExperimentResult, PromotionAudit, ScoredRun,
)


class PhoenixLearningStore(Protocol):
    """The ONLY contract the Coordinator has to Phoenix (INV-1). Real impl talks to
    Phoenix MCP/SDK; the fake mirrors the same shapes in memory."""

    def read_scored_runs(self, *, dataset_split: str, prompt_version: str | None = None,
                         playbook_version: str | None = None) -> list[ScoredRun]: ...

    def read_prompt_version(self, component_id: str, version: str | None = None) -> ComponentVersion: ...

    def list_prompt_versions(self, component_id: str) -> list[ComponentVersion]: ...

    def register_promotion(self, candidate: Candidate, audit: PromotionAudit) -> None: ...


class InMemoryPhoenixLearningStore:
    """Deterministic offline fake. Reads back recorded runs (the substrate's
    InMemoryPhoenixRecorder feeds these) and versions components in memory."""

    name = "in_memory_learning_store"

    def __init__(self) -> None:
        self._runs: dict[str, list[ScoredRun]] = {}
        self._versions: dict[str, list[ComponentVersion]] = {}
        self.audits: list[PromotionAudit] = []

    # --- test/seed helpers ---
    def add_run(self, dataset_split: str, run: ScoredRun) -> None:
        self._runs.setdefault(dataset_split, []).append(run)

    def seed_component(self, component: Component) -> None:
        self._versions.setdefault(component.component_id, []).append(
            ComponentVersion(component_id=component.component_id, version=component.version,
                             text=component.text, playbook=component.playbook))

    # --- read ---
    def read_scored_runs(self, *, dataset_split: str, prompt_version: str | None = None,
                         playbook_version: str | None = None) -> list[ScoredRun]:
        runs = self._runs.get(dataset_split, [])
        if prompt_version is not None:
            runs = [r for r in runs if r.prompt_version == prompt_version]
        if playbook_version is not None:
            runs = [r for r in runs if r.playbook_version == playbook_version]
        return list(runs)

    def read_prompt_version(self, component_id: str, version: str | None = None) -> ComponentVersion:
        versions = self._versions[component_id]
        if version is None:
            return versions[-1]
        return next(v for v in versions if v.version == version)

    def list_prompt_versions(self, component_id: str) -> list[ComponentVersion]:
        return list(self._versions.get(component_id, []))

    # --- write ---
    def register_promotion(self, candidate: Candidate, audit: PromotionAudit) -> None:
        for comp in candidate.components.values():
            existing = self._versions.setdefault(comp.component_id, [])
            if not existing or existing[-1].version != comp.version:   # only register real changes
                existing.append(ComponentVersion(component_id=comp.component_id, version=comp.version,
                                                 text=comp.text, playbook=comp.playbook))
        self.audits.append(audit)
