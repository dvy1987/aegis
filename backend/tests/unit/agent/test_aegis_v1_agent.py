from __future__ import annotations

from app.aegis_v1.agent import AEGIS_V1_TOOL_NAMES, root_agent
from app.aegis_v1.schemas import AppealPackage


def test_root_agent_is_aegis_v1_with_required_tools() -> None:
    assert root_agent.name == "aegis_v1"
    assert root_agent.output_schema is AppealPackage

    tool_names = {
        getattr(tool, "__name__", getattr(tool, "name", ""))
        for tool in root_agent.tools
    }

    assert tool_names == AEGIS_V1_TOOL_NAMES


def test_root_agent_instruction_requires_ordered_tool_flow_and_disclaimer() -> None:
    instruction = str(root_agent.instruction)

    for tool_name in AEGIS_V1_TOOL_NAMES:
        assert tool_name in instruction

    assert "Not legal or medical advice. Draft assistance only." in instruction
    assert "JSON" in instruction
