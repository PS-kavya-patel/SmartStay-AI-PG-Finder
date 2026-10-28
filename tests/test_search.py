import pytest
from tools.pg_search import search_pgs, get_pg_details
from database.data_service import data_service

def test_data_service_loads_records():
    listings = data_service.load_all_pgs()
    assert len(listings) >= 10
    for pg in listings:
        assert pg.id
        assert pg.name
        assert pg.monthly_rent > 0
        assert pg.city == "Ahmedabad"

def test_search_girls_pgs():
    results = search_pgs(city="Ahmedabad", gender="girls")
    assert len(results) > 0
    for pg in results:
        assert pg["gender"] in ["girls", "co-ed"]

def test_search_boys_pgs():
    results = search_pgs(city="Ahmedabad", gender="boys")
    assert len(results) > 0
    for pg in results:
        assert pg["gender"] in ["boys", "co-ed"]

def test_search_by_area():
    results = search_pgs(city="Ahmedabad", area="Navrangpura")
    assert len(results) > 0
    for pg in results:
        assert "navrangpura" in pg["area"].lower()

def test_search_no_matching_pgs():
    results = search_pgs(city="NonExistentCity999")
    assert len(results) == 0

def test_get_pg_details_valid():
    details = get_pg_details("pg_ahm_001")
    assert details is not None
    assert details["name"] == "Shree Shanti Girls PG"
    assert details["monthly_rent"] == 7500

def test_get_pg_details_invalid():
    details = get_pg_details("invalid_id_9999")
    assert details is None
