import sys
import json
from pathlib import Path
from typing import List, Optional, Dict, Any

# Ensure workspace root is in sys.path
BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from mcp.server.fastmcp import FastMCP
from tools.pg_search import search_pgs as _search_pgs, get_pg_details as _get_pg_details
from tools.budget_filter import filter_by_budget as _filter_by_budget
from tools.amenity_checker import check_amenities as _check_amenities
from tools.distance_calculator import calculate_distance as _calculate_distance
from tools.pg_comparator import compare_pgs as _compare_pgs
from tools.pg_ranker import rank_pgs as _rank_pgs

# Initialize FastMCP Server
mcp = FastMCP("SmartStay-PG-Server")

@mcp.tool()
def search_pgs(
    city: Optional[str] = "Ahmedabad",
    area: Optional[str] = None,
    gender: Optional[str] = None,
    room_type: Optional[str] = None
) -> str:
    """
    Search PG listings in the database matching city, neighborhood area, gender preference ('girls', 'boys', 'co-ed'), or room type.
    Returns a JSON string containing matching PG listings.
    """
    results = _search_pgs(city=city, area=area, gender=gender, room_type=room_type)
    return json.dumps({
        "success": True,
        "count": len(results),
        "results": results
    }, indent=2)


@mcp.tool()
def filter_by_budget(
    pg_ids: Optional[List[str]] = None,
    max_rent: float = 0.0
) -> str:
    """
    Filter PG listings by maximum monthly budget in INR (monthly_rent <= max_rent).
    Pass pg_ids to filter an existing candidate set, or leave empty to filter all PGs.
    """
    res = _filter_by_budget(pg_input=pg_ids, max_rent=max_rent)
    return json.dumps(res, indent=2)


@mcp.tool()
def check_amenities(
    pg_ids: Optional[List[str]] = None,
    required_amenities: Optional[List[str]] = None
) -> str:
    """
    Verify whether mandatory amenities (e.g. ['Wi-Fi', 'Food', 'AC', 'Laundry']) are present in the PG listings.
    Returns only listings satisfying all required amenities, along with a missing breakdown.
    """
    res = _check_amenities(pg_input=pg_ids, required_amenities=required_amenities or [])
    return json.dumps(res, indent=2)


@mcp.tool()
def calculate_distance(
    origin_lat: Optional[float] = None,
    origin_lon: Optional[float] = None,
    dest_lat: Optional[float] = None,
    dest_lon: Optional[float] = None,
    origin_name: str = "Origin",
    dest_name: str = "Destination"
) -> str:
    """
    Calculate straight-line distance in kilometers between two sets of coordinates using verified Haversine formula.
    Safe error reporting if coordinates are missing.
    """
    res = _calculate_distance(
        origin_lat=origin_lat,
        origin_lon=origin_lon,
        dest_lat=dest_lat,
        dest_lon=dest_lon,
        origin_name=origin_name,
        dest_name=dest_name
    )
    return json.dumps(res, indent=2)


@mcp.tool()
def compare_pgs(pg_ids: List[str]) -> str:
    """
    Compare 2 to 4 candidate PGs side-by-side on rent, deposit, amenities, room type, rating, and standout highlights.
    """
    res = _compare_pgs(pg_ids=pg_ids)
    return json.dumps(res, indent=2)


@mcp.tool()
def rank_pgs(
    pg_ids: List[str],
    max_budget: Optional[float] = None,
    dest_lat: Optional[float] = None,
    dest_lon: Optional[float] = None,
    max_distance_km: Optional[float] = None,
    required_amenities: Optional[List[str]] = None
) -> str:
    """
    Rank PG listings using transparent multi-criteria formula (budget savings, proximity, amenity coverage, user ratings).
    Returns ranked listings with score breakdown and match reasons.
    """
    res = _rank_pgs(
        pg_ids=pg_ids,
        max_budget=max_budget,
        dest_lat=dest_lat,
        dest_lon=dest_lon,
        max_distance_km=max_distance_km,
        required_amenities=required_amenities
    )
    return json.dumps(res, indent=2)


@mcp.tool()
def get_pg_details(pg_id: str) -> str:
    """
    Retrieve full verified details for a specific PG listing by its unique ID.
    """
    details = _get_pg_details(pg_id)
    if details:
        return json.dumps({"success": True, "details": details}, indent=2)
    return json.dumps({"success": False, "error": f"PG with ID '{pg_id}' not found."}, indent=2)


if __name__ == "__main__":
    mcp.run(transport="stdio")
