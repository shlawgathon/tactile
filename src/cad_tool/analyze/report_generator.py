from typing import List, Dict, Any
import cadquery as cq
from .geometry_analyzer import GeometryAnalyzer
from .surface_analyzer import SurfaceAnalyzer
from .assembly_analyzer import AssemblyAnalyzer
from .physical_analyzer import PhysicalAnalyzer

class AnalysisReportGenerator:
    """Consolidate results from various analyzers into a single report."""
    
    @staticmethod
    def generate_full_report(workplane: cq.Workplane, process: str) -> Dict[str, Any]:
        from .analyzer import analyze_dfm
        
        issues = analyze_dfm(workplane, process)
        
        report = {
            "process": process,
            "physical_properties": PhysicalAnalyzer.analyze_physical_properties(workplane),
            "geometry_analysis": {},
            "surface_analysis": {},
            "assembly_analysis": {},
            "issues": issues,
            "summary": {
                "total_issues": len(issues),
                "critical_issues": len([i for i in issues if i.get("severity") == "high" or "CRITICAL" in i.get("recommendation", "")])
            }
        }
        
        # Detailed Geometry Analysis
        report["geometry_analysis"]["draft_angles"] = GeometryAnalyzer.analyze_draft_angles(workplane)
        report["geometry_analysis"]["undercuts"] = GeometryAnalyzer.detect_undercuts(workplane)
        report["geometry_analysis"]["overhangs"] = GeometryAnalyzer.analyze_overhangs_3d_print(workplane)
        report["geometry_analysis"]["holes"] = GeometryAnalyzer.analyze_hole_dimensions(workplane)
        report["geometry_analysis"]["machinability"] = GeometryAnalyzer.analyze_hole_machinability(workplane)
        report["geometry_analysis"]["hole_clearance"] = GeometryAnalyzer.analyze_hole_clearance(workplane)
        report["geometry_analysis"]["bosses"] = GeometryAnalyzer.analyze_boss_manufacturability(workplane)
        report["geometry_analysis"]["ribs"] = GeometryAnalyzer.analyze_rib_proportions(workplane)
        report["geometry_analysis"]["pockets"] = GeometryAnalyzer.analyze_pocket_accessibility(workplane)
        report["geometry_analysis"]["wall_thickness"] = GeometryAnalyzer.analyze_wall_thickness(workplane)
        report["geometry_analysis"]["small_features"] = GeometryAnalyzer.detect_small_features(workplane)
        
        # Surface Analysis
        report["surface_analysis"]["curvature"] = SurfaceAnalyzer.analyze_curvature(workplane)
        report["surface_analysis"]["efficiency"] = SurfaceAnalyzer.analyze_surface_area_efficiency(workplane)
        
        # Assembly Analysis
        report["assembly_analysis"]["solids"] = AssemblyAnalyzer.analyze_solids(workplane)
        report["assembly_analysis"]["interferences"] = AssemblyAnalyzer.detect_interferences(workplane)
        report["assembly_analysis"]["clearances"] = AssemblyAnalyzer.analyze_clearances(workplane)
        
        return report
