#!/usr/bin/env python3
"""Full guinea-pig GEPA run (preview-shaped) for a single case, then auto-approve.

Runs one GEPA round mutating drafter, question agent, insurer playbook, and US geo
playbook. On success, promotes the candidate to live prompt/playbook files so a
follow-up ``run_guinea_pig_measure.py`` uses the optimized versions.

Requires Phoenix telemetry (``setup_telemetry``) so judge traces reach project
``default`` before GEPA reads them.

Usage (from backend/):
    env UV_CACHE_DIR=/tmp/uv-cache uv run python scripts/run_guinea_pig_gepa.py \\
        --case ../eval/cases/drafts/guinea-pigs/case_127_aetna_priorauth.json
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))

from guinea_pig_common import (
    OUTPUT_ROOT,
    REPO_ROOT,
    apply_ipv4_patch,
    estimate_cost_usd,
    install_token_tracker,
    load_env,
    ping_phoenix,
    setup_phoenix_telemetry,
)

apply_ipv4_patch()

DEFAULT_CASE = (
    REPO_ROOT / "eval/cases/drafts/guinea-pigs/case_127_aetna_priorauth.json"
)


def _clean_output_root() -> None:
    if not OUTPUT_ROOT.exists():
        OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
        return
    for child in OUTPUT_ROOT.iterdir():
        if child.name.startswith("."):
            continue
        if child.is_dir():
            shutil.rmtree(child)
        else:
            child.unlink()


def _write_candidate_artifacts(out_dir: Path, proposal: dict[str, Any]) -> None:
    candidate = proposal.get("candidate") or {}
    components = candidate.get("components") or {}
    promoted_dir = out_dir / "promoted"
    promoted_dir.mkdir(parents=True, exist_ok=True)

    drafter = components.get("drafter_system_prompt") or {}
    if drafter.get("text"):
        (promoted_dir / f"{drafter.get('version', 'drafter')}.md").write_text(
            str(drafter["text"]), encoding="utf-8"
        )

    question_agent = components.get("question_agent_system_prompt") or {}
    if question_agent.get("text"):
        (promoted_dir / f"{question_agent.get('version', 'question_agent')}.md").write_text(
            str(question_agent["text"]), encoding="utf-8"
        )

    for comp_id, comp in components.items():
        if not comp_id.startswith("playbook:") or not comp.get("playbook"):
            continue
        slug = comp_id.removeprefix("playbook:").replace(":", "__")
        (promoted_dir / f"{slug}__{comp.get('version', 'v')}.json").write_text(
            json.dumps(comp["playbook"], indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

    geo = components.get("geo_playbook:us") or {}
    if geo.get("playbook"):
        (promoted_dir / f"us_playbook__{geo.get('version', 'v')}.json").write_text(
            json.dumps(geo["playbook"], indent=2, ensure_ascii=False),
            encoding="utf-8",
        )


def _summary_md(
    *,
    case_id: str,
    session_status: str,
    approved: bool,
    cost: dict[str, Any],
    proposal: dict[str, Any] | None,
    phoenix_trace_ids: list[str],
) -> str:
    lift = ""
    if proposal:
        before = float((proposal.get("before") or {}).get("composite") or 0)
        after = float((proposal.get("after") or {}).get("composite") or 0)
        vetoes = proposal.get("vetoes") or []
        lift = (
            f"- Judge composite: {before:.3f} → {after:.3f}\n"
            f"- Vetoes: {vetoes or 'none'}\n"
        )
    traces = ", ".join(phoenix_trace_ids) if phoenix_trace_ids else "(none recorded)"
    return f"""# Guinea pig GEPA run — {case_id}

- **Status:** {session_status}
- **Auto-approved:** {approved}
- **GEPA rounds:** 1 (drafter + question agent + insurer playbook + US geo)
- **Phoenix project:** default
- **Phoenix trace ids:** {traces}
- **Estimated Gemini cost:** ${cost['estimated_total_usd']} ({cost['total_tokens']} tokens, {cost['gemini_calls']} tracked calls)
- **Post-promote holdout measure:** skipped (run `run_guinea_pig_measure.py` next)

{lift}
## Artifacts

- `session.json` — full showcase session state
- `proposal.json` — GEPA promotion proposal
- `promotion_preview.json` — human-readable diff preview
- `measurement_pre.json` / `measurement_training_pre.json` / `measurement_training_post.json`
- `cost_summary.json` — token + USD estimate (partial; ADK not tracked)
- `promoted/` — candidate component snapshots

Not legal or medical advice. Draft assistance only.
"""


def main() -> None:
    parser = argparse.ArgumentParser(description="Guinea pig full GEPA + auto-approve.")
    parser.add_argument("--case", default=str(DEFAULT_CASE))
    parser.add_argument("--approver", default="guinea_pig_cli")
    parser.add_argument(
        "--no-approve",
        action="store_true",
        help="stop at needs_approval without promoting to live files",
    )
    parser.add_argument(
        "--keep-prior-runs",
        action="store_true",
        help="do not delete existing folders under eval/GUINEA-PIG-RUNS/",
    )
    args = parser.parse_args()

    load_env(require_phoenix=True)
    # Must run before any evaluated_case / showcase imports (mirrors main_v1.py).
    setup_phoenix_telemetry()
    phoenix_ping = ping_phoenix()
    print(json.dumps({"phoenix_preflight": phoenix_ping}, indent=2), flush=True)
    token_records = install_token_tracker()

    try:
        import google.auth

        google.auth.default()
    except Exception as exc:
        sys.exit(f"Google ADC missing: {exc}")

    if not args.keep_prior_runs:
        _clean_output_root()

    # App imports intentionally deferred until after setup_phoenix_telemetry().
    from app.aegis_v1.showcase_manifest import load_showcase_case_from_path
    from app.aegis_v1.showcase_runner import (
        approve_guinea_pig_session,
        run_guinea_pig_session,
    )
    from app.aegis_v1.showcase_session import ShowcaseSessionManager

    case_path = Path(args.case)
    case = load_showcase_case_from_path(case_path)
    case_id = case.case_id

    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out_dir = OUTPUT_ROOT / f"{case_id}_gepa_{stamp}"
    out_dir.mkdir(parents=True, exist_ok=True)
    ledger_dir = out_dir / "session_ledger"
    os.environ["AEGIS_SHOWCASE_LEDGER_DIR"] = str(ledger_dir)

    manager = ShowcaseSessionManager(ledger_dir=ledger_dir)
    session = manager.start_quick(case_ids=[case.case_id])

    run_guinea_pig_session(session.session_id, case=case)
    session = manager.get(session.session_id)

    approved = False
    if session.status == "needs_approval" and not args.no_approve:
        approve_guinea_pig_session(session.session_id, approver=args.approver)
        session = manager.get(session.session_id)
        approved = session.status == "successful"
    elif session.status == "successful":
        approved = bool(session.approved_by)

    cost = estimate_cost_usd(token_records)
    trace_ids = list(session.diagnostics.phoenix_trace_ids or [])

    (out_dir / "session.json").write_text(
        json.dumps(session.model_dump(), indent=2, default=str),
        encoding="utf-8",
    )
    if session.proposal:
        (out_dir / "proposal.json").write_text(
            json.dumps(session.proposal, indent=2, default=str),
            encoding="utf-8",
        )
        _write_candidate_artifacts(out_dir, session.proposal)
    if session.promotion_preview:
        (out_dir / "promotion_preview.json").write_text(
            json.dumps(session.promotion_preview, indent=2, default=str),
            encoding="utf-8",
        )

    phase_files = {
        "measurement_pre.json": session.pre_measure_results,
        "measurement_training_pre.json": session.training_pre_measure_results,
        "measurement_training_post.json": session.training_post_measure_results,
    }
    for name, payload in phase_files.items():
        (out_dir / name).write_text(
            json.dumps(payload, indent=2, default=str),
            encoding="utf-8",
        )

    (out_dir / "cost_summary.json").write_text(
        json.dumps(cost, indent=2),
        encoding="utf-8",
    )
    (out_dir / "run_meta.json").write_text(
        json.dumps(
            {
                "case_path": str(case_path),
                "case_id": case_id,
                "run_type": "guinea_pig_gepa",
                "gepa_rounds": 1,
                "phoenix_preflight": phoenix_ping,
                "phoenix_project": "default",
                "phoenix_trace_ids": trace_ids,
                "mutate_targets": [
                    "drafter_system_prompt",
                    "question_agent_system_prompt",
                    "insurer_playbook",
                    "geo_playbook:us",
                ],
                "auto_approved": approved,
                "approver": args.approver if approved else None,
                "session_id": session.session_id,
                "timestamp_utc": stamp,
                "estimated_cost_usd": cost["estimated_total_usd"],
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    (out_dir / "summary.md").write_text(
        _summary_md(
            case_id=case_id,
            session_status=session.status,
            approved=approved,
            cost=cost,
            proposal=session.proposal,
            phoenix_trace_ids=trace_ids,
        ),
        encoding="utf-8",
    )

    result = {
        "output_dir": str(out_dir),
        "session_id": session.session_id,
        "status": session.status,
        "approved": approved,
        "proposal_vetoes": (session.proposal or {}).get("vetoes"),
        "phoenix_trace_ids": trace_ids,
        "cost": cost,
    }
    print(json.dumps(result, indent=2))

    if session.status == "failed":
        error = session.diagnostics.last_error
        detail = error.message if error else "unknown error"
        sys.exit(f"GEPA run failed: {detail}")
    if session.status == "needs_approval" and args.no_approve:
        sys.exit("Stopped at needs_approval (--no-approve). Promote manually or re-run.")
    if not approved and session.status != "successful":
        sys.exit(f"GEPA finished with status={session.status} but promotion did not complete.")


if __name__ == "__main__":
    main()
