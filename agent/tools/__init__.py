# Tools package for CAD Agent

# x402 demand-side payment client
try:
    from .x402_client import X402DemandClient, generate_wallet, X402_SDK_AVAILABLE
except ImportError:
    X402DemandClient = None
    generate_wallet = None
    X402_SDK_AVAILABLE = False

# Parts search with x402 payment integration
try:
    from .parts_search import (
        PartsSearchTool,
        PartsSearchResult,
        PARTS_SEARCH_TOOL_DEFINITION,
        DOWNLOAD_CAD_TOOL_DEFINITION,
        handle_parts_search_tool_call,
    )
except ImportError:
    PartsSearchTool = None
    PartsSearchResult = None
    PARTS_SEARCH_TOOL_DEFINITION = None
    DOWNLOAD_CAD_TOOL_DEFINITION = None
    handle_parts_search_tool_call = None

__all__ = [
    # x402 client
    "X402DemandClient",
    "generate_wallet",
    "X402_SDK_AVAILABLE",
    # Parts search
    "PartsSearchTool",
    "PartsSearchResult",
    "PARTS_SEARCH_TOOL_DEFINITION",
    "DOWNLOAD_CAD_TOOL_DEFINITION",
    "handle_parts_search_tool_call",
]
