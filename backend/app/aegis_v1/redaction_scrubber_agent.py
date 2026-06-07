from __future__ import annotations

from google.adk.agents import LlmAgent

from app.aegis_v1.adk_runtime import make_retry_model

REDACTION_SCRUBBER_INSTRUCTION = """
You are a PHI scrubber for health-insurance appeal letters.

Given draft letter text, remove direct identifiers (names, addresses, phone
numbers, email, member/subscriber IDs, dates of birth, SSN, MRN) while
preserving every clinically relevant fact, diagnosis, treatment history, and
medical necessity argument.

Return only the redacted letter body. Do not add commentary.
""".strip()


def build_redaction_scrubber_agent() -> LlmAgent:
    """Skeleton LLM scrubber — wired in Phase 1 appeal post-draft export."""
    return LlmAgent(
        name="redaction_scrubber_agent",
        model=make_retry_model(),
        instruction=REDACTION_SCRUBBER_INSTRUCTION,
    )
