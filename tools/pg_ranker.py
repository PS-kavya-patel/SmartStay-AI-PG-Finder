from typing import List, Dict, Any, Optional
from database.data_service import data_service
from services.scoring_service import ScoringService
from tools.distance_calculator import haversine_distance

def rank_pgs(
    pg_ids: List[str],
    max_budget: Optional[float] = None,
    dest_lat: Optional[float] = None,
    dest_lon: Optional[float] = None,
    max_distance_km: Optional[float] = None,
    required_amenities: Optional[List[str]] = None
) -> Dict[str, Any]:
    """
    Ranks PG listings using multi-criteria scoring:
    budget savings, proximity, amenity coverage, and ratings.
    """
    if not pg_ids:
        return {
            "success": False,
            "error": "pg_ids list cannot be empty",
            "ranked_pgs": []
        }

    scored_list = []
    excluded_by_distance = []

    for pid in pg_ids:
        pg = data_service.get_pg_by_id(pid.strip())
        if not pg:
            continue

        # Calculate distance if coords available
        dist_km: Optional[float] = None
        if dest_lat is not None and dest_lon is not None:
            if pg.latitude is not None and pg.longitude is not None:
                dist_km = haversine_distance(pg.latitude, pg.longitude, dest_lat, dest_lon)
                # Check max distance filter
                if max_distance_km is not None and dist_km > max_distance_km:
                    excluded_by_distance.append({
                        "id": pg.id,
                        "name": pg.name,
                        "distance_km": dist_km,
                        "reason": f"Distance {dist_km} km exceeds limit of {max_distance_km} km"
                    })
                    continue

        scored_item = ScoringService.calculate_score(
            pg=pg,
            max_budget=max_budget,
            distance_km=dist_km,
            desired_amenities=required_amenities
        )
        scored_list.append(scored_item)

    # Sort descending by score
    scored_list.sort(key=lambda x: x.final_score, reverse=True)

    formatted_rankings = []
    for rank_idx, item in enumerate(scored_list, 1):
        formatted_rankings.append({
            "rank": rank_idx,
            "id": item.pg.id,
            "name": item.pg.name,
            "monthly_rent": item.pg.monthly_rent,
            "area": item.pg.area,
            "room_type": item.pg.room_type,
            "gender": item.pg.gender,
            "distance_km": item.distance_km,
            "final_score": item.final_score,
            "score_breakdown": item.score_breakdown,
            "match_reasons": item.match_reasons,
            "amenities": item.pg.amenities,
            "contact_number": item.pg.contact_number
        })

    return {
        "success": True,
        "total_ranked": len(formatted_rankings),
        "ranked_pgs": formatted_rankings,
        "excluded_by_distance": excluded_by_distance
    }
