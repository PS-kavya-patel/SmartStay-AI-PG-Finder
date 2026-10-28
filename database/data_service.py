import json
import logging
from pathlib import Path
from typing import List, Optional
from config import PG_DATA_FILE
from models.schemas import PGListing

logger = logging.getLogger(__name__)

class DataService:
    def __init__(self, data_file_path: Optional[Path] = None):
        self.data_file_path = data_file_path or PG_DATA_FILE
        self._cached_listings: Optional[List[PGListing]] = None

    def load_all_pgs(self, force_reload: bool = False) -> List[PGListing]:
        """Loads and validates all PG listings from the JSON dataset."""
        if self._cached_listings is not None and not force_reload:
            return self._cached_listings

        if not self.data_file_path.exists():
            logger.error(f"Data file does not exist at {self.data_file_path}")
            return []

        try:
            with open(self.data_file_path, "r", encoding="utf-8") as f:
                raw_data = json.load(f)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to decode JSON from {self.data_file_path}: {e}")
            return []
        except Exception as e:
            logger.error(f"Unexpected error loading data file: {e}")
            return []

        if not isinstance(raw_data, list):
            logger.error("Dataset JSON root must be a list of records")
            return []

        validated_listings: List[PGListing] = []
        for index, item in enumerate(raw_data):
            try:
                pg = PGListing(**item)
                validated_listings.append(pg)
            except Exception as e:
                logger.warning(f"Record at index {index} failed validation: {e}. Record skipped.")

        self._cached_listings = validated_listings
        return validated_listings

    def get_pg_by_id(self, pg_id: str) -> Optional[PGListing]:
        """Finds a PG listing by its unique ID."""
        listings = self.load_all_pgs()
        for pg in listings:
            if pg.id.lower() == pg_id.strip().lower():
                return pg
        return None

    def reload_data(self) -> List[PGListing]:
        """Forces a reload from disk."""
        return self.load_all_pgs(force_reload=True)


# Singleton instance
data_service = DataService()
