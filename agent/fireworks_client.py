"""
Fireworks AI client for LLM inference with MCP tool support.
Uses the Responses API: POST /inference/v1/responses
"""

import os
import httpx
from typing import Dict, Any, Optional, List

# Standard Chat Completions API
FIREWORKS_API_URL = "https://api.fireworks.ai/inference/v1/chat/completions"
DEFAULT_MODEL = "accounts/fireworks/models/minimax-m2p1"


class FireworksClient:
    """Client for Fireworks AI Chat Completions API with MCP tool support."""
    
    def __init__(self, api_key: Optional[str] = None, model: str = DEFAULT_MODEL):
        self.api_key = api_key or os.getenv("FIREWORKS_API_KEY")
        if not self.api_key:
            raise ValueError("FIREWORKS_API_KEY environment variable required")
        self.model = model
        self.client = httpx.AsyncClient(timeout=120.0)
    
    async def analyze_cad(
        self,
        cad_description: str,
        manufacturing_process: str,
        geometry_data: Optional[Dict[str, Any]] = None,
        mcp_tools: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        """
        Send CAD analysis request to Fireworks AI LLM.
        """
        
        system_instructions = self._build_system_prompt(manufacturing_process)
        user_content = self._build_input(cad_description, geometry_data)
        
        # Build standard chat messages
        messages = [
            {"role": "system", "content": system_instructions},
            {"role": "user", "content": user_content}
        ]
        
        # Payload matching Fireworks API format
        payload = {
            "model": self.model,
            "max_tokens": 4096,
            "top_p": 1,
            "top_k": 40,
            "presence_penalty": 0,
            "frequency_penalty": 0,
            "temperature": 0.6,
            "messages": messages,
        }
        
        # Add tools if provided (OpenAI function calling format)
        if mcp_tools:
            payload["tools"] = mcp_tools
        
        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }
        
        # Using httpx for async compatibility (replaces requests.request)
        response = await self.client.post(
            FIREWORKS_API_URL,
            json=payload,
            headers=headers
        )
        
        if response.status_code == 401:
             raise Exception(f"Authentication failed (401). Please check provided API Key. Response: {response.text}")
             
        response.raise_for_status()
        
        return response.json()
    
    def _build_system_prompt(self, manufacturing_process: str) -> str:
        """Build system prompt with DFM rules for the specified process."""
        
        base_prompt = """You are a DFM (Design for Manufacturing) analysis expert. 
Analyze CAD geometry data and identify manufacturability issues.

For each issue found, provide:
1. rule_id: Unique identifier (e.g., "IM_WALL_001")
2. rule_name: Human-readable name
3. severity: ERROR (blocks manufacturing), WARNING (may cause problems), INFO (optimization)
4. description: Clear explanation of the issue
5. affected_features: List of face/edge IDs affected
6. recommendation: Specific fix recommendation
7. auto_fix_available: Boolean if CadQuery can auto-fix

Also provide CadQuery code snippets to fix issues where possible.

Respond in valid JSON format with "issues" and "suggestions" arrays.
"""
        
        process_rules = {
            "INJECTION_MOLDING": """
INJECTION MOLDING DFM RULES:
- Minimum wall thickness: 0.8mm (ERROR if below)
- Maximum wall thickness: 4.0mm (WARNING if above)
- Wall thickness uniformity: ±25% variation (WARNING)
- Minimum draft angle: 0.5° (ERROR if below), recommend 1-2°
- Rib thickness: 50-70% of wall thickness
- Rib height: Max 3x rib thickness
- Internal corner radius: Min 0.5mm
""",
            "CNC_MACHINING": """
CNC MACHINING DFM RULES:
- Internal corner radius: Min 1.5mm (tool radius constraint) (ERROR)
- Pocket depth: Max 3x tool diameter (WARNING)
- Minimum wall thickness: 0.8mm metal, 1.5mm plastic (ERROR)
- Hole depth: Max 10x diameter (WARNING)
- Use standard drill sizes when possible (INFO)
""",
            "FDM_3D_PRINTING": """
FDM 3D PRINTING DFM RULES:
- Overhang angle: Max 45° from vertical without support (WARNING)
- Bridge length: Max 5mm without support (WARNING)
- Minimum wall thickness: 0.8mm (2x nozzle diameter) (ERROR)
- Minimum feature size: 0.4mm (nozzle diameter) (ERROR)
"""
        }
        
        return base_prompt + process_rules.get(manufacturing_process, "")
    
    def _build_input(
        self,
        cad_description: str,
        geometry_data: Optional[Dict[str, Any]] = None
    ) -> str:
        """Build input text with CAD context."""
        
        input_parts = [f"CAD Description: {cad_description}"]
        
        if geometry_data:
            input_parts.append(f"\nGeometry Analysis Data:\n{geometry_data}")
        
        input_parts.append("\nAnalyze this CAD model for DFM issues and provide recommendations.")
        
        return "\n".join(input_parts)
    
    async def close(self):
        """Close the HTTP client."""
        await self.client.aclose()


def get_cadquery_mcp_tools() -> List[Dict[str, Any]]:
    """
    Define MCP tool specifications for CadQuery operations.
    These allow the LLM to request geometry queries.
    """
    return [
        {
            "type": "mcp",
            "server_label": "cadquery",
            "server_url": "https://cadquery-mcp.example.com",  # Replace with actual MCP server
            "require_approval": "never"
        }
    ]
