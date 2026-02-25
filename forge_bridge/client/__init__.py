"""
forge-bridge client.

Two clients, same capabilities:

    SyncClient   — blocking API, safe for Flame hooks and scripts
    AsyncClient  — async/await API, for MCP server and async contexts
"""

from forge_bridge.client.async_client import (
    AsyncClient,
    ClientError,
    ConnectionError,
    ServerError,
    TimeoutError,
)
from forge_bridge.client.sync_client import SyncClient

__all__ = [
    "AsyncClient", "SyncClient",
    "ClientError", "ServerError", "ConnectionError", "TimeoutError",
]
