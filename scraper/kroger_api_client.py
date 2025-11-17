"""
Kroger Official API Client for product search
"""
import os
import logging
import aiohttp
import base64
from typing import List, Dict, Any, Optional
import asyncio
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

class KrogerAPIClient:
    """Client for Kroger Official API"""
    
    BASE_URL = "https://api.kroger.com/v1"
    
    def __init__(self):
        """Initialize Kroger API client"""
        # Kroger uses OAuth2 client credentials
        # Try environment variables first
        self.client_id = os.getenv("KROGER_CLIENT_ID")
        self.client_secret = os.getenv("KROGER_CLIENT_SECRET")
        
        # Fallback: use the hardcoded base64 credentials from TypeScript code
        # The TS code uses: 'Basic eW91ZGxlcHJvZHVjdGlvbi03MDY5ODM5MzY5MTg1YTdkZmMzMmFjY2ZmYmE1MjcwYTMzNTEzODc4MTc3NTY1NDgyNTQ6d3B4T0hWM1cxWjdqMmV0NzJCVVhqSEVMUGtxalNWcUdnMGNMbjhmTQ=='
        if not self.client_id or not self.client_secret:
            # Decode the base64 string to get client_id:client_secret
            import base64
            try:
                decoded = base64.b64decode("eW91ZGxlcHJvZHVjdGlvbi03MDY5ODM5MzY5MTg1YTdkZmMzMmFjY2ZmYmE1MjcwYTMzNTEzODc4MTc3NTY1NDgyNTQ6d3B4T0hWM1cxWjdqMmV0NzJCVVhqSEVMUGtxalNWcUdnMGNMbjhmTQ==").decode()
                if ":" in decoded:
                    self.client_id, self.client_secret = decoded.split(":", 1)
                    logger.info("✅ Using fallback Kroger credentials from TypeScript code")
                else:
                    self.client_id = None
                    self.client_secret = None
            except Exception as e:
                logger.warning(f"⚠️ Failed to decode fallback Kroger credentials: {e}")
                self.client_id = None
                self.client_secret = None
        
        self.access_token = None
        self.token_expires_at = None
    
    def is_available(self) -> bool:
        """Check if Kroger API is available"""
        return self.client_id is not None and self.client_secret is not None
    
    async def _get_access_token(self) -> Optional[str]:
        """Get OAuth2 access token"""
        if not self.is_available():
            return None
        
        # Check if token is still valid
        if self.access_token and self.token_expires_at:
            if datetime.now() < self.token_expires_at:
                return self.access_token
        
        # Request new token
        auth_string = base64.b64encode(
            f"{self.client_id}:{self.client_secret}".encode()
        ).decode()
        
        url = f"{self.BASE_URL}/connect/oauth2/token?grant_type=client_credentials&scope=product.compact"
        headers = {
            "Content-Type": "application/x-www-form-urlencoded",
            "Authorization": f"Basic {auth_string}"
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(url, headers=headers, timeout=aiohttp.ClientTimeout(total=15)) as response:
                    if response.status != 200:
                        logger.error(f"Kroger auth failed with status {response.status}")
                        return None
                    
                    data = await response.json()
                    self.access_token = data.get("access_token")
                    expires_in = data.get("expires_in", 3600)
                    self.token_expires_at = datetime.now() + timedelta(seconds=expires_in - 60)  # Refresh 1 min early
                    
                    return self.access_token
        except Exception as e:
            logger.error(f"Error getting Kroger access token: {e}")
            return None
    
    async def get_stores(self, zipcode: str, radius: int = 10, limit: int = 5) -> List[Dict[str, Any]]:
        """Get Kroger stores near a zipcode"""
        if not self.is_available():
            return []
        
        token = await self._get_access_token()
        if not token:
            return []
        
        url = f"{self.BASE_URL}/locations?filter.zipCode.near={zipcode}&filter.radiusInMiles={radius}&filter.limit={limit}"
        headers = {
            "Accept": "application/json",
            "Authorization": f"Bearer {token}"
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers, timeout=aiohttp.ClientTimeout(total=15)) as response:
                    if response.status != 200:
                        logger.warning(f"Kroger stores API returned status {response.status}")
                        return []
                    
                    data = await response.json()
                    stores = []
                    
                    for store in data.get("data", []):
                        # Kroger API returns locationId and address at top level
                        address = store.get("address", {})
                        geolocation = store.get("geolocation", {})
                        
                        stores.append({
                            "store_id": store.get("locationId", ""),
                            "retailer_store_id": store.get("locationId", ""),
                            "name": store.get("name", "Kroger"),
                            "address": address.get("addressLine1", ""),
                            "city": address.get("city", ""),
                            "state": address.get("state", ""),
                            "zipcode": address.get("zipCode", zipcode),
                            "distance": None,  # Not provided by API
                            "latitude": geolocation.get("latitude"),
                            "longitude": geolocation.get("longitude"),
                        })
                    
                    return stores
        except Exception as e:
            logger.error(f"Error fetching Kroger stores: {e}")
            return []
    
    def _build_product_link(self, product_name: str, upc: str) -> str:
        """Build Kroger product link from name and UPC"""
        clean_name = "".join(c if c.isalnum() or c == " " else "" for c in product_name)
        hyphenated_name = clean_name.replace(" ", "-")
        return f"https://www.kroger.com/p/{hyphenated_name}/{upc}"
    
    async def search_products(
        self,
        query: str,
        store_id: str,
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """Search for products at a specific Kroger store"""
        if not self.is_available():
            return []
        
        token = await self._get_access_token()
        if not token:
            return []
        
        url = f"{self.BASE_URL}/products?filter.term={query}&filter.locationId={store_id}&filter.fulfillment=ais"
        headers = {
            "Accept": "application/json",
            "Authorization": f"Bearer {token}"
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers, timeout=aiohttp.ClientTimeout(total=20)) as response:
                    if response.status != 200:
                        logger.warning(f"Kroger products API returned status {response.status}")
                        return []
                    
                    data = await response.json()
                    products = []
                    
                    # Kroger API returns products directly in data array
                    for item in data.get("data", [])[:limit]:
                        # Product info is at top level of each item
                        upc = item.get("upc", item.get("productId", ""))
                        description = item.get("description", "")
                        
                        # Get price and availability from items array if available
                        price = None
                        availability = "CHECK_STORE"
                        if "items" in item and item["items"]:
                            first_item = item["items"][0]
                            price = first_item.get("price", {}).get("regular", None)
                            
                            # Extract availability from fulfillment.inStore
                            fulfillment = first_item.get("fulfillment", {})
                            in_store = fulfillment.get("inStore")
                            if in_store is True:
                                availability = "IN_STOCK"
                            elif in_store is False:
                                availability = "OUT_OF_STOCK"
                            # If inStore is None or not present, keep CHECK_STORE
                        
                        # Get image URL
                        image_url = None
                        if item.get("images"):
                            first_image = item["images"][0]
                            if first_image.get("sizes"):
                                image_url = first_image["sizes"][0].get("url", "")
                        
                        product_data = {
                            "name": description,
                            "brand": item.get("brand", ""),
                            "price": price,
                            "currency": "USD",
                            "quantity": None,  # Extract from description if possible
                            "size": None,
                            "availability": availability,
                            "product_url": self._build_product_link(description, upc),
                            "image_url": image_url,
                            "store_id": "kroger",
                            "store_name": "Kroger",
                            "store_address": None,
                            "store_city": None,
                            "store_state": None,
                            "store_zipcode": None,
                            "rating": None,
                            "review_count": None,
                            "description": description,
                            "category": item.get("categories", [""])[0] if item.get("categories") else None,
                            "source": ["kroger_api"],
                            "upc": upc
                        }
                        
                        products.append(product_data)
                    
                    logger.info(f"✅ Kroger API returned {len(products)} products")
                    return products
                    
        except Exception as e:
            logger.error(f"Error searching Kroger products: {e}", exc_info=True)
            return []
    
    async def search_products_multiple_stores(
        self,
        query: str,
        zipcode: str,
        radius: int = 10,
        limit_per_store: int = 10
    ) -> List[Dict[str, Any]]:
        """Search products across multiple Kroger stores near a zipcode"""
        if not self.is_available():
            return []
        
        # Get stores first
        stores = await self.get_stores(zipcode, radius)
        if not stores:
            logger.warning(f"No Kroger stores found near {zipcode}")
            return []
        
        # Search each store concurrently with individual timeouts
        async def search_with_timeout(store_id: str, query: str, limit: int):
            """Helper function to search a store with timeout"""
            try:
                return await asyncio.wait_for(
                    self.search_products(query, store_id, limit),
                    timeout=25  # Individual store timeout
                )
            except asyncio.TimeoutError:
                logger.warning(f"Kroger store {store_id} search timed out")
                return []
            except Exception as e:
                logger.error(f"Error searching Kroger store {store_id}: {e}")
                return []
        
        tasks = []
        for store in stores[:3]:  # Limit to top 3 stores to reduce timeout risk
            store_id = store.get("retailer_store_id")
            if store_id:
                # Use partial to properly capture values
                tasks.append(search_with_timeout(store_id, query, limit_per_store))
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Combine and deduplicate products by UPC
        all_products = []
        seen_upcs = set()
        
        for store_products in results:
            if isinstance(store_products, Exception):
                logger.warning(f"Error fetching from store: {store_products}")
                continue
            
            for product in store_products:
                upc = product.get("upc")
                if upc and upc not in seen_upcs:
                    seen_upcs.add(upc)
                    all_products.append(product)
        
        return all_products[:limit_per_store * len(stores[:5])]  # Limit total results

