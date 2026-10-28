import math
from typing import Optional, Dict, Any
from models.schemas import DistanceResult

EARTH_RADIUS_KM = 6371.0

def haversine_distance(
    lat1: float,
    lon1: float,
    lat2: float,
    lon2: float
) -> float:
    """Calculates great-circle distance between two points in km."""
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)

    a = (math.sin(delta_phi / 2.0) ** 2 +
         math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2.0) ** 2)
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
    return round(EARTH_RADIUS_KM * c, 2)


def calculate_distance(
    origin_lat: Optional[float],
    origin_lon: Optional[float],
    dest_lat: Optional[float],
    dest_lon: Optional[float],
    origin_name: str = "Origin",
    dest_name: str = "Destination"
) -> Dict[str, Any]:
    """
    Computes straight-line distance with explicit coordinate verification.
    Does NOT fabricate driving distance.
    """
    if origin_lat is None or origin_lon is None:
        return {
            "success": False,
            "error": f"Missing coordinates for {origin_name} ({origin_lat}, {origin_lon})",
            "distance_km": None,
            "distance_type": "unverified",
            "source": "distance_calculator"
        }

    if dest_lat is None or dest_lon is None:
        return {
            "success": False,
            "error": f"Missing coordinates for {dest_name} ({dest_lat}, {dest_lon})",
            "distance_km": None,
            "distance_type": "unverified",
            "source": "distance_calculator"
        }

    # Validate coordinate ranges
    if not (-90.0 <= origin_lat <= 90.0 and -180.0 <= origin_lon <= 180.0):
        return {
            "success": False,
            "error": f"Invalid coordinate range for {origin_name}: ({origin_lat}, {origin_lon})",
            "distance_km": None
        }

    if not (-90.0 <= dest_lat <= 90.0 and -180.0 <= dest_lon <= 180.0):
        return {
            "success": False,
            "error": f"Invalid coordinate range for {dest_name}: ({dest_lat}, {dest_lon})",
            "distance_km": None
        }

    distance = haversine_distance(origin_lat, origin_lon, dest_lat, dest_lon)
    return {
        "success": True,
        "origin": origin_name,
        "destination": dest_name,
        "distance_km": distance,
        "distance_type": "haversine_straight_line",
        "source": "haversine_calculator",
        "details": f"Straight-line distance of {distance} km between {origin_name} and {dest_name}"
    }
