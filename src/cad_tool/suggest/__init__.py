"""
Suggest module - AI-powered fix suggestion generation for DFM issues.
"""

from .suggester import (
    suggest_fixes,
    SuggestionGenerator,
    generate_fillet_code,
    generate_chamfer_code,
    generate_shell_code,
    generate_hole_code,
)

from .code_validator import CodeValidator
from .prompts import PromptTemplates

__all__ = [
    # Main functions
    'suggest_fixes',
    'SuggestionGenerator',

    # Code generators
    'generate_fillet_code',
    'generate_chamfer_code',
    'generate_shell_code',
    'generate_hole_code',

    # Utilities
    'CodeValidator',
    'PromptTemplates',
]
