"""
Backend API Client for CAD Agent.
Posts events, memories, and suggestions to the Java backend API,
which then broadcasts them via WebSocket to connected frontend clients.
"""

import os
import logging
from typing import Any, Dict, List, Optional

import httpx

logger = logging.getLogger(__name__)


class BackendClient:
    """
    HTTP client for communicating with the Java backend.
    All agent events are posted here to be:
    1. Stored in MongoDB
    2. Broadcast to WebSocket clients in real-time
    """
    
    def __init__(self, base_url: Optional[str] = None, api_key: Optional[str] = None):
        self.base_url = base_url or os.getenv("BACKEND_URL", "http://localhost:8080")
        self.api_key = api_key or os.getenv("AGENT_API_KEY", "")
        self._client: Optional[httpx.AsyncClient] = None
        self._connection_failed = False  # Track if backend is unavailable
    
    async def connect(self):
        """Create the HTTP client with API key header if configured."""
        if self._client is None:
            headers = {}
            if self.api_key:
                headers["X-Agent-Api-Key"] = self.api_key
            self._client = httpx.AsyncClient(timeout=30.0, headers=headers)
    
    async def close(self):
        """Close the HTTP client."""
        if self._client:
            await self._client.aclose()
            self._client = None
    
    # ==================== Agent Events ====================
    
    async def post_event(
        self,
        job_id: str,
        event_type: str,
        title: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Post an agent event to the backend.
        The backend will store it and broadcast via WebSocket.
        
        Args:
            job_id: The job ID
            event_type: One of ANALYZING, RUNNING_CODE, TOOL_RESULT, THINKING, 
                       SUGGESTION, ERROR, MEMORY_STORED
            title: Short title for display
            content: Detailed content
            metadata: Additional structured data
        """
        # Skip if backend is known to be unavailable
        if self._connection_failed:
            return {"success": False, "error": "Backend unavailable"}
        
        await self.connect()
        
        # Map our EventType to backend's AgentEventType
        type_mapping = {
            "thinking": "THINKING",
            "tool_call": "RUNNING_CODE",
            "tool_result": "TOOL_RESULT",
            "suggestion": "SUGGESTION",
            "memory": "MEMORY_STORED",
            "error": "ERROR",
            "complete": "THINKING",  # Use THINKING for completion messages
            "screenshot": "ANALYZING",
        }
        
        backend_type = type_mapping.get(event_type.lower(), "THINKING")
        
        payload = {
            "type": backend_type,
            "title": title,
            "content": content,
            "metadata": metadata or {}
        }
        
        try:
            response = await self._client.post(
                f"{self.base_url}/internal/jobs/{job_id}/events",
                json=payload
            )
            response.raise_for_status()
            return {"success": True, "event": response.json()}
        except httpx.HTTPStatusError as e:
            logger.error(f"Failed to post event: {e.response.status_code} - {e.response.text}")
            return {"success": False, "error": str(e)}
        except httpx.ConnectError:
            # Backend not running - mark as failed and stop spamming logs
            if not self._connection_failed:
                logger.warning("Backend unavailable - events will not be posted")
                self._connection_failed = True
            return {"success": False, "error": "Backend unavailable"}
        except Exception as e:
            if "connection" in str(e).lower():
                if not self._connection_failed:
                    logger.warning("Backend unavailable - events will not be posted")
                    self._connection_failed = True
                return {"success": False, "error": "Backend unavailable"}
            logger.error(f"Failed to post event: {e}")
            return {"success": False, "error": str(e)}
    
    # ==================== Memory Operations ====================
    
    async def store_memory(
        self,
        job_id: str,
        key: str,
        value: str,
        category: str = "observation"
    ) -> Dict[str, Any]:
        """
        Store a memory about the CAD model via the backend API.
        
        Args:
            job_id: Job ID to associate memory with
            key: Memory key/identifier  
            value: Memory value/content
            category: Memory category (observation, measurement, issue, geometry)
        """
        if self._connection_failed:
            return {"success": False, "error": "Backend unavailable"}
        
        await self.connect()
        
        payload = {
            "category": category,
            "content": f"{key}: {value}",
            "metadata": {"key": key, "original_value": value}
        }
        
        try:
            response = await self._client.post(
                f"{self.base_url}/internal/jobs/{job_id}/memory",
                json=payload
            )
            response.raise_for_status()
            return {"success": True, "memory": response.json()}
        except httpx.HTTPStatusError as e:
            logger.error(f"Failed to store memory: {e.response.status_code} - {e.response.text}")
            return {"success": False, "error": str(e)}
        except (httpx.ConnectError, Exception) as e:
            if "connection" in str(e).lower() or isinstance(e, httpx.ConnectError):
                self._connection_failed = True
            return {"success": False, "error": str(e)}
    
    async def read_memory(
        self,
        job_id: str,
        query: Optional[str] = None,
        category: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Read memories from the backend API.
        
        Args:
            job_id: Job ID to read memories for
            query: Optional text to search for
            category: Optional category filter
        """
        if self._connection_failed:
            return {"success": False, "error": "Backend unavailable", "memories": []}
        
        await self.connect()
        
        params = {}
        if category:
            params["category"] = category
        
        try:
            response = await self._client.get(
                f"{self.base_url}/internal/jobs/{job_id}/memory",
                params=params
            )
            response.raise_for_status()
            memories = response.json()
            
            # Filter by query if provided
            if query:
                query_lower = query.lower()
                memories = [
                    m for m in memories 
                    if query_lower in (m.get("content", "") or "").lower()
                ]
            
            return {"success": True, "memories": memories, "count": len(memories)}
        except httpx.HTTPStatusError as e:
            logger.error(f"Failed to read memory: {e.response.status_code}")
            return {"success": False, "error": str(e), "memories": []}
        except (httpx.ConnectError, Exception) as e:
            if "connection" in str(e).lower() or isinstance(e, httpx.ConnectError):
                self._connection_failed = True
            return {"success": False, "error": str(e), "memories": []}
    
    # ==================== Suggestions ====================
    
    async def give_suggestion(
        self,
        job_id: str,
        suggestion: str,
        issue_id: Optional[str] = None,
        priority: int = 2,
        auto_fix_code: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Submit a suggestion via the backend API.
        
        Args:
            job_id: Job ID to associate suggestion with
            suggestion: The suggestion text
            issue_id: Optional related issue ID
            priority: Priority level (1=high, 2=medium, 3=low)
            auto_fix_code: Optional CadQuery code to auto-fix
        """
        if self._connection_failed:
            return {"success": False, "error": "Backend unavailable"}
        
        await self.connect()
        
        payload = {
            "issueId": issue_id,
            "description": suggestion,
            "expectedImprovement": "Addresses identified manufacturing concern",
            "priority": priority,
            "codeSnippet": auto_fix_code
        }
        
        try:
            response = await self._client.post(
                f"{self.base_url}/internal/jobs/{job_id}/suggestions",
                json=payload
            )
            response.raise_for_status()
            return {"success": True, "suggestion": payload}
        except httpx.HTTPStatusError as e:
            logger.error(f"Failed to submit suggestion: {e.response.status_code} - {e.response.text}")
            return {"success": False, "error": str(e)}
        except (httpx.ConnectError, Exception) as e:
            if "connection" in str(e).lower() or isinstance(e, httpx.ConnectError):
                self._connection_failed = True
            return {"success": False, "error": str(e)}
    
    # ==================== Job Lifecycle ====================
    
    async def update_job_status(
        self,
        job_id: str,
        stage: str,
        stage_index: int = 0,
        state: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Send a checkpoint/status update to the backend.
        
        Args:
            job_id: The job ID
            stage: Current stage name (PARSE, ANALYZE, SUGGEST, VALIDATE)
            stage_index: Stage index for progress calculation
            state: Optional state data
        """
        await self.connect()
        
        payload = {
            "stage": stage,
            "stageIndex": stage_index,
            "state": state or {},
            "intermediateResults": {}
        }
        
        try:
            response = await self._client.post(
                f"{self.base_url}/internal/jobs/{job_id}/checkpoint",
                json=payload
            )
            response.raise_for_status()
            return {"success": True}
        except httpx.HTTPStatusError as e:
            logger.error(f"Failed to update status: {e.response.status_code}")
            return {"success": False, "error": str(e)}
        except Exception as e:
            logger.error(f"Failed to update status: {e}")
            return {"success": False, "error": str(e)}
    
    async def complete_job(
        self,
        job_id: str,
        issues: List[Dict[str, Any]],
        suggestions: List[Dict[str, Any]],
        geometry_summary: Optional[Dict[str, Any]] = None,
        markdown_report: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Mark the job as completed with results.
        
        Args:
            job_id: The job ID
            issues: List of identified issues
            suggestions: List of suggestions
            geometry_summary: Optional geometry data
            markdown_report: Optional markdown analysis report
        """
        await self.connect()
        
        payload = {
            "success": True,
            "results": {
                "geometrySummary": geometry_summary,
                "issues": issues,
                "suggestions": suggestions,
                "generatedCode": [],
                "markdownReport": markdown_report
            },
            "outputFiles": {}
        }
        
        try:
            response = await self._client.post(
                f"{self.base_url}/internal/jobs/{job_id}/complete",
                json=payload
            )
            response.raise_for_status()
            return {"success": True}
        except httpx.HTTPStatusError as e:
            logger.error(f"Failed to complete job: {e.response.status_code} - {e.response.text}")
            return {"success": False, "error": str(e)}
        except Exception as e:
            logger.error(f"Failed to complete job: {e}")
            return {"success": False, "error": str(e)}
    
    async def fail_job(self, job_id: str, error_message: str) -> Dict[str, Any]:
        """
        Mark the job as failed.
        
        Args:
            job_id: The job ID
            error_message: Error description
        """
        await self.connect()
        
        payload = {"errorMessage": error_message}
        
        try:
            response = await self._client.post(
                f"{self.base_url}/internal/jobs/{job_id}/fail",
                json=payload
            )
            response.raise_for_status()
            return {"success": True}
        except Exception as e:
            logger.error(f"Failed to report failure: {e}")
            return {"success": False, "error": str(e)}
    
    # ==================== File Download ====================
    
    async def download_file(self, file_url: str, output_path: str) -> Dict[str, Any]:
        """
        Download a file from the backend.
        
        Args:
            file_url: The file URL (relative or absolute)
            output_path: Local path to save the file
        """
        await self.connect()
        
        # Handle relative URLs
        if file_url.startswith("/"):
            full_url = f"{self.base_url}{file_url}"
        else:
            full_url = file_url
        
        try:
            response = await self._client.get(full_url)
            response.raise_for_status()
            
            with open(output_path, "wb") as f:
                f.write(response.content)
            
            return {"success": True, "path": output_path, "size": len(response.content)}
        except httpx.HTTPStatusError as e:
            logger.error(f"Failed to download file: {e.response.status_code}")
            return {"success": False, "error": str(e)}
        except Exception as e:
            logger.error(f"Failed to download file: {e}")
            return {"success": False, "error": str(e)}


# Singleton instance
_backend_client: Optional[BackendClient] = None


async def get_backend_client() -> BackendClient:
    """Get or create the backend client singleton."""
    global _backend_client
    if _backend_client is None:
        _backend_client = BackendClient()
        await _backend_client.connect()
    return _backend_client

