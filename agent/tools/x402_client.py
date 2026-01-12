"""
x402 Demand-Side Payment Client

Enables the agent to autonomously pay for x402-protected external services.
Uses the Coinbase x402 Python SDK with httpx for async HTTP requests.

How to create an agent wallet:
    from eth_account import Account
    acct = Account.create()
    print(f"Address: {acct.address}")
    print(f"Private Key: {acct.key.hex()}")

Then fund with test USDC on Base Sepolia: https://faucet.cdp.coinbase.com/
"""

from typing import Optional, Any
import os
import logging
import httpx
from eth_account import Account

logger = logging.getLogger(__name__)

# Try to import x402 SDK - may not be installed yet
try:
    from x402.clients.httpx import x402HttpxClient, x402_payment_hooks
    X402_SDK_AVAILABLE = True
except ImportError:
    X402_SDK_AVAILABLE = False
    x402HttpxClient = None
    x402_payment_hooks = None
    logger.warning("x402 SDK not installed. Run: pip install x402")


class X402DemandClient:
    """
    Client for making requests to x402-protected endpoints.
    Automatically handles 402 responses and payment signing.

    Example usage:
        async with X402DemandClient() as client:
            response = await client.get("https://api.example.com/paid-endpoint")
            data = response.json()
    """

    def __init__(self, private_key: Optional[str] = None):
        """
        Initialize the x402 demand client.

        Args:
            private_key: EVM private key for signing payments.
                        Defaults to X402_AGENT_PRIVATE_KEY env var.
        
        Raises:
            ValueError: If no private key is provided and env var is not set.
            ImportError: If x402 SDK is not installed.
        """
        if not X402_SDK_AVAILABLE:
            raise ImportError(
                "x402 SDK not installed. Run: pip install x402 eth-account"
            )

        key = private_key or os.getenv("X402_AGENT_PRIVATE_KEY")
        if not key:
            raise ValueError(
                "X402_AGENT_PRIVATE_KEY environment variable required. "
                "Create a wallet with: "
                "from eth_account import Account; acct = Account.create(); print(acct.key.hex())"
            )

        # Ensure key has 0x prefix
        if not key.startswith("0x"):
            key = "0x" + key

        self.account = Account.from_key(key)
        self.address = self.account.address
        self._client: Optional[x402HttpxClient] = None

        logger.info(f"x402 client initialized with wallet: {self.address}")

    async def __aenter__(self):
        """Async context manager entry."""
        self._client = x402HttpxClient(account=self.account)
        await self._client.__aenter__()
        return self

    async def __aexit__(self, *args):
        """Async context manager exit."""
        if self._client:
            await self._client.__aexit__(*args)

    async def get(self, url: str, **kwargs) -> httpx.Response:
        """
        Make a GET request, automatically handling x402 payments.

        If the server returns 402 Payment Required, the client will:
        1. Parse the payment requirements
        2. Sign the payment with the agent wallet
        3. Retry the request with the payment header

        Args:
            url: The URL to request
            **kwargs: Additional arguments passed to httpx.get()

        Returns:
            httpx.Response: The response from the server
        """
        if not self._client:
            raise RuntimeError("Client not initialized. Use 'async with' context.")
        return await self._client.get(url, **kwargs)

    async def post(self, url: str, **kwargs) -> httpx.Response:
        """
        Make a POST request, automatically handling x402 payments.

        Args:
            url: The URL to request
            **kwargs: Additional arguments passed to httpx.post()

        Returns:
            httpx.Response: The response from the server
        """
        if not self._client:
            raise RuntimeError("Client not initialized. Use 'async with' context.")
        return await self._client.post(url, **kwargs)

    async def request(self, method: str, url: str, **kwargs) -> httpx.Response:
        """
        Make a request with any HTTP method, handling x402 payments.

        Args:
            method: HTTP method (GET, POST, PUT, DELETE, etc.)
            url: The URL to request
            **kwargs: Additional arguments passed to httpx.request()

        Returns:
            httpx.Response: The response from the server
        """
        if not self._client:
            raise RuntimeError("Client not initialized. Use 'async with' context.")
        return await self._client.request(method, url, **kwargs)


async def create_x402_client(private_key: Optional[str] = None) -> X402DemandClient:
    """
    Factory function to create and initialize an x402 client.

    Args:
        private_key: Optional EVM private key. Defaults to env var.

    Returns:
        Initialized X402DemandClient (must be used with async with)
    """
    return X402DemandClient(private_key)


def generate_wallet() -> dict:
    """
    Generate a new EVM wallet for the agent.

    Returns:
        dict with 'address' and 'private_key' fields

    Example:
        wallet = generate_wallet()
        print(f"Address: {wallet['address']}")
        print(f"Private Key: {wallet['private_key']}")
        # Fund at: https://faucet.cdp.coinbase.com/
    """
    acct = Account.create()
    return {
        "address": acct.address,
        "private_key": acct.key.hex(),
    }


if __name__ == "__main__":
    # Utility: Generate a new wallet when run directly
    print("Generating new agent wallet...")
    wallet = generate_wallet()
    print(f"\nAddress: {wallet['address']}")
    print(f"Private Key: {wallet['private_key']}")
    print("\nTo use this wallet:")
    print(f"1. Add to .env: X402_AGENT_PRIVATE_KEY={wallet['private_key']}")
    print("2. Fund with test USDC: https://faucet.cdp.coinbase.com/")
