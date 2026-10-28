from typing import List, Optional, Dict
from models.schemas import PGListing, ScoredPG

class ScoringService:
    """
    Explainable multi-criteria scoring engine for PG listings.
    Total Score: 0 to 100 points.
    - Budget factor: up to 30 points
    - Distance factor: up to 30 points
    - Amenities factor: up to 25 points
    - Quality/Rating factor: up to 15 points
    """

    @staticmethod
    def calculate_score(
        pg: PGListing,
        max_budget: Optional[float] = None,
        distance_km: Optional[float] = None,
        desired_amenities: Optional[List[str]] = None
    ) -> ScoredPG:
        breakdown: Dict[str, float] = {}
        reasons: List[str] = []

        # 1. Budget Score (max 30 pts)
        if max_budget and max_budget > 0:
            if pg.monthly_rent <= max_budget:
                savings = max_budget - pg.monthly_rent
                pct_saved = savings / max_budget
                budget_score = round(20.0 + min(pct_saved * 10.0, 10.0), 1)
                reasons.append(f"Rent ₹{pg.monthly_rent:,.0f} is within budget of ₹{max_budget:,.0f} (saved ₹{savings:,.0f})")
            else:
                budget_score = 0.0
                reasons.append(f"Rent ₹{pg.monthly_rent:,.0f} exceeds budget of ₹{max_budget:,.0f}")
        else:
            budget_score = 25.0  # neutral high when no budget specified
            reasons.append(f"Monthly rent is ₹{pg.monthly_rent:,.0f}")
        breakdown["budget_score"] = budget_score

        # 2. Distance Score (max 30 pts)
        if distance_km is not None:
            if distance_km <= 1.0:
                dist_score = 30.0
                reasons.append(f"Walking distance ({distance_km:.2f} km) to destination")
            elif distance_km <= 2.0:
                dist_score = 25.0
                reasons.append(f"Very close ({distance_km:.2f} km) to destination")
            elif distance_km <= 3.0:
                dist_score = 20.0
                reasons.append(f"Convenient distance ({distance_km:.2f} km) to destination")
            elif distance_km <= 5.0:
                dist_score = 12.0
                reasons.append(f"Moderate distance ({distance_km:.2f} km)")
            else:
                dist_score = max(5.0, round(30.0 - (distance_km * 2.5), 1))
                reasons.append(f"Distance is {distance_km:.2f} km")
        else:
            dist_score = 15.0  # neutral midpoint when distance is unverified
            reasons.append("Distance is unverified or coordinates not available")
        breakdown["distance_score"] = dist_score

        # 3. Amenities Score (max 25 pts)
        all_pg_amenities = [a.lower().strip() for a in pg.amenities]
        if desired_amenities:
            matched_count = 0
            for req in desired_amenities:
                if req.lower().strip() in all_pg_amenities:
                    matched_count += 1
            ratio = matched_count / max(len(desired_amenities), 1)
            amenity_score = round(ratio * 25.0, 1)
            reasons.append(f"Includes {matched_count}/{len(desired_amenities)} requested amenities")
        else:
            # Baseline based on amenity count
            amenity_score = round(min(len(pg.amenities) / 6.0, 1.0) * 25.0, 1)
            reasons.append(f"Offers {len(pg.amenities)} key amenities")
        breakdown["amenity_score"] = amenity_score

        # 4. Rating Score (max 15 pts)
        if pg.rating is not None:
            rating_score = round((pg.rating / 5.0) * 15.0, 1)
            reasons.append(f"User rating: {pg.rating:.1f}/5.0")
        else:
            rating_score = 10.0  # neutral default
            reasons.append("Rating not yet reviewed")
        breakdown["rating_score"] = rating_score

        total_score = round(sum(breakdown.values()), 1)
        # Clamp to 0 - 100
        total_score = max(0.0, min(100.0, total_score))

        return ScoredPG(
            pg=pg,
            distance_km=distance_km,
            final_score=total_score,
            score_breakdown=breakdown,
            match_reasons=reasons
        )
