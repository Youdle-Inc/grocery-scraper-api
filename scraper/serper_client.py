#!/usr/bin/env python3
"""
Serper API Client for Grocery Product Search
Uses Serper (Google Search API) to find products across stores
"""

import asyncio
import os
import logging
import aiohttp
import re
from typing import Dict, List, Any, Optional
from dotenv import load_dotenv
from scraper.cache import Cache

load_dotenv()
logger = logging.getLogger(__name__)


class SerperClient:
    """Serper API client for grocery product search"""
    
    API_BASE_URL = "https://google.serper.dev"
    
    # Store display name mapping
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
    
    # Store domain mapping for site-specific searches
    STORE_DOMAINS = {
        "target": "target.com",
        "walmart": "walmart.com",
        "kroger": "kroger.com",
        "costco": "costco.com",
        "albertsons": "albertsons.com",
        "safeway": "safeway.com",
        "publix": "publix.com",
        "heb": "heb.com",
        "aldi": "aldi.us",
        "sams_club": "samsclub.com",
        "whole_foods": "wholefoodsmarket.com",
        "meijer": "meijer.com",
        "winco": "wincofoods.com",
        "bjs": "bjs.com",
        "dollar_general": "dollargeneral.com",
        "dollar_tree": "dollartree.com",
        "trader_joes": "traderjoes.com",
        "hy_vee": "hy-vee.com",
        "wegmans": "wegmans.com",
        "sprouts": "sprouts.com",
        "giant_eagle": "gianteagle.com",
    }
    
    def __init__(self, api_key: Optional[str] = None):
        """Initialize Serper client"""
        self.api_key = api_key or os.getenv("SERPER_API_KEY")
        self.cache = Cache()
        
        if not self.api_key:
            logger.warning("⚠️ No SERPER_API_KEY found in environment - please set it in .env file")
        else:
            logger.info("✅ Serper client initialized")
    
    def is_available(self) -> bool:
        """Check if Serper client is available"""
        return self.api_key is not None
    
    async def _get_session(self) -> aiohttp.ClientSession:
        """
        Create a new aiohttp session for each request.
        This is safer for serverless environments where event loops can be closed between requests.
        """
        if not self.api_key:
            raise ValueError("SERPER_API_KEY is not set. Please configure it in your environment variables.")
        
        # Create a new session for each request (safer for serverless)
        session = aiohttp.ClientSession(
            headers={
                "X-API-KEY": self.api_key,
                "Content-Type": "application/json",
            },
            timeout=aiohttp.ClientTimeout(total=30)
        )
        return session
    
    def get_store_display_name(self, store_id: Optional[str]) -> str:
        """Get display name for store ID"""
        if not store_id:
            return "Unknown Store"
        store_id_lower = store_id.lower().strip()
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
        """
        if not availability_text:
            return "CHECK_STORE"
        
        availability_lower = str(availability_text).lower().strip()
        
        # Out of stock indicators
        out_of_stock_patterns = [
            "out of stock", "sold out", "unavailable", "not available",
            "currently unavailable", "temporarily unavailable",
        ]
        
        for pattern in out_of_stock_patterns:
            if pattern in availability_lower:
                return "OUT_OF_STOCK"
        
        # Low stock indicators
        low_stock_patterns = [
            "low stock", "limited availability", "few left",
            "almost gone", "substituteable",
        ]
        
        for pattern in low_stock_patterns:
            if pattern in availability_lower:
                return "LOW_STOCK"
        
        # In stock indicators
        in_stock_patterns = [
            "in stock", "available", "add to cart", "buy now",
        ]
        
        for pattern in in_stock_patterns:
            if pattern in availability_lower:
                return "IN_STOCK"
        
        return "CHECK_STORE"
    
    def _normalize_product(self, result: Dict[str, Any], store_name: Optional[str] = None) -> Dict[str, Any]:
        """
        Normalize Serper search result to our schema with enhanced extraction
        """
        title = result.get("title", "")
        link = result.get("link", "")
        snippet = result.get("snippet", "")
        full_text = f"{title} {snippet}".lower()
        
        # Extract store name and ID from link or use provided
        detected_store = store_name
        detected_store_id = None
        if not detected_store and link:
            for store_id, domain in self.STORE_DOMAINS.items():
                if domain in link.lower():
                    detected_store = self.get_store_display_name(store_id)
                    detected_store_id = store_id
                    break
        
        # If store_name provided but no store_id, derive it
        if detected_store and not detected_store_id:
            store_name_lower = detected_store.lower().replace(" ", "_")
            detected_store_id = store_name_lower
            # Try to find matching store_id
            for store_id in self.STORE_DISPLAY_NAMES.keys():
                if store_id.replace("_", " ") == store_name_lower.replace("_", " "):
                    detected_store_id = store_id
                    break
        
        # Extract price from snippet or title (multiple formats) - enhanced
        price = None
        price_patterns = [
            r'\$(\d+\.?\d{0,2})',  # $5.99, $5, $5.9
            r'(\d+\.?\d{0,2})\s*USD',  # 5.99 USD
            r'price[:\s]+(\d+\.?\d{0,2})',  # Price: 5.99
            r'(\d+\.?\d{0,2})\s*dollars?',  # 5.99 dollars
            r'(\d+\.?\d{0,2})\s*\$',  # 5.99 $
            r'\$\s*(\d+\.?\d{0,2})',  # $ 5.99 (with space)
            r'(\d+\.?\d{0,2})\s*per\s*(?:each|unit|item|lb|oz|gallon)',  # 5.99 per each
            r'(\d+\.?\d{0,2})\s*ea\.?',  # 5.99 ea.
            r'(\d+\.?\d{0,2})\s*each',  # 5.99 each
        ]
        
        # Search in snippet first (more reliable), then title
        search_text = snippet + " " + title
        for pattern in price_patterns:
            price_match = re.search(pattern, search_text, re.IGNORECASE)
            if price_match:
                try:
                    price_val = float(price_match.group(1))
                    # Validate price is reasonable (between $0.01 and $1000)
                    if 0.01 <= price_val <= 1000:
                        price = price_val
                        break
                except:
                    pass
        
        # If no price found, try to extract from structured data
        if price is None and "pagemap" in result:
            pagemap = result.get("pagemap", {})
            # Check for price in structured data
            if "offer" in pagemap:
                for offer in pagemap["offer"]:
                    if "price" in offer:
                        try:
                            price_str = offer["price"]
                            price_val = float(re.search(r'(\d+\.?\d*)', price_str).group(1))
                            if 0.01 <= price_val <= 1000:
                                price = price_val
                                break
                        except:
                            pass
        
        # Extract brand from title (common patterns)
        brand = None
        # Pattern: "Brand Name Product Name" or "Product Name - Brand Name"
        brand_patterns = [
            r'^([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)\s+',  # Start with capitalized words
            r'-\s*([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)',  # After dash
            r'by\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)',  # "by Brand"
        ]
        for pattern in brand_patterns:
            brand_match = re.search(pattern, title)
            if brand_match:
                potential_brand = brand_match.group(1).strip()
                # Filter out common non-brands
                if potential_brand.lower() not in ['target', 'walmart', 'kroger', 'whole foods', 'good', 'gather']:
                    brand = potential_brand
                    break
        
        # Extract quantity/size from title or snippet
        quantity = None
        size = None
        quantity_patterns = [
            r'(\d+\s*(?:oz|ounce|ounces|fl\s*oz|fluid\s*ounce|fluid\s*ounces|lb|pound|pounds|gallon|gallons|liter|liters|ml|milliliter|milliliters|count|ct|pack|packs|piece|pieces))',
            r'(\d+\s*x\s*\d+\s*(?:oz|ounce|lb|pound|count))',  # 12 x 16 oz
            r'((?:half|quarter|full)\s*(?:gallon|gallon|oz|ounce))',
        ]
        for pattern in quantity_patterns:
            qty_match = re.search(pattern, full_text, re.IGNORECASE)
            if qty_match:
                quantity = qty_match.group(1).strip()
                size = quantity
                break
        
        # Extract category from query context or infer from product name
        category = None
        category_keywords = {
            'dairy': ['milk', 'cheese', 'yogurt', 'butter', 'cream'],
            'produce': ['apple', 'banana', 'orange', 'lettuce', 'tomato', 'onion', 'carrot', 'fruit', 'vegetable'],
            'meat': ['beef', 'chicken', 'pork', 'fish', 'meat', 'steak', 'ground', 'sausage', 'bacon'],
            'bakery': ['bread', 'bagel', 'muffin', 'cake', 'cookie', 'pastry'],
            'beverages': ['juice', 'soda', 'water', 'coffee', 'tea', 'drink'],
            'frozen': ['frozen', 'ice cream', 'pizza'],
            'snacks': ['chip', 'cracker', 'snack', 'pretzel'],
        }
        for cat, keywords in category_keywords.items():
            if any(kw in full_text for kw in keywords):
                category = cat
                break
        
        # Extract image if available
        image_url = None
        if "imageUrl" in result:
            image_url = result.get("imageUrl")
        elif "pagemap" in result and "cse_image" in result["pagemap"]:
            images = result["pagemap"]["cse_image"]
            if images and len(images) > 0:
                image_url = images[0].get("src")
        
        # Extract product name (clean title)
        product_name = title
        # Remove store name from title if present
        if detected_store:
            product_name = product_name.replace(detected_store, "").strip()
            product_name = product_name.replace(" - ", "").strip()
            product_name = product_name.replace(" | ", "").strip()
        
        # Remove brand from product name if we extracted it
        if brand and brand.lower() in product_name.lower():
            product_name = product_name.replace(brand, "").strip()
            product_name = re.sub(r'\s+', ' ', product_name)  # Clean up extra spaces
        
        return {
            "id": f"serper_{hash(link)}",
            "name": product_name,
            "product_name": product_name,
            "brand": brand,
            "price": price,
            "currency": "USD",
            "quantity": quantity,
            "size": size or quantity,
            "availability": "CHECK_STORE",  # Serper doesn't provide availability
            "image_url": image_url,
            "product_url": link,
            "description": snippet,
            "category": category,
            "store_name": detected_store or "Unknown Store",
            "store_id": detected_store_id,
            "source": "serper",
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
        Search for products using Serper API
        
        Args:
            query: Product search query
            store_name: Optional store/retailer name to filter by
            zipcode: ZIP code for location scoping (added to query)
            num_results: Maximum number of results to return
            include_location: Whether to include location data
            context: Search context (unused for Serper)
            
        Returns:
            List of normalized product dictionaries
        """
        if not self.is_available():
            logger.warning("⚠️ Serper client not available")
            return []
        
        # Build search query - optimize for product pages
        search_query = query
        
        # Add store-specific product search terms
        if store_name:
            store_display = self.get_store_display_name(store_name)
            # Simple query with store name - let siteSearch filter handle domain
            search_query = f'"{query}" {store_display}'
        else:
            # General product search across grocery stores
            search_query = f'"{query}" grocery product'
        
        # Don't add zipcode to query - it makes results too location-focused
        # Instead, we'll filter by store domain
        
        # Add site filter if store specified
        site_filter = None
        if store_name:
            store_id_lower = store_name.lower().replace(" ", "_")
            site_filter = self.STORE_DOMAINS.get(store_id_lower)
        
        # Check cache
        cache_key = f"serper:products:{search_query}:{num_results}"
        cached = await self.cache.get_json(cache_key)
        if cached:
            logger.debug(f"Cache hit for Serper search: {query}")
            return cached
        
        session = None
        try:
            session = await self._get_session()
            url = f"{self.API_BASE_URL}/search"
            
            payload = {
                "q": search_query,
                "num": min(num_results, 20),  # Serper API limit
            }
            
            # Add site filter if available
            if site_filter:
                payload["siteSearch"] = site_filter
            
            async with session.post(url, json=payload) as response:
                if response.status == 200:
                    data = await response.json()
                    
                    # Extract organic results
                    organic_results = data.get("organic", [])
                    
                    # Normalize products
                    normalized_products = []
                    for result in organic_results[:num_results * 2]:  # Get more to filter
                        # Filter out non-product pages (store locators, category pages, etc.)
                        link = result.get("link", "").lower()
                        title = result.get("title", "").lower()
                        
                        # Only skip obvious store locator pages
                        skip_patterns = [
                            "/store-locator", "/find-stores", "/sl/", "/location/", "/locator",
                            "store locator", "find stores", "locations", "store directory",
                            "/blog/", "/q/", "/pb/", "/c/", "/browse/", "/search",  # Category/search pages
                        ]
                        
                        # Skip if link or title matches skip patterns
                        if any(skip in link or skip in title for skip in skip_patterns):
                            continue
                        
                        # Skip third-party sites
                        if any(site in link for site in ["yelp.com", "findhelp.org", "realmilk.com"]):
                            continue
                        
                        normalized = self._normalize_product(result, store_name)
                        
                        # Skip if product name looks like a page title (too generic)
                        product_name = normalized.get("name", "")
                        if len(product_name) < 3:
                            continue
                        
                        # Skip very generic titles
                        generic_titles = ["find", "search", "store", "location", "directory"]
                        if product_name.lower() in generic_titles:
                            continue
                        
                        # Add location data if requested
                        if include_location and zipcode:
                            normalized.update({
                                "store_zipcode": zipcode,
                                "store_address": None,  # Serper doesn't provide addresses
                                "store_city": None,
                                "store_state": None,
                            })
                        
                        # Ensure store_id is set
                        if not normalized.get("store_id") and store_name:
                            store_id_lower = store_name.lower().replace(" ", "_")
                            normalized["store_id"] = store_id_lower
                        
                        normalized_products.append(normalized)
                        
                        # Stop when we have enough valid products
                        if len(normalized_products) >= num_results:
                            break
                    
                    # Cache for 15 minutes
                    await self.cache.set_json(cache_key, normalized_products, ttl_seconds=900)
                    logger.info(f"✅ Found {len(normalized_products)} products via Serper for '{query}'")
                    return normalized_products
                elif response.status == 429:
                    logger.warning("⚠️ Serper API rate limit exceeded")
                    return []
                else:
                    error_text = await response.text()
                    logger.warning(f"⚠️ Serper API error {response.status}: {error_text[:200]}")
                    # Log API key status for debugging (without exposing the key)
                    if response.status == 403:
                        logger.error(f"❌ Serper API 403 Unauthorized - Check if SERPER_API_KEY is set in deployment environment")
                        logger.error(f"❌ API key present: {bool(self.api_key)}, key length: {len(self.api_key) if self.api_key else 0}")
                    return []
        except Exception as e:
            logger.error(f"❌ Serper search failed: {e}")
            return []
        finally:
            # Always close the session to prevent "Event loop is closed" errors
            if session and not session.closed:
                try:
                    await session.close()
                except Exception as e:
                    logger.debug(f"Error closing session: {e}")
    
    async def search_stores_in_zipcode(self, store_chain: str, zipcode: str) -> List[Dict[str, Any]]:
        """
        Search for store locations in a zipcode using Serper
        
        Args:
            store_chain: Store chain name (e.g., "Target", "Walmart")
            zipcode: ZIP code to search
            
        Returns:
            List of store location dictionaries
        """
        if not self.is_available():
            return []
        
        # Check cache
        cache_key = f"serper:stores:{store_chain}:{zipcode}"
        cached = await self.cache.get_json(cache_key)
        if cached:
            return cached
        
        session = None
        try:
            session = await self._get_session()
            url = f"{self.API_BASE_URL}/search"
            
            # Build search query for store locations
            search_query = f"{store_chain} store locations zipcode {zipcode}"
            
            payload = {
                "q": search_query,
                "num": 10,
            }
            
            # Add site filter
            store_id_lower = store_chain.lower().replace(" ", "_")
            site_filter = self.STORE_DOMAINS.get(store_id_lower)
            if site_filter:
                payload["siteSearch"] = site_filter
            
            async with session.post(url, json=payload) as response:
                if response.status == 200:
                    data = await response.json()
                    organic_results = data.get("organic", [])
                    
                    stores = []
                    for result in organic_results:
                        title = result.get("title", "")
                        link = result.get("link", "")
                        snippet = result.get("snippet", "")
                        
                        # Skip store locator pages - they don't have real addresses
                        if any(skip in link.lower() for skip in ["/store-locator", "/find-stores", "/locations", "/stores/", "/sl/"]):
                            continue
                        if any(skip in title.lower() for skip in ["store locator", "find stores", "locations", "store directory"]):
                            continue
                        
                        # Extract full address from snippet/title using regex
                        address = None
                        city = None
                        state = None
                        
                        # Pattern: "123 Main St, City, State ZIP" or "123 Main St, City, State"
                        address_pattern = r'(\d+\s+[^,]+(?:Street|St|Avenue|Ave|Road|Rd|Boulevard|Blvd|Drive|Dr|Lane|Ln|Way|Court|Ct|Place|Pl)[^,]*),\s*([^,]+?)(?:,\s*([A-Z]{2})(?:\s+(\d{5}))?|$)'
                        match = re.search(address_pattern, snippet + " " + title, re.IGNORECASE)
                        if match:
                            address = match.group(1).strip()
                            city = match.group(2).strip()
                            # Clean up city - remove common suffixes
                            city = re.sub(r'\s*(just|about|near|from|mi|miles?|away).*$', '', city, flags=re.IGNORECASE).strip()
                            if match.group(3):
                                state = match.group(3).strip().upper()
                        else:
                            # Try simpler pattern: "City, State" or "City State"
                            city_state_pattern = r'([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?),\s*([A-Z]{2})'
                            match = re.search(city_state_pattern, snippet + " " + title)
                            if match:
                                city = match.group(1).strip()
                                state = match.group(2).strip().upper()
                                # Try to get street address separately
                                street_match = re.search(r'(\d+\s+[^,]+)', snippet)
                                if street_match:
                                    address = street_match.group(1).strip()
                        
                        # If still no address, try to extract from snippet parts
                        if not address and snippet:
                            # Try to extract meaningful address from snippet
                            parts = snippet.split(",")
                            if len(parts) >= 2:
                                potential_address = parts[0].strip()
                                # Only use if it looks like an address (has a number)
                                if re.search(r'\d+', potential_address):
                                    address = potential_address
                                if len(parts) >= 2 and not city:
                                    city = parts[1].strip()
                                if len(parts) >= 3 and not state:
                                    state_match = re.search(r'([A-Z]{2})', parts[2])
                                    if state_match:
                                        state = state_match.group(1)
                        
                        # Skip if we didn't get a valid address (don't add generic store locator results)
                        # Require both address and city for quality
                        if not address or not city:
                            continue
                        
                        # Validate address quality - require street number
                        if address:
                            # Check if address looks valid (has street number and name)
                            if not re.search(r'^\d+\s+', address):
                                continue  # Invalid address format, skip
                        
                        # Validate ZIP code matches (if extracted ZIP doesn't match requested, skip)
                        # This helps filter out wrong addresses
                        extracted_zip = None
                        if state:
                            zip_match = re.search(r'\b(\d{5})\b', snippet + " " + title)
                            if zip_match:
                                extracted_zip = zip_match.group(1)
                                # If ZIP doesn't match requested ZIP (within reasonable distance), skip
                                # Allow some flexibility (same city/area)
                                if extracted_zip != zipcode:
                                    # Still allow if city matches (might be nearby)
                                    pass  # Keep it for now, but could be stricter
                        
                        store_location = {
                            "store_id": store_id_lower,
                            "store_name": self.get_store_display_name(store_id_lower),
                            "address": address,
                            "city": city,
                            "state": state or "IL",  # Default to IL if not found
                            "zipcode": extracted_zip or zipcode,  # Use extracted ZIP or requested
                            "phone": None,
                            "hours": None,
                            "services": ["in-store", "pickup"],
                            "status": "active",
                            "source": "serper",
                            "website": link,
                        }
                        stores.append(store_location)
                    
                    # Cache for 1 hour
                    await self.cache.set_json(cache_key, stores, ttl_seconds=3600)
                    logger.info(f"✅ Found {len(stores)} {store_chain} locations via Serper near {zipcode}")
                    return stores
                else:
                    logger.warning(f"⚠️ Serper API error: {response.status}")
                    # Log API key status for debugging (without exposing the key)
                    if response.status == 403:
                        logger.error(f"❌ Serper API 403 Unauthorized - Check if SERPER_API_KEY is set in deployment environment")
                        logger.error(f"❌ API key present: {bool(self.api_key)}, key length: {len(self.api_key) if self.api_key else 0}")
                    return []
        except Exception as e:
            logger.error(f"❌ Failed to search stores: {e}")
            return []
        finally:
            # Always close the session to prevent "Event loop is closed" errors
            if session and not session.closed:
                try:
                    await session.close()
                except Exception as e:
                    logger.debug(f"Error closing session: {e}")

