from __future__ import annotations

import logging
from typing import Literal

from app.aegis_v1.appeal_phoenix_export import write_training_phoenix_checkpoint
from app.aegis_v1.phoenix_mode import PhoenixMode
from app.aegis_v1.pipeline import run_aegis_v1_pipeline
from app.aegis_v1.showcase_manifest import ShowcaseCase, load_showcase_manifest
from app.aegis_v1.showcase_rollback import PromotionStack
from app.aegis_v1.showcase_resilience import (
    failure_message,
    insufficient_training_message,
    min_training_cases_required,
    no_learning_signal_message,
)
from app.aegis_v1.showcase_session import ShowcaseSessionManager
from app.aegis_v1.simulator_client import AdkSimulatorClient
from app.aegis_v1.tools import case_parser, phoenix_mcp_lookup
from app.evals.part_a.evaluated_run import run_evaluated_case
from app.evals.part_a.llm_judges import GeminiJudgeClient
from app.evals.part_a.measurement_run import run_measurement_case
from app.evals.part_a.recorder import OtelPhoenixRecorder
from app.learning.coordinator import LearningCoordinator
from app.learning.experiment import LiveExperimentRunner
from app.learning.models import PromotionAudit, PromotionProposal
from app.learning.phoenix_live import LivePhoenixLearningStore
from app.learning.reflection_agent import AdkReflectionClient
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
    simulator = AdkSimulatorClient()
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
        # Per-case isolation: one bad case (LLM error, malformed response, etc.)
        # is recorded and skipped so the rest of the batch still completes,
        # instead of failing the whole session.
        try:
            result = run_measurement_case(
                _case_obj(case, dataset_split=f"showcase_{phase}_measure_{session_id}"),
                drafter_client=None,
                simulator_client=simulator,
                drafter_prompt_version=drafter_prompt_version,
                drafter_prompt_text=drafter_prompt_text,
                playbook_override=(playbook_overrides or {}).get(_case_slice(case)),
            )
        except Exception as exc:
            logger.warning(
                "measurement case failed; skipping",
                extra={
                    "session_id": session_id,
                    "showcase_stage": stage,
                    "case_id": case.case_id,
                },
                exc_info=True,
            )
            manager.record_case_failure(
                session_id,
                phase=f"measure_{phase}",
                case_id=case.case_id,
                error=str(exc) or exc.__class__.__name__,
            )
            continue
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
    from app import gemini_retry

    recorder = OtelPhoenixRecorder()
    trace_ids: list[str] = []
    for index, case in enumerate(cases, start=1):
        if index > 1:
            gemini_retry.pace_gemini_call()
        judge = GeminiJudgeClient()
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
        # Per-case isolation: a failed judge/draft on one case is recorded and
        # skipped so the training stage still gathers signal from the rest.
        try:
            run = run_evaluated_case(
                case.judge_case(dataset_split=dataset_split),
                recorder=recorder,
                drafter_client=None,
                judge_client=judge,
                run_simulator=False,
                run_mode="gepa_seed",
                trace_tags={
                    "memory_eligible": "true",
                    "candidate_id": "seed",
                    "run_mode": "gepa_seed",
                    "dataset_split": dataset_split,
                },
            )
        except Exception as exc:
            logger.warning(
                "training-signal case failed; skipping",
                extra={
                    "session_id": session_id,
                    "showcase_stage": "train_gepa",
                    "case_id": case.case_id,
                },
                exc_info=True,
            )
            manager.record_case_failure(
                session_id,
                phase="train_gepa",
                case_id=case.case_id,
                error=str(exc) or exc.__class__.__name__,
            )
            continue
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
        judge_client=GeminiJudgeClient(),
        recorder=OtelPhoenixRecorder(),
        memory_eligible=False,
        run_mode="gepa_optimize_candidate",
    )
    coordinator = LearningCoordinator(
        store=store,
        runner=runner,
        reflection_client=AdkReflectionClient(),
        slice_filter=slice_filters[0],
        slice_filters=slice_filters,
        train_split=train_split,
        holdout_split=holdout_split,
        max_rounds=max_rounds,
    )
    return coordinator.optimize()


def _write_training_checkpoint(
    manager: ShowcaseSessionManager,
    session_id: str,
    *,
    cases: list[ShowcaseCase],
    train_split: str,
    checkpoint: Literal["a", "b"],
    proposal: PromotionProposal | None = None,
) -> list[str]:
    if not cases:
        return []
    if _is_cancelled(manager, session_id):
        return []
    case = cases[0]
    parsed = case_parser(
        denial_text=case.denial_letter_text,
        clinical_context=case.clinical_context,
        case_id=case.case_id,
    )
    slice_key = f"{parsed['insurer']}:{parsed['denial_type']}"
    prompt_version: str | None = None
    prompt_text: str | None = None
    playbook_override: dict | None = None
    if checkpoint == "b" and proposal is not None:
        prompt_version, prompt_text = _candidate_prompt(proposal)
        playbook_override = _candidate_playbooks(proposal).get(slice_key)
    package = run_aegis_v1_pipeline(
        denial_text=case.denial_letter_text,
        clinical_context=case.clinical_context,
        case_id=case.case_id,
        dataset_split=train_split,
        run_mode=f"training_checkpoint_{checkpoint}",
        drafter_client=None,
        drafter_prompt_version=prompt_version,
        drafter_prompt_text=prompt_text,
        playbook_override=playbook_override,
        phoenix_mode=PhoenixMode.TRAINING_READWRITE,
    )
    trace_ref = write_training_phoenix_checkpoint(
        package,
        checkpoint=checkpoint,
        train_split=train_split,
    )
    return [trace_ref] if trace_ref else []


def _eval_post_gepa_candidate(
    manager: ShowcaseSessionManager,
    session_id: str,
    *,
    cases: list[ShowcaseCase],
    train_split: str,
    proposal: PromotionProposal,
) -> list[str]:
    if _is_cancelled(manager, session_id):
        return []
    from app import gemini_retry

    recorder = OtelPhoenixRecorder()
    prompt_version, prompt_text = _candidate_prompt(proposal)
    playbooks = _candidate_playbooks(proposal)
    trace_ids: list[str] = []
    manager.set_stage(session_id, stage="train_gepa", total_cases=len(cases))
    for index, case in enumerate(cases, start=1):
        if index > 1:
            gemini_retry.pace_gemini_call()
        if _is_cancelled(manager, session_id):
            return trace_ids
        parsed = case_parser(
            denial_text=case.denial_letter_text,
            clinical_context=case.clinical_context,
            case_id=case.case_id,
        )
        slice_key = f"{parsed['insurer']}:{parsed['denial_type']}"
        try:
            run = run_evaluated_case(
                case.judge_case(dataset_split=train_split),
                recorder=recorder,
                drafter_client=None,
                judge_client=GeminiJudgeClient(),
                run_simulator=False,
                drafter_prompt_version=prompt_version,
                drafter_prompt_text=prompt_text,
                playbook_override=playbooks.get(slice_key),
                run_mode="training_checkpoint_post_gepa",
                trace_tags={
                    "memory_eligible": "true",
                    "candidate_id": proposal.candidate.candidate_id,
                    "run_mode": "training_checkpoint_post_gepa",
                    "dataset_split": train_split,
                },
            )
        except Exception as exc:
            logger.warning(
                "post-gepa candidate eval failed; skipping",
                extra={"session_id": session_id, "case_id": case.case_id},
                exc_info=True,
            )
            manager.record_case_failure(
                session_id,
                phase="train_gepa_candidate",
                case_id=case.case_id,
                error=str(exc) or exc.__class__.__name__,
            )
            continue
        trace_ids.append(run.trace_ref)
        manager.set_stage(
            session_id,
            stage="train_gepa",
            current_case_id=case.case_id,
            completed_cases=index,
            total_cases=len(cases),
        )
    return trace_ids


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


def _checkpoint(manager: ShowcaseSessionManager, session_id: str):
    return manager.get(session_id).checkpoint


def _run_learning_session(
    session_id: str,
    *,
    run_type: str,
    train_cases: list[ShowcaseCase],
    holdout_cases: list[ShowcaseCase],
    max_rounds: int,
    train_split: str,
) -> None:
    """Shared quick/serious flow. Checkpoint-aware: each stage is skipped if the
    session checkpoint already marks it done, so a failed/interrupted run can be
    resumed (via the resume endpoint) without redoing completed work."""
    manager = ShowcaseSessionManager()
    try:
        if not _creds_available():
            manager.fail_stage(
                session_id,
                stage="queued",
                code="missing_live_credentials",
                message=failure_message("missing_live_credentials"),
                retryable=True,
            )
            return
        slice_filters = _slice_filters(train_cases)

        if not _checkpoint(manager, session_id).pre_measure_done:
            _measure(manager, session_id, phase="pre", cases=holdout_cases)
            manager.save_checkpoint(session_id, pre_measure_done=True)

        if not _checkpoint(manager, session_id).training_pre_done:
            _measure(manager, session_id, phase="training_pre", cases=train_cases)
            manager.save_checkpoint(session_id, training_pre_done=True)

        if not _checkpoint(manager, session_id).training_checkpoint_a_done:
            _write_training_checkpoint(
                manager,
                session_id,
                cases=train_cases,
                train_split=train_split,
                checkpoint="a",
            )
            manager.save_checkpoint(session_id, training_checkpoint_a_done=True)

        if not _checkpoint(manager, session_id).training_signal_done:
            trace_ids = _seed_training_signal(
                manager,
                session_id,
                cases=train_cases,
                dataset_split=train_split,
            )
            session = manager.get(session_id)
            session.diagnostics.phoenix_trace_ids = trace_ids
            manager._save(session)
            manager.save_checkpoint(
                session_id,
                training_signal_done=True,
                training_trace_ids=trace_ids,
            )
        else:
            trace_ids = _checkpoint(manager, session_id).training_trace_ids

        required = min_training_cases_required(len(train_cases))
        if len(trace_ids) < required:
            manager.fail_stage(
                session_id,
                stage="train_gepa",
                code="insufficient_training_data",
                message=insufficient_training_message(
                    succeeded=len(trace_ids),
                    required=required,
                    total=len(train_cases),
                ),
                retryable=True,
            )
            return

        if not _checkpoint(manager, session_id).optimize_done:
            proposal = _optimize(
                cases=train_cases,
                slice_filters=slice_filters,
                train_split=train_split,
                holdout_split=train_split,
                max_rounds=max_rounds,
            )
            if proposal is None:
                manager.fail_stage(
                    session_id,
                    stage="train_gepa",
                    code="no_learning_signal",
                    message=no_learning_signal_message(trace_count=len(trace_ids)),
                    retryable=True,
                )
                return
            manager.set_proposal(session_id, proposal=proposal.model_dump())
            manager.save_checkpoint(session_id, optimize_done=True)
        else:
            proposal = PromotionProposal.model_validate(
                manager.get(session_id).proposal
            )

        if not _checkpoint(manager, session_id).train_gepa_candidate_done:
            candidate_trace_ids = _eval_post_gepa_candidate(
                manager,
                session_id,
                cases=train_cases,
                train_split=train_split,
                proposal=proposal,
            )
            session = manager.get(session_id)
            session.diagnostics.phoenix_trace_ids.extend(candidate_trace_ids)
            manager._save(session)
            manager.save_checkpoint(session_id, train_gepa_candidate_done=True)

        if not _checkpoint(manager, session_id).training_checkpoint_b_done:
            _write_training_checkpoint(
                manager,
                session_id,
                cases=train_cases,
                train_split=train_split,
                checkpoint="b",
                proposal=proposal,
            )
            manager.save_checkpoint(session_id, training_checkpoint_b_done=True)

        if not _checkpoint(manager, session_id).training_post_done:
            candidate_prompt_version, candidate_prompt_text = _candidate_prompt(proposal)
            _measure(
                manager,
                session_id,
                phase="training_post",
                cases=train_cases,
                drafter_prompt_version=candidate_prompt_version,
                drafter_prompt_text=candidate_prompt_text,
                playbook_overrides=_candidate_playbooks(proposal),
            )
            manager.save_checkpoint(session_id, training_post_done=True)

        manager.mark_needs_approval(session_id, proposal=proposal.model_dump())
    except Exception as exc:
        manager.fail_stage(
            session_id,
            stage="train_gepa",
            code=exc.__class__.__name__,
            message=(
                f"The {run_type} run hit an unexpected error and stopped. "
                f"Technical detail: {str(exc) or exc.__class__.__name__}"
            ),
            retryable=True,
        )


def run_quick_session(session_id: str) -> None:
    manifest = load_showcase_manifest()
    _run_learning_session(
        session_id,
        run_type="quick",
        train_cases=manifest.quick_train,
        holdout_cases=manifest.quick_holdout,
        max_rounds=1,
        train_split=f"showcase_quick_train_{session_id}",
    )


def run_serious_session(session_id: str) -> None:
    manifest = load_showcase_manifest()
    _run_learning_session(
        session_id,
        run_type="serious",
        train_cases=manifest.serious_train,
        holdout_cases=manifest.serious_holdout,
        max_rounds=3,
        train_split=f"showcase_serious_train_{session_id}",
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
                message=failure_message("cancelled"),
                retryable=False,
            )
            return
        if not session.proposal:
            manager.fail_stage(
                session_id,
                stage="promote",
                code="missing_proposal",
                message=failure_message("missing_proposal"),
                retryable=False,
            )
            return
        proposal = PromotionProposal.model_validate(session.proposal)
        manager.set_stage(session_id, stage="promote", status="running")
        _log(session_id, "promote", "showcase promotion started", approver=approver)

        # Promotion is checkpointed so a retried/resumed approval (e.g. after an
        # instance restart mid post-measure) never registers the candidate twice.
        if not _checkpoint(manager, session_id).promotion_done:
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
            manager.save_checkpoint(session_id, promotion_done=True)

        # Post-measure on the holdout runs after promotion to detect regressions
        # (rollback stays available). The whole phase is checkpointed; on resume
        # the holdout is simply re-measured from the persisted pre-measure baseline.
        if not _checkpoint(manager, session_id).post_measure_done:
            post_cases = (
                manifest.quick_holdout
                if session.run_type == "quick"
                else manifest.serious_holdout
            )
            post_results = _measure(manager, session_id, phase="post", cases=post_cases)
            session = manager.get(session_id)
            manager.set_regression_warning(
                session_id,
                summary=_regression_summary(session.pre_measure_results, post_results),
            )
            manager.save_checkpoint(session_id, post_measure_done=True)

        manager.mark_success(session_id)
        _log(session_id, "measure_after", "showcase approved run completed")
    except Exception as exc:
        manager.fail_stage(
            session_id,
            stage="promote",
            code=exc.__class__.__name__,
            message=(
                "Approval/promotion hit an unexpected error and stopped. "
                f"Technical detail: {str(exc) or exc.__class__.__name__}"
            ),
            retryable=True,
        )
