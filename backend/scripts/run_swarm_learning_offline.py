#!/usr/bin/env python3
"""Offline swarm Learning Coordinator demo (Phase 6).

Seeds in-memory Phoenix with synthetic train signal, runs one optimize() pass,
prints the promotion proposal or corpus-gap recommendation.
"""

from __future__ import annotations

import argparse

from app.learning.benchmark_dataset import micro_benchmark_fixture
from app.learning.models import ScoredRun, composite_score
from app.learning.reflection_client import StubReflectionClient
from app.learning.store import InMemoryPhoenixLearningStore
from app.learning.swarm_candidate import swarm_seed_candidate
from app.learning.swarm_coordinator import SwarmLearningCoordinator
from app.learning.swarm_experiment import StubSwarmExperimentRunner

SLICE = "Cigna:medical_necessity"


def main() -> None:
    parser = argparse.ArgumentParser(description="Run offline swarm learning coordinator")
    parser.add_argument(
        "--dimension",
        default="appeal_vector_capture",
        help="Weakest dimension to simulate in train signal",
    )
    args = parser.parse_args()

    store = InMemoryPhoenixLearningStore()
    seed = swarm_seed_candidate()
    for comp in seed.components.values():
        store.seed_component(comp)

    dims = {d: 5 for d in [
        "grounding", "appeal_vector_capture", "case_specific_clinical_rebuttal",
        "question_agent", "persuasive_coherence",
    ]}
    dims[args.dimension] = 1
    for case in micro_benchmark_fixture():
        if case["dataset_split"] != "benchmark_train":
            continue
        store.add_run(
            "benchmark_train",
            ScoredRun(
                case_id=case["case_id"],
                slice=SLICE,
                dimension_scores=dims,
                hard_gate_pass=True,
                weighted_quality=composite_score(dims, True),
                improvement_notes={args.dimension: "offline demo signal"},
            ),
        )

    coord = SwarmLearningCoordinator(
        store=store,
        runner=StubSwarmExperimentRunner(micro_benchmark_fixture()),
        reflection_client=StubReflectionClient(),
        slice_filter=SLICE,
    )
    result = coord.optimize()
    if result is None:
        print("No signal — learning halted (INV-1).")
        return
    if result.corpus_gap:
        print(f"Corpus gap queued: {result.corpus_gap.weakest_dimension}")
        print(f"  reason: {result.corpus_gap.reason}")
        return
    if result.proposal:
        p = result.proposal
        print(f"Resolved component: {result.resolved_component_id}")
        print(f"  before composite: {p.before.composite:.4f}")
        print(f"  after composite:  {p.after.composite:.4f}")
        print(f"  promotable: {p.is_promotable}")
        print(f"  vetoes: {p.vetoes}")
        print(f"  diff: {p.candidate.diff_summary}")


if __name__ == "__main__":
    main()
