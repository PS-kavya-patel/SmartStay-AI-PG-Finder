import json
import logging
from typing import Optional, Dict, Any
from mcp_servers.location_server import (
    resolve_location_coordinates,
    geocode_location as _srv_geocode,
    get_distance_and_route_info as _srv_distance
)

logger = logging.getLogger(__name__)

class LocationClient:
    """
    Client interface for interacting with location tools.
    Provides verified geocoding and distance calculations with fail-safes.
    """

    def geocode(self, location_name: str) -> Dict[str, Any]:
        """Geocodes a destination into coordinates with verification."""
        try:
            raw_res = _srv_geocode(location_name)
            return json.loads(raw_res)
        except Exception as e:
            logger.error(f"Error calling geocode tool: {e}")
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
        """Calculates distance between locations, tagging distance type."""
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
            logger.error(f"Error calling distance tool: {e}")
            return {
                "success": False,
                "error": str(e),
                "distance_km": None
            }


# Shared client instance
location_client = LocationClient()
