import cadquery as cq
from typing import List, Dict, Any
import math

class SurfaceAnalyzer:
    """Analyze surface properties of the CAD model."""
    
    @staticmethod
    def analyze_curvature(workplane: cq.Workplane) -> List[Dict[str, Any]]:
        """Identify high curvature or complex regions that might be difficult to manufacture."""
        faces = workplane.faces().vals()
        results = []
        for i, face in enumerate(faces):
            geom_type = face.geomType()
            if geom_type != "PLANE":
                # For non-planar faces, check complexity
                complexity = "low"
                if geom_type in ["CYLINDER", "CONE", "SPHERE"]:
                    complexity = "medium"
                elif geom_type in ["TORUS", "BSPLINE", "OFFSET", "OTHER"]:
                    complexity = "high"
                
                results.append({
                    "face_id": f"F{i}",
                    "type": geom_type,
                    "complexity": complexity,
                    "area": face.Area(),
                    "recommendation": f"Complex {geom_type} surface detected. Ensure it's necessary for the design."
                })
        return results

    @staticmethod
    def analyze_surface_area_efficiency(workplane: cq.Workplane) -> Dict[str, Any]:
        """Calculate surface area to volume ratio. Higher ratios indicate less efficient designs."""
        try:
            solid = workplane.val()
            if not solid:
                return {"error": "No solid found"}
            
            area = solid.Area()
            volume = solid.Volume()
            ratio = area / volume if volume > 0 else 0
            
            # Reference: for a cube of side L, A/V = 6/L. For a sphere, A/V = 3/R.
            # We can use a characteristic length from bounding box to normalize.
            bbox = solid.BoundingBox()
            char_length = (bbox.xlen + bbox.ylen + bbox.zlen) / 3
            normalized_ratio = ratio * char_length
            
            return {
                "surface_area": area,
                "volume": volume,
                "area_to_volume_ratio": ratio,
                "normalized_ratio": normalized_ratio,
                "is_efficient": normalized_ratio < 10.0,  # Heuristic threshold
                "description": "Surface area to volume ratio normalized by characteristic length."
            }
        except:
             return {"error": "Analysis failed"}

    @staticmethod
    def detect_fillets_and_chamfers(workplane: cq.Workplane) -> List[Dict[str, Any]]:
        """Detect existing fillets and chamfers based on geometry."""
        faces = workplane.faces().vals()
        features = []
        for i, face in enumerate(faces):
            geom_type = face.geomType()
            # Fillets are often cylindrical or toroidal; chamfers are often conical or planar at an angle
            if geom_type in ["CYLINDER", "CONE", "TORUS"]:
                features.append({
                    "face_id": f"F{i}",
                    "type": "potential_fillet_or_chamfer",
                    "geometry": geom_type,
                    "area": face.Area()
                })
        return features
