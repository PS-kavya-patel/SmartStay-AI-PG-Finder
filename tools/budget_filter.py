from typing import List, Dict, Any, Union, Optional
from database.data_service import data_service

def filter_by_budget(
    pg_input: Optional[Union[List[Dict[str, Any]], List[str]]] = None,
    max_rent: float = 0.0
) -> Dict[str, Any]:
    """
    Filters PG listings by maximum monthly rent (monthly_rent <= max_rent).
    Supports either a list of PG dicts, a list of PG IDs, or None (searches all).
    """
    if max_rent <= 0:
        return {
            "success": False,
            "error": "Budget must be greater than zero",
            "matching_pgs": [],
            "count": 0
        }

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
            "error": f"Invalid pg_input format: expected list or None, got {type(pg_input)}",
            "matching_pgs": [],
            "count": 0
        }

    matching = [pg for pg in listings if pg.get("monthly_rent", float("inf")) <= max_rent]

    return {
        "success": True,
        "max_rent": max_rent,
        "total_evaluated": len(listings),
        "count": len(matching),
        "matching_pgs": matching
    }
