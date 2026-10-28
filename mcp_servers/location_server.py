import sys
import json
import logging
from pathlib import Path
from typing import Optional, Dict, Any

BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from mcp.server.fastmcp import FastMCP
from tools.distance_calculator import calculate_distance as _calc_dist

logger = logging.getLogger(__name__)

# FastMCP Location Server
location_mcp = FastMCP("PreBuilt-Location-MCP")

# High-accuracy landmark database for Ahmedabad and education hubs
KNOWN_LANDMARKS = {
    "ld college of engineering": {"lat": 23.0338, "lon": 72.5463, "display_name": "L.D. College of Engineering, Navrangpura, Ahmedabad"},
    "ld college": {"lat": 23.0338, "lon": 72.5463, "display_name": "L.D. College of Engineering, Navrangpura, Ahmedabad"},
    "gujarat university": {"lat": 23.0375, "lon": 72.5458, "display_name": "Gujarat University, Navrangpura, Ahmedabad"},
    "iim ahmedabad": {"lat": 23.0315, "lon": 72.5312, "display_name": "Indian Institute of Management (IIM-A), Vastrapur, Ahmedabad"},
    "iima": {"lat": 23.0315, "lon": 72.5312, "display_name": "Indian Institute of Management (IIM-A), Vastrapur, Ahmedabad"},
    "cept university": {"lat": 23.0380, "lon": 72.5480, "display_name": "CEPT University, Navrangpura, Ahmedabad"},
    "st. xavier's college": {"lat": 23.0322, "lon": 72.5567, "display_name": "St. Xavier's College, Navrangpura, Ahmedabad"},
    "nirma university": {"lat": 23.1287, "lon": 72.5435, "display_name": "Nirma University, SG Highway, Ahmedabad"},
    "navrangpura": {"lat": 23.0373, "lon": 72.5532, "display_name": "Navrangpura, Ahmedabad"},
    "vastrapur": {"lat": 23.0350, "lon": 72.5293, "display_name": "Vastrapur, Ahmedabad"},
    "bodakdev": {"lat": 23.0425, "lon": 72.5110, "display_name": "Bodakdev, Ahmedabad"},
    "satellite": {"lat": 23.0280, "lon": 72.5190, "display_name": "Satellite, Ahmedabad"},
    "paldi": {"lat": 23.0125, "lon": 72.5620, "display_name": "Paldi, Ahmedabad"}
}

def resolve_location_coordinates(place_query: str) -> Dict[str, Any]:
    """
    Resolves place query to verified coordinates.
    Attempts online geocoding via Nominatim with graceful fallback to landmark directory.
    """
    if not place_query or not place_query.strip():
        return {
            "success": False,
            "error": "Empty location query provided",
            "place": place_query,
            "coordinates": None
        }

    query_clean = place_query.strip().lower()

    # 1. Check known landmarks first for immediate high-accuracy match
    for landmark_key, landmark_info in KNOWN_LANDMARKS.items():
        if landmark_key in query_clean:
            return {
                "success": True,
                "place": place_query,
                "display_name": landmark_info["display_name"],
                "latitude": landmark_info["lat"],
                "longitude": landmark_info["lon"],
                "source": "verified_landmark_catalog"
            }

    # 2. Try online geocoding via geopy Nominatim (with short timeout)
    try:
        from geopy.geocoders import Nominatim
        geolocator = Nominatim(user_agent="smartstay_mcp_location", timeout=2.5)
        # Ensure query mentions city if not already specified
        search_term = place_query if "ahmedabad" in query_clean else f"{place_query}, Ahmedabad, Gujarat, India"
        loc = geolocator.geocode(search_term)
        if loc:
            return {
                "success": True,
                "place": place_query,
                "display_name": loc.address,
                "latitude": round(loc.latitude, 4),
                "longitude": round(loc.longitude, 4),
                "source": "osm_nominatim_geocoding"
            }
    except Exception as e:
        logger.warning(f"Online geocoding exception: {e}")

    return {
        "success": False,
        "error": f"Could not verify coordinates for '{place_query}'. Coordinates unavailable.",
        "place": place_query,
        "coordinates": None,
        "source": "location_service"
    }


@location_mcp.tool()
def geocode_location(location_name: str) -> str:
    """
    Geocode a college, office, landmark, or neighborhood name into verified latitude and longitude coordinates.
    Returns latitude, longitude, and verification source.
    """
    res = resolve_location_coordinates(location_name)
    return json.dumps(res, indent=2)


@location_mcp.tool()
def get_distance_and_route_info(
    origin_name: str,
    destination_name: str,
    origin_lat: Optional[float] = None,
    origin_lon: Optional[float] = None,
    dest_lat: Optional[float] = None,
    dest_lon: Optional[float] = None
) -> str:
    """
    Calculate straight-line distance between two places, resolving coordinates if they are not passed.
    Explicitly tags the distance type as 'haversine_straight_line' to avoid misrepresenting as driving route.
    """
    # Resolve origin coords if missing
    if origin_lat is None or origin_lon is None:
        origin_geo = resolve_location_coordinates(origin_name)
        if origin_geo.get("success"):
            origin_lat = origin_geo["latitude"]
            origin_lon = origin_geo["longitude"]

    # Resolve dest coords if missing
    if dest_lat is None or dest_lon is None:
        dest_geo = resolve_location_coordinates(destination_name)
        if dest_geo.get("success"):
            dest_lat = dest_geo["latitude"]
            dest_lon = dest_geo["longitude"]

    calc_res = _calc_dist(
        origin_lat=origin_lat,
        origin_lon=origin_lon,
        dest_lat=dest_lat,
        dest_lon=dest_lon,
        origin_name=origin_name,
        dest_name=destination_name
    )
    return json.dumps(calc_res, indent=2)


if __name__ == "__main__":
    location_mcp.run(transport="stdio")
