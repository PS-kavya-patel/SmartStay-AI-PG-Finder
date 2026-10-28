from typing import List, Dict, Any, Union, Optional
from database.data_service import data_service

AMENITY_SYNONYMS = {
    "wifi": "wi-fi",
    "wi-fi": "wi-fi",
    "internet": "wi-fi",
    "food": "food",
    "meals": "food",
    "mess": "food",
    "tiffin": "food",
    "ac": "ac",
    "air conditioner": "ac",
    "air conditioning": "ac",
    "laundry": "laundry",
    "washing machine": "laundry",
    "power backup": "power backup",
    "generator": "power backup",
    "cctv": "cctv",
    "security": "cctv",
    "gym": "gym",
    "housekeeping": "housekeeping",
    "cleaning": "housekeeping"
}

def normalize_amenity(name: str) -> str:
    cleaned = name.strip().lower()
    return AMENITY_SYNONYMS.get(cleaned, cleaned)


def check_amenities(
    pg_input: Optional[Union[List[Dict[str, Any]], List[str]]] = None,
    required_amenities: Optional[List[str]] = None
) -> Dict[str, Any]:
    """
    Checks if listings satisfy all mandatory amenities.
    Returns matched listings and explains missing amenities.
    """
    if not required_amenities:
        required_amenities = []

    normalized_required = [normalize_amenity(a) for a in required_amenities if a.strip()]

    # Resolve items
    listings: List[Dict[str, Any]] = []
    if pg_input is None:
        all_pgs = data_service.load_all_pgs()
        listings = [pg.model_dump() for pg in all_pgs]
    elif isinstance(pg_input, list):
        if not pg_input:
            listings = []
        elif isinstance(pg_input[0], str):
            for pid in pg_input:
                pg = data_service.get_pg_by_id(pid)
                if pg:
                    listings.append(pg.model_dump())
        elif isinstance(pg_input[0], dict):
            listings = pg_input
    else:
        return {
            "success": False,
            "error": "Invalid pg_input format",
            "matching_pgs": [],
            "count": 0
        }

    fully_matching: List[Dict[str, Any]] = []
    missing_amenity_breakdown: Dict[str, List[str]] = {}

    for pg in listings:
        pg_amenities_raw = pg.get("amenities", [])
        pg_amenities_norm = [normalize_amenity(a) for a in pg_amenities_raw]

        missing = [req for req in normalized_required if req not in pg_amenities_norm]

        if not missing:
            fully_matching.append(pg)
        else:
            missing_amenity_breakdown[pg.get("id", "unknown")] = missing

    return {
        "success": True,
        "required_amenities": required_amenities,
        "count": len(fully_matching),
        "matching_pgs": fully_matching,
        "missing_breakdown": missing_amenity_breakdown
    }
