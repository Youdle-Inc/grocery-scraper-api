"""
Location-based store discovery service
Store location discovery and management

Uses:
- Static zip code range coverage (primary, fast)
- Google Places API for actual store location verification (optional, more accurate)
- Geocoding service for zip code to coordinates conversion
"""

import logging
import re
import os
import asyncio
from typing import List, Dict, Optional, Set, Tuple
import aiohttp
from dotenv import load_dotenv

from .models import StoreLocation, StoreInfo
from .config import SUPPORTED_STORES, CANONICAL_STORES, STORE_ALIASES
from .geocoding_service import get_geocoding_service

load_dotenv()

logger = logging.getLogger(__name__)

class LocationService:
    """Service for location-based store discovery and management"""
    
    # Store chain search terms for Google Places API
    STORE_SEARCH_TERMS = {
        "walmart": "Walmart",
        "target": "Target",
        "kroger": "Kroger",
        "costco": "Costco",
        "aldi": "ALDI",
        "whole_foods": "Whole Foods Market",
        "trader_joes": "Trader Joe's",
        "safeway": "Safeway",
        "albertsons": "Albertsons",
        "publix": "Publix",
        "wegmans": "Wegmans",
        "giant_eagle": "Giant Eagle",
        "gianteagle": "Giant Eagle",
        "shoprite": "ShopRite",
        "marianos": "Mariano's",
        "sams_club": "Sam's Club",
        "heb": "H-E-B",
        "meijer": "Meijer",
        "hy_vee": "Hy-Vee",
        "sprouts": "Sprouts Farmers Market",
    }
    
    def __init__(self, google_api_key: Optional[str] = None):
        # Store coverage mappings (zipcode ranges -> store_ids)
        # Store coverage mapping for location-based discovery
        self.store_coverage = self._initialize_store_coverage()
        
        # Google Places API key for actual store location detection
        self.google_api_key = google_api_key or os.getenv("GOOGLE_PLACES_API_KEY") or os.getenv("GOOGLE_GEOCODING_API_KEY") or os.getenv("GOOGLE_MAPS_API_KEY")
        
        # Cache for Places API results: {(store_id, zipcode): (stores, timestamp)}
        self._places_cache: Dict[Tuple[str, str], Tuple[List[Dict], float]] = {}
        self._places_cache_ttl = 3600  # 1 hour cache TTL
        
        if self.google_api_key:
            logger.info("Google Places API initialized for store location detection")
        else:
            logger.info("Google Places API not available - using static coverage only")
        
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
            # Wegmans - NY, PA, NJ, VA, MD, MA, NC, CT, DC, DE
            # Wegmans has over 100 stores in these states
            "wegmans": [
                "10000-14999",  # NY (Rochester, Buffalo, Syracuse, Albany, Metro NY)
                "15000-19699",  # PA (Pittsburgh area 150xx-159xx, Eastern PA 170xx-196xx including Allentown, Bethlehem, Lancaster, Harrisburg, Scranton, Wilkes-Barre, King of Prussia, Malvern, etc.)
                "07000-08999",  # NJ (Bridgewater, Cherry Hill, Hanover, Manalapan, Montvale, Mt Laurel, Ocean, Princeton, Woodbridge)
                "22000-24699",  # VA (Alexandria, Arlington, Chantilly, Charlottesville, Dulles, Fairfax, Fredericksburg, Leesburg, Midlothian, Reston, Tysons, Virginia Beach)
                "20000-21999",  # MD & DC (Bel Air, Columbia, Crofton, Frederick, Germantown, Hunt Valley, Owings Mills, Rockville, Woodmore, DC)
                "01000-02799",  # MA (Burlington, Chestnut Hill, Medford, Northborough, Westwood)
                "27000-28999",  # NC (Chapel Hill, Raleigh, Cary, Wake Forest)
                "06000-06999",  # CT (Norwalk)
                "19700-19999",  # DE (Wilmington area)
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
            ],
            # Mariano's - Chicago area (Illinois)
            "marianos": [
                "60000-60999",  # Chicago suburbs (Cook, Lake, DuPage, Kane, McHenry counties)
                "60601-60699",  # Chicago city
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
            "walmart", "target", "aldi", "costco",
            "whole_foods", "sams_club", "trader_joes", "safeway", "albertsons"
        }
    
    def _normalize_store_id(self, store_id: str) -> str:
        """Normalize store ID using aliases"""
        normalized = store_id.lower().strip().replace(" ", "_").replace("-", "_").replace("'", "")
        if normalized in {"marianos", "mariano"}:
            return "marianos"
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
            
            # Fail closed for stores without explicit coverage.
            logger.debug(f"Store {normalized_id} not in coverage map, excluding it for {zipcode}")
            return False
            
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
    
    # ==================== Google Places API Integration ====================
    
    def is_places_api_available(self) -> bool:
        """Check if Google Places API is available"""
        return bool(self.google_api_key)
    
    async def search_stores_via_places_api(
        self,
        store_id: str,
        zipcode: str,
        radius_meters: int = 16093  # ~10 miles
    ) -> List[Dict]:
        """
        Search for actual store locations near a zipcode using Google Places API.
        
        Args:
            store_id: Store chain identifier (e.g., "wegmans", "walmart")
            zipcode: 5-digit ZIP code
            radius_meters: Search radius in meters (default ~10 miles)
            
        Returns:
            List of store locations found via Places API
        """
        if not self.google_api_key:
            logger.debug("Google Places API not available")
            return []
        
        # Check cache first
        import time
        cache_key = (store_id, zipcode)
        if cache_key in self._places_cache:
            cached_stores, timestamp = self._places_cache[cache_key]
            if time.time() - timestamp < self._places_cache_ttl:
                logger.debug(f"Places API cache hit for {store_id} in {zipcode}")
                return cached_stores
        
        try:
            # Get coordinates from zipcode
            geocoding_service = get_geocoding_service()
            city, state, lat, lng = await geocoding_service.get_location_from_zipcode(zipcode)
            
            if lat is None or lng is None:
                logger.debug(f"Could not get coordinates for zipcode {zipcode}")
                return []
            
            # Get search term for store
            search_term = self.STORE_SEARCH_TERMS.get(store_id.lower(), store_id.title())
            
            # Call Google Places API (Nearby Search)
            url = "https://maps.googleapis.com/maps/api/place/nearbysearch/json"
            params = {
                "location": f"{lat},{lng}",
                "radius": radius_meters,
                "keyword": search_term,
                "type": "supermarket",
                "key": self.google_api_key
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, params=params, timeout=aiohttp.ClientTimeout(total=10)) as response:
                    if response.status != 200:
                        logger.warning(f"Google Places API returned status {response.status}")
                        return []
                    
                    data = await response.json()
                    
                    if data.get("status") not in ["OK", "ZERO_RESULTS"]:
                        logger.warning(f"Google Places API error: {data.get('status')}")
                        return []
                    
                    results = data.get("results", [])
                    
                    # Filter results to only include the requested store chain
                    stores = []
                    search_term_lower = search_term.lower()
                    for place in results:
                        name = place.get("name", "").lower()
                        # Check if the store name contains the search term
                        if search_term_lower in name or name in search_term_lower:
                            stores.append({
                                "name": place.get("name"),
                                "address": place.get("vicinity"),
                                "place_id": place.get("place_id"),
                                "location": place.get("geometry", {}).get("location", {}),
                                "rating": place.get("rating"),
                                "open_now": place.get("opening_hours", {}).get("open_now")
                            })
                    
                    # Cache the results
                    self._places_cache[cache_key] = (stores, time.time())
                    
                    logger.info(f"Found {len(stores)} {search_term} stores near {zipcode} via Places API")
                    return stores
                    
        except asyncio.TimeoutError:
            logger.warning(f"Google Places API timeout for {store_id} in {zipcode}")
            return []
        except Exception as e:
            logger.warning(f"Google Places API error for {store_id} in {zipcode}: {e}")
            return []
    
    async def verify_store_in_zipcode(
        self,
        store_id: str,
        zipcode: str,
        radius_meters: int = 16093
    ) -> bool:
        """
        Verify if a specific store chain has locations near a zipcode.
        
        Uses Google Places API for accurate verification.
        Falls back to static coverage if API unavailable.
        
        Args:
            store_id: Store chain identifier
            zipcode: 5-digit ZIP code
            radius_meters: Search radius in meters
            
        Returns:
            True if store is verified to exist near zipcode
        """
        # Nationwide stores are always available (skip verification)
        normalized_id = self._normalize_store_id(store_id)
        if normalized_id in self._get_nationwide_stores():
            return True

        # Explicit static coverage is enough for covered stores.
        if self.is_store_available_in_zipcode(store_id, zipcode):
            return True

        # Unknown stores are only allowed if Places can verify them nearby.
        if self.google_api_key:
            stores = await self.search_stores_via_places_api(store_id, zipcode, radius_meters)
            return bool(stores)

        return False

    async def resolve_store_ids_by_location(
        self,
        store_ids: List[str],
        zipcode: str,
        verify_with_api: bool = True,
    ) -> List[str]:
        """
        Filter store IDs to only those that are actually available for a zipcode.

        Explicit coverage is accepted immediately. Stores without coverage are
        only included when Places verification confirms they are nearby.
        """
        if not store_ids:
            return []

        resolved: List[str] = []
        seen = set()

        for store_id in store_ids:
            normalized_id = self._normalize_store_id(store_id)
            if not normalized_id or normalized_id in seen:
                continue
            seen.add(normalized_id)

            if self.is_store_available_in_zipcode(normalized_id, zipcode):
                resolved.append(normalized_id)
                continue

            if verify_with_api and self.google_api_key:
                try:
                    if await self.verify_store_in_zipcode(normalized_id, zipcode):
                        resolved.append(normalized_id)
                except Exception as e:
                    logger.warning(f"Error verifying {normalized_id} in {zipcode}: {e}")

        return resolved
    
    async def get_verified_stores_for_zipcode(
        self,
        zipcode: str,
        store_ids: Optional[List[str]] = None,
        verify_with_api: bool = True
    ) -> List[StoreLocation]:
        """
        Get stores available in zipcode with optional Places API verification.
        
        Args:
            zipcode: 5-digit ZIP code
            store_ids: Optional list of store IDs to check (defaults to all regional stores)
            verify_with_api: Whether to verify with Google Places API
            
        Returns:
            List of verified store locations
        """
        # Get stores from static coverage first
        static_stores = await self.get_stores_for_zipcode(zipcode)
        
        # If no API verification requested or API unavailable, return static results
        if not verify_with_api or not self.google_api_key:
            return static_stores
        
        # Get list of regional stores to verify
        regional_stores_to_verify = []
        nationwide_stores = self._get_nationwide_stores()
        
        if store_ids:
            # Only verify requested stores
            for store_id in store_ids:
                normalized_id = self._normalize_store_id(store_id)
                if normalized_id not in nationwide_stores:
                    regional_stores_to_verify.append(normalized_id)
        else:
            # Verify all regional stores from static coverage
            for store in static_stores:
                if store.store_id not in nationwide_stores:
                    regional_stores_to_verify.append(store.store_id)
        
        # Verify regional stores with Places API
        verified_stores = []
        for store in static_stores:
            if store.store_id in nationwide_stores:
                # Nationwide stores are always included
                verified_stores.append(store)
            elif store.store_id in regional_stores_to_verify:
                # Verify regional store with Places API
                is_verified = await self.verify_store_in_zipcode(store.store_id, zipcode)
                if is_verified:
                    verified_stores.append(store)
                else:
                    logger.debug(f"Store {store.store_id} not verified in {zipcode} via Places API")
        
        return verified_stores
    
    async def find_nearest_store(
        self,
        store_id: str,
        zipcode: str,
        radius_meters: int = 32186  # ~20 miles
    ) -> Optional[Dict]:
        """
        Find the nearest store of a specific chain to a zipcode.
        
        Args:
            store_id: Store chain identifier
            zipcode: 5-digit ZIP code
            radius_meters: Search radius in meters
            
        Returns:
            Dict with store information, or None if not found
        """
        stores = await self.search_stores_via_places_api(store_id, zipcode, radius_meters)
        if stores:
            # Return the first result (Google Places returns results sorted by relevance/distance)
            return stores[0]
        return None
    
    def clear_places_cache(self):
        """Clear the Places API cache"""
        self._places_cache.clear()
        logger.info("Places API cache cleared")
