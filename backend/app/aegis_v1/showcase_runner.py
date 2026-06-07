from __future__ import annotations

import logging
from typing import Literal

from app.aegis_v1.drafter_client import GeminiDrafterClient
from app.aegis_v1.showcase_manifest import ShowcaseCase, load_showcase_manifest
from app.aegis_v1.showcase_rollback import PromotionStack
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
MeasurePhase = Literal["pre", "training_pre", "training_post", "post"]


def _log(session_id: str, stage: str, message: str, **extra) -> None:
    logger.info(
        message,
        extra={"session_id": session_id, "showcase_stage": stage, **extra},
    )


def _is_cancelled(manager: ShowcaseSessionManager, session_id: str) -> bool:
    try:
        return manager.get(session_id).cancelled
    except Exception:
        return False


def _case_obj(case: ShowcaseCase, *, dataset_split: str) -> dict:
    return case.student_case(dataset_split=dataset_split)


def _case_slice(case: ShowcaseCase) -> str:
    insurer = "UnitedHealthcare" if case.insurer == "UHC" else case.insurer
    return f"{insurer}:{case.denial_type}"


def _slice_filters(cases: list[ShowcaseCase]) -> list[str]:
    return list(dict.fromkeys(_case_slice(case) for case in cases))


def _dataset(cases: list[ShowcaseCase]) -> list[dict]:
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
                "slice": f"{parsed['insurer']}:{parsed['denial_type']}",
                "parsed_case": parsed,
                "citations": [],
                "phoenix_summary": phoenix_mcp_lookup(
                    insurer=parsed["insurer"],
                    denial_type=parsed["denial_type"],
                    case_id=parsed["case_id"],
                ),
                "denial_letter_text": case.denial_letter_text,
                "clinical_context": case.clinical_context,
                "_teacher_case": case.judge_case(dataset_split="showcase_optimizer"),
            }
        )
    return out


def _measure(
    manager: ShowcaseSessionManager,
    session_id: str,
    *,
    phase: MeasurePhase,
    cases: list[ShowcaseCase],
    drafter_prompt_version: str | None = None,
    drafter_prompt_text: str | None = None,
    playbook_overrides: dict[str, dict] | None = None,
) -> list[dict]:
    stage = "measure_before" if phase in {"pre", "training_pre"} else "measure_after"
    if _is_cancelled(manager, session_id):
        _log(session_id, stage, "showcase measurement skipped because session is cancelled")
        return []
    manager.set_stage(session_id, stage=stage, total_cases=len(cases))
    _log(session_id, stage, "showcase measurement started", total_cases=len(cases))
    results: list[dict] = []
    drafter = GeminiDrafterClient()
    simulator = GeminiSimulatorClient()
    for index, case in enumerate(cases, start=1):
        if _is_cancelled(manager, session_id):
            _log(session_id, stage, "showcase measurement cancelled mid-loop")
            return results
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
            drafter_prompt_version=drafter_prompt_version,
            drafter_prompt_text=drafter_prompt_text,
            playbook_override=(playbook_overrides or {}).get(_case_slice(case)),
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
    if _is_cancelled(manager, session_id):
        _log(session_id, "train_gepa", "showcase training skipped because session is cancelled")
        return []
    manager.set_stage(session_id, stage="train_gepa", total_cases=len(cases))
    recorder = OtelPhoenixRecorder()
    drafter = GeminiDrafterClient()
    judge = GeminiJudgeClient()
    trace_ids: list[str] = []
    for index, case in enumerate(cases, start=1):
        if _is_cancelled(manager, session_id):
            _log(session_id, "train_gepa", "showcase training cancelled mid-loop")
            return trace_ids
        manager.set_stage(
            session_id,
            stage="train_gepa",
            current_case_id=case.case_id,
            completed_cases=index - 1,
            total_cases=len(cases),
        )
        run = run_evaluated_case(
            case.judge_case(dataset_split=dataset_split),
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
    slice_filters: list[str],
    train_split: str,
    holdout_split: str,
    max_rounds: int,
):
    store = LivePhoenixLearningStore()
    runner = LiveExperimentRunner(
        dataset=_dataset(cases),
        drafter_client=GeminiDrafterClient(),
        judge_client=PanelJudgeAdapter(judge_client=GeminiJudgeClient()),
    )
    coordinator = LearningCoordinator(
        store=store,
        runner=runner,
        reflection_client=GeminiReflectionClient(),
        slice_filter=slice_filters[0],
        slice_filters=slice_filters,
        train_split=train_split,
        holdout_split=holdout_split,
        max_rounds=max_rounds,
    )
    return coordinator.optimize()


def _candidate_prompt(proposal: PromotionProposal) -> tuple[str | None, str | None]:
    comp = proposal.candidate.components.get("drafter_system_prompt")
    if comp is None:
        return None, None
    return comp.version, comp.text


def _candidate_playbooks(proposal: PromotionProposal) -> dict[str, dict]:
    out: dict[str, dict] = {}
    for comp_id, comp in proposal.candidate.components.items():
        if not comp_id.startswith("playbook:") or comp.playbook is None:
            continue
        out[comp_id.removeprefix("playbook:")] = comp.playbook
    return out


def _regression_summary(before: list[dict], after: list[dict]) -> str | None:
    before_by_case = {str(item.get("case_id")): item for item in before}
    after_by_case = {str(item.get("case_id")): item for item in after}
    common_ids = sorted(set(before_by_case) & set(after_by_case))
    if not common_ids:
        return None

    flipped = [
        case_id
        for case_id in common_ids
        if before_by_case[case_id].get("verdict") == "APPROVE"
        and after_by_case[case_id].get("verdict") == "DENY"
    ]

    def _mean(items: list[dict]) -> float:
        values: list[float] = []
        for item in items:
            try:
                values.append(float(item.get("score")))
            except (TypeError, ValueError):
                continue
        return sum(values) / len(values) if values else 0.0

    before_mean = _mean([before_by_case[case_id] for case_id in common_ids])
    after_mean = _mean([after_by_case[case_id] for case_id in common_ids])
    if flipped or after_mean < before_mean - 0.05:
        return (
            "Post-measure score dropped — consider rolling back. "
            f"Before={before_mean:.2f}, after={after_mean:.2f}, "
            f"approve-to-deny flips={len(flipped)}."
        )
    return None


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
        quick_train = manifest.quick_train
        quick_holdout = manifest.quick_holdout
        slice_filters = _slice_filters(quick_train)
        _measure(manager, session_id, phase="pre", cases=quick_holdout)
        _measure(manager, session_id, phase="training_pre", cases=quick_train)
        trace_ids = _seed_training_signal(
            manager,
            session_id,
            cases=quick_train,
            dataset_split=train_split,
        )
        session = manager.get(session_id)
        session.diagnostics.phoenix_trace_ids = trace_ids
        manager._save(session)
        proposal = _optimize(
            cases=quick_train,
            slice_filters=slice_filters,
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
        candidate_prompt_version, candidate_prompt_text = _candidate_prompt(proposal)
        _measure(
            manager,
            session_id,
            phase="training_post",
            cases=quick_train,
            drafter_prompt_version=candidate_prompt_version,
            drafter_prompt_text=candidate_prompt_text,
            playbook_overrides=_candidate_playbooks(proposal),
        )
        manager.mark_needs_approval(session_id, proposal=proposal.model_dump())
    except Exception as exc:
        manager.fail_stage(
            session_id,
            stage="train_gepa",
            code=exc.__class__.__name__,
            message=str(exc) or "Showcase quick run failed.",
            retryable=True,
        )


def run_serious_session(session_id: str) -> None:
    manager = ShowcaseSessionManager()
    manifest = load_showcase_manifest()
    train_split = f"showcase_serious_train_{session_id}"
    try:
        if not _creds_available():
            manager.fail_stage(
                session_id,
                stage="queued",
                code="missing_live_credentials",
                message="Live serious run requires PHOENIX_API_KEY and Google ADC.",
                retryable=True,
            )
            return
        serious_train = manifest.serious_train
        serious_holdout = manifest.serious_holdout
        slice_filters = _slice_filters(serious_train)
        _measure(manager, session_id, phase="pre", cases=serious_holdout)
        _measure(manager, session_id, phase="training_pre", cases=serious_train)
        trace_ids = _seed_training_signal(
            manager,
            session_id,
            cases=serious_train,
            dataset_split=train_split,
        )
        session = manager.get(session_id)
        session.diagnostics.phoenix_trace_ids = trace_ids
        manager._save(session)
        proposal = _optimize(
            cases=serious_train,
            slice_filters=slice_filters,
            train_split=train_split,
            holdout_split=train_split,
            max_rounds=3,
        )
        if proposal is None:
            manager.fail_stage(
                session_id,
                stage="train_gepa",
                code="no_learning_signal",
                message="Phoenix did not return learning signal for this serious run.",
                retryable=True,
            )
            return
        candidate_prompt_version, candidate_prompt_text = _candidate_prompt(proposal)
        _measure(
            manager,
            session_id,
            phase="training_post",
            cases=serious_train,
            drafter_prompt_version=candidate_prompt_version,
            drafter_prompt_text=candidate_prompt_text,
            playbook_overrides=_candidate_playbooks(proposal),
        )
        manager.mark_needs_approval(session_id, proposal=proposal.model_dump())
    except Exception as exc:
        manager.fail_stage(
            session_id,
            stage="train_gepa",
            code=exc.__class__.__name__,
            message=str(exc) or "Showcase serious run failed.",
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
        PromotionStack().push_checkpoint(
            run_type=session.run_type,
            session_id=session_id,
            candidate=proposal.candidate,
        )
        LivePhoenixLearningStore().register_promotion(proposal.candidate, audit)
        session = manager.get(session_id)
        session.approved_by = approver
        manager._save(session)
        post_cases = manifest.quick_holdout if session.run_type == "quick" else manifest.serious_holdout
        post_results = _measure(manager, session_id, phase="post", cases=post_cases)
        session = manager.get(session_id)
        manager.set_regression_warning(
            session_id,
            summary=_regression_summary(session.pre_measure_results, post_results),
        )
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
