"""
Sandboxed CadQuery code executor for CAD Agent.
Executes LLM-generated CadQuery code in an ISOLATED subprocess for safety.
This prevents CadQuery crashes from taking down the main agent process.
"""

import os
import sys
import json
import tempfile
import traceback
from typing import Any, Dict, Optional
import asyncio
import multiprocessing as mp
from multiprocessing import Process, Queue


def _worker_execute(
    code: str,
    step_file_path: Optional[str],
    result_queue: Queue,
    error_queue: Queue,
):
    """
    Worker function that runs in a separate process.
    Loads the STEP file and executes the code.
    """
    try:
        import cadquery as cq
        
        # Load workplane from STEP file if provided
        workplane = None
        if step_file_path and os.path.exists(step_file_path):
            workplane = cq.importers.importStep(step_file_path)
        
        # Build execution context
        exec_globals = {
            "cq": cq,
            "__builtins__": __builtins__,
        }
        
        if workplane is not None:
            exec_globals["workplane"] = workplane
            exec_globals["wp"] = workplane
        
        exec_locals: Dict[str, Any] = {}
        
        # Execute the code
        exec(code, exec_globals, exec_locals)
        
        # Extract result
        result = exec_locals.get("result", None)
        
        # If no explicit result, look for common variable names
        if result is None:
            for key in ["output", "value", "data", "analysis", "measurements"]:
                if key in exec_locals:
                    result = exec_locals[key]
                    break
        
        # Make result JSON serializable
        result = _make_serializable(result)
        
        result_queue.put({
            "success": True,
            "result": result,
            "variables": list(exec_locals.keys())
        })
        
    except Exception as e:
        error_queue.put({
            "success": False,
            "error": f"{type(e).__name__}: {str(e)}",
            "traceback": traceback.format_exc(),
        })


def _make_serializable(obj: Any) -> Any:
    """Make an object JSON serializable."""
    if obj is None:
        return None
    if isinstance(obj, (str, int, float, bool)):
        return obj
    if isinstance(obj, (list, tuple)):
        return [_make_serializable(item) for item in obj]
    if isinstance(obj, dict):
        return {str(k): _make_serializable(v) for k, v in obj.items()}
    # Try to convert to dict
    if hasattr(obj, "__dict__"):
        return _make_serializable(obj.__dict__)
    # Last resort: string representation
    return str(obj)


async def execute_cadquery_code(
    code: str,
    workplane: Optional[Any] = None,
    step_file_path: Optional[str] = None,
    context: Optional[Dict[str, Any]] = None,
    timeout_seconds: float = 30.0
) -> Dict[str, Any]:
    """
    Execute CadQuery code in an ISOLATED subprocess.
    
    This prevents CadQuery crashes (segfaults) from affecting the main process.
    
    Args:
        code: Python/CadQuery code to execute
        workplane: CadQuery workplane (will be saved to temp file)
        step_file_path: Path to STEP file (alternative to workplane)
        context: Optional additional context (not currently used in subprocess)
        timeout_seconds: Maximum execution time in seconds
        
    Returns:
        Execution result
    """
    # If we have a workplane but no file path, export to temp file
    temp_step = None
    if workplane is not None and step_file_path is None:
        try:
            from cadquery import exporters
            temp_step = tempfile.NamedTemporaryFile(suffix=".step", delete=False)
            temp_step.close()
            exporters.export(workplane, temp_step.name)
            step_file_path = temp_step.name
        except Exception as e:
            return {
                "success": False,
                "error": f"Failed to export workplane: {e}",
                "result": None
            }
    
    # Create queues for communication
    result_queue = Queue()
    error_queue = Queue()
    
    # Start worker process
    process = Process(
        target=_worker_execute,
        args=(code, step_file_path, result_queue, error_queue)
    )
    
    try:
        process.start()
        
        # Wait for process with timeout
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(
            None,
            lambda: process.join(timeout=timeout_seconds)
        )
        
        # Check if process is still running (timeout)
        if process.is_alive():
            process.terminate()
            process.join(timeout=5)
            if process.is_alive():
                process.kill()
            return {
                "success": False,
                "error": f"Execution timed out after {timeout_seconds} seconds",
                "result": None
            }
        
        # Check exit code
        if process.exitcode != 0:
            # Process crashed (segfault, etc.)
            if not error_queue.empty():
                error_data = error_queue.get_nowait()
                return {
                    "success": False,
                    "error": error_data.get("error", f"Process crashed with code {process.exitcode}"),
                    "traceback": error_data.get("traceback", ""),
                    "result": None
                }
            return {
                "success": False,
                "error": f"CadQuery process crashed (exit code: {process.exitcode})",
                "result": None
            }
        
        # Get result
        if not result_queue.empty():
            return result_queue.get_nowait()
        elif not error_queue.empty():
            error_data = error_queue.get_nowait()
            return {
                "success": False,
                "error": error_data.get("error", "Unknown error"),
                "traceback": error_data.get("traceback", ""),
                "result": None
            }
        else:
            return {
                "success": False,
                "error": "No result returned from subprocess",
                "result": None
            }
            
    except Exception as e:
        return {
            "success": False,
            "error": f"Subprocess error: {type(e).__name__}: {str(e)}",
            "result": None
        }
    finally:
        # Clean up temp file
        if temp_step and os.path.exists(temp_step.name):
            try:
                os.unlink(temp_step.name)
            except:
                pass
        
        # Ensure process is dead
        if process.is_alive():
            process.terminate()


# Common analysis code snippets that can be requested
ANALYSIS_SNIPPETS = {
    "bounding_box": """
# Get bounding box of the model
bb = workplane.val().BoundingBox()
result = {
    "xmin": bb.xmin, "xmax": bb.xmax,
    "ymin": bb.ymin, "ymax": bb.ymax,
    "zmin": bb.zmin, "zmax": bb.zmax,
    "width": bb.xmax - bb.xmin,
    "depth": bb.ymax - bb.ymin,
    "height": bb.zmax - bb.zmin,
}
""",
    
    "face_count": """
# Count faces
faces = workplane.faces().vals()
result = {"face_count": len(faces)}
""",
    
    "volume": """
# Calculate volume
solid = workplane.val()
result = {"volume_mm3": solid.Volume()}
""",
    
    "surface_area": """
# Calculate surface area
solid = workplane.val()
result = {"surface_area_mm2": solid.Area()}
""",
    
    "face_normals": """
# Get face normals
faces = workplane.faces().vals()
result = []
for i, face in enumerate(faces[:50]):  # Limit to 50 faces
    try:
        center = face.Center()
        normal = face.normalAt()
        result.append({
            "face_id": i,
            "center": {"x": center.x, "y": center.y, "z": center.z},
            "normal": {"x": normal.x, "y": normal.y, "z": normal.z}
        })
    except:
        pass
""",
}


async def run_analysis_snippet(
    snippet_name: str,
    workplane: Any = None,
    step_file_path: str = None,
    timeout_seconds: float = 30.0
) -> Dict[str, Any]:
    """
    Run a predefined analysis snippet in a subprocess.
    
    Args:
        snippet_name: Name of the snippet to run
        workplane: CadQuery workplane to analyze
        step_file_path: Path to STEP file (alternative)
        timeout_seconds: Maximum execution time
        
    Returns:
        Analysis result
    """
    if snippet_name not in ANALYSIS_SNIPPETS:
        return {
            "success": False,
            "error": f"Unknown snippet: {snippet_name}. Available: {list(ANALYSIS_SNIPPETS.keys())}"
        }
    
    code = ANALYSIS_SNIPPETS[snippet_name]
    return await execute_cadquery_code(
        code, 
        workplane=workplane, 
        step_file_path=step_file_path,
        timeout_seconds=timeout_seconds
    )
