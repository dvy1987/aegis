# ruff: noqa
# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import os
import asyncio
from google.adk.agents import Agent
from google.adk.apps import App
from google.adk.models import Gemini
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

async def fetch_traces(query: str = "") -> str:
    params = StdioServerParameters(command="npx", args=["-y", "@arizeai/phoenix-mcp"])
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            try:
                res = await session.call_tool("get_dataset", arguments={})
                return f"MCP connected. Available tools: {[t.name for t in (await session.list_tools()).tools]}"
            except Exception as e:
                return f"Error or trace result: {e}"

def query_traces_sync(query: str = "") -> str:
    return asyncio.run(fetch_traces(query))

root_agent = Agent(
    name="spike_agent",
    model=Gemini(model="gemini-3.1-pro-preview"),
    instruction="Use the query_traces_sync tool to fetch the tools list from Phoenix. Reply with what you find.",
    tools=[query_traces_sync]
)

app = App(root_agent=root_agent, name="spike_app")

