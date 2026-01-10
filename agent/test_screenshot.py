"""
Test: Render ALL view angles to SVG.
Runs each view in a subprocess to avoid OCC segfaults.
"""

import os
import sys
import subprocess

VIEWS = [
    "iso", "iso_back", "top", "bottom", 
    "front", "back", "left", "right",
    "front_right", "front_left", "back_right", "back_left"
]

AGENT_DIR = "/Users/xiao/tactile/agent"
PYTHON = "/Users/xiao/tactile/agent/.venv/bin/python"


def render_single(step_file: str, output_dir: str, view: str):
    """Render a single view using a subprocess."""
    script = f'''
import sys
sys.path.insert(0, "{AGENT_DIR}")
import cadquery as cq
from tools.screenshot_renderer import render_to_svg

workplane = cq.importers.importStep("{step_file}")
output_path = "{output_dir}/battery_{view}.svg"
r = render_to_svg(workplane, output_path, view="{view}")
if r.get("success"):
    print("OK " + str(r.get("file_size_kb")) + " KB")
else:
    print("FAIL " + str(r.get("error")))
'''
    
    result = subprocess.run(
        [PYTHON, "-c", script],
        capture_output=True,
        text=True,
        timeout=60
    )
    
    output = result.stdout.strip() if result.stdout else result.stderr.strip()
    return output, result.returncode


def main():
    step_file = "/Users/xiao/tactile/agent/battery.step"
    output_dir = "/Users/xiao/tactile/agent/screenshots"
    os.makedirs(output_dir, exist_ok=True)
    
    print(f"Rendering {len(VIEWS)} views (each in separate process)...\n")
    
    success_count = 0
    for view in VIEWS:
        try:
            output, code = render_single(step_file, output_dir, view)
            if code == 0 and output.startswith("OK"):
                print(f"  ✓ {view}: {output.replace('OK ', '')}")
                success_count += 1
            else:
                print(f"  ✗ {view}: {output[:80] if output else 'crashed'}")
        except subprocess.TimeoutExpired:
            print(f"  ✗ {view}: timeout")
        except Exception as e:
            print(f"  ✗ {view}: {e}")
    
    print(f"\n✅ Done! {success_count}/{len(VIEWS)} views rendered")
    print(f"   Check: {output_dir}")


if __name__ == "__main__":
    main()
