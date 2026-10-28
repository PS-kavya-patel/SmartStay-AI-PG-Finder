import json
import logging
import subprocess
import re
from typing import Optional, Dict, Any
from mcp_servers.location_server import (
    resolve_location_coordinates,
    geocode_location as _srv_geocode,
    get_distance_and_route_info as _srv_distance
)

logger = logging.getLogger(__name__)

class OSMMCPClient:
    """
    Client for interacting with the pre-built OpenStreetMap MCP server (osm-mcp).
    Uses stdio JSON-RPC 2.0 communication with automatic fallback to local landmark engine.
    """

    def __init__(self, timeout: float = 5.0):
        self.timeout = timeout

    def _call_mcp_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Invokes a tool on the pre-built osm-mcp server via standard I/O."""
        try:
            proc = subprocess.Popen(
                ["npx", "-y", "osm-mcp"],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                shell=True
            )

            # 1. MCP initialize handshake
            init_payload = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {},
                    "clientInfo": {"name": "smartstay-agent", "version": "1.0.0"}
                }
            }
            proc.stdin.write(json.dumps(init_payload) + "\n")
            proc.stdin.flush()
            proc.stdout.readline()

            # 2. notifications/initialized
            proc.stdin.write(json.dumps({"jsonrpc": "2.0", "method": "notifications/initialized"}) + "\n")
            proc.stdin.flush()

            # 3. tools/call
            call_payload = {
                "jsonrpc": "2.0",
                "id": 2,
                "method": "tools/call",
                "params": {"name": tool_name, "arguments": arguments}
            }
            proc.stdin.write(json.dumps(call_payload) + "\n")
            proc.stdin.flush()

            resp_line = proc.stdout.readline()
            proc.terminate()

            if not resp_line:
                return None

            data = json.loads(resp_line)
            content_list = data.get("result", {}).get("content", [])
            if not content_list:
                return None

            text = content_list[0].get("text", "")
            match = re.search(r"\{.*\}", text, re.DOTALL)
            if match:
                return json.loads(match.group(0))
            return None
        except Exception as e:
            logger.debug(f"Pre-built osm-mcp call error: {e}. Falling back to internal engine.")
            return None

    def geocode(self, location_name: str) -> Dict[str, Any]:
        """
        Geocodes a destination using pre-built osm-mcp server with fallback.
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

        # Try pre-built OSM MCP server first
        osm_res = self._call_mcp_tool("geocode", {"query": search_term})
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

        # Fallback to local landmark catalog
        try:
            raw_res = _srv_geocode(location_name)
            return json.loads(raw_res)
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
        Calculates straight-line or route distance using osm-mcp with fallback.
        """
        # If coordinates provided, attempt osm-mcp straight_line_distance
        if origin_lat is not None and origin_lon is not None and dest_lat is not None and dest_lon is not None:
            from_pt = f"{origin_lat},{origin_lon}"
            to_pt = f"{dest_lat},{dest_lon}"
            dist_res = self._call_mcp_tool("straight_line_distance", {"from": from_pt, "to": to_pt})
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

        # Fallback to internal distance engine
        try:
            raw_res = _srv_distance(
                origin_name=origin_name,
                destination_name=destination_name,
                origin_lat=origin_lat,
                origin_lon=origin_lon,
                dest_lat=dest_lat,
                dest_lon=dest_lon
            )
            return json.loads(raw_res)
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "distance_km": None
            }

# Singleton instances
location_client = OSMMCPClient()
osm_location_client = location_client
