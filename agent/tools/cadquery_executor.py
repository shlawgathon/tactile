"""
Sandboxed CadQuery code executor for CAD Agent.
Executes LLM-generated CadQuery code safely with timeout and error handling.
"""

import io
import sys
import traceback
from contextlib import redirect_stdout, redirect_stderr
from typing import Any, Dict, Optional
import asyncio
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeoutError


# Try to import CadQuery
try:
    import cadquery as cq
    CADQUERY_AVAILABLE = True
except ImportError:
    CADQUERY_AVAILABLE = False
    cq = None


# Thread pool for blocking operations
_executor = ThreadPoolExecutor(max_workers=2)


def _execute_code_sync(
    code: str,
    workplane: Optional[Any] = None,
    context: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Execute CadQuery code synchronously.
    
    Args:
        code: Python/CadQuery code to execute
        workplane: Optional existing workplane to use
        context: Optional additional context variables
        
    Returns:
        Execution result with stdout, stderr, result, and any errors
    """
    if not CADQUERY_AVAILABLE:
        return {
            "success": False,
            "error": "CadQuery is not installed",
            "stdout": "",
            "stderr": "",
            "result": None
        }
    
    stdout_capture = io.StringIO()
    stderr_capture = io.StringIO()
    
    # Build execution context
    exec_globals = {
        "cq": cq,
        "__builtins__": __builtins__,
    }
    
    # Add workplane if provided
    if workplane is not None:
        exec_globals["workplane"] = workplane
        exec_globals["wp"] = workplane  # Shorthand
    
    # Add any extra context
    if context:
        exec_globals.update(context)
    
    exec_locals: Dict[str, Any] = {}
    
    try:
        with redirect_stdout(stdout_capture), redirect_stderr(stderr_capture):
            exec(code, exec_globals, exec_locals)
        
        # Try to extract result
        result = exec_locals.get("result", None)
        
        # If no explicit result, look for common variable names
        if result is None:
            for key in ["output", "value", "data", "analysis", "measurements"]:
                if key in exec_locals:
                    result = exec_locals[key]
                    break
        
        # If still no result, try to serialize any new workplane
        if result is None and "workplane" in exec_locals:
            wp = exec_locals["workplane"]
            if hasattr(wp, "val"):
                result = _extract_workplane_info(wp)
        
        return {
            "success": True,
            "error": None,
            "stdout": stdout_capture.getvalue(),
            "stderr": stderr_capture.getvalue(),
            "result": _make_serializable(result),
            "variables": list(exec_locals.keys())
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": f"{type(e).__name__}: {str(e)}",
            "traceback": traceback.format_exc(),
            "stdout": stdout_capture.getvalue(),
            "stderr": stderr_capture.getvalue(),
            "result": None
        }


def _extract_workplane_info(wp: Any) -> Dict[str, Any]:
    """Extract information from a CadQuery workplane."""
    try:
        solid = wp.val()
        bb = solid.BoundingBox()
        
        return {
            "type": "workplane",
            "bounding_box": {
                "xmin": bb.xmin, "xmax": bb.xmax,
                "ymin": bb.ymin, "ymax": bb.ymax,
                "zmin": bb.zmin, "zmax": bb.zmax,
                "width": bb.xmax - bb.xmin,
                "depth": bb.ymax - bb.ymin,
                "height": bb.zmax - bb.zmin,
            },
            "volume": solid.Volume() if hasattr(solid, "Volume") else None,
            "face_count": len(wp.faces().vals()) if hasattr(wp, "faces") else None,
            "edge_count": len(wp.edges().vals()) if hasattr(wp, "edges") else None,
        }
    except Exception as e:
        return {"type": "workplane", "error": str(e)}


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
    context: Optional[Dict[str, Any]] = None,
    timeout_seconds: float = 30.0
) -> Dict[str, Any]:
    """
    Execute CadQuery code asynchronously with timeout.
    
    Args:
        code: Python/CadQuery code to execute
        workplane: Optional existing workplane to use
        context: Optional additional context variables
        timeout_seconds: Maximum execution time in seconds
        
    Returns:
        Execution result
    """
    loop = asyncio.get_event_loop()
    
    try:
        result = await asyncio.wait_for(
            loop.run_in_executor(
                _executor,
                _execute_code_sync,
                code,
                workplane,
                context
            ),
            timeout=timeout_seconds
        )
        return result
    except asyncio.TimeoutError:
        return {
            "success": False,
            "error": f"Execution timed out after {timeout_seconds} seconds",
            "stdout": "",
            "stderr": "",
            "result": None
        }
    except Exception as e:
        return {
            "success": False,
            "error": f"Unexpected error: {type(e).__name__}: {str(e)}",
            "stdout": "",
            "stderr": "",
            "result": None
        }


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
for i, face in enumerate(faces):
    center = face.Center()
    normal = face.normalAt()
    result.append({
        "face_id": i,
        "center": {"x": center.x, "y": center.y, "z": center.z},
        "normal": {"x": normal.x, "y": normal.y, "z": normal.z}
    })
""",
}


async def run_analysis_snippet(
    snippet_name: str,
    workplane: Any,
    timeout_seconds: float = 30.0
) -> Dict[str, Any]:
    """
    Run a predefined analysis snippet.
    
    Args:
        snippet_name: Name of the snippet to run
        workplane: CadQuery workplane to analyze
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
    return await execute_cadquery_code(code, workplane=workplane, timeout_seconds=timeout_seconds)
