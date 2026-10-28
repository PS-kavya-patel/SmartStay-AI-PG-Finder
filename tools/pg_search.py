from typing import List, Optional, Dict, Any
from database.data_service import data_service
from models.schemas import PGListing

def search_pgs(
    city: Optional[str] = None,
    area: Optional[str] = None,
    gender: Optional[str] = None,
    room_type: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    Search PG listings based on city, area, gender preference, and room type.
    Returns serialized list of matching PG records.
    """
    all_listings = data_service.load_all_pgs()
    results: List[PGListing] = []

    # Clean inputs
    clean_city = city.strip().lower() if city else None
    clean_area = area.strip().lower() if area else None
    clean_gender = gender.strip().lower() if gender else None
    clean_room = room_type.strip().lower() if room_type else None

    # Normalize gender term
    if clean_gender:
        if "girl" in clean_gender or "female" in clean_gender or "women" in clean_gender:
            target_gender = "girls"
        elif "boy" in clean_gender or "male" in clean_gender or "men" in clean_gender:
            target_gender = "boys"
        elif "co" in clean_gender or "unisex" in clean_gender:
            target_gender = "co-ed"
        else:
            target_gender = clean_gender
    else:
        target_gender = None

    for pg in all_listings:
        # Check city
        if clean_city and clean_city not in pg.city.lower():
            continue

        # Check area
        if clean_area and clean_area not in pg.area.lower():
            continue

        # Check gender restriction
        if target_gender:
            # If user asks for girls: matches girls or co-ed
            if target_gender == "girls" and pg.gender not in ["girls", "co-ed"]:
                continue
            elif target_gender == "boys" and pg.gender not in ["boys", "co-ed"]:
                continue
            elif target_gender == "co-ed" and pg.gender != "co-ed":
                continue

        # Check room type
        if clean_room and clean_room not in pg.room_type.lower():
            continue

        results.append(pg)

    return [pg.model_dump() for pg in results]


def get_pg_details(pg_id: str) -> Optional[Dict[str, Any]]:
    """Fetches full listing details for a specific PG ID."""
    if not pg_id:
        return None
    pg = data_service.get_pg_by_id(pg_id.strip())
    if pg:
        return pg.model_dump()
    return None
