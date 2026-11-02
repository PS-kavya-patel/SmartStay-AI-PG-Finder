import re
from typing import List, Dict, Any, Optional
from database.data_service import data_service
from models.schemas import ValidationResult, PGSearchCriteria, PGListing
from tools.amenity_checker import normalize_amenity

# Known facility/amenity keywords to audit in proposed text
KNOWN_AUDITABLE_AMENITIES = [
    ("swimming pool", ["swimming pool", "pool"]),
    ("gym", ["gym", "fitness center", "fitness"]),
    ("ac", ["ac", "air conditioning", "air conditioner"]),
    ("wi-fi", ["wi-fi", "wifi", "internet"]),
    ("food", ["food", "meals", "mess", "breakfast", "dinner", "lunch"]),
    ("laundry", ["laundry", "washing machine"]),
    ("power backup", ["power backup", "generator", "inverter"]),
    ("cctv", ["cctv", "security camera"]),
    ("housekeeping", ["housekeeping", "cleaning"]),
    ("refrigerator", ["refrigerator", "fridge"]),
    ("tv", ["tv", "television"]),
    ("parking", ["parking", "garage"]),
    ("study table", ["study table", "desk"]),
    ("geyser", ["geyser", "hot water"]),
    ("balcony", ["balcony", "terrace"])
]

class ValidationService:
    """
    Deterministic validator to rigorously verify agent recommendations against
    actual database records, user constraints, and asserted factual claims in text.
    """

    @staticmethod
    def extract_claimed_rent(text: str, pg_context: str) -> Optional[float]:
        """
        Extracts any explicit numeric rent claimed in the text for a specific PG context.
        Handles: 'costs ₹1', 'costs ₹7,500', 'rent of ₹1/month', '₹1 per month', '₹7,500', etc.
        """
        # Search within the specific PG context or sentences
        rent_patterns = [
            r"(?:costs?|rent(?:\s*(?:is|of|:))?|pricing(?:\s*(?:is|of|:))?)\s*(?:₹|rs\.?|inr)?\s*([0-9]+(?:,[0-9]+)*|\d+k)\b",
            r"(?:₹|rs\.?|inr)\s*([0-9]+(?:,[0-9]+)*|\d+k)\s*(?:/\s*month|per\s*month|\s*pm|\b)",
            r"([0-9]+(?:,[0-9]+)*|\d+k)\s*(?:rupees|inr)?\s*(?:/\s*month|per\s*month|\s*pm)"
        ]
        for pattern in rent_patterns:
            match = re.search(pattern, pg_context, re.IGNORECASE)
            if match:
                val_str = match.group(1).replace(",", "").strip().lower()
                try:
                    if val_str.endswith("k"):
                        return float(val_str[:-1]) * 1000.0
                    return float(val_str)
                except ValueError:
                    continue
        return None

    @staticmethod
    def extract_claimed_amenities(pg_context: str) -> List[str]:
        """
        Extracts amenities claimed to be provided/offered in the given context text.
        """
        claimed = []
        clean_context = pg_context.lower()

        for canonical_name, aliases in KNOWN_AUDITABLE_AMENITIES:
            for alias in aliases:
                # Use word boundaries so 'ac' does not match 'accommodation'
                pattern = rf"\b{re.escape(alias)}\b"
                if re.search(pattern, clean_context):
                    # Check negative context like 'no swimming pool' or 'without gym'
                    neg_pattern = rf"(?:no|without|lacks?|does\s*not\s*(?:have|offer))\s+{re.escape(alias)}"
                    if not re.search(neg_pattern, clean_context):
                        if canonical_name not in claimed:
                            claimed.append(canonical_name)
                    break
        return claimed

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

        all_db_pgs = data_service.load_all_pgs()
        distance_data = distance_data or {}

        # 0. Check for rejected PGs mentioned in proposed text (Fix 3 blocker)
        if proposed_text:
            text_lower = proposed_text.lower()
            for p in all_db_pgs:
                # If this PG is mentioned in text
                if (p.id.lower() in text_lower or p.name.lower() in text_lower):
                    if p.id not in recommended_pg_ids:
                        errors.append(
                            f"Rejected listing in text: '{p.name}' ({p.id}) is mentioned in the proposed text "
                            f"but is not in the approved recommendation set."
                        )

        if not recommended_pg_ids:
            warnings.append("No PG IDs provided in recommendation set.")
            is_valid = len(errors) == 0
            return ValidationResult(is_valid=is_valid, errors=errors, warnings=warnings, verified_items=verified)

        for pid in recommended_pg_ids:
            pg = data_service.get_pg_by_id(pid.strip())

            # 1. Grounding in Database
            if not pg:
                errors.append(f"Grounding failure: PG ID '{pid}' does not exist in the database.")
                continue

            verified.append(f"PG '{pg.name}' ({pg.id}) verified in database.")

            # 2. Neighborhood / Area Verification
            if criteria.area and criteria.area.strip().lower() not in ["all areas", "all", ""]:
                clean_target_area = criteria.area.strip().lower()
                if clean_target_area != pg.area.strip().lower():
                    errors.append(
                        f"Neighborhood violation: '{pg.name}' is in '{pg.area}', "
                        f"but user requested '{criteria.area}'."
                    )
                else:
                    verified.append(f"'{pg.name}' neighborhood '{pg.area}' matches requested '{criteria.area}'.")

            # 3. Budget Verification
            if criteria.max_rent is not None and criteria.max_rent > 0:
                if pg.monthly_rent > criteria.max_rent:
                    errors.append(
                        f"Budget violation: '{pg.name}' monthly rent of ₹{pg.monthly_rent:,.0f} "
                        f"exceeds user budget of ₹{criteria.max_rent:,.0f}."
                    )
                else:
                    verified.append(f"'{pg.name}' rent ₹{pg.monthly_rent:,.0f} is within budget ₹{criteria.max_rent:,.0f}.")

            # 4. Gender Verification
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

            # 5. Mandatory Amenities Verification against Database
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

            # 6. Distance Limit Verification & Strict Missing Coordinate Check (Fix 5 blocker)
            if criteria.max_distance_km is not None and criteria.max_distance_km > 0:
                pg_distance = distance_data.get(pg.id)
                # Check if coordinates exist in DB
                if pg.latitude is None or pg.longitude is None:
                    errors.append(
                        f"Distance verification failure: '{pg.name}' has unrecorded GPS coordinates. "
                        f"Cannot verify requirement of within {criteria.max_distance_km} km."
                    )
                elif pg_distance is not None:
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
                    errors.append(
                        f"Distance verification failure: Distance for '{pg.name}' could not be computed. "
                        f"Cannot verify requirement of within {criteria.max_distance_km} km."
                    )

            # 7. Availability Check
            if pg.availability and pg.availability.lower() == "full":
                warnings.append(f"'{pg.name}' is currently marked as FULL in the database.")

            # 8. Factual Claim Verification in Proposed Text (Fix 2 blocker)
            if proposed_text:
                # Find context around this specific PG in the proposed text
                # We split by PG name or sections, or look for lines referencing this PG
                pg_sentences = []
                for sentence in re.split(r"[.\n;]", proposed_text):
                    if (pg.id.lower() in sentence.lower() or
                        pg.name.lower() in sentence.lower() or
                        pg.name.split()[0].lower() in sentence.lower()):
                        pg_sentences.append(sentence)

                pg_context = " ".join(pg_sentences) if pg_sentences else proposed_text

                # 8A. Audit Claimed Rent
                claimed_rent = ValidationService.extract_claimed_rent(proposed_text, pg_context)
                if claimed_rent is not None:
                    if abs(claimed_rent - pg.monthly_rent) > 1.0:
                        errors.append(
                            f"Fact mismatch: Proposed text claims '{pg.name}' costs ₹{claimed_rent:,.0f}, "
                            f"but actual database rent is ₹{pg.monthly_rent:,.0f}."
                        )
                    else:
                        verified.append(f"Claimed rent ₹{claimed_rent:,.0f} for '{pg.name}' matches database.")

                # 8B. Audit Claimed Amenities
                claimed_amenities = ValidationService.extract_claimed_amenities(pg_context)
                pg_norm_amenities = [normalize_amenity(a) for a in pg.amenities]
                for am in claimed_amenities:
                    norm_am = normalize_amenity(am)
                    if norm_am not in pg_norm_amenities:
                        errors.append(
                            f"Hallucination error: Proposed text claims '{pg.name}' offers '{am}', "
                            f"but it is not listed in the database record."
                        )
                    else:
                        verified.append(f"Claimed facility '{am}' for '{pg.name}' verified in database.")

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
