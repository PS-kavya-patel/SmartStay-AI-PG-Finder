import pytest
from services.scoring_service import ScoringService
from tools.pg_ranker import rank_pgs
from database.data_service import data_service

def test_scoring_within_budget_and_close():
    pg = data_service.get_pg_by_id("pg_ahm_001")
    assert pg is not None
    scored = ScoringService.calculate_score(
        pg=pg,
        max_budget=8000,
        distance_km=0.8,
        desired_amenities=["Wi-Fi", "Food"]
    )
    assert 0 <= scored.final_score <= 100
    assert scored.score_breakdown["budget_score"] > 20
    assert scored.score_breakdown["distance_score"] == 30.0  # < 1km
    assert len(scored.match_reasons) > 0

def test_scoring_unverified_distance():
    pg = data_service.get_pg_by_id("pg_ahm_012")  # Missing GPS
    assert pg is not None
    scored = ScoringService.calculate_score(
        pg=pg,
        max_budget=8000,
        distance_km=None
    )
    assert scored.score_breakdown["distance_score"] == 15.0  # Neutral midpoint

def test_rank_pgs_excludes_over_distance():
    # Destination at LD College (23.0338, 72.5463)
    # Bodakdev PG (pg_ahm_005) is around 4.5 - 5 km away
    res = rank_pgs(
        pg_ids=["pg_ahm_001", "pg_ahm_005"],
        max_budget=15000,
        dest_lat=23.0338,
        dest_lon=72.5463,
        max_distance_km=2.0  # Limit 2 km
    )
    assert res["success"] is True
    ranked_ids = [r["id"] for r in res["ranked_pgs"]]
    assert "pg_ahm_001" in ranked_ids
    assert "pg_ahm_005" not in ranked_ids  # Should be excluded because > 2km
    excluded_ids = [e["id"] for e in res["excluded_by_distance"]]
    assert "pg_ahm_005" in excluded_ids
