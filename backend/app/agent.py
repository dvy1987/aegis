from __future__ import annotations

import os

from google.adk.agents import Agent
from google.adk.apps import App
from google.adk.models import Gemini
from google.adk.tools.mcp_tool import McpToolset
from google.adk.tools.mcp_tool.mcp_session_manager import StdioConnectionParams
from mcp import StdioServerParameters


def _phoenix_mcp_env() -> dict[str, str]:
    env = os.environ.copy()
    env["PHOENIX_PROJECT"] = env.get("PHOENIX_PROJECT_NAME", "aegis-hackathon")
    api_key = env.get("PHOENIX_API_KEY", "")
    if api_key:
        env["PHOENIX_CLIENT_HEADERS"] = f"api_key={api_key}"
    return env


root_agent = Agent(
    name="aegis_v1",
    model=Gemini(model="gemini-3.1-pro-preview"),
    instruction=(
        "You are Aegis, an assistant that helps people draft health-insurance "
        "appeal letters. When given a denial scenario, produce a structured "
        "appeal draft. Always include the disclaimer: 'Not legal or medical "
        "advice. Draft assistance only.'\n\n"
        "Before drafting, use the Phoenix MCP tools to look up past traces "
        "from the aegis-hackathon project. Summarize relevant patterns from "
        "prior runs (latency, tool usage, failure modes) to ground your draft."
    ),
    tools=[
        McpToolset(
            connection_params=StdioConnectionParams(
                server_params=StdioServerParameters(
                    command="npx",
                    args=["-y", "@arizeai/phoenix-mcp"],
                    env=_phoenix_mcp_env(),
                ),
                timeout=30.0,
            ),
            tool_filter=["list-traces", "get-trace", "get-spans"],
        ),
    ],
)

app = App(root_agent=root_agent, name="aegis")
