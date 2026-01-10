"""
Tactile Agent Module - FastAPI Application
DFM Analysis endpoint with Fireworks AI LLM and CadQuery integration.
"""

import os
import json
from typing import Optional
from contextlib import asynccontextmanager

from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse

from models import (
    AnalyzeRequest,
    AnalyzeResponse,
    Issue,
    Suggestion,
    GeometrySummary,
    Severity,
    ManufacturingProcess,
)
from fireworks_client import FireworksClient, get_cadquery_mcp_tools
from report_generator import generate_markdown_report

# Import CAD Agent for streaming analysis
try:
    from cad_agent import CADAgent, create_agent
    CAD_AGENT_AVAILABLE = True
except ImportError:
    CAD_AGENT_AVAILABLE = False
    CADAgent = None

# Optional: Import teammate's analyzer if available
try:
    from cad_tool.source import CADTool
    from cad_tool.analyze.geometry_analyzer import GeometryAnalyzer
    CAD_ANALYZER_AVAILABLE = True
except ImportError:
    CAD_ANALYZER_AVAILABLE = False
    CADTool = None
    GeometryAnalyzer = None


# Lifespan management for Fireworks client
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Initialize Fireworks client if API key available
    api_key = os.getenv("FIREWORKS_API_KEY")
    if api_key:
        app.state.fireworks_client = FireworksClient(api_key=api_key)
    else:
        app.state.fireworks_client = None
    
    yield
    
    # Shutdown: Close client
    if app.state.fireworks_client:
        await app.state.fireworks_client.close()


app = FastAPI(
    title="Tactile Agent Module",
    description="DFM Analysis API with Fireworks AI LLM and CadQuery integration",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS middleware for frontend integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "cad_analyzer_available": CAD_ANALYZER_AVAILABLE,
        "fireworks_configured": app.state.fireworks_client is not None,
    }


@app.post("/analyze", response_model=AnalyzeResponse)
async def analyze_cad(request: AnalyzeRequest):
    """
    Analyze a CAD model for DFM issues.
    
    This endpoint:
    1. Receives CAD description or file URL
    2. Calls Fireworks AI LLM with CadQuery MCP for analysis
    3. Routes to GeometryAnalyzer methods for detailed checks
    4. Returns issues/suggestions as JSON + markdown report
    """
    
    try:
        issues: list[Issue] = []
        suggestions: list[Suggestion] = []
        geometry_summary: Optional[GeometrySummary] = None
        
        # Step 1: Run CadQuery geometry analysis if analyzer available
        geometry_data = None
        if CAD_ANALYZER_AVAILABLE and request.file_url:
            geometry_data = await run_geometry_analysis(
                file_url=request.file_url,
                manufacturing_process=request.manufacturing_process,
                pull_direction=request.pull_direction,
            )
            
            # Convert geometry analysis to issues
            if geometry_data:
                issues.extend(convert_analysis_to_issues(
                    geometry_data,
                    request.manufacturing_process
                ))
        
        # Step 2: Call Fireworks AI LLM for enhanced analysis
        if app.state.fireworks_client:
            llm_response = await analyze_with_llm(
                client=app.state.fireworks_client,
                cad_description=request.cad_description or "",
                manufacturing_process=request.manufacturing_process.value,
                geometry_data=geometry_data,
            )
            
            # Parse LLM response for additional issues and suggestions
            llm_issues, llm_suggestions = parse_llm_response(llm_response)
            issues.extend(llm_issues)
            suggestions.extend(llm_suggestions)
        
        # Step 3: Generate markdown report
        markdown_report = generate_markdown_report(
            issues=issues,
            suggestions=suggestions,
            geometry_summary=geometry_summary,
            manufacturing_process=request.manufacturing_process.value,
        )
        
        return AnalyzeResponse(
            job_id=request.job_id,
            success=True,
            geometry_summary=geometry_summary,
            issues=issues,
            suggestions=suggestions,
            markdown_report=markdown_report,
        )
        
    except Exception as e:
        return AnalyzeResponse(
            job_id=request.job_id,
            success=False,
            issues=[],
            suggestions=[],
            markdown_report=f"# Analysis Failed\n\nError: {str(e)}",
            error=str(e),
        )


@app.get("/analyze-stream/{job_id}")
async def analyze_stream(job_id: str, process: str = "FDM_3D_PRINTING"):
    """
    Stream CAD analysis via Server-Sent Events.
    
    The agent will:
    1. Examine the CAD model screenshot/geometry
    2. Execute CadQuery code to analyze features
    3. Store findings to memory
    4. Provide suggestions
    
    Events are streamed in real-time as the agent thinks.
    """
    if not CAD_AGENT_AVAILABLE:
        raise HTTPException(
            status_code=503,
            detail="CAD Agent not available. Check cad_agent.py imports."
        )
    
    async def event_generator():
        # Load battery.step by default for testing
        workplane = None
        try:
            import cadquery as cq
            import os
            
            # Check for battery.step in agent dir
            default_step = os.path.join(os.path.dirname(os.path.abspath(__file__)), "battery.step")
            if os.path.exists(default_step):
                workplane = cq.importers.importStep(default_step)
        except Exception:
            pass  # Fallback to None (or handle error)

        agent = await create_agent(
            job_id=job_id,
            manufacturing_process=process,
            workplane=workplane,
        )
        
        try:
            async for event in agent.analyze_stream():
                yield event.to_sse()
        finally:
            await agent.close()
    
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        }
    )


async def run_geometry_analysis(
    file_url: str,
    manufacturing_process: ManufacturingProcess,
    pull_direction: tuple[float, float, float],
) -> dict:
    """
    Run CadQuery geometry analysis using teammate's GeometryAnalyzer.
    
    Returns dict with analysis results from various checks.
    """
    if not CAD_ANALYZER_AVAILABLE:
        return {}
    
    # TODO: Download STEP file from file_url
    # For now, this is a placeholder for integration with teammate's code
    
    # Example of how to call teammate's analyzer methods:
    # workplane = cq.importers.importStep(file_path)
    # 
    # results = {
    #     "draft_analysis": GeometryAnalyzer.analyze_draft_angles(workplane, pull_direction),
    #     "wall_thickness": GeometryAnalyzer.analyze_wall_thickness(workplane),
    #     "undercuts": GeometryAnalyzer.detect_undercuts(workplane, pull_direction),
    #     "sharp_corners": GeometryAnalyzer.detect_sharp_internal_corners(workplane),
    # }
    #
    # if manufacturing_process == ManufacturingProcess.FDM_3D_PRINTING:
    #     results["overhangs"] = GeometryAnalyzer.analyze_overhangs_3d_print(workplane)
    #
    # return results
    
    return {}


def convert_analysis_to_issues(
    geometry_data: dict,
    manufacturing_process: ManufacturingProcess,
) -> list[Issue]:
    """
    Convert GeometryAnalyzer results to Issue objects.
    
    Maps the raw analysis data to our Issue model.
    """
    issues = []
    
    # Convert draft angle issues
    draft_results = geometry_data.get("draft_analysis", [])
    for item in draft_results:
        if item.get("needs_draft"):
            issues.append(Issue(
                rule_id="IM_DRAFT_001",
                rule_name="Insufficient Draft Angle",
                severity=Severity.ERROR if item["draft_angle"] < 0 else Severity.WARNING,
                description=f"Face {item['face_id']} has draft angle of {item['draft_angle']:.1f}°",
                affected_features=[item["face_id"]],
                recommendation=item.get("recommendation", "Add draft angle of 1-2°"),
                auto_fix_available=False,
            ))
    
    # Convert wall thickness issues
    wall_data = geometry_data.get("wall_thickness", {})
    min_thickness = wall_data.get("min_thickness")
    if min_thickness is not None:
        threshold = 0.8  # mm
        if min_thickness < threshold:
            issues.append(Issue(
                rule_id="IM_WALL_001",
                rule_name="Wall Too Thin",
                severity=Severity.ERROR,
                description=f"Minimum wall thickness is {min_thickness:.2f}mm (below {threshold}mm)",
                affected_features=wall_data.get("thin_regions", []),
                recommendation=f"Increase wall thickness to at least {threshold}mm",
                auto_fix_available=False,
            ))
    
    # Convert undercut issues
    undercuts = geometry_data.get("undercuts", [])
    for item in undercuts:
        issues.append(Issue(
            rule_id="IM_UNDERCUT_001",
            rule_name="Undercut Detected",
            severity=Severity.ERROR if item["severity"] == "high" else Severity.WARNING,
            description=item.get("description", "Undercut prevents mold release"),
            affected_features=[item["face_id"]],
            recommendation="Redesign to eliminate undercut or use side actions",
            auto_fix_available=False,
        ))
    
    # Convert overhang issues (3D printing)
    if manufacturing_process == ManufacturingProcess.FDM_3D_PRINTING:
        overhangs = geometry_data.get("overhangs", [])
        for item in overhangs:
            if item.get("needs_support"):
                issues.append(Issue(
                    rule_id="FDM_OVERHANG_001",
                    rule_name="Overhang Requires Support",
                    severity=Severity.WARNING,
                    description=item.get("recommendation", f"Overhang angle exceeds 45°"),
                    affected_features=[item["face_id"]],
                    recommendation="Add support structure or redesign to reduce overhang",
                    auto_fix_available=False,
                ))
    
    # Convert sharp corner issues
    sharp_corners = geometry_data.get("sharp_corners", [])
    for item in sharp_corners:
        issues.append(Issue(
            rule_id="CNC_CORNER_001",
            rule_name="Sharp Internal Corner",
            severity=Severity.WARNING,
            description=f"Edge {item['edge_id']} has insufficient radius",
            affected_features=[item["edge_id"]],
            recommendation=item.get("recommendation", "Add fillet of 0.5mm+"),
            auto_fix_available=True,
        ))
    
    return issues


async def analyze_with_llm(
    client: FireworksClient,
    cad_description: str,
    manufacturing_process: str,
    geometry_data: Optional[dict] = None,
) -> dict:
    """
    Call Fireworks AI LLM for enhanced DFM analysis.
    """
    mcp_tools = get_cadquery_mcp_tools()
    
    response = await client.analyze_cad(
        cad_description=cad_description,
        manufacturing_process=manufacturing_process,
        geometry_data=geometry_data,
        mcp_tools=mcp_tools,
    )
    
    return response


def parse_llm_response(response: dict) -> tuple[list[Issue], list[Suggestion]]:
    """
    Parse Fireworks AI response to extract issues and suggestions.
    """
    issues = []
    suggestions = []
    
    # Extract text content from response
    output_items = response.get("output", [])
    for item in output_items:
        if item.get("type") == "message":
            content_list = item.get("content", [])
            for content in content_list:
                if content.get("type") == "text":
                    text = content.get("text", "")
                    
                    # Try to parse as JSON
                    try:
                        # Find JSON in the response
                        json_start = text.find("{")
                        json_end = text.rfind("}") + 1
                        if json_start >= 0 and json_end > json_start:
                            json_str = text[json_start:json_end]
                            data = json.loads(json_str)
                            
                            # Parse issues
                            for issue_data in data.get("issues", []):
                                issues.append(Issue(
                                    rule_id=issue_data.get("rule_id", "LLM_001"),
                                    rule_name=issue_data.get("rule_name", "LLM Detected Issue"),
                                    severity=Severity(issue_data.get("severity", "WARNING")),
                                    description=issue_data.get("description", ""),
                                    affected_features=issue_data.get("affected_features", []),
                                    recommendation=issue_data.get("recommendation", ""),
                                    auto_fix_available=issue_data.get("auto_fix_available", False),
                                ))
                            
                            # Parse suggestions
                            for sugg_data in data.get("suggestions", []):
                                suggestions.append(Suggestion(
                                    issue_id=sugg_data.get("issue_id", ""),
                                    description=sugg_data.get("description", ""),
                                    expected_improvement=sugg_data.get("expected_improvement", ""),
                                    priority=sugg_data.get("priority", 3),
                                    code_snippet=sugg_data.get("code_snippet", ""),
                                    validated=sugg_data.get("validated", False),
                                ))
                    except (json.JSONDecodeError, ValueError):
                        # If not valid JSON, skip
                        pass
    
    return issues, suggestions


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
