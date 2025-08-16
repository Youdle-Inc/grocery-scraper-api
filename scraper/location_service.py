"""
Location-based store discovery service
Prepares for Perplexity Sonar integration
"""

import logging
import re
import os
from typing import List, Dict, Optional, Set
from .models import StoreLocation, StoreInfo
from .config import SUPPORTED_STORES
from .sonar_client import SonarClient

logger = logging.getLogger(__name__)

class LocationService:
    """Service for location-based store discovery and management"""
    
    def __init__(self):
        # Store coverage mappings (zipcode ranges -> store_ids)
        # This will be enhanced with Perplexity Sonar later
        self.store_coverage = self._initialize_store_coverage()
        
        # Initialize Perplexity Sonar client
        api_key = os.environ.get("PERPLEXITY_API_KEY")
        self.sonar_client = SonarClient(api_key)
        
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
    
    async def get_stores_for_zipcode(self, zipcode: str) -> List[StoreLocation]:
        """Get available stores for a given zipcode using Perplexity Sonar"""
        try:
            # First try Perplexity Sonar for dynamic store discovery
            if self.sonar_client.is_available():
                logger.info(f"🔍 Using Perplexity Sonar to find stores in {zipcode}")
                sonar_stores = await self.sonar_client.search_stores(zipcode)
                
                if sonar_stores:
                    logger.info(f"✅ Found {len(sonar_stores)} stores via Sonar for {zipcode}")
                    return sonar_stores
                else:
                    logger.info(f"⚠️ No stores found via Sonar for {zipcode}, falling back to static coverage")
            
            # Fallback to static coverage if Sonar fails or is unavailable
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
            return available_stores
            
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
        """Add or update store coverage (for future Perplexity Sonar integration)"""
        self.store_coverage[store_id] = zipcode_ranges
        logger.info(f"Updated coverage for {store_id}: {zipcode_ranges}")
    
    async def get_nearby_stores(self, zipcode: str, radius_miles: int = 10) -> List[StoreLocation]:
        """Get stores within specified radius using Perplexity Sonar"""
        # This will be enhanced with actual distance calculations
        # For now, return stores available in the zipcode
        return await self.get_stores_for_zipcode(zipcode)
    
    def validate_zipcode(self, zipcode: str) -> bool:
        """Validate zipcode format"""
        return bool(re.match(r'^\d{5}$', zipcode))
    
    def get_store_services(self, store_id: str) -> List[str]:
        """Get available services for a store (delivery, pickup, etc.)"""
        # This will be enhanced with Perplexity Sonar data
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
