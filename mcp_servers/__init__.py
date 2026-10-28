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

__all__ = [
    "LocationClient",
    "location_client",
    "OSMMCPClient",
    "osm_location_client",
]
