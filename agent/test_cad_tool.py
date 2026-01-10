"""
Quick tests for cad_tool module.
Run with: pytest test_cad_tool.py -v
"""

import pytest
import sys
import os

# Add parent dir to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


class TestGeometryAnalyzerBasic:
    """Basic tests for GeometryAnalyzer that don't require CadQuery geometry."""
    
    def test_draft_recommendation_critical(self):
        """Test draft recommendation for negative angles."""
        from cad_tool.analyze.geometry_analyzer import GeometryAnalyzer
        
        result = GeometryAnalyzer._draft_recommendation(-1.0)
        assert "CRITICAL" in result
        assert "Negative draft" in result
    
    def test_draft_recommendation_warning(self):
        """Test draft recommendation for minimal angles."""
        from cad_tool.analyze.geometry_analyzer import GeometryAnalyzer
        
        result = GeometryAnalyzer._draft_recommendation(0.3)
        assert "WARNING" in result
    
    def test_draft_recommendation_caution(self):
        """Test draft recommendation for low angles."""
        from cad_tool.analyze.geometry_analyzer import GeometryAnalyzer
        
        result = GeometryAnalyzer._draft_recommendation(0.7)
        assert "CAUTION" in result
    
    def test_draft_recommendation_ok(self):
        """Test draft recommendation for good angles."""
        from cad_tool.analyze.geometry_analyzer import GeometryAnalyzer
        
        result = GeometryAnalyzer._draft_recommendation(2.0)
        assert result == "OK"


class TestCADToolClass:
    """Tests for CADTool main class."""
    
    def test_init(self):
        """Test CADTool initialization."""
        from cad_tool.source import CADTool
        
        tool = CADTool(job_id="test-123")
        assert tool.job_id == "test-123"
        assert tool.callback_url is None
        assert tool.current_state == {}
    
    def test_init_with_callback(self):
        """Test CADTool initialization with callback URL."""
        from cad_tool.source import CADTool
        
        tool = CADTool(job_id="test-456", callback_url="http://localhost:8000/callback")
        assert tool.job_id == "test-456"
        assert tool.callback_url == "http://localhost:8000/callback"


class TestWithCadQuery:
    """Tests that require CadQuery - marked to skip if CadQuery not available."""
    
    @pytest.fixture
    def simple_box(self):
        """Create a simple box workplane for testing."""
        try:
            import cadquery as cq
            return cq.Workplane("XY").box(10, 10, 5)
        except ImportError:
            pytest.skip("CadQuery not installed")
    
    def test_analyze_wall_thickness_box(self, simple_box):
        """Test wall thickness analysis on a simple box."""
        from cad_tool.analyze.geometry_analyzer import GeometryAnalyzer
        
        result = GeometryAnalyzer.analyze_wall_thickness(simple_box)
        
        assert "min_thickness" in result
        assert "max_thickness" in result
        assert "avg_thickness" in result
        assert "thin_regions" in result
    
    def test_analyze_draft_angles_box(self, simple_box):
        """Test draft angle analysis on a simple box."""
        from cad_tool.analyze.geometry_analyzer import GeometryAnalyzer
        
        result = GeometryAnalyzer.analyze_draft_angles(simple_box, (0, 0, 1))
        
        assert isinstance(result, list)
        # A box should have 6 faces
        assert len(result) == 6
        
        for face_result in result:
            assert "face_id" in face_result
            assert "draft_angle" in face_result
            assert "needs_draft" in face_result
            assert "recommendation" in face_result
    
    def test_detect_undercuts_box(self, simple_box):
        """Test undercut detection on a simple box (should have none)."""
        from cad_tool.analyze.geometry_analyzer import GeometryAnalyzer
        
        result = GeometryAnalyzer.detect_undercuts(simple_box, (0, 0, 1))
        
        assert isinstance(result, list)
        # A simple box shouldn't have undercuts in Z direction
        # (though bottom face may be detected)
    
    def test_analyze_overhangs_box(self, simple_box):
        """Test overhang analysis on a simple box."""
        from cad_tool.analyze.geometry_analyzer import GeometryAnalyzer
        
        result = GeometryAnalyzer.analyze_overhangs_3d_print(simple_box, max_angle=45.0)
        
        assert isinstance(result, list)
    
    def test_analyze_hole_dimensions_box(self, simple_box):
        """Test hole dimension analysis on a simple box (no holes)."""
        from cad_tool.analyze.geometry_analyzer import GeometryAnalyzer
        
        result = GeometryAnalyzer.analyze_hole_dimensions(simple_box)
        
        assert isinstance(result, list)
        # Simple box has no cylindrical features
        assert len(result) == 0
    
    @pytest.fixture
    def box_with_hole(self):
        """Create a box with a hole for testing."""
        try:
            import cadquery as cq
            return cq.Workplane("XY").box(20, 20, 10).faces(">Z").hole(5)
        except ImportError:
            pytest.skip("CadQuery not installed")
    
    def test_analyze_hole_dimensions_with_hole(self, box_with_hole):
        """Test hole dimension analysis on a box with a hole."""
        from cad_tool.analyze.geometry_analyzer import GeometryAnalyzer
        
        result = GeometryAnalyzer.analyze_hole_dimensions(box_with_hole)
        
        assert isinstance(result, list)
        # Should detect at least one cylindrical feature
        assert len(result) >= 1
        
        # Check the hole properties
        hole = next((r for r in result if r.get("is_internal")), None)
        if hole:
            assert hole["type"] == "HOLE"
            assert abs(hole["diameter"] - 5.0) < 0.1  # 5mm hole


class TestDFMAnalyzer:
    """Tests for the main DFM analyzer."""
    
    def test_analyze_dfm_imports(self):
        """Test that analyze_dfm can be imported."""
        from cad_tool.analyze.analyzer import analyze_dfm
        assert callable(analyze_dfm)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
