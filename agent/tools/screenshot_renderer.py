"""
CAD Screenshot Renderer - SVG export for LLM consumption.
Uses CadQuery's native SVG export which works without external dependencies.
"""

import os
import tempfile
from typing import Any, Dict, Optional

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
    # Diagonal views (between front and sides)
    "front_right": (1, -1, 0),    # 45° between front and right
    "front_left": (-1, -1, 0),   # 45° between front and left
    "back_right": (1, 1, 0),     # 45° between back and right
    "back_left": (-1, 1, 0),     # 45° between back and left
}


def render_to_svg(
    workplane: Any,
    output_path: str,
    view: str = "iso",
    width: int = 800,
    height: int = 600,
    show_hidden: bool = False,
) -> Dict[str, Any]:
    """
    Render a CadQuery workplane to SVG.
    
    Args:
        workplane: CadQuery workplane to render
        output_path: Path to save SVG (will add .svg if needed)
        view: View angle name
        width: SVG width
        height: SVG height
        show_hidden: Whether to show hidden lines
    
    Returns:
        Dict with success status and file path
    """
    try:
        from cadquery import exporters
        
        # Ensure .svg extension
        if not output_path.endswith(".svg"):
            output_path = output_path.replace(".png", ".svg")
            if not output_path.endswith(".svg"):
                output_path += ".svg"
        
        # Get view direction
        proj_dir = VIEW_ANGLES.get(view, (1, 1, 1))
        
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
        
        return {
            "success": True,
            "path": output_path,
            "format": "svg",
            "view": view,
            "projection_dir": proj_dir,
            "file_size_kb": round(file_size / 1024, 1),
        }
            
    except Exception as e:
        return {"success": False, "error": str(e)}


async def capture_screenshot(
    workplane: Any,
    view: str = "iso",
    width: int = 800,
    height: int = 600,
    output_dir: Optional[str] = None,
) -> Dict[str, Any]:
    """Capture an SVG screenshot of a CadQuery workplane."""
    if output_dir is None:
        output_dir = tempfile.gettempdir()
    
    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, f"cad_render_{view}.svg")
    
    return render_to_svg(workplane, output_path, view, width, height)


async def capture_multiple_views(
    workplane: Any,
    views: Optional[list] = None,
    width: int = 800,
    height: int = 600,
    output_dir: Optional[str] = None,
) -> Dict[str, Any]:
    """Capture SVG screenshots from multiple view angles."""
    if views is None:
        views = ["iso", "top", "front", "right"]
    
    if output_dir is None:
        output_dir = tempfile.mkdtemp(prefix="cad_renders_")
    
    results = []
    for view in views:
        result = await capture_screenshot(workplane, view, width, height, output_dir)
        results.append(result)
    
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


AVAILABLE_VIEWS = list(VIEW_ANGLES.keys())
