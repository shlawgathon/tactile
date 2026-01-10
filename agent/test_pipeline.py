#!/usr/bin/env python3
"""
CLI test script for the CAD analysis pipeline.

Tests the full flow:
1. Load a STEP file
2. Screenshot it
3. Run LLM analysis with tool calling
4. Execute CadQuery code
5. Store memories
6. Generate suggestions

Usage:
    python test_pipeline.py [--file path/to/file.step] [--process FDM_3D_PRINTING]
"""

import asyncio
import argparse
import os
import sys
from pathlib import Path

# Add parent to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv
load_dotenv()


async def test_screenshot(workplane, output_dir: str = "./test_output"):
    """Test the screenshot functionality."""
    from tools.screenshot_renderer import capture_screenshot, capture_multiple_views, read_svg_content
    
    print("\n" + "="*60)
    print("📸 TESTING SCREENSHOT RENDERER")
    print("="*60)
    
    os.makedirs(output_dir, exist_ok=True)
    
    # Capture ISO view
    result = await capture_screenshot(workplane, view="iso", output_dir=output_dir)
    
    if result.get("success"):
        print(f"✅ Screenshot captured: {result['path']}")
        print(f"   Format: {result['format']}")
        print(f"   Size: {result['file_size_kb']} KB")
        
        # Read content preview
        svg_content = read_svg_content(result['path'])
        print(f"   SVG length: {len(svg_content)} chars")
        return result['path'], svg_content
    else:
        print(f"❌ Screenshot failed: {result.get('error')}")
        return None, None


async def test_cadquery_execution(workplane):
    """Test CadQuery code execution."""
    from tools.cadquery_executor import execute_cadquery_code, run_analysis_snippet
    
    print("\n" + "="*60)
    print("⚙️  TESTING CADQUERY EXECUTOR")
    print("="*60)
    
    # Test 1: Bounding box
    print("\n1. Testing bounding_box snippet...")
    result = await run_analysis_snippet("bounding_box", workplane)
    if result.get("success"):
        bb = result.get("result", {})
        print(f"   ✅ Bounding box: {bb.get('width', 0):.2f} x {bb.get('depth', 0):.2f} x {bb.get('height', 0):.2f} mm")
    else:
        print(f"   ❌ Failed: {result.get('error')}")
    
    # Test 2: Face count
    print("\n2. Testing face_count snippet...")
    result = await run_analysis_snippet("face_count", workplane)
    if result.get("success"):
        print(f"   ✅ Face count: {result.get('result', {}).get('face_count', 'N/A')}")
    else:
        print(f"   ❌ Failed: {result.get('error')}")
    
    # Test 3: Custom code
    print("\n3. Testing custom code execution...")
    custom_code = """
# Analyze face normals to find overhangs
faces = workplane.faces().vals()
overhangs = []
for i, face in enumerate(faces):
    try:
        normal = face.normalAt()
        # Check if face normal points downward (z < -0.5)
        if normal.z < -0.5:
            overhangs.append({
                "face_id": i,
                "normal_z": normal.z,
                "is_overhang": True
            })
    except:
        pass
result = {"overhang_faces": len(overhangs), "details": overhangs[:5]}
"""
    result = await execute_cadquery_code(custom_code, workplane=workplane)
    if result.get("success"):
        print(f"   ✅ Custom analysis result: {result.get('result')}")
    else:
        print(f"   ❌ Failed: {result.get('error')}")
    
    return result


async def test_memory_client(job_id: str = "test-job-001"):
    """Test memory operations."""
    from tools.memory_client import get_memory_client
    
    print("\n" + "="*60)
    print("🧠 TESTING MEMORY CLIENT")
    print("="*60)
    
    try:
        client = await get_memory_client()
        
        # Store a memory
        print("\n1. Storing memory...")
        result = await client.store_memory(
            job_id=job_id,
            key="test_observation",
            value="Model has 24 faces with complex geometry",
            category="observation"
        )
        if result.get("success"):
            print(f"   ✅ Memory stored")
        else:
            print(f"   ❌ Failed: {result.get('error')}")
        
        # Read memories
        print("\n2. Reading memories...")
        result = await client.read_memory(job_id=job_id)
        if result.get("success"):
            print(f"   ✅ Found {result.get('count', 0)} memories")
            for mem in result.get("memories", [])[:3]:
                print(f"      - {mem.get('key')}: {mem.get('value')[:50]}...")
        else:
            print(f"   ❌ Failed: {result.get('error')}")
        
        # Store a suggestion
        print("\n3. Storing suggestion...")
        result = await client.give_suggestion(
            job_id=job_id,
            suggestion="Add 1mm fillet to sharp internal corners to improve moldability",
            issue_id="sharp_corners_001",
            priority=2
        )
        if result.get("success"):
            print(f"   ✅ Suggestion stored")
        else:
            print(f"   ❌ Failed: {result.get('error')}")
        
        return True
    except Exception as e:
        print(f"   ⚠️  Memory client error (MongoDB may not be running): {e}")
        return False


async def test_llm_client():
    """Test LLM client."""
    from fireworks_client import FireworksClient
    
    print("\n" + "="*60)
    print("🤖 TESTING LLM CLIENT (Fireworks)")
    print("="*60)
    
    api_key = os.getenv("FIREWORKS_API_KEY")
    if not api_key:
        print("   ⚠️  FIREWORKS_API_KEY not set - skipping LLM test")
        return False
    
    try:
        client = FireworksClient(api_key=api_key)
        
        print("\n   Testing basic completion...")
        response = await client.analyze_cad(
            cad_description="Simple test cube 10x10x10mm",
            manufacturing_process="FDM_3D_PRINTING",
            geometry_data={"test": True},
            mcp_tools=None  # No tools for basic test
        )
        
        await client.close()
        
        if response.get("choices"):
            content = response["choices"][0].get("message", {}).get("content", "")
            print(f"   ✅ LLM response received ({len(content)} chars)")
            print(f"   Preview: {content[:200]}...")
            return True
        else:
            print(f"   ❌ Unexpected response format: {response}")
            return False
            
    except Exception as e:
        print(f"   ❌ LLM error: {e}")
        return False


async def test_full_agent(workplane, job_id: str, process: str, step_file_path: str = None):
    """Test the full agent loop with subprocess-isolated CadQuery."""
    from cad_agent import create_agent, EventType
    
    print("\n" + "="*60)
    print("🔄 TESTING FULL AGENT LOOP")
    print("="*60)
    
    api_key = os.getenv("FIREWORKS_API_KEY")
    if not api_key:
        print("   ⚠️  FIREWORKS_API_KEY not set - skipping agent test")
        return
    
    try:
        agent = await create_agent(
            job_id=job_id,
            manufacturing_process=process,
            workplane=workplane,
            step_file_path=step_file_path,
        )
        
        print(f"\n   Job ID: {job_id}")
        print(f"   Process: {process}")
        print(f"   Max iterations: {agent.max_iterations}")
        print("\n   Streaming events:")
        print("-" * 50)
        
        event_count = 0
        async for event in agent.analyze_stream():
            event_count += 1
            
            # Format output based on event type
            if event.type == EventType.THINKING:
                print(f"\n💭 THINKING:")
                print(f"   {event.content[:500]}{'...' if len(event.content) > 500 else ''}")
            
            elif event.type == EventType.TOOL_CALL:
                tool = event.data.get("tool", "unknown") if event.data else "unknown"
                print(f"\n🔧 TOOL CALL: {tool}")
                if event.data and event.data.get("input"):
                    inp = event.data["input"]
                    if "code" in inp:
                        print(f"   Code: {inp['code'][:100]}...")
                    elif "suggestion" in inp:
                        print(f"   Suggestion: {inp['suggestion'][:100]}...")
                    else:
                        print(f"   Input: {str(inp)[:100]}...")
            
            elif event.type == EventType.TOOL_RESULT:
                tool = event.data.get("tool", "unknown") if event.data else "unknown"
                success = event.data.get("result", {}).get("success", False) if event.data else False
                print(f"\n✅ TOOL RESULT: {tool} - {'Success' if success else 'Failed'}")
                if event.data and event.data.get("result"):
                    result = event.data["result"]
                    if "result" in result:
                        print(f"   Result: {str(result['result'])[:200]}...")
            
            elif event.type == EventType.SUGGESTION:
                print(f"\n💡 SUGGESTION:")
                print(f"   {event.content}")
            
            elif event.type == EventType.MEMORY:
                print(f"\n📝 MEMORY STORED: {event.content}")
            
            elif event.type == EventType.SCREENSHOT:
                print(f"\n📸 SCREENSHOT: {event.content}")
            
            elif event.type == EventType.ERROR:
                print(f"\n❌ ERROR: {event.content}")
            
            elif event.type == EventType.COMPLETE:
                print(f"\n🎉 COMPLETE: {event.content}")
        
        print("-" * 50)
        print(f"\n   Total events: {event_count}")
        
        await agent.close()
        
    except Exception as e:
        print(f"   ❌ Agent error: {e}")
        import traceback
        traceback.print_exc()


async def main():
    parser = argparse.ArgumentParser(description="Test CAD analysis pipeline")
    parser.add_argument("--file", "-f", type=str, help="Path to STEP file (default: battery.step)")
    parser.add_argument("--process", "-p", type=str, default="FDM_3D_PRINTING",
                       choices=["FDM_3D_PRINTING", "INJECTION_MOLDING", "CNC_MACHINING"],
                       help="Manufacturing process")
    parser.add_argument("--job-id", "-j", type=str, default="cli-test-001",
                       help="Job ID for testing")
    parser.add_argument("--skip-llm", action="store_true", help="Skip LLM tests")
    parser.add_argument("--skip-memory", action="store_true", help="Skip memory tests")
    parser.add_argument("--agent-only", action="store_true", help="Only run full agent test")
    
    args = parser.parse_args()
    
    print("="*60)
    print("🚀 TACTILE CAD ANALYSIS PIPELINE TEST")
    print("="*60)
    
    # Load STEP file
    step_path = args.file
    if not step_path:
        step_path = os.path.join(os.path.dirname(__file__), "battery.step")
    
    print(f"\nLoading STEP file: {step_path}")
    
    workplane = None
    try:
        import cadquery as cq
        if os.path.exists(step_path):
            workplane = cq.importers.importStep(step_path)
            print(f"✅ STEP file loaded successfully")
            
            # Quick geometry check
            solid = workplane.val()
            bb = solid.BoundingBox()
            print(f"   Bounding box: {bb.xmax - bb.xmin:.2f} x {bb.ymax - bb.ymin:.2f} x {bb.zmax - bb.zmin:.2f} mm")
            print(f"   Faces: {len(workplane.faces().vals())}")
            print(f"   Edges: {len(workplane.edges().vals())}")
        else:
            print(f"⚠️  STEP file not found: {step_path}")
            print("   Creating test box instead...")
            workplane = cq.Workplane("XY").box(50, 30, 20)
    except ImportError:
        print("❌ CadQuery not installed")
        return
    except Exception as e:
        print(f"❌ Failed to load STEP: {e}")
        return
    
    if args.agent_only:
        # CadQuery now runs in isolated subprocess, so we can use the real model
        print("\n📦 Using loaded model (CadQuery runs in isolated subprocess)")
        await test_full_agent(workplane, args.job_id, args.process, step_path)
    else:
        # Run individual component tests
        
        # Test screenshot
        await test_screenshot(workplane)
        
        # Test CadQuery execution
        await test_cadquery_execution(workplane)
        
        # Test memory client (requires MongoDB)
        if not args.skip_memory:
            await test_memory_client(args.job_id)
        
        # Test LLM client
        if not args.skip_llm:
            await test_llm_client()
        
        # Test full agent
        if not args.skip_llm:
            await test_full_agent(workplane, args.job_id, args.process)
    
    print("\n" + "="*60)
    print("✨ PIPELINE TEST COMPLETE")
    print("="*60)


if __name__ == "__main__":
    asyncio.run(main())

