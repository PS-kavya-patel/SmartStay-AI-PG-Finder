"""
Model Context Protocol (MCP) Servers and Clients Package.
Exposes MCP clients and server entrypoints for SmartStay.
"""

from mcp_servers.location_client import (
    LocationClient,
    location_client,
    OSMMCPClient,
    osm_location_client,
)
from mcp_servers.pg_client import (
    PGClient,
    pg_client,
)

__all__ = [
    "LocationClient",
    "location_client",
    "OSMMCPClient",
    "osm_location_client",
    "PGClient",
    "pg_client",
]
