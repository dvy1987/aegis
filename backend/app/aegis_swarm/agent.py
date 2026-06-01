"""ADK entrypoint for the Part B swarm (Phase 4).

The root agent exposes ONE tool that delegates to the pure ``swarm_pipeline``
core — no duplicated orchestration logic. Live vs offline wiring comes from
``swarm_config.build_live_stack()``.
"""

from __future__ import annotations

from typing import Any

from google.adk.agents import Agent
from google.adk.apps import App
from google.adk.models import Gemini
_DISCLAIMER_NOTE = (
    "Not legal or medical advice. Draft assistance only."
)


def run_swarm_appeal(
    denial_text: str,
    clinical_context: str = "",
    case_id: str = "interactive_case",
) -> dict[str, Any]:
    """Run the full swarm Student pipeline and return the terminal package.

    Wired through ``swarm_config`` so live mode uses Gemini + Vertex corpus when
    env vars are set; default is offline stub + local BM25.
    """
    from app.aegis_swarm.swarm_config import build_live_stack
    from app.aegis_swarm.trace_recorder import build_trace_recorder
    from app.aegis_swarm.swarm_pipeline import run_swarm_pipeline

    stack = build_live_stack()
    result = run_swarm_pipeline(
        denial_text=denial_text,
        clinical_context=clinical_context,
        case_id=case_id,
        client=stack["client"],
        corpus_store=stack["corpus_store"],
        discovery=stack["discovery"],
        trace_recorder=build_trace_recorder(),
    )
    return result


AEGIS_SWARM_INSTRUCTION = f"""
You are the Aegis Swarm coordinator for US commercial health-insurance appeals.

You orchestrate a multi-agent pipeline (Triage, researchers, Strategist, Drafter,
Adversarial Reviewer) by calling the ``run_swarm_appeal`` tool. Do NOT invent
statutes, case law, insurer policy text, or medical guidelines.

Hard safety rules:
- Include the mandatory disclaimer in outputs: "{_DISCLAIMER_NOTE}"
- Do not claim the appeal will win.
- Do not reproduce PHI.
- Use "person" not "human".

When the user provides a denial, call ``run_swarm_appeal`` and return the JSON
result from the tool unchanged.
"""


root_agent = Agent(
    name="aegis_swarm_coordinator",
    model=Gemini(model="gemini-3.1-pro"),
    instruction=AEGIS_SWARM_INSTRUCTION,
    tools=[run_swarm_appeal],
)

app = App(root_agent=root_agent, name="aegis_swarm")
