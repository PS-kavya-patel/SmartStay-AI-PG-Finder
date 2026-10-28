from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, field_validator

class PGListing(BaseModel):
    id: str = Field(..., description="Unique PG identifier")
    name: str = Field(..., description="Name of the PG accommodation")
    city: str = Field(..., description="City where PG is located")
    area: str = Field(..., description="Neighborhood or area name")
    gender: str = Field(..., description="Gender restriction: 'girls', 'boys', 'co-ed'")
    monthly_rent: float = Field(..., ge=0, description="Monthly rent in INR")
    security_deposit: Optional[float] = Field(None, ge=0, description="Refundable security deposit in INR")
    latitude: Optional[float] = Field(None, ge=-90.0, le=90.0, description="Latitude coordinate")
    longitude: Optional[float] = Field(None, ge=-180.0, le=180.0, description="Longitude coordinate")
    amenities: List[str] = Field(default_factory=list, description="List of amenities provided")
    room_type: str = Field(..., description="Room sharing type: 'single', 'double-sharing', 'triple-sharing'")
    rating: Optional[float] = Field(None, ge=0.0, le=5.0, description="User rating out of 5.0")
    availability: Optional[str] = Field(None, description="Current availability: 'available', 'limited', 'full'")
    contact_number: Optional[str] = Field(None, description="Contact phone or inquiry number")
    data_source: str = Field(default="demo_dataset", description="Source of the listing record")

    @field_validator("gender")
    @classmethod
    def normalize_gender(cls, v: str) -> str:
        v_clean = v.strip().lower()
        if "girl" in v_clean or "female" in v_clean or "women" in v_clean:
            return "girls"
        elif "boy" in v_clean or "male" in v_clean or "men" in v_clean:
            return "boys"
        elif "co" in v_clean or "unisex" in v_clean or "both" in v_clean:
            return "co-ed"
        return v_clean


class PGSearchCriteria(BaseModel):
    city: Optional[str] = None
    area: Optional[str] = None
    gender: Optional[str] = None
    max_rent: Optional[float] = None
    required_amenities: Optional[List[str]] = Field(default_factory=list)
    room_type: Optional[str] = None
    destination_name: Optional[str] = None
    max_distance_km: Optional[float] = None
    user_lat: Optional[float] = None
    user_lon: Optional[float] = None


class DistanceResult(BaseModel):
    origin: str
    destination: str
    distance_km: float
    distance_type: str = "haversine_straight_line"
    source: str = "location_service"
    details: Optional[str] = None


class ScoredPG(BaseModel):
    pg: PGListing
    distance_km: Optional[float] = None
    final_score: float = Field(..., ge=0.0, le=100.0)
    score_breakdown: Dict[str, float] = Field(default_factory=dict)
    match_reasons: List[str] = Field(default_factory=list)


class ValidationResult(BaseModel):
    is_valid: bool
    errors: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
    verified_items: List[str] = Field(default_factory=list)


class ReflectionResult(BaseModel):
    passed_validation: bool
    needs_correction: bool
    critique: str
    correction_suggestions: List[str] = Field(default_factory=list)
    corrected_response: Optional[str] = None
