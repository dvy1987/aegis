from __future__ import annotations

import argparse
import json
import os
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from app.aegis_v1.pipeline import run_aegis_v1_pipeline
from app.evals.part_a.llm_judges import GeminiJudgeClient, OfflineHeuristicJudgeClient
from app.evals.part_a.panel import run_panel
from app.evals.part_a.teacher_packet import build_teacher_grading_packet, load_case

REPO_ROOT = Path(os.environ.get("AEGIS_REPO_ROOT", Path(__file__).resolve().parents[4]))
PLAYBOOK_DIR = REPO_ROOT / "playbooks"


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


def _run_learning(panel_report_path: Path, slice_filter: str, approver: str) -> dict[str, Any]:
    """Load panel results into the learning store and run optimize+promote.

    Returns a summary dict describing what happened (promoted / skipped / no signal).
    Safe to call even if the coordinator finds no signal — it returns None and we skip.
    """
    from app.learning.coordinator import LearningCoordinator
    from app.learning.experiment import LiveExperimentRunner, StubExperimentRunner
    from app.learning.fs_store import FileSystemPhoenixLearningStore
    from app.learning.reflection_client import ReflectionClient

    store = FileSystemPhoenixLearningStore(playbooks_dir=PLAYBOOK_DIR)
    loaded = store.load_panel_runs(panel_report_path, dataset_split="benchmark_train")
    if loaded == 0:
        return {"learning": "skipped", "reason": "no runs loaded from panel report"}

    # Seed the current prompt and playbook versions so the coordinator can read them.
    # If the playbook file for this slice doesn't exist yet the coordinator will still
    # run — it just won't have a prior playbook to diff against.
    try:
        from app.aegis_v1.tools import CURRENT_PROMPT_VERSION, playbook_loader
        from app.learning.models import Component
        pb = playbook_loader(*slice_filter.split(":", 1)) if ":" in slice_filter else {}
        insurer, denial_type = (slice_filter.split(":", 1) + ["unknown"])[:2]
        store.seed_component(Component(
            component_id=f"playbook:{slice_filter}",
            kind="playbook",
            version=pb.get("version", "v0"),
            playbook=pb,
        ))
        store.seed_component(Component(
            component_id="drafter_system_prompt",
            kind="prompt",
            version=CURRENT_PROMPT_VERSION,
            text="",  # text not needed for signal acquisition
        ))
    except Exception:
        pass  # missing playbook or version constant is non-fatal; coordinator checks for signal first

    # Use StubExperimentRunner for offline / no-cloud runs; LiveExperimentRunner
    # requires drafter + judge clients and is used in the full GCP eval loop.
    runner = StubExperimentRunner(dataset=[])

    coordinator = LearningCoordinator(
        store=store,
        runner=runner,
        reflection_client=ReflectionClient(),
        slice_filter=slice_filter,
    )

    proposal = coordinator.optimize()
    if proposal is None:
        return {"learning": "skipped", "reason": "no Phoenix signal — coordinator halted (INV-1)"}

    if proposal.vetoes:
        return {
            "learning": "skipped",
            "reason": "vetoed",
            "vetoes": proposal.vetoes,
            "before": proposal.before.composite,
            "after": proposal.after.composite,
        }

    coordinator.promote(proposal, approver=approver)
    return {
        "learning": "promoted",
        "candidate_id": proposal.candidate.candidate_id,
        "before": proposal.before.composite,
        "after": proposal.after.composite,
        "deltas": proposal.per_dimension_deltas,
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
    parser.add_argument(
        "--learn",
        metavar="INSURER:DENIAL_TYPE",
        default=None,
        help=(
            "After scoring, run the learning coordinator for this slice "
            "(e.g. 'Cigna:medical_necessity') and promote if the proposal passes gates."
        ),
    )
    parser.add_argument(
        "--approver",
        default="cli_auto",
        help="Approver label written into the promotion audit (default: cli_auto).",
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
    panel_report_path = out_dir / "panel_report.json"
    output: dict[str, Any] = {
        "run_id": run_id,
        "judge": getattr(judge_client, "name", args.judge),
        "official_score": args.judge == "gemini",
        "results": results,
    }
    panel_report_path.write_text(
        json.dumps(output, indent=2, default=str),
        encoding="utf-8",
    )
    print(panel_report_path)

    # Learning loop: only runs when --learn is passed.
    if args.learn:
        learning_summary = _run_learning(
            panel_report_path=panel_report_path,
            slice_filter=args.learn,
            approver=args.approver,
        )
        output["learning"] = learning_summary
        panel_report_path.write_text(
            json.dumps(output, indent=2, default=str),
            encoding="utf-8",
        )
        print(json.dumps(learning_summary, indent=2))


if __name__ == "__main__":
    main()
