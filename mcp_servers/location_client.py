import json
import logging
import shutil
import re
import asyncio
import concurrent.futures
from typing import Optional, Dict, Any, List

# Official Model Context Protocol (MCP) Python Client SDK
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

# Local fallback services
from database.location_service import location_service
from tools.distance_calculator import calculate_distance as _calc_dist


logger = logging.getLogger(__name__)

class LocationClient:
    """
    Official MCP Client interface for interacting with the pre-built OpenStreetMap MCP server (osm-mcp).
    Communicates via official MCP Python SDK (stdio_client + ClientSession) with automatic fallback.
    """

    def __init__(self, timeout: float = 8.0):
        self.timeout = timeout
        self._command = shutil.which("npx") or "npx"

    def _get_server_params(self) -> StdioServerParameters:
        """Constructs StdioServerParameters for launching the pre-built osm-mcp server."""
        return StdioServerParameters(
            command=self._command,
            args=["-y", "osm-mcp"],
            env=None
        )

    async def list_tools_async(self) -> List[str]:
        """Discovers tools exposed by the pre-built osm-mcp server using the official MCP SDK."""
        server_params = self._get_server_params()
        async with stdio_client(server_params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                tools_result = await session.list_tools()
                return [t.name for t in tools_result.tools]

    def list_tools(self) -> List[str]:
        """Synchronous wrapper for discovering tools via official MCP SDK."""
        try:
            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
                return pool.submit(lambda: asyncio.run(self.list_tools_async())).result(timeout=self.timeout)
        except Exception as e:
            logger.debug(f"Could not list tools from osm-mcp: {e}")
            return ["geocode", "straight_line_distance", "route"]

    async def call_tool_async(self, tool_name: str, arguments: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Executes a tool on the pre-built osm-mcp server using the official MCP SDK sequence:
        stdio_client -> ClientSession -> session.initialize() -> session.call_tool()
        """
        server_params = self._get_server_params()
        async with stdio_client(server_params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                result = await session.call_tool(tool_name, arguments=arguments)
                if result.content:
                    text = result.content[0].text
                    match = re.search(r"\{.*\}", text, re.DOTALL)
                    if match:
                        return json.loads(match.group(0))
                    return {"raw": text}
                return None

    def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Synchronous runner for calling an MCP tool via the official SDK."""
        try:
            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
                return pool.submit(lambda: asyncio.run(self.call_tool_async(tool_name, arguments))).result(timeout=self.timeout)
        except Exception as e:
            logger.debug(f"Pre-built osm-mcp tool call failed ({tool_name}): {e}")
            return None

    def geocode(self, location_name: str) -> Dict[str, Any]:
        """
        Geocodes a destination using pre-built osm-mcp 'geocode' tool with verified fallback.
        """
        if not location_name or not location_name.strip():
            return {
                "success": False,
                "error": "Empty location query",
                "place": location_name,
                "coordinates": None
            }

        query = location_name.strip()
        search_term = query if "ahmedabad" in query.lower() else f"{query}, Ahmedabad"

        # 1. Call pre-built osm-mcp server via official MCP ClientSession
        osm_res = self.call_tool("geocode", {"query": search_term})
        if osm_res and isinstance(osm_res, dict) and "results" in osm_res:
            results = osm_res.get("results", [])
            if results and len(results) > 0:
                top = results[0]
                return {
                    "success": True,
                    "place": location_name,
                    "display_name": top.get("label", location_name),
                    "latitude": round(float(top["lat"]), 4),
                    "longitude": round(float(top["lon"]), 4),
                    "source": "osm_mcp_prebuilt"
                }

        # 2. Seamless fallback to local verified landmark database
        try:
            place_info = location_service.resolve_place_coordinates(location_name)
            if place_info:
                return {
                    "success": True,
                    "place": location_name,
                    "display_name": place_info["display_name"],
                    "latitude": round(place_info["latitude"], 4),
                    "longitude": round(place_info["longitude"], 4),
                    "source": "verified_landmark_catalog"
                }
            return {
                "success": False,
                "error": f"Coordinates unavailable for '{location_name}'",
                "place": location_name,
                "coordinates": None
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "place": location_name,
                "coordinates": None
            }

    def compute_distance(
        self,
        origin_name: str,
        destination_name: str,
        origin_lat: Optional[float] = None,
        origin_lon: Optional[float] = None,
        dest_lat: Optional[float] = None,
        dest_lon: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        Calculates straight-line or route distance using pre-built osm-mcp with fallback.
        """
        # If coordinates provided, call osm-mcp 'straight_line_distance' via official SDK
        if origin_lat is not None and origin_lon is not None and dest_lat is not None and dest_lon is not None:
            from_pt = f"{origin_lat},{origin_lon}"
            to_pt = f"{dest_lat},{dest_lon}"
            dist_res = self.call_tool("straight_line_distance", {"from": from_pt, "to": to_pt})
            if dist_res and "distance_m" in dist_res:
                dist_km = round(float(dist_res["distance_m"]) / 1000.0, 2)
                return {
                    "success": True,
                    "origin": origin_name,
                    "destination": destination_name,
                    "distance_km": dist_km,
                    "distance_type": "haversine_straight_line",
                    "source": "osm_mcp_prebuilt"
                }

        # Seamless fallback to internal distance engine
        try:
            if origin_lat is None or origin_lon is None:
                o_info = location_service.resolve_place_coordinates(origin_name)
                if o_info:
                    origin_lat, origin_lon = o_info["latitude"], o_info["longitude"]
            if dest_lat is None or dest_lon is None:
                d_info = location_service.resolve_place_coordinates(destination_name)
                if d_info:
                    dest_lat, dest_lon = d_info["latitude"], d_info["longitude"]

            return _calc_dist(
                origin_lat=origin_lat,
                origin_lon=origin_lon,
                dest_lat=dest_lat,
                dest_lon=dest_lon,
                origin_name=origin_name,
                dest_name=destination_name
            )
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "distance_km": None
            }

# Aliases and singleton instances
OSMMCPClient = LocationClient
location_client = LocationClient()
osm_location_client = location_client

__all__ = [
    "LocationClient",
    "OSMMCPClient",
    "location_client",
    "osm_location_client"
]
