import os
import time
import asyncio
from dotenv import load_dotenv
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

load_dotenv("../.env")

async def test_latency():
    env = os.environ.copy()
    env["PHOENIX_PROJECT"] = env.get("PHOENIX_PROJECT_NAME", "default")
    params = StdioServerParameters(command="npx", args=["-y", "@arizeai/phoenix-mcp"], env=env)
    
    latencies = []
    successes = 0
    failures = 0
    
    print("Starting MCP latency test (20 queries)...")
    
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            
            for i in range(20):
                start_time = time.time()
                try:
                    res = await session.call_tool("list-traces", arguments={"projectIdentifier": "aegis-swarm", "limit": 1})
                    latency = time.time() - start_time
                    latencies.append(latency)
                    successes += 1
                    print(f"Query {i+1}/20: SUCCESS in {latency:.2f}s")
                except Exception as e:
                    latency = time.time() - start_time
                    failures += 1
                    print(f"Query {i+1}/20: FAIL in {latency:.2f}s - {e}")
                await asyncio.sleep(0.5)

    if latencies:
        latencies.sort()
        p50 = latencies[len(latencies)//2]
        p95 = latencies[int(len(latencies)*0.95)]
        print(f"\n--- Results ---")
        print(f"Successes: {successes}/20")
        print(f"Failures: {failures}/20")
        print(f"p50 Latency: {p50:.2f}s")
        print(f"p95 Latency: {p95:.2f}s")
        
        if p95 < 10.0 and failures == 0:
            print("GO DECISION: MCP is reliable and fast enough.")
        else:
            print("NO-GO DECISION: MCP is too slow or unreliable.")

if __name__ == "__main__":
    asyncio.run(test_latency())
