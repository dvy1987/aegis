from __future__ import annotations

import logging
from typing import Literal

from app.aegis_v1.drafter_client import GeminiDrafterClient
from app.aegis_v1.showcase_manifest import ShowcaseCase, load_showcase_manifest
from app.aegis_v1.showcase_session import ShowcaseSessionManager
from app.aegis_v1.simulator_client import GeminiSimulatorClient
from app.aegis_v1.tools import case_parser, phoenix_mcp_lookup
from app.evals.part_a.evaluated_run import run_evaluated_case
from app.evals.part_a.llm_judges import GeminiJudgeClient
from app.evals.part_a.measurement_run import run_measurement_case
from app.evals.part_a.recorder import OtelPhoenixRecorder
from app.learning.coordinator import LearningCoordinator
from app.learning.experiment import LiveExperimentRunner
from app.learning.judge_adapter import PanelJudgeAdapter
from app.learning.models import PromotionAudit, PromotionProposal
from app.learning.phoenix_live import LivePhoenixLearningStore
from app.learning.reflection_client import GeminiReflectionClient
from app.learning.run_live import _creds_available


logger = logging.getLogger(__name__)


def _log(session_id: str, stage: str, message: str, **extra) -> None:
    logger.info(
        message,
        extra={"session_id": session_id, "showcase_stage": stage, **extra},
    )


def _case_obj(case: ShowcaseCase, *, dataset_split: str) -> dict:
    return {
        "case_id": case.case_id,
        "denial_letter_text": case.denial_letter_text,
        "clinical_context": case.clinical_context,
        "dataset_split": dataset_split,
    }


def _dataset(cases: list[ShowcaseCase], *, slice_filter: str) -> list[dict]:
    out: list[dict] = []
    for case in cases:
        parsed = case_parser(
            denial_text=case.denial_letter_text,
            clinical_context=case.clinical_context,
            case_id=case.case_id,
        )
        out.append(
            {
                "case_id": case.case_id,
                "slice": slice_filter,
                "parsed_case": parsed,
                "citations": [],
                "phoenix_summary": phoenix_mcp_lookup(
                    insurer=parsed["insurer"],
                    denial_type=parsed["denial_type"],
                    case_id=parsed["case_id"],
                ),
                "denial_letter_text": case.denial_letter_text,
                "clinical_context": case.clinical_context,
            }
        )
    return out


def _measure(
    manager: ShowcaseSessionManager,
    session_id: str,
    *,
    phase: Literal["pre", "post"],
    cases: list[ShowcaseCase],
) -> list[dict]:
    stage = "measure_before" if phase == "pre" else "measure_after"
    manager.set_stage(session_id, stage=stage, total_cases=len(cases))
    _log(session_id, stage, "showcase measurement started", total_cases=len(cases))
    results: list[dict] = []
    drafter = GeminiDrafterClient()
    simulator = GeminiSimulatorClient()
    for index, case in enumerate(cases, start=1):
        manager.set_stage(
            session_id,
            stage=stage,
            current_case_id=case.case_id,
            completed_cases=index - 1,
            total_cases=len(cases),
        )
        result = run_measurement_case(
            _case_obj(case, dataset_split=f"showcase_{phase}_measure_{session_id}"),
            drafter_client=drafter,
            simulator_client=simulator,
        )
        results.append(result.model_dump())
        manager.set_stage(
            session_id,
            stage=stage,
            current_case_id=case.case_id,
            completed_cases=index,
            total_cases=len(cases),
        )
    manager.set_measure_results(session_id, phase=phase, results=results)
    _log(session_id, stage, "showcase measurement finished", completed_cases=len(cases))
    return results


def _seed_training_signal(
    manager: ShowcaseSessionManager,
    session_id: str,
    *,
    cases: list[ShowcaseCase],
    dataset_split: str,
) -> list[str]:
    manager.set_stage(session_id, stage="train_gepa", total_cases=len(cases))
    recorder = OtelPhoenixRecorder()
    drafter = GeminiDrafterClient()
    judge = GeminiJudgeClient()
    trace_ids: list[str] = []
    for index, case in enumerate(cases, start=1):
        manager.set_stage(
            session_id,
            stage="train_gepa",
            current_case_id=case.case_id,
            completed_cases=index - 1,
            total_cases=len(cases),
        )
        run = run_evaluated_case(
            _case_obj(case, dataset_split=dataset_split),
            recorder=recorder,
            drafter_client=drafter,
            judge_client=judge,
            run_simulator=False,
        )
        trace_ids.append(run.trace_ref)
        manager.set_stage(
            session_id,
            stage="train_gepa",
            current_case_id=case.case_id,
            completed_cases=index,
            total_cases=len(cases),
        )
    return trace_ids


def _optimize(
    *,
    cases: list[ShowcaseCase],
    slice_filter: str,
    train_split: str,
    holdout_split: str,
    max_rounds: int,
):
    store = LivePhoenixLearningStore()
    runner = LiveExperimentRunner(
        dataset=_dataset(cases, slice_filter=slice_filter),
        drafter_client=GeminiDrafterClient(),
        judge_client=PanelJudgeAdapter(judge_client=GeminiJudgeClient()),
    )
    coordinator = LearningCoordinator(
        store=store,
        runner=runner,
        reflection_client=GeminiReflectionClient(),
        slice_filter=slice_filter,
        train_split=train_split,
        holdout_split=holdout_split,
        max_rounds=max_rounds,
    )
    return coordinator.optimize()


def run_quick_session(session_id: str) -> None:
    manager = ShowcaseSessionManager()
    manifest = load_showcase_manifest()
    train_split = f"showcase_quick_train_{session_id}"
    try:
        if not _creds_available():
            manager.fail_stage(
                session_id,
                stage="queued",
                code="missing_live_credentials",
                message="Live quick run requires PHOENIX_API_KEY and Google ADC.",
                retryable=True,
            )
            return
        _measure(manager, session_id, phase="pre", cases=manifest.quick_train)
        trace_ids = _seed_training_signal(
            manager,
            session_id,
            cases=manifest.quick_train,
            dataset_split=train_split,
        )
        session = manager.get(session_id)
        session.diagnostics.phoenix_trace_ids = trace_ids
        manager._save(session)
        proposal = _optimize(
            cases=manifest.quick_train,
            slice_filter=manifest.quick_slice,
            train_split=train_split,
            holdout_split=train_split,
            max_rounds=1,
        )
        if proposal is None:
            manager.fail_stage(
                session_id,
                stage="train_gepa",
                code="no_learning_signal",
                message="Phoenix did not return learning signal for this quick run.",
                retryable=True,
            )
            return
        manager.mark_needs_approval(session_id, proposal=proposal.model_dump())
    except Exception as exc:
        manager.fail_stage(
            session_id,
            stage="train_gepa",
            code=exc.__class__.__name__,
            message=str(exc) or "Showcase quick run failed.",
            retryable=True,
        )


def approve_session(session_id: str, *, approver: str) -> None:
    manager = ShowcaseSessionManager()
    manifest = load_showcase_manifest()
    try:
        session = manager.get(session_id)
        if session.cancelled:
            manager.fail_stage(
                session_id,
                stage="promote",
                code="cancelled",
                message="Cancelled runs cannot be promoted.",
                retryable=False,
            )
            return
        if not session.proposal:
            manager.fail_stage(
                session_id,
                stage="promote",
                code="missing_proposal",
                message="No GEPA proposal is ready for approval.",
                retryable=False,
            )
            return
        proposal = PromotionProposal.model_validate(session.proposal)
        manager.set_stage(session_id, stage="promote", status="running")
        _log(session_id, "promote", "showcase promotion started", approver=approver)
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
        LivePhoenixLearningStore().register_promotion(proposal.candidate, audit)
        session = manager.get(session_id)
        session.approved_by = approver
        manager._save(session)
        _measure(manager, session_id, phase="post", cases=manifest.quick_train)
        manager.mark_success(session_id)
        _log(session_id, "measure_after", "showcase approved run completed")
    except Exception as exc:
        manager.fail_stage(
            session_id,
            stage="promote",
            code=exc.__class__.__name__,
            message=str(exc) or "Showcase approval failed.",
            retryable=True,
        )
