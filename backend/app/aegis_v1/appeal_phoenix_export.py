from __future__ import annotations

import copy
import logging
import os
from typing import Any

from app.aegis_v1.phoenix_mode import PhoenixMode, can_write_phoenix
from app.aegis_v1.redaction import redact_identifiers
from app.evals.part_a.recorder import InMemoryPhoenixRecorder, OtelPhoenixRecorder, PhoenixRecorder

logger = logging.getLogger(__name__)


def _scrub_letter_with_agent(text: str) -> str:
    """Optional LLM scrubber pass (plan §6). Skipped when env or offline."""
    if os.environ.get("AEGIS_SKIP_SCRUBBER", "").lower() in {"1", "true", "yes"}:
        return text
    try:
        from app.aegis_v1.adk_runtime import collect_text, run_llm_agent_sync
        from app.aegis_v1.redaction_scrubber_agent import build_redaction_scrubber_agent

        agent = build_redaction_scrubber_agent()
        result = run_llm_agent_sync(
            agent,
            app_name="aegis_v1",
            user_id="redaction_scrubber",
            message=text,
        )
        scrubbed = collect_text(result.get("events", [])).strip()
        return scrubbed or text
    except Exception:
        logger.warning("redaction scrubber failed; using rule-based text only", exc_info=True)
        return text


def build_redacted_appeal_package(
    appeal_package: dict[str, Any],
    *,
    denial_text: str,
    clinical_context: str,
    use_scrubber: bool = True,
) -> dict[str, Any]:
    """Build a Phoenix-safe copy of an appeal package (/appeal export only)."""
    pkg = copy.deepcopy(appeal_package)
    draft = pkg.get("appeal_package_draft") or {}
    letter = str(draft.get("appeal_letter", ""))
    rule_redacted = redact_identifiers(letter).text
    draft["appeal_letter"] = (
        _scrub_letter_with_agent(rule_redacted) if use_scrubber else rule_redacted
    )
    pkg["appeal_package_draft"] = draft

    parsed = dict(pkg.get("parsed_case") or {})
    if denial_text:
        parsed["denial_text"] = redact_identifiers(denial_text).text
    if clinical_context:
        parsed["clinical_context"] = redact_identifiers(clinical_context).text
    pkg["parsed_case"] = parsed
    return pkg


def write_appeal_phoenix_export(
    appeal_package: dict[str, Any],
    *,
    denial_text: str = "",
    clinical_context: str = "",
    recorder: PhoenixRecorder | None = None,
    use_scrubber: bool = True,
    phoenix_mode: PhoenixMode = PhoenixMode.APPEAL,
) -> str | None:
    """Write a redacted appeal run to Phoenix (/appeal path — D8 post-draft export).

    Returns trace_ref on success, None if recording is skipped or fails.
    """
    if not can_write_phoenix(phoenix_mode):
        logger.info(
            "skipping appeal Phoenix export for mode=%s", phoenix_mode.value
        )
        return None
    resolved = recorder or OtelPhoenixRecorder()
    redacted = build_redacted_appeal_package(
        appeal_package,
        denial_text=denial_text,
        clinical_context=clinical_context,
        use_scrubber=use_scrubber,
    )
    trace_metadata = {
        **dict(appeal_package.get("trace_metadata") or {}),
        "memory_eligible": "true",
        "phoenix_mode": "appeal",
        "redacted_export": "true",
        "run_mode": "interactive",
    }
    try:
        return resolved.record_run(redacted, trace_metadata)
    except Exception:
        logger.warning("appeal Phoenix export failed", exc_info=True)
        return None


def in_memory_recorder() -> InMemoryPhoenixRecorder:
    """Test helper."""
    return InMemoryPhoenixRecorder()
