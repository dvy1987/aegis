from __future__ import annotations

from app.learning.experiment import ExperimentRunner, baseline_experiment_from_phoenix
from app.learning.gates import evaluate_vetoes
from app.learning.merge import system_aware_merge
from app.learning.models import (
    Candidate, Component, DIMENSIONS, ExperimentResult, PromotionAudit, PromotionProposal,
)
from app.learning.mutation import reflective_mutate
from app.learning.reflection_client import ReflectionClient
from app.learning.selection import pareto_select, select_component
from app.learning.signal import acquire_signal
from app.learning.slice_key import parse_slice_key, playbook_component_id
from app.learning.store import PhoenixLearningStore

JUDGE_CONFIG_VERSION = "frozen_v1"


class LearningCoordinator:
    """GEPA-faithful reflective prompt evolution over {drafter prompt} ∪ {per-slice
    playbooks}. Reads its gradient FROM Phoenix (INV-1), reflects one component per
    child (V2-INV-2), selects on an instance-wise Pareto frontier, merges lineages,
    and returns a human-reviewable PromotionProposal. Promotion is explicit (HITL)."""

    def __init__(self, *, store: PhoenixLearningStore, runner: ExperimentRunner,
                 reflection_client: ReflectionClient, slice_filter: str,
                 slice_filters: list[str] | None = None,
                 holdout_split: str = "benchmark_holdout", train_split: str = "benchmark_train",
                 max_rounds: int = 8, max_merges: int = 5,
                 minibatch_size: int = 3) -> None:
        self.store = store
        self.runner = runner
        self.reflection_client = reflection_client
        self.slice_filter = slice_filter
        self.slice_filters = list(dict.fromkeys(slice_filters or [slice_filter]))
        self.holdout_split = holdout_split
        self.train_split = train_split
        self.max_rounds = max_rounds
        self.max_merges = max_merges
        self.minibatch_size = minibatch_size

    def _eligible_component_ids(self) -> frozenset[str]:
        return frozenset(
            {"drafter_system_prompt"}
            | {playbook_component_id(slice_key) for slice_key in self.slice_filters}
        )

    def _load_playbook_component(self, slice_key: str) -> Component:
        from app.aegis_v1.tools import playbook_loader

        comp_id = playbook_component_id(slice_key)
        versions = self.store.list_prompt_versions(comp_id)
        if versions:
            pb = self.store.read_prompt_version(comp_id)
            if pb.playbook:
                return Component(
                    component_id=comp_id,
                    kind="playbook",
                    version=pb.version,
                    playbook=pb.playbook,
                )
        insurer, denial_type, sub_tactic = parse_slice_key(slice_key)
        raw = playbook_loader(insurer, denial_type, sub_tactic=sub_tactic)
        return Component(
            component_id=comp_id,
            kind="playbook",
            version=str(raw.get("version") or "cold-start"),
            playbook=raw,
        )

    def _seed(self) -> Candidate:
        prompt = self.store.read_prompt_version("drafter_system_prompt")
        components = {
            "drafter_system_prompt": Component(component_id="drafter_system_prompt", kind="prompt",
                                               version=prompt.version, text=prompt.text),
        }
        for slice_key in self.slice_filters:
            components[playbook_component_id(slice_key)] = self._load_playbook_component(slice_key)
        return Candidate(candidate_id="seed", components=components, origin="seed")

    def _component_slice_filter(self, component_id: str) -> str | None:
        if component_id == "drafter_system_prompt":
            return None
        if component_id.startswith("playbook:"):
            return component_id.removeprefix("playbook:")
        return self.slice_filter

    def _case_scores(self, result: ExperimentResult) -> dict[str, float]:
        return {c.case_id: c.composite for c in result.per_case}

    def optimize(self) -> PromotionProposal | None:
        # INV-1: no Phoenix signal -> no gradient -> halt before any candidate work.
        probe = acquire_signal(self.store, component_id="drafter_system_prompt",
                               dataset_split=self.train_split,
                               slice_filter=self._component_slice_filter("drafter_system_prompt"))
        if probe is None:
            return None

        seed = self._seed()
        seed_baseline = baseline_experiment_from_phoenix(
            self.store,
            seed,
            train_split=self.train_split,
            dataset_split=self.holdout_split,
        )
        if seed_baseline is None:
            seed_baseline = self.runner.run(
                seed, dataset_split=self.holdout_split, gepa_round=0
            )
        results: dict[str, ExperimentResult] = {seed.candidate_id: seed_baseline}
        pool: list[Candidate] = [seed]
        scores = {seed.candidate_id: self._case_scores(results[seed.candidate_id])}
        best = seed
        merges = 0
        counter = 0

        allowed = self._eligible_component_ids()
        for round_index in range(self.max_rounds):
            parent = pareto_select(pool, scores)
            comp_id = select_component(parent, round_index, allowed=allowed)
            signal = acquire_signal(self.store, component_id=comp_id,
                                    dataset_split=self.train_split,
                                    slice_filter=self._component_slice_filter(comp_id))
            if signal is None:
                break
            minibatch = signal.failing_cases[: self.minibatch_size]
            counter += 1
            child = reflective_mutate(parent, signal, self.reflection_client,
                                      minibatch=minibatch, next_id=f"c{counter}")
            res = self.runner.run(child, dataset_split=self.holdout_split, gepa_round=round_index + 1)
            pool.append(child)
            results[child.candidate_id] = res
            scores[child.candidate_id] = self._case_scores(res)
            if res.composite > results[best.candidate_id].composite:
                best = child

            # system-aware merge of two complementary lineages (capped)
            if merges < self.max_merges and len(pool) >= 3:
                merged = system_aware_merge(best, child, base=seed, next_id=f"m{counter}")
                if merged is not None:
                    mres = self.runner.run(
                        merged, dataset_split=self.holdout_split, gepa_round=round_index + 1
                    )
                    pool.append(merged)
                    results[merged.candidate_id] = mres
                    scores[merged.candidate_id] = self._case_scores(mres)
                    merges += 1
                    if mres.composite > results[best.candidate_id].composite:
                        best = merged

        before, after = results[seed.candidate_id], results[best.candidate_id]
        deltas = {d: round(after.dimension_means()[d] - before.dimension_means()[d], 4) for d in DIMENSIONS}
        vetoes = evaluate_vetoes(before, after, best)
        return PromotionProposal(candidate=best, before=before, after=after,
                                 per_dimension_deltas=deltas, vetoes=vetoes)

    def promote(self, proposal: PromotionProposal, *, approver: str) -> None:
        """HITL promotion: register the new component versions + write the audit. Caller
        is responsible for only calling this on an approved, promotable proposal."""
        active = set(self.slice_filters)
        filtered_components = {}
        for comp_id, comp in proposal.candidate.components.items():
            if comp_id.startswith("playbook:"):
                slice_key = comp_id.removeprefix("playbook:")
                if slice_key not in active:
                    continue
            filtered_components[comp_id] = comp
        candidate = proposal.candidate.model_copy(update={"components": filtered_components})
        audit = PromotionAudit(
            candidate_id=candidate.candidate_id, experiment_id=proposal.after.experiment_id,
            before_composite=proposal.before.composite, after_composite=proposal.after.composite,
            per_dimension_deltas=proposal.per_dimension_deltas, diff_summary=candidate.diff_summary,
            approver=approver, vetoes=proposal.vetoes)
        self.store.register_promotion(candidate, audit)
