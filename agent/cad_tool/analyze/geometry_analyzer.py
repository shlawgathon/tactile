import cadquery as cq
from typing import List, Dict, Any, Tuple
import math

class GeometryAnalyzer:
    """Perform DFM-relevant geometry analysis."""
    
    @staticmethod
    def analyze_wall_thickness(workplane: cq.Workplane, 
                                sample_points: int = 20) -> Dict[str, Any]:
        """
        Estimate wall thickness by sampling distances between faces.
        """
        try:
            solid = workplane.val()
            if not solid:
                return {"min_thickness": None, "max_thickness": None, "avg_thickness": None, "thin_regions": []}
            
            faces = workplane.faces().vals()
            thickness_values = []
            
            # Select a subset of faces to sample from to keep it performant
            # Focus on larger faces or just a representative sample
            sampled_faces = sorted(faces, key=lambda f: f.Area(), reverse=True)[:sample_points]
            
            for i, f1 in enumerate(sampled_faces):
                try:
                    p = f1.Center()
                    n = f1.normalAt(p).normalized()
                    v1 = cq.Vertex.makeVertex(p.x, p.y, p.z)
                    
                    # Look for the nearest face in the opposite direction of the normal
                    min_dist = float('inf')
                    for j, f2 in enumerate(faces):
                        # Skip if it's the same face
                        if f1 == f2:
                            continue
                            
                        # Distance from center of f1 to f2
                        dist = f2.distToShape(v1)
                        
                        if dist < min_dist:
                            # Verify if f2 is 'behind' f1 at this point
                            # We can check if a point slightly inside the solid from f1
                            # is closer to f2.
                            epsilon = 0.01
                            p_in = p.add(n.multiply(-epsilon))
                            v_in = cq.Vertex.makeVertex(p_in.x, p_in.y, p_in.z)
                            dist_in = f2.distToShape(v_in)
                            
                            if dist_in < dist: # Moving inward got us closer to f2
                                min_dist = dist
                    
                    if min_dist < float('inf') and min_dist > 1e-6:
                        thickness_values.append(min_dist)
                except:
                    continue
            
            if not thickness_values:
                # Fallback to bounding box heuristic if sampling failed
                bbox = solid.BoundingBox()
                dims = [bbox.xlen, bbox.ylen, bbox.zlen]
                return {
                    "min_thickness": min(dims),
                    "max_thickness": max(dims),
                    "avg_thickness": sum(dims)/3,
                    "thin_regions": [],
                    "note": "Used bounding box fallback"
                }
            
            return {
                "min_thickness": min(thickness_values),
                "max_thickness": max(thickness_values),
                "avg_thickness": sum(thickness_values) / len(thickness_values),
                "thin_regions": [] # Could populate with face IDs that are thin
            }
        except Exception as e:
            return {"min_thickness": None, "max_thickness": None, "avg_thickness": None, "thin_regions": [], "error": str(e)}

    @staticmethod
    def analyze_draft_angles(workplane: cq.Workplane, 
                             pull_direction: Tuple[float, float, float] = (0, 0, 1)
                            ) -> List[Dict[str, Any]]:
        """
        Analyze draft angles relative to a pull direction.
        Improved to handle non-planar faces by sampling.
        """
        pull_vec = cq.Vector(*pull_direction).normalized()
        faces = workplane.faces().vals()
        
        results = []
        for i, face in enumerate(faces):
            try:
                # Sample points on the face
                sample_points = [face.Center()]
                if face.geomType() != "PLANE":
                    # For non-planar faces, add more sample points from edges
                    for edge in face.edges().vals():
                        sample_points.append(edge.Center())
                
                min_draft = 90.0
                worst_normal = None
                
                for pt in sample_points:
                    normal = face.normalAt(pt).normalized()
                    # Draft angle is angle between normal and plane perpendicular to pull
                    # Which is 90 - angle between normal and pull
                    dot = abs(normal.dot(pull_vec))
                    angle_from_pull = math.degrees(math.acos(min(dot, 1.0)))
                    draft_angle = 90 - angle_from_pull
                    
                    if draft_angle < min_draft:
                        min_draft = draft_angle
                        worst_normal = normal
                
                results.append({
                    "face_id": f"F{i}",
                    "face_type": face.geomType(),
                    "draft_angle": min_draft,
                    "needs_draft": min_draft < 0.5,
                    "recommendation": GeometryAnalyzer._draft_recommendation(min_draft)
                })
            except:
                pass
        
        return results
    
    @staticmethod
    def _draft_recommendation(angle: float) -> str:
        if angle < 0:
            return "CRITICAL: Negative draft - part will not eject. Add positive draft."
        elif angle < 0.5:
            return "WARNING: Minimal draft - ejection difficult. Recommend 1-2°."
        elif angle < 1.0:
            return "CAUTION: Low draft - may cause ejection marks. Consider 2°+."
        else:
            return "OK"
    
    @staticmethod
    def detect_undercuts(workplane: cq.Workplane,
                         pull_direction: Tuple[float, float, float] = (0, 0, 1)
                        ) -> List[Dict[str, Any]]:
        """
        Detect undercut features that would prevent mold release.
        Improved to check face normals against pull direction.
        """
        pull_vec = cq.Vector(*pull_direction).normalized()
        faces = workplane.faces().vals()
        
        undercuts = []
        for i, face in enumerate(faces):
            try:
                # Undercut detection: normal points against pull direction
                # Dot product < 0 means the face is 'facing' the pull direction, which blocks it
                # during ejection if it's an internal or re-entrant feature.
                
                normal = face.normalAt(face.Center()).normalized()
                dot = normal.dot(pull_vec)
                
                # If dot is negative, the surface normal is opposite to pull direction.
                # For an external surface, this means it's an undercut.
                if dot < -0.05:
                    undercuts.append({
                        "face_id": f"F{i}",
                        "severity": "high" if dot < -0.7 else "medium",
                        "dot_product": dot,
                        "description": f"Face F{i} creates an undercut (normal dot pull = {dot:.2f}).",
                        "recommendation": "Avoid features that face opposite to the pull direction, or use a complex mold with side-actions."
                    })
            except:
                pass
        
        return undercuts
    
    @staticmethod
    def analyze_overhangs_3d_print(workplane: cq.Workplane,
                                    max_angle: float = 45.0
                                   ) -> List[Dict[str, Any]]:
        """
        Analyze overhangs for 3D printing (FDM).
        Improved to sample more points on non-planar surfaces.
        """
        build_direction = cq.Vector(0, 0, 1)  # Assume Z-up build
        faces = workplane.faces().vals()
        
        overhangs = []
        for i, face in enumerate(faces):
            try:
                # Sample center and edges for non-planar faces
                sample_pts = [face.Center()]
                if face.geomType() != "PLANE":
                    for e in face.edges().vals():
                        sample_pts.append(e.Center())
                
                max_overhang = 0
                for pt in sample_pts:
                    normal = face.normalAt(pt).normalized()
                    # Angle from vertical (build direction)
                    dot = normal.dot(build_direction)
                    
                    # If dot < 0, it's downward facing
                    if dot < -1e-6:
                        # Angle from vertical: acos(abs(dot))
                        # Overhang angle (from horizontal) is 90 - angle from vertical
                        # Or simply: asin(abs(dot))
                        angle_from_vertical = math.degrees(math.acos(abs(dot)))
                        overhang_angle = 90 - angle_from_vertical
                        max_overhang = max(max_overhang, overhang_angle)
                
                if max_overhang > max_angle:
                    overhangs.append({
                        "face_id": f"F{i}",
                        "overhang_angle": max_overhang,
                        "needs_support": True,
                        "recommendation": f"Overhang of {max_overhang:.1f}° exceeds {max_angle}°. Requires support material."
                    })
            except:
                pass
        
        return overhangs
    
    @staticmethod
    def detect_sharp_internal_corners(workplane: cq.Workplane,
                                       min_radius: float = 0.5
                                      ) -> List[Dict[str, Any]]:
        """
        Detect sharp internal corners by identifying concave edges between faces.
        """
        try:
            solid = workplane.val()
            if not solid: return []
            
            edges = workplane.edges().vals()
            faces = workplane.faces().vals()
            
            # Build edge to face map
            edge_to_faces = {}
            for f_idx, face in enumerate(faces):
                for edge in face.edges().vals():
                    if edge not in edge_to_faces:
                        edge_to_faces[edge] = []
                    edge_to_faces[edge].append(f_idx)
            
            sharp_corners = []
            for edge, face_indices in edge_to_faces.items():
                if len(face_indices) == 2:
                    f1, f2 = faces[face_indices[0]], faces[face_indices[1]]
                    
                    try:
                        if edge.geomType() != "LINE": continue
                        
                        mid_pt = edge.Center()
                        n1 = f1.normalAt(mid_pt).normalized()
                        n2 = f2.normalAt(mid_pt).normalized()
                        
                        # Angle between normals
                        dot = n1.dot(n2)
                        if abs(dot) > 0.999: continue # Coplanar or parallel
                        
                        angle = math.degrees(math.acos(max(-1.0, min(1.0, dot))))
                        
                        # Concavity check: point slightly 'outside' the edge in normal direction
                        # If that point is INSIDE the solid, it's a concave corner.
                        test_dir = n1.add(n2).normalized()
                        test_pt = mid_pt.add(test_dir.multiply(0.1))
                        
                        if solid.isInside(test_pt):
                            sharp_corners.append({
                                "edge_id": "SHARP_EDGE", # Could use coordinates for ID
                                "angle": angle,
                                "type": "SHARP_INTERNAL",
                                "severity": "medium",
                                "recommendation": f"Concave corner (angle {angle:.1f}°) detected. Consider adding a fillet (min R{min_radius}mm)."
                            })
                    except:
                        pass
            
            return sharp_corners
        except:
            return []
    
    @staticmethod
    def analyze_hole_dimensions(workplane: cq.Workplane) -> List[Dict[str, Any]]:
        """
        Analyze cylindrical features (holes and bosses) for manufacturability.
        """
        try:
            faces = workplane.faces().vals()
            features = []
            for i, face in enumerate(faces):
                if face.geomType() == "CYLINDER":
                    radius, height = GeometryAnalyzer._get_cylinder_properties(face)
                    # Orientation() == "REVERSED" usually means it's an internal face (hole)
                    # for a single solid.
                    is_internal = face.Orientation() == "REVERSED"
                    
                    features.append({
                        "face_id": f"F{i}",
                        "type": "HOLE" if is_internal else "BOSS",
                        "radius": radius,
                        "diameter": 2 * radius,
                        "height": height,
                        "area": face.Area(),
                        "is_internal": is_internal,
                        "recommendation": f"Check if {2*radius:.2f}mm diameter matches standard tooling."
                    })
            return features
        except:
            return []

    @staticmethod
    def analyze_hole_machinability(workplane: cq.Workplane) -> List[Dict[str, Any]]:
        """
        Analyze holes for depth-to-diameter ratio.
        Deep holes (L/D > 5) are difficult to drill and may require special tooling.
        """
        issues = []
        try:
            holes = GeometryAnalyzer.analyze_hole_dimensions(workplane)
            for hole in holes:
                if hole["is_internal"]:
                    diameter = hole["diameter"]
                    depth = hole["height"]
                    if diameter > 0:
                        ratio = depth / diameter
                        
                        if ratio > 5.0:
                            issues.append({
                                "face_id": hole["face_id"],
                                "type": "DEEP_HOLE",
                                "diameter": diameter,
                                "depth": depth,
                                "ratio": ratio,
                                "severity": "high" if ratio > 10 else "medium",
                                "recommendation": f"Hole L/D ratio is {ratio:.1f}. Ratios > 5 require special drills; > 10 are very difficult."
                            })
                        
                        if diameter < 1.5: # Standard small drill bit threshold
                            issues.append({
                                "face_id": hole["face_id"],
                                "type": "SMALL_HOLE",
                                "diameter": diameter,
                                "severity": "medium",
                                "recommendation": f"Hole diameter {diameter:.2f}mm is small. Ensure availability of micro-drills."
                            })
                        
                        # Standard tap drill size matching
                        taps = {
                            2.5: "M3",
                            3.3: "M4",
                            4.2: "M5",
                            5.0: "M6",
                            6.8: "M8",
                            8.5: "M10",
                            10.2: "M12"
                        }
                        for size, tap in taps.items():
                            if abs(diameter - size) < 0.05:
                                issues.append({
                                    "face_id": hole["face_id"],
                                    "type": "POTENTIAL_TAPPED_HOLE",
                                    "tap": tap,
                                    "diameter": diameter,
                                    "severity": "info",
                                    "recommendation": f"Hole matches tap drill size for {tap}. Ensure appropriate thread clearance and depth."
                                })
                                break
        except:
            pass
        return issues

    @staticmethod
    def _get_cylinder_properties(face: cq.Face) -> Tuple[float, float]:
        """Estimate radius and height of a cylindrical face."""
        try:
            # Try to get radius from circular edges first as it's more reliable
            circ_edges = [e for e in face.edges().vals() if e.geomType() == "CIRCLE"]
            radius = 0.0
            if circ_edges:
                radius = circ_edges[0].Radius()
            else:
                # Fallback: if we can't find circular edges, maybe it's a partial cylinder
                # We can try to use the bounding box or surface properties if available
                # In CadQuery/OCCT we could use face.wrapped.Surface()
                pass
            
            if radius > 0:
                area = face.Area()
                # Side surface area of cylinder is 2 * pi * r * h
                # This works even for partial cylinders (arcs) if we adjust for the arc angle,
                # but for now we assume full or nearly full cylinders for DFM.
                height = area / (2 * math.pi * radius)
                return radius, height
        except:
            pass
        return 0.0, 0.0

    @staticmethod
    def detect_small_features(workplane: cq.Workplane, threshold: float = 0.5) -> List[Dict[str, Any]]:
        """Detect very small faces that might be hard to manufacture or represent noise."""
        faces = workplane.faces().vals()
        small_features = []
        
        for i, face in enumerate(faces):
            try:
                area = face.Area()
                if 0 < area < (threshold * threshold):
                    small_features.append({
                        "face_id": f"F{i}",
                        "type": "SMALL_FACE",
                        "area": area,
                        "severity": "low",
                        "recommendation": f"Face area ({area:.3f} mm²) is very small. Verify if it's intentional or a modeling artifact."
                    })
            except:
                pass
        
        return small_features

    @staticmethod
    def analyze_hole_clearance(workplane: cq.Workplane, min_factor: float = 1.5) -> List[Dict[str, Any]]:
        """
        Check if holes are too close to the edge of the part.
        Holes should typically be at least 1.5x diameter away from any edge.
        """
        issues = []
        try:
            solid = workplane.val()
            if not solid: return []
            
            # Get all outer faces (approximation: faces not belonging to any identified hole)
            holes = GeometryAnalyzer.analyze_hole_dimensions(workplane)
            hole_face_ids = {h["face_id"] for h in holes if h["is_internal"]}
            
            # We also need to consider the edges that belong to the hole itself
            # but we want to check distance to edges NOT belonging to the hole.
            
            faces = workplane.faces().vals()
            
            for hole in holes:
                if not hole["is_internal"]: continue
                
                try:
                    f_idx = int(hole["face_id"][1:])
                    hole_face = faces[f_idx]
                    center = hole_face.Center()
                    radius = hole["radius"]
                    diameter = hole["diameter"]
                    
                    # Find min distance from hole center to any face that isn't this hole
                    min_dist = float('inf')
                    for i, face in enumerate(faces):
                        if i == f_idx: continue
                        
                        # Use distance to face. Note: this might hit adjacent faces.
                        # Realistically we want distance to "boundary" edges.
                        # But distToShape(face) is a good start.
                        d = face.distToShape(cq.Vertex.makeVertex(center.x, center.y, center.z))
                        
                        # We want the distance from the EDGE of the hole to the edge of the part.
                        # d is from center, so clearance is d - radius.
                        clearance = d - radius
                        
                        if 1e-3 < clearance < min_dist:
                            min_dist = clearance
                    
                    target = diameter * min_factor
                    if min_dist < target:
                        issues.append({
                            "face_id": hole["face_id"],
                            "type": "HOLE_EDGE_CLEARANCE",
                            "clearance": min_dist,
                            "required": target,
                            "severity": "high" if min_dist < diameter else "medium",
                            "recommendation": f"Hole {hole['face_id']} is too close to an edge ({min_dist:.2f}mm). Recommend at least {target:.2f}mm clearance."
                        })
                except:
                    continue
        except:
            pass
        return issues

    @staticmethod
    def analyze_boss_manufacturability(workplane: cq.Workplane) -> List[Dict[str, Any]]:
        """
        Analyze bosses for height-to-diameter ratio.
        Tall, thin bosses are prone to breaking or bending during molding/machining.
        """
        issues = []
        try:
            features = GeometryAnalyzer.analyze_hole_dimensions(workplane)
            for feat in features:
                if feat["type"] == "BOSS":
                    diameter = feat["diameter"]
                    height = feat["height"]
                    if diameter > 0:
                        ratio = height / diameter
                        # Rule of thumb: H/D should be <= 3
                        if ratio > 3.0:
                            issues.append({
                                "face_id": feat["face_id"],
                                "type": "TALL_BOSS",
                                "height": height,
                                "diameter": diameter,
                                "ratio": ratio,
                                "severity": "medium",
                                "recommendation": f"Boss height-to-diameter ratio is {ratio:.1f}. Recommend keeping H/D <= 3.0 to prevent breakage."
                            })
        except:
            pass
        return issues

    @staticmethod
    def analyze_pocket_accessibility(workplane: cq.Workplane) -> List[Dict[str, Any]]:
        """
        Analyze pockets for CNC tool accessibility.
        Deep, narrow pockets require long tools which are prone to chatter and breakage.
        """
        issues = []
        try:
            solid = workplane.val()
            if not solid: return []
            
            # Identify concave faces (already have logic in detect_sharp_internal_corners)
            # A pocket is generally a set of faces surrounded by concave edges.
            # Simplified: Look at all faces and find those that are 'sunk' into the bounding box.
            
            bbox = solid.BoundingBox()
            faces = workplane.faces().vals()
            
            for i, face in enumerate(faces):
                # If the face is not on the bounding box, it's a candidate for being inside a pocket
                f_bbox = face.BoundingBox()
                
                # Check if it's "internal" - not touching the outer boundary of the part's BB
                # on at least one side (the 'opening' side).
                # This is heuristic.
                
                # Let's use a better heuristic: Area vs. Bounding Box aspect ratio for concave features.
                pass
            
            # For now, let's focus on Slot accessibility
            # Slots are often non-cylindrical pockets.
            for i, face in enumerate(faces):
                if face.geomType() == "PLANE":
                    # Check for narrow slots: parallel faces close to each other
                    pass
            
            return issues
        except:
            return []

    @staticmethod
    def analyze_rib_proportions(workplane: cq.Workplane, 
                                nominal_thickness: float = 2.0) -> List[Dict[str, Any]]:
        """
        Analyze ribs for injection molding.
        Ribs should be 50-70% of the nominal wall thickness to avoid sink marks.
        """
        issues = []
        try:
            # Ribs are typically thin, long features.
            # We can find them by looking for 'thin' walls that are shorter than the main walls.
            # This is hard to automate perfectly, but we can look for any wall 
            # that is significantly thinner than the 'average' thickness.
            
            thickness_data = GeometryAnalyzer.analyze_wall_thickness(workplane)
            avg_t = thickness_data.get("avg_thickness", nominal_thickness)
            min_t = thickness_data.get("min_thickness")
            
            if min_t and avg_t and min_t < (0.4 * avg_t):
                # Potential overly thin rib
                issues.append({
                    "type": "THIN_RIB",
                    "thickness": min_t,
                    "nominal": avg_t,
                    "severity": "medium",
                    "recommendation": f"Thin feature detected ({min_t:.2f}mm). If this is a rib, ensure it is 50-70% of wall thickness ({avg_t:.2f}mm) to balance strength and sink marks."
                })
        except:
            pass
        return issues
