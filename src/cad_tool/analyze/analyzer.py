import cadquery as cq
from typing import List, Dict, Any
from enum import Enum

from .geometry_analyzer import GeometryAnalyzer
from .surface_analyzer import SurfaceAnalyzer
from .assembly_analyzer import AssemblyAnalyzer


class ManufacturingProcess(str, Enum):
    """Manufacturing process types matching OpenAPI spec"""
    INJECTION_MOLDING = "INJECTION_MOLDING"
    CNC_MACHINING = "CNC_MACHINING"
    FDM_3D_PRINTING = "FDM_3D_PRINTING"


class IssueSeverity(str, Enum):
    """Issue severity levels matching OpenAPI spec"""
    ERROR = "ERROR"
    WARNING = "WARNING"
    INFO = "INFO"


def analyze_cad(workplane: cq.Workplane, process: str, material: str = None) -> Dict[str, Any]:
    """
    Performs complete CAD analysis and returns results matching the OpenAPI AnalysisResult schema.

    Args:
        workplane: CadQuery Workplane object
        process: Manufacturing process (INJECTION_MOLDING, CNC_MACHINING, FDM_3D_PRINTING)
        material: Optional material specification

    Returns:
        Dict containing geometry summary and issues in OpenAPI-compliant format
    """
    # Extract geometry summary
    geometry_summary = _extract_geometry_summary(workplane)

    # Perform DFM analysis
    issues = analyze_dfm(workplane, process)

    # Count issues by severity
    issues_by_severity = {
        "ERROR": sum(1 for i in issues if i.get("severity") == IssueSeverity.ERROR),
        "WARNING": sum(1 for i in issues if i.get("severity") == IssueSeverity.WARNING),
        "INFO": sum(1 for i in issues if i.get("severity") == IssueSeverity.INFO)
    }

    return {
        "geometry_summary": geometry_summary,
        "issues": issues,
        "issues_by_severity": issues_by_severity
    }


def _extract_geometry_summary(workplane: cq.Workplane) -> Dict[str, Any]:
    """Extract geometry summary matching OpenAPI BoundingBox schema"""
    try:
        solid = workplane.val()
        bbox = solid.BoundingBox()

        # Calculate dimensions
        width = bbox.xlen
        height = bbox.ylen
        depth = bbox.zlen

        # Get counts
        faces = workplane.faces().vals()
        edges = workplane.edges().vals()

        return {
            "bounding_box": {
                "minX": bbox.xmin,
                "minY": bbox.ymin,
                "minZ": bbox.zmin,
                "maxX": bbox.xmax,
                "maxY": bbox.ymax,
                "maxZ": bbox.zmax,
                "width": width,
                "height": height,
                "depth": depth
            },
            "volume": solid.Volume(),
            "surface_area": sum(f.Area() for f in faces),
            "face_count": len(faces),
            "edge_count": len(edges)
        }
    except Exception as e:
        return {
            "bounding_box": None,
            "volume": 0.0,
            "surface_area": 0.0,
            "face_count": 0,
            "edge_count": 0,
            "error": str(e)
        }


def _create_issue(rule_id: str, rule_name: str, severity: IssueSeverity,
                  description: str, recommendation: str, affected_features: List[str] = None,
                  auto_fix_available: bool = False) -> Dict[str, Any]:
    """
    Creates an issue dict matching the OpenAPI Issue schema.

    Args:
        rule_id: Unique identifier for the DFM rule
        rule_name: Human-readable rule name
        severity: ERROR, WARNING, or INFO
        description: Detailed description of the issue
        recommendation: How to fix the issue
        affected_features: List of affected feature IDs (face/edge identifiers)
        auto_fix_available: Whether automatic fix is available

    Returns:
        Issue dict matching OpenAPI schema
    """
    return {
        "ruleId": rule_id,
        "ruleName": rule_name,
        "severity": severity.value if isinstance(severity, IssueSeverity) else severity,
        "description": description,
        "affectedFeatures": affected_features or [],
        "recommendation": recommendation,
        "autoFixAvailable": auto_fix_available
    }


def analyze_dfm(workplane: cq.Workplane, process: str) -> List[Dict[str, Any]]:
    """
    Analyzes the workplane for Design for Manufacturing issues.
    Returns issues in OpenAPI-compliant format with ruleId, ruleName, severity, etc.
    """
    issues = []

    # 1. Process Specific Checks
    if process == "CNC_MACHINING":
        # Sharp internal corners
        sharp_corners = GeometryAnalyzer.detect_sharp_internal_corners(workplane)
        for corner in sharp_corners:
            issues.append(_create_issue(
                rule_id="CNC_001",
                rule_name="Sharp Internal Corners",
                severity=IssueSeverity.ERROR,
                description=f"Sharp internal corner detected with radius < 1.5mm. {corner.get('details', '')}",
                recommendation="Add fillet radius ≥ 1.5mm (matching tool radius) to internal corners for CNC accessibility.",
                affected_features=corner.get("affected_features", []),
                auto_fix_available=True
            ))

        # Hole dimensions and machinability
        hole_issues = GeometryAnalyzer.analyze_hole_machinability(workplane)
        for hole in hole_issues:
            issues.append(_create_issue(
                rule_id="CNC_002",
                rule_name="Hole Machinability",
                severity=IssueSeverity.WARNING if hole.get("severity") == "medium" else IssueSeverity.ERROR,
                description=hole.get("description", "Hole may be difficult to machine"),
                recommendation=hole.get("recommendation", "Review hole dimensions and depth-to-diameter ratio."),
                affected_features=hole.get("affected_features", [])
            ))

        # Hole edge clearance
        edge_clearance = GeometryAnalyzer.analyze_hole_clearance(workplane)
        for clearance in edge_clearance:
            issues.append(_create_issue(
                rule_id="CNC_003",
                rule_name="Hole Edge Clearance",
                severity=IssueSeverity.WARNING,
                description=clearance.get("description", "Insufficient clearance between hole and edge"),
                recommendation=clearance.get("recommendation", "Ensure minimum 2x wall thickness between holes and edges."),
                affected_features=clearance.get("affected_features", [])
            ))

        # Pocket accessibility
        pockets = GeometryAnalyzer.analyze_pocket_accessibility(workplane)
        for pocket in pockets:
            issues.append(_create_issue(
                rule_id="CNC_004",
                rule_name="Pocket Accessibility",
                severity=IssueSeverity.WARNING,
                description=pocket.get("description", "Pocket may be difficult to access"),
                recommendation=pocket.get("recommendation", "Ensure pocket depth ≤ 3x tool diameter for optimal machining."),
                affected_features=pocket.get("affected_features", [])
            ))

        # General wall thickness for CNC
        thickness = GeometryAnalyzer.analyze_wall_thickness(workplane)
        min_thick = thickness.get("min_thickness")
        if min_thick is not None and min_thick < 0.8:
            issues.append(_create_issue(
                rule_id="CNC_005",
                rule_name="Minimum Wall Thickness",
                severity=IssueSeverity.ERROR,
                description=f"Wall thickness of {min_thick:.2f}mm is below minimum for CNC machining.",
                recommendation="Metal parts typically require ≥0.8mm wall thickness for CNC machining stability.",
                affected_features=[]
            ))

    elif process == "INJECTION_MOLDING":
        # Draft angles
        draft_issues = GeometryAnalyzer.analyze_draft_angles(workplane)
        for issue in draft_issues:
            if issue.get("needs_draft"):
                issues.append(_create_issue(
                    rule_id="IM_001",
                    rule_name="Insufficient Draft Angle",
                    severity=IssueSeverity.ERROR,
                    description=f"Face requires draft angle. {issue.get('description', '')}",
                    recommendation="Add minimum 0.5° draft (1-2° recommended) in pull direction for easy part ejection.",
                    affected_features=issue.get("affected_features", []),
                    auto_fix_available=True
                ))

        # Undercuts
        undercuts = GeometryAnalyzer.detect_undercuts(workplane)
        for undercut in undercuts:
            issues.append(_create_issue(
                rule_id="IM_002",
                rule_name="Undercut Detection",
                severity=IssueSeverity.ERROR,
                description=undercut.get("description", "Undercut detected that prevents straight mold ejection"),
                recommendation="Remove undercuts or design for side-action/lifter mechanisms (increases cost).",
                affected_features=undercut.get("affected_features", [])
            ))

        # Boss manufacturability
        boss_issues = GeometryAnalyzer.analyze_boss_manufacturability(workplane)
        for boss in boss_issues:
            issues.append(_create_issue(
                rule_id="IM_003",
                rule_name="Boss Design",
                severity=IssueSeverity.WARNING,
                description=boss.get("description", "Boss design may cause sink marks or structural issues"),
                recommendation=boss.get("recommendation", "Ensure boss outer diameter is 2x inner diameter and add ribs for support."),
                affected_features=boss.get("affected_features", [])
            ))

        # Rib proportions
        rib_issues = GeometryAnalyzer.analyze_rib_proportions(workplane)
        for rib in rib_issues:
            issues.append(_create_issue(
                rule_id="IM_004",
                rule_name="Rib Proportions",
                severity=IssueSeverity.WARNING,
                description=rib.get("description", "Rib proportions may cause sink marks or warping"),
                recommendation="Rib thickness should be 50-70% of wall thickness, height ≤ 3x rib thickness.",
                affected_features=rib.get("affected_features", [])
            ))

        # Hole edge clearance
        edge_clearance = GeometryAnalyzer.analyze_hole_clearance(workplane)
        for clearance in edge_clearance:
            issues.append(_create_issue(
                rule_id="IM_005",
                rule_name="Feature Edge Clearance",
                severity=IssueSeverity.WARNING,
                description=clearance.get("description", "Insufficient clearance between features"),
                recommendation=clearance.get("recommendation", "Maintain adequate spacing between features."),
                affected_features=clearance.get("affected_features", [])
            ))

        # Wall thickness uniformity and minimums
        thickness = GeometryAnalyzer.analyze_wall_thickness(workplane)
        min_thick = thickness.get("min_thickness")
        max_thick = thickness.get("max_thickness")

        if min_thick is not None:
            if min_thick < 0.8:
                issues.append(_create_issue(
                    rule_id="IM_006",
                    rule_name="Minimum Wall Thickness",
                    severity=IssueSeverity.ERROR,
                    description=f"Wall thickness of {min_thick:.2f}mm is below minimum for injection molding.",
                    recommendation="Increase wall thickness to at least 0.8mm-1.0mm for injection molding.",
                    affected_features=[]
                ))

            if max_thick is not None and min_thick > 0:
                variation = (max_thick - min_thick) / min_thick
                if variation > 0.5:
                    issues.append(_create_issue(
                        rule_id="IM_007",
                        rule_name="Wall Thickness Uniformity",
                        severity=IssueSeverity.WARNING,
                        description=f"Wall thickness varies by {variation*100:.1f}% (min: {min_thick:.2f}mm, max: {max_thick:.2f}mm).",
                        recommendation="Aim for uniform thickness (±25% variation) to prevent warping and sink marks.",
                        affected_features=[]
                    ))

    elif process == "FDM_3D_PRINTING":
        # Overhangs
        overhangs = GeometryAnalyzer.analyze_overhangs_3d_print(workplane)
        for overhang in overhangs:
            issues.append(_create_issue(
                rule_id="FDM_001",
                rule_name="Overhang Angle",
                severity=IssueSeverity.WARNING,
                description=overhang.get("description", "Overhang exceeds 45° and may require support structures"),
                recommendation="Redesign to keep overhangs ≤45° from vertical or add support structures.",
                affected_features=overhang.get("affected_features", [])
            ))

        # Hole edge clearance
        edge_clearance = GeometryAnalyzer.analyze_hole_clearance(workplane)
        for clearance in edge_clearance:
            issues.append(_create_issue(
                rule_id="FDM_002",
                rule_name="Feature Spacing",
                severity=IssueSeverity.WARNING,
                description=clearance.get("description", "Insufficient spacing between features"),
                recommendation=clearance.get("recommendation", "Ensure adequate spacing for print quality."),
                affected_features=clearance.get("affected_features", [])
            ))

        # Wall thickness
        thickness = GeometryAnalyzer.analyze_wall_thickness(workplane)
        min_thick = thickness.get("min_thickness")
        if min_thick is not None and min_thick < 0.8:
            issues.append(_create_issue(
                rule_id="FDM_003",
                rule_name="Minimum Wall Thickness",
                severity=IssueSeverity.WARNING,
                description=f"Wall thickness of {min_thick:.2f}mm is below recommended minimum for FDM.",
                recommendation="Wall thickness below 0.8mm (2x nozzle diameter) may be fragile or fail to print.",
                affected_features=[]
            ))

    # 2. General Surface Complexity Checks (Applicable to all processes)
    complex_surfaces = SurfaceAnalyzer.analyze_curvature(workplane)
    for surf in complex_surfaces:
        if surf.get("complexity") == "high":
            issues.append(_create_issue(
                rule_id="GEN_001",
                rule_name="Complex Surface Geometry",
                severity=IssueSeverity.INFO,
                description=f"Complex BSPLINE surface detected (face {surf.get('face_id', 'unknown')}).",
                recommendation="Consider simplifying this surface to reduce manufacturing complexity and cost.",
                affected_features=[str(surf.get("face_id", ""))]
            ))

    efficiency = SurfaceAnalyzer.analyze_surface_area_efficiency(workplane)
    if not efficiency.get("is_efficient", True):
        issues.append(_create_issue(
            rule_id="GEN_002",
            rule_name="Material Efficiency",
            severity=IssueSeverity.INFO,
            description=f"High surface-to-volume ratio: {efficiency.get('ratio', 0):.2f}",
            recommendation="Consider simplifying geometry or increasing thickness to improve material efficiency.",
            affected_features=[]
        ))

    # 3. Assembly Checks
    assembly_info = AssemblyAnalyzer.analyze_solids(workplane)
    if assembly_info.get("solid_count", 0) > 1:
        interferences = AssemblyAnalyzer.detect_interferences(workplane)
        for interference in interferences:
            issues.append(_create_issue(
                rule_id="ASM_001",
                rule_name="Part Interference",
                severity=IssueSeverity.ERROR,
                description=interference.get("description", "Parts overlap in assembly"),
                recommendation="Adjust part positions or geometry to eliminate interference.",
                affected_features=interference.get("affected_features", [])
            ))

        clearances = AssemblyAnalyzer.analyze_clearances(workplane)
        for clearance in clearances:
            issues.append(_create_issue(
                rule_id="ASM_002",
                rule_name="Assembly Clearance",
                severity=IssueSeverity.WARNING,
                description=clearance.get("description", "Insufficient clearance between parts"),
                recommendation=clearance.get("recommendation", "Ensure adequate clearance for assembly."),
                affected_features=clearance.get("affected_features", [])
            ))

    # 4. Small Feature detection (General)
    small_features = GeometryAnalyzer.detect_small_features(workplane)
    for feature in small_features:
        issues.append(_create_issue(
            rule_id="GEN_003",
            rule_name="Small Feature Detection",
            severity=IssueSeverity.WARNING,
            description=feature.get("description", "Feature may be too small to manufacture reliably"),
            recommendation=feature.get("recommendation", "Increase feature size or remove if not critical."),
            affected_features=feature.get("affected_features", [])
        ))

    return issues
