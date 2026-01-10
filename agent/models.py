"""
Pydantic models for the Agent Module API.
Matches the schema from plan.md sections 4.5-4.7.
"""

from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
from enum import Enum


class ManufacturingProcess(str, Enum):
    INJECTION_MOLDING = "INJECTION_MOLDING"
    CNC_MACHINING = "CNC_MACHINING"
    FDM_3D_PRINTING = "FDM_3D_PRINTING"


class Severity(str, Enum):
    ERROR = "ERROR"
    WARNING = "WARNING"
    INFO = "INFO"


class Issue(BaseModel):
    """A DFM issue detected in the CAD model."""
    rule_id: str
    rule_name: str
    severity: Severity
    description: str
    affected_features: List[str] = Field(default_factory=list, description="Face/edge IDs")
    recommendation: str
    auto_fix_available: bool = False


class Suggestion(BaseModel):
    """A suggested fix for a detected issue."""
    issue_id: str
    description: str
    expected_improvement: str
    priority: int = Field(ge=1, le=5, description="1-5 priority scale")
    code_snippet: str = Field(description="CadQuery code to apply fix")
    validated: bool = False


class GeometrySummary(BaseModel):
    """Summary of the CAD model geometry."""
    bounding_box: Dict[str, float] = Field(description="xmin, xmax, ymin, ymax, zmin, zmax")
    volume: Optional[float] = None
    surface_area: Optional[float] = None
    face_count: int = 0
    edge_count: int = 0


class AnalyzeRequest(BaseModel):
    """Request payload for the /analyze endpoint."""
    job_id: Optional[str] = None
    file_url: Optional[str] = Field(None, description="URL to STEP file")
    cad_description: Optional[str] = Field(None, description="Text description for LLM analysis")
    manufacturing_process: ManufacturingProcess
    material: Optional[str] = None
    pull_direction: tuple[float, float, float] = (0, 0, 1)


class AnalyzeResponse(BaseModel):
    """Response payload from the /analyze endpoint."""
    job_id: Optional[str] = None
    success: bool
    geometry_summary: Optional[GeometrySummary] = None
    issues: List[Issue] = Field(default_factory=list)
    suggestions: List[Suggestion] = Field(default_factory=list)
    markdown_report: str = Field(description="Formatted markdown output")
    error: Optional[str] = None
