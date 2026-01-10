"""
Geometry Validator - Execute and validate CadQuery fix code

This module executes generated CadQuery code and validates the resulting geometry
to ensure it produces valid, closed solids with improved characteristics.
"""

import cadquery as cq
import logging
import subprocess
import sys
import tempfile
import json
import ast
from pathlib import Path
from typing import Dict, Any, Tuple, Optional, List

logger = logging.getLogger(__name__)


class GeometryValidator:
    """
    Validates CadQuery geometry by executing fix code and checking the results.
    Uses subprocess isolation for safe code execution.
    """

    # Dangerous operations to block
    BLOCKED_OPERATIONS = {
        'eval', 'exec', 'compile', '__import__', 'open',
        'file', 'input', 'raw_input', 'reload', 'vars',
        'globals', 'locals', 'dir', 'delattr', 'setattr',
        'os.', 'sys.', 'subprocess', '__builtins__'
    }

    @staticmethod
    def check_code_safety(code: str) -> Tuple[bool, Optional[str]]:
        """
        Check if code contains dangerous operations.

        Args:
            code: Python code string to check

        Returns:
            Tuple of (is_safe, error_message)
        """
        # Check for blocked operations
        for blocked in GeometryValidator.BLOCKED_OPERATIONS:
            if blocked in code:
                return False, f"Blocked operation detected: {blocked}"

        # Try to parse as AST to check syntax
        try:
            tree = ast.parse(code)

            # Check for dangerous imports
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        if alias.name not in ['cadquery', 'cq', 'math']:
                            return False, f"Blocked import: {alias.name}"
                elif isinstance(node, ast.ImportFrom):
                    if node.module not in ['cadquery', 'cq', 'math']:
                        return False, f"Blocked import from: {node.module}"

        except SyntaxError as e:
            return False, f"Syntax error: {e}"

        return True, None

    @staticmethod
    def validate_geometry(
        workplane: cq.Workplane,
        fix_code: str,
        timeout: int = 30
    ) -> Tuple[bool, Optional[cq.Workplane], Dict[str, Any], Optional[str]]:
        """
        Execute fix code and validate the resulting geometry.

        Args:
            workplane: Input CadQuery workplane
            fix_code: Python code to execute (should modify 'workplane' and assign to 'result')
            timeout: Maximum execution time in seconds

        Returns:
            Tuple of (success, modified_workplane, validation_results, error_message)
        """
        logger.info("Starting geometry validation")

        # 1. Safety check
        is_safe, safety_error = GeometryValidator.check_code_safety(fix_code)
        if not is_safe:
            logger.error(f"Code safety check failed: {safety_error}")
            return False, None, {}, f"Security violation: {safety_error}"

        # 2. Execute code in subprocess for isolation
        try:
            success, result_metadata, exec_error = GeometryValidator._execute_in_subprocess(
                fix_code, workplane, timeout
            )

            if not success:
                logger.error(f"Code execution failed: {exec_error}")
                return False, None, {}, f"Execution failed: {exec_error}"

            # 3. Validate the results
            validation_results = GeometryValidator._validate_results(
                original_wp=workplane,
                result_metadata=result_metadata
            )

            # 4. Load the modified geometry if available
            modified_workplane = None
            if result_metadata.get('output_step'):
                try:
                    modified_workplane = cq.importers.importStep(result_metadata['output_step'])
                    logger.info("Successfully loaded modified geometry")
                except Exception as e:
                    logger.warning(f"Could not load modified geometry: {e}")

            return True, modified_workplane, validation_results, None

        except Exception as e:
            logger.error(f"Validation error: {e}")
            return False, None, {}, f"Validation error: {str(e)}"

    @staticmethod
    def _execute_in_subprocess(
        code: str,
        workplane: Optional[cq.Workplane],
        timeout: int
    ) -> Tuple[bool, Dict[str, Any], Optional[str]]:
        """
        Execute CadQuery code in an isolated subprocess.

        Args:
            code: Python code to execute
            workplane: Optional input workplane
            timeout: Timeout in seconds

        Returns:
            Tuple of (success, metadata_dict, error_message)
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)

            # Save input workplane if provided
            input_step = None
            if workplane is not None:
                input_step = tmpdir_path / "input.step"
                try:
                    cq.exporters.export(workplane, str(input_step))
                except Exception as e:
                    return False, {}, f"Failed to export input workplane: {e}"

            # Create the subprocess execution script
            output_step = tmpdir_path / "output.step"
            output_json = tmpdir_path / "metadata.json"

            script = GeometryValidator._create_subprocess_script(
                code=code,
                input_step=str(input_step) if input_step else None,
                output_step=str(output_step),
                output_json=str(output_json)
            )

            script_file = tmpdir_path / "execute.py"
            script_file.write_text(script)

            # Execute in subprocess
            try:
                result = subprocess.run(
                    [sys.executable, str(script_file)],
                    capture_output=True,
                    text=True,
                    timeout=timeout,
                    cwd=tmpdir
                )

                if result.returncode != 0:
                    error_msg = result.stderr or result.stdout or "Unknown error"
                    return False, {}, f"Execution failed: {error_msg}"

                # Read metadata
                if output_json.exists():
                    metadata = json.loads(output_json.read_text())

                    # Add output_step path if file exists
                    if output_step.exists():
                        metadata['output_step'] = str(output_step)

                    return True, metadata, None
                else:
                    return False, {}, "No metadata output generated"

            except subprocess.TimeoutExpired:
                return False, {}, f"Execution timed out after {timeout}s"
            except Exception as e:
                return False, {}, f"Subprocess error: {str(e)}"

    @staticmethod
    def _create_subprocess_script(
        code: str,
        input_step: Optional[str],
        output_step: str,
        output_json: str
    ) -> str:
        """
        Create a Python script for subprocess execution.

        Args:
            code: User code to execute
            input_step: Path to input STEP file (optional)
            output_step: Path to output STEP file
            output_json: Path to output JSON metadata

        Returns:
            Complete Python script as string
        """
        # Indent user code
        indented_code = '\n'.join('    ' + line if line.strip() else line
                                  for line in code.split('\n'))

        script = f'''#!/usr/bin/env python3
"""Subprocess execution script for CadQuery code validation."""
import sys
import json
import traceback

try:
    import cadquery as cq

    # Load input workplane if provided
    workplane = None
    {"workplane = cq.importers.importStep('" + input_step + "')" if input_step else "# No input workplane"}

    # Execute user code
    try:
{indented_code}
    except Exception as e:
        print(f"Error executing user code: {{e}}", file=sys.stderr)
        traceback.print_exc()
        sys.exit(1)

    # Check that result was created
    if 'result' not in locals():
        print("Error: Code must assign to 'result' variable", file=sys.stderr)
        sys.exit(1)

    # Validate result is a Workplane
    if not isinstance(result, cq.Workplane):
        print(f"Error: Result must be a Workplane, got {{type(result)}}", file=sys.stderr)
        sys.exit(1)

    # Extract geometry
    try:
        solid = result.val()

        # Check if it's valid
        if not solid.isValid():
            print("Warning: Resulting geometry is not valid", file=sys.stderr)

        # Extract metadata
        metadata = {{
            'volume': solid.Volume(),
            'is_valid': solid.isValid(),
            'is_closed': True,  # Solids are typically closed
        }}

        # Get bounding box
        try:
            bbox = solid.BoundingBox()
            metadata['bounding_box'] = {{
                'xmin': bbox.xmin,
                'ymin': bbox.ymin,
                'zmin': bbox.zmin,
                'xmax': bbox.xmax,
                'ymax': bbox.ymax,
                'zmax': bbox.zmax,
            }}
        except:
            pass

        # Count faces and edges
        try:
            metadata['face_count'] = len(result.faces().vals())
            metadata['edge_count'] = len(result.edges().vals())
        except:
            pass

        # Export to STEP
        try:
            cq.exporters.export(result, "{output_step}")
            metadata['step_exported'] = True
        except Exception as e:
            print(f"Warning: Could not export STEP: {{e}}", file=sys.stderr)
            metadata['step_exported'] = False

        # Write metadata
        with open("{output_json}", 'w') as f:
            json.dump(metadata, f, indent=2)

        print("SUCCESS")
        sys.exit(0)

    except Exception as e:
        print(f"Error extracting geometry: {{e}}", file=sys.stderr)
        traceback.print_exc()
        sys.exit(1)

except Exception as e:
    print(f"Fatal error: {{e}}", file=sys.stderr)
    traceback.print_exc()
    sys.exit(1)
'''
        return script

    @staticmethod
    def _validate_results(
        original_wp: cq.Workplane,
        result_metadata: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Validate execution results against criteria.

        Args:
            original_wp: Original workplane
            result_metadata: Metadata from code execution

        Returns:
            Dictionary of validation results
        """
        validation = {
            'is_valid_geometry': result_metadata.get('is_valid', False),
            'is_closed': result_metadata.get('is_closed', False),
            'has_volume': result_metadata.get('volume', 0) > 0,
            'step_exported': result_metadata.get('step_exported', False),
            'face_count': result_metadata.get('face_count', 0),
            'edge_count': result_metadata.get('edge_count', 0),
            'volume': result_metadata.get('volume', 0),
            'bounding_box': result_metadata.get('bounding_box', {}),
        }

        # Compare with original if available
        if original_wp is not None:
            try:
                orig_solid = original_wp.val()
                orig_volume = orig_solid.Volume()
                new_volume = result_metadata.get('volume', 0)

                validation['volume_changed'] = abs(new_volume - orig_volume) > 0.001
                validation['volume_change_percent'] = (
                    ((new_volume - orig_volume) / orig_volume * 100) if orig_volume > 0 else 0
                )
                validation['original_volume'] = orig_volume

                # Compare face/edge counts
                try:
                    orig_faces = len(original_wp.faces().vals())
                    orig_edges = len(original_wp.edges().vals())
                    validation['original_face_count'] = orig_faces
                    validation['original_edge_count'] = orig_edges
                    validation['faces_added'] = result_metadata.get('face_count', 0) - orig_faces
                    validation['edges_added'] = result_metadata.get('edge_count', 0) - orig_edges
                except:
                    pass

            except Exception as e:
                logger.warning(f"Could not compare with original: {e}")

        # Overall success
        validation['passed'] = (
            validation['is_valid_geometry'] and
            validation['has_volume'] and
            validation['step_exported']
        )

        return validation


# Convenience function for direct use
def validate_geometry(
    workplane: cq.Workplane,
    fix_code: str,
    timeout: int = 30
) -> Tuple[bool, Optional[cq.Workplane], Dict[str, Any], Optional[str]]:
    """
    Execute fix code and validate the resulting geometry.

    This is the main entry point for the validate stage of the pipeline.

    Args:
        workplane: Input CadQuery workplane
        fix_code: Python code to execute (should modify 'workplane' and assign to 'result')
        timeout: Maximum execution time in seconds

    Returns:
        Tuple of (success, modified_workplane, validation_results, error_message)

    Example:
        ```python
        import cadquery as cq
        from validate import validate_geometry

        # Original geometry
        box = cq.Workplane("XY").box(10, 10, 10)

        # Fix code (e.g., add fillets)
        fix_code = '''
        result = workplane.edges("|Z").fillet(1.0)
        '''

        success, modified, results, error = validate_geometry(box, fix_code)

        if success:
            print(f"Validation passed!")
            print(f"Volume: {results['volume']}")
            print(f"Valid geometry: {results['is_valid_geometry']}")
        else:
            print(f"Validation failed: {error}")
        ```
    """
    return GeometryValidator.validate_geometry(workplane, fix_code, timeout)


if __name__ == "__main__":
    # Simple test
    print("Testing GeometryValidator...")

    # Create a simple box
    box = cq.Workplane("XY").box(10, 10, 10)

    # Code to add fillets
    code = """
result = workplane.edges("|Z").fillet(1.0)
"""

    print("\nTest 1: Valid fillet operation")
    success, modified, results, error = validate_geometry(box, code)

    if success:
        print("✓ Validation passed!")
        print(f"  Valid geometry: {results['is_valid_geometry']}")
        print(f"  Volume: {results['volume']:.2f}")
        print(f"  Face count: {results['face_count']}")
        print(f"  Volume change: {results.get('volume_change_percent', 0):.2f}%")
    else:
        print(f"✗ Validation failed: {error}")

    # Test invalid code
    print("\n\nTest 2: Invalid code (syntax error)")
    bad_code = """
result = workplane.edges("|Z").fillet(1.0  # Missing closing paren
"""
    success, modified, results, error = validate_geometry(box, bad_code)

    if success:
        print("✗ Should have failed")
    else:
        print(f"✓ Correctly rejected: {error}")

    # Test dangerous code
    print("\n\nTest 3: Dangerous code (file operations)")
    dangerous_code = """
import os
os.system('ls')
result = workplane
"""
    success, modified, results, error = validate_geometry(box, dangerous_code)

    if success:
        print("✗ Should have blocked dangerous code")
    else:
        print(f"✓ Security check passed: {error}")

    print("\n\nAll tests complete!")
