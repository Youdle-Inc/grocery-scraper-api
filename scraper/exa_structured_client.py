#!/usr/bin/env python3
"""
Enhanced Exa API Client with structured data extraction for grocery products.
Uses Exa's search and contents APIs to get structured product information.
"""

import asyncio
import os
import logging
import re
import json
from typing import Dict, List, Any, Optional
from urllib.parse import parse_qs, urlencode, urlparse, urlunparse
from dotenv import load_dotenv

# Import Exa with error handling for missing dependencies
try:
    from exa_py import Exa
    EXA_AVAILABLE = True
except ImportError:
    EXA_AVAILABLE = False
    Exa = None
    logging.getLogger(__name__).warning("⚠️ exa_py not installed - Exa features will be unavailable")

# Prompt templates removed - using inline prompts

# Import store-specific extractors
from scraper.store_extractors import get_extractor

# Import geocoding service for zip code to city/state conversion
from scraper.geocoding_service import get_geocoding_service

load_dotenv()
# Initialize exa client lazily to avoid errors if API key is missing
exa = None
if EXA_AVAILABLE:
    try:
        api_key = os.getenv("EXA_API_KEY")
        if api_key:
            exa = Exa(api_key)
    except Exception as e:
        logging.getLogger(__name__).warning(f"⚠️ Failed to initialize global Exa client: {e}")
logger = logging.getLogger(__name__)

# Image cache will be initialized in main.py and passed in
_image_cache = None

def set_image_cache(cache):
    """Set the image cache instance"""
    global _image_cache
    _image_cache = cache


class ExaStructuredClient:
    """Enhanced Exa client for structured grocery product data extraction"""
    
    # Store domain mapping for search optimization
    STORE_DOMAINS = {
        "target": "target.com",
        "walmart": "walmart.com",
        "whole_foods": "wholefoodsmarket.com",
        "whole foods": "wholefoodsmarket.com",
        "aldi": "aldi.us",
        "costco": "costco.com",
        "kroger": "kroger.com",
        "sams_club": "samsclub.com",
        "trader_joes": "traderjoes.com",
        "trader joe's": "traderjoes.com",
        "safeway": "safeway.com",
        "albertsons": "albertsons.com",
        "publix": "publix.com",
        "heb": "heb.com",
        "wegmans": "wegmans.com",
    }
    
    def __init__(self, api_key: Optional[str] = None):
        """Initialize Exa client"""
        self.api_key = api_key or os.getenv("EXA_API_KEY")
        self._client = None
        
        if not EXA_AVAILABLE or Exa is None:
            logger.warning("⚠️ exa_py not available - Exa features will be disabled")
            return
        
        if not self.api_key:
            logger.warning("⚠️ No EXA_API_KEY found in environment")
        else:
            try:
                self._client = Exa(self.api_key)
                logger.info("✅ Exa structured client initialized")
            except Exception as e:
                logger.error(f"❌ Failed to initialize Exa client: {e}")
    
    def is_available(self) -> bool:
        """Check if Exa client is available"""
        return self._client is not None
    
    def _get_store_domain(self, store_name: str) -> Optional[str]:
        """Get domain for store name"""
        return self.STORE_DOMAINS.get(store_name.lower().strip())
    
    def _detect_product_category(self, query: str) -> str:
        """Detect product category from search query"""
        query_lower = query.lower()
        
        # Dairy products
        if any(word in query_lower for word in ["milk", "cheese", "yogurt", "butter", "cream", "dairy"]):
            return "dairy"
        
        # Produce
        if any(word in query_lower for word in ["apple", "banana", "orange", "lettuce", "tomato", "onion", "carrot", "produce", "fruit", "vegetable"]):
            return "produce"
        
        # Meat
        if any(word in query_lower for word in ["beef", "chicken", "pork", "fish", "meat", "steak", "ground", "sausage", "bacon"]):
            return "meat"
        
        # Frozen
        if any(word in query_lower for word in ["frozen", "ice cream", "pizza", "frozen dinner", "frozen meal"]):
            return "frozen"
        
        # Organic
        if any(word in query_lower for word in ["organic", "natural", "non-gmo", "free range"]):
            return "organic"
        
        return "generic"
    
    def _get_context_prompt(self, context: str) -> str:
        """Get context-specific prompt"""
        prompts = {
            "store_search": "Find grocery stores and supermarkets in the specified location. Focus on major chains and local stores.",
            "product_search": "Search for specific grocery products and food items only. Focus on product details, prices, and availability. EXCLUDE gift cards, gift certificates, prepaid cards, and non-food items. Only return actual food products.",
            "price_comparison": "Search for specific grocery products and food items for price comparison. Focus on product details, prices, and availability. EXCLUDE gift cards, gift certificates, prepaid cards, and non-food items. Only return actual food products.",
            "generic": "Search for grocery-related information including stores, products, and services."
        }
        return prompts.get(context, prompts["generic"])
    
    def _get_category_prompt(self, category: str) -> str:
        """Get category-specific prompt"""
        prompts = {
            "dairy": "Focus on dairy products like milk, cheese, yogurt, and butter.",
            "produce": "Focus on fresh fruits and vegetables, organic options, and seasonal items.",
            "meat": "Focus on fresh meat, poultry, seafood, and deli items.",
            "bakery": "Focus on bread, pastries, cakes, and baked goods.",
            "organic": "Focus on organic, natural, and health-focused products.",
            "generic": "Search for general grocery products and items."
        }
        return prompts.get(category, prompts["generic"])
    
    def _build_enhanced_query(self, query: str, store_name: str, zipcode: str, category: str) -> str:
        """Build enhanced search query with context"""
        # For better product results, make query more specific
        # Add common product variations to get individual product pages
        
        # Detect if query is a liquid product (milk, juice, etc.) that uses gallons
        liquid_products = ["milk", "juice", "water", "soda", "beer", "wine"]
        is_liquid = any(liquid in query.lower() for liquid in liquid_products)
        
        if store_name and store_name != "grocery store":
            if len(query.split()) == 1 and is_liquid:  # Single word liquid product like "milk"
                # Expand to find specific products with size
                base_query = f"{query} gallon {store_name} product"
            elif len(query.split()) == 1:  # Single word non-liquid product like "bread"
                # Just add store name, don't add "gallon"
                base_query = f"{query} {store_name} product"
            else:
                base_query = f"{query} {store_name}"
        else:
            if len(query.split()) == 1 and is_liquid:
                base_query = f"{query} gallon grocery product"
            elif len(query.split()) == 1:
                base_query = f"{query} grocery product"
            else:
                base_query = f"{query} grocery"
        
        # Add location information if zipcode is provided
        if zipcode:
            # Get city/state from zipcode FIRST for better location context
            # This is needed before building store-specific queries
            city, state = self._get_city_state_from_zipcode(zipcode)
            
            # For Wegmans, use single site: restriction with proper location context
            # Wegmans has stores in: NY, PA, NJ, VA, MD, MA, NC, CT, DC, DE
            if store_name and store_name.lower() == "wegmans":
                # Use single site: restriction (not double site:) for wegmans.com
                # Include location context to find stores/products in the zipcode area
                if city and state:
                    # Use city/state for better location matching
                    base_query = f"{base_query} site:wegmans.com near {city} {state} zipcode {zipcode}"
                else:
                    # Fallback: try to get state from zipcode prefix for Wegmans coverage areas
                    geocoding_service = get_geocoding_service()
                    state_abbr = geocoding_service.get_state_from_zipcode(zipcode)
                    if state_abbr:
                        state_name = geocoding_service.STATE_NAMES.get(state_abbr, state_abbr)
                        base_query = f"{base_query} site:wegmans.com near {state_name} {state_abbr} zipcode {zipcode}"
                    else:
                        # Last resort: just use zipcode
                        base_query = f"{base_query} site:wegmans.com zipcode {zipcode}"
            
            # For Costco, explicitly include zipcode in search to ensure location-based results
            # Costco filters products by warehouse/delivery location based on zipcode
            elif store_name and store_name.lower() == "costco":
                # Costco search URLs can include zipcode parameter
                if city and state:
                    base_query = f"{base_query} site:costco.com near {city} {state} zipcode {zipcode}"
                else:
                    base_query = f"{base_query} site:costco.com zipcode {zipcode}"
            
            # For other stores, add general location context
            else:
                if city and state:
                    # Use city, state, and zipcode for best location filtering
                    base_query = f"{base_query} near {city} {state} zipcode {zipcode}"
                else:
                    # For unknown zipcodes, use explicit zipcode location filtering
                    # Exa understands zipcodes well, so this should still work effectively
                    base_query = f"{base_query} location zipcode {zipcode} in {zipcode}"
        
        # Explicitly exclude gift cards and non-food items
        # Exa supports exclusion with minus sign
        base_query = f"{base_query} -gift card -giftcard -gift-card -non-food -non food"

        return base_query

    def _add_or_replace_query_param(self, url: str, key: str, value: str) -> str:
        """Return URL with query param added/replaced; fall back to original on error."""
        try:
            parsed = urlparse(url)
            qs = parse_qs(parsed.query)
            if qs.get(key) == [value]:
                return url
            qs[key] = [value]
            new_query = urlencode(qs, doseq=True)
            return urlunparse(parsed._replace(query=new_query))
        except Exception as e:
            logger.debug(f"Failed to add query param {key}={value} to {url[:80]}...: {e}")
            return url
    
    def _detect_search_context(self, query: str) -> str:
        """Detect search context from user query"""
        query_lower = query.lower()
        if any(word in query_lower for word in ['store', 'location', 'near', 'find']):
            return "store_search"
        elif any(word in query_lower for word in ['product', 'item', 'buy', 'price']):
            return "product_search"
        return "generic"
    
    def _get_optimized_prompt(self, query: str, context: str = None) -> str:
        """Get optimized prompt based on query context and category"""
        # Auto-detect context if not provided
        if not context:
            context = self._detect_search_context(query)
        
        # Get context-specific prompt
        context_prompt = self._get_context_prompt(context)
        
        # Get category-specific prompt
        category = self._detect_product_category(query)
        category_prompt = self._get_category_prompt(category)
        
        # Combine context and category prompts
        combined_prompt = f"{context_prompt}\n\nCategory-specific focus: {category_prompt}"
        
        # Add validation instructions
        validation_instructions = """
        
        Validation requirements:
        1. Price must be numeric (e.g., 4.99, not "$4.99")
        2. Quantity must include units (e.g., "64 fl oz", "1 gallon")
        3. Store address must be complete with city, state, ZIP
        4. Availability must be current status
        5. Ratings must be 1-5 scale
        6. If information is incomplete, mark confidence level and provide best available data
        
        CRITICAL EXCLUSIONS:
        - DO NOT include gift cards, gift certificates, prepaid cards, or e-gift cards
        - DO NOT include category pages or brand pages (e.g., "STK Steakhouse products at Target")
        - ONLY return actual food products and grocery items
        - Exclude non-food items like electronics, clothing, toys, etc.
        """
        
        return combined_prompt + validation_instructions
    
    async def search_products_structured(
        self,
        query: str,
        store_name: Optional[str] = None,
        zipcode: Optional[str] = None,
        num_results: int = 20,
        include_location: bool = True,
        context: str = None
    ) -> List[Dict[str, Any]]:
        """
        Search for grocery products with structured data extraction
        
        Args:
            query: Product search query
            store_name: Optional store name to filter results
            zipcode: Optional zipcode for location-based results
            num_results: Number of results to return
            include_location: Whether to include store location data
            
        Returns:
            List of structured product data
        """
        if not self.is_available():
            logger.warning("⚠️ Exa client not available")
            return []
        
        try:
            # Build search query with category-specific template
            category = self._detect_product_category(query)
            search_query = self._build_enhanced_query(query, store_name or "grocery store", zipcode or "", category)
            
            # Get optimized prompt based on context and category
            optimized_prompt = self._get_optimized_prompt(query, context)
            
            # Define structured schema for product data
            product_schema = {
                "type": "object",
                "properties": {
                    "product_name": {
                        "type": "string",
                        "description": "Name of the product"
                    },
                    "brand": {
                        "type": "string",
                        "description": "Brand name of the product"
                    },
                    "price": {
                        "type": "number",
                        "description": "Price in USD"
                    },
                    "currency": {
                        "type": "string",
                        "description": "Currency code (USD)"
                    },
                    "quantity": {
                        "type": "string",
                        "description": "Product quantity or size (e.g., '1 gallon', '64 oz', '12 pack')"
                    },
                    "availability": {
                        "type": "string",
                        "description": "Stock availability status"
                    },
                    "store_name": {
                        "type": "string",
                        "description": "Name of the store selling the product"
                    },
                    "store_address": {
                        "type": "string",
                        "description": "Full store address"
                    },
                    "store_zipcode": {
                        "type": "string",
                        "description": "Store ZIP code"
                    },
                    "store_city": {
                        "type": "string",
                        "description": "Store city"
                    },
                    "store_state": {
                        "type": "string",
                        "description": "Store state"
                    },
                    "category": {
                        "type": "string",
                        "description": "Product category"
                    },
                    "description": {
                        "type": "string",
                        "description": "Product description"
                    },
                    "rating": {
                        "type": "number",
                        "description": "Customer rating (1-5)"
                    },
                    "reviews_count": {
                        "type": "number",
                        "description": "Number of customer reviews"
                    },
                    "confidence_score": {
                        "type": "number",
                        "description": "Confidence in data accuracy (0-1)"
                    }
                },
                "required": ["product_name", "price"]
            }
            
            logger.info(f"🔍 Searching Exa for: {search_query} (Category: {category}, Context: {context or 'auto-detected'})")
            
            # OPTIMIZED: Reduced text extraction for faster processing
            # Search with text content extraction - reduced for speed
            # Note: Exa's search_and_contents doesn't support summary parameter
            # Use get_contents with summary for individual URLs if needed
            # Increase results for Wegmans to get more products
            is_wegmans_search = store_name and store_name.lower() == "wegmans"
            wegmans_multiplier = 3 if is_wegmans_search else 2
            wegmans_max = 50 if is_wegmans_search else 30
            search_options = {
                "query": search_query,
                "num_results": min(num_results * wegmans_multiplier, wegmans_max),
                "type": "neural",  # Neural search for semantic matching
                "text": {"max_characters": 1500}  # Reduced from 3000 to 1500 for faster processing
                # Note: extras/image_links is only available in get_contents, not search_and_contents
            }
            logger.debug(f"Exa search options: {search_options}")

            # Add domain filter if store specified
            if store_name:
                domain = self._get_store_domain(store_name)
                logger.info(f"🔍 Store name: '{store_name}' -> Domain: '{domain}'")
                if domain:
                    # Include both www and non-www versions for better coverage
                    domains_to_include = [domain]
                    if domain.startswith("www."):
                        domains_to_include.append(domain[4:])  # Also include without www
                    elif not domain.startswith("www."):
                        domains_to_include.append(f"www.{domain}")  # Also include with www
                    search_options["include_domains"] = domains_to_include
                    logger.info(f"✅ Using domain filter: {domains_to_include}")
                else:
                    logger.warning(f"⚠️ No domain found for store_name: '{store_name}'")

            # Execute search - OPTIMIZED: Use async executor with timeout
            try:
                logger.info(f"📡 Calling Exa API with query: {search_query}")
                logger.debug(f"📋 Search options: {search_options}")
                # Add timeout to prevent hanging
                response = await asyncio.wait_for(
                    asyncio.get_event_loop().run_in_executor(
                        None,
                        lambda: self._client.search_and_contents(**search_options)
                    ),
                    timeout=10.0  # 10 second timeout per store search
                )
                
                if not response:
                    logger.warning("⚠️ Exa returned None response")
                    return []
                
                logger.info(f"📥 Exa response received: {type(response)}")
                
                # Log raw results count before processing
                raw_results = getattr(response, "results", [])
                logger.info(f"📊 Exa returned {len(raw_results)} raw results for {store_name}")
                if len(raw_results) == 0:
                    logger.warning(f"⚠️ Zero results from Exa for {store_name} with query: {search_query}")
                    logger.warning(f"⚠️ Search options were: {search_options}")
                
                # Process results
                products = await self._process_search_results(response, store_name, zipcode)
            except asyncio.TimeoutError:
                logger.warning(f"⏱️ Exa API call timed out for {store_name}")
                return []
            except Exception as e:
                logger.error(f"❌ Exa API call failed: {e}", exc_info=True)
                return []

            # Limit to requested number
            products = products[:num_results]

            logger.info(f"✅ Found {len(products)} products via Exa")
            return products
            
        except Exception as e:
            logger.error(f"❌ Exa structured search failed: {e}")
            return []
    
    def _build_search_query(self, query: str, store_name: Optional[str], zipcode: Optional[str]) -> str:
        """Build optimized search query for better product discovery"""
        parts = [query]
        
        # Add store context for better targeting
        if store_name:
            parts.append(f"at {store_name}")
        
        # Add location context if provided
        if zipcode:
            parts.append(f"near {zipcode}")
        
        # Add grocery-specific keywords to improve results
        grocery_keywords = ["milk", "bread", "eggs", "cheese", "butter", "meat", "produce", "frozen", "organic", "fresh"]
        if any(keyword in query.lower() for keyword in grocery_keywords):
            parts.append("grocery store product")
        
        # Add shopping context for better results
        if not any(word in query.lower() for word in ["buy", "shop", "store", "grocery"]):
            parts.append("buy online")
        
        return " ".join(parts)
    
    def _is_product_page(self, url: str, title: str) -> bool:
        """Check if URL is an actual product page, not a category/search page"""
        if not url:
            return False

        # Filter out obvious search and category pages
        exclude_patterns = [
            '/search',
            '/category',
            '/browse',
            '/s/',  # Target search pages
            '/c/',  # Target category pages
            '?Nao=',  # Pagination
            'Page ',  # Page indicators in title
        ]

        url_lower = url.lower()
        title_lower = title.lower() if title else ""
        
        for pattern in exclude_patterns:
            if pattern in url_lower or pattern in title_lower:
                return False
        
        # Filter out gift cards and non-food items
        gift_card_patterns = [
            'gift card',
            'giftcard',
            'gift-card',
            '/gift',
            'egift',
            'e-gift',
            'digital gift',
            'prepaid',
            'reloadable',
        ]
        
        for pattern in gift_card_patterns:
            if pattern in url_lower or pattern in title_lower:
                logger.debug(f"Filtering out gift card: {title[:60]}... (URL: {url[:60]}...)")
                return False

        # Wegmans-specific filtering - allow product pages and search pages
        if 'wegmans.com' in url_lower:
            # Wegmans product pages are at /shop/product/{id}-{name}
            # Also allow search pages at /shop/search/ for more results
            if '/shop/product/' in url_lower or '/shop/search' in url_lower:
                # Exclude store location pages, sitemaps, FAQs, etc.
                exclude_wegmans = [
                    '/stores/',
                    '/sitemap',
                    '/service/',
                    '/faq',
                    '/about',
                    '/privacy',
                    '/terms',
                    '/recipes',
                    '/pharmacy',
                ]
                if not any(exclude in url_lower for exclude in exclude_wegmans):
                    return True
            return False
        
        # ALDI-specific filtering - only include actual product pages
        if 'aldi.us' in url_lower:
            # ALDI product pages are at /product/{name}-{id}
            if '/product/' in url_lower and not '/products/' in url_lower:
                # Exclude category pages, search pages, help pages, etc.
                exclude_aldi = [
                    '/products/',  # Category/listing pages
                    '/products/featured/',
                    '/products/recipes/',
                    '/help',
                    '/about',
                    '/privacy',
                    '/terms',
                    '/sitemap',
                    '/stores',
                    '/careers',
                ]
                if not any(exclude in url_lower for exclude in exclude_aldi):
                    return True
            return False
        
        # Check for product page indicators
        product_indicators = [
            '/p/',  # Target product pages
            '/ip/',  # Walmart individual product pages
            '/A-',  # Target product ID
            '/product/',  # Generic product pages
            '/products/',  # Generic products pages
            '/item/',  # Item pages
        ]

        for indicator in product_indicators:
            if indicator in url_lower:
                return True
        
        # If URL contains common store domains and doesn't look like a search page, assume it might be a product
        store_domains = ['target.com', 'walmart.com', 'wholefoodsmarket.com', 'kroger.com', 'aldi.us']
        if any(domain in url_lower for domain in store_domains):
            # If it's not clearly a search/category page, give it a chance
            if not any(exclude in url_lower for exclude in ['/search', '/category', '/browse', '/s/', '/c/']):
                return True

        return False

    async def _process_search_results(
        self,
        response: Any,
        store_name: Optional[str],
        zipcode: Optional[str]
    ) -> List[Dict[str, Any]]:
        """Process Exa search results into structured product data - OPTIMIZED for speed"""
        products = []

        try:
            results = getattr(response, "results", [])
            logger.info(f"🔍 Processing {len(results)} results from Exa")

            # OPTIMIZED: Process results concurrently (up to 10 at a time)
            semaphore = asyncio.Semaphore(10)
            
            async def process_single_result(idx: int, result: Any):
                async with semaphore:
                    return await self._process_single_result(result, store_name, zipcode, idx)
            
            # Process all results concurrently
            tasks = [process_single_result(idx, result) for idx, result in enumerate(results)]
            processed_results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Filter out None and exceptions
            for processed in processed_results:
                if processed and isinstance(processed, dict):
                    products.append(processed)
                elif isinstance(processed, Exception):
                    logger.debug(f"Failed to process result: {processed}")

            logger.info(f"✅ Processed {len(results)} results, extracted {len(products)} products")
        except Exception as e:
            logger.error(f"❌ Failed to process search results: {e}")

        return products
    
    async def _process_single_result(
        self,
        result: Any,
        store_name: Optional[str],
        zipcode: Optional[str],
        idx: int
    ) -> Optional[Dict[str, Any]]:
        """Process a single search result - extracted for concurrent processing"""
        try:
            # Check if this is an actual product page
            url = getattr(result, "url", "")
            title = getattr(result, "title", "")

            if not url:
                logger.debug(f"Skipping result {idx}: No URL")
                return None
            
            logger.debug(f"Result {idx}: {title[:60]}... | URL: {url[:80]}...")

            if not self._is_product_page(url, title):
                logger.debug(f"Skipping non-product page: {title[:60]}... (URL: {url[:60]}...)")
                # For Wegmans, allow search pages since products are in modals
                if 'wegmans.com' in url.lower() and '/shop/search' in url.lower():
                    logger.debug(f"✅ Allowing Wegmans search page (products extracted from search results): {url[:60]}...")
                    # Don't filter out - continue processing
                elif 'wegmans.com' in url.lower():
                    logger.debug(f"Filtering out Wegmans non-product URL: {url[:60]}...")
                    return None
                # For ALDI, be strict - only allow /product/ URLs (not /products/)
                if 'aldi.us' in url.lower():
                    logger.debug(f"Filtering out ALDI non-product URL: {url[:60]}...")
                    return None
                # For now, let's be less strict and include results that might be products
                # Only skip obvious search/category pages
                if any(exclude in url.lower() for exclude in ['/search', '/category', '/browse', '/s/', '/c/']):
                    logger.debug(f"Definitely skipping search/category page: {url[:60]}...")
                    return None

            # Extract product data (skip async image extraction during batch for performance)
            product = await self._extract_product_data(result, store_name, zipcode, extract_images_async=False)
            
            # Filter out gift cards and non-food items based on product name/content
            if product:
                product_name = product.get("name", "").lower()
                product_url_lower = product.get("product_url", "").lower()
                
                # Check for gift card indicators in product name or URL
                gift_card_keywords = [
                    'gift card', 'giftcard', 'gift-card', 'egift', 'e-gift',
                    'digital gift', 'prepaid', 'reloadable', 'gift certificate'
                ]
                
                # Check for category/brand pages (not specific products)
                category_page_indicators = [
                    'products at', 'products in', 'products from',
                    'at target', 'at walmart', 'at kroger',
                    'shop all', 'browse', 'view all',
                    'brand shop', 'brand store'
                ]
                
                # Skip gift cards
                if any(keyword in product_name or keyword in product_url_lower for keyword in gift_card_keywords):
                    logger.debug(f"Filtering out gift card product: {product.get('name', 'Unknown')[:50]}...")
                    return None
                
                # Skip category/brand pages (e.g., "STK Steakhouse products at Target")
                if any(indicator in product_name for indicator in category_page_indicators):
                    logger.debug(f"Filtering out category page: {product.get('name', 'Unknown')[:50]}...")
                    return None
            
            # SMART IMAGE CACHING: Check cache first, then Exa if needed
            if product and not product.get("image_url"):
                # Try fuzzy matching cache first (FAST - DB lookup)
                cached_image = None
                if _image_cache:
                    try:
                        cached_image = await _image_cache.get_cached_image(
                            name=product.get("name", ""),
                            brand=product.get("brand"),
                            size=product.get("size") or product.get("quantity"),
                            store=product.get("store_name")
                        )
                        if cached_image:
                            product["image_url"] = cached_image
                            logger.debug(f"✅ Got image from cache for '{product.get('name', 'Unknown')[:50]}'")
                    except Exception as e:
                        logger.debug(f"Cache lookup failed: {e}")
                
                # If cache miss, try Exa extraction (SLOW - API call)
                # For Wegmans, ALDI, and other stores that need better image extraction, always try Exa
                product_url = product.get("product_url")
                is_wegmans = product_url and "wegmans.com" in product_url.lower()
                is_aldi = product_url and "aldi.us" in product_url.lower()
                
                if not product.get("image_url") and product_url:
                    try:
                        extracted_image = await self.get_product_image_url(product_url)
                        if extracted_image:
                            product["image_url"] = extracted_image
                            # Cache it for future use
                            if _image_cache:
                                try:
                                    await _image_cache.cache_image(
                                        name=product.get("name", ""),
                                        image_url=extracted_image,
                                        brand=product.get("brand"),
                                        size=product.get("size") or product.get("quantity"),
                                        store=product.get("store_name"),
                                        product_url=product_url
                                    )
                                except Exception as e:
                                    logger.debug(f"Failed to cache image: {e}")
                            logger.debug(f"✅ Got image from Exa for '{product.get('name', 'Unknown')[:50]}' ({'Wegmans' if is_wegmans else 'ALDI' if is_aldi else 'other'})")
                    except Exception as e:
                        logger.debug(f"Exa image extraction failed: {e}")
            
            if product:
                logger.debug(f"✅ Added product: {product.get('name', 'Unknown')[:50]}...")
                return product
            else:
                logger.debug(f"⚠️ Failed to extract product data from: {title[:50]}...")
                return None
                
        except Exception as e:
            logger.warning(f"⚠️ Failed to process result {idx}: {e}")
            return None
    
    
    def _clean_exa_summary(self, summary: str) -> Optional[str]:
        """Clean and format Exa AI-generated summary"""
        if not summary:
            return None
        
        import re
        # Exa summaries are usually clean, but remove any artifacts
        summary = re.sub(r'\[skip to [^\]]+\]', '', summary, flags=re.IGNORECASE)
        summary = re.sub(r'\[[^\]]+\]\([^\)]+\)', '', summary)
        summary = re.sub(r'https?://[^\s]+', '', summary)
        summary = re.sub(r'\s+', ' ', summary).strip()
        
        # Limit length but keep informative
        if len(summary) > 500:
            sentences = summary.split('. ')
            result = []
            for sentence in sentences:
                if len('. '.join(result + [sentence])) <= 500:
                    result.append(sentence)
                else:
                    break
            summary = '. '.join(result) + '.' if result else summary[:497] + '...'
        
        return summary if len(summary) > 20 else None
    
    def _extract_product_description(self, text: str, title: str) -> Optional[str]:
        """Extract clean, meaningful product description from text"""
        if not text:
            return None
        
        import re
        
        # Aggressive cleaning - remove all navigation/UI elements
        text = re.sub(r'\[skip to [^\]]+\]', '', text, flags=re.IGNORECASE)
        text = re.sub(r'\[[^\]]+\]\([^\)]+\)', '', text)  # Remove markdown links
        text = re.sub(r'https?://[^\s]+', '', text)  # Remove URLs
        text = re.sub(r'Target Circle[™®]?|Registry|Wish List|Weekly Ad|Find Stores|Categories|Deals|New & featured|Pickup|delivery', '', text, flags=re.IGNORECASE)
        text = re.sub(r'Robot or human\?.*?Thank You!', '', text, flags=re.IGNORECASE | re.DOTALL)
        text = re.sub(r'Sponsored|Add to cart|Add to list|Sign in|Shipping|Return this item|Eligible for|At a glance|About this item|Details|Label info', '', text, flags=re.IGNORECASE)
        text = re.sub(r'Specifications & Returns|Q&A|Additional product information|recommendations|Load all content|Discover more options|Loading content|Buy it again|Frequently bought together|Gue', '', text, flags=re.IGNORECASE)
        text = re.sub(r'registries and s|## |###|Your views|This product is featured|Featured products|ratings & reviews|Disclaimer|Get top|latest trends', '', text, flags=re.IGNORECASE)  # Remove markdown headers and navigation
        text = re.sub(r'and at once|sts also viewed', '', text, flags=re.IGNORECASE)
        text = re.sub(r'\( \( search|! ! !|# #|###', '', text)  # Remove weird formatting
        text = re.sub(r'\$\d+\.\d+/[^\s]+', '', text)  # Remove unit prices like "$9.07/fluid ounce"
        text = re.sub(r'out of 5 stars|reviews?\s*\d+', '', text, flags=re.IGNORECASE)  # Remove rating text
        text = re.sub(r'Gluten Free|Sponsored|Search', '', text, flags=re.IGNORECASE)
        text = re.sub(r'Only at [a-z\s]+', '', text, flags=re.IGNORECASE)  # Remove "Only at target"
        text = re.sub(r'Free & easy returns.*?days', '', text, flags=re.IGNORECASE | re.DOTALL)  # Remove return policy
        text = re.sub(r'by mail or in store|for a full refund', '', text, flags=re.IGNORECASE)
        # Fix formatting issues
        text = re.sub(r'Fat Content(\d+)', r'Fat Content: \1%', text, flags=re.IGNORECASE)  # Fix "Fat Content1" -> "Fat Content: 1%"
        text = re.sub(r'Fat Content:\s*(\d+)%\s*Percent', r'Fat Content: \1%', text, flags=re.IGNORECASE)  # Fix "Fat Content: 1% Percent" -> "Fat Content: 1%"
        text = re.sub(r'Size(\d+\.?\d*)', r'Size: \1', text, flags=re.IGNORECASE)  # Fix "Size0.5" -> "Size: 0.5"
        text = re.sub(r'-{2,}', ' ', text)  # Replace multiple dashes with space
        text = re.sub(r'\s+-\s+-\s+', ' ', text)  # Fix " - - " patterns
        text = re.sub(r'\s+-\s+$', '', text)  # Remove trailing dashes
        text = re.sub(r'Percent\s*-\s*-', 'Percent', text, flags=re.IGNORECASE)  # Fix "Percent - -"
        text = re.sub(r'Gallon\s*-\s*-', 'Gallon', text, flags=re.IGNORECASE)  # Fix "Gallon - -"
        text = re.sub(r'\s+', ' ', text)  # Normalize whitespace
        # Final cleanup - remove any remaining "Only at" patterns
        text = re.sub(r'Only at\s+\w+', '', text, flags=re.IGNORECASE)
        
        # Look for actual product description patterns
        # Pattern 1: "About this item" or "Details" sections
        about_match = re.search(r'(?:about|details|description|overview|product info)[\s:]+(.+?)(?:sponsored|additional|discover|more|$)', text, re.IGNORECASE | re.DOTALL)
        if about_match:
            desc_text = about_match.group(1)
            # Clean it further
            desc_text = re.sub(r'\s+', ' ', desc_text).strip()
            if len(desc_text) > 30:
                # Take first 200 chars
                desc_text = desc_text[:200] if len(desc_text) <= 200 else desc_text[:197] + '...'
                return desc_text
        
        # Pattern 2: Look for sentences with product keywords
        sentences = re.split(r'[.!?]\s+', text)
        meaningful_sentences = []
        
        skip_patterns = [
            r'^skip to|^terms of use|^privacy policy|^activate and hold|^thank you',
            r'^banner|^cookie|^javascript|^enable|^loading|^return|^eligible',
            r'^sponsored|^add to|^sign in|^shipping|^free|^easy',
            r'^\s*$|^[^\w]*$|^[()\[\]{}]+$',  # Empty or only symbols
            r'^\d+\.\d+$|^\d+$'  # Just numbers
        ]
        
        product_keywords = [
            'organic', 'whole', 'fat', 'reduced', 'low fat', 'skim', 'fresh', 'natural',
            'pasteurized', 'homogenized', 'vitamin', 'calcium', 'protein', 'nutrition',
            'ingredients', 'allergen', 'contains', 'gluten', 'dairy', 'cage free',
            'free range', 'grade a', 'large', 'extra large', 'gallon', 'fluid ounce',
            'wheat', 'whole grain', 'sliced', 'enriched', 'fortified'
        ]
        
        for sentence in sentences:
            sentence = sentence.strip()
            if not sentence or len(sentence) < 15:
                continue
            
            # Skip navigation/UI text
            skip = False
            for pattern in skip_patterns:
                if re.search(pattern, sentence, re.IGNORECASE):
                    skip = True
                    break
            
            if skip:
                continue
            
            # Must not contain navigation chars or junk text
            if any(char in sentence for char in ['[', ']', '{', '}', 'http', 'www.', '* * *']):
                continue
            
            # Skip sentences with navigation words
            junk_words = ['specifications', 'returns', 'q&a', 'additional', 'recommendations', 
                         'loading', 'discover', 'buy it again', 'frequently bought', 'featured',
                         'ratings & reviews', 'disclaimer', 'get top', 'latest trends', 
                         'and at once', 'also viewed', 'your views', 'target finds']
            sentence_lower = sentence.lower()
            if any(junk in sentence_lower for junk in junk_words):
                continue
            
            # Check if it contains product keywords or looks like descriptive content
            has_keywords = any(keyword in sentence_lower for keyword in product_keywords)
            is_descriptive = len(sentence) > 40 and not re.search(r'^\d+', sentence) and not re.search(r'^\s*[*#]', sentence)
            
            if has_keywords or is_descriptive:
                # Clean sentence
                sentence = re.sub(r'\s+', ' ', sentence).strip()
                sentence = re.sub(r'\s*[*#]+\s*', ' ', sentence)  # Remove asterisks and hashes
                if len(sentence) > 20:  # Only add if meaningful length
                    meaningful_sentences.append(sentence)
                
                # Limit to 2-3 best sentences
                if len(meaningful_sentences) >= 3:
                    break
        
        if meaningful_sentences:
            description = '. '.join(meaningful_sentences)
            description = re.sub(r'\s+', ' ', description).strip()
            
            # Final cleanup - remove all remaining formatting issues
            description = re.sub(r'\s+-\s+-\s+', ' ', description)  # Remove " - - " patterns
            description = re.sub(r'\s+-\s+$', '', description)  # Remove trailing dashes
            description = re.sub(r'^\s*-\s*', '', description)  # Remove leading dashes
            description = re.sub(r'^[^\w]+|[^\w]+$', '', description)  # Remove leading/trailing non-word chars
            description = re.sub(r'\s+', ' ', description).strip()  # Final whitespace normalization
            
            if len(description) > 20:
                # Limit length
                if len(description) > 300:
                    description = description[:297] + '...'
                return description
        
        # Fallback: Generate description from title if we have product info
        if title and len(title) > 5:
            # Try to create a simple description from title
            title_lower = title.lower()
            desc_parts = []
            
            if 'organic' in title_lower:
                desc_parts.append('Organic product')
            if any(word in title_lower for word in ['milk', 'dairy']):
                desc_parts.append('Fresh dairy product')
            if any(word in title_lower for word in ['egg', 'eggs']):
                desc_parts.append('Fresh eggs')
            if any(word in title_lower for word in ['bread']):
                desc_parts.append('Fresh baked bread')
            
            if desc_parts:
                return '. '.join(desc_parts) + '.'
        
        return None
    
    async def _get_price_from_exa(self, url: Optional[str], store_name: Optional[str] = None) -> Optional[float]:
        """
        Get price from Exa using structured extraction with store-specific optimizations.
        This makes an API call to Exa to get structured price data.
        
        Args:
            url: Product page URL
            store_name: Optional store name for better context
        
        Returns price as float or None if extraction fails.
        """
        if not url or not self.is_available():
            return None
        
        try:
            # Detect store from URL for better extraction hints
            detected_store = None
            if "aldi.us" in url:
                detected_store = "ALDI"
            elif "wegmans.com" in url:
                detected_store = "Wegmans"
            elif "target.com" in url:
                detected_store = "Target"
            elif "walmart.com" in url:
                detected_store = "Walmart"
            elif "wholefoodsmarket.com" in url:
                detected_store = "Whole Foods"
            
            store_name = store_name or detected_store
            
            # Store-specific extraction hints for better accuracy
            store_hints = {
                "ALDI": "ALDI displays prices prominently near the product title, usually in format '$X.XX'. Look for the main product price, not unit prices.",
                "Wegmans": "Wegmans shows prices in the product details section. Look for the current price, not sale prices unless that's the only price.",
                "Target": "Target displays prices clearly in the product info section. Extract the main price shown.",
                "Walmart": "Walmart shows prices prominently. Look for the current price displayed for the product.",
                "Whole Foods": "Whole Foods may show prices with organic/premium indicators. Extract the main product price."
            }
            
            store_hint = store_hints.get(store_name, "Extract the main product price displayed on the page.")
            
            # Define schema focused on price with better validation
            price_schema = {
                "type": "object",
                "properties": {
                    "price": {
                        "type": "number",
                        "description": f"Product price in USD as a number (e.g., 4.65, 12.50, 29.99). {store_hint} Extract ONLY the main product price, not unit prices, sale prices, or 'was' prices. Return the numeric value without currency symbols."
                    },
                    "price_text": {
                        "type": "string",
                        "description": "Original price text as displayed on page (e.g., '$4.65', '$12.50/lb', '29.99') for verification"
                    },
                    "confidence": {
                        "type": "string",
                        "enum": ["high", "medium", "low"],
                        "description": "Confidence level in the extracted price"
                    }
                },
                "required": ["price"]
            }
            
            # Build optimized query with store context
            query = f"""Extract the product price from this {store_name or 'grocery store'} product page.

{store_hint}

Focus on:
1. Main product price (the price you pay for the product)
2. Price displayed near "Add to Cart" or product title
3. Current/active price (not "was" prices or sale prices unless that's the only price)

Ignore:
- Unit prices (per lb, per oz, etc.) unless that's the only price
- "Was" prices or crossed-out prices
- Shipping costs or additional fees
- Prices from other products or related items

Return the exact numeric price value in USD (e.g., 4.65 for $4.65, 12.50 for $12.50)."""
            
            response = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: self._client.get_contents(
                    [url],
                    text=True,
                    summary={
                        "query": query,
                        "schema": price_schema
                    }
                )
            )
            
            if response and response.results:
                result = response.results[0]
                if hasattr(result, "summary") and result.summary:
                    # Parse the summary JSON to get price
                    try:
                        summary_data = json.loads(result.summary)
                        exa_price = summary_data.get("price")
                        confidence = summary_data.get("confidence", "medium")
                        
                        if exa_price is not None:
                            try:
                                price_value = float(exa_price)
                                # Validate price is reasonable
                                if 0.01 <= price_value <= 1000:
                                    # Log with confidence level
                                    confidence_msg = f" (confidence: {confidence})" if confidence else ""
                                    logger.debug(f"✅ Got price from Exa structured extraction{' for ' + store_name if store_name else ''}: ${price_value}{confidence_msg}")
                                    return price_value
                                else:
                                    logger.debug(f"⚠️ Price out of range: ${price_value} (expected $0.01-$1000)")
                            except (ValueError, TypeError) as ve:
                                logger.debug(f"⚠️ Invalid price format: {exa_price} - {ve}")
                                pass
                        else:
                            logger.debug(f"⚠️ No price found in Exa extraction for {store_name or 'unknown store'}")
                    except json.JSONDecodeError as je:
                        logger.debug(f"⚠️ Failed to parse Exa JSON response: {je}")
                        # Try to extract price from text as fallback
                        if hasattr(result, "text") and result.text:
                            price_match = re.search(r'\$(\d+\.\d{2})', result.text)
                            if price_match:
                                try:
                                    fallback_price = float(price_match.group(1))
                                    if 0.01 <= fallback_price <= 1000:
                                        logger.debug(f"✅ Got price from text fallback: ${fallback_price}")
                                        return fallback_price
                                except (ValueError, TypeError):
                                    pass
                    except AttributeError as ae:
                        logger.debug(f"⚠️ Missing attribute in Exa response: {ae}")
            
            return None
        except Exception as e:
            logger.debug(f"Failed to get price from Exa for {url[:80]}... ({store_name or 'unknown'}): {e}")
            return None
    
    async def _get_availability_from_exa(self, url: Optional[str]) -> Optional[str]:
        """
        Get availability status from Exa using structured extraction.
        This makes an API call to Exa to get structured availability data.
        
        Returns availability string or None if extraction fails.
        """
        if not url or not self.is_available():
            return None
        
        try:
            # Define schema focused on availability
            availability_schema = {
                "type": "object",
                "properties": {
                    "availability": {
                        "type": "string",
                        "description": "Stock availability status. Extract exact status from page: 'in stock', 'out of stock', 'sold out', 'available', 'unavailable', 'low stock', 'limited availability', 'check store', 'available for pickup', 'available for delivery'. Be precise - look for stock status indicators, 'add to cart' buttons (usually means in stock), 'out of stock' messages, or inventory warnings."
                    }
                },
                "required": ["availability"]
            }
            
            response = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: self._client.get_contents(
                    [url],
                    text=True,
                    summary={
                        "query": "Extract the product availability/stock status from this product page. Look for indicators like 'in stock', 'out of stock', 'add to cart', 'sold out', 'available for pickup', 'available for delivery', or inventory warnings. Return the exact availability status.",
                        "schema": availability_schema
                    }
                )
            )
            
            if response and response.results:
                result = response.results[0]
                if hasattr(result, "summary") and result.summary:
                    # Parse the summary JSON to get availability
                    try:
                        summary_data = json.loads(result.summary)
                        exa_availability = summary_data.get("availability", "").strip()
                        if exa_availability:
                            # Normalize the availability value
                            exa_avail_lower = exa_availability.lower()
                            if "out" in exa_avail_lower or "sold out" in exa_avail_lower or "unavailable" in exa_avail_lower:
                                return "Out of Stock"
                            elif "low" in exa_avail_lower or "limited" in exa_avail_lower:
                                return "Low Stock"
                            elif "in stock" in exa_avail_lower or "available" in exa_avail_lower:
                                return "In Stock"
                            else:
                                return exa_availability  # Return as-is if it's a valid status
                    except (json.JSONDecodeError, AttributeError):
                        # If summary is not JSON, try to extract from text
                        pass
            
            return None
        except Exception as e:
            logger.debug(f"Failed to get availability from Exa for {url[:80]}...: {e}")
            return None
    
    def _extract_availability(self, text: str, title: str, url: Optional[str] = None) -> str:
        """
        Extract product availability status from page text content.
        
        Returns one of: "In Stock", "Out of Stock", "Low Stock", "Check Store"
        """
        if not text:
            return "Check Store"
        
        text_lower = text.lower()
        title_lower = title.lower() if title else ""
        combined_text = f"{text_lower} {title_lower}"
        
        # Patterns for out of stock
        out_of_stock_patterns = [
            r'out\s+of\s+stock',
            r'currently\s+unavailable',
            r'not\s+available',
            r'unavailable',
            r'sold\s+out',
            r'no\s+longer\s+available',
            r'discontinued',
            r'temporarily\s+unavailable',
            r'backorder',
            r'pre-order',
        ]
        
        # Patterns for in stock
        in_stock_patterns = [
            r'in\s+stock',
            r'available\s+now',
            r'ready\s+to\s+ship',
            r'add\s+to\s+cart',  # Usually means in stock
            r'buy\s+now',
            r'ships\s+from',
            r'available\s+for',
        ]
        
        # Patterns for low stock
        low_stock_patterns = [
            r'low\s+stock',
            r'only\s+\d+\s+left',
            r'few\s+left',
            r'limited\s+availability',
            r'limited\s+stock',
            r'only\s+\d+\s+in\s+stock',
        ]
        
        # Check for out of stock first (highest priority)
        for pattern in out_of_stock_patterns:
            if re.search(pattern, combined_text, re.IGNORECASE):
                return "Out of Stock"
        
        # Check for low stock
        for pattern in low_stock_patterns:
            if re.search(pattern, combined_text, re.IGNORECASE):
                return "Low Stock"
        
        # Check for in stock
        for pattern in in_stock_patterns:
            if re.search(pattern, combined_text, re.IGNORECASE):
                return "In Stock"
        
        # Store-specific availability indicators
        if url:
            url_lower = url.lower()
            # Target-specific patterns
            if "target.com" in url_lower:
                # Target often shows "Check Store" or "Available for pickup/delivery"
                if any(phrase in text_lower for phrase in ["pickup", "delivery", "shipping"]):
                    return "In Stock"
            
            # Walmart-specific patterns
            if "walmart.com" in url_lower:
                if any(phrase in text_lower for phrase in ["add to cart", "free pickup", "free delivery"]):
                    return "In Stock"
            
            # Wegmans-specific patterns
            if "wegmans.com" in url_lower:
                # Wegmans shows products filtered by store location
                # If product appears on page with store context, it's typically available
                # Look for "Add to List" button (indicates product is available)
                if any(phrase in text_lower for phrase in ["add to list", "add to cart", "price is:", "unit price is:"]):
                    # If we have a price and "Add to List", product is likely in stock
                    if "$" in text or "price" in text_lower:
                        return "In Stock"
                # Check for out of stock indicators
                if any(phrase in text_lower for phrase in ["out of stock", "unavailable", "not available", "sold out"]):
                    return "Out of Stock"
            
            # ALDI-specific patterns
            if "aldi.us" in url_lower:
                # ALDI shows products with "Add to Cart" button when available
                # If product appears on page, it's typically available
                if any(phrase in text_lower for phrase in ["add to cart", "add", "price", "$"]):
                    # If we have a price and "Add to Cart", product is likely in stock
                    if "$" in text or "price" in text_lower:
                        return "In Stock"
                # Check for out of stock indicators
                if any(phrase in text_lower for phrase in ["out of stock", "unavailable", "not available", "sold out", "temporarily unavailable"]):
                    return "Out of Stock"
        
        # Default: Check Store (when we can't determine)
        return "Check Store"
    
    async def _extract_product_data(
        self,
        result: Any,
        store_name: Optional[str],
        zipcode: Optional[str],
        extract_images_async: bool = False
    ) -> Optional[Dict[str, Any]]:
        """Extract structured product data from a single result"""
        try:
            import re

            # Get title and URL - OPTIMIZED: Reduced text processing
            title = getattr(result, "title", "Unknown Product")
            url = getattr(result, "url", None)
            text = getattr(result, "text", "")[:1500] if hasattr(result, "text") else ""  # Reduced from 3000 to 1500
            
            # Wegmans needs a store context to show real prices; add zipcode as store param when missing
            if zipcode and url and 'wegmans.com' in url.lower():
                updated_url = self._add_or_replace_query_param(url, "store", zipcode)
                if updated_url != url:
                    logger.debug(f"🔄 Added Wegmans store context ({zipcode}) to product URL for price extraction")
                    url = updated_url
            
            # Costco needs zipcode in search URLs to show location-specific products and availability
            # Costco filters products by warehouse/delivery location based on zipcode
            if zipcode and url and 'costco.com' in url.lower():
                # Add zipcode parameter to Costco search URLs
                # Format: /s?keyword={query}&zipcode={zipcode}
                if '/s?' in url.lower() or '/s?keyword=' in url.lower():
                    updated_url = self._add_or_replace_query_param(url, "zipcode", zipcode)
                    if updated_url != url:
                        logger.debug(f"🔄 Added Costco zipcode ({zipcode}) to search URL for location-based results")
                        url = updated_url
            
            # Wegmans-specific: Extract product name from URL if title is generic
            if url and 'wegmans.com/shop/product/' in url.lower():
                # URL format: /shop/product/{id}-{name}?store={zipcode}
                # Extract name from URL if title is generic, excluding query parameters
                url_match = re.search(r'/shop/product/\d+-([^?]+)', url)
                if url_match:
                    url_product_name = url_match.group(1).replace('-', ' ').title()
                    # If title is generic (like "Wegmans", "Product Information", etc.), use URL name
                    generic_titles = ['wegmans', 'product information', 'faqs', 'faq', 'loading', 'wegmans food markets']
                    if title.lower() in generic_titles or len(title) < 10:
                        title = url_product_name
                        logger.debug(f"✅ Extracted Wegmans product name from URL: {title}")
            
            # ALDI-specific: Extract product name from URL if title is generic
            if url and 'aldi.us/product/' in url.lower():
                # URL format: /product/{name}-{id}
                # Extract name from URL if title is generic
                url_match = re.search(r'/product/(.+?)-000000000000\d+', url)
                if url_match:
                    url_product_name = url_match.group(1).replace('-', ' ').title()
                    # If title is generic (like "ALDI", "Products", etc.), use URL name
                    generic_titles = ['aldi', 'products', 'product', 'quality products', 'aldi us', 'loading']
                    if title.lower() in generic_titles or len(title) < 10:
                        title = url_product_name
                        logger.debug(f"✅ Extracted ALDI product name from URL: {title}")
            
            # Try to use store-specific extractor if we have HTML content
            # This is especially useful for search result pages
            detected_store_id = self._detect_store_from_url(url)
            if detected_store_id and text and len(text) > 500:
                # Check if this looks like a search results page (has multiple products)
                try:
                    extractor = get_extractor(detected_store_id)
                    if extractor and hasattr(extractor, 'extract_products'):
                        # Try to extract products using store-specific extractor
                        extracted_products = extractor.extract_products(text, detected_store_id)
                        if extracted_products and len(extracted_products) > 0:
                            # Use the first product (or best match)
                            store_product = extracted_products[0]
                            logger.debug(f"✅ Extracted product using {detected_store_id} extractor: {store_product.get('name', 'Unknown')[:50]}")
                            
                            # Enhance with additional data from Exa result
                            enhanced_product = {
                                "name": store_product.get('name') or title,
                                "brand": store_product.get('brand'),
                                "price": store_product.get('price'),
                                "price_display": store_product.get('price_display'),
                                "price_per_unit": store_product.get('price_per_unit'),
                                "size": store_product.get('size'),
                                "variants": store_product.get('variants'),
                                "currency": "USD",
                                "quantity": store_product.get('size') or store_product.get('quantity'),
                                "availability": store_product.get('availability', 'Check Store'),
                                "image_url": store_product.get('image_url'),
                                "product_url": store_product.get('product_url') or url,
                                "description": None,  # Will be filled below
                                "category": None,
                                "rating": store_product.get('rating'),
                                "reviews_count": store_product.get('review_count'),
                                "store_name": store_product.get('store_name') or detected_store_id.title(),
                                "store_zipcode": zipcode,
                                "source": "exa_structured_with_extractor"
                            }
                            
                            # Try to get description from Exa summary if available
                            exa_summary = None
                            if hasattr(result, "summary") and result.summary:
                                exa_summary = result.summary
                            
                            if exa_summary:
                                enhanced_product["description"] = self._clean_exa_summary(exa_summary)
                            else:
                                enhanced_product["description"] = self._extract_product_description(text, title)
                            
                            # If we got a good extraction, use it
                            if enhanced_product.get('name') and enhanced_product.get('price'):
                                return enhanced_product
                except Exception as extractor_error:
                    logger.debug(f"Store extractor failed, falling back to standard extraction: {extractor_error}")
                    # Fall through to standard extraction
            
            # Try to get Exa summary for better description (if available)
            exa_summary = None
            if hasattr(result, "summary") and result.summary:
                exa_summary = result.summary
                logger.debug(f"✅ Got Exa summary for {title[:50]}")

            # Extract price from text content using regex
            price = None
            
            # Improved price extraction patterns
            # Pattern 1: Price with dollar sign: $4.99, $12.50, $29.99
            price_with_dollar = re.search(r'\$(\d+\.\d{2})', text)
            if price_with_dollar:
                try:
                    price = float(price_with_dollar.group(1))
                except:
                    pass
            
            # Pattern 2: Price without dollar sign but with context: "4.99", "Price: 12.50"
            if not price:
                # Look for patterns like "Price: 4.99", "Cost: 12.50", "Only 29.99"
                contextual_price = re.search(r'(?:price|cost|only|was|now|save|sale)[\s:]*\$?(\d+\.\d{2})', text, re.IGNORECASE)
                if contextual_price:
                    try:
                        price = float(contextual_price.group(1))
                    except:
                        pass
            
            # Pattern 3: Decimal numbers in reasonable range (fallback)
            if not price:
                all_decimals = re.findall(r'\b(\d+\.\d{2})\b', text)
                for decimal in all_decimals:
                    try:
                        potential_price = float(decimal)
                        if 0.50 <= potential_price <= 500:
                            price = potential_price
                            break
                    except:
                        continue
            
            # Pattern 4: Whole Foods specific patterns (e.g., "4 99" or "12 50" without decimal)
            if not price and url and "wholefoodsmarket.com" in url:
                # Look for patterns like "4 99" (space instead of decimal)
                space_price = re.search(r'(\d+)\s+(\d{2})\b', text)
                if space_price:
                    try:
                        dollars = int(space_price.group(1))
                        cents = int(space_price.group(2))
                        if 0 <= dollars <= 500 and 0 <= cents <= 99:
                            price = float(f"{dollars}.{cents:02d}")
                    except:
                        pass
            
            # Priority: Use Exa structured extraction for Whole Foods and ALDI (always) or if regex failed
            # This is especially important for Whole Foods and ALDI as their price format may vary
            is_whole_foods = url and "wholefoodsmarket.com" in url
            is_aldi = url and "aldi.us" in url
            is_wegmans = url and "wegmans.com" in url
            
            # Detect store name for better extraction
            detected_store_name = None
            if is_whole_foods:
                detected_store_name = "Whole Foods"
            elif is_aldi:
                detected_store_name = "ALDI"
            elif is_wegmans:
                detected_store_name = "Wegmans"
            elif url and "target.com" in url:
                detected_store_name = "Target"
            elif url and "walmart.com" in url:
                detected_store_name = "Walmart"
            
            if (not price or is_whole_foods or is_aldi or is_wegmans) and url:
                try:
                    exa_price = await self._get_price_from_exa(url, store_name=detected_store_name)
                    if exa_price:
                        # For Whole Foods, ALDI, and Wegmans, prefer Exa extraction (more reliable)
                        # For other stores, use Exa only if regex failed
                        if is_whole_foods or is_aldi or is_wegmans or not price:
                            price = exa_price
                            logger.debug(f"✅ Got price from Exa structured extraction{' for ' + detected_store_name if detected_store_name else ''}: ${price}")
                except Exception as e:
                    logger.debug(f"Failed to get price from Exa: {e}")
            
            # For Wegmans: If price extraction failed due to JavaScript limitations, set "check store"
            if is_wegmans and not price:
                price = "check store"
                logger.debug(f"⚠️ Wegmans price extraction failed (likely JavaScript limitation) - setting to 'check store'")

            # Extract brand from title or text
            brand = None
            common_brands = ["Horizon", "Organic Valley", "Oatly", "Silk", "Chobani", "Target", "365", "Kirkland", "Great Value"]
            for brand_name in common_brands:
                if brand_name.lower() in title.lower() or brand_name.lower() in text.lower():
                    brand = brand_name
                    break

            # Extract quantity/size
            quantity = None
            size_patterns = [
                r'(\d+\.?\d*\s*(?:oz|fl oz|gallon|quart|liter|lb|count|ct|pack))',
                r'(\d+\.?\d*\s*(?:ounce|fluid ounce))',
            ]
            for pattern in size_patterns:
                match = re.search(pattern, text, re.IGNORECASE)
                if match:
                    quantity = match.group(1)
                    break

            # Detect store from URL (using helper method) - NEEDED BEFORE CACHE LOOKUP
            detected_store = self._detect_store_from_url(url) or store_name
            if detected_store:
                detected_store = detected_store.title()

            # SMART IMAGE EXTRACTION: Cache -> Exa image_links -> Exa image field
            image_url = None
            
            # Priority 0: Check fuzzy matching cache FIRST (FASTEST - DB lookup)
            if _image_cache and title:
                try:
                    cached_image = await _image_cache.get_cached_image(
                        name=title,
                        brand=brand,
                        size=quantity,
                        store=detected_store
                    )
                    if cached_image:
                        image_url = cached_image
                        logger.debug(f"✅ Got image from cache: {cached_image[:80]}...")
                except Exception as e:
                    logger.debug(f"Cache lookup failed: {e}")
            
            # Priority 1: Check for image_links in extras (Exa-extracted product images)
            # This is like Exa "right-clicking" the image and copying the URL
            if not image_url and hasattr(result, "extras") and result.extras:
                # Try both snake_case and camelCase for compatibility
                image_links = getattr(result.extras, "image_links", None) or getattr(result.extras, "imageLinks", None)
                if image_links and len(image_links) > 0:
                    image_url = image_links[0]
                    logger.debug(f"✅ Got image from Exa image_links: {image_url[:80]}...")
                    # Cache it for future use
                    if _image_cache:
                        try:
                            await _image_cache.cache_image(
                                name=title,
                                image_url=image_url,
                                brand=brand,
                                size=quantity,
                                store=detected_store,
                                product_url=url
                            )
                        except Exception as e:
                            logger.debug(f"Failed to cache image: {e}")
            
            # Priority 2: Check Exa's image field (may be thumbnail or page image)
            if not image_url and hasattr(result, "image") and result.image:
                image_url = result.image
                logger.debug(f"✅ Using Exa image field: {image_url[:80]}...")
                # Cache it for future use
                if _image_cache:
                    try:
                        await _image_cache.cache_image(
                            name=title,
                            image_url=image_url,
                            brand=brand,
                            size=quantity,
                            store=detected_store,
                            product_url=url
                        )
                    except Exception as e:
                        logger.debug(f"Failed to cache image: {e}")
            
            # Fallback image extraction for specific stores (only if still no image)
            # Cache any extracted images for future use
            if not image_url and url:
                # Note: Wegmans images require actual page scraping (HTML/AI extraction)
                # They're not available via simple URL patterns
                # Use /products/aggregate endpoint for Wegmans images
                if "target.com" in url:
                    # Try to find GUEST ID pattern in text (Target images often have GUEST IDs in HTML)
                    guest_match = re.search(r'GUEST_[a-f0-9\-]+', text, re.IGNORECASE)
                    if guest_match:
                        guest_id = guest_match.group(0)
                        image_url = f"https://target.scene7.com/is/image/Target/{guest_id}?wid=1200&hei=1200&qlt=80"
                        # Cache it
                        if _image_cache:
                            try:
                                await _image_cache.cache_image(
                                    name=title,
                                    image_url=image_url,
                                    brand=brand,
                                    size=quantity,
                                    store=detected_store,
                                    product_url=url
                                )
                            except Exception as e:
                                logger.debug(f"Failed to cache Target image: {e}")
                    elif extract_images_async:
                        # Only do async extraction if explicitly requested
                        try:
                            extracted_image = await self.get_product_image_url(url)
                            if extracted_image:
                                image_url = extracted_image
                                # Cache it
                                if _image_cache:
                                    try:
                                        await _image_cache.cache_image(
                                            name=title,
                                            image_url=image_url,
                                            brand=brand,
                                            size=quantity,
                                            store=detected_store,
                                            product_url=url
                                        )
                                    except Exception as e:
                                        logger.debug(f"Failed to cache Target image: {e}")
                        except Exception as e:
                            logger.debug(f"Failed to extract Target image: {e}")
                elif "walmart.com" in url:
                    # Try to find Walmart image pattern in text
                    walmart_img_patterns = [
                        r'https?://i\d+\.walmartimages\.com/[^\s"\'\)\]\}\s]+\.(?:jpg|jpeg|png|webp|gif)(?:\?[^\s"\'\)\]\}]*)?',
                        r'https?://i\d+\.walmartimages\.com/[^\s"\'\)\]\}]+\.(?:jpg|jpeg|png|webp|gif)',
                    ]
                    for pattern in walmart_img_patterns:
                        walmart_img_match = re.search(pattern, text, re.IGNORECASE)
                        if walmart_img_match:
                            raw_url = walmart_img_match.group(0)
                            image_url = raw_url.rstrip('.,;!?)').split(')')[0].split(']')[0].split('}')[0].split('"')[0].split("'")[0]
                            if image_url.startswith('http') and '.' in image_url:
                                logger.debug(f"✅ Extracted Walmart image from text: {image_url[:80]}...")
                                # Cache it
                                if _image_cache:
                                    try:
                                        await _image_cache.cache_image(
                                            name=title,
                                            image_url=image_url,
                                            brand=brand,
                                            size=quantity,
                                            store=detected_store,
                                            product_url=url
                                        )
                                    except Exception as e:
                                        logger.debug(f"Failed to cache Walmart image: {e}")
                                break
                            else:
                                image_url = None
                    # If still no image, try async extraction
                    if not image_url and extract_images_async:
                        try:
                            extracted_image = await self.get_product_image_url(url)
                            if extracted_image:
                                image_url = extracted_image
                                # Cache it
                                if _image_cache:
                                    try:
                                        await _image_cache.cache_image(
                                            name=title,
                                            image_url=image_url,
                                            brand=brand,
                                            size=quantity,
                                            store=detected_store,
                                            product_url=url
                                        )
                                    except Exception as e:
                                        logger.debug(f"Failed to cache Walmart image: {e}")
                        except Exception as e:
                            logger.debug(f"Failed to extract Walmart image: {e}")
                elif "wegmans.com" in url:
                    # For Wegmans, try to extract image from text first (product pages often have image URLs)
                    wegmans_img_patterns = [
                        r'https?://[^\s"\'\)\]\}]*wegmans[^\s"\'\)\]\}]*\.(?:jpg|jpeg|png|webp|gif)(?:\?[^\s"\'\)\]\}]*)?',
                        r'https?://[^\s"\'\)\]\}]*\.wegmans\.com[^\s"\'\)\]\}]*\.(?:jpg|jpeg|png|webp|gif)',
                    ]
                    for pattern in wegmans_img_patterns:
                        wegmans_img_match = re.search(pattern, text, re.IGNORECASE)
                        if wegmans_img_match:
                            raw_url = wegmans_img_match.group(0)
                            image_url = raw_url.rstrip('.,;!?)').split(')')[0].split(']')[0].split('}')[0].split('"')[0].split("'")[0]
                            if image_url.startswith('http') and '.' in image_url:
                                logger.debug(f"✅ Extracted Wegmans image from text: {image_url[:80]}...")
                                # Cache it
                                if _image_cache:
                                    try:
                                        await _image_cache.cache_image(
                                            name=title,
                                            image_url=image_url,
                                            brand=brand,
                                            size=quantity,
                                            store=detected_store,
                                            product_url=url
                                        )
                                    except Exception as e:
                                        logger.debug(f"Failed to cache Wegmans image: {e}")
                                break
                            else:
                                image_url = None
                    # If still no image, try async extraction (Exa get_contents)
                    if not image_url and extract_images_async:
                        try:
                            extracted_image = await self.get_product_image_url(url)
                            if extracted_image:
                                image_url = extracted_image
                                # Cache it
                                if _image_cache:
                                    try:
                                        await _image_cache.cache_image(
                                            name=title,
                                            image_url=image_url,
                                            brand=brand,
                                            size=quantity,
                                            store=detected_store,
                                            product_url=url
                                        )
                                    except Exception as e:
                                        logger.debug(f"Failed to cache Wegmans image: {e}")
                        except Exception as e:
                            logger.debug(f"Failed to extract Wegmans image: {e}")

            # Clean and extract meaningful description
            # Prefer Exa summary (AI-generated, much better quality)
            if exa_summary:
                description = self._clean_exa_summary(exa_summary)
            else:
                # Fallback to text extraction
                description = self._extract_product_description(text, title)
            
            # Extract availability from Exa (preferred) or fallback to text extraction
            availability = None
            
            # Priority 1: Try to get availability from Exa summary if available
            if exa_summary:
                try:
                    # Check if summary contains availability info
                    summary_lower = exa_summary.lower()
                    if any(phrase in summary_lower for phrase in ["in stock", "out of stock", "available", "unavailable", "sold out"]):
                        # Try to extract from summary
                        availability = self._extract_availability(exa_summary, title, url)
                        if availability and availability != "Check Store":
                            logger.debug(f"✅ Got availability from Exa summary: {availability}")
                except Exception as e:
                    logger.debug(f"Failed to extract availability from Exa summary: {e}")
            
            # Priority 2: If not found, try to get from Exa structured extraction (async call)
            if not availability or availability == "Check Store":
                try:
                    exa_availability = await self._get_availability_from_exa(url)
                    if exa_availability:
                        availability = exa_availability
                        logger.debug(f"✅ Got availability from Exa structured extraction: {availability}")
                except Exception as e:
                    logger.debug(f"Failed to get availability from Exa: {e}")
            
            # Priority 3: Fallback to text extraction
            if not availability or availability == "Check Store":
                try:
                    availability = self._extract_availability(text, title, url)
                    # For Wegmans: If product has price and URL, assume in stock (products are store-filtered)
                    if url and "wegmans.com" in url.lower() and availability == "Check Store":
                        if price or "$" in text:
                            # Wegmans shows products filtered by store/zipcode, so if it appears, it's available
                            availability = "In Stock"
                            logger.debug(f"✅ Wegmans product with price detected - assuming In Stock for store-filtered product")
                    
                    # For ALDI: If product has price and URL, assume in stock (products shown are typically available)
                    if url and "aldi.us" in url.lower() and availability == "Check Store":
                        if price or "$" in text:
                            # ALDI shows products with prices when available, so if it appears, it's likely in stock
                            availability = "In Stock"
                            logger.debug(f"✅ ALDI product with price detected - assuming In Stock")
                except Exception as e:
                    logger.debug(f"Failed to extract availability from text: {e}")
                    availability = "Check Store"
            
            # Build product object with enhanced fields
            product = {
                "name": title,
                "brand": brand,
                "price": price,
                "currency": "USD",
                "quantity": quantity,
                "price_per_unit": None,  # Will be extracted if available
                "size": quantity,  # Alias for quantity
                "variants": None,  # Will be extracted if available
                "availability": availability,
                "image_url": image_url,
                "product_url": url,
                "description": description,
                "category": None,
                "rating": None,
                "reviews_count": None,
                "store_name": detected_store,
                "store_zipcode": zipcode,
                "source": "exa_structured"
            }
            
            # Try to extract price per unit and variants from text if available
            if text:
                # Extract price per unit (e.g., "$0.02/fl oz", "$/lb")
                price_per_unit_match = re.search(r'\$(\d+\.?\d*)\s*/\s*([^\s]+)', text)
                if price_per_unit_match:
                    unit_price = price_per_unit_match.group(1)
                    unit = price_per_unit_match.group(2)
                    product["price_per_unit"] = f"${unit_price}/{unit}"
                
                # Extract variants (e.g., "3 more sizes | 6 more flavors")
                variants_match = re.search(r'(\d+\s+more\s+sizes?[^|]*\|?\s*\d*\s*more\s+flavors?)', text, re.IGNORECASE)
                if variants_match:
                    product["variants"] = variants_match.group(1).strip()

            return product

        except Exception as e:
            logger.error(f"❌ Failed to extract product data: {e}")
            return None
    
    def _detect_store_from_url(self, url: Optional[str]) -> Optional[str]:
        """Detect store ID from URL"""
        if not url:
            return None
        
        url_lower = url.lower()
        store_mappings = {
            'target.com': 'target',
            'walmart.com': 'walmart',
            'kroger.com': 'kroger',
            'wholefoodsmarket.com': 'whole_foods',
            'safeway.com': 'safeway',
            'albertsons.com': 'albertsons',
            'aldi.us': 'aldi',
            'costco.com': 'costco',
            'samsclub.com': 'sams_club',
            'traderjoes.com': 'trader_joes',
            'publix.com': 'publix',
            'heb.com': 'heb',
            'wegmans.com': 'wegmans',
        }
        
        for domain, store_id in store_mappings.items():
            if domain in url_lower:
                return store_id
        
        return None
    
    async def get_product_image_url(self, product_url: str) -> Optional[str]:
        """
        Extract the actual product image URL from a product page using Exa.
        This is like "right-clicking the image and copying the image URL".
        
        Args:
            product_url: URL of the product page
            
        Returns:
            Direct image URL if found, None otherwise
        """
        if not self.is_available() or not product_url:
            return None
        
        try:
            # Use get_contents to extract image URLs from the product page
            # This is like "right-clicking the image and copying the image URL"
            response = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: self._client.get_contents(
                    [product_url],
                    extras={
                        "image_links": 1  # Get the main product image URL
                    }
                )
            )
            
            if response and response.results:
                result = response.results[0]
                
                # Check for image_links in extras (Exa-extracted product images)
                if hasattr(result, "extras") and result.extras:
                    # Try both snake_case and camelCase for compatibility
                    image_links = getattr(result.extras, "image_links", None) or getattr(result.extras, "imageLinks", None)
                    if image_links and len(image_links) > 0:
                        image_url = image_links[0]
                        logger.info(f"✅ Extracted image URL from {product_url}: {image_url[:80]}...")
                        return image_url
                
                # Fallback: check if Exa returned an image field
                if hasattr(result, "image") and result.image:
                    logger.info(f"✅ Using Exa image field: {result.image[:80]}...")
                    return result.image
            
            return None
            
        except Exception as e:
            logger.debug(f"Failed to extract image URL from {product_url}: {e}")
            return None
    
    async def get_product_images_batch(
        self,
        product_urls: List[str],
        max_concurrent: int = 5
    ) -> Dict[str, Optional[str]]:
        """
        Extract product image URLs from multiple product pages concurrently using Exa.
        More efficient than calling get_product_image_url() multiple times.
        
        Args:
            product_urls: List of product page URLs
            max_concurrent: Maximum concurrent Exa API calls (default: 5 to respect rate limits)
            
        Returns:
            Dictionary mapping product_url -> image_url (or None if not found)
        """
        if not self.is_available() or not product_urls:
            return {url: None for url in product_urls}
        
        results = {}
        semaphore = asyncio.Semaphore(max_concurrent)
        
        async def extract_image(url: str):
            async with semaphore:
                try:
                    image_url = await self.get_product_image_url(url)
                    # Validate image URL if found
                    if image_url:
                        is_valid = await self._validate_image_url(image_url)
                        if is_valid:
                            results[url] = image_url
                        else:
                            logger.debug(f"⚠️ Exa image URL failed validation: {image_url[:80]}...")
                            results[url] = None
                    else:
                        results[url] = None
                except Exception as e:
                    logger.debug(f"Failed to extract image for {url}: {e}")
                    results[url] = None
        
        await asyncio.gather(*[extract_image(url) for url in product_urls])
        return results
    
    async def _validate_image_url(self, image_url: str) -> bool:
        """
        Validate that an image URL actually exists and returns a valid image.
        Uses HTTP HEAD request for efficiency.
        """
        if not image_url or not image_url.startswith('http'):
            return False
        
        try:
            import aiohttp
            async with aiohttp.ClientSession() as session:
                async with session.head(image_url, allow_redirects=True, timeout=aiohttp.ClientTimeout(total=5)) as response:
                    if response.status == 200:
                        content_type = response.headers.get('Content-Type', '').lower()
                        # Check if it's an image content type
                        if content_type.startswith('image/'):
                            return True
                        # Some CDNs don't set content-type correctly, check URL extension
                        if any(ext in image_url.lower() for ext in ['.jpg', '.jpeg', '.png', '.webp', '.gif']):
                            return True
            
            return False
            
        except Exception as e:
            logger.debug(f"Image validation failed for {image_url[:80]}...: {e}")
            return False
    
    async def get_product_details(self, url: str) -> Optional[Dict[str, Any]]:
        """
        Get detailed product information from a specific URL
        
        Args:
            url: Product page URL
            
        Returns:
            Structured product details
        """
        if not self.is_available():
            return None
        
        try:
            # Define detailed schema
            detail_schema = {
                "type": "object",
                "properties": {
                    "product_name": {"type": "string"},
                    "brand": {"type": "string"},
                    "price": {"type": "number"},
                    "quantity": {"type": "string"},
                    "description": {"type": "string"},
                    "ingredients": {"type": "array", "items": {"type": "string"}},
                    "nutrition_facts": {"type": "object"},
                    "allergens": {"type": "array", "items": {"type": "string"}},
                    "rating": {"type": "number"},
                    "reviews_count": {"type": "number"},
                    "availability": {"type": "string"}
                }
            }
            
            response = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: self._client.get_contents(
                    [url],
                    text=True,
                    extras={
                        "image_links": 1  # Also extract image URL
                    },
                    summary={
                        "query": "Extract comprehensive grocery product details from the product page. Focus on: complete product name and brand, exact price, detailed quantity/size, full description, ingredients list, nutritional facts, allergens, customer ratings and review counts, availability status. Ensure all data is current and accurate from the product page.",
                        "schema": detail_schema
                    }
                )
            )
            
            if response and response.results:
                result = response.results[0]
                # Allow async image extraction for individual product details
                return await self._extract_product_data(result, None, None, extract_images_async=True)
            
            return None
            
        except Exception as e:
            logger.error(f"❌ Failed to get product details: {e}")
            return None
    
    def _get_city_state_from_zipcode(self, zipcode: str) -> tuple:
        """
        Get city and state from zipcode using Google Geocoding API with static fallback.
        
        Uses the GeocodingService which:
        1. First checks an in-memory cache
        2. Tries Google Geocoding API if API key is available
        3. Falls back to static zip code mapping
        4. Falls back to state-from-prefix mapping
        
        Args:
            zipcode: 5-digit US zip code
            
        Returns:
            Tuple of (city, state) or (None, None) if not found
        """
        try:
            geocoding_service = get_geocoding_service()
            # Use synchronous version to avoid blocking (static lookup only)
            # For async API calls, use async method in search functions
            return geocoding_service.get_city_state_sync(zipcode)
        except Exception as e:
            logger.warning(f"Failed to get city/state for {zipcode}: {e}")
            return None, None
    
    async def _get_city_state_from_zipcode_async(self, zipcode: str) -> tuple:
        """
        Async version of _get_city_state_from_zipcode that can use Google Geocoding API.
        
        Args:
            zipcode: 5-digit US zip code
            
        Returns:
            Tuple of (city, state) or (None, None) if not found
        """
        try:
            geocoding_service = get_geocoding_service()
            return await geocoding_service.get_city_state_from_zipcode(zipcode)
        except Exception as e:
            logger.warning(f"Failed to get city/state for {zipcode}: {e}")
            return None, None

    async def search_stores_in_zipcode(self, store_chain: str, zipcode: str) -> List[Dict[str, Any]]:
        """
        Search for specific store locations in a zipcode

        Args:
            store_chain: Store chain name (e.g., "Target", "Walmart")
            zipcode: ZIP code to search

        Returns:
            List of store locations with addresses
        """
        if not self.is_available():
            return []

        try:
            # Get default city/state from zipcode
            default_city, default_state = self._get_city_state_from_zipcode(zipcode)
            # Build store location search query - explicitly request full address information
            # Make it very clear we need complete address details
            if default_city and default_state:
                search_query = f"{store_chain} store locations in {default_city} {default_state} zipcode {zipcode} with complete address details: street number, street name, city, state, zipcode. Find store location pages that show the full physical address near {zipcode}"
            else:
                search_query = f"{store_chain} store locations in zipcode {zipcode} area with complete address details: street number, street name, city, state, zipcode. Find store location pages that show the full physical address near zipcode {zipcode}"
            domain = self._get_store_domain(store_chain)
            
            # Define store location schema
            store_schema = {
                "type": "object",
                "properties": {
                    "store_name": {"type": "string"},
                    "address": {"type": "string", "description": "Complete street address with street number and name (e.g., '95 E Houston St')"},
                    "city": {"type": "string"},
                    "state": {"type": "string"},
                    "zipcode": {"type": "string"},
                    "phone": {"type": "string"},
                    "hours": {"type": "object"},
                    "services": {"type": "array", "items": {"type": "string"}}
                }
            }
            
            search_options = {
                "query": search_query,
                "num_results": 10,
                "type": "keyword",
                "text": {"max_characters": 5000}  # Get more text to find address information
            }

            if domain:
                search_options["include_domains"] = [domain]
            
            response = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: self._client.search_and_contents(**search_options)
            )
            
            stores = []
            for result in getattr(response, "results", []):
                # Extract address info from text content
                import re
                # Get more text to find address information (increased from 2000 to 5000)
                text = getattr(result, "text", "")[:5000] if hasattr(result, "text") else ""
                title = getattr(result, "title", "")
                url = getattr(result, "url", "")
                
                # Log for debugging
                logger.debug(f"Processing store location result: {title[:80]}... | URL: {url[:80]}...")

                # Initialize address variables
                address = None
                city = None
                state = None
                store_zip = zipcode
                retailer_store_id = None
                
                # Try to get structured address data using get_contents if URL is available
                # This gives us better structured data extraction with explicit prompts
                if url:
                    try:
                        detail_response = await asyncio.get_event_loop().run_in_executor(
                            None,
                            lambda: self._client.get_contents(
                                [url],
                                text={"max_characters": 5000},
                                summary={
                                    "query": f"Extract the complete store address for this {store_chain} store location. Find the full street address including street number, street name, city, state, and zipcode. Format should be like '95 E Houston St, New York, NY 10002'. Also extract the retailer store ID if available.",
                                    "schema": {
                                        "type": "object",
                                        "properties": {
                                            "address": {"type": "string", "description": "Complete street address with number and name (e.g., '95 E Houston St')"},
                                            "city": {"type": "string"},
                                            "state": {"type": "string"},
                                            "zipcode": {"type": "string"},
                                            "retailer_store_id": {"type": "string", "description": "Store ID number if available"}
                                        }
                                    }
                                }
                            )
                        )
                        
                        if detail_response and detail_response.results:
                            detail_result = detail_response.results[0]
                            # Get enhanced text from detailed response
                            detail_text = getattr(detail_result, "text", "")[:5000] if hasattr(detail_result, "text") else ""
                            if detail_text:
                                text = detail_text  # Use detailed text for extraction
                            
                            # Try to parse structured data from summary if available
                            if hasattr(detail_result, "summary") and detail_result.summary:
                                import json
                                try:
                                    # Summary might be JSON or structured text
                                    summary_text = detail_result.summary
                                    logger.debug(f"Got summary from Exa: {summary_text[:200]}...")
                                    
                                    # Try to extract JSON from summary - handle nested objects
                                    # Look for JSON object with multiple lines
                                    json_match = re.search(r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}', summary_text, re.DOTALL)
                                    if json_match:
                                        try:
                                            parsed_data = json.loads(json_match.group(0))
                                            logger.debug(f"Parsed JSON data: {parsed_data}")
                                            if parsed_data.get("address"):
                                                address = parsed_data["address"]
                                                logger.debug(f"✅ Extracted address from summary: {address}")
                                            if parsed_data.get("city"):
                                                city = parsed_data["city"]
                                            if parsed_data.get("state"):
                                                state = parsed_data["state"]
                                            if parsed_data.get("zipcode"):
                                                store_zip = parsed_data["zipcode"]
                                            if parsed_data.get("retailer_store_id"):
                                                retailer_store_id = parsed_data["retailer_store_id"]
                                                logger.debug(f"✅ Extracted retailer_store_id from summary: {retailer_store_id}")
                                        except json.JSONDecodeError:
                                            # Try to extract values using regex if JSON parsing fails
                                            address_match = re.search(r'"address"\s*:\s*"([^"]+)"', summary_text)
                                            if address_match:
                                                address = address_match.group(1)
                                            city_match = re.search(r'"city"\s*:\s*"([^"]+)"', summary_text)
                                            if city_match:
                                                city = city_match.group(1)
                                            state_match = re.search(r'"state"\s*:\s*"([^"]+)"', summary_text)
                                            if state_match:
                                                state = state_match.group(1)
                                            zipcode_match = re.search(r'"zipcode"\s*:\s*"([^"]+)"', summary_text)
                                            if zipcode_match:
                                                store_zip = zipcode_match.group(1)
                                            store_id_match = re.search(r'"retailer_store_id"\s*:\s*"([^"]+)"', summary_text)
                                            if store_id_match:
                                                retailer_store_id = store_id_match.group(1)
                                except Exception as parse_error:
                                    logger.debug(f"Could not parse summary: {parse_error}")
                                    # Continue with text extraction
                    except Exception as e:
                        logger.debug(f"Failed to get detailed address for {url}: {e}")

                # Extract full address from text (using enhanced text from get_contents if available)
                # Look for address patterns like "123 Main St, City, ST 12345"
                # Improved pattern to handle various address formats
                address_patterns = [
                    # Full address with directional: "95 E Houston St, New York, NY 10002"
                    r'(\d+\s+[NSEWnsew]\.?\s+[A-Za-z\s]+(?:Street|St|Avenue|Ave|Road|Rd|Boulevard|Blvd|Drive|Dr|Lane|Ln|Way|Court|Ct|Place|Pl|Parkway|Pkwy)[.,]?)\s*[,\s]+\s*([A-Za-z][A-Za-z\s]+?)\s*,\s*([A-Z]{2})\s+(\d{5})',
                    # Full address: "123 Main St, City, ST 12345" or "95 E Houston St, New York, NY 10002"
                    r'(\d+\s+[A-Za-z\s\.]+(?:Street|St|Avenue|Ave|Road|Rd|Boulevard|Blvd|Drive|Dr|Lane|Ln|Way|Court|Ct|Place|Pl|Parkway|Pkwy)[.,]?)\s*[,\s]+\s*([A-Za-z][A-Za-z\s]+?)\s*,\s*([A-Z]{2})\s+(\d{5})',
                    # Address with abbreviations: "95 E Houston St, New York, NY 10002"
                    r'(\d+\s+[A-Za-z\s\.]+(?:St|Ave|Rd|Blvd|Dr|Ln)[.,]?)\s*[,\s]+\s*([A-Za-z][A-Za-z\s]+?)\s*,\s*([A-Z]{2})\s+(\d{5})',
                    # Address with directional only: "95 E Houston St"
                    r'(\d+\s+[NSEWnsew]\.?\s+[A-Za-z\s]+(?:St|Street|Ave|Avenue|Rd|Road|Blvd|Boulevard|Dr|Drive|Ln|Lane)[.,]?)',
                    # Address without directional: "95 Houston St"
                    r'(\d+\s+[A-Za-z\s]+(?:St|Street|Ave|Avenue|Rd|Road|Blvd|Boulevard|Dr|Drive|Ln|Lane)[.,]?)',
                    # Without full address: "City, ST 12345"
                    r'([A-Za-z][A-Za-z\s]+?)\s*,\s*([A-Z]{2})\s+(\d{5})',
                ]
                
                for pattern in address_patterns:
                    match = re.search(pattern, text)
                    if match:
                        if len(match.groups()) == 4:  # Full address pattern
                            potential_address = match.group(1).strip()
                            potential_city = match.group(2).strip()
                            potential_state = match.group(3).strip()
                            potential_zip = match.group(4)
                            
                            # Only use if it looks like a valid address
                            if not address and re.match(r'^\d+\s+[A-Za-z]', potential_address):
                                address = potential_address.rstrip(',. ')  # Clean trailing punctuation
                            if not city:
                                city = potential_city
                            if not state:
                                state = potential_state
                            if not store_zip or store_zip == zipcode:
                                store_zip = potential_zip
                        elif len(match.groups()) == 3:  # City, state pattern
                            if not city:
                                city = match.group(1).strip()
                            if not state:
                                state = match.group(2).strip()
                            if not store_zip or store_zip == zipcode:
                                store_zip = match.group(3)
                        elif len(match.groups()) == 1:  # Just address
                            potential_address = match.group(1).strip()
                            if not address and re.match(r'^\d+\s+[A-Za-z]', potential_address):
                                address = potential_address.rstrip(',. ')  # Clean trailing punctuation
                        break

                # Extract from title if available (e.g., "Target - Chicago" or "Whole Foods Market Bowery")
                if not city and " - " in title:
                    parts = title.split(" - ")
                    if len(parts) > 1:
                        location_part = parts[1].strip()
                        # Clean up location - remove duplicates like "New YorkNew York"
                        location_part = re.sub(r'([A-Z][a-z]+)\1', r'\1', location_part)
                        city = location_part
                
                # Also check for store name patterns like "Whole Foods Market Bowery" or "Target - Lower East Side"
                if "Whole Foods" in title or "whole foods" in title.lower():
                    # Try to extract location from title
                    title_lower = title.lower()
                    if "bowery" in title_lower:
                        city = "New York"
                        # Try to extract Bowery address (95 E Houston St)
                        bowery_address = re.search(r'(\d+\s+[Ee]\.?\s+[Hh]ouston\s+[Ss]t)', text, re.IGNORECASE)
                        if bowery_address:
                            address = bowery_address.group(1).strip()
                    elif "east houston" in title_lower or "e houston" in title_lower:
                        city = "New York"
                        # Extract street name for address - try multiple patterns
                        street_patterns = [
                            r'(\d+\s+[Ee]\.?\s+[Hh]ouston\s+[Ss]t)',  # "95 E Houston St"
                            r'(\d+\s+[Ee]ast\s+[Hh]ouston\s+[Ss]t)',  # "95 East Houston St"
                            r'(\d+\s+[Ee]\.?\s+[Hh]ouston)',  # "95 E Houston"
                        ]
                        for pattern in street_patterns:
                            street_match = re.search(pattern, text, re.IGNORECASE)
                            if street_match:
                                address = street_match.group(1).strip()
                                break

                # Clean up city name - remove any street name parts that got mixed in
                if city:
                    # Remove common street suffixes if they appear at the start
                    city = re.sub(r'^(East|West|North|South|Upper|Lower)\s+([A-Za-z]+)\s+(St|Street|Ave|Avenue)', '', city, flags=re.IGNORECASE)
                    # Remove duplicates like "New YorkNew York" -> "New York"
                    city = re.sub(r'([A-Z][a-z]+)\1', r'\1', city)
                    # Remove trailing street names
                    city = re.sub(r'\s+(St|Street|Ave|Avenue|Rd|Road)\s*$', '', city, flags=re.IGNORECASE)
                    city = city.strip()

                # Use default city/state if not found
                if not city or len(city) < 2:
                    city = default_city
                if not state:
                    state = default_state

                # Try to extract retailer_store_id from URL or text if not already found
                if not retailer_store_id and url:
                    # Whole Foods: look for store ID in URL or text
                    if "wholefoodsmarket.com" in url:
                        # Whole Foods URLs might have store IDs
                        store_id_match = re.search(r'store[_-]?id[=:]?(\d+)', text, re.IGNORECASE)
                        if store_id_match:
                            retailer_store_id = store_id_match.group(1)
                        # Or try to extract from URL
                        url_match = re.search(r'/stores/(\d+)', url, re.IGNORECASE)
                        if url_match:
                            retailer_store_id = url_match.group(1)
                    
                    # Target: extract store number
                    elif "target.com" in url:
                        store_num_match = re.search(r'store[_-]?(\d+)', text, re.IGNORECASE)
                        if store_num_match:
                            retailer_store_id = store_num_match.group(1)
                    
                    # Walmart: extract store number
                    elif "walmart.com" in url:
                        store_num_match = re.search(r'store[_-]?(\d+)', text, re.IGNORECASE)
                        if store_num_match:
                            retailer_store_id = store_num_match.group(1)
                
                # Build store name - try to get specific location name
                location_name = store_chain
                
                # Extract location identifier from title (e.g., "Bowery", "Lower East Side", etc.)
                location_identifier = None
                
                # Check for Whole Foods specific patterns
                if "whole foods" in store_chain.lower() or "wholefoods" in store_chain.lower():
                    # Look for location identifiers in title
                    if "bowery" in title.lower():
                        location_identifier = "Bowery"
                    elif "east houston" in title.lower():
                        # Extract street address for name
                        street_match = re.search(r'(\d+\s+[Ee]ast\s+[Hh]ouston)', text, re.IGNORECASE)
                        if street_match:
                            location_identifier = street_match.group(1).strip()
                        else:
                            location_identifier = "East Houston"
                    elif " - " in title:
                        parts = title.split(" - ")
                        if len(parts) > 1:
                            location_identifier = parts[1].strip()
                            # Clean up location identifier
                            location_identifier = re.sub(r'New York.*', '', location_identifier, flags=re.IGNORECASE)
                            location_identifier = location_identifier.strip()
                
                # For other stores, extract from title
                elif " - " in title:
                    parts = title.split(" - ")
                    if len(parts) > 1:
                        location_identifier = parts[1].strip()
                        # Remove city name if it's duplicated
                        location_identifier = re.sub(r'\s*New York.*$', '', location_identifier, flags=re.IGNORECASE)
                        location_identifier = location_identifier.strip()
                
                # Build final store name
                if location_identifier:
                    location_name = f"{store_chain} {location_identifier}"
                elif city and city != default_city and city != "New York":
                    location_name = f"{store_chain} {city}"
                elif city == "New York" and address:
                    # Use address for location if we have it
                    location_name = f"{store_chain} {address}"
                
                stores.append({
                    "store_id": store_chain.lower().replace(" ", "_"),
                    "retailer_store_id": retailer_store_id,
                    "store_name": location_name,
                    "address": address.rstrip(',. ') if address else None,  # Clean trailing punctuation
                    "city": city,
                    "state": state,
                    "zipcode": store_zip,
                    "phone": None,
                    "hours": None,
                    "services": ["in-store"],
                    "status": "active",
                    "source": "exa_structured"
                })
            
            logger.info(f"✅ Found {len(stores)} {store_chain} locations near {zipcode}")
            return stores
            
        except Exception as e:
            logger.error(f"❌ Store location search failed: {e}")
            return []
