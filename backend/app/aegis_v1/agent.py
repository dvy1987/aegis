from __future__ import annotations

from google.adk.agents import LlmAgent
from google.adk.apps import App

from app.aegis_v1.adk_runtime import make_retry_model

# Tool registry metadata kept here so existing tool-contract tests stay stable.
AEGIS_V1_TOOL_NAMES = {
    "case_parser",
    "corpus_retrieval",
    "phoenix_mcp_lookup",
    "playbook_loader",
    "drafter",
    "self_check",
}

PHASE0_PLACEHOLDER_INSTRUCTION = """
Phase 0 ADK placeholder. The student workflow graph and v1-drafter-agent land in
Phase 1. Production /appeal and /showcase paths still use Gemini*Client until then.

Not legal or medical advice. Draft assistance only.
""".strip()

root_agent = LlmAgent(
    name="aegis_v1",
    model=make_retry_model(),
    instruction=PHASE0_PLACEHOLDER_INSTRUCTION,
)

app = App(root_agent=root_agent, name="aegis_v1")
