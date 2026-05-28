from __future__ import annotations

from google.adk.agents import Agent
from google.adk.apps import App
from google.adk.models import Gemini

# Stub agent for the swarm (to be expanded in Part B)
root_agent = Agent(
    name="aegis_swarm_coordinator",
    model=Gemini(model="gemini-3.1-pro-preview"),
    instruction="You are the Learning Coordinator for Aegis Swarm.",
    tools=[],
)

app = App(root_agent=root_agent, name="aegis_swarm")
