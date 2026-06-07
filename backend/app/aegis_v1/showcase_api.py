from __future__ import annotations

import os
import threading
from contextlib import contextmanager
from typing import Literal

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.aegis_v1.showcase_manifest import ShowcaseManifest, load_showcase_manifest
from app.aegis_v1.showcase_session import (
    SessionBusyError,
    SessionLockedError,
    ShowcaseSession,
    ShowcaseSessionManager,
)
from app.evals.part_a.evaluated_run import run_evaluated_case
from app.evals.part_a.llm_judges import GeminiJudgeClient, OfflineHeuristicJudgeClient
from app.evals.part_a.recorder import OtelPhoenixRecorder


router = APIRouter(prefix="/v1/showcase", tags=["showcase"])


class ShowcaseManifestResponse(BaseModel):
    benchmark_id: str
    version: str
    quick_slice: str
    quick_train: list[dict]
    quick_holdout: list[dict]
    serious_train_count: int
    serious_holdout: list[dict]


class ApprovalRequest(BaseModel):
    approver: str = "pm"


class RejectionRequest(BaseModel):
    reviewer: str = "pm"


def _manager() -> ShowcaseSessionManager:
    return ShowcaseSessionManager()


def _autorun_enabled() -> bool:
    return os.environ.get("AEGIS_SHOWCASE_AUTORUN", "true").lower() not in {
        "0",
        "false",
        "no",
    }


def _launch_quick(session_id: str) -> None:
    if not _autorun_enabled():
        return
    from app.aegis_v1.showcase_runner import run_quick_session

    thread = threading.Thread(target=run_quick_session, args=(session_id,), daemon=True)
    thread.start()


def _launch_serious(session_id: str) -> None:
    if not _autorun_enabled():
        return
    from app.aegis_v1.showcase_runner import run_serious_session

    thread = threading.Thread(target=run_serious_session, args=(session_id,), daemon=True)
    thread.start()


@router.get("/manifest", response_model=ShowcaseManifestResponse)
def get_manifest() -> ShowcaseManifestResponse:
    manifest: ShowcaseManifest = load_showcase_manifest()
    return ShowcaseManifestResponse(
        benchmark_id=manifest.benchmark_id,
        version=manifest.version,
        quick_slice=manifest.quick_slice,
        quick_train=[case.model_dump() for case in manifest.quick_train],
        quick_holdout=[case.model_dump() for case in manifest.quick_holdout],
        serious_train_count=len(manifest.serious_train),
        serious_holdout=[case.model_dump() for case in manifest.serious_holdout],
    )


@router.post("/runs/quick", response_model=ShowcaseSession)
def start_quick_run() -> ShowcaseSession:
    manifest = load_showcase_manifest()
    session = _manager().start_quick(
        case_ids=[case.case_id for case in manifest.quick_train + manifest.quick_holdout]
    )
    _launch_quick(session.session_id)
    return session


@router.post("/runs/serious", response_model=ShowcaseSession)
def start_serious_run() -> ShowcaseSession:
    manifest = load_showcase_manifest()
    try:
        session = _manager().start_serious(
            case_ids=[case.case_id for case in manifest.serious_train + manifest.serious_holdout]
        )
        _launch_serious(session.session_id)
        return session
    except SessionLockedError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.get("/runs/{session_id}", response_model=ShowcaseSession)
def get_run(session_id: str) -> ShowcaseSession:
    try:
        return _manager().get(session_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail="showcase session not found") from exc


@router.post("/runs/{session_id}/cancel", response_model=ShowcaseSession)
def cancel_run(session_id: str) -> ShowcaseSession:
    try:
        return _manager().cancel(session_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail="showcase session not found") from exc


@router.post("/runs/{session_id}/resume", response_model=ShowcaseSession)
def resume_run(session_id: str) -> ShowcaseSession:
    """Resume a failed-but-retryable run from its last checkpoint. Completed
    stages (measurements, training signal, optimization) are reused, not redone."""
    manager = _manager()
    try:
        session = manager.get(session_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail="showcase session not found") from exc
    try:
        manager.mark_resumable(session_id)
    except SessionBusyError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    if session.run_type == "quick":
        _launch_quick(session_id)
    else:
        _launch_serious(session_id)
    return manager.get(session_id)


@router.post("/runs/{session_id}/approve", response_model=ShowcaseSession)
def approve_run(session_id: str, req: ApprovalRequest) -> ShowcaseSession:
    manager = _manager()
    try:
        session = manager.get(session_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail="showcase session not found") from exc
    if session.cancelled:
        raise HTTPException(status_code=409, detail="cancelled runs cannot be promoted")
    if not session.proposal:
        raise HTTPException(status_code=409, detail="no GEPA proposal is ready for approval")
    from app.aegis_v1.showcase_runner import approve_session

    approve_session(session_id, approver=req.approver)
    return manager.get(session_id)


@router.post("/runs/{session_id}/reject", response_model=ShowcaseSession)
def reject_run(session_id: str, req: RejectionRequest) -> ShowcaseSession:
    manager = _manager()
    try:
        session = manager.get(session_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail="showcase session not found") from exc
    if session.cancelled:
        raise HTTPException(status_code=409, detail="cancelled runs cannot be rejected")
    if not session.proposal:
        raise HTTPException(status_code=409, detail="no GEPA proposal is ready for rejection")
    return manager.mark_rejected(session_id, reviewer=req.reviewer)


@router.get("/rollback-target")
def get_rollback_target() -> dict | None:
    from app.aegis_v1.showcase_rollback import PromotionStack

    target = PromotionStack().rollback_target()
    return target.model_dump() if target is not None else None


@router.post("/rollback")
def rollback_latest() -> dict:
    from app.aegis_v1.showcase_rollback import PromotionStack

    try:
        return PromotionStack().rollback_latest().model_dump()
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


class ShowcaseEvaluateRequest(BaseModel):
    case_id: str
    denial_letter_text: str
    clinical_context: str = ""

    baseline_prompt_version: str = "drafter_v1"
    candidate_prompt_version: str = "drafter_v2"

    judge_mode: Literal["official", "fast"] = "official"
    run_counterfactual: bool = True


class ShowcaseSide(BaseModel):
    composite: float = 0.0
    verdict: Literal["APPROVE", "DENY"] = "DENY"
    letter_excerpt: str = ""


class ShowcaseCounterfactual(BaseModel):
    on_composite: float = 0.0
    off_composite: float = 0.0


class ShowcaseBundle(BaseModel):
    case_id: str
    measured: bool = True
    v1: ShowcaseSide
    v3: ShowcaseSide
    lift_relative_pct: float = 0.0
    what_changed: list[str] = Field(default_factory=list)
    counterfactual: ShowcaseCounterfactual
    phoenix_url: str | None = None


@contextmanager
def _temp_env(key: str, value: str):
    old = os.environ.get(key)
    os.environ[key] = value
    try:
        yield
    finally:
        if old is None:
            os.environ.pop(key, None)
        else:
            os.environ[key] = old


def _excerpt(letter: str, limit: int = 520) -> str:
    compact = " ".join((letter or "").split())
    return compact[:limit] + ("…" if len(compact) > limit else "")


def _composite(panel_weighted_quality: float | None, simulator_score: float | None = None) -> float:
    """Return a demo-friendly composite.

    If the teacher panel hard-gates (e.g., missing structured citations),
    fall back to the simulator's deterministic score so the UI still shows a
    meaningful before/after. Official runs should normally have panel scores.
    """
    if panel_weighted_quality is not None:
        return float(panel_weighted_quality)
    if simulator_score is not None:
        try:
            return float(simulator_score)
        except Exception:
            return 0.0
    return 0.0


def _lift(before: float, after: float) -> float:
    denom = before if before > 1e-6 else 1e-6
    return round(((after - before) / denom) * 100.0, 2)


def _what_changed(before: dict, after: dict) -> list[str]:
    b = dict(before.get("dimension_scores", {}) or {})
    a = dict(after.get("dimension_scores", {}) or {})
    out: list[str] = []
    for dim in sorted(set(b) | set(a)):
        bv = b.get(dim)
        av = a.get(dim)
        if isinstance(bv, int) and isinstance(av, int) and av != bv:
            direction = "up" if av > bv else "down"
            out.append(f"{dim.replace('_', ' ')}: {bv} → {av} ({direction})")
    return out[:6]


@router.post("/evaluate", response_model=ShowcaseBundle)
def evaluate_showcase(req: ShowcaseEvaluateRequest) -> ShowcaseBundle:
    """
    Demo-friendly, UI-triggerable evaluation:
    - Runs the same case with a baseline prompt vs a candidate prompt.
    - Uses either official Gemini judges or a fast diagnostic heuristic panel.
    - Logs the run + evaluations to Phoenix, and returns a direct Phoenix link.
    """

    from app.aegis_v1.drafter_client import GeminiDrafterClient
    from app.aegis_v1.simulator_client import GeminiSimulatorClient

    case_obj = {
        "case_id": req.case_id,
        "denial_letter_text": req.denial_letter_text,
        "clinical_context": req.clinical_context,
        "dataset_split": "benchmark",
    }

    recorder = OtelPhoenixRecorder()
    # For the hackathon demo, we want "official" runs to use the same Vertex-hosted
    # model family everywhere. Gemini 3.1 Pro is currently exposed on Vertex as a
    # preview model (suffix matters).
    location = os.environ.get("GOOGLE_CLOUD_LOCATION", "global")
    drafter_model = os.environ.get("AEGIS_DRAFTER_MODEL", "gemini-3.1-pro-preview")
    judge_model = os.environ.get("AEGIS_JUDGE_MODEL", "gemini-3.1-pro-preview")
    simulator_model = os.environ.get("AEGIS_SIMULATOR_MODEL", "gemini-3.1-pro-preview")

    simulator_client = GeminiSimulatorClient(model=simulator_model, location=location)
    drafter_client = GeminiDrafterClient(model=drafter_model, location=location)

    judge_client = (
        GeminiJudgeClient(
            model=judge_model,
            location=location,
        )
        if req.judge_mode == "official"
        else OfflineHeuristicJudgeClient()
    )

    baseline = run_evaluated_case(
        case_obj,
        recorder=recorder,
        drafter_client=drafter_client,
        judge_client=judge_client,
        simulator_client=simulator_client,
        drafter_prompt_version=req.baseline_prompt_version,
    )
    candidate = run_evaluated_case(
        case_obj,
        recorder=recorder,
        drafter_client=drafter_client,
        judge_client=judge_client,
        simulator_client=simulator_client,
        drafter_prompt_version=req.candidate_prompt_version,
    )

    bq = _composite(baseline.panel_report.weighted_quality)
    cq = _composite(candidate.panel_report.weighted_quality)
    lift = _lift(bq, cq)

    counter_on = cq
    counter_off = cq
    if req.run_counterfactual:
        with _temp_env("PHOENIX_MCP_ENABLED", "false"):
            off = run_evaluated_case(
                case_obj,
                recorder=recorder,
                drafter_client=drafter_client,
                judge_client=judge_client,
                simulator_client=simulator_client,
                drafter_prompt_version=req.candidate_prompt_version,
                run_simulator=False,
            )
            counter_off = _composite(off.panel_report.weighted_quality)

    host = os.environ.get("PHOENIX_HOST", "https://app.phoenix.arize.com").rstrip("/")
    phoenix_url = f"{host}/redirects/spans/{candidate.trace_ref}"

    return ShowcaseBundle(
        case_id=req.case_id,
        measured=True,
        v1=ShowcaseSide(
            composite=bq,
            verdict=(baseline.simulator_result or {}).get("verdict", "DENY"),
            letter_excerpt=_excerpt(
                baseline.appeal_package.get("appeal_package_draft", {}).get("appeal_letter", "")
            ),
        ),
        v3=ShowcaseSide(
            composite=cq,
            verdict=(candidate.simulator_result or {}).get("verdict", "DENY"),
            letter_excerpt=_excerpt(
                candidate.appeal_package.get("appeal_package_draft", {}).get("appeal_letter", "")
            ),
        ),
        lift_relative_pct=lift,
        what_changed=_what_changed(
            baseline.panel_report.model_dump(), candidate.panel_report.model_dump()
        ),
        counterfactual=ShowcaseCounterfactual(on_composite=counter_on, off_composite=counter_off),
        phoenix_url=phoenix_url,
    )
