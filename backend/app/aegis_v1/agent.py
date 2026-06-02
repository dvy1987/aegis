from __future__ import annotations

from google.adk.agents import Agent
from google.adk.apps import App
from google.adk.models import Gemini
from google.genai import types

from app.aegis_v1.schemas import AppealPackage
from app.aegis_v1.tools import (
    DISCLAIMER,
    case_parser,
    corpus_retrieval,
    drafter,
    phoenix_mcp_lookup,
    playbook_loader,
    self_check,
)


AEGIS_V1_TOOL_NAMES = {
    "case_parser",
    "corpus_retrieval",
    "phoenix_mcp_lookup",
    "playbook_loader",
    "drafter",
    "self_check",
}


AEGIS_V1_INSTRUCTION = f"""
You are Aegis v1, the baseline single-agent workflow for drafting US commercial
health-insurance appeal letters from synthetic cases.

This is the deliberately weak v1 baseline: be competent, structured, and safe,
but do not invent advanced strategy beyond the local corpus, cold-start
playbook, and Phoenix-memory summary returned by tools.

You must use the six tools in this order:
1. case_parser
2. corpus_retrieval
3. phoenix_mcp_lookup
4. playbook_loader
5. drafter
6. self_check

Then return exactly one JSON object matching the AppealPackage schema. Use
`run_id` as a short stable identifier for this run. In `trace_metadata`, include
case_id, insurer, denial_type, plan_type, state, prompt_version
`aegis_v1_weak`, playbook_version, dataset_split, and run_mode.

Hard safety rules:
- Include this exact disclaimer in the appeal letter: "{DISCLAIMER}"
- Do not provide legal or medical advice.
- Do not claim the appeal will win.
- Do not invent statutes, case law, insurer policy text, addresses, or medical
  guideline language. Use only citations returned by corpus_retrieval.
- If Phoenix memory or a playbook is unavailable, keep going but put the
  relevant risk flag in the final JSON.
"""


root_agent = Agent(
    name="aegis_v1",
    model=Gemini(model="gemini-3.1-pro-preview"),
    instruction=AEGIS_V1_INSTRUCTION,
    tools=[
        case_parser,
        corpus_retrieval,
        phoenix_mcp_lookup,
        playbook_loader,
        drafter,
        self_check,
    ],
    output_schema=AppealPackage,
    generate_content_config=types.GenerateContentConfig(
        response_mime_type="application/json",
        temperature=0.2,
    ),
)

app = App(root_agent=root_agent, name="aegis")
