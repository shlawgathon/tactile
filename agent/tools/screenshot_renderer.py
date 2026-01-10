"""
CAD Screenshot Renderer - SVG export for LLM consumption.
Uses CadQuery's native SVG export in an ISOLATED subprocess for safety.
"""

import os
import tempfile
import asyncio
from typing import Any, Dict, Optional
from multiprocessing import Process, Queue


# View direction vectors
VIEW_ANGLES = {
    "iso": (1, 1, 1),
    "iso_back": (-1, -1, 1),
    "top": (0, 0, 1),
    "bottom": (0, 0, -1),
    "front": (0, -1, 0),
    "back": (0, 1, 0),
    "left": (-1, 0, 0),
    "right": (1, 0, 0),
    "front_right": (1, -1, 0),
    "front_left": (-1, -1, 0),
    "back_right": (1, 1, 0),
    "back_left": (-1, 1, 0),
}

AVAILABLE_VIEWS = list(VIEW_ANGLES.keys())


def _worker_render(
    step_file_path: str,
    output_path: str,
    view: str,
    width: int,
    height: int,
    show_hidden: bool,
    result_queue: Queue,
    error_queue: Queue,
):
    """
    Worker function that runs in a separate process.
    Loads the STEP file and renders to SVG.
    """
    try:
        from cadquery import importers, exporters
        
        # Load workplane
        workplane = importers.importStep(step_file_path)
        
        # Get view direction
        proj_dir = VIEW_ANGLES.get(view, (1, 1, 1))
        
        # Ensure output path has .svg extension
        if not output_path.endswith(".svg"):
            output_path = output_path.replace(".png", ".svg")
            if not output_path.endswith(".svg"):
                output_path += ".svg"
        
        # Export to SVG
        exporters.export(
            workplane,
            output_path,
            opt={
                "projectionDir": proj_dir,
                "showAxes": False,
                "showHidden": show_hidden,
                "strokeWidth": 0.5,
                "width": width,
                "height": height,
            }
        )
        
        # Get file size
        file_size = os.path.getsize(output_path)
        
        result_queue.put({
            "success": True,
            "path": output_path,
            "format": "svg",
            "view": view,
            "projection_dir": proj_dir,
            "file_size_kb": round(file_size / 1024, 1),
        })
        
    except Exception as e:
        import traceback
        error_queue.put({
            "success": False,
            "error": str(e),
            "traceback": traceback.format_exc(),
        })


async def capture_screenshot(
    workplane: Any = None,
    step_file_path: str = None,
    view: str = "iso",
    width: int = 800,
    height: int = 600,
    output_dir: Optional[str] = None,
    show_hidden: bool = False,
    timeout_seconds: float = 60.0,
) -> Dict[str, Any]:
    """
    Capture an SVG screenshot in an ISOLATED subprocess.
    
    This prevents CadQuery crashes from affecting the main process.
    
    Args:
        workplane: CadQuery workplane to render
        step_file_path: Path to STEP file (alternative to workplane)
        view: View angle name
        width: SVG width
        height: SVG height
        output_dir: Directory for output file
        show_hidden: Whether to show hidden lines
        timeout_seconds: Maximum time to wait
        
    Returns:
        Dict with success status and file path
    """
    if output_dir is None:
        output_dir = tempfile.gettempdir()
    
    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, f"cad_render_{view}.svg")
    
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
            }
    
    if not step_file_path:
        return {
            "success": False,
            "error": "No workplane or step_file_path provided",
        }
    
    # Create queues for communication
    result_queue = Queue()
    error_queue = Queue()
    
    # Start worker process
    process = Process(
        target=_worker_render,
        args=(step_file_path, output_path, view, width, height, show_hidden, result_queue, error_queue)
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
                "error": f"Screenshot timed out after {timeout_seconds} seconds",
            }
        
        # Check exit code
        if process.exitcode != 0:
            if not error_queue.empty():
                error_data = error_queue.get_nowait()
                return {
                    "success": False,
                    "error": error_data.get("error", f"Process crashed with code {process.exitcode}"),
                }
            return {
                "success": False,
                "error": f"Screenshot process crashed (exit code: {process.exitcode})",
            }
        
        # Get result
        if not result_queue.empty():
            return result_queue.get_nowait()
        elif not error_queue.empty():
            error_data = error_queue.get_nowait()
            return {
                "success": False,
                "error": error_data.get("error", "Unknown error"),
            }
        else:
            return {
                "success": False,
                "error": "No result returned from subprocess",
            }
            
    except Exception as e:
        return {
            "success": False,
            "error": f"Subprocess error: {type(e).__name__}: {str(e)}",
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


async def capture_multiple_views(
    workplane: Any = None,
    step_file_path: str = None,
    views: Optional[list] = None,
    width: int = 800,
    height: int = 600,
    output_dir: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Capture SVG screenshots from multiple view angles.
    Each screenshot runs in its own subprocess.
    """
    if views is None:
        views = ["iso", "top", "front", "right"]
    
    if output_dir is None:
        output_dir = tempfile.mkdtemp(prefix="cad_renders_")
    
    # If we have a workplane, export once and reuse
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
                "images": [],
            }
    
    results = []
    for view in views:
        result = await capture_screenshot(
            step_file_path=step_file_path,
            view=view,
            width=width,
            height=height,
            output_dir=output_dir,
        )
        results.append(result)
    
    # Clean up temp file
    if temp_step and os.path.exists(temp_step.name):
        try:
            os.unlink(temp_step.name)
        except:
            pass
    
    successful = [r for r in results if r.get("success")]
    
    return {
        "success": len(successful) > 0,
        "output_dir": output_dir,
        "images": results,
        "successful_count": len(successful),
        "total_count": len(views),
    }


def read_svg_content(svg_path: str) -> str:
    """Read SVG content for direct LLM consumption."""
    with open(svg_path, "r") as f:
        return f.read()
