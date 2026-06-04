import os
import asyncio
from dotenv import load_dotenv
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

load_dotenv("../.env")

async def test_phoenix_mcp():
    env = os.environ.copy()
    project = env.get("PHOENIX_PROJECT_NAME", "default")
    env["PHOENIX_PROJECT"] = project
    if "PHOENIX_API_KEY" in env and "PHOENIX_CLIENT_HEADERS" not in env:
        env["PHOENIX_CLIENT_HEADERS"] = f"api_key={env['PHOENIX_API_KEY']}"
    params = StdioServerParameters(command="npx", args=["-y", "@arizeai/phoenix-mcp"], env=env)
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            print(f"Connected (project={project}). Listing tools:")
            tools = await session.list_tools()
            for t in tools.tools:
                print(f" - {t.name}: {t.description[:100]}...")

            for tool_name, args in [
                ("list-projects", {}),
                ("get-spans", {"projectIdentifier": project, "limit": 1}),
                ("list-traces", {"projectIdentifier": project, "limit": 1}),
            ]:
                print(f"\nCalling {tool_name} {args}...")
                try:
                    res = await session.call_tool(tool_name, arguments=args)
                    text = str(res.content)
                    print(f"  -> {text[:400]}")
                except Exception as e:
                    print(f"  ERROR: {e}")

if __name__ == "__main__":
    asyncio.run(test_phoenix_mcp())
