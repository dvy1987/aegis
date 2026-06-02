"""Swarm Learning Coordinator — credit-map re-point + GEPA loop (Phase 6)."""

from __future__ import annotations

from pydantic import BaseModel, Field

from app.learning.autonomy_ladder import AutonomyLadder
from app.learning.coordinator import JUDGE_CONFIG_VERSION
from app.learning.credit_resolution import assert_evolvable
from app.learning.swarm_gates import evaluate_swarm_vetoes
from app.learning.merge import system_aware_merge
from app.learning.models import (
    DIMENSIONS,
    Candidate,
    CorpusGapRecommendation,
    ExperimentResult,
    PromotionAudit,
    PromotionProposal,
)
from app.learning.mutation import reflective_mutate
from app.learning.reflection_client import ReflectionClient
from app.learning.selection import pareto_select
from app.learning.store import PhoenixLearningStore
from app.learning.swarm_candidate import swarm_seed_candidate
from app.learning.swarm_experiment import SwarmExperimentRunner
from app.learning.swarm_signal import acquire_swarm_signal


class SwarmOptimizationResult(BaseModel):
    """Outcome of one coordinator pass."""

    proposal: PromotionProposal | None = None
    corpus_gap: CorpusGapRecommendation | None = None
    resolved_component_id: str = ""
    judge_config_version: str = JUDGE_CONFIG_VERSION


class SwarmLearningCoordinator:
    """GEPA loop over all evolvable swarm agent prompts (one component per child).

    Unlike Part A's coordinator (drafter + playbooks only), this resolves the
    mutation target via the credit-assignment map so **any** pipeline agent
    can evolve when judges attribute weakness to that role.
    """

    def __init__(
        self,
        *,
        store: PhoenixLearningStore,
        runner: SwarmExperimentRunner,
        reflection_client: ReflectionClient,
        slice_filter: str | None = None,
        holdout_split: str = "benchmark_holdout",
        train_split: str = "benchmark_train",
        max_rounds: int = 8,
        max_merges: int = 5,
        minibatch_size: int = 3,
        autonomy: AutonomyLadder | None = None,
    ) -> None:
        self.store = store
        self.runner = runner
        self.reflection_client = reflection_client
        self.slice_filter = slice_filter
        self.holdout_split = holdout_split
        self.train_split = train_split
        self.max_rounds = max_rounds
        self.max_merges = max_merges
        self.minibatch_size = minibatch_size
        self.autonomy = autonomy or AutonomyLadder()
        self.corpus_gap_queue: list[CorpusGapRecommendation] = []

    def _seed(self) -> Candidate:
        return swarm_seed_candidate()

    def _case_scores(self, result: ExperimentResult) -> dict[str, float]:
        return {c.case_id: c.composite for c in result.per_case}

    def optimize(self) -> SwarmOptimizationResult | None:
        signal, corpus_gap = acquire_swarm_signal(
            self.store,
            dataset_split=self.train_split,
            slice_filter=self.slice_filter,
        )
        if signal is None and corpus_gap is None:
            return None  # INV-1: no Phoenix signal

        if corpus_gap is not None:
            self.corpus_gap_queue.append(corpus_gap)
            return SwarmOptimizationResult(corpus_gap=corpus_gap)

        assert_evolvable(signal.component_id)

        seed = self._seed()
        if hasattr(self.runner, "set_seed"):
            self.runner.set_seed(seed)  # type: ignore[attr-defined]

        results: dict[str, ExperimentResult] = {
            seed.candidate_id: self.runner.run(seed, dataset_split=self.holdout_split),
        }
        pool: list[Candidate] = [seed]
        scores: dict[str, dict[str, float]] = {
            seed.candidate_id: self._case_scores(results[seed.candidate_id]),
        }
        best = seed
        merges = 0
        counter = 0

        for _round_index in range(self.max_rounds):
            parent = pareto_select(pool, scores)
            minibatch = signal.failing_cases[: self.minibatch_size]
            counter += 1
            child = reflective_mutate(
                parent,
                signal,
                self.reflection_client,
                minibatch=minibatch,
                next_id=f"swarm_c{counter}",
            )
            res = self.runner.run(child, dataset_split=self.holdout_split)
            pool.append(child)
            results[child.candidate_id] = res
            scores[child.candidate_id] = self._case_scores(res)
            if res.composite > results[best.candidate_id].composite:
                best = child

            if merges < self.max_merges and len(pool) >= 3:
                merged = system_aware_merge(best, child, base=seed, next_id=f"swarm_m{counter}")
                if merged is not None:
                    mres = self.runner.run(merged, dataset_split=self.holdout_split)
                    pool.append(merged)
                    results[merged.candidate_id] = mres
                    scores[merged.candidate_id] = self._case_scores(mres)
                    merges += 1
                    if mres.composite > results[best.candidate_id].composite:
                        best = merged

        before, after = results[seed.candidate_id], results[best.candidate_id]
        self.autonomy.record_holdout(after.composite)
        deltas = {
            d: round(after.dimension_means()[d] - before.dimension_means()[d], 4)
            for d in DIMENSIONS
        }
        vetoes = evaluate_swarm_vetoes(before, after, best, seed)
        proposal = PromotionProposal(
            candidate=best,
            before=before,
            after=after,
            per_dimension_deltas=deltas,
            vetoes=vetoes,
        )
        return SwarmOptimizationResult(
            proposal=proposal,
            resolved_component_id=signal.component_id,
        )

    def promote(self, proposal: PromotionProposal, *, approver: str, auto: bool = False) -> None:
        """Register promoted component versions + audit. Respects autonomy ladder."""
        if auto and not self.autonomy.may_auto_promote(proposal):
            raise PermissionError(
                f"autonomy stage {self.autonomy.state.stage.value} requires HITL for this promotion"
            )
        audit = PromotionAudit(
            candidate_id=proposal.candidate.candidate_id,
            experiment_id=proposal.after.experiment_id,
            before_composite=proposal.before.composite,
            after_composite=proposal.after.composite,
            per_dimension_deltas=proposal.per_dimension_deltas,
            diff_summary=proposal.candidate.diff_summary,
            approver=approver,
            vetoes=proposal.vetoes,
        )
        self.store.register_promotion(proposal.candidate, audit)
        if auto:
            self.autonomy.note_auto_promotion()
        else:
            self.autonomy.note_pm_approval()
