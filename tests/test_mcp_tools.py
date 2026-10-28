import pytest
import json
from tools.budget_filter import filter_by_budget
from tools.amenity_checker import check_amenities
from tools.distance_calculator import calculate_distance, haversine_distance
from tools.pg_comparator import compare_pgs
from mcp_servers.location_server import resolve_location_coordinates

def test_filter_by_budget_exact_boundary():
    # pg_ahm_003 has monthly_rent = 8000
    res = filter_by_budget(max_rent=8000)
    assert res["success"] is True
    ids = [p["id"] for p in res["matching_pgs"]]
    assert "pg_ahm_003" in ids
    # Any PG with rent > 8000 should not be present
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

def test_geocoding_known_landmark():
    res = resolve_location_coordinates("LD College of Engineering, Ahmedabad")
    assert res["success"] is True
    assert abs(res["latitude"] - 23.0338) < 0.01
    assert abs(res["longitude"] - 72.5463) < 0.01

def test_geocoding_empty():
    res = resolve_location_coordinates("")
    assert res["success"] is False
    assert res["coordinates"] is None
