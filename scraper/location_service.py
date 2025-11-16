"""
Location-based store discovery service
Store location discovery and management
"""

import logging
import re
import os
from typing import List, Dict, Optional, Set
from .models import StoreLocation, StoreInfo
from .config import SUPPORTED_STORES, CANONICAL_STORES, STORE_ALIASES
# SonarClient removed - using Exa only

logger = logging.getLogger(__name__)

class LocationService:
    """Service for location-based store discovery and management"""
    
    def __init__(self):
        # Store coverage mappings (zipcode ranges -> store_ids)
        # Store coverage mapping for location-based discovery
        self.store_coverage = self._initialize_store_coverage()
        
        # SonarClient removed - using Exa only
        
    def _initialize_store_coverage(self) -> Dict[str, List[str]]:
        """Initialize store coverage by zipcode ranges"""
        return {
            # Giant Eagle - Pennsylvania, Ohio, West Virginia, Indiana, Maryland
            "gianteagle": [
                "15000-16999",  # PA
                "43000-45999",  # OH
                "25000-26999",  # WV
                "46000-47999",  # IN
                "21000-21999",  # MD
            ],
            # Wegmans - NY, PA, NJ, VA, MD, MA, NC
            "wegmans": [
                "10000-14999",  # NY
                "15000-16999",  # PA
                "07000-08999",  # NJ
                "22000-22999",  # VA
                "21000-21999",  # MD
                "01000-02799",  # MA
                "27000-28999",  # NC
            ],
            # ALDI - Nationwide
            "aldi": [
                "00000-99999",  # Nationwide coverage
            ],
            # Albertsons - Nationwide
            "albertsons": [
                "00000-99999",  # Nationwide coverage
            ],
            # ShopRite - Northeast
            "shoprite": [
                "10000-14999",  # NY
                "15000-16999",  # PA
                "07000-08999",  # NJ
                "01000-02799",  # MA
                "06000-06999",  # CT
            ]
        }
    
    async def get_stores_for_zipcode(self, zipcode: str, chains: Optional[Set[str]] = None) -> List[StoreLocation]:
        """Get available stores for a given zipcode using static coverage and filter to canonical chains."""
        try:
            # SonarClient removed - using static coverage only
            logger.info(f"🔍 Using static store coverage for {zipcode}")
            
            # Use static coverage for store discovery
            zipcode_int = int(zipcode)
            available_stores = []
            
            for store_id, coverage_ranges in self.store_coverage.items():
                if self._zipcode_in_range(zipcode_int, coverage_ranges):
                    store_info = SUPPORTED_STORES.get(store_id, {})
                    store_location = StoreLocation(
                        store_id=store_id,
                        store_name=store_info.get("name", store_id.title()),
                        zipcode=zipcode,
                        status="active"
                    )
                    available_stores.append(store_location)
            
            logger.info(f"Found {len(available_stores)} stores via static coverage for zipcode {zipcode}")
            return self._filter_to_canonical_chains(available_stores, chains)
            
        except ValueError:
            logger.error(f"Invalid zipcode format: {zipcode}")
            return []
        except Exception as e:
            logger.error(f"Error getting stores for zipcode {zipcode}: {e}")
            return []
    
    def _zipcode_in_range(self, zipcode: int, ranges: List[str]) -> bool:
        """Check if zipcode falls within any of the given ranges"""
        for range_str in ranges:
            if range_str == "00000-99999":  # Nationwide coverage
                return True
            
            start, end = map(int, range_str.split("-"))
            if start <= zipcode <= end:
                return True
        return False
    
    def get_store_coverage_info(self) -> Dict[str, List[str]]:
        """Get store coverage information"""
        return self.store_coverage
    
    def add_store_coverage(self, store_id: str, zipcode_ranges: List[str]) -> None:
        """Add or update store coverage for location-based discovery"""
        self.store_coverage[store_id] = zipcode_ranges
        logger.info(f"Updated coverage for {store_id}: {zipcode_ranges}")
    
    async def get_nearby_stores(self, zipcode: str, radius_miles: int = 10) -> List[StoreLocation]:
        """Get stores within specified radius using static coverage"""
        # This will be enhanced with actual distance calculations
        # For now, return stores available in the zipcode
        return await self.get_stores_for_zipcode(zipcode)

    def _filter_to_canonical_chains(self, stores: List[StoreLocation], chains: Optional[Set[str]] = None) -> List[StoreLocation]:
        """Filter stores to a set of canonical chains and normalize IDs by aliases."""
        if chains is None or len(chains) == 0:
            allowed = set(CANONICAL_STORES)
        else:
            allowed = set(chains)
        normalized: List[StoreLocation] = []
        for s in stores:
            store_id = (s.store_id or s.store_name or "").lower().replace(" ", "_")
            
            # Try exact match first
            canonical = STORE_ALIASES.get(store_id, store_id)
            
            # If no exact match, try partial matching
            if canonical not in allowed and canonical not in CANONICAL_STORES:
                for alias, canonical_id in STORE_ALIASES.items():
                    if alias in store_id or store_id.startswith(alias):
                        canonical = canonical_id
                        break
            
            # If still no match, try direct canonical store matching
            if canonical not in allowed and canonical not in CANONICAL_STORES:
                for canonical_store in CANONICAL_STORES:
                    if canonical_store in store_id or store_id.startswith(canonical_store):
                        canonical = canonical_store
                        break
            
            if canonical in allowed or canonical in CANONICAL_STORES:
                s.store_id = canonical
                normalized.append(s)
        return normalized
    
    def validate_zipcode(self, zipcode: str) -> bool:
        """Validate zipcode format"""
        return bool(re.match(r'^\d{5}$', zipcode))
    
    def _get_nationwide_stores(self) -> Set[str]:
        """Get set of nationwide store IDs that are always available"""
        return {
            "walmart", "target", "aldi", "kroger", "costco", 
            "whole_foods", "sams_club", "trader_joes", "safeway", "albertsons"
        }
    
    def _normalize_store_id(self, store_id: str) -> str:
        """Normalize store ID using aliases"""
        normalized = store_id.lower().strip().replace(" ", "_")
        return STORE_ALIASES.get(normalized, normalized)
    
    def is_store_available_in_zipcode(self, store_id: str, zipcode: str) -> bool:
        """
        Check if a store is available in the given zipcode.
        
        Args:
            store_id: Store identifier (e.g., "walmart", "wegmans")
            zipcode: 5-digit ZIP code
            
        Returns:
            True if store is available in zipcode, False otherwise
        """
        try:
            # Validate zipcode format
            if not self.validate_zipcode(zipcode):
                logger.warning(f"Invalid zipcode format: {zipcode}")
                return False
            
            # Normalize store ID
            normalized_id = self._normalize_store_id(store_id)
            
            # Nationwide stores are always available
            nationwide_stores = self._get_nationwide_stores()
            if normalized_id in nationwide_stores:
                return True
            
            # Check regional store coverage
            if normalized_id in self.store_coverage:
                zipcode_int = int(zipcode)
                return self._zipcode_in_range(zipcode_int, self.store_coverage[normalized_id])
            
            # If store not in coverage map, assume it's available (fallback for stores without coverage data)
            logger.debug(f"Store {normalized_id} not in coverage map, assuming available")
            return True
            
        except ValueError:
            logger.error(f"Invalid zipcode format: {zipcode}")
            return False
        except Exception as e:
            logger.error(f"Error checking store availability for {store_id} in {zipcode}: {e}")
            return False
    
    def filter_stores_by_location(self, store_ids: List[str], zipcode: str) -> List[str]:
        """
        Filter a list of store IDs to only include stores available in the given zipcode.
        
        Args:
            store_ids: List of store identifiers to filter
            zipcode: 5-digit ZIP code
            
        Returns:
            Filtered list of store IDs that are available in the zipcode
        """
        if not store_ids:
            return []
        
        available_stores = []
        filtered_out = []
        
        for store_id in store_ids:
            if self.is_store_available_in_zipcode(store_id, zipcode):
                available_stores.append(store_id)
            else:
                filtered_out.append(store_id)
        
        if filtered_out:
            logger.info(f"📍 Filtered out {len(filtered_out)} stores not available in {zipcode}: {filtered_out}")
        
        logger.info(f"✅ {len(available_stores)} stores available in {zipcode}: {available_stores}")
        return available_stores
    
    def get_store_services(self, store_id: str) -> List[str]:
        """Get available services for a store (delivery, pickup, etc.)"""
        # This will be enhanced with additional store data
        default_services = ["pickup", "delivery"]
        
        # Store-specific services
        store_services = {
            "gianteagle": ["pickup", "delivery", "curbside"],
            "wegmans": ["pickup", "delivery", "curbside"],
            "aldi": ["pickup"],
            "albertsons": ["pickup", "delivery", "curbside"],
            "shoprite": ["pickup", "delivery"]
        }
        
        return store_services.get(store_id, default_services)
