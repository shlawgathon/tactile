"""
STEP File Parser and Geometry Extractor

This module provides comprehensive tools for loading STEP files and extracting
detailed geometric information including bounding boxes, volumes, surface areas,
faces, edges, vertices, and topological relationships.
"""

import cadquery as cq
from typing import Dict, List, Any, Optional, Tuple
import logging
from dataclasses import dataclass, asdict
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass
class BoundingBoxInfo:
    """Bounding box information for a geometry."""
    min_x: float
    min_y: float
    min_z: float
    max_x: float
    max_y: float
    max_z: float
    length_x: float
    length_y: float
    length_z: float
    center_x: float
    center_y: float
    center_z: float
    diagonal: float


@dataclass
class FaceInfo:
    """Information about a single face."""
    face_index: int
    face_type: str  # Plane, Cylinder, Cone, Sphere, Torus, BSpline, etc.
    area: float
    center: Tuple[float, float, float]
    normal: Optional[Tuple[float, float, float]]
    edge_count: int


@dataclass
class EdgeInfo:
    """Information about a single edge."""
    edge_index: int
    edge_type: str  # Line, Circle, Ellipse, BSpline, etc.
    length: float
    center: Tuple[float, float, float]
    start_point: Tuple[float, float, float]
    end_point: Tuple[float, float, float]


@dataclass
class VertexInfo:
    """Information about a single vertex."""
    vertex_index: int
    position: Tuple[float, float, float]


@dataclass
class GeometryInfo:
    """Complete geometric information extracted from a STEP file."""
    file_path: str
    bounding_box: BoundingBoxInfo
    volume: float
    surface_area: float
    center_of_mass: Tuple[float, float, float]

    # Topological counts
    solid_count: int
    shell_count: int
    face_count: int
    edge_count: int
    vertex_count: int

    # Detailed information
    faces: List[FaceInfo]
    edges: List[EdgeInfo]
    vertices: List[VertexInfo]

    # Additional properties
    is_valid: bool
    is_closed: bool
    has_multiple_solids: bool


class StepFileParser:
    """Parser for STEP files with comprehensive geometry extraction."""

    def __init__(self):
        self.workplane: Optional[cq.Workplane] = None
        self.geometry_info: Optional[GeometryInfo] = None

    def load_step_file(self, file_path: str) -> cq.Workplane:
        """
        Load a STEP file and return the CadQuery Workplane.

        Args:
            file_path: Path to the STEP file

        Returns:
            CadQuery Workplane containing the loaded geometry

        Raises:
            FileNotFoundError: If the file doesn't exist
            ValueError: If the file cannot be parsed
        """
        logger.info(f"Loading STEP file: {file_path}")

        # Validate file exists
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"STEP file not found: {file_path}")

        if not path.suffix.lower() in ['.step', '.stp']:
            logger.warning(f"File extension {path.suffix} may not be a STEP file")

        try:
            self.workplane = cq.importers.importStep(file_path)
            logger.info(f"Successfully loaded STEP file: {file_path}")
            return self.workplane
        except Exception as e:
            logger.error(f"Failed to load STEP file {file_path}: {e}")
            raise ValueError(f"Failed to parse STEP file: {e}") from e

    def extract_bounding_box(self, solid) -> BoundingBoxInfo:
        """Extract bounding box information from a solid."""
        try:
            bbox = solid.BoundingBox()

            length_x = bbox.xmax - bbox.xmin
            length_y = bbox.ymax - bbox.ymin
            length_z = bbox.zmax - bbox.zmin

            center_x = (bbox.xmax + bbox.xmin) / 2
            center_y = (bbox.ymax + bbox.ymin) / 2
            center_z = (bbox.zmax + bbox.zmin) / 2

            diagonal = (length_x**2 + length_y**2 + length_z**2)**0.5

            return BoundingBoxInfo(
                min_x=bbox.xmin,
                min_y=bbox.ymin,
                min_z=bbox.zmin,
                max_x=bbox.xmax,
                max_y=bbox.ymax,
                max_z=bbox.zmax,
                length_x=length_x,
                length_y=length_y,
                length_z=length_z,
                center_x=center_x,
                center_y=center_y,
                center_z=center_z,
                diagonal=diagonal
            )
        except Exception as e:
            logger.error(f"Failed to extract bounding box: {e}")
            raise

    def get_face_type(self, face) -> str:
        """Determine the type of a face."""
        try:
            # Get the underlying surface type
            surface = face.Surface()
            surface_type = str(type(surface).__name__)

            # Map to common geometric types
            if 'Plane' in surface_type:
                return 'Plane'
            elif 'Cylinder' in surface_type:
                return 'Cylinder'
            elif 'Cone' in surface_type:
                return 'Cone'
            elif 'Sphere' in surface_type:
                return 'Sphere'
            elif 'Torus' in surface_type:
                return 'Torus'
            elif 'BSpline' in surface_type or 'Bezier' in surface_type:
                return 'BSpline'
            else:
                return surface_type
        except:
            return 'Unknown'

    def extract_face_info(self, face, index: int) -> FaceInfo:
        """Extract information from a single face."""
        try:
            center = face.Center()
            center_tuple = (center.x, center.y, center.z)

            # Get normal at center (for planar faces)
            try:
                normal = face.normalAt(center)
                normal_tuple = (normal.x, normal.y, normal.z)
            except:
                normal_tuple = None

            # Count edges in this face
            edge_count = len(face.Edges())

            return FaceInfo(
                face_index=index,
                face_type=self.get_face_type(face),
                area=face.Area(),
                center=center_tuple,
                normal=normal_tuple,
                edge_count=edge_count
            )
        except Exception as e:
            logger.warning(f"Failed to extract info for face {index}: {e}")
            return FaceInfo(
                face_index=index,
                face_type='Unknown',
                area=0.0,
                center=(0, 0, 0),
                normal=None,
                edge_count=0
            )

    def get_edge_type(self, edge) -> str:
        """Determine the type of an edge."""
        try:
            # Get the underlying curve type
            curve = edge.Curve()
            curve_type = str(type(curve).__name__)

            # Map to common geometric types
            if 'Line' in curve_type:
                return 'Line'
            elif 'Circle' in curve_type:
                return 'Circle'
            elif 'Ellipse' in curve_type:
                return 'Ellipse'
            elif 'BSpline' in curve_type or 'Bezier' in curve_type:
                return 'BSpline'
            else:
                return curve_type
        except:
            return 'Unknown'

    def extract_edge_info(self, edge, index: int) -> EdgeInfo:
        """Extract information from a single edge."""
        try:
            center = edge.Center()
            center_tuple = (center.x, center.y, center.z)

            # Get start and end points
            start = edge.startPoint()
            end = edge.endPoint()
            start_tuple = (start.x, start.y, start.z)
            end_tuple = (end.x, end.y, end.z)

            return EdgeInfo(
                edge_index=index,
                edge_type=self.get_edge_type(edge),
                length=edge.Length(),
                center=center_tuple,
                start_point=start_tuple,
                end_point=end_tuple
            )
        except Exception as e:
            logger.warning(f"Failed to extract info for edge {index}: {e}")
            return EdgeInfo(
                edge_index=index,
                edge_type='Unknown',
                length=0.0,
                center=(0, 0, 0),
                start_point=(0, 0, 0),
                end_point=(0, 0, 0)
            )

    def extract_vertex_info(self, vertex, index: int) -> VertexInfo:
        """Extract information from a single vertex."""
        try:
            point = vertex.toTuple()
            return VertexInfo(
                vertex_index=index,
                position=point
            )
        except Exception as e:
            logger.warning(f"Failed to extract info for vertex {index}: {e}")
            return VertexInfo(
                vertex_index=index,
                position=(0, 0, 0)
            )

    def extract_geometry_info(self, workplane: Optional[cq.Workplane] = None) -> GeometryInfo:
        """
        Extract comprehensive geometric information from the loaded STEP file.

        Args:
            workplane: Optional workplane to extract from (uses self.workplane if None)

        Returns:
            GeometryInfo object containing all extracted geometry data

        Raises:
            ValueError: If no workplane is available
        """
        wp = workplane or self.workplane
        if wp is None:
            raise ValueError("No workplane available. Load a STEP file first.")

        logger.info("Extracting geometry information...")

        try:
            # Get the solid(s)
            solids = wp.solids().vals()
            if not solids:
                raise ValueError("No solids found in the STEP file")

            # For simplicity, we'll work with the first solid
            # In a multi-solid assembly, you'd iterate through all
            solid = solids[0]
            has_multiple_solids = len(solids) > 1

            # Extract basic properties
            volume = solid.Volume()
            center_of_mass = solid.CenterOfMass()
            com_tuple = (center_of_mass.x, center_of_mass.y, center_of_mass.z)

            # Extract bounding box
            bbox_info = self.extract_bounding_box(solid)

            # Get all topological elements
            all_faces = wp.faces().vals()
            all_edges = wp.edges().vals()
            all_vertices = wp.vertices().vals()

            # Calculate surface area from all faces
            surface_area = sum(face.Area() for face in all_faces)

            # Extract detailed information for each element
            logger.info(f"Extracting info for {len(all_faces)} faces...")
            faces_info = [self.extract_face_info(face, i) for i, face in enumerate(all_faces)]

            logger.info(f"Extracting info for {len(all_edges)} edges...")
            edges_info = [self.extract_edge_info(edge, i) for i, edge in enumerate(all_edges)]

            logger.info(f"Extracting info for {len(all_vertices)} vertices...")
            vertices_info = [self.extract_vertex_info(vertex, i) for i, vertex in enumerate(all_vertices)]

            # Check validity
            is_valid = solid.isValid()
            is_closed = True  # Solids are typically closed by definition

            # Count shells (for complex geometries)
            try:
                shells = wp.shells().vals()
                shell_count = len(shells)
            except:
                shell_count = 1

            self.geometry_info = GeometryInfo(
                file_path=str(self.workplane) if hasattr(self, 'workplane') else 'unknown',
                bounding_box=bbox_info,
                volume=volume,
                surface_area=surface_area,
                center_of_mass=com_tuple,
                solid_count=len(solids),
                shell_count=shell_count,
                face_count=len(all_faces),
                edge_count=len(all_edges),
                vertex_count=len(all_vertices),
                faces=faces_info,
                edges=edges_info,
                vertices=vertices_info,
                is_valid=is_valid,
                is_closed=is_closed,
                has_multiple_solids=has_multiple_solids
            )

            logger.info("Geometry extraction complete")
            return self.geometry_info

        except Exception as e:
            logger.error(f"Failed to extract geometry info: {e}")
            raise

    def get_summary(self) -> Dict[str, Any]:
        """
        Get a summary of the extracted geometry information.

        Returns:
            Dictionary containing summary statistics
        """
        if self.geometry_info is None:
            raise ValueError("No geometry info available. Extract geometry first.")

        info = self.geometry_info

        return {
            'topology': {
                'solids': info.solid_count,
                'shells': info.shell_count,
                'faces': info.face_count,
                'edges': info.edge_count,
                'vertices': info.vertex_count,
            },
            'properties': {
                'volume': info.volume,
                'surface_area': info.surface_area,
                'center_of_mass': info.center_of_mass,
            },
            'bounding_box': {
                'min': (info.bounding_box.min_x, info.bounding_box.min_y, info.bounding_box.min_z),
                'max': (info.bounding_box.max_x, info.bounding_box.max_y, info.bounding_box.max_z),
                'dimensions': (info.bounding_box.length_x, info.bounding_box.length_y, info.bounding_box.length_z),
                'center': (info.bounding_box.center_x, info.bounding_box.center_y, info.bounding_box.center_z),
                'diagonal': info.bounding_box.diagonal,
            },
            'validation': {
                'is_valid': info.is_valid,
                'is_closed': info.is_closed,
                'has_multiple_solids': info.has_multiple_solids,
            },
            'face_types': self._count_face_types(),
            'edge_types': self._count_edge_types(),
        }

    def _count_face_types(self) -> Dict[str, int]:
        """Count faces by type."""
        if self.geometry_info is None:
            return {}

        type_counts = {}
        for face in self.geometry_info.faces:
            type_counts[face.face_type] = type_counts.get(face.face_type, 0) + 1
        return type_counts

    def _count_edge_types(self) -> Dict[str, int]:
        """Count edges by type."""
        if self.geometry_info is None:
            return {}

        type_counts = {}
        for edge in self.geometry_info.edges:
            type_counts[edge.edge_type] = type_counts.get(edge.edge_type, 0) + 1
        return type_counts

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert the complete geometry information to a dictionary.

        Returns:
            Dictionary representation of all geometry data
        """
        if self.geometry_info is None:
            raise ValueError("No geometry info available. Extract geometry first.")

        return asdict(self.geometry_info)


# Convenience functions
def load_and_extract(file_path: str) -> Tuple[cq.Workplane, GeometryInfo]:
    """
    Load a STEP file and extract all geometry information in one call.

    Args:
        file_path: Path to the STEP file

    Returns:
        Tuple of (CadQuery Workplane, GeometryInfo)
    """
    parser = StepFileParser()
    workplane = parser.load_step_file(file_path)
    geometry_info = parser.extract_geometry_info()
    return workplane, geometry_info


def quick_summary(file_path: str) -> Dict[str, Any]:
    """
    Get a quick summary of a STEP file's geometry.

    Args:
        file_path: Path to the STEP file

    Returns:
        Dictionary containing summary statistics
    """
    parser = StepFileParser()
    parser.load_step_file(file_path)
    parser.extract_geometry_info()
    return parser.get_summary()


if __name__ == "__main__":
    # Example usage
    import sys

    if len(sys.argv) > 1:
        file_path = sys.argv[1]
        print(f"Analyzing STEP file: {file_path}")

        try:
            summary = quick_summary(file_path)

            print("\n=== Geometry Summary ===")
            print(f"Topology: {summary['topology']}")
            print(f"Volume: {summary['properties']['volume']:.2f}")
            print(f"Surface Area: {summary['properties']['surface_area']:.2f}")
            print(f"Bounding Box Dimensions: {summary['bounding_box']['dimensions']}")
            print(f"Face Types: {summary['face_types']}")
            print(f"Edge Types: {summary['edge_types']}")
            print(f"Valid Geometry: {summary['validation']['is_valid']}")

        except Exception as e:
            print(f"Error: {e}")
            sys.exit(1)
    else:
        print("Usage: python parse.py <path_to_step_file>")
