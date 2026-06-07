from __future__ import annotations

from google.adk.apps import App

from app.aegis_v1.student_workflow import v1_student_workflow

# Tool registry metadata kept here so existing tool-contract tests stay stable.
AEGIS_V1_TOOL_NAMES = {
    "case_parser",
    "corpus_retrieval",
    "phoenix_mcp_lookup",
    "playbook_loader",
    "drafter",
    "self_check",
}

# Phase 1: v1_student_workflow (google.adk.Workflow) replaces the Phase 0
# placeholder LlmAgent.  Workflow is a BaseNode — valid App root.
root_agent = v1_student_workflow

app = App(root_agent=root_agent, name="aegis_v1")
