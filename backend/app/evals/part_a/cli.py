from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from app.aegis_v1.pipeline import run_aegis_v1_pipeline
from app.evals.part_a.llm_judges import GeminiJudgeClient
from app.evals.part_a.llm_judges import OfflineHeuristicJudgeClient
from app.evals.part_a.panel import run_panel
from app.evals.part_a.teacher_packet import build_teacher_grading_packet
from app.evals.part_a.teacher_packet import load_case


REPO_ROOT = Path(__file__).resolve().parents[4]


def _case_paths(args: argparse.Namespace) -> list[Path]:
    paths = [Path(value) for value in args.cases]
    if args.case_dir:
        paths.extend(sorted(Path(args.case_dir).glob("*.json")))
    return paths


def _client(name: str):
    if name == "gemini":
        return GeminiJudgeClient()
    return OfflineHeuristicJudgeClient()


def _run_one(path: Path, judge_client: Any) -> dict[str, Any]:
    case_obj = load_case(path)
    appeal_package = run_aegis_v1_pipeline(
        denial_text=case_obj.get("denial_letter_text", ""),
        clinical_context=case_obj.get("clinical_context", ""),
        case_id=case_obj.get("case_id", path.stem),
        dataset_split="benchmark",
        run_mode="benchmark",
    )
    teacher = build_teacher_grading_packet(case_obj, appeal_package)
    report = run_panel(appeal_package, teacher, judge_client)
    return {
        "case_path": str(path),
        "appeal_package": appeal_package,
        "panel_report": report.model_dump(),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the Part A judge panel.")
    parser.add_argument("cases", nargs="*", help="Generated case JSON files.")
    parser.add_argument("--case-dir", help="Directory of generated case JSON files.")
    parser.add_argument(
        "--judge",
        choices=["offline", "gemini"],
        default="offline",
        help="Judge backend. Offline is diagnostic only and requires no cloud config.",
    )
    parser.add_argument(
        "--output-dir",
        default=str(REPO_ROOT / "eval" / "runs"),
        help="Directory where the run report is written.",
    )
    args = parser.parse_args()

    paths = _case_paths(args)
    if not paths:
        raise SystemExit("Provide at least one case path or --case-dir.")

    judge_client = _client(args.judge)
    results = [_run_one(path, judge_client) for path in paths]
    run_id = datetime.now(UTC).strftime("part-a-panel-%Y%m%d-%H%M%S")
    out_dir = Path(args.output_dir) / run_id
    out_dir.mkdir(parents=True, exist_ok=True)
    output = {
        "run_id": run_id,
        "judge": getattr(judge_client, "name", args.judge),
        "official_score": args.judge == "gemini",
        "results": results,
    }
    (out_dir / "panel_report.json").write_text(
        json.dumps(output, indent=2, default=str),
        encoding="utf-8",
    )
    print(out_dir / "panel_report.json")


if __name__ == "__main__":
    main()
