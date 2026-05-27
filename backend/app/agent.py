from __future__ import annotations

from google.adk.agents import Agent
from google.adk.apps import App
from google.adk.models import Gemini

root_agent = Agent(
    name="aegis_v1",
    model=Gemini(model="gemini-3.1-pro-preview"),
    instruction=(
        "You are Aegis, an assistant that helps people draft health-insurance "
        "appeal letters. When given a denial scenario, produce a structured "
        "appeal draft. Always include the disclaimer: 'Not legal or medical "
        "advice. Draft assistance only.'"
    ),
)

app = App(root_agent=root_agent, name="aegis")
