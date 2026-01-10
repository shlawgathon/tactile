"""
Tactile Agent Module - FastAPI Application
DFM Analysis endpoint with Fireworks AI LLM and CadQuery integration.
"""

import os
import json
import tempfile
from typing import Optional
from contextlib import asynccontextmanager
from pydantic import BaseModel

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


# Request models for agent endpoints
class StartJobRequest(BaseModel):
    """Request to start a new analysis job."""
    jobId: str
    fileUrl: str
    manufacturingProcess: str = "FDM_3D_PRINTING"
    material: Optional[str] = None
    callbackUrl: Optional[str] = None
    resumeFromCheckpoint: Optional[dict] = None


class ResumeCheckpoint(BaseModel):
    """Checkpoint data for resuming a job."""
    stage: str
    state: Optional[dict] = None
    intermediateResults: Optional[dict] = None

# Import CAD Agent for streaming analysis
try:
    from cad_agent import CADAgent, create_agent
    CAD_AGENT_AVAILABLE = True
except ImportError:
    CAD_AGENT_AVAILABLE = False
    CADAgent = None

# Import backend client for posting events
try:
    from tools.backend_client import BackendClient, get_backend_client
    BACKEND_CLIENT_AVAILABLE = True
except ImportError:
    BACKEND_CLIENT_AVAILABLE = False
    BackendClient = None

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


# ==================== Backend Integration Endpoints ====================

@app.post("/agent/jobs/start")
async def start_job(request: StartJobRequest, background_tasks: BackgroundTasks):
    """
    Start a new analysis job. Called by the Java backend.
    
    This endpoint:
    1. Downloads the STEP file from the backend
    2. Loads it into CadQuery
    3. Starts the analysis agent in a background task
    4. Posts events back to the backend via HTTP (which broadcasts via WebSocket)
    """
    import logging
    logger = logging.getLogger(__name__)
    
    logger.info(f"[AGENT] Received start job request: jobId={request.jobId}")
    logger.info(f"[AGENT] FileUrl: {request.fileUrl}")
    logger.info(f"[AGENT] Process: {request.manufacturingProcess}, Material: {request.material}")
    
    if not CAD_AGENT_AVAILABLE:
        logger.error("[AGENT] CAD Agent not available!")
        raise HTTPException(
            status_code=503,
            detail="CAD Agent not available"
        )
    
    # Start the analysis as a background task
    logger.info(f"[AGENT] Starting background analysis task for job: {request.jobId}")
    background_tasks.add_task(
        run_analysis_job,
        job_id=request.jobId,
        file_url=request.fileUrl,
        manufacturing_process=request.manufacturingProcess,
        callback_url=request.callbackUrl,
    )
    
    return {"status": "accepted", "jobId": request.jobId}


@app.delete("/agent/jobs/{job_id}/cancel")
async def cancel_job(job_id: str):
    """Cancel a running job."""
    # TODO: Implement job cancellation tracking
    return {"status": "cancelled", "jobId": job_id}


async def run_analysis_job(
    job_id: str,
    file_url: str,
    manufacturing_process: str,
    callback_url: Optional[str] = None,
):
    """
    Background task to run the full analysis pipeline.
    Downloads STEP file, runs agent, posts events to backend.
    """
    import logging
    logger = logging.getLogger(__name__)
    
    backend_client = None
    agent = None
    workplane = None
    temp_file_path = None
    
    try:
        # Initialize backend client
        if BACKEND_CLIENT_AVAILABLE:
            backend_client = await get_backend_client()
        
        # Post initial event
        if backend_client:
            await backend_client.post_event(
                job_id=job_id,
                event_type="thinking",
                title="Starting Analysis",
                content=f"Initializing {manufacturing_process} analysis pipeline..."
            )
            await backend_client.update_job_status(job_id, "PARSE", 0)
        
        # Download the STEP file
        if file_url:
            logger.info(f"Downloading STEP file from: {file_url}")
            
            if backend_client:
                await backend_client.post_event(
                    job_id=job_id,
                    event_type="thinking",
                    title="Downloading CAD File",
                    content="Retrieving STEP file from storage..."
                )
            
            # Create temp file
            temp_file_path = os.path.join(tempfile.gettempdir(), f"job_{job_id}.step")
            
            download_result = await backend_client.download_file(file_url, temp_file_path)
            
            if download_result.get("success"):
                # Load into CadQuery
                try:
                    import cadquery as cq
                    workplane = cq.importers.importStep(temp_file_path)
                    logger.info(f"Successfully loaded STEP file for job {job_id}")
                    
                    if backend_client:
                        await backend_client.post_event(
                            job_id=job_id,
                            event_type="thinking",
                            title="CAD File Loaded",
                            content="STEP file successfully parsed and loaded into CadQuery."
                        )
                except Exception as e:
                    logger.error(f"Failed to parse STEP file: {e}")
                    if backend_client:
                        await backend_client.post_event(
                            job_id=job_id,
                            event_type="error",
                            title="Parse Error",
                            content=f"Failed to parse STEP file: {str(e)}"
                        )
            else:
                logger.warning(f"Failed to download STEP file: {download_result}")
        
        # If no workplane loaded, try default test file
        if workplane is None:
            default_step = os.path.join(os.path.dirname(os.path.abspath(__file__)), "battery.step")
            if os.path.exists(default_step):
                try:
                    import cadquery as cq
                    workplane = cq.importers.importStep(default_step)
                    logger.info("Using default battery.step for testing")
                except Exception as e:
                    logger.warning(f"Failed to load default STEP: {e}")
        
        # Update status to analyzing
        if backend_client:
            await backend_client.update_job_status(job_id, "ANALYZE", 1)
        
        # Create and run agent
        agent = await create_agent(
            job_id=job_id,
            manufacturing_process=manufacturing_process,
            workplane=workplane,
        )
        
        # Replace agent's memory client with backend client
        if backend_client:
            agent.backend_client = backend_client
        
        # Collect results
        issues = []
        suggestions = []
        
        # Run analysis and stream events to backend
        async for event in agent.analyze_stream():
            # Post each event to backend for WebSocket broadcast
            if backend_client:
                await backend_client.post_event(
                    job_id=job_id,
                    event_type=event.type.value,
                    title=event.type.value.replace("_", " ").title(),
                    content=event.content,
                    metadata=event.data
                )
            
            # Collect suggestions for final result
            if event.type.value == "suggestion" and event.data:
                suggestions.append(event.data)
        
        # Update status to suggesting
        if backend_client:
            await backend_client.update_job_status(job_id, "SUGGEST", 2)
        
        # Get geometry summary if workplane available
        geometry_summary = None
        if workplane:
            try:
                solid = workplane.val()
                bb = solid.BoundingBox()
                geometry_summary = {
                    "boundingBox": {
                        "minX": bb.xmin, "maxX": bb.xmax,
                        "minY": bb.ymin, "maxY": bb.ymax,
                        "minZ": bb.zmin, "maxZ": bb.zmax,
                    },
                    "volume": solid.Volume() if hasattr(solid, "Volume") else None,
                    "surfaceArea": solid.Area() if hasattr(solid, "Area") else None,
                    "faceCount": len(workplane.faces().vals()),
                    "edgeCount": len(workplane.edges().vals()),
                }
            except Exception as e:
                logger.warning(f"Failed to extract geometry summary: {e}")
        
        # Generate markdown report
        markdown_report = generate_markdown_report(
            issues=[],  # Convert from collected data if available
            suggestions=suggestions,
            geometry_summary=None,  # Would need model conversion
            manufacturing_process=manufacturing_process,
        )
        
        # Complete the job with markdown report
        if backend_client:
            await backend_client.update_job_status(job_id, "VALIDATE", 3)
            await backend_client.complete_job(
                job_id=job_id,
                issues=issues,
                suggestions=suggestions,
                geometry_summary=geometry_summary,
                markdown_report=markdown_report
            )
            
            await backend_client.post_event(
                job_id=job_id,
                event_type="complete",
                title="Analysis Complete",
                content=f"Completed analysis with {len(suggestions)} suggestions."
            )
        
        logger.info(f"Job {job_id} completed successfully")
        
    except Exception as e:
        logger.error(f"Job {job_id} failed: {e}")
        import traceback
        traceback.print_exc()
        
        if backend_client:
            await backend_client.post_event(
                job_id=job_id,
                event_type="error",
                title="Analysis Failed",
                content=f"Error: {str(e)}"
            )
            await backend_client.fail_job(job_id, str(e))
    
    finally:
        # Cleanup
        if agent:
            await agent.close()
        
        # Remove temp file
        if temp_file_path and os.path.exists(temp_file_path):
            try:
                os.remove(temp_file_path)
            except Exception:
                pass


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
