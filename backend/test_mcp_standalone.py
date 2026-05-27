import os
import asyncio
from dotenv import load_dotenv
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

load_dotenv("../.env")

async def test_phoenix_mcp():
    env = os.environ.copy()
    env["PHOENIX_PROJECT"] = env.get("PHOENIX_PROJECT_NAME", "default")
    params = StdioServerParameters(command="npx", args=["-y", "@arizeai/phoenix-mcp"], env=env)
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            print("Connected! Listing tools:")
            tools = await session.list_tools()
            for t in tools.tools:
                print(f" - {t.name}: {t.description[:100]}...")
            
            print("\nQuerying a trace...")
            try:
                res = await session.call_tool("list-traces", arguments={"projectIdentifier": "aegis-hackathon", "limit": 1})
                print(f"Result: {res.content}")
            except Exception as e:
                print(f"Query error: {e}")

if __name__ == "__main__":
    asyncio.run(test_phoenix_mcp())
