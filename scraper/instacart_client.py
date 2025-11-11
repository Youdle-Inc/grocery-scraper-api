#!/usr/bin/env python3
"""
Instacart Developer Platform API Client
Replaces Exa API integration with Instacart's marketplace API for grocery product search
"""

import asyncio
import os
import logging
import aiohttp
from typing import Dict, List, Any, Optional
from dotenv import load_dotenv
from scraper.cache import Cache

load_dotenv()
logger = logging.getLogger(__name__)


class InstacartClient:
    """Instacart Developer Platform API client for grocery product search"""
    
    # Instacart API base URL
    API_BASE_URL = "https://api.instacart.com/v1"
    
    # Store display name mapping (matching ExaStructuredClient interface)
    STORE_DISPLAY_NAMES = {
        "target": "Target",
        "walmart": "Walmart",
        "kroger": "Kroger",
        "costco": "Costco",
        "albertsons": "Albertsons",
        "safeway": "Safeway",
        "vons": "Vons",
        "jewel": "Jewel-Osco",
        "jewel_osco": "Jewel-Osco",
        "ahold_delhaize": "Ahold Delhaize",
        "food_lion": "Food Lion",
        "giant": "Giant",
        "harris_teeter": "Harris Teeter",
        "hannaford": "Hannaford",
        "stop_and_shop": "Stop & Shop",
        "stop_n_shop": "Stop & Shop",
        "publix": "Publix",
        "heb": "H-E-B",
        "aldi": "ALDI",
        "sams_club": "Sam's Club",
        "whole_foods": "Whole Foods Market",
        "wholefoods": "Whole Foods Market",
        "whole_foods_market": "Whole Foods Market",
        "amazon_fresh": "Amazon Fresh",
        "meijer": "Meijer",
        "winco": "WinCo Foods",
        "bjs": "BJ's Wholesale Club",
        "bj's": "BJ's Wholesale Club",
        "bjs_wholesale": "BJ's Wholesale Club",
        "dollar_general": "Dollar General",
        "dollar_tree": "Dollar Tree",
        "trader_joes": "Trader Joe's",
        "trader joe's": "Trader Joe's",
        "hy_vee": "Hy-Vee",
        "wegmans": "Wegmans",
        "sprouts": "Sprouts Farmers Market",
        "giant_eagle": "Giant Eagle",
        "gianteagle": "Giant Eagle",
        "price_chopper": "Price Chopper",
        "cash_saver": "Cash Saver",
        "south_point_grocery": "South Point Grocery",
        "high_point_grocery": "High Point Grocery",
        "rs_market": "RS Market",
        "miss_cordelias": "Miss Cordelia's",
    }
    
    # Map our store IDs to Instacart retailer IDs (will be populated from API)
    RETAILER_ID_MAP = {
        # Common mappings - these may need to be updated based on actual Instacart retailer IDs
        "target": "target",
        "walmart": "walmart",
        "kroger": "kroger",
        "costco": "costco",
        "safeway": "safeway",
        "publix": "publix",
        "heb": "heb",
        "aldi": "aldi",
        "whole_foods": "whole-foods-market",
        "sprouts": "sprouts-farmers-market",
    }
    
    def __init__(self, api_key: Optional[str] = None):
        """Initialize Instacart client"""
        self.api_key = api_key or os.getenv("INSTACART_API_KEY")
        self._session: Optional[aiohttp.ClientSession] = None
        self.cache = Cache()
        
        if not self.api_key:
            logger.warning("⚠️ No INSTACART_API_KEY found in environment")
        else:
            logger.info("✅ Instacart client initialized")
    
    def is_available(self) -> bool:
        """Check if Instacart client is available"""
        return self.api_key is not None
    
    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create aiohttp session"""
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession(
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                timeout=aiohttp.ClientTimeout(total=30)
            )
        return self._session
    
    async def _close_session(self):
        """Close aiohttp session"""
        if self._session and not self._session.closed:
            await self._session.close()
    
    def get_store_display_name(self, store_id: Optional[str]) -> str:
        """Get display name for store ID"""
        if not store_id:
            return "Unknown Store"
        store_id_lower = store_id.lower().strip()
        # Try exact match first
        display_name = self.STORE_DISPLAY_NAMES.get(store_id_lower)
        if display_name:
            return display_name
        # Try with underscores/spaces variations
        for key, value in self.STORE_DISPLAY_NAMES.items():
            if key.replace('_', ' ') == store_id_lower.replace('_', ' '):
                return value
        # Fallback: capitalize and format
        return store_id.replace('_', ' ').title()
    
    def parse_availability(self, availability_text: Optional[str]) -> str:
        """
        Parse availability text into standardized status codes
        
        Returns:
            "IN_STOCK" - Product is available
            "OUT_OF_STOCK" - Product is sold out/unavailable
            "LOW_STOCK" - Limited availability
            "CHECK_STORE" - Cannot determine from available data
        """
        if not availability_text:
            return "CHECK_STORE"
        
        availability_lower = str(availability_text).lower().strip()
        
        # Out of stock indicators
        out_of_stock_patterns = [
            "out of stock",
            "sold out",
            "unavailable",
            "not available",
            "currently unavailable",
            "temporarily unavailable",
        ]
        
        for pattern in out_of_stock_patterns:
            if pattern in availability_lower:
                return "OUT_OF_STOCK"
        
        # Low stock indicators
        low_stock_patterns = [
            "low stock",
            "limited availability",
            "few left",
            "almost gone",
            "substituteable",
        ]
        
        for pattern in low_stock_patterns:
            if pattern in availability_lower:
                return "LOW_STOCK"
        
        # In stock indicators
        in_stock_patterns = [
            "in stock",
            "available",
            "add to cart",
            "buy now",
        ]
        
        for pattern in in_stock_patterns:
            if pattern in availability_lower:
                return "IN_STOCK"
        
        # Default: check store
        return "CHECK_STORE"
    
    async def get_retailers(self, zipcode: str) -> List[Dict[str, Any]]:
        """
        Get available retailers for a zipcode
        
        Args:
            zipcode: 5-digit ZIP code
            
        Returns:
            List of retailer dictionaries with id, name, etc.
        """
        if not self.is_available():
            return []
        
        # Check cache
        cache_key = f"instacart:retailers:{zipcode}"
        cached = await self.cache.get_json(cache_key)
        if cached:
            return cached
        
        try:
            session = await self._get_session()
            url = f"{self.API_BASE_URL}/retailers"
            params = {"zipcode": zipcode, "country": "US"}
            
            async with session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    retailers = data.get("data", [])
                    # Cache for 1 hour
                    await self.cache.set_json(cache_key, retailers, ttl_seconds=3600)
                    logger.info(f"✅ Found {len(retailers)} retailers for zipcode {zipcode}")
                    return retailers
                else:
                    logger.warning(f"⚠️ Instacart API error: {response.status}")
                    return []
        except Exception as e:
            logger.error(f"❌ Failed to fetch retailers: {e}")
            return []
    
    def _normalize_product(self, instacart_product: Dict[str, Any], retailer_info: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Normalize Instacart API product response to our schema
        
        Args:
            instacart_product: Raw product data from Instacart API
            retailer_info: Optional retailer information
            
        Returns:
            Normalized product dictionary matching our schema
        """
        # Extract product data
        product_id = instacart_product.get("id", "")
        name = instacart_product.get("name", "")
        price_data = instacart_product.get("price", {})
        availability = instacart_product.get("availability", {})
        images = instacart_product.get("images", [])
        
        # Extract price
        price = None
        currency = "USD"
        if isinstance(price_data, dict):
            price = price_data.get("amount")
            currency = price_data.get("currency", "USD")
        elif isinstance(price_data, (int, float)):
            price = float(price_data)
        
        # Extract availability
        availability_status = availability.get("status", "unknown") if isinstance(availability, dict) else str(availability)
        normalized_availability = self.parse_availability(availability_status)
        
        # Extract image URL
        image_url = None
        if images and isinstance(images, list):
            image_url = images[0].get("url") if isinstance(images[0], dict) else images[0]
        
        # Extract product URL
        product_url = instacart_product.get("url", "")
        if product_url and not product_url.startswith("http"):
            product_url = f"https://www.instacart.com{product_url}"
        
        # Extract retailer/store info
        retailer_data = instacart_product.get("retailer", {}) or retailer_info or {}
        store_name = retailer_data.get("name", "") if isinstance(retailer_data, dict) else str(retailer_data)
        store_id = retailer_data.get("id", "") if isinstance(retailer_data, dict) else None
        
        # Extract quantity/size
        quantity = instacart_product.get("quantity", "") or instacart_product.get("size", "")
        
        # Extract brand
        brand = instacart_product.get("brand", "")
        
        # Extract description
        description = instacart_product.get("description", "")
        
        # Extract category
        category = instacart_product.get("category", "")
        
        return {
            "id": f"ic_{product_id}",
            "name": name,
            "product_name": name,  # Alias for compatibility
            "brand": brand,
            "price": price,
            "currency": currency,
            "quantity": quantity,
            "size": quantity,
            "availability": normalized_availability,
            "image_url": image_url,
            "product_url": product_url,
            "description": description,
            "category": category,
            "store_name": store_name,
            "store_id": store_id,
            "source": "instacart",
        }
    
    async def search_products_structured(
        self,
        query: str,
        store_name: Optional[str] = None,
        zipcode: Optional[str] = None,
        num_results: int = 10,
        include_location: bool = True,
        context: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Search for products using Instacart API
        
        Args:
            query: Product search query
            store_name: Optional store/retailer name to filter by
            zipcode: ZIP code for location scoping (required for Instacart)
            num_results: Maximum number of results to return
            include_location: Whether to include location data
            context: Search context (unused for Instacart)
            
        Returns:
            List of normalized product dictionaries
        """
        if not self.is_available():
            logger.warning("⚠️ Instacart client not available")
            return []
        
        if not zipcode:
            logger.warning("⚠️ Zipcode required for Instacart search")
            return []
        
        # Check cache
        cache_key = f"instacart:products:{zipcode}:{query}:{store_name or 'all'}:{num_results}"
        cached = await self.cache.get_json(cache_key)
        if cached:
            logger.debug(f"Cache hit for Instacart search: {query}")
            return cached
        
        try:
            session = await self._get_session()
            
            # Get retailers for this zipcode
            retailers = await self.get_retailers(zipcode)
            
            # Filter by store_name if provided
            retailer_id = None
            if store_name:
                # Try to find matching retailer
                store_name_lower = store_name.lower()
                for retailer in retailers:
                    retailer_name = retailer.get("name", "").lower()
                    if store_name_lower in retailer_name or retailer_name in store_name_lower:
                        retailer_id = retailer.get("id")
                        break
                
                # Fallback to retailer ID map
                if not retailer_id:
                    retailer_id = self.RETAILER_ID_MAP.get(store_name.lower().replace(" ", "_"))
            
            # Build search URL
            url = f"{self.API_BASE_URL}/products/search"
            params = {
                "query": query,
                "zipcode": zipcode,
                "country": "US",
                "limit": min(num_results, 50),  # Instacart API limit
            }
            
            if retailer_id:
                params["retailer_id"] = retailer_id
            
            async with session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    products_data = data.get("data", [])
                    
                    # Normalize products
                    normalized_products = []
                    for product in products_data[:num_results]:
                        # Get retailer info if available
                        retailer_info = None
                        if retailer_id:
                            retailer_info = next((r for r in retailers if r.get("id") == retailer_id), None)
                        
                        normalized = self._normalize_product(product, retailer_info)
                        
                        # Add location data if requested
                        if include_location and retailer_info:
                            normalized.update({
                                "store_address": retailer_info.get("address"),
                                "store_city": retailer_info.get("city"),
                                "store_state": retailer_info.get("state"),
                                "store_zipcode": zipcode,
                            })
                        
                        normalized_products.append(normalized)
                    
                    # Cache for 15 minutes (Instacart has real-time pricing)
                    await self.cache.set_json(cache_key, normalized_products, ttl_seconds=900)
                    logger.info(f"✅ Found {len(normalized_products)} products via Instacart for '{query}'")
                    return normalized_products
                elif response.status == 429:
                    logger.warning("⚠️ Instacart API rate limit exceeded")
                    return []
                else:
                    error_text = await response.text()
                    logger.warning(f"⚠️ Instacart API error {response.status}: {error_text[:200]}")
                    return []
        except Exception as e:
            logger.error(f"❌ Instacart search failed: {e}")
            return []
    
    async def search_stores_in_zipcode(self, store_chain: str, zipcode: str) -> List[Dict[str, Any]]:
        """
        Search for store locations in a zipcode
        
        Args:
            store_chain: Store chain name (e.g., "Target", "Walmart")
            zipcode: ZIP code to search
            
        Returns:
            List of store location dictionaries
        """
        if not self.is_available():
            return []
        
        # Check cache
        cache_key = f"instacart:stores:{store_chain}:{zipcode}"
        cached = await self.cache.get_json(cache_key)
        if cached:
            return cached
        
        try:
            # Get retailers for this zipcode
            retailers = await self.get_retailers(zipcode)
            
            # Filter by store chain
            store_name_lower = store_chain.lower()
            matching_stores = []
            
            for retailer in retailers:
                retailer_name = retailer.get("name", "").lower()
                # Check if retailer name matches store chain
                if store_name_lower in retailer_name or retailer_name in store_name_lower:
                    # Check if we have store locations
                    stores = retailer.get("stores", [])
                    if stores:
                        for store in stores:
                            store_location = {
                                "store_id": retailer.get("id", "").lower().replace(" ", "_"),
                                "retailer_store_id": store.get("id"),
                                "store_name": f"{retailer.get('name')} {store.get('name', '')}".strip(),
                                "address": store.get("address", {}).get("street"),
                                "city": store.get("address", {}).get("city"),
                                "state": store.get("address", {}).get("state"),
                                "zipcode": store.get("address", {}).get("zipcode") or zipcode,
                                "phone": store.get("phone"),
                                "hours": store.get("hours"),
                                "services": ["delivery", "pickup"] if store.get("delivery_enabled") else ["pickup"],
                                "status": "active",
                                "source": "instacart",
                            }
                            matching_stores.append(store_location)
                    else:
                        # If no specific stores, create a generic location entry
                        store_location = {
                            "store_id": retailer.get("id", "").lower().replace(" ", "_"),
                            "retailer_store_id": retailer.get("id"),
                            "store_name": retailer.get("name"),
                            "address": None,
                            "city": None,
                            "state": None,
                            "zipcode": zipcode,
                            "phone": retailer.get("phone"),
                            "hours": None,
                            "services": ["delivery", "pickup"],
                            "status": "active",
                            "source": "instacart",
                        }
                        matching_stores.append(store_location)
            
            # Cache for 1 hour
            await self.cache.set_json(cache_key, matching_stores, ttl_seconds=3600)
            logger.info(f"✅ Found {len(matching_stores)} {store_chain} locations via Instacart near {zipcode}")
            return matching_stores
            
        except Exception as e:
            logger.error(f"❌ Failed to search stores: {e}")
            return []

