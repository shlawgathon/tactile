"""
Parts Search Tool with x402 Payment Integration

This tool enables the CAD agent to search for parts from external suppliers
and pay for premium part data or CAD downloads using the x402 protocol.

Use cases:
- Search for standard components (screws, bearings, motors, etc.)
- Get detailed specifications for parts
- Download CAD models of parts (paid via x402)
- Compare pricing across suppliers
"""

from typing import Optional, List, Any
import os
import json
import logging
import httpx

logger = logging.getLogger(__name__)

# Try to import x402 client
try:
    from tools.x402_client import X402DemandClient, X402_SDK_AVAILABLE
except ImportError:
    X402_SDK_AVAILABLE = False
    X402DemandClient = None


class PartsSearchResult:
    """Result from a parts search query."""

    def __init__(
        self,
        part_number: str,
        name: str,
        manufacturer: str,
        description: str,
        category: str,
        price: Optional[float] = None,
        specifications: Optional[dict] = None,
        cad_available: bool = False,
        cad_url: Optional[str] = None,
        supplier_url: Optional[str] = None,
    ):
        self.part_number = part_number
        self.name = name
        self.manufacturer = manufacturer
        self.description = description
        self.category = category
        self.price = price
        self.specifications = specifications or {}
        self.cad_available = cad_available
        self.cad_url = cad_url
        self.supplier_url = supplier_url

    def to_dict(self) -> dict:
        return {
            "part_number": self.part_number,
            "name": self.name,
            "manufacturer": self.manufacturer,
            "description": self.description,
            "category": self.category,
            "price": self.price,
            "specifications": self.specifications,
            "cad_available": self.cad_available,
            "cad_url": self.cad_url,
            "supplier_url": self.supplier_url,
        }

    def __repr__(self):
        return f"<Part {self.part_number}: {self.name} by {self.manufacturer}>"


class PartsSearchTool:
    """
    Tool for searching parts catalogs and purchasing CAD data via x402.

    This tool can be used by the CAD agent during chat to:
    1. Search for parts matching specifications
    2. Get detailed part information
    3. Download CAD models (paid via x402 if required)
    """

    def __init__(
        self,
        private_key: Optional[str] = None,
        backend_url: Optional[str] = None,
    ):
        """
        Initialize the parts search tool.

        Args:
            private_key: EVM private key for x402 payments.
            backend_url: Backend API URL for parts endpoint.
        """
        self.private_key = private_key or os.getenv("X402_AGENT_PRIVATE_KEY")
        self.backend_url = backend_url or os.getenv("BACKEND_URL", "http://localhost:8080")
        self._x402_client: Optional[X402DemandClient] = None

    async def _get_x402_client(self) -> X402DemandClient:
        """Get or create x402 client for paid requests."""
        if not X402_SDK_AVAILABLE:
            raise ImportError("x402 SDK required for paid parts search. Run: pip install x402")
        if not self.private_key:
            raise ValueError("X402_AGENT_PRIVATE_KEY required for paid parts search")
        
        if self._x402_client is None:
            self._x402_client = X402DemandClient(self.private_key)
        return self._x402_client

    async def search(
        self,
        query: str,
        category: Optional[str] = None,
        manufacturer: Optional[str] = None,
        max_results: int = 10,
    ) -> List[PartsSearchResult]:
        """
        Search for parts matching the query.

        Args:
            query: Search query (e.g., "M3 socket head cap screw")
            category: Optional category filter (e.g., "fasteners", "bearings")
            manufacturer: Optional manufacturer filter
            max_results: Maximum number of results to return

        Returns:
            List of PartsSearchResult objects
        """
        results = []

        # Try to call backend API first
        try:
            async with httpx.AsyncClient() as client:
                params = {"query": query}
                if category:
                    params["category"] = category
                
                response = await client.get(
                    f"{self.backend_url}/api/parts/search",
                    params=params,
                    timeout=10.0
                )
                
                if response.status_code == 200:
                    data = response.json()
                    for part in data.get("results", []):
                        results.append(PartsSearchResult(
                            part_number=part.get("partNumber", ""),
                            name=part.get("name", ""),
                            manufacturer=part.get("manufacturer", ""),
                            description=part.get("name", ""),
                            category=part.get("category", ""),
                            price=part.get("priceUsd"),
                            cad_available=True,
                            cad_url=f"{self.backend_url}{part.get('cadUrl', '')}",
                        ))
                    logger.info(f"Backend search returned {len(results)} results")
                    return results[:max_results]
        except Exception as e:
            logger.warning(f"Backend parts search failed, using mock: {e}")

        # Fall back to mock search if backend unavailable
        mock_results = await self._mock_parts_search(query, category, manufacturer)
        results.extend(mock_results[:max_results])
        return results[:max_results]

    async def get_part_details(
        self,
        part_number: str,
        source_url: Optional[str] = None,
    ) -> Optional[dict]:
        """
        Get detailed information about a specific part.

        May require x402 payment for premium data.

        Args:
            part_number: The part number to look up
            source_url: Optional specific API URL to query

        Returns:
            Detailed part information dict, or None if not found
        """
        # For demo, return mock data
        return await self._mock_get_details(part_number)

    async def download_cad(
        self,
        part_number: str,
        cad_format: str = "step",
        cad_url: Optional[str] = None,
    ) -> Optional[dict]:
        """
        Download CAD model for a part via x402 payment.

        Args:
            part_number: The part number
            cad_format: CAD format (step, iges, stl)
            cad_url: Optional direct URL to CAD file

        Returns:
            Dict with CAD data and transaction info, or None if failed
        """
        # Build CAD URL from backend if not provided
        if not cad_url:
            cad_url = f"{self.backend_url}/api/parts/{part_number}/cad"
        
        # Use x402 client to download (handles payment automatically)
        try:
            async with await self._get_x402_client() as client:
                response = await client.get(cad_url)
                
                if response.status_code == 200:
                    # Payment succeeded, we have CAD data
                    data = response.json() if response.headers.get("content-type", "").startswith("application/json") else {"cadData": response.text}
                    tx_hash = response.headers.get("x-payment-response", "")
                    
                    logger.info(f"CAD download succeeded for {part_number}, tx: {tx_hash}")
                    return {
                        "success": True,
                        "part_number": part_number,
                        "transaction_hash": tx_hash,
                        "cad_data": data.get("cadData", data),
                    }
                elif response.status_code == 402:
                    logger.warning(f"Payment required for CAD: {part_number}")
                    return {"success": False, "error": "Payment required"}
                else:
                    logger.error(f"Failed to download CAD: {response.status_code}")
                    return {"success": False, "error": f"HTTP {response.status_code}"}
        except Exception as e:
            logger.error(f"x402 CAD download failed: {e}")
            return {"success": False, "error": str(e)}

    async def _mock_parts_search(
        self,
        query: str,
        category: Optional[str] = None,
        manufacturer: Optional[str] = None,
    ) -> List[PartsSearchResult]:
        """
        Mock parts search for development/demo.

        In production, this would be replaced with real API calls.
        """
        query_lower = query.lower()

        # Mock database of common parts
        mock_parts = [
            PartsSearchResult(
                part_number="91292A113",
                name="M3 x 10mm Socket Head Cap Screw",
                manufacturer="McMaster-Carr",
                description="Alloy steel socket head cap screw, black oxide finish",
                category="fasteners",
                price=0.15,
                specifications={
                    "thread_size": "M3",
                    "length": "10mm",
                    "material": "Alloy Steel",
                    "head_type": "Socket Head",
                    "drive": "Hex",
                },
                cad_available=True,
            ),
            PartsSearchResult(
                part_number="91290A115",
                name="M3 x 12mm Socket Head Cap Screw",
                manufacturer="McMaster-Carr",
                description="18-8 stainless steel socket head cap screw",
                category="fasteners",
                price=0.22,
                specifications={
                    "thread_size": "M3",
                    "length": "12mm",
                    "material": "18-8 Stainless Steel",
                    "head_type": "Socket Head",
                    "drive": "Hex",
                },
                cad_available=True,
            ),
            PartsSearchResult(
                part_number="60355K502",
                name="MR63ZZ Miniature Ball Bearing",
                manufacturer="McMaster-Carr",
                description="Shielded miniature ball bearing, 3mm ID x 6mm OD",
                category="bearings",
                price=2.50,
                specifications={
                    "inner_diameter": "3mm",
                    "outer_diameter": "6mm",
                    "width": "2.5mm",
                    "type": "Deep Groove Ball Bearing",
                    "shielding": "Double Shielded (ZZ)",
                },
                cad_available=True,
            ),
            PartsSearchResult(
                part_number="6384K421",
                name="NEMA 17 Stepper Motor",
                manufacturer="McMaster-Carr",
                description="1.8° step angle, 0.4 N-m holding torque",
                category="motors",
                price=25.00,
                specifications={
                    "step_angle": "1.8°",
                    "holding_torque": "0.4 N-m",
                    "voltage": "12V",
                    "current": "1.2A/phase",
                    "shaft_diameter": "5mm",
                },
                cad_available=True,
            ),
            PartsSearchResult(
                part_number="LM8UU",
                name="8mm Linear Ball Bearing",
                manufacturer="Generic",
                description="Linear motion ball bearing for 8mm shafts",
                category="bearings",
                price=1.50,
                specifications={
                    "inner_diameter": "8mm",
                    "outer_diameter": "15mm",
                    "length": "24mm",
                    "type": "Linear Ball Bearing",
                },
                cad_available=True,
            ),
        ]

        # Filter by query
        results = []
        for part in mock_parts:
            if (
                query_lower in part.name.lower()
                or query_lower in part.description.lower()
                or query_lower in part.part_number.lower()
            ):
                if category and category.lower() != part.category.lower():
                    continue
                if manufacturer and manufacturer.lower() not in part.manufacturer.lower():
                    continue
                results.append(part)

        return results

    async def _mock_get_details(self, part_number: str) -> Optional[dict]:
        """Mock get part details."""
        results = await self._mock_parts_search(part_number)
        if results:
            return results[0].to_dict()
        return None


# Tool definition for LLM function calling
PARTS_SEARCH_TOOL_DEFINITION = {
    "type": "function",
    "function": {
        "name": "search_parts",
        "description": (
            "Search for mechanical/electronic parts from suppliers. "
            "Use this to find standard components like screws, bearings, motors, "
            "and other parts. Can also download CAD models of parts (may require x402 payment)."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Search query, e.g., 'M3 socket head cap screw' or 'NEMA 17 motor'",
                },
                "category": {
                    "type": "string",
                    "description": "Optional category filter: fasteners, bearings, motors, electronics",
                    "enum": ["fasteners", "bearings", "motors", "electronics", "linear_motion"],
                },
                "max_results": {
                    "type": "integer",
                    "description": "Maximum number of results to return",
                    "default": 5,
                },
            },
            "required": ["query"],
        },
    },
}

DOWNLOAD_CAD_TOOL_DEFINITION = {
    "type": "function",
    "function": {
        "name": "download_part_cad",
        "description": (
            "Download CAD model (STEP file) for a specific part. "
            "This may require an x402 payment for premium CAD data."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "part_number": {
                    "type": "string",
                    "description": "The part number to download CAD for",
                },
                "format": {
                    "type": "string",
                    "description": "CAD format",
                    "enum": ["step", "iges", "stl"],
                    "default": "step",
                },
            },
            "required": ["part_number"],
        },
    },
}


async def handle_parts_search_tool_call(
    tool_name: str,
    arguments: dict,
    private_key: Optional[str] = None,
) -> dict:
    """
    Handle tool calls from the LLM for parts search.

    Args:
        tool_name: The tool being called (search_parts or download_part_cad)
        arguments: Arguments from the LLM
        private_key: Optional x402 private key for payments

    Returns:
        Dict with the tool result
    """
    tool = PartsSearchTool(private_key=private_key)

    if tool_name == "search_parts":
        results = await tool.search(
            query=arguments.get("query", ""),
            category=arguments.get("category"),
            max_results=arguments.get("max_results", 5),
        )
        return {
            "success": True,
            "results": [r.to_dict() for r in results],
            "count": len(results),
        }

    elif tool_name == "download_part_cad":
        result = await tool.download_cad(
            part_number=arguments.get("part_number", ""),
            cad_format=arguments.get("format", "step"),
        )
        if result and result.get("success"):
            return {
                "success": True,
                "message": f"CAD downloaded for {arguments.get('part_number')}",
                "transaction_hash": result.get("transaction_hash", ""),
                "cad_data": result.get("cad_data"),
            }
        else:
            return {
                "success": False,
                "message": result.get("error", "CAD not available or payment failed") if result else "CAD not available",
            }

    return {"success": False, "error": f"Unknown tool: {tool_name}"}


if __name__ == "__main__":
    import asyncio

    async def demo():
        tool = PartsSearchTool()

        print("Searching for 'M3 screw'...")
        results = await tool.search("M3 screw")
        for r in results:
            print(f"  {r}")

        print("\nSearching for 'bearing'...")
        results = await tool.search("bearing")
        for r in results:
            print(f"  {r}")

    asyncio.run(demo())
