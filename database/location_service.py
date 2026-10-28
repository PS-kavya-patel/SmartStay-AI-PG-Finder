import json
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional

try:
    from config import LOCATIONS_FILE
except (ImportError, AttributeError):
    LOCATIONS_FILE = Path(__file__).resolve().parent / "locations.json"



logger = logging.getLogger(__name__)

class LocationService:
    """
    Manages structured mapping between Cities, Neighborhoods, and Colleges/Offices.
    """
    def __init__(self, locations_file_path: Optional[Path] = None):
        self.locations_file_path = locations_file_path or LOCATIONS_FILE
        self._data: Optional[Dict[str, Dict[str, List[Dict[str, Any]]]]] = None

    def _load_data(self, force_reload: bool = False) -> Dict[str, Dict[str, List[Dict[str, Any]]]]:
        if self._data is not None and not force_reload:
            return self._data

        if not self.locations_file_path.exists():
            logger.error(f"Locations file does not exist at {self.locations_file_path}")
            return {}

        try:
            with open(self.locations_file_path, "r", encoding="utf-8") as f:
                self._data = json.load(f)
                return self._data
        except Exception as e:
            logger.error(f"Failed to load locations from {self.locations_file_path}: {e}")
            return {}

    def get_cities(self) -> List[str]:
        """Returns list of supported cities."""
        data = self._load_data()
        return list(data.keys()) or ["Ahmedabad"]

    def get_neighborhoods(self, city: str = "Ahmedabad") -> List[str]:
        """Returns list of neighborhoods for a given city."""
        data = self._load_data()
        city_dict = data.get(city) or {}
        return list(city_dict.keys())

    def get_destinations(self, city: str = "Ahmedabad", neighborhood: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Returns destination objects (colleges/offices) for a city and optional neighborhood.
        If neighborhood is None or 'All Areas', returns all destinations for that city.
        """
        data = self._load_data()
        city_dict = data.get(city) or {}

        if not neighborhood or neighborhood.strip().lower() in ["all areas", "all"]:
            all_dests = []
            for n_name, dest_list in city_dict.items():
                all_dests.extend(dest_list)
            return all_dests

        clean_n = neighborhood.strip().lower()
        for n_name, dest_list in city_dict.items():
            if n_name.strip().lower() == clean_n:
                return dest_list

        return []

    def get_destination_names(self, city: str = "Ahmedabad", neighborhood: Optional[str] = None) -> List[str]:
        """Returns destination names for the dropdown."""
        dests = self.get_destinations(city=city, neighborhood=neighborhood)
        return [d["name"] for d in dests]

    def get_destination_info(self, destination_name: str) -> Optional[Dict[str, Any]]:
        """Finds destination record and coordinates by exact or fuzzy name."""
        if not destination_name:
            return None
        data = self._load_data()
        target = destination_name.strip().lower()

        for city_dict in data.values():
            for dest_list in city_dict.values():
                for dest in dest_list:
                    if dest["name"].strip().lower() == target or target in dest["name"].strip().lower() or dest["name"].strip().lower() in target:
                        return dest
        return None

# Singleton instance
location_service = LocationService()
