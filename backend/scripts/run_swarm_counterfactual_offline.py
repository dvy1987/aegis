#!/usr/bin/env python3
"""Run the swarm Phoenix-MCP counterfactual offline (no HTTP server, no API key).

Usage:
    cd backend && uv run python scripts/run_swarm_counterfactual_offline.py
    cd backend && uv run python scripts/run_swarm_counterfactual_offline.py --cases 3
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from app.aegis_swarm.client import StubSwarmClient
from app.evals.part_a.llm_judges import OfflineHeuristicJudgeClient
from app.learning.swarm_counterfactual import run_swarm_counterfactual

REPO_ROOT = Path(__file__).resolve().parents[2]
CASE_DIR = REPO_ROOT / "eval" / "cases" / "drafts"
DEFAULT_CASES = [
    "case_01_cigna_mednec.json",
    "case_02_cigna_priorauth.json",
    "case_03_aetna_mednec.json",
]


def _load_cases(limit: int) -> list[dict]:
    paths = sorted(CASE_DIR.glob("case_*.json"))[:limit]
    if not paths:
        raise SystemExit(f"No cases found under {CASE_DIR}")
    out: list[dict] = []
    for path in paths:
        data = json.loads(path.read_text(encoding="utf-8"))
        data.setdefault("dataset_split", "benchmark")
        out.append(data)
    return out


def main() -> None:
    parser = argparse.ArgumentParser(description="Swarm MCP counterfactual (offline)")
    parser.add_argument(
        "--cases",
        type=int,
        default=len(DEFAULT_CASES),
        help="Number of draft cases to score (from eval/cases/drafts/)",
    )
    args = parser.parse_args()
    cases = _load_cases(max(1, args.cases))
    result = run_swarm_counterfactual(
        cases,
        swarm_client=StubSwarmClient(),
        judge_client=OfflineHeuristicJudgeClient(),
    )
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
