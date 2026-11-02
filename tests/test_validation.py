import pytest
from services.validation_service import ValidationService
from models.schemas import PGSearchCriteria
from agents.reflection_agent import ReflectionAgent

def test_validation_passes_valid_recommendations():
    criteria = PGSearchCriteria(
        city="Ahmedabad",
        gender="girls",
        max_rent=8000,
        required_amenities=["Wi-Fi", "Food"]
    )
    val = ValidationService.validate_recommendations(
        recommended_pg_ids=["pg_ahm_001"],
        criteria=criteria,
        proposed_text="Recommended Shree Shanti Girls PG"
    )
    assert val.is_valid is True
    assert len(val.errors) == 0
    assert len(val.verified_items) > 0

def test_validation_fails_budget_violation():
    criteria = PGSearchCriteria(max_rent=7000)
    # pg_ahm_001 has rent 7500 > 7000
    val = ValidationService.validate_recommendations(
        recommended_pg_ids=["pg_ahm_001"],
        criteria=criteria
    )
    assert val.is_valid is False
    assert any("Budget violation" in e for e in val.errors)

def test_validation_fails_gender_violation():
    criteria = PGSearchCriteria(gender="girls")
    # pg_ahm_008 is boys PG
    val = ValidationService.validate_recommendations(
        recommended_pg_ids=["pg_ahm_008"],
        criteria=criteria
    )
    assert val.is_valid is False
    assert any("Gender restriction violation" in e for e in val.errors)

def test_validation_fails_missing_amenity():
    criteria = PGSearchCriteria(required_amenities=["Gym"])
    # pg_ahm_001 has no Gym
    val = ValidationService.validate_recommendations(
        recommended_pg_ids=["pg_ahm_001"],
        criteria=criteria
    )
    assert val.is_valid is False
    assert any("Amenity violation" in e for e in val.errors)

def test_validation_fails_ungrounded_pg_id():
    criteria = PGSearchCriteria(max_rent=10000)
    val = ValidationService.validate_recommendations(
        recommended_pg_ids=["fabricated_pg_999"],
        criteria=criteria
    )
    assert val.is_valid is False
    assert any("Grounding failure" in e for e in val.errors)

def test_validation_rejects_false_factual_claims():
    """Fix 2 Blocker: Verify that false rent (₹1) and invented swimming pool are rejected."""
    criteria = PGSearchCriteria(city="Ahmedabad", gender="girls", max_rent=8000)
    false_draft = "Shree Shanti Girls PG (pg_ahm_001) costs ₹1 per month and offers a swimming pool."
    val = ValidationService.validate_recommendations(
        recommended_pg_ids=["pg_ahm_001"],
        criteria=criteria,
        proposed_text=false_draft
    )
    assert val.is_valid is False
    # Check that both false rent and hallucinated swimming pool are flagged as errors
    assert any("Fact mismatch" in e and "₹1" in e for e in val.errors)
    assert any("Hallucination error" in e and "swimming pool" in e for e in val.errors)

def test_validation_rejects_rejected_pgs_in_text():
    """Fix 3 Blocker: Verify that mentioning an excluded PG in the proposed text fails validation."""
    criteria = PGSearchCriteria(city="Ahmedabad", gender="girls", max_rent=8000)
    # Draft mentions pg_ahm_005 (Sunrise Luxury PG, rent 12000 > 8000), which is not in recommended_pg_ids
    draft_with_excluded = "I recommend Shree Shanti Girls PG (pg_ahm_001). Also Sunrise Luxury PG (pg_ahm_005) is available."
    val = ValidationService.validate_recommendations(
        recommended_pg_ids=["pg_ahm_001"],
        criteria=criteria,
        proposed_text=draft_with_excluded
    )
    assert val.is_valid is False
    assert any("Rejected listing in text" in e for e in val.errors)

def test_validation_strict_distance_rejects_missing_gps():
    """Fix 5 Blocker: Missing GPS coordinates cannot satisfy strict distance request."""
    criteria = PGSearchCriteria(city="Ahmedabad", max_distance_km=1.0)
    # pg_ahm_012 has latitude=None, longitude=None
    val = ValidationService.validate_recommendations(
        recommended_pg_ids=["pg_ahm_012"],
        criteria=criteria,
        distance_data={"pg_ahm_012": None}
    )
    assert val.is_valid is False
    assert any("Distance verification failure" in e for e in val.errors)

def test_reflection_correction_on_failure():
    criteria = PGSearchCriteria(max_rent=7000)
    # Give a list containing one invalid (7500) and one valid (6800)
    initial_val = ValidationService.validate_recommendations(
        recommended_pg_ids=["pg_ahm_001", "pg_ahm_002"],
        criteria=criteria
    )
    assert initial_val.is_valid is False

    reflector = ReflectionAgent()
    ref_res = reflector._fallback_correction(
        user_query="Find PG under 7000",
        criteria=criteria,
        original_draft="Proposed both pg_ahm_001 and pg_ahm_002",
        validation_result=initial_val,
        recommended_pg_ids=["pg_ahm_001", "pg_ahm_002"]
    )
    assert ref_res.needs_correction is True
    # Corrected text should keep pg_ahm_002 (rent 6800) and drop pg_ahm_001
    assert "Saraswati Bhavan" in ref_res.corrected_response
    assert "Shree Shanti" not in ref_res.corrected_response
