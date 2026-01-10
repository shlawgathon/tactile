import cadquery as cq
from typing import Dict, Any, List, Tuple

class PhysicalAnalyzer:
    """Analyze physical properties like mass, center of gravity, and bounding box."""
    
    @staticmethod
    def analyze_physical_properties(workplane: cq.Workplane, density_g_cm3: float = 7.85) -> Dict[str, Any]:
        """
        Calculate mass properties for all solids in the workplane.
        Default density is for Steel (7.85 g/cm³).
        """
        solids = workplane.solids().vals()
        if not solids:
            return {
                "total_volume": 0.0,
                "total_mass": 0.0,
                "center_of_gravity": (0, 0, 0),
                "solids": []
            }
            
        # Density in g/mm³ (1 cm³ = 1000 mm³)
        density_mm = density_g_cm3 / 1000.0
        
        total_volume = 0.0
        weighted_center = cq.Vector(0, 0, 0)
        
        individual_properties = []
        
        for i, solid in enumerate(solids):
            vol = solid.Volume()
            mass = vol * density_mm
            # In CadQuery, solid.Center() returns the center of mass for uniform density
            center = solid.Center()
            
            total_volume += vol
            weighted_center = weighted_center.add(center.multiply(vol))
            
            individual_properties.append({
                "id": f"S{i}",
                "volume": vol,
                "mass": mass,
                "center_of_gravity": (center.x, center.y, center.z),
                "bounding_box": PhysicalAnalyzer._get_bbox_dict(solid.BoundingBox())
            })
            
        if total_volume > 0:
            cog = weighted_center.multiply(1.0 / total_volume)
        else:
            cog = cq.Vector(0, 0, 0)
            
        total_mass = total_volume * density_mm
        
        # Combined Bounding Box
        combined_bbox = solids[0].BoundingBox()
        for s in solids[1:]:
            combined_bbox.add(s.BoundingBox())
            
        return {
            "total_volume": total_volume,
            "total_mass": total_mass,
            "center_of_gravity": (cog.x, cog.y, cog.z),
            "density": density_g_cm3,
            "units": {
                "mass": "g", 
                "volume": "mm³", 
                "density": "g/cm³", 
                "dimensions": "mm"
            },
            "bounding_box": PhysicalAnalyzer._get_bbox_dict(combined_bbox),
            "solids": individual_properties
        }

    @staticmethod
    def _get_bbox_dict(bbox: cq.BoundBox) -> Dict[str, float]:
        return {
            "xmin": bbox.xmin, "xmax": bbox.xmax,
            "ymin": bbox.ymin, "ymax": bbox.ymax,
            "zmin": bbox.zmin, "zmax": bbox.zmax,
            "length": bbox.xlen,
            "width": bbox.ylen,
            "height": bbox.zlen
        }
