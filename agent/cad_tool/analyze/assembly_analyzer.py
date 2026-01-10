import cadquery as cq
from typing import List, Dict, Any

class AssemblyAnalyzer:
    """Analyze assembly-level properties and multi-solid interactions."""
    
    @staticmethod
    def analyze_solids(workplane: cq.Workplane) -> Dict[str, Any]:
        """Count and evaluate individual solids in the workplane."""
        solids = workplane.solids().vals()
        return {
            "solid_count": len(solids),
            "is_assembly": len(solids) > 1,
            "total_volume": sum(s.Volume() for s in solids)
        }

    @staticmethod
    def detect_interferences(workplane: cq.Workplane) -> List[Dict[str, Any]]:
        """Detect overlapping solids and calculate interference severity."""
        solids = workplane.solids().vals()
        interferences = []
        
        for i in range(len(solids)):
            for j in range(i + 1, len(solids)):
                s1 = solids[i]
                s2 = solids[j]
                
                # Check bounding box overlap first for performance
                if s1.BoundingBox().overlap(s2.BoundingBox()):
                    try:
                        # Calculate actual intersection
                        intersection = s1.intersect(s2)
                        volume = intersection.Volume()
                        
                        if volume > 1e-6:
                            # Calculate relative severity
                            v1 = s1.Volume()
                            v2 = s2.Volume()
                            rel_severity = volume / min(v1, v2) if min(v1, v2) > 0 else 0
                            
                            interferences.append({
                                "solids": (f"S{i}", f"S{j}"),
                                "type": "INTERFERENCE",
                                "volume": volume,
                                "relative_severity": rel_severity,
                                "severity": "high" if rel_severity > 0.01 else "medium",
                                "recommendation": f"Solid {i} and {j} overlap by {volume:.2f} mm³. Redesign to remove interference."
                            })
                    except Exception:
                        # Fallback if intersection fails
                        interferences.append({
                            "solids": (f"S{i}", f"S{j}"),
                            "type": "POTENTIAL_INTERFERENCE",
                            "severity": "medium",
                            "description": "Bounding boxes overlap, but exact volume check failed."
                        })
                    
        return interferences

    @staticmethod
    def analyze_clearances(workplane: cq.Workplane, min_clearance: float = 0.5) -> List[Dict[str, Any]]:
        """Find solids that are too close to each other or touching."""
        solids = workplane.solids().vals()
        clearance_issues = []
        
        for i in range(len(solids)):
            for j in range(i + 1, len(solids)):
                s1 = solids[i]
                s2 = solids[j]
                
                try:
                    # Calculate exact distance between solids
                    distance = s1.distToShape(s2)
                    
                    if distance < 1e-6:
                        # They are touching or interfering
                        # Interferences are handled by detect_interferences, 
                        # but touching might be okay depending on assembly intent.
                        pass
                    elif distance < min_clearance:
                        clearance_issues.append({
                            "solids": (f"S{i}", f"S{j}"),
                            "distance": distance,
                            "type": "LOW_CLEARANCE",
                            "severity": "high" if distance < min_clearance/2 else "medium",
                            "recommendation": f"Clearance between Solid {i} and {j} is {distance:.3f}mm. Target: {min_clearance}mm."
                        })
                except Exception:
                    pass
                    
        return clearance_issues
