"""
Target RapidAPI Client for official Target product search
"""
import os
import logging
import aiohttp
from typing import List, Dict, Any, Optional
import asyncio

logger = logging.getLogger(__name__)

class TargetAPIClient:
    """Client for Target RapidAPI"""
    
    BASE_URL = "https://target1.p.rapidapi.com"
    
    def __init__(self):
        """Initialize Target API client with API keys"""
        self.api_keys = []
        
        # Get RapidAPI key from environment
        rapidapi_key = os.getenv("RAPIDAPI")
        if rapidapi_key:
            self.api_keys.append(rapidapi_key)
            logger.info("✅ Found RAPIDAPI key")
        
        # RapidAPI Host
        self.rapidapi_host = os.getenv("RAPID_API_HOST", "target1.p.rapidapi.com")
        self.current_key_index = 0
        
        if not self.api_keys:
            logger.warning("⚠️ No Target API keys found. Target API will be unavailable.")
        else:
            logger.info(f"✅ Target API initialized with {len(self.api_keys)} key(s), host: {self.rapidapi_host}")
    
    def is_available(self) -> bool:
        """Check if Target API is available"""
        return len(self.api_keys) > 0
    
    def _get_headers(self) -> Dict[str, str]:
        """Get headers with current API key"""
        if not self.api_keys:
            return {}
        
        # Rotate to next key
        key = self.api_keys[self.current_key_index]
        self.current_key_index = (self.current_key_index + 1) % len(self.api_keys)
        
        return {
            "X-RapidAPI-Key": key,
            "X-RapidAPI-Host": self.rapidapi_host
        }
    
    async def get_stores(self, zipcode: str, radius: int = 10) -> List[Dict[str, Any]]:
        """Get Target stores near a zipcode"""
        if not self.is_available():
            return []
        
        url = f"{self.BASE_URL}/stores/v2/list?place={zipcode}"
        headers = self._get_headers()
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers, timeout=aiohttp.ClientTimeout(total=10)) as response:
                    if response.status != 200:
                        logger.warning(f"Target stores API returned status {response.status}")
                        return []
                    
                    data = await response.json()
                    if "errors" in data:
                        logger.error(f"Target API error: {data['errors']}")
                        return []
                    
                    stores = []
                    nearby_stores = data.get("data", {}).get("nearby_stores", {}).get("stores", [])
                    for store in nearby_stores:
                        if store.get("distance", 999) <= radius:
                            stores.append({
                                "store_id": str(store.get("location_id")),
                                "retailer_store_id": str(store.get("location_id")),
                                "name": store.get("name", "Target"),
                                "address": store.get("address", {}).get("address_line1", ""),
                                "city": store.get("address", {}).get("city", ""),
                                "state": store.get("address", {}).get("state", ""),
                                "zipcode": store.get("address", {}).get("postal_code", zipcode),
                                "distance": store.get("distance", 0),
                                "latitude": store.get("geographic_coordinates", {}).get("latitude"),
                                "longitude": store.get("geographic_coordinates", {}).get("longitude"),
                            })
                    
                    return stores
        except Exception as e:
            logger.error(f"Error fetching Target stores: {e}")
            return []
    
    async def search_products(
        self,
        query: str,
        store_id: str,
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """Search for products at a specific Target store"""
        if not self.is_available():
            return []
        
        # Special handling for baby formula
        if query.lower() == "baby formula":
            url = f"{self.BASE_URL}/products/v2/list?store_id={store_id}&category=5xtkh&offset=0&default_purchasability_filter=true&sort_by=relevance"
        else:
            url = f"{self.BASE_URL}/products/v2/list?store_id={store_id}&keyword={query}&offset=0&default_purchasability_filter=true&sort_by=relevance"
        
        headers = self._get_headers()
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers, timeout=aiohttp.ClientTimeout(total=10)) as response:
                    if response.status != 200:
                        logger.warning(f"Target products API returned status {response.status}")
                        return []
                    
                    data = await response.json()
                    if "errors" in data:
                        logger.error(f"Target API error: {data['errors']}")
                        return []
                    
                    # Extract products from response
                    products = []
                    products_data = {}
                    
                    try:
                        products_data = data.get("data", {}).get("search", {}).get("search_response", {}).get("buckets", [{}])[0].get("products", {})
                    except (KeyError, IndexError):
                        products_data = data.get("data", {}).get("search", {}).get("products", {})
                    
                    if not products_data:
                        return []
                    
                    count = 0
                    for item in products_data.values():
                        if count >= limit:
                            break
                        
                        # Skip items without fulfillment info
                        if "fulfillment" not in item:
                            continue
                        
                        fulfillment = item.get("fulfillment", {}).get("store_options", [{}])[0]
                        in_store_status = fulfillment.get("in_store_only", {}).get("availability_status", "")
                        
                        # Skip discontinued or not sold items
                        if in_store_status in ["NOT_SOLD_IN_STORE", "DISCONTINUED"]:
                            continue
                        
                        # Map availability
                        availability_map = {
                            "IN_STOCK": "In Stock",
                            "LIMITED_STOCK": "Limited Stock"
                        }
                        availability = availability_map.get(in_store_status, "Out of Stock")
                        
                        # Extract product data
                        item_data = item.get("item", {})
                        product_desc = item_data.get("product_description", {})
                        enrichment = item_data.get("enrichment", {})
                        price_data = item.get("price", {})
                        
                        product = {
                            "name": product_desc.get("title", ""),
                            "brand": None,  # Target API doesn't always provide brand separately
                            "price": price_data.get("current_retail"),
                            "currency": "USD",
                            "quantity": None,  # Extract from title if possible
                            "size": None,
                            "availability": availability,
                            "product_url": enrichment.get("buy_url", ""),
                            "image_url": enrichment.get("images", {}).get("primary_image_url", ""),
                            "store_id": "target",
                            "store_name": "Target",
                            "store_address": None,  # Would need to fetch separately
                            "store_city": None,
                            "store_state": None,
                            "store_zipcode": None,
                            "rating": None,
                            "review_count": None,
                            "description": product_desc.get("downstream_description", ""),
                            "category": None,
                            "source": ["target_api"],
                            "tcin": str(item_data.get("tcin", ""))  # Target's product ID
                        }
                        
                        products.append(product)
                        count += 1
                    
                    logger.info(f"✅ Target API returned {len(products)} products")
                    return products
                    
        except Exception as e:
            logger.error(f"Error searching Target products: {e}", exc_info=True)
            return []
    
    async def search_products_multiple_stores(
        self,
        query: str,
        zipcode: str,
        radius: int = 10,
        limit_per_store: int = 10
    ) -> List[Dict[str, Any]]:
        """Search products across multiple Target stores near a zipcode"""
        if not self.is_available():
            return []
        
        # Get stores first
        stores = await self.get_stores(zipcode, radius)
        if not stores:
            logger.warning(f"No Target stores found near {zipcode}")
            return []
        
        # Search each store concurrently
        tasks = []
        for store in stores[:5]:  # Limit to top 5 stores
            store_id = store.get("retailer_store_id")
            tasks.append(self.search_products(query, store_id, limit_per_store))
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Combine and deduplicate products by TCIN
        all_products = []
        seen_tcins = set()
        
        for store_products in results:
            if isinstance(store_products, Exception):
                logger.warning(f"Error fetching from store: {store_products}")
                continue
            
            for product in store_products:
                tcin = product.get("tcin")
                if tcin and tcin not in seen_tcins:
                    seen_tcins.add(tcin)
                    all_products.append(product)
        
        return all_products[:limit_per_store * len(stores[:5])]  # Limit total results

