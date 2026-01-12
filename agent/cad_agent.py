"""
CAD Agent - LLM-powered agentic loop for CAD analysis.
Uses tool calling to execute CadQuery code, store memories, and generate suggestions.
"""

import json
import logging
from dataclasses import dataclass
from enum import Enum
from typing import Any, AsyncGenerator, Dict, List, Optional

from fireworks_client import FireworksClient
from tools.cadquery_executor import execute_cadquery_code
from tools.screenshot_renderer import capture_screenshot, capture_multiple_views, AVAILABLE_VIEWS

# Import backend client for posting events to Java backend
try:
    from tools.backend_client import BackendClient, get_backend_client
    BACKEND_CLIENT_AVAILABLE = True
except ImportError:
    BACKEND_CLIENT_AVAILABLE = False
    BackendClient = None

# Import parts search tool with x402 payment integration
try:
    from tools.parts_search import (
        PartsSearchTool,
        PARTS_SEARCH_TOOL_DEFINITION,
        DOWNLOAD_CAD_TOOL_DEFINITION,
        handle_parts_search_tool_call,
    )
    PARTS_SEARCH_AVAILABLE = True
except ImportError:
    PARTS_SEARCH_AVAILABLE = False
    PartsSearchTool = None
    PARTS_SEARCH_TOOL_DEFINITION = None
    DOWNLOAD_CAD_TOOL_DEFINITION = None
    handle_parts_search_tool_call = None


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class EventType(str, Enum):
    """Types of events streamed to the frontend."""
    THINKING = "thinking"
    TOOL_CALL = "tool_call"
    TOOL_RESULT = "tool_result"
    SUGGESTION = "suggestion"
    MEMORY = "memory"
    ERROR = "error"
    COMPLETE = "complete"
    SCREENSHOT = "screenshot"


@dataclass
class AgentEvent:
    """An event to stream to the frontend."""
    type: EventType
    content: str
    data: Optional[Dict[str, Any]] = None
    
    def to_sse(self) -> str:
        """Format as Server-Sent Event."""
        payload = {
            "type": self.type.value,
            "content": self.content,
        }
        if self.data:
            payload["data"] = self.data
        return f"data: {json.dumps(payload)}\n\n"


@dataclass
class Message:
    """A message in the conversation history."""
    role: str  # "system", "user", "assistant", "tool"
    content: str
    tool_calls: Optional[List[Dict[str, Any]]] = None
    tool_call_id: Optional[str] = None
    name: Optional[str] = None


# Tool definitions for LLM
TOOL_DEFINITIONS = [
    {
        "type": "function",
        "function": {
            "name": "execute_cadquery_code",
            "description": "Execute CadQuery Python code to analyze the CAD model geometry. IMPORTANT: Only use standard CadQuery (cq) module - do NOT import cq_warehouse, cq_gears, or other external packages. The 'workplane' variable is already loaded with the model.",
            "parameters": {
                "type": "object",
                "properties": {
                    "code": {
                        "type": "string",
                        "description": "Python code using CadQuery. MUST set 'result' variable. Available: 'cq' module and 'workplane' (loaded model). Example: bb = workplane.val().BoundingBox(); result = bb.xmax - bb.xmin"
                    },
                    "description": {
                        "type": "string",
                        "description": "Brief description of what this code analyzes"
                    }
                },
                "required": ["code", "description"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "store_memory",
            "description": "IMPORTANT: Store observations and findings about the CAD model. Call this FREQUENTLY - after EVERY measurement, after finding ANY issue, after analyzing ANY feature. This creates a thorough audit trail of your analysis.",
            "parameters": {
                "type": "object",
                "properties": {
                    "key": {
                        "type": "string",
                        "description": "Short identifier for this memory (e.g., 'bounding_box', 'face_count', 'overhang_issue_1', 'wall_thickness_min')"
                    },
                    "value": {
                        "type": "string",
                        "description": "The observation, measurement, or finding to store. Be detailed and include values."
                    },
                    "category": {
                        "type": "string",
                        "enum": ["observation", "measurement", "issue", "geometry"],
                        "description": "Category: 'measurement' for dimensions/counts, 'issue' for problems found, 'observation' for general notes, 'geometry' for shape analysis"
                    }
                },
                "required": ["key", "value", "category"]
            }
        }
    },
    {
        "type": "function", 
        "function": {
            "name": "read_memory",
            "description": "Read previously stored memories about the CAD model. Use this to recall earlier findings or observations.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Optional search term to filter memories"
                    },
                    "category": {
                        "type": "string",
                        "enum": ["observation", "measurement", "issue", "geometry"],
                        "description": "Optional category filter"
                    }
                },
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "capture_screenshot",
            "description": "Capture a SVG screenshot of the CAD model from a specific view angle. Returns the SVG text content which visualizes the wireframe. Use this to 'see' the geometry.",
            "parameters": {
                "type": "object",
                "properties": {
                    "view": {
                        "type": "string",
                        "enum": ["iso", "iso_back", "top", "bottom", "front", "back", "left", "right", "front_right", "front_left", "back_right", "back_left"],
                        "description": "View angle to capture from"
                    },
                    "description": {
                        "type": "string",
                        "description": "What you're looking for in this view"
                    }
                },
                "required": ["view", "description"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "give_suggestion",
            "description": "Provide a design improvement suggestion to the user. Use this when you've identified an issue and have a recommendation to fix it.",
            "parameters": {
                "type": "object",
                "properties": {
                    "suggestion": {
                        "type": "string", 
                        "description": "Clear, actionable suggestion for the user"
                    },
                    "issue_id": {
                        "type": "string",
                        "description": "Related issue identifier if applicable"
                    },
                    "priority": {
                        "type": "integer",
                        "enum": [1, 2, 3],
                        "description": "Priority: 1=high (blocks manufacturing), 2=medium (problems), 3=low (optimization)"
                    },
                    "auto_fix_code": {
                        "type": "string",
                        "description": "Optional CadQuery code to automatically apply this fix"
                    }
                },
                "required": ["suggestion", "priority"]
            }
        }
    }
]

# Add parts search tools if available (x402 demand-side payments)
if PARTS_SEARCH_AVAILABLE and PARTS_SEARCH_TOOL_DEFINITION:
    TOOL_DEFINITIONS.append(PARTS_SEARCH_TOOL_DEFINITION)
if PARTS_SEARCH_AVAILABLE and DOWNLOAD_CAD_TOOL_DEFINITION:
    TOOL_DEFINITIONS.append(DOWNLOAD_CAD_TOOL_DEFINITION)


class CADAgent:
    """
    LLM-powered agent for CAD analysis with tool calling.
    Follows an agentic loop: LLM thinks → calls tools → gets results → thinks more.
    
    CadQuery operations run in ISOLATED subprocesses to prevent crashes.
    """
    
    def __init__(
        self,
        job_id: str,
        manufacturing_process: str = "FDM_3D_PRINTING",
        workplane: Optional[Any] = None,
        step_file_path: Optional[str] = None,
        llm_client: Optional[FireworksClient] = None,
        backend_client: Optional[Any] = None,
    ):
        self.job_id = job_id
        self.manufacturing_process = manufacturing_process
        self.workplane = workplane
        self.step_file_path = step_file_path  # Path to STEP file for subprocess use
        self._temp_step_file: Optional[str] = None  # Track temp file for cleanup
        self.llm_client = llm_client
        self.backend_client = backend_client  # For posting events to Java backend
        self.conversation: List[Message] = []
        self.max_iterations = 10  # Increased to allow thorough analysis with frequent memory storage
        
    async def initialize(self):
        """Initialize async resources."""
        if self.llm_client is None:
            self.llm_client = FireworksClient()
        # Initialize backend client - required for all tool operations
        if self.backend_client is None:
            if not BACKEND_CLIENT_AVAILABLE:
                raise RuntimeError("Backend client is required but not available")
            self.backend_client = await get_backend_client()
        
        # Export workplane to temp STEP file for subprocess use
        if self.workplane is not None and self.step_file_path is None:
            try:
                import tempfile
                from cadquery import exporters
                temp_file = tempfile.NamedTemporaryFile(suffix=".step", delete=False)
                temp_file.close()
                exporters.export(self.workplane, temp_file.name)
                self.step_file_path = temp_file.name
                self._temp_step_file = temp_file.name
                logger.info(f"Exported workplane to temp file: {temp_file.name}")
            except Exception as e:
                logger.warning(f"Could not export workplane to temp file: {e}")
    
    async def close(self):
        """Close async resources."""
        if self.llm_client:
            await self.llm_client.close()
        
        # Clean up temp STEP file
        if self._temp_step_file:
            try:
                import os
                if os.path.exists(self._temp_step_file):
                    os.unlink(self._temp_step_file)
                    logger.info(f"Cleaned up temp file: {self._temp_step_file}")
            except Exception as e:
                logger.warning(f"Could not clean up temp file: {e}")
    
    async def _post_event_to_backend(self, event: AgentEvent):
        """Post an event to the backend for WebSocket broadcast."""
        if self.backend_client is None:
            return
        
        try:
            await self.backend_client.post_event(
                job_id=self.job_id,
                event_type=event.type.value,
                title=event.type.value.replace("_", " ").title(),
                content=event.content,
                metadata=event.data
            )
        except Exception as e:
            logger.warning(f"Failed to post event to backend: {e}")
    
    def _build_system_prompt(self, image_description: Optional[str] = None) -> str:
        """Build the system prompt for the agent."""
        base = f"""You are a DFM (Design for Manufacturing) analysis expert AI agent.
Your task is to analyze a CAD model for manufacturability issues specific to {self.manufacturing_process}.

IMPORTANT MODEL ACCESS:
- The CAD model is ALREADY LOADED and accessible via the execute_cadquery_code tool
- The 'workplane' variable is pre-loaded with the complete CAD geometry
- You DO NOT need to ask for geometry data - just USE THE TOOLS to analyze it
- The STEP file is already loaded - execute CadQuery code to examine it

YOU HAVE ACCESS TO THESE TOOLS - USE THEM:
1. execute_cadquery_code - Run Python/CadQuery code. The 'workplane' variable has the model loaded.
2. store_memory - IMPORTANT: Store EVERY finding, measurement, and observation as memory!
3. read_memory - Recall your previous findings
4. capture_screenshot - Get SVG visualization of the model from different angles
5. give_suggestion - Provide actionable recommendations for issues found

MEMORY IS CRITICAL - STORE FINDINGS FREQUENTLY:
- After EVERY measurement, call store_memory to record it
- After identifying ANY issue, call store_memory to document it  
- After analyzing ANY feature, call store_memory with observations
- Memory categories: 'measurement', 'issue', 'observation', 'geometry'
- This creates a complete audit trail of your analysis!

ANALYSIS WORKFLOW:
1. Start by examining overall geometry (bounding box, faces, edges, volume)
2. STORE each measurement as memory immediately after getting it
3. Check for process-specific issues (overhangs, wall thickness, draft angles)
4. STORE each issue found as memory with category='issue'
5. Use capture_screenshot for visual verification when needed
6. Provide specific suggestions for each issue using give_suggestion
7. Summarize your findings

When writing CadQuery code:
- The 'workplane' variable IS ALREADY LOADED with the CAD model!
- Always set 'result' variable with your analysis output
- ONLY use the 'cq' module - do NOT import external packages
- Example: faces = workplane.faces().vals(); result = len(faces)
- Example: bb = workplane.val().BoundingBox(); result = {{'xlen': bb.xmax - bb.xmin}}

DO NOT ask for geometry data - you have the tools to get it yourself!
Be thorough but efficient. Focus on issues that actually affect manufacturing.
"""
        
        if image_description:
            base += f"\n\nCAD MODEL SCREENSHOT DESCRIPTION:\n{image_description}\n"
        
        # Add process-specific rules
        process_rules = {
            "FDM_3D_PRINTING": """
FDM 3D PRINTING RULES:
- Overhangs >45° from vertical need support (WARNING)
- Bridges >5mm need support (WARNING)
- Min wall thickness: 0.8mm (ERROR)
- Min feature size: 0.4mm (nozzle diameter) (ERROR)
""",
            "INJECTION_MOLDING": """
INJECTION MOLDING RULES:
- Min wall: 0.8mm, Max wall: 4.0mm
- Draft angle ≥0.5° required (ERROR), recommend 1-2°
- Rib thickness: 50-70% of wall
- Internal corners need ≥0.5mm radius
""",
            "CNC_MACHINING": """
CNC MACHINING RULES:
- Internal corner radius ≥1.5mm (tool constraint)
- Pocket depth ≤3x tool diameter
- Hole depth ≤10x diameter
- Min wall: 0.8mm (metal), 1.5mm (plastic)
"""
        }
        
        base += process_rules.get(self.manufacturing_process, "")
        return base
    
    async def _execute_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a tool and return the result. CadQuery runs in isolated subprocess."""
        # Handle both naming conventions (LLM sometimes uses underscores)
        if tool_name in ("execute_cadquery_code", "execute_cad_query_code"):
            code = arguments.get("code", "")
            description = arguments.get("description", "CadQuery analysis")
            # Pass step_file_path for subprocess isolation
            result = await execute_cadquery_code(
                code, 
                step_file_path=self.step_file_path,
                timeout_seconds=30.0
            )
            
            # AUTO-STORE MEMORY: Automatically store successful CadQuery results with rich detail
            if result.get("success") and self.backend_client:
                try:
                    result_data = result.get("result", result.get("output", ""))
                    # Build a detailed, descriptive memory entry
                    memory_content = f"""**Analysis: {description}**

**Result:** {result_data}

**Code executed:**
```python
{code[:500]}{'...' if len(code) > 500 else ''}
```

**Manufacturing Process:** {self.manufacturing_process}"""
                    await self.backend_client.store_memory(
                        job_id=self.job_id,
                        key=f"analysis_{description[:30].replace(' ', '_').lower()}",
                        value=memory_content,
                        category="measurement"
                    )
                    logger.info(f"Auto-stored detailed memory for CadQuery: {description[:50]}")
                except Exception as e:
                    logger.warning(f"Failed to auto-store CadQuery memory: {e}")
            
            return result
            
        elif tool_name == "store_memory":
            result = await self.backend_client.store_memory(
                job_id=self.job_id,
                key=arguments.get("key", ""),
                value=arguments.get("value", ""),
                category=arguments.get("category", "observation")
            )
            return result
            
        elif tool_name == "read_memory":
            result = await self.backend_client.read_memory(
                job_id=self.job_id,
                query=arguments.get("query"),
                category=arguments.get("category")
            )
            return result
            
        elif tool_name == "give_suggestion":
            suggestion_text = arguments.get("suggestion", "")
            priority = arguments.get("priority", 2)
            
            result = await self.backend_client.give_suggestion(
                job_id=self.job_id,
                suggestion=suggestion_text,
                issue_id=arguments.get("issue_id"),
                priority=priority,
                auto_fix_code=arguments.get("auto_fix_code")
            )
            
            # AUTO-STORE MEMORY: Store suggestions as detailed issue entries
            if result.get("success") and self.backend_client:
                try:
                    priority_label = {1: "🔴 HIGH", 2: "🟡 MEDIUM", 3: "🟢 LOW"}.get(priority, "🟡 MEDIUM")
                    issue_id = arguments.get('issue_id', 'general')
                    auto_fix = arguments.get('auto_fix_code')
                    
                    memory_content = f"""**DFM Issue Found - {priority_label} Priority**

**Issue ID:** {issue_id}

**Problem:** {suggestion_text}

**Manufacturing Process:** {self.manufacturing_process}

**Auto-fix available:** {'Yes' if auto_fix else 'No'}"""
                    
                    if auto_fix:
                        memory_content += f"\n\n**Suggested fix code:**\n```python\n{auto_fix[:300]}{'...' if len(str(auto_fix)) > 300 else ''}\n```"
                    
                    await self.backend_client.store_memory(
                        job_id=self.job_id,
                        key=f"issue_{issue_id}",
                        value=memory_content,
                        category="issue"
                    )
                    logger.info(f"Auto-stored detailed issue memory: {suggestion_text[:50]}")
                except Exception as e:
                    logger.warning(f"Failed to auto-store suggestion memory: {e}")
            
            return result
            
        elif tool_name == "capture_screenshot":
            # Lazy import to avoid circular dep
            from tools.screenshot_renderer import capture_screenshot, read_svg_content
            
            view = arguments.get("view", "iso")
            description = arguments.get("description", f"Screenshot from {view} view")
            
            # Use step_file_path for subprocess isolation
            result = await capture_screenshot(
                step_file_path=self.step_file_path,
                view=view,
            )
            
            # If successful, read the SVG content to pass to LLM
            if result.get("success") and result.get("path"):
                try:
                    svg_content = read_svg_content(result["path"])
                    result["svg_content"] = svg_content
                    
                    # AUTO-STORE MEMORY: Store detailed screenshot observation
                    if self.backend_client:
                        view_descriptions = {
                            "iso": "Isometric view showing 3D perspective",
                            "iso_back": "Back isometric view",
                            "top": "Top-down view (Z-axis)",
                            "bottom": "Bottom view (underside)",
                            "front": "Front elevation",
                            "back": "Rear elevation",
                            "left": "Left side view",
                            "right": "Right side view"
                        }
                        view_desc = view_descriptions.get(view, f"{view} angle")
                        
                        memory_content = f"""**Visual Inspection: {view_desc}**

**View angle:** {view}
**Purpose:** {description}
**Manufacturing process:** {self.manufacturing_process}

**What to look for in this view:**
- Overhangs and bridges (for 3D printing)
- Draft angles (for injection molding)
- Undercuts and negative features
- Surface details and geometry complexity"""
                        
                        await self.backend_client.store_memory(
                            job_id=self.job_id,
                            key=f"visual_{view}",
                            value=memory_content,
                            category="observation"
                        )
                        logger.info(f"Auto-stored detailed visual memory: {view}")
                except Exception as e:
                    result["error_reading_content"] = str(e)
                    
            return result
        
        elif tool_name in ("search_parts", "download_part_cad"):
            # Parts search with x402 payment - handle tool calls
            if not PARTS_SEARCH_AVAILABLE or handle_parts_search_tool_call is None:
                return {"error": "Parts search tool not available. Install x402: pip install x402 eth-account"}
            
            import os
            private_key = os.getenv("X402_AGENT_PRIVATE_KEY")
            result = await handle_parts_search_tool_call(
                tool_name=tool_name,
                arguments=arguments,
                private_key=private_key,
            )
            
            # AUTO-STORE MEMORY: Store parts search results
            if result.get("success") and self.backend_client:
                try:
                    if tool_name == "search_parts":
                        query = arguments.get("query", "")
                        count = result.get("count", 0)
                        results_preview = result.get("results", [])[:3]
                        memory_content = f"""**Parts Search: "{query}"**

**Results found:** {count}

**Top results:**
"""
                        for r in results_preview:
                            memory_content += f"- {r.get('part_number', 'N/A')}: {r.get('name', 'Unknown')} (${r.get('price', 'N/A')})\n"
                        
                        await self.backend_client.store_memory(
                            job_id=self.job_id,
                            key=f"parts_search_{query[:20].replace(' ', '_')}",
                            value=memory_content,
                            category="observation"
                        )
                    elif tool_name == "download_part_cad":
                        part_number = arguments.get("part_number", "")
                        await self.backend_client.store_memory(
                            job_id=self.job_id,
                            key=f"cad_download_{part_number}",
                            value=f"Downloaded CAD for part {part_number} via x402 payment",
                            category="observation"
                        )
                except Exception as e:
                    logger.warning(f"Failed to store parts search memory: {e}")
            
            return result
        
        else:
            return {"error": f"Unknown tool: {tool_name}"}
    
    async def analyze_stream(
        self,
        image_description: Optional[str] = None,
        initial_prompt: Optional[str] = None
    ) -> AsyncGenerator[AgentEvent, None]:
        """
        Run the agentic analysis loop and stream events.
        Events are both yielded (for SSE) and posted to backend (for WebSocket).
        """
        await self.initialize()
        
        # Helper to yield and post event
        async def emit_event(event: AgentEvent) -> AgentEvent:
            await self._post_event_to_backend(event)
            return event
        
        # 0. Initial Screenshot Step
        yield await emit_event(AgentEvent(type=EventType.THINKING, content="Capturing initial view of the model..."))
        
        # Lazy import to avoid circular dep
        from tools.screenshot_renderer import capture_screenshot, read_svg_content
        
        # Capture ISO view automatically (using step_file_path for subprocess isolation)
        init_shot = await capture_screenshot(step_file_path=self.step_file_path, view="iso")
        
        svg_context = ""
        if init_shot.get("success"):
            path = init_shot.get("path")
            yield await emit_event(AgentEvent(
                type=EventType.SCREENSHOT,
                content="Initial ISO View",
                data=init_shot
            ))
            
            # Read minimal content for LLM context - truncate to avoid context overflow
            try:
                svg_content = read_svg_content(path)
                # Truncate SVG to ~20KB to avoid context overflow (most detail in first portion)
                max_svg_chars = 20000
                if len(svg_content) > max_svg_chars:
                    svg_context = svg_content[:max_svg_chars] + "\n<!-- SVG truncated -->"
                else:
                    svg_context = svg_content
            except Exception:
                pass

        # Build system prompt
        system_prompt = self._build_system_prompt(image_description)
        
        # Initial user message with visual context
        base_msg = initial_prompt or f"Analyze this CAD model for {self.manufacturing_process} manufacturability. Examine the geometry thoroughly, identify all potential issues, and provide actionable suggestions."
        
        if svg_context:
            user_message = f"{base_msg}\n\n[Attached SVG of model view]:\n{svg_context}"
        else:
            user_message = base_msg
        
        yield await emit_event(AgentEvent(
            type=EventType.THINKING,
            content=f"Starting {self.manufacturing_process} analysis loop..."
        ))
        
        iteration = 0
        
        while iteration < self.max_iterations:
            iteration += 1
            
            try:
                # Call LLM
                # Build iteration-appropriate prompts that emphasize tool usage
                if iteration == 1:
                    prompt_content = user_message
                else:
                    # More detailed continuation prompt that reminds about tools
                    prompt_content = f"""Continue your DFM analysis (iteration {iteration}/{self.max_iterations}).

REMEMBER: The CAD model is loaded and accessible via your tools!
- Use execute_cadquery_code to analyze geometry (workplane variable has the model)
- Use store_memory to record EVERY finding and measurement
- Use capture_screenshot if you need visual verification
- Use give_suggestion for any issues you've identified
- Use read_memory to recall what you've already found

Based on your previous analysis, continue with:
1. Any remaining geometry measurements (and STORE them as memories)
2. Process-specific DFM checks for {self.manufacturing_process}
3. Suggestions for any issues found

If analysis is complete, provide a final summary. Otherwise, keep using tools to analyze."""
                
                response = await self.llm_client.analyze_cad(
                    cad_description=prompt_content,
                    manufacturing_process=self.manufacturing_process,
                    geometry_data={"iteration": iteration, "max_iterations": self.max_iterations},
                    mcp_tools=TOOL_DEFINITIONS
                )
                
                # Parse OpenAI-compatible response format
                choices = response.get("choices", [])
                if not choices:
                    break
                    
                message = choices[0].get("message", {})
                content = message.get("content", "")
                tool_calls = message.get("tool_calls", [])
                
                # Stream thought content
                if content:
                    yield await emit_event(AgentEvent(
                        type=EventType.THINKING,
                        content=content
                    ))
                
                # Handle tool calls
                if tool_calls:
                    for tool_call in tool_calls:
                        function = tool_call.get("function", {})
                        tool_name = function.get("name", "")
                        try:
                            tool_input = json.loads(function.get("arguments", "{}"))
                        except:
                            tool_input = {}
                            
                        yield await emit_event(AgentEvent(
                            type=EventType.TOOL_CALL,
                            content=f"Calling {tool_name}...",
                            data={"tool": tool_name, "input": tool_input}
                        ))
                        
                        # Execute tool
                        result = await self._execute_tool(tool_name, tool_input)
                        
                        yield await emit_event(AgentEvent(
                            type=EventType.TOOL_RESULT,
                            content=f"{tool_name} completed",
                            data={"tool": tool_name, "result": result}
                        ))
                        
                        # Special handling for Screenshot tool result to show it
                        if tool_name == "capture_screenshot" and result.get("success"):
                             yield await emit_event(AgentEvent(
                                type=EventType.SCREENSHOT,
                                content=f"Screenshot ({tool_input.get('view', 'view')})",
                                data=result
                            ))
                        
                        # Special handling for suggestions
                        if tool_name == "give_suggestion" and result.get("success"):
                            yield await emit_event(AgentEvent(
                                type=EventType.SUGGESTION,
                                content=tool_input.get("suggestion", ""),
                                data=result.get("suggestion")
                            ))
                        
                        # Special handling for memory storage
                        if tool_name == "store_memory" and result.get("success"):
                            yield await emit_event(AgentEvent(
                                type=EventType.MEMORY,
                                content=f"Stored: {tool_input.get('key')}",
                                data={"action": "store", "key": tool_input.get("key")}
                            ))
                
                # Stop condition (if no tool calls and we have content, usually implies done or waiting for user)
                # But in this loop, if no tools calls, we generally stop unless we want to prompt for confirmation
                if not tool_calls:
                     break
                     
            except Exception as e:
                logger.error(f"Error in agent loop: {e}")
                import traceback
                traceback.print_exc()
                yield await emit_event(AgentEvent(
                    type=EventType.ERROR,
                    content=f"Error: {str(e)}"
                ))
                break
        
        # Completion event
        yield await emit_event(AgentEvent(
            type=EventType.COMPLETE,
            content=f"Analysis complete after {iteration} iterations.",
            data={"iterations": iteration}
        ))
    
    async def analyze(
        self,
        image_description: Optional[str] = None,
        initial_prompt: Optional[str] = None
    ) -> List[AgentEvent]:
        """
        Run analysis and return all events as a list.
        Non-streaming version.
        """
        events = []
        async for event in self.analyze_stream(image_description, initial_prompt):
            events.append(event)
        return events


async def create_agent(
    job_id: str,
    manufacturing_process: str = "FDM_3D_PRINTING",
    workplane: Optional[Any] = None,
    step_file_path: Optional[str] = None,
) -> CADAgent:
    """Factory function to create and initialize an agent."""
    agent = CADAgent(
        job_id=job_id,
        manufacturing_process=manufacturing_process,
        workplane=workplane,
        step_file_path=step_file_path,
    )
    await agent.initialize()
    return agent
