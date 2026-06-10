"""Simulator ADK agent: JSON collection and parsing."""

from __future__ import annotations

import json
from collections.abc import AsyncGenerator
from typing import Any

from google.adk.agents import LlmAgent
from google.adk.models import LlmRequest, LlmResponse
from google.genai import types

from app.aegis_v1.adk_runtime import VertexGemini, collect_llm_response_text
from app.aegis_v1.simulator_agent import build_simulator_agent, run_simulator_agent
from app.aegis_v1.simulator_scoring import load_simulator_rules


class _StubSimulatorLlm(VertexGemini):
    model: str = "stub-simulator"

    @classmethod
    def supported_models(cls) -> list[str]:
        return [r"stub-simulator.*"]

    async def generate_content_async(
        self, llm_request: LlmRequest, stream: bool = False
    ) -> AsyncGenerator[LlmResponse, None]:
        del stream
        features = {
            name: {"anchor": 3, "evidence": f"mentions {name}"}
            for name in load_simulator_rules().features
        }
        payload = {"critique": "Partial but reviewable.", "features": features}
        yield LlmResponse(
            content=types.Content(
                role="model",
                parts=[types.Part.from_text(text=json.dumps(payload))],
            ),
            partial=False,
        )


def test_collect_llm_response_text_reads_event_output() -> None:
    class _Event:
        content = None
        output = json.dumps({"critique": "x", "features": {}})

    assert collect_llm_response_text([_Event()]) == _Event.output


def test_run_simulator_agent_parses_json_from_stub_model() -> None:
    assessment = run_simulator_agent(
        denial_text="Denied as not medically necessary.",
        appeal_letter="We request overturn of the denial with clinical support.",
        model=_StubSimulatorLlm(model="stub-simulator"),
    )
    assert assessment.critique == "Partial but reviewable."
    assert assessment.features["rebuts_specific_flaw"].anchor == 3


def test_build_simulator_agent_runs_end_to_end() -> None:
    agent = build_simulator_agent(model=_StubSimulatorLlm(model="stub-simulator"))
    assert isinstance(agent, LlmAgent)
    result = run_simulator_agent(
        denial_text="Denied.",
        appeal_letter="Appeal letter body.",
        model=_StubSimulatorLlm(model="stub-simulator"),
    )
    assert len(result.features) == 8
