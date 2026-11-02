import pytest
import json
from tools.budget_filter import filter_by_budget
from tools.amenity_checker import check_amenities
from tools.distance_calculator import calculate_distance, haversine_distance
from tools.pg_comparator import compare_pgs
from tools.pg_ranker import rank_pgs
from mcp_servers.location_client import location_client
from mcp_servers.pg_client import pg_client

def test_filter_by_budget_exact_boundary():
    # pg_ahm_003 has monthly_rent = 8000
    res = filter_by_budget(max_rent=8000)
    assert res["success"] is True
    ids = [p["id"] for p in res["matching_pgs"]]
    assert "pg_ahm_003" in ids
    for p in res["matching_pgs"]:
        assert p["monthly_rent"] <= 8000

def test_filter_by_budget_invalid():
    res = filter_by_budget(max_rent=-100)
    assert res["success"] is False
    assert "greater than zero" in res["error"]

def test_check_amenities_present():
    res = check_amenities(pg_input=["pg_ahm_001"], required_amenities=["Wi-Fi", "Food"])
    assert res["success"] is True
    assert len(res["matching_pgs"]) == 1

def test_check_amenities_missing_mandatory():
    # pg_ahm_006 has ["Wi-Fi", "Housekeeping", "CCTV", "Study Table"] - NO Food!
    res = check_amenities(pg_input=["pg_ahm_006"], required_amenities=["Wi-Fi", "Food"])
    assert res["success"] is True
    assert len(res["matching_pgs"]) == 0
    assert "pg_ahm_006" in res["missing_breakdown"]
    assert "food" in res["missing_breakdown"]["pg_ahm_006"]

def test_calculate_distance_valid():
    # Distance between Navrangpura (23.0373, 72.5532) and LD College (23.0338, 72.5463)
    res = calculate_distance(23.0373, 72.5532, 23.0338, 72.5463, "Navrangpura", "LD College")
    assert res["success"] is True
    assert res["distance_type"] == "haversine_straight_line"
    assert 0.5 <= res["distance_km"] <= 1.5

def test_calculate_distance_missing_coordinates():
    res = calculate_distance(None, None, 23.0338, 72.5463)
    assert res["success"] is False
    assert res["distance_km"] is None
    assert "Missing coordinates" in res["error"]

def test_calculate_distance_invalid_range():
    res = calculate_distance(999.0, 72.0, 23.0, 72.0)
    assert res["success"] is False
    assert "Invalid coordinate range" in res["error"]

def test_compare_pgs_valid():
    res = compare_pgs(["pg_ahm_001", "pg_ahm_002"])
    assert res["success"] is True
    assert res["total_compared"] == 2
    assert "highlights" in res
    assert res["highlights"]["lowest_rent"]["id"] == "pg_ahm_002"

def test_compare_pgs_empty():
    res = compare_pgs([])
    assert res["success"] is False
    assert "At least one PG ID" in res["error"]

def test_rank_pgs_strict_distance_excludes_missing_gps():
    """Fix 5 Blocker: Strict distance limit rejects PGs with unrecorded GPS coordinates."""
    # pg_ahm_012 has latitude=None, longitude=None
    res = rank_pgs(["pg_ahm_012"], dest_lat=23.0338, dest_lon=72.5463, max_distance_km=1.0)
    assert res["success"] is True
    ranked_ids = [p["id"] for p in res["ranked_pgs"]]
    assert "pg_ahm_012" not in ranked_ids
    excluded_ids = [e["id"] for e in res["excluded_by_distance"]]
    assert "pg_ahm_012" in excluded_ids

def test_pg_mcp_client_tool_discovery():
    """Fix 1 Blocker: Test dynamic tool discovery from custom FastMCP server."""
    tools = pg_client.list_tools()
    assert len(tools) >= 7
    tool_names = [t["name"] for t in tools]
    assert "search_pgs" in tool_names
    assert "filter_by_budget" in tool_names
    assert "check_amenities" in tool_names
    assert "rank_pgs" in tool_names

def test_pg_mcp_client_call_tool():
    """Fix 1 Blocker: Test executing search_pgs through the custom MCP client."""
    raw_res = pg_client.call_tool("search_pgs", {"city": "Ahmedabad", "gender": "girls"})
    parsed = json.loads(raw_res)
    assert parsed["success"] is True
    assert parsed["count"] >= 5
    for p in parsed["results"]:
        assert p["gender"] in ["girls", "co-ed"]

def test_geocoding_known_landmark():
    res = location_client.geocode("LD College of Engineering, Ahmedabad")
    assert res["success"] is True
    assert abs(res["latitude"] - 23.0338) < 0.05
    assert abs(res["longitude"] - 72.5463) < 0.05

def test_geocoding_empty():
    res = location_client.geocode("")
    assert res["success"] is False
    assert res["coordinates"] is None
