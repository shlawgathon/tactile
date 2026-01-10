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
from tools.memory_client import MemoryClient, get_memory_client
from tools.screenshot_renderer import capture_screenshot, capture_multiple_views, AVAILABLE_VIEWS


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
            "description": "Execute CadQuery Python code to analyze or measure the CAD model geometry. Use this to examine specific features, measure dimensions, check angles, count faces, etc. The code has access to a 'workplane' variable containing the current CAD model.",
            "parameters": {
                "type": "object",
                "properties": {
                    "code": {
                        "type": "string",
                        "description": "Python code using CadQuery to analyze the model. Must set 'result' variable with the output. Has access to 'cq' (cadquery module) and 'workplane' (current model)."
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
            "description": "Store an important observation or finding about the CAD model that should be remembered. Use this to save key insights, measurements, or identified issues.",
            "parameters": {
                "type": "object",
                "properties": {
                    "key": {
                        "type": "string",
                        "description": "Short identifier for this memory (e.g., 'overhang_issue', 'wall_thickness')"
                    },
                    "value": {
                        "type": "string",
                        "description": "The observation or finding to store"
                    },
                    "category": {
                        "type": "string",
                        "enum": ["observation", "measurement", "issue", "geometry"],
                        "description": "Category of the memory"
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


class CADAgent:
    """
    LLM-powered agent for CAD analysis with tool calling.
    Follows an agentic loop: LLM thinks → calls tools → gets results → thinks more.
    """
    
    def __init__(
        self,
        job_id: str,
        manufacturing_process: str = "FDM_3D_PRINTING",
        workplane: Optional[Any] = None,
        memory_client: Optional[MemoryClient] = None,
        llm_client: Optional[FireworksClient] = None,
    ):
        self.job_id = job_id
        self.manufacturing_process = manufacturing_process
        self.workplane = workplane
        self.memory_client = memory_client
        self.llm_client = llm_client
        self.conversation: List[Message] = []
        self.max_iterations = 10
        
    async def initialize(self):
        """Initialize async resources."""
        if self.memory_client is None:
            self.memory_client = await get_memory_client()
        if self.llm_client is None:
            self.llm_client = FireworksClient()
    
    async def close(self):
        """Close async resources."""
        if self.llm_client:
            await self.llm_client.close()
    
    def _build_system_prompt(self, image_description: Optional[str] = None) -> str:
        """Build the system prompt for the agent."""
        base = f"""You are a DFM (Design for Manufacturing) analysis expert AI agent.
Your task is to analyze a CAD model for manufacturability issues specific to {self.manufacturing_process}.

You have access to tools to:
1. execute_cadquery_code - Run Python/CadQuery code to examine the geometry
2. store_memory - Save important findings about the model
3. read_memory - Recall previously saved findings
4. give_suggestion - Provide actionable recommendations to improve the design

ANALYSIS WORKFLOW:
1. First, examine the overall geometry (bounding box, face count, volume)
2. Check for process-specific issues (overhangs for 3D printing, draft angles for molding, etc.)
3. Measure critical dimensions and tolerances
4. Store important findings as memories
5. Provide specific, actionable suggestions for each issue found

When writing CadQuery code:
- The 'workplane' variable contains the loaded CAD model
- Always set the 'result' variable with your analysis output
- Be precise with measurements (use mm)
- Handle potential errors gracefully

Be thorough but efficient. Focus on issues that would actually affect manufacturing.
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
        """Execute a tool and return the result."""
        if tool_name == "execute_cadquery_code":
            code = arguments.get("code", "")
            result = await execute_cadquery_code(
                code, 
                workplane=self.workplane,
                timeout_seconds=30.0
            )
            return result
            
        elif tool_name == "store_memory":
            result = await self.memory_client.store_memory(
                job_id=self.job_id,
                key=arguments.get("key", ""),
                value=arguments.get("value", ""),
                category=arguments.get("category", "observation")
            )
            return result
            
        elif tool_name == "read_memory":
            result = await self.memory_client.read_memory(
                job_id=self.job_id,
                query=arguments.get("query"),
                category=arguments.get("category")
            )
            return result
            
        elif tool_name == "give_suggestion":
            result = await self.memory_client.give_suggestion(
                job_id=self.job_id,
                suggestion=arguments.get("suggestion", ""),
                issue_id=arguments.get("issue_id"),
                priority=arguments.get("priority", 2),
                auto_fix_code=arguments.get("auto_fix_code")
            )
            return result
            
        elif tool_name == "capture_screenshot":
            # Lazy import to avoid circular dep
            from tools.screenshot_renderer import capture_screenshot, read_svg_content
            
            result = await capture_screenshot(
                workplane=self.workplane,
                view=arguments.get("view", "iso"),
            )
            
            # If successful, read the SVG content to pass to LLM
            if result.get("success") and result.get("path"):
                try:
                    svg_content = read_svg_content(result["path"])
                    # Truncate if excessively large (e.g. > 1MB) to avoid OOM, 
                    # but current models can handle large context. 
                    # Providing a reasonable limit of 200KB characters for safety if needed,
                    # but usually we want the whole thing.
                    result["svg_content"] = svg_content
                except Exception as e:
                    result["error_reading_content"] = str(e)
                    
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
        """
        await self.initialize()
        
        # 0. Initial Screenshot Step
        yield AgentEvent(type=EventType.THINKING, content="Capturing initial view of the model...")
        
        # Lazy import to avoid circular dep
        from tools.screenshot_renderer import capture_screenshot, read_svg_content
        
        # Capture ISO view automatically
        init_shot = await capture_screenshot(self.workplane, view="iso")
        
        svg_context = ""
        if init_shot.get("success"):
            path = init_shot.get("path")
            yield AgentEvent(
                type=EventType.SCREENSHOT,  # New event type (need to add to Enum)
                content="Initial ISO View",
                data=init_shot
            )
            
            # Read minimal content for LLM context
            try:
                svg_content = read_svg_content(path)
                # We can truncate or optimize here if needed, but for now pass standard context
                # Just indicate we have the visual
                svg_context = f"\n\nInitial Model View (SVG):\n{svg_content[:500]}... (truncated for brevity in log, full content passed to model)"
                
                # Update screenshot result with content for the actual LLM call if we decide to pass full content
                # For this implementation, we'll append standard SVG context to the user message
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
        
        yield AgentEvent(
            type=EventType.THINKING,
            content=f"Starting {self.manufacturing_process} analysis loop..."
        )
        
        iteration = 0
        
        while iteration < self.max_iterations:
            iteration += 1
            
            try:
                # Call LLM
                # Note: cad_description is used as the 'user' message content in our updated client
                prompt_content = user_message if iteration == 1 else f"Iteration {iteration}: Continue analysis. If issues found, give suggestions. If done, summarize."
                
                response = await self.llm_client.analyze_cad(
                    cad_description=prompt_content,
                    manufacturing_process=self.manufacturing_process,
                    geometry_data={"iteration": iteration},
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
                    yield AgentEvent(
                        type=EventType.THINKING,
                        content=content
                    )
                
                # Handle tool calls
                if tool_calls:
                    for tool_call in tool_calls:
                        function = tool_call.get("function", {})
                        tool_name = function.get("name", "")
                        try:
                            tool_input = json.loads(function.get("arguments", "{}"))
                        except:
                            tool_input = {}
                            
                        yield AgentEvent(
                            type=EventType.TOOL_CALL,
                            content=f"Calling {tool_name}...",
                            data={"tool": tool_name, "input": tool_input}
                        )
                        
                        # Execute tool
                        result = await self._execute_tool(tool_name, tool_input)
                        
                        yield AgentEvent(
                            type=EventType.TOOL_RESULT,
                            content=f"{tool_name} completed",
                            data={"tool": tool_name, "result": result}
                        )
                        
                        # Special handling for Screenshot tool result to show it
                        if tool_name == "capture_screenshot" and result.get("success"):
                             yield AgentEvent(
                                type=EventType.SCREENSHOT,
                                content=f"Screenshot ({tool_input.get('view', 'view')})",
                                data=result
                            )
                        
                        # Special handling for suggestions
                        if tool_name == "give_suggestion" and result.get("success"):
                            yield AgentEvent(
                                type=EventType.SUGGESTION,
                                content=tool_input.get("suggestion", ""),
                                data=result.get("suggestion")
                            )
                        
                        # Special handling for memory storage
                        if tool_name == "store_memory" and result.get("success"):
                            yield AgentEvent(
                                type=EventType.MEMORY,
                                content=f"Stored: {tool_input.get('key')}",
                                data={"action": "store", "key": tool_input.get("key")}
                            )
                
                # Stop condition (if no tool calls and we have content, usually implies done or waiting for user)
                # But in this loop, if no tools calls, we generally stop unless we want to prompt for confirmation
                if not tool_calls:
                     break
                     
            except Exception as e:
                logger.error(f"Error in agent loop: {e}")
                import traceback
                traceback.print_exc()
                yield AgentEvent(
                    type=EventType.ERROR,
                    content=f"Error: {str(e)}"
                )
                break
        
        # Completion event
        yield AgentEvent(
            type=EventType.COMPLETE,
            content=f"Analysis complete after {iteration} iterations.",
            data={"iterations": iteration}
        )
    
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
) -> CADAgent:
    """Factory function to create and initialize an agent."""
    agent = CADAgent(
        job_id=job_id,
        manufacturing_process=manufacturing_process,
        workplane=workplane,
    )
    await agent.initialize()
    return agent
