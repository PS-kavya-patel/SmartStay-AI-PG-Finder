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

    def resolve_place_coordinates(self, place_query: str) -> Optional[Dict[str, Any]]:
        """Resolves a landmark, college, or neighborhood into latitude and longitude."""
        if not place_query or not place_query.strip():
            return None
        clean = place_query.strip().lower()

        # 1. High-accuracy landmark dictionary for Ahmedabad educational and corporate hubs
        known_landmarks = {
            "ld college of engineering": {"lat": 23.0338, "lon": 72.5463, "display_name": "L.D. College of Engineering, Navrangpura, Ahmedabad"},
            "ld college": {"lat": 23.0338, "lon": 72.5463, "display_name": "L.D. College of Engineering, Navrangpura, Ahmedabad"},
            "gujarat university": {"lat": 23.0375, "lon": 72.5458, "display_name": "Gujarat University, Navrangpura, Ahmedabad"},
            "cept university": {"lat": 23.0380, "lon": 72.5480, "display_name": "CEPT University, Navrangpura, Ahmedabad"},
            "st. xavier's college": {"lat": 23.0322, "lon": 72.5567, "display_name": "St. Xavier's College, Navrangpura, Ahmedabad"},
            "iim ahmedabad": {"lat": 23.0315, "lon": 72.5312, "display_name": "IIM Ahmedabad (IIM-A), Vastrapur, Ahmedabad"},
            "iima": {"lat": 23.0315, "lon": 72.5312, "display_name": "IIM Ahmedabad (IIM-A), Vastrapur, Ahmedabad"},
            "national institute of design": {"lat": 23.0122, "lon": 72.5683, "display_name": "National Institute of Design (NID), Paldi, Ahmedabad"},
            "nid": {"lat": 23.0122, "lon": 72.5683, "display_name": "National Institute of Design (NID), Paldi, Ahmedabad"},
            "ahmedabad management association": {"lat": 23.0305, "lon": 72.5348, "display_name": "AMA, Vastrapur, Ahmedabad"},
            "ama": {"lat": 23.0305, "lon": 72.5348, "display_name": "AMA, Vastrapur, Ahmedabad"},
            "gujarat chamber of commerce": {"lat": 23.0135, "lon": 72.5702, "display_name": "GCCI, Paldi, Ahmedabad"},
            "gcci": {"lat": 23.0135, "lon": 72.5702, "display_name": "GCCI, Paldi, Ahmedabad"},
            "pinnacle business park": {"lat": 23.0425, "lon": 72.5110, "display_name": "Pinnacle Business Park, Bodakdev, Ahmedabad"},
            "judges bungalow": {"lat": 23.0410, "lon": 72.5135, "display_name": "Judges Bungalow Hub, Bodakdev, Ahmedabad"},
            "isro": {"lat": 23.0232, "lon": 72.5186, "display_name": "ISRO Space Applications Centre, Satellite, Ahmedabad"},
            "space applications centre": {"lat": 23.0232, "lon": 72.5186, "display_name": "ISRO Space Applications Centre, Satellite, Ahmedabad"},
            "shivranjani": {"lat": 23.0265, "lon": 72.5255, "display_name": "Shivranjani Hub, Satellite, Ahmedabad"},
        }
        for landmark_key, landmark_info in known_landmarks.items():
            if landmark_key in clean:
                return {
                    "latitude": landmark_info["lat"],
                    "longitude": landmark_info["lon"],
                    "display_name": landmark_info["display_name"]
                }

        # 2. Check destination dataset
        info = self.get_destination_info(clean)
        if info:
            return {
                "latitude": info["lat"],
                "longitude": info["lon"],
                "display_name": info["name"]
            }

        # 3. Check neighborhood centers
        area_centers = {
            "navrangpura": (23.0373, 72.5532),
            "vastrapur": (23.0350, 72.5293),
            "bodakdev": (23.0425, 72.5110),
            "satellite": (23.0280, 72.5190),
            "paldi": (23.0125, 72.5620),
            "ahmedabad": (23.0225, 72.5714),
        }
        for area_name, (lat, lon) in area_centers.items():
            if area_name in clean:
                return {
                    "latitude": lat,
                    "longitude": lon,
                    "display_name": f"{area_name.capitalize()}, Ahmedabad"
                }
        return None

# Singleton instance
location_service = LocationService()
