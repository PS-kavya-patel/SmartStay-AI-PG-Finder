from typing import List, Dict, Any
from database.data_service import data_service

def compare_pgs(pg_ids: List[str]) -> Dict[str, Any]:
    """
    Compares multiple PG listings side-by-side.
    Provides key metric comparison and summary highlights.
    """
    if not pg_ids:
        return {
            "success": False,
            "error": "At least one PG ID must be provided for comparison",
            "comparison": []
        }

    items: List[Dict[str, Any]] = []
    for pid in pg_ids:
        pg = data_service.get_pg_by_id(pid.strip())
        if pg:
            items.append({
                "id": pg.id,
                "name": pg.name,
                "monthly_rent": pg.monthly_rent,
                "security_deposit": pg.security_deposit if pg.security_deposit is not None else "Not specified",
                "area": pg.area,
                "gender": pg.gender,
                "room_type": pg.room_type,
                "rating": pg.rating if pg.rating is not None else "Unrated",
                "availability": pg.availability or "Unknown",
                "amenities": pg.amenities,
                "amenity_count": len(pg.amenities)
            })

    if not items:
        return {
            "success": False,
            "error": f"None of the provided PG IDs were found: {pg_ids}",
            "comparison": []
        }

    # Identify highlights
    lowest_rent_pg = min(items, key=lambda x: x["monthly_rent"])
    rated_pgs = [x for x in items if isinstance(x["rating"], (int, float))]
    highest_rated_pg = max(rated_pgs, key=lambda x: x["rating"]) if rated_pgs else None
    most_amenities_pg = max(items, key=lambda x: x["amenity_count"])

    return {
        "success": True,
        "total_compared": len(items),
        "comparison": items,
        "highlights": {
            "lowest_rent": {
                "id": lowest_rent_pg["id"],
                "name": lowest_rent_pg["name"],
                "monthly_rent": lowest_rent_pg["monthly_rent"]
            },
            "highest_rated": {
                "id": highest_rated_pg["id"],
                "name": highest_rated_pg["name"],
                "rating": highest_rated_pg["rating"]
            } if highest_rated_pg else None,
            "most_amenities": {
                "id": most_amenities_pg["id"],
                "name": most_amenities_pg["name"],
                "amenity_count": most_amenities_pg["amenity_count"]
            }
        }
    }
