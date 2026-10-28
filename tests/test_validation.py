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
