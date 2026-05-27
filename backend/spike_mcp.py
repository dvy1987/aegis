import os
import asyncio
from dotenv import load_dotenv
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from google.adk.agents import Agent
from google.adk.models import Gemini

# Load environment variables
load_dotenv()

async def fetch_traces(query: str = "") -> str:
    """Fetches traces from Phoenix using MCP.
    
    Args:
        query: The filter query to use.
    Returns:
        A string representation of the trace.
    """
    params = StdioServerParameters(command="npx", args=["-y", "@arizeai/phoenix-mcp"])
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            try:
                res = await session.call_tool("get_dataset", arguments={})
                # get_dataset or search_traces may not be the exact tool name depending on version, 
                # but it proves the MCP connection if it connects.
                return f"MCP tools available: {[t.name for t in (await session.list_tools()).tools]}"
            except Exception as e:
                return f"Error or trace result: {e}"

def query_traces_sync(query: str = "") -> str:
    """Synchronous wrapper for fetch_traces.
    
    Args:
        query: The filter query to use.
    Returns:
        A string representation of the trace.
    """
    return asyncio.run(fetch_traces(query))

async def run_agent(agent):
    print("Running ADK Agent with Phoenix MCP connection...")
    async for event in agent.run_live("Fetch tools list from Phoenix"):
        print(f"Event: {event}")

from google.adk.apps import App
from google.adk import Runner
from google.genai import types

def main():
    agent = Agent(
        name="spike_agent",
        model=Gemini(model="gemini-2.5-flash"),
        instruction="Use the query_traces_sync tool to see what tools are available and output the tools list.",
        tools=[query_traces_sync]
    )

    app = App(root_agent=agent, name="spike_app")
    runner = Runner(app=app)
    
    print("Running ADK Agent with Phoenix MCP connection...")
    
    new_message = types.Content(role="user", parts=[types.Part.from_text(text="Fetch tools list from Phoenix")])
    for event in runner.run(user_id="test_user", session_id="test_session", new_message=new_message):
        print(event)

if __name__ == "__main__":
    main()
