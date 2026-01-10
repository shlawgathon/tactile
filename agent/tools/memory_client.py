"""
MongoDB memory client for CAD Agent.
Provides store_memory, read_memory, and give_suggestion operations.
"""

import os
from datetime import datetime
from typing import Any, Dict, List, Optional

from motor.motor_asyncio import AsyncIOMotorClient
from pymongo.errors import PyMongoError


class MemoryClient:
    """MongoDB client for agent memory operations."""
    
    def __init__(self, mongo_uri: Optional[str] = None, database: str = "tactile"):
        self.mongo_uri = mongo_uri or os.getenv("MONGODB_URI", "mongodb://localhost:27017")
        self.database_name = database
        self._client: Optional[AsyncIOMotorClient] = None
        self._db = None
    
    async def connect(self):
        """Connect to MongoDB."""
        if self._client is None:
            self._client = AsyncIOMotorClient(self.mongo_uri)
            self._db = self._client[self.database_name]
    
    async def close(self):
        """Close MongoDB connection."""
        if self._client:
            self._client.close()
            self._client = None
            self._db = None
    
    @property
    def memories(self):
        """Get memories collection."""
        return self._db["agent_memories"]
    
    @property
    def suggestions(self):
        """Get suggestions collection."""
        return self._db["agent_suggestions"]
    
    async def store_memory(
        self,
        job_id: str,
        key: str,
        value: Any,
        category: str = "observation"
    ) -> Dict[str, Any]:
        """
        Store a memory about the CAD model.
        
        Args:
            job_id: Job ID to associate memory with
            key: Memory key/identifier
            value: Memory value (any JSON-serializable data)
            category: Memory category (observation, measurement, issue, etc.)
            
        Returns:
            Stored memory document
        """
        await self.connect()
        
        memory = {
            "job_id": job_id,
            "key": key,
            "value": value,
            "category": category,
            "created_at": datetime.utcnow(),
        }
        
        try:
            result = await self.memories.insert_one(memory)
            memory["_id"] = str(result.inserted_id)
            return {"success": True, "memory": memory}
        except PyMongoError as e:
            return {"success": False, "error": str(e)}
    
    async def read_memory(
        self,
        job_id: str,
        query: Optional[str] = None,
        category: Optional[str] = None,
        limit: int = 10
    ) -> Dict[str, Any]:
        """
        Read memories for a job.
        
        Args:
            job_id: Job ID to read memories for
            query: Optional text to search for in keys/values
            category: Optional category filter
            limit: Maximum number of memories to return
            
        Returns:
            List of matching memories
        """
        await self.connect()
        
        filter_query: Dict[str, Any] = {"job_id": job_id}
        
        if category:
            filter_query["category"] = category
        
        if query:
            # Simple text search in key and value
            filter_query["$or"] = [
                {"key": {"$regex": query, "$options": "i"}},
                {"value": {"$regex": query, "$options": "i"}} if isinstance(query, str) else {}
            ]
        
        try:
            cursor = self.memories.find(filter_query).sort("created_at", -1).limit(limit)
            memories = []
            async for doc in cursor:
                doc["_id"] = str(doc["_id"])
                memories.append(doc)
            return {"success": True, "memories": memories, "count": len(memories)}
        except PyMongoError as e:
            return {"success": False, "error": str(e), "memories": []}
    
    async def give_suggestion(
        self,
        job_id: str,
        suggestion: str,
        issue_id: Optional[str] = None,
        priority: int = 2,
        auto_fix_code: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Store a suggestion for the user.
        
        Args:
            job_id: Job ID to associate suggestion with
            suggestion: The suggestion text
            issue_id: Optional related issue ID
            priority: Priority level (1=high, 2=medium, 3=low)
            auto_fix_code: Optional CadQuery code to auto-fix
            
        Returns:
            Stored suggestion document
        """
        await self.connect()
        
        suggestion_doc = {
            "job_id": job_id,
            "suggestion": suggestion,
            "issue_id": issue_id,
            "priority": priority,
            "auto_fix_code": auto_fix_code,
            "status": "pending",
            "created_at": datetime.utcnow(),
        }
        
        try:
            result = await self.suggestions.insert_one(suggestion_doc)
            suggestion_doc["_id"] = str(result.inserted_id)
            return {"success": True, "suggestion": suggestion_doc}
        except PyMongoError as e:
            return {"success": False, "error": str(e)}
    
    async def get_suggestions(
        self,
        job_id: str,
        status: Optional[str] = None,
        limit: int = 20
    ) -> Dict[str, Any]:
        """
        Get suggestions for a job.
        
        Args:
            job_id: Job ID to get suggestions for
            status: Optional status filter (pending, accepted, rejected)
            limit: Maximum number of suggestions to return
            
        Returns:
            List of suggestions
        """
        await self.connect()
        
        filter_query: Dict[str, Any] = {"job_id": job_id}
        if status:
            filter_query["status"] = status
        
        try:
            cursor = self.suggestions.find(filter_query).sort("priority", 1).limit(limit)
            suggestions = []
            async for doc in cursor:
                doc["_id"] = str(doc["_id"])
                suggestions.append(doc)
            return {"success": True, "suggestions": suggestions, "count": len(suggestions)}
        except PyMongoError as e:
            return {"success": False, "error": str(e), "suggestions": []}


# Singleton instance
_memory_client: Optional[MemoryClient] = None


async def get_memory_client() -> MemoryClient:
    """Get or create the memory client singleton."""
    global _memory_client
    if _memory_client is None:
        _memory_client = MemoryClient()
        await _memory_client.connect()
    return _memory_client
