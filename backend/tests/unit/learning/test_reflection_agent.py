from app.learning.models import Component, DimensionSignal
from app.learning.reflection_agent import AdkReflectionClient, build_reflection_agent
from app.learning.reflection_client import build_reflection_prompt


def test_reflection_agent_builds_adk_llm_agent() -> None:
    agent = build_reflection_agent()
    assert agent.name == "reflection_agent"


def test_adk_reflection_client_name() -> None:
    assert AdkReflectionClient().name == "adk_reflection"


def test_reflection_firewall_in_prompt() -> None:
    comp = Component(component_id="drafter_system_prompt", kind="prompt", version="v1", text="draft")
    sig = DimensionSignal(
        component_id="drafter_system_prompt",
        weakest_dimension="grounding",
        notes={"grounding": ["cite the denial flaw"]},
    )
    prompt = build_reflection_prompt(component=comp, signal=sig, minibatch=[])
    assert "citation-only rule" in prompt
    assert "never an answer key" in prompt.lower() or "answer key" in prompt.lower()
