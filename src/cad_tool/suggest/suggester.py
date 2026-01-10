"""
AI-powered suggestion generator for DFM issues.
Uses Fireworks AI LLM to generate intelligent fix suggestions and CadQuery code snippets.
"""

import cadquery as cq
from typing import List, Dict, Any, Optional
import logging
import json
import os
import asyncio
import httpx

from .prompts import PromptTemplates
from .code_validator import CodeValidator

logger = logging.getLogger(__name__)


class SuggestionGenerator:
    """
    Generates fix suggestions and CadQuery code snippets using Fireworks AI LLM.
    """

    def __init__(self, api_key: Optional[str] = None, model: str = "accounts/fireworks/models/llama-v3p3-70b-instruct"):
        """
        Initialize the suggestion generator.

        Args:
            api_key: Fireworks AI API key (or from FIREWORKS_API_KEY env var)
            model: LLM model to use
        """
        self.api_key = api_key or os.getenv("FIREWORKS_API_KEY")
        self.model = model
        self.api_url = "https://api.fireworks.ai/inference/v1/chat/completions"
        self.validator = CodeValidator()

        # Check if API key is available
        if not self.api_key:
            logger.warning("FIREWORKS_API_KEY not set - LLM features will be disabled")
            self.llm_enabled = False
        else:
            self.llm_enabled = True

    def generate_suggestions(
        self,
        workplane: cq.Workplane,
        issues: List[Dict[str, Any]],
        manufacturing_process: str,
        geometry_context: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Generate fix suggestions for a list of issues.

        Args:
            workplane: CadQuery Workplane object
            issues: List of issue dicts from analyzer
            manufacturing_process: Manufacturing process type
            geometry_context: Optional geometry data for context

        Returns:
            List of suggestion dicts
        """
        suggestions = []

        for issue in issues:
            try:
                suggestion = self._generate_suggestion_for_issue(
                    workplane=workplane,
                    issue=issue,
                    manufacturing_process=manufacturing_process,
                    geometry_context=geometry_context
                )
                if suggestion:
                    suggestions.append(suggestion)
            except Exception as e:
                logger.error(f"Error generating suggestion for issue {issue.get('ruleId')}: {e}")
                # Create fallback suggestion
                suggestions.append(self._create_fallback_suggestion(issue))

        return suggestions

    def _generate_suggestion_for_issue(
        self,
        workplane: cq.Workplane,
        issue: Dict[str, Any],
        manufacturing_process: str,
        geometry_context: Optional[Dict[str, Any]]
    ) -> Optional[Dict[str, Any]]:
        """
        Generate a suggestion for a single issue using LLM.

        Args:
            workplane: CadQuery Workplane object
            issue: Issue dict
            manufacturing_process: Manufacturing process type
            geometry_context: Optional geometry data

        Returns:
            Suggestion dict or None
        """
        rule_id = issue.get('ruleId', '')

        # Determine if this is an auto-fixable issue
        auto_fixable = issue.get('autoFixAvailable', False)

        # Generate suggestion using LLM if enabled
        if self.llm_enabled and auto_fixable:
            try:
                suggestion = self._llm_generate_suggestion(
                    issue=issue,
                    manufacturing_process=manufacturing_process,
                    geometry_context=geometry_context
                )
                if suggestion:
                    # Validate and enhance the code if present
                    if 'code_snippet' in suggestion and suggestion['code_snippet']:
                        suggestion = self._validate_and_enhance_code(suggestion, workplane)
                    return suggestion
            except Exception as e:
                logger.error(f"LLM generation failed for {rule_id}: {e}")

        # Fallback to rule-based suggestions
        return self._rule_based_suggestion(issue, manufacturing_process)

    def _llm_generate_suggestion(
        self,
        issue: Dict[str, Any],
        manufacturing_process: str,
        geometry_context: Optional[Dict[str, Any]]
    ) -> Optional[Dict[str, Any]]:
        """
        Use Fireworks AI LLM to generate a suggestion.

        Args:
            issue: Issue dict
            manufacturing_process: Manufacturing process type
            geometry_context: Optional geometry data

        Returns:
            Suggestion dict or None
        """
        # Build prompts
        system_prompt = PromptTemplates.get_system_prompt(manufacturing_process)
        user_prompt = PromptTemplates.get_issue_prompt(
            rule_id=issue.get('ruleId', ''),
            issue_data=issue,
            geometry_context=geometry_context
        )

        # Call LLM
        try:
            response = self._call_fireworks_api(system_prompt, user_prompt)

            # Parse response
            suggestion = self._parse_llm_response(response, issue)
            return suggestion

        except Exception as e:
            logger.error(f"Fireworks API call failed: {e}")
            return None

    def _call_fireworks_api(self, system_prompt: str, user_prompt: str) -> str:
        """
        Synchronous wrapper for async Fireworks API call.

        Args:
            system_prompt: System prompt
            user_prompt: User prompt

        Returns:
            LLM response text
        """
        # Run async call in sync context
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        return loop.run_until_complete(
            self._call_fireworks_api_async(system_prompt, user_prompt)
        )

    async def _call_fireworks_api_async(self, system_prompt: str, user_prompt: str) -> str:
        """
        Call Fireworks AI API asynchronously.

        Args:
            system_prompt: System prompt
            user_prompt: User prompt

        Returns:
            LLM response text
        """
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            "max_tokens": 2048,
            "temperature": 0.3,  # Lower temperature for more deterministic output
            "top_p": 0.9,
        }

        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                self.api_url,
                headers=headers,
                json=payload
            )
            response.raise_for_status()

            data = response.json()

            # Extract content from response
            if 'choices' in data and len(data['choices']) > 0:
                return data['choices'][0]['message']['content']
            else:
                raise ValueError("No response content from Fireworks API")

    def _parse_llm_response(self, response: str, issue: Dict[str, Any]) -> Dict[str, Any]:
        """
        Parse LLM response into a suggestion dict.

        Args:
            response: LLM response text
            issue: Original issue dict

        Returns:
            Suggestion dict
        """
        # Try to extract JSON from response
        suggestion_data = self._extract_json_from_text(response)

        if suggestion_data and 'suggestion' in suggestion_data:
            suggestion_data = suggestion_data['suggestion']

        # Build suggestion dict
        suggestion = {
            'issue_id': issue.get('ruleId', ''),
            'description': suggestion_data.get('description', response[:200]) if suggestion_data else response[:200],
            'expected_improvement': suggestion_data.get('expected_improvement', '') if suggestion_data else '',
            'priority': self._determine_priority(issue),
            'code_snippet': '',
            'validated': False,
            'notes': suggestion_data.get('notes', []) if suggestion_data else [],
            'parameters': suggestion_data.get('parameters', {}) if suggestion_data else {}
        }

        # Extract code snippet
        if suggestion_data and 'code_snippet' in suggestion_data:
            suggestion['code_snippet'] = suggestion_data['code_snippet']
        else:
            # Try to extract code from markdown blocks
            code = CodeValidator.extract_code_from_markdown(response)
            if code:
                suggestion['code_snippet'] = code

        return suggestion

    def _extract_json_from_text(self, text: str) -> Optional[Dict[str, Any]]:
        """
        Extract JSON object from text that may contain other content.

        Args:
            text: Text that may contain JSON

        Returns:
            Parsed JSON dict or None
        """
        # Try to find JSON object in text
        import re
        json_pattern = r'\{(?:[^{}]|(?:\{(?:[^{}]|(?:\{[^{}]*\}))*\}))*\}'
        matches = re.findall(json_pattern, text, re.DOTALL)

        for match in matches:
            try:
                data = json.loads(match)
                return data
            except json.JSONDecodeError:
                continue

        return None

    def _validate_and_enhance_code(
        self,
        suggestion: Dict[str, Any],
        workplane: Optional[cq.Workplane]
    ) -> Dict[str, Any]:
        """
        Validate and enhance the generated code.

        Args:
            suggestion: Suggestion dict with code_snippet
            workplane: Optional workplane for testing

        Returns:
            Enhanced suggestion dict
        """
        code = suggestion.get('code_snippet', '')
        if not code:
            return suggestion

        # Clean the code
        code = CodeValidator.clean_code(code)
        suggestion['code_snippet'] = code

        # Validate syntax and safety
        is_valid, error, metadata = CodeValidator.validate_code(code, strict=True)

        suggestion['validation_metadata'] = metadata

        if not is_valid:
            suggestion['validated'] = False
            suggestion['validation_error'] = error
            logger.warning(f"Code validation failed: {error}")
            return suggestion

        # Add validation summary to notes
        if 'notes' not in suggestion:
            suggestion['notes'] = []

        if metadata.get('warnings'):
            suggestion['notes'].extend(metadata['warnings'])

        # Optionally test execution (commented out for safety)
        # if workplane is not None:
        #     success, result, exec_error = CodeValidator.execute_safe(code, workplane)
        #     suggestion['validated'] = success
        #     if not success:
        #         suggestion['execution_error'] = exec_error
        # else:
        #     suggestion['validated'] = True  # Syntax valid, but not executed

        suggestion['validated'] = True  # Mark as validated if syntax is correct

        return suggestion

    def _rule_based_suggestion(
        self,
        issue: Dict[str, Any],
        manufacturing_process: str
    ) -> Dict[str, Any]:
        """
        Generate a rule-based suggestion when LLM is not available.

        Args:
            issue: Issue dict
            manufacturing_process: Manufacturing process type

        Returns:
            Suggestion dict
        """
        rule_id = issue.get('ruleId', '')

        # Map rule IDs to basic fix suggestions
        rule_suggestions = {
            'CNC_001': {
                'description': 'Add fillet radius of 1.5mm or greater to internal corners',
                'code_snippet': '# Add fillet to internal corners\nresult = workplane.edges("|Z").fillet(1.5)',
                'expected_improvement': 'Enables CNC machining with standard end mills',
            },
            'IM_001': {
                'description': 'Add 1-2° draft angle to vertical walls in pull direction',
                'code_snippet': '# Add draft angle to vertical faces\n# Note: Requires rebuilding geometry with draft',
                'expected_improvement': 'Enables easier part ejection from mold',
            },
            'FDM_001': {
                'description': 'Add 45° chamfer or support structures for overhangs',
                'code_snippet': '# Add chamfer to reduce overhang angle\nresult = workplane.faces(">Z").edges().chamfer(2.0)',
                'expected_improvement': 'Reduces or eliminates need for support structures',
            },
        }

        template = rule_suggestions.get(rule_id, {
            'description': issue.get('recommendation', 'Follow the recommendation provided'),
            'code_snippet': '# Manual fix required - see recommendation',
            'expected_improvement': 'Improves manufacturability',
        })

        return {
            'issue_id': rule_id,
            'description': template['description'],
            'expected_improvement': template['expected_improvement'],
            'priority': self._determine_priority(issue),
            'code_snippet': template['code_snippet'],
            'validated': False,
            'notes': ['Generated from rule-based template (LLM not available)']
        }

    def _create_fallback_suggestion(self, issue: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create a basic fallback suggestion when generation fails.

        Args:
            issue: Issue dict

        Returns:
            Basic suggestion dict
        """
        return {
            'issue_id': issue.get('ruleId', ''),
            'description': issue.get('recommendation', 'Review and fix manually'),
            'expected_improvement': 'Resolves the identified DFM issue',
            'priority': self._determine_priority(issue),
            'code_snippet': '# Manual fix required',
            'validated': False,
            'notes': ['Automatic suggestion generation failed']
        }

    def _determine_priority(self, issue: Dict[str, Any]) -> int:
        """
        Determine suggestion priority based on issue severity.

        Args:
            issue: Issue dict

        Returns:
            Priority (1-5, where 5 is highest)
        """
        severity = issue.get('severity', 'INFO')

        priority_map = {
            'ERROR': 5,
            'WARNING': 3,
            'INFO': 1
        }

        return priority_map.get(severity, 3)


def suggest_fixes(workplane: cq.Workplane, issues: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Main entry point: Generate fix suggestions and CadQuery code snippets for issues.

    Args:
        workplane: CadQuery Workplane object
        issues: List of issue dicts from analyzer

    Returns:
        List of suggestion dicts
    """
    if not issues:
        logger.info("No issues to generate suggestions for")
        return []

    # Determine manufacturing process from first issue (should be consistent)
    manufacturing_process = "INJECTION_MOLDING"  # Default

    # Try to infer from rule IDs
    if issues:
        first_rule = issues[0].get('ruleId', '')
        if first_rule.startswith('CNC_'):
            manufacturing_process = "CNC_MACHINING"
        elif first_rule.startswith('FDM_'):
            manufacturing_process = "FDM_3D_PRINTING"
        elif first_rule.startswith('IM_'):
            manufacturing_process = "INJECTION_MOLDING"

    # Create generator and generate suggestions
    generator = SuggestionGenerator()

    logger.info(f"Generating suggestions for {len(issues)} issues (process: {manufacturing_process})")
    suggestions = generator.generate_suggestions(
        workplane=workplane,
        issues=issues,
        manufacturing_process=manufacturing_process
    )

    logger.info(f"Generated {len(suggestions)} suggestions")

    return suggestions


# Convenience functions for specific operations

def generate_fillet_code(edge_selector: str, radius: float) -> str:
    """
    Generate CadQuery code for adding fillets.

    Args:
        edge_selector: Edge selector string (e.g., "|Z", ">X and <Y")
        radius: Fillet radius in mm

    Returns:
        Python code string
    """
    return f'''# Add {radius}mm fillet to selected edges
result = workplane.edges("{edge_selector}").fillet({radius})'''


def generate_chamfer_code(edge_selector: str, length: float) -> str:
    """
    Generate CadQuery code for adding chamfers.

    Args:
        edge_selector: Edge selector string
        length: Chamfer length in mm

    Returns:
        Python code string
    """
    return f'''# Add {length}mm chamfer to selected edges
result = workplane.edges("{edge_selector}").chamfer({length})'''


def generate_shell_code(thickness: float, face_selector: Optional[str] = None) -> str:
    """
    Generate CadQuery code for shell operation.

    Args:
        thickness: Wall thickness in mm
        face_selector: Optional face to remove (e.g., ">Z")

    Returns:
        Python code string
    """
    if face_selector:
        return f'''# Create shell with {thickness}mm wall thickness
result = workplane.faces("{face_selector}").shell(-{thickness})'''
    else:
        return f'''# Create shell with {thickness}mm wall thickness
result = workplane.shell(-{thickness})'''


def generate_hole_code(diameter: float, depth: Optional[float] = None) -> str:
    """
    Generate CadQuery code for adding holes.

    Args:
        diameter: Hole diameter in mm
        depth: Optional hole depth (None for through hole)

    Returns:
        Python code string
    """
    if depth:
        return f'''# Add {diameter}mm diameter hole, {depth}mm deep
result = workplane.hole({diameter}, depth={depth})'''
    else:
        return f'''# Add {diameter}mm diameter through hole
result = workplane.hole({diameter})'''
