from __future__ import annotations

from app.aegis_v1.agent import AEGIS_V1_TOOL_NAMES, root_agent
from app.aegis_v1.schemas import AppealPackage

EXPECTED_TOOLS = {
    "case_parser", "corpus_retrieval", "phoenix_mcp_lookup",
    "playbook_loader", "drafter", "self_check",
}


def test_root_agent_is_aegis_v1_with_required_tools() -> None:
    assert root_agent.name == "aegis_v1"
    assert root_agent.output_schema is AppealPackage

    # The Outcome Simulator was relocated out of the Student pipeline (6 tools).
    assert AEGIS_V1_TOOL_NAMES == EXPECTED_TOOLS

    tool_names = {
        getattr(tool, "__name__", getattr(tool, "name", ""))
        for tool in root_agent.tools
    }

    assert tool_names == EXPECTED_TOOLS
    assert "simulator" not in tool_names


def test_root_agent_instruction_requires_ordered_tool_flow_and_disclaimer() -> None:
    instruction = str(root_agent.instruction)

    for tool_name in AEGIS_V1_TOOL_NAMES:
        assert tool_name in instruction

    assert "Not legal or medical advice. Draft assistance only." in instruction
    assert "JSON" in instruction
