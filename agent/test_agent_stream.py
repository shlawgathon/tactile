"""
Test script to stream events from the CAD Agent via CLI.
Connects to the SSE endpoint and prints formatted events.
"""

import asyncio
import json
import httpx
import sys

async def stream_agent_events():
    url = "http://localhost:8001/analyze-stream/test-cli-job?process=FDM_3D_PRINTING"
    print(f"Connecting to {url}...\n")
    
    try:
        async with httpx.AsyncClient(timeout=300.0) as client:
            async with client.stream("GET", url) as response:
                if response.status_code != 200:
                    print(f"Error: {response.status_code}")
                    return

                async for line in response.aiter_lines():
                    if line.startswith("data: "):
                        data = line[6:]
                        try:
                            event = json.loads(data)
                            event_type = event.get("type", "unknown")
                            content = event.get("content", "")
                            
                            # Pretty print based on type
                            if event_type == "thinking":
                                print(f"🧠 \033[36mTHINKING\033[0m: {content}")
                            elif event_type == "tool_call":
                                tool_name = event.get("data", {}).get("tool", "unknown")
                                print(f"🛠️  \033[33mTOOL CALL\033[0m: {tool_name}")
                            elif event_type == "tool_result":
                                print(f"✅ \033[32mTOOL RESULT\033[0m: {content}")
                            elif event_type == "suggestion":
                                print(f"💡 \033[35mSUGGESTION\033[0m: {content}")
                            elif event_type == "memory":
                                print(f"💾 \033[34mMEMORY\033[0m: {content}")
                            elif event_type == "error":
                                print(f"❌ \033[31mERROR\033[0m: {content}")
                            elif event_type == "complete":
                                print(f"\n✨ \033[1;32mCOMPLETE\033[0m: {content}")
                            else:
                                print(f"Event: {event_type} - {content}")
                                
                        except json.JSONDecodeError:
                            print(f"Raw: {data}")
                            
    except Exception as e:
        print(f"Connection failed: {e}")
        print("Make sure the server is running: uvicorn main:app --reload --port 8001")

if __name__ == "__main__":
    try:
        asyncio.run(stream_agent_events())
    except KeyboardInterrupt:
        print("\nStopped.")
