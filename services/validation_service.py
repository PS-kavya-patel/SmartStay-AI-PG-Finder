import re
from typing import List, Dict, Any, Optional
from database.data_service import data_service
from models.schemas import ValidationResult, PGSearchCriteria, PGListing
from tools.amenity_checker import normalize_amenity

class ValidationService:
    """
    Deterministic validator to rigorously verify agent recommendations against
    actual database records and user constraints.
    """

    @staticmethod
    def validate_recommendations(
        recommended_pg_ids: List[str],
        criteria: PGSearchCriteria,
        proposed_text: str = "",
        distance_data: Optional[Dict[str, float]] = None
    ) -> ValidationResult:
        errors: List[str] = []
        warnings: List[str] = []
        verified: List[str] = []

        if not recommended_pg_ids:
            # If no PGs were recommended, verify if this was justified
            warnings.append("No PG IDs provided in recommendation set.")
            return ValidationResult(is_valid=True, errors=errors, warnings=warnings, verified_items=verified)

        distance_data = distance_data or {}

        for pid in recommended_pg_ids:
            pg = data_service.get_pg_by_id(pid.strip())

            # 1. Grounding in Database
            if not pg:
                errors.append(f"Grounding failure: PG ID '{pid}' does not exist in the database.")
                continue

            verified.append(f"PG '{pg.name}' ({pg.id}) verified in database.")

            # 2. Budget Verification
            if criteria.max_rent is not None and criteria.max_rent > 0:
                if pg.monthly_rent > criteria.max_rent:
                    errors.append(
                        f"Budget violation: '{pg.name}' monthly rent of ₹{pg.monthly_rent:,.0f} "
                        f"exceeds user budget of ₹{criteria.max_rent:,.0f}."
                    )
                else:
                    verified.append(f"'{pg.name}' rent ₹{pg.monthly_rent:,.0f} is within budget ₹{criteria.max_rent:,.0f}.")

            # 3. Gender Verification
            if criteria.gender:
                clean_gender = criteria.gender.strip().lower()
                if "girl" in clean_gender or "female" in clean_gender:
                    if pg.gender not in ["girls", "co-ed"]:
                        errors.append(
                            f"Gender restriction violation: '{pg.name}' is marked as '{pg.gender}', "
                            "but user requested a girls' accommodation."
                        )
                elif "boy" in clean_gender or "male" in clean_gender:
                    if pg.gender not in ["boys", "co-ed"]:
                        errors.append(
                            f"Gender restriction violation: '{pg.name}' is marked as '{pg.gender}', "
                            "but user requested a boys' accommodation."
                        )

            # 4. Mandatory Amenities Verification
            if criteria.required_amenities:
                pg_norm_amenities = [normalize_amenity(a) for a in pg.amenities]
                for req in criteria.required_amenities:
                    norm_req = normalize_amenity(req)
                    if norm_req not in pg_norm_amenities:
                        errors.append(
                            f"Amenity violation: '{pg.name}' does not provide mandatory amenity '{req}'."
                        )
                    else:
                        verified.append(f"'{pg.name}' confirmed to provide '{req}'.")

            # 5. Distance Limit Verification
            if criteria.max_distance_km is not None and criteria.max_distance_km > 0:
                pg_distance = distance_data.get(pg.id)
                if pg_distance is not None:
                    if pg_distance > criteria.max_distance_km:
                        errors.append(
                            f"Distance violation: '{pg.name}' is {pg_distance:.2f} km away, "
                            f"exceeding max allowed distance of {criteria.max_distance_km} km."
                        )
                    else:
                        verified.append(
                            f"'{pg.name}' distance {pg_distance:.2f} km satisfies <= {criteria.max_distance_km} km."
                        )
                else:
                    warnings.append(
                        f"Distance for '{pg.name}' could not be verified because coordinates are unrecorded."
                    )

            # 6. Availability Check
            if pg.availability and pg.availability.lower() == "full":
                warnings.append(f"'{pg.name}' is currently marked as FULL in the database.")

        # Check for fabricated driving distance claims in proposed text
        if "driving distance" in proposed_text.lower():
            warnings.append(
                "Proposed text refers to 'driving distance'. The system only provides straight-line Haversine distance."
            )

        is_valid = len(errors) == 0
        return ValidationResult(
            is_valid=is_valid,
            errors=errors,
            warnings=warnings,
            verified_items=verified
        )
