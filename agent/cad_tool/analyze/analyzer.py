import cadquery as cq
from typing import List, Dict, Any

from .geometry_analyzer import GeometryAnalyzer
from .surface_analyzer import SurfaceAnalyzer
from .assembly_analyzer import AssemblyAnalyzer

def analyze_dfm(workplane: cq.Workplane, process: str) -> List[Dict[str, Any]]:
    """
    Analyzes the workplane for Design for Manufacturing issues.
    """
    issues = []
    
    # 1. Process Specific Checks
    if process == "CNC_MACHINING":
        # Sharp internal corners
        sharp_corners = GeometryAnalyzer.detect_sharp_internal_corners(workplane)
        issues.extend(sharp_corners)
            
        # Hole dimensions and machinability
        hole_issues = GeometryAnalyzer.analyze_hole_machinability(workplane)
        issues.extend(hole_issues)

        # Hole edge clearance
        edge_clearance = GeometryAnalyzer.analyze_hole_clearance(workplane)
        issues.extend(edge_clearance)
        
        # Pocket accessibility
        pockets = GeometryAnalyzer.analyze_pocket_accessibility(workplane)
        issues.extend(pockets)

        # General wall thickness for CNC
        thickness = GeometryAnalyzer.analyze_wall_thickness(workplane)
        min_thick = thickness.get("min_thickness")
        if min_thick is not None and min_thick < 0.8:
             issues.append({
                 "type": "THIN_WALL",
                 "details": thickness,
                 "severity": "high",
                 "recommendation": "Metal parts typically require >0.8mm wall thickness for CNC machining."
             })

    elif process == "INJECTION_MOLDING":
        # Draft angles
        draft_issues = GeometryAnalyzer.analyze_draft_angles(workplane)
        for issue in draft_issues:
            if issue.get("needs_draft"):
                issue["type"] = "LACK_OF_DRAFT"
                issues.append(issue)
                
        # Undercuts
        undercuts = GeometryAnalyzer.detect_undercuts(workplane)
        issues.extend(undercuts)
            
        # Boss manufacturability
        boss_issues = GeometryAnalyzer.analyze_boss_manufacturability(workplane)
        issues.extend(boss_issues)
        
        # Rib proportions
        rib_issues = GeometryAnalyzer.analyze_rib_proportions(workplane)
        issues.extend(rib_issues)
        
        # Hole edge clearance
        edge_clearance = GeometryAnalyzer.analyze_hole_clearance(workplane)
        issues.extend(edge_clearance)

        # Wall thickness uniformity and minimums
        thickness = GeometryAnalyzer.analyze_wall_thickness(workplane)
        min_thick = thickness.get("min_thickness")
        max_thick = thickness.get("max_thickness")
        
        if min_thick is not None:
            if min_thick < 0.8:
                 issues.append({
                     "type": "THIN_WALL",
                     "details": thickness,
                     "severity": "high",
                     "recommendation": "Increase wall thickness to at least 0.8mm-1.0mm for injection molding."
                 })
            
            if max_thick is not None and min_thick > 0:
                variation = (max_thick - min_thick) / min_thick
                if variation > 0.5:
                    issues.append({
                        "type": "THICKNESS_VARIATION",
                        "details": thickness,
                        "severity": "medium",
                        "recommendation": "Wall thickness varies significantly. Aim for uniform thickness to prevent warping and sink marks."
                    })

    elif process == "FDM_3D_PRINTING":
        # Overhangs
        overhangs = GeometryAnalyzer.analyze_overhangs_3d_print(workplane)
        issues.extend(overhangs)
            
        # Hole edge clearance
        edge_clearance = GeometryAnalyzer.analyze_hole_clearance(workplane)
        issues.extend(edge_clearance)

        # Wall thickness
        thickness = GeometryAnalyzer.analyze_wall_thickness(workplane)
        min_thick = thickness.get("min_thickness")
        if min_thick is not None and min_thick < 0.8:
             issues.append({
                 "type": "THIN_WALL",
                 "details": thickness,
                 "severity": "medium",
                 "recommendation": "Wall thickness below 0.8mm may be fragile or fail to print correctly on FDM machines."
             })

    # 2. General Surface Complexity Checks (Applicable to all processes)
    complex_surfaces = SurfaceAnalyzer.analyze_curvature(workplane)
    for surf in complex_surfaces:
        if surf["complexity"] == "high":
            issues.append({
                "type": "COMPLEX_SURFACE",
                "face_id": surf["face_id"],
                "details": surf,
                "severity": "low",
                "recommendation": "Consider simplifying this BSPLINE surface to reduce manufacturing cost."
            })
            
    efficiency = SurfaceAnalyzer.analyze_surface_area_efficiency(workplane)
    if not efficiency["is_efficient"]:
        issues.append({
            "type": "MATERIAL_EFFICIENCY",
            "details": efficiency,
            "severity": "low",
            "recommendation": "High surface-to-volume ratio. Consider simplifying geometry or increasing thickness."
        })

    # 3. Assembly Checks
    assembly_info = AssemblyAnalyzer.analyze_solids(workplane)
    if assembly_info["solid_count"] > 1:
        interferences = AssemblyAnalyzer.detect_interferences(workplane)
        # Add interferences directly as they already have the right format
        issues.extend(interferences)
        
        clearances = AssemblyAnalyzer.analyze_clearances(workplane)
        issues.extend(clearances)

    # 4. Small Feature detection (General)
    small_features = GeometryAnalyzer.detect_small_features(workplane)
    issues.extend(small_features)

    return issues
