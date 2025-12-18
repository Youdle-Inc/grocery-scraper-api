#!/usr/bin/env python3
"""
Grocery Scraper API
A professional FastAPI service for scraping grocery store product data
"""

from fastapi import FastAPI, HTTPException, Query, Path
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse
from typing import List, Optional, Dict, Any
import asyncio
import os
import json
from datetime import datetime
import logging
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Debug: Check if environment variables are loaded
logger = logging.getLogger(__name__)
exa_key = os.getenv("EXA_API_KEY")
if exa_key:
    logger.info(f"✅ EXA_API_KEY loaded: {exa_key[:10]}...")
else:
    logger.warning("⚠️ EXA_API_KEY not found in environment")

# Import our scraper modules
from scraper.models import StoreInfo
from scraper.location_service import LocationService
from scraper.cache import Cache, stores_key, products_key
from scraper.exa_structured_client import ExaStructuredClient, set_image_cache
from scraper.image_cache import ProductImageCache
from scraper.partner_api_client import PartnerAPIClient
from scraper.models import (
    HealthResponse,
    StoresResponse,
    StoreDetailsResponse,
    ProductsSearchResponse,
    AggregateResponse,
    AggregateResponseEnhanced,
    ProductResultEnhanced,
    OfferEnhanced,
    StoreInfoDetailed,
    ProductImage,
    NutritionInfo,
)
from scraper.image_scraper import ImageScraper
from scraper.ai_scraper import AIScraper
from scraper.html_image_extractor import HTMLImageExtractor
from scraper.web_search_service import WebSearchService
from scraper.geocoding_service import get_geocoding_service

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# Helper functions for address parsing
def extract_city_from_address(address: str) -> Optional[str]:
    """Extract city from address string"""
    if not address:
        return None
    
    # Look for city pattern: "City, State ZIP"
    import re
    city_pattern = r'([^,]+),\s*([A-Z]{2})\s+\d{5}'
    match = re.search(city_pattern, address)
    if match:
        return match.group(1).strip()
    
    return None

def extract_state_from_address(address: str) -> Optional[str]:
    """Extract state from address string"""
    if not address:
        return None
    
    # Look for state pattern: "City, State ZIP"
    import re
    state_pattern = r'([^,]+),\s*([A-Z]{2})\s+\d{5}'
    match = re.search(state_pattern, address)
    if match:
        return match.group(2).strip()
    
    return None

# Initialize services with error handling for Vercel compatibility
try:
    cache = Cache()
    exa_client = ExaStructuredClient()
    partner_api_client = PartnerAPIClient()  # Official partner APIs (Target, Kroger, Walmart)
    
    # Initialize image cache with fuzzy matching
    image_cache = ProductImageCache(cache)
    set_image_cache(image_cache)  # Make it available to ExaStructuredClient
    location_service = LocationService()
    ai_scraper = AIScraper()  # AI-powered scraper for direct price extraction
    web_search_service = WebSearchService(exa_client=exa_client)  # Web search for price verification
    
    # Debug: Check client status
    logger.info(f"🔍 ExaStructuredClient initialized: {exa_client.is_available()}")
    logger.info(f"🔑 API key loaded: {bool(exa_client.api_key)}")
except Exception as e:
    logger.error(f"❌ Failed to initialize services: {e}", exc_info=True)
    # Initialize with None values to prevent crashes
    cache = None
    exa_client = None
    partner_api_client = None
    image_cache = None
    location_service = None
    ai_scraper = None
    web_search_service = None

# Create FastAPI app
# Note: Removed lifespan for Vercel compatibility - serverless functions don't support startup/shutdown events
app = FastAPI(
    title="Grocery Scraper API",
    description="""
    ## 🛒 AI-Powered Grocery Product Discovery API

    Search for grocery products across major retailers with real product URLs and images.

    ### ✨ Features
    - **Real Product URLs**: Direct links to Target, Walmart, and other major stores
    - **High-Quality Images**: 800x800 product images from store CDNs
    - **Smart Search**: AI-powered semantic search with Exa API
    - **Multi-Store Comparison**: Compare products across different retailers
    - **Location-Based**: Search by ZIP code for local availability

    ### 🏬 Supported Stores
    Target • Walmart • Whole Foods • Kroger • Safeway • ALDI • Costco • Trader Joe's

    ### 🚀 Quick Start
    1. Try the `/health` endpoint to verify the API is running
    2. Use `/stores/{zipcode}` to find stores in your area
    3. Search products with `/products/search?query=milk&store_name=Target&zipcode=60601`
    4. Compare prices with `/products/aggregate?query=eggs&zipcode=60601`

    ### 📊 Response Format
    All responses include `product_url` and `image_url` for easy web app integration.
    """,
    version="2.0.0",
    docs_url="/swagger",  # Swagger UI at /swagger for interactive testing
    redoc_url=None,       # We'll mount ReDoc at root manually
    contact={
        "name": "Grocery Scraper API",
        "url": "https://github.com/Youdle-Inc/grocery-scraper-api",
    },
    license_info={
        "name": "MIT",
        "url": "https://opensource.org/licenses/MIT",
    },
    servers=[
        {"url": "https://grocery-scraper-api.vercel.app", "description": "Production server"},
        {"url": "http://localhost:8001", "description": "Local development server"},
        {"url": "http://localhost:8000", "description": "Alternative local server"},
    ]
)

# Custom JSON response class for pretty formatting
class PrettyJSONResponse(JSONResponse):
    def render(self, content: Any) -> bytes:
        return json.dumps(
            content,
            ensure_ascii=False,
            allow_nan=False,
            indent=2,
            separators=(",", ": "),
        ).encode("utf-8")

# CORS middleware driven by env
from os import getenv
allowed_origins = getenv("CORS_ALLOW_ORIGINS", "*")
allow_origins_list = [o.strip() for o in allowed_origins.split(",") if o.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=allow_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files
# Static files removed for Vercel compatibility

from fastapi.openapi.docs import get_redoc_html

@app.get("/", response_class=HTMLResponse, tags=["meta"], include_in_schema=False)
async def root():
    """Root endpoint - serves ReDoc documentation"""
    return get_redoc_html(
        openapi_url=app.openapi_url,
        title=app.title + " - Documentation",
        redoc_js_url="https://cdn.jsdelivr.net/npm/redoc@next/bundles/redoc.standalone.js",
    )

@app.get("/api", tags=["meta"])
async def api_info():
    """API information endpoint (JSON)"""
    return {
        "name": "Grocery Scraper API",
        "version": "2.0.0",
        "description": "AI-powered grocery product discovery with Exa - structured data with real URLs and images",
        "endpoints": {
            "health": "/health",
            "stores": "/stores/{zipcode}",
            "products": "/products/search",
            "aggregate": "/products/aggregate"
        },
        "features": [
            "Exa-powered structured product search",
            "Real product URLs and high-quality images",
            "Store location discovery",
            "Smart product matching across multiple stores",
            "Structured data extraction (price, quantity, address, etc.)"
        ],
        "data_fields": [
            "product_name",
            "price",
            "currency",
            "quantity",
            "image_url",
            "store_name",
            "store_address",
            "store_zipcode",
            "availability"
        ]
    }

@app.get(
    "/health",
    response_model=HealthResponse,
    tags=["🏥 Health"],
    response_model_exclude_none=True,
    response_class=PrettyJSONResponse,
    summary="Health Check",
    description="""
    Check if the API and all services are running properly.

    Returns the current status, version, and availability of external services (Exa API).

    **Example Response:**
    ```json
    {
      "status": "healthy",
      "timestamp": "2025-10-28T11:45:16.737109",
      "version": "2.0.0",
      "services": {
        "exa_api": "available"
      }
    }
    ```
    """,
)
def health_check():
    """Health check endpoint - verify API is running"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "version": "2.0.0",
        "services": {
            "exa_api": "available"
        }
    }





@app.get(
    "/stores/{zipcode}",
    tags=["🏪 Stores"],
    response_model=StoresResponse,
    response_model_exclude_none=True,
    response_class=PrettyJSONResponse,
    summary="Find Stores by ZIP Code",
    description="""
    Find grocery stores in a specific ZIP code.

    Returns a list of stores with their locations, services, and contact information.

    **Parameters:**
    - `zipcode` (path): 5-digit ZIP code (e.g., 60601)
    - `store_chain` (query, optional): Filter by specific store chain (e.g., "Target", "Walmart")

    **Example Request:**
    ```
    GET /stores/60601
    GET /stores/60601?store_chain=Target
    ```

    **Example Response:**
    ```json
    {
      "zipcode": "60601",
      "stores_found": 44,
      "stores": [
        {
          "store_id": "target",
          "store_name": "Target",
          "address": "123 Main St, Chicago, IL 60601",
          "services": ["in-store", "pickup", "delivery"],
          "status": "active",
          "zipcode": "60601",
          "location": {
            "zipcode": "60601",
            "city": "Chicago",
            "state": "IL"
          }
        }
      ]
    }
    ```

    **Supported Store Chains:**
    Target, Walmart, Whole Foods, Kroger, Safeway, ALDI, Costco, Trader Joe's, Sam's Club
    """,
)
async def get_stores_in_zipcode(
    zipcode: str = Path(..., description="5-digit ZIP code", example="60601"),
    store_chain: Optional[str] = Query(None, description="Filter by store chain", example="Target")
):
    """Find grocery stores in a ZIP code"""
    try:
        # Validate zipcode format
        import re
        if not re.match(r"^\d{5}$", zipcode):
            raise HTTPException(status_code=400, detail="Invalid zipcode format. Use 5-digit ZIP code.")
        
        # Try cache first
        cache_key = f"stores:{zipcode}:{store_chain or 'all'}"
        cached = await cache.get_json(cache_key) if cache else None
        if cached:
            logger.info(f"cache_hit stores zip={zipcode}")
            return {**cached, "cache": {"hit": True}}

        if not exa_client or not exa_client.is_available():
            raise HTTPException(
                status_code=503,
                detail="Exa client not available - check API key configuration"
            )
        
        # Get stores for specific chain or major chains
        all_stores = []
        chains_to_search = [store_chain] if store_chain else [
            "Target", "Walmart", "Whole Foods", "Kroger", "Safeway", "ALDI"
        ]
        
        for chain in chains_to_search:
            stores = await exa_client.search_stores_in_zipcode(chain, zipcode)
            all_stores.extend(stores)
        
        response_payload = {
            "zipcode": zipcode,
            "stores_found": len(all_stores),
            "search_timestamp": datetime.now().isoformat(),
            "stores": [
                {
                    "store_id": store["store_id"],
                    "store_name": store["store_name"],
                    "address": store.get("address"),
                    "services": store.get("services", ["in-store"]),
                    "status": store.get("status", "active"),
                    "zipcode": store.get("zipcode", zipcode),
                    "website": None,
                    "location": {
                        "zipcode": store.get("zipcode", zipcode),
                        "city": store.get("city"),
                        "state": store.get("state")
                    }
                }
                for store in all_stores
            ],
            "source": "exa_structured",
            "api_version": "2.0.0"
        }
        
        # Cache the results
        logger.info(f"cache_miss stores zip={zipcode} -> setting cache")
        if cache:
            await cache.set_json(cache_key, response_payload, ttl_seconds=60*60*24*7)  # 1 week cache
        
        return {**response_payload, "cache": {"hit": False}}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Store search failed: {e}")
        return {
                    "zipcode": zipcode,
            "stores_found": 0,
                    "search_timestamp": datetime.now().isoformat(),
            "stores": [],
            "source": f"error:{str(e)}",
            "api_version": "2.0.0",
        }

    



@app.get(
    "/products/search",
    response_model=ProductsSearchResponse,
    tags=["🛒 Products"],
    response_model_exclude_none=True,
    response_class=PrettyJSONResponse,
    summary="Search for Products",
    description="""
    Search for grocery products with AI-powered semantic search.

    Returns products with **real URLs** and **high-quality images** ready for web app integration.

    **Parameters:**
    - `query` (required): Product search term (e.g., "milk", "organic eggs", "whole wheat bread")
    - `store_name` (optional): Filter by store (e.g., "Target", "Walmart")
    - `zipcode` (optional): 5-digit ZIP code for location-based results
    - `num_results`: Number of results to return (default: 20, max: 50)
    - `refresh`: Bypass cache and get fresh results (default: false)

    **Example Requests:**
    ```
    GET /products/search?query=milk&zipcode=60601
    GET /products/search?query=organic+eggs&store_name=Target&zipcode=60601
    GET /products/search?query=bread&num_results=10
    ```

    **Example Response:**
    ```json
    {
      "query": "milk",
      "store_name": "Target",
      "location": "60601",
      "products_found": 5,
      "products": [
        {
          "name": "Milk - Good & Gather™",
          "brand": "Target",
          "price": null,
          "currency": "USD",
          "quantity": "0.5 Gallon",
          "image_url": "https://target.scene7.com/is/image/Target/94602358?wid=800&hei=800&qlt=80&fmt=webp",
          "product_url": "https://www.target.com/p/milk-good-gather/-/A-94602358",
          "store_name": "Target",
          "store_zipcode": "60601",
          "availability": "Check Store"
        }
      ]
    }
    ```

    **✅ What You Get:**
    - Real product page URLs (clickable links)
    - High-quality 800x800 images
    - Product names, brands, and quantities
    - Prices when available in page text (~20% coverage)
    - Store information and location
    """,
)
async def search_products(
    query: str = Query(..., description="Product search query", example="milk"),
    store_name: Optional[str] = Query(None, description="Filter by store name", example="Target"),
    zipcode: Optional[str] = Query(None, description="5-digit ZIP code", example="60601"),
    num_results: int = Query(20, ge=1, le=50, description="Number of results"),
    context: Optional[str] = Query(None, description="Search context (internal use)"),
    refresh: bool = Query(False, description="Bypass cache")
):
    """Search for grocery products with AI-powered search"""
    try:
        # Validate zipcode if provided
        if zipcode:
            import re
            if not re.match(r"^\d{5}$", zipcode):
                raise HTTPException(status_code=400, detail="Invalid zipcode format. Use 5-digit ZIP code.")
        
        # Check cache (skip if refresh requested)
        cache_key = f"products:{query}:{store_name or 'all'}:{zipcode or 'any'}:{num_results}"
        cached = None if refresh or not cache else await cache.get_json(cache_key)
        if cached and not refresh:
            logger.info(f"cache_hit products q='{query}'")
            return {**cached, "cache": {"hit": True}}
        
        products = []
        
        # Try partner API first if store_name is specified and we have API keys
        if store_name:
            store_id = store_name.lower().replace(" ", "_").replace("-", "_")
            # Normalize common store name variations
            store_id_map = {
                "target": "target",
                "walmart": "walmart",
                "kroger": "kroger",
                "marianos": "marianos",
                "mariano's": "marianos",
                "mariano": "marianos",
                "whole_foods": "whole_foods",
                "whole foods": "whole_foods",
            }
            store_id = store_id_map.get(store_id, store_id)
            
            # If searching Kroger in Chicago area, map to Mariano's
            if store_id == "kroger" and zipcode:
                from scraper.partner_api_client import is_chicago_area_zipcode
                if is_chicago_area_zipcode(zipcode):
                    store_id = "marianos"
                    logger.info(f"📍 Chicago area zipcode ({zipcode}) detected, mapping Kroger to Mariano's")
            
            if partner_api_client and partner_api_client.has_partner_api(store_id):
                logger.info(f"🎯 Using official {store_name} API for '{query}'")
                try:
                    products = await partner_api_client.search_products(
                        store_id=store_id,
                        query=query,
                        zipcode=zipcode,
                        limit=num_results
                    )
                    if products:
                        logger.info(f"✅ {store_name} partner API returned {len(products)} products")
                    else:
                        logger.info(f"⚠️ {store_name} partner API returned no results, falling back to Exa")
                except Exception as e:
                    logger.warning(f"Partner API error for {store_name}: {e}, falling back to Exa")
        
        # Fallback to Exa if no partner API or partner API returned no results
        if not products:
            if not exa_client or not exa_client.is_available():
                raise HTTPException(
                    status_code=503,
                    detail="Exa client not available - check API key configuration"
                )
            
            logger.info(f"🔍 Using Exa API for {store_name or 'all stores'}")
            products = await exa_client.search_products_structured(
                query=query,
                store_name=store_name,
                zipcode=zipcode,
                num_results=num_results,
                include_location=True,
                context=context
            )
        
        # SMART IMAGE HANDLING: Cache lookup + Exa extraction
        # Images are fetched using:
        # 1. Fuzzy matching cache (FAST - DB lookup, reuses images for similar products)
        # 2. Exa image_links (already included in search results)
        # 3. Exa get_contents (if needed, cached for future use)
        # This gives us images while staying fast!
        
        # Cache all products with images for future fuzzy matching
        if products:
            try:
                if image_cache:
                    await image_cache.cache_images_batch(products)
            except Exception as e:
                logger.debug(f"Failed to cache product images: {e}")
        
        # Verify prices using web search for products without prices (especially ALDI, Wegmans)
        if products and web_search_service:
            try:
                # Only verify prices for products that don't have prices yet
                products_to_verify = [p for p in products if not p.get("price") and p.get("product_url")]
                if products_to_verify:
                    logger.info(f"🔍 Verifying prices for {len(products_to_verify)} products using web search...")
                    verified_products = await web_search_service.batch_verify_prices(products_to_verify)
                    # Update original products list with verified prices
                    for i, product in enumerate(products):
                        if not product.get("price") and product.get("product_url"):
                            verified = next((p for p in verified_products if p.get("product_url") == product.get("product_url")), None)
                            if verified and verified.get("price"):
                                product["price"] = verified.get("price")
                                product["price_source"] = "web_search_verified"
                                logger.debug(f"✅ Verified price for {product.get('name', 'Unknown')}: ${product['price']}")
            except Exception as e:
                logger.warning(f"Price verification failed: {e}")
        
        # Determine source for response
        source = "exa_structured"
        if store_name and products:
            store_id_normalized = store_name.lower().replace(" ", "_").replace("-", "_")
            store_id_map = {
                "target": "target",
                "walmart": "walmart",
                "kroger": "kroger",
                "whole_foods": "whole_foods",
                "whole foods": "whole_foods",
            }
            store_id_normalized = store_id_map.get(store_id_normalized, store_id_normalized)
            if partner_api_client and partner_api_client.has_partner_api(store_id_normalized):
                source = "partner_api"
        
        response_payload = {
            "query": query,
            "store_name": store_name or "All Stores",
            "location": zipcode or "All Locations",
            "products_found": len(products),
            "search_timestamp": datetime.now().isoformat(),
            "products": products,
            "source": source,
            "api_version": "2.0.0"
        }
        
        # Cache the results
        logger.info(f"cache_miss products q='{query}' -> setting cache")
        if cache:
            await cache.set_json(cache_key, response_payload, ttl_seconds=60*60*4)  # 4 hours
        
        return {**response_payload, "cache": {"hit": False}}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Product search failed: {e}")
        return {
            "query": query,
            "store_name": store_name or "All Stores",
            "location": zipcode or "All Locations",
            "products_found": 0,
            "search_timestamp": datetime.now().isoformat(),
            "products": [],
            "source": f"error:{str(e)}",
            "api_version": "2.0.0"
        }

@app.get(
    "/products/verify-price",
    tags=["🛒 Products"],
    summary="Verify Product Price via Web Search",
    description="""
    Verify and extract accurate price from a product URL using web search.
    
    This endpoint uses Exa's structured extraction to get the exact price from the product page.
    Useful for verifying prices that may have been incorrectly extracted or are missing.
    
    **Parameters:**
    - `url` (required): Product page URL
    - `product_name` (optional): Product name for better context
    
    **Example:**
    ```
    GET /products/verify-price?url=https://www.aldi.us/product/strawberries-1-lb-0000000000003798
    ```
    
    **Response:**
    ```json
    {
      "price": 4.65,
      "currency": "USD",
      "source": "web_search",
      "url": "https://www.aldi.us/product/strawberries-1-lb-0000000000003798"
    }
    ```
    """,
)
async def verify_price(
    url: str = Query(..., description="Product page URL"),
    product_name: Optional[str] = Query(None, description="Product name (optional)")
):
    """Verify product price using web search"""
    if not web_search_service:
        raise HTTPException(
            status_code=503,
            detail="Web search service not available"
        )
    
    try:
        # Extract store name from URL if possible
        store_name = None
        if "aldi.us" in url:
            store_name = "ALDI"
        elif "wegmans.com" in url:
            store_name = "Wegmans"
        elif "target.com" in url:
            store_name = "Target"
        elif "walmart.com" in url:
            store_name = "Walmart"
        
        result = await web_search_service.verify_product_price(
            product_url=url,
            product_name=product_name,
            store_name=store_name
        )
        
        if result:
            return result
        else:
            raise HTTPException(
                status_code=404,
                detail="Could not extract price from the provided URL"
            )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Price verification error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get(
    "/products/search/stream",
    tags=["🛒 Products"],
    summary="Search Products (Streaming)",
    description="""
    Search for products with streaming results - products are returned as they're found!
    
    Returns products in real-time using Server-Sent Events (SSE) format.
    Each product is sent as a JSON event as soon as it's found, instead of waiting for all results.
    
    **Parameters:**
    - `query` (required): Product search term
    - `stores` (optional): Comma-separated store names (e.g., "Target,Walmart,ALDI")
    - `zipcode` (optional): 5-digit ZIP code
    - `num_results` (optional): Number of results per store (default: 5)
    
    **Example:**
    ```
    GET /products/search/stream?query=oat+milk&stores=Target,Walmart&zipcode=38125
    ```
    
    **Response Format (Server-Sent Events):**
    ```
    data: {"type": "product", "store": "Walmart", "product": {...}}
    
    data: {"type": "product", "store": "Target", "product": {...}}
    
    data: {"type": "complete", "total_products": 10}
    ```
    
    **Benefits:**
    - See results immediately as they're found
    - No waiting for slow stores
    - Better user experience with progressive loading
    """,
)
async def search_products_stream(
    query: str = Query(..., description="Product search query", example="oat milk"),
    stores: Optional[str] = Query(None, description="Comma-separated store names", example="Target,Walmart"),
    zipcode: Optional[str] = Query(None, description="5-digit ZIP code", example="38125"),
    num_results: int = Query(5, ge=1, le=20, description="Results per store")
):
    """Stream product search results in real-time"""
    
    async def generate_products():
        """Generator function that yields products as they're found"""
        try:
            # Determine which stores to search
            if stores:
                store_list = [s.strip() for s in stores.split(",")]
            else:
                # Default stores
                store_list = ["Walmart", "Target", "ALDI"]
            
            total_products = 0
            
            # Send initial metadata
            yield f"data: {json.dumps({'type': 'start', 'query': query, 'stores': store_list, 'zipcode': zipcode})}\n\n"
            
            # Use a queue to collect products from all stores as they arrive
            product_queue = asyncio.Queue()
            semaphore = asyncio.Semaphore(5)  # Limit concurrent store searches
            active_tasks = len(store_list)
            
            async def search_store(store_name: str):
                """Search a single store and put products in queue"""
                async with semaphore:
                    try:
                        # Map store name to store_id
                        store_id = store_name.lower().replace(" ", "_").replace("-", "_")
                        
                        # Try partner API first
                        products = []
                        if partner_api_client and partner_api_client.has_partner_api(store_id):
                            logger.info(f"🎯 Streaming from {store_name} partner API")
                            products = await partner_api_client.search_products(
                                store_id=store_id,
                                query=query,
                                zipcode=zipcode,
                                limit=num_results
                            )
                        else:
                            # Use Exa
                            if exa_client and exa_client.is_available():
                                logger.info(f"🔍 Streaming from Exa for {store_name}")
                                products = await exa_client.search_products_structured(
                                    query=query,
                                    store_name=store_name,
                                    zipcode=zipcode,
                                    num_results=num_results,
                                    include_location=False
                                )
                        
                        # Put each product in the queue
                        for product in products:
                            await product_queue.put(("product", store_name, product))
                        
                        # Send store completion
                        await product_queue.put(("store_complete", store_name, len(products)))
                        
                    except Exception as e:
                        logger.error(f"Error streaming from {store_name}: {e}")
                        await product_queue.put(("error", store_name, str(e)))
            
            # Start all store searches concurrently
            tasks = [asyncio.create_task(search_store(store)) for store in store_list]
            
            # Create a task to mark completion when all searches are done
            async def mark_complete():
                await asyncio.gather(*tasks, return_exceptions=True)
                await product_queue.put(("complete", None, None))
            
            completion_task = asyncio.create_task(mark_complete())
            
            # Yield products as they arrive in the queue
            while True:
                event_type, store, data = await product_queue.get()
                
                if event_type == "product":
                    total_products += 1
                    event_data = {
                        "type": "product",
                        "store": store,
                        "product": data
                    }
                    yield f"data: {json.dumps(event_data)}\n\n"
                
                elif event_type == "store_complete":
                    yield f"data: {json.dumps({'type': 'store_complete', 'store': store, 'count': data})}\n\n"
                
                elif event_type == "error":
                    yield f"data: {json.dumps({'type': 'error', 'store': store, 'error': data})}\n\n"
                
                elif event_type == "complete":
                    # All stores finished
                    yield f"data: {json.dumps({'type': 'complete', 'total_products': total_products})}\n\n"
                    break
            
        except Exception as e:
            logger.error(f"Streaming error: {e}")
            yield f"data: {json.dumps({'type': 'error', 'error': str(e)})}\n\n"
    
    return StreamingResponse(
        generate_products(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"  # Disable nginx buffering
        }
    )

@app.get(
    "/products/aggregate/stream",
    tags=["📊 Aggregate"],
    summary="Compare Products (Streaming)",
    description="""
    Compare products across multiple stores with streaming results - offers are returned as they're found!
    
    Returns aggregated product offers in real-time using Server-Sent Events (SSE) format.
    Each store's products are sent as JSON events as soon as they're found.
    
    **Parameters:**
    - `query` (required): Product to search for
    - `zipcode` (required): 5-digit ZIP code
    - `stores` (optional): Comma-separated store names (e.g., "Walmart,Target,ALDI")
    - `limit` (optional): Max products per store (default: 8)
    
    **Example:**
    ```
    GET /products/aggregate/stream?query=oat+milk&zipcode=38125&stores=Walmart,Target,ALDI
    ```
    
    **Response Format (Server-Sent Events):**
    ```
    data: {"type": "start", "query": "oat milk", "stores": [...]}
    
    data: {"type": "store_products", "store": "Walmart", "products": [...], "count": 5}
    
    data: {"type": "store_products", "store": "Target", "products": [...], "count": 3}
    
    data: {"type": "complete", "total_products": 8, "stores_searched": ["Walmart", "Target"]}
    ```
    
    **Benefits:**
    - See results immediately as each store responds
    - No waiting for slow stores
    - Better user experience with progressive loading
    - Perfect for real-time price comparison UIs
    """,
)
async def aggregate_products_stream(
    query: str = Query(..., description="Product to search for", example="oat milk"),
    zipcode: str = Query(..., description="5-digit ZIP code", example="38125"),
    stores: Optional[str] = Query(None, description="Comma-separated store names", example="Walmart,Target,ALDI"),
    limit: int = Query(8, ge=1, le=20, description="Max products per store")
):
    """Stream aggregate product comparison results in real-time"""
    import re
    
    # Validate zipcode
    if not re.match(r"^\d{5}$", zipcode):
        raise HTTPException(status_code=400, detail="Invalid zipcode format")
    
    async def generate_aggregate():
        """Generator function that yields aggregated products as they're found"""
        try:
            # Determine which stores to search
            if stores:
                store_list = [s.strip() for s in stores.split(",")]
            else:
                # Default stores
                store_list = ["Walmart", "ALDI", "Kroger"]
            
            # Map to store IDs
            store_ids = [s.lower().replace(" ", "_").replace("-", "_") for s in store_list]
            
            # Filter by location if location_service available
            if location_service:
                considered_store_ids = location_service.filter_stores_by_location(store_ids, zipcode)
                if not considered_store_ids:
                    considered_store_ids = store_ids[:3]  # Fallback to first 3
            else:
                considered_store_ids = store_ids
            
            total_products = 0
            stores_with_results = []
            
            # Send initial metadata
            yield f"data: {json.dumps({'type': 'start', 'query': query, 'stores': considered_store_ids, 'zipcode': zipcode})}\n\n"
            
            # Helper to convert store_id to display name
            def to_store_name(store_id: str) -> str:
                mapping = {
                    "whole_foods": "Whole Foods",
                    "sams_club": "Sam's Club",
                    "trader_joes": "Trader Joe's",
                    "kroger": "Kroger",
                    "marianos": "Mariano's",
                    "target": "Target",
                    "walmart": "Walmart",
                    "costco": "Costco",
                    "aldi": "ALDI",
                    "safeway": "Safeway",
                    "albertsons": "Albertsons",
                    "publix": "Publix",
                    "heb": "H-E-B",
                    "wegmans": "Wegmans",
                }
                return mapping.get(store_id, store_id.replace("_", " ").title())
            
            # Use a queue to collect products from all stores as they arrive
            product_queue = asyncio.Queue()
            semaphore = asyncio.Semaphore(5)  # Limit concurrent store searches
            
            async def search_store(store_id: str):
                """Search a single store and put products in queue"""
                async with semaphore:
                    try:
                        store_name = to_store_name(store_id)
                        products = []
                        
                        # Try partner API first
                        if partner_api_client and partner_api_client.has_partner_api(store_id):
                            logger.info(f"🎯 Streaming aggregate from {store_name} partner API")
                            products = await partner_api_client.search_products(
                                store_id=store_id,
                                query=query,
                                zipcode=zipcode,
                                limit=limit
                            )
                        
                        # Fallback to Exa if no partner API or no results
                        if not products and exa_client and exa_client.is_available():
                            logger.info(f"🔍 Streaming aggregate from Exa for {store_name}")
                            products = await exa_client.search_products_structured(
                                query=query,
                                store_name=store_name,
                                zipcode=zipcode,
                                num_results=limit,
                                include_location=False,
                                context="price_comparison"
                            )
                        
                        # Format products for aggregate response
                        formatted_products = []
                        for p in products:
                            formatted_products.append({
                                "name": p.get("name"),
                                "brand": p.get("brand"),
                                "price": p.get("price"),
                                "currency": p.get("currency", "USD"),
                                "quantity": p.get("quantity") or p.get("size"),
                                "image_url": p.get("image_url"),
                                "product_url": p.get("product_url"),
                                "store_name": store_name,
                                "store_id": store_id,
                                "store_zipcode": zipcode
                            })
                        
                        # Put all products for this store in the queue
                        await product_queue.put(("store_products", store_id, store_name, formatted_products))
                        
                    except Exception as e:
                        logger.error(f"Error streaming aggregate from {store_id}: {e}")
                        await product_queue.put(("error", store_id, to_store_name(store_id), str(e)))
            
            # Start all store searches concurrently
            tasks = [asyncio.create_task(search_store(sid)) for sid in considered_store_ids]
            
            # Create a task to mark completion when all searches are done
            async def mark_complete():
                await asyncio.gather(*tasks, return_exceptions=True)
                await product_queue.put(("complete", None, None, None))
            
            completion_task = asyncio.create_task(mark_complete())
            
            # Yield products as they arrive in the queue
            while True:
                event_type, store_id, store_name, data = await product_queue.get()
                
                if event_type == "store_products":
                    product_count = len(data)
                    total_products += product_count
                    if product_count > 0:
                        stores_with_results.append(store_name)
                    event_data = {
                        "type": "store_products",
                        "store": store_name,
                        "store_id": store_id,
                        "products": data,
                        "count": product_count
                    }
                    yield f"data: {json.dumps(event_data)}\n\n"
                
                elif event_type == "error":
                    yield f"data: {json.dumps({'type': 'error', 'store': store_name, 'error': data})}\n\n"
                
                elif event_type == "complete":
                    # All stores finished
                    yield f"data: {json.dumps({'type': 'complete', 'total_products': total_products, 'stores_searched': stores_with_results, 'zipcode': zipcode})}\n\n"
                    break
            
        except Exception as e:
            logger.error(f"Streaming aggregate error: {e}")
            yield f"data: {json.dumps({'type': 'error', 'error': str(e)})}\n\n"
    
    return StreamingResponse(
        generate_aggregate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"  # Disable nginx buffering
        }
    )

@app.get(
    "/products/aggregate",
    response_model=AggregateResponseEnhanced,
    tags=["📊 Aggregate"],
    response_model_exclude_none=True,
    response_class=PrettyJSONResponse,
    responses={
        200: {
            "description": "Aggregate product results",
            "content": {
                "application/json": {
                    "schema": AggregateResponse.model_json_schema()
                }
            }
        }
    },
    summary="Compare Products Across Stores",
    description="""
    Compare the same products across multiple stores to find the best deals.

    Groups identical products together and shows offers from different retailers.

    **Parameters:**
    - `query` (required): Product to search for (e.g., "eggs", "milk", "bread")
    - `zipcode` (required): 5-digit ZIP code
    - `radius_miles`: Search radius in miles (default: 10)
    - `stores`: Comma-separated store IDs to search (e.g., "target,walmart")
    - `limit`: Maximum number of products to return (default: 50, max: 100)
    - `refresh`: Bypass cache (default: false)

    **Example Requests:**
    ```
    GET /products/aggregate?query=eggs&zipcode=60601
    GET /products/aggregate?query=milk&zipcode=60601&stores=target,walmart
    GET /products/aggregate?query=bread&zipcode=10001&radius_miles=15
    GET /products/aggregate?query=eggs&zipcode=60601&limit=10
    ```

    **Example Response:**
    ```json
    {
      "query": "eggs",
      "zipcode": "60601",
      "stores_considered": ["target", "walmart"],
      "results": [
        {
          "canonical_product": {
            "name": "Grade A Large Eggs - 12ct",
            "brand": "Target",
            "quantity": "12ct",
            "images": [
              "https://target.scene7.com/is/image/Target/14713534?wid=800&hei=800&qlt=80&fmt=webp"
            ]
          },
          "offers": [
            {
              "store_id": "target",
              "store_name": "Target",
              "price": 4.99,
              "currency": "USD",
              "product_url": "https://www.target.com/p/...",
              "image_url": "https://target.scene7.com/...",
              "zipcode": "60601"
            },
            {
              "store_id": "walmart",
              "store_name": "Walmart",
              "price": 4.49,
              "currency": "USD",
              "product_url": "https://www.walmart.com/ip/...",
              "zipcode": "60601"
            }
          ]
        }
      ]
    }
    ```

    **💡 Use Cases:**
    - Price comparison across stores
    - Finding the best deals
    - Checking product availability at multiple retailers
    - Building shopping lists with optimal store selection

    **Default Stores (when no stores parameter provided):**
    walmart, aldi, kroger
    
    **Available Stores:**
    target, walmart, whole_foods, kroger, aldi, costco, trader_joes, sams_club, safeway, albertsons, publix, heb, wegmans
    """,
)
async def aggregate_products(
    query: str = Query(..., description="Product to search for", example="eggs"),
    zipcode: str = Query(..., description="5-digit ZIP code", example="60601"),
    radius_miles: int = Query(10, ge=1, le=50, description="Search radius in miles"),
    stores: Optional[str] = Query(None, description="Comma-separated store IDs", example="target,walmart"),
    limit: int = Query(50, ge=1, le=100, description="Maximum number of products to return"),
    refresh: bool = Query(False, description="Bypass cache")
):
    """Compare products across multiple stores"""
    import re  # Import at function level for use in derive_image_from_product_url
    try:
        # Validate zipcode
        if not re.match(r"^\d{5}$", zipcode):
            raise HTTPException(status_code=400, detail="Invalid zipcode format")

        # Determine store set
        user_store_ids = []
        if stores:
            user_store_ids = [s.strip().lower() for s in stores.split(",") if s.strip()]

        # Default major grocery store chains
        default_stores = ["walmart", "aldi", "kroger"]
        requested_store_ids = user_store_ids[:10] if user_store_ids else default_stores
        
        # If searching in Chicago area, map Kroger to Mariano's
        from scraper.partner_api_client import is_chicago_area_zipcode
        if is_chicago_area_zipcode(zipcode):
            # Replace kroger with marianos in requested stores (whether from user input or defaults)
            if "kroger" in requested_store_ids:
                requested_store_ids = [s if s != "kroger" else "marianos" for s in requested_store_ids]
                logger.info(f"📍 Chicago area zipcode ({zipcode}) detected, mapping Kroger to Mariano's in aggregate search")
            # If using defaults and marianos not already in list, add it
            elif not user_store_ids and "marianos" not in requested_store_ids:
                requested_store_ids.append("marianos")
                logger.info(f"📍 Chicago area zipcode ({zipcode}) detected, adding Mariano's to default stores")
        
        # Filter stores by location availability
        if location_service:
            # Filter requested stores to only include those available in zipcode
            considered_store_ids = location_service.filter_stores_by_location(requested_store_ids, zipcode)
            
            # If no stores available after filtering, return empty response
            if not considered_store_ids:
                logger.warning(f"⚠️ No stores available in zipcode {zipcode} from requested stores: {requested_store_ids}")
                return {
                    "query": query,
                    "zipcode": zipcode,
                    "search_timestamp": datetime.utcnow().isoformat() + "Z",
                    "results": [],
                    "stores_considered": [],
                    "meta": {
                        "api_version": "2.1.0",
                        "cache": {"hit": False},
                        "stores_searched": [],
                        "stores_available": location_service.filter_stores_by_location(
                            ["walmart", "target", "aldi", "kroger", "marianos", "costco", "whole_foods", "sams_club", 
                             "trader_joes", "safeway", "albertsons", "wegmans", "publix", "heb", "giant_eagle",
                             "meijer", "hy_vee", "sprouts"],
                            zipcode
                        )
                    }
                }
            
            # Get all available stores for this zipcode (for UI display)
            # This includes all nationwide stores + regional stores available in zipcode
            all_available_store_ids = location_service.filter_stores_by_location(
                ["walmart", "target", "aldi", "kroger", "marianos", "costco", "whole_foods", "sams_club", 
                 "trader_joes", "safeway", "albertsons", "wegmans", "publix", "heb", "giant_eagle",
                 "meijer", "hy_vee", "sprouts"],
                zipcode
            )
        else:
            # Fallback if location_service not available
            logger.warning("LocationService not available, skipping location filtering")
            considered_store_ids = requested_store_ids
            all_available_store_ids = requested_store_ids

        # Helper functions for data normalization (needed for cache transformation)
        def norm_text(s: Optional[str]) -> str:
            return (s or "").lower().strip()

        def norm_name(name: Optional[str]) -> str:
            n = norm_text(name)
            for token in ["brand", "original", "the"]:
                n = n.replace(f" {token} ", " ")
            n = n.replace("-", " ")
            return " ".join(n.split())

        def norm_quantity(qty: Optional[str]) -> str:
            q = norm_text(qty)
            q = q.replace("fluid ounces", "fl oz").replace("fluid ounce", "fl oz")
            q = q.replace("ounces", "oz").replace("ounce", "oz")
            q = q.replace("fl. oz", "fl oz").replace("fl-oz", "fl oz")
            q = q.replace("packs", "pack").replace(" ct", " count")
            return " ".join(q.split())

        def to_store_name(store_id: str) -> str:
            mapping = {
                "whole_foods": "Whole Foods",
                "sams_club": "Sam's Club",
                "trader_joes": "Trader Joe's",
                "kroger": "Kroger",
                "marianos": "Mariano's",
                "mariano's": "Mariano's",
                "target": "Target",
                "walmart": "Walmart",
                "costco": "Costco",
                "aldi": "ALDI",
                "safeway": "Safeway",
                "albertsons": "Albertsons",
                "publix": "Publix",
                "heb": "H-E-B",
                "wegmans": "Wegmans",
            }
            return mapping.get(store_id, store_id.replace("_", " ").title())

        # Cache lookup - use filtered stores in cache key
        cache_key = f"aggregate:{zipcode}:{query}:{':'.join(sorted(considered_store_ids))}:limit{limit}"
        cached = None if refresh or not cache else await cache.get_json(cache_key)
        if cached and not refresh:
            logger.info(f"cache_hit aggregate zip={zipcode} q='{query}'")
            # Check if cached data is in enhanced format (has search_timestamp and meta)
            if cached.get("search_timestamp") and cached.get("meta"):
                # Already in enhanced format, just update cache hit status and apply limit
                cached["meta"]["cache"] = {"hit": True}
                if limit and len(cached.get("results", [])) > limit:
                    cached["results"] = cached["results"][:limit]
                return cached
            else:
                # Old standard format cached, need to transform it
                logger.info("Transforming cached standard format to enhanced format")
                # Rebuild grouped structure from cached standard format
                grouped_from_cache = {}
                for result in cached.get("results", []):
                    canonical = result.get("canonical_product", {})
                    offers = result.get("offers", [])
                    # Create grouping key
                    brand = norm_text(canonical.get("brand"))
                    name = norm_name(canonical.get("name"))
                    quantity = norm_quantity(canonical.get("quantity") or canonical.get("size"))
                    gkey = f"{brand}|{name}|{quantity}"
                    grouped_from_cache[gkey] = {
                        "canonical_product": canonical,
                        "offers": offers
                    }
                # Fetch store locations for transformation
                store_locations_cache = {}
                async def fetch_store_locations(store_id: str):
                    try:
                        store_name = to_store_name(store_id)
                        stores = await exa_client.search_stores_in_zipcode(store_name, zipcode)
                        if stores:
                            store_locations_cache[store_id] = stores[0]
                    except Exception as e:
                        logger.warning(f"⚠️ Failed to fetch store location for {store_id}: {e}")
                
                await asyncio.gather(*[fetch_store_locations(sid) for sid in considered_store_ids], return_exceptions=True)
                
                # Get coordinates for the zipcode
                geocoding_service = get_geocoding_service()
                _, _, cached_lat, cached_lng = await geocoding_service.get_location_from_zipcode(zipcode)
                
                # Transform to enhanced format
                # Get available stores for cached response (use considered_store_ids as fallback)
                cached_stores_available = all_available_store_ids if 'all_available_store_ids' in locals() else considered_store_ids
                enhanced_cached = await transform_to_enhanced_format(
                    grouped_from_cache, 
                    considered_store_ids, 
                    query, 
                    zipcode, 
                    store_locations_cache,
                    stores_available=cached_stores_available,
                    zipcode_lat=cached_lat,
                    zipcode_lng=cached_lng
                )
                enhanced_cached["meta"]["cache"] = {"hit": True}
                # Apply limit if needed
                if limit and len(enhanced_cached.get("results", [])) > limit:
                    enhanced_cached["results"] = enhanced_cached["results"][:limit]
                return enhanced_cached

        if not exa_client.is_available():
            raise HTTPException(
                status_code=503,
                detail="Exa client not available - check API key configuration"
            )

        # Search products across all stores concurrently - INCREASED CONCURRENCY
        semaphore = asyncio.Semaphore(10)  # Increased from 5 to 10 for faster parallel processing
        
        async def fetch_store_products(store_id: str):
            async with semaphore:
                try:
                    store_name = to_store_name(store_id)
                    logger.info(f"Searching {store_name} for '{query}' near {zipcode}")
                    
                    products = []
                    
                    # Try official partner API first if available
                    if partner_api_client and partner_api_client.has_partner_api(store_id):
                        logger.info(f"🎯 Using official {store_name} API")
                        products = await partner_api_client.search_products(
                            store_id=store_id,
                            query=query,
                            zipcode=zipcode,
                            limit=8
                        )
                        
                        # If partner API returned results, use them
                        if products:
                            logger.info(f"✅ {store_name} partner API returned {len(products)} products")
                        else:
                            logger.info(f"⚠️ {store_name} partner API returned no results (skipping Exa for legacy products)")
                    else:
                        # Only use Exa for stores without partner API
                        logger.info(f"🔍 Using Exa API for {store_name} (no partner API available)")
                        products = await exa_client.search_products_structured(
                            query=query,
                            store_name=store_name,
                            zipcode=zipcode,
                            num_results=8,  # Reduced from 10 to 8 for faster processing
                            include_location=False,  # Skip location fetching for speed (can be added later if needed)
                            context="price_comparison"  # Use price comparison context for aggregate
                        )
                    
                    return {
                        "store_id": store_id,
                        "store_name": store_name,
                        "products": products
                    }
                except Exception as e:
                    logger.warning(f"Error fetching from {store_id}: {e}", exc_info=True)
                    return {
                        "store_id": store_id,
                        "store_name": to_store_name(store_id),
                        "products": []
                    }

        # Fetch from all stores concurrently with timeout
        tasks = [fetch_store_products(sid) for sid in considered_store_ids]
        # Use asyncio.wait_for with timeout to prevent hanging
        async def fetch_with_timeout(task, timeout=30):  # Increased timeout for partner APIs (Kroger can be slow)
            try:
                return await asyncio.wait_for(task, timeout=timeout)
            except asyncio.TimeoutError:
                logger.warning(f"Store search timed out after {timeout}s")
                return {"store_id": "unknown", "store_name": "Unknown", "products": []}
        
        store_results = await asyncio.gather(*[fetch_with_timeout(task) for task in tasks], return_exceptions=False)

        # Log results from each store
        total_products = 0
        for result in store_results:
            product_count = len(result.get("products", []))
            total_products += product_count
            logger.info(f"📦 {result.get('store_name', 'Unknown')}: {product_count} products found")
        
        logger.info(f"📊 Total products found across all stores: {total_products}")

        # Verify prices using web search for products without prices (especially ALDI, Wegmans)
        if web_search_service:
            try:
                # Collect all products that need price verification
                products_to_verify = []
                for result in store_results:
                    for product in result.get("products", []):
                        if not product.get("price") and product.get("product_url"):
                            products_to_verify.append(product)
                
                if products_to_verify:
                    logger.info(f"🔍 Verifying prices for {len(products_to_verify)} products in aggregate search using web search...")
                    verified_products = await web_search_service.batch_verify_prices(products_to_verify)
                    # Create lookup dict for verified prices
                    verified_dict = {p.get("product_url"): p.get("price") for p in verified_products if p.get("price")}
                    # Update products with verified prices
                    for result in store_results:
                        for product in result.get("products", []):
                            product_url = product.get("product_url")
                            if not product.get("price") and product_url and product_url in verified_dict:
                                product["price"] = verified_dict[product_url]
                                product["price_source"] = "web_search_verified"
                                logger.debug(f"✅ Verified price for {product.get('name', 'Unknown')}: ${product['price']}")
            except Exception as e:
                logger.warning(f"Price verification failed in aggregate: {e}")

        # Aggregate products by canonical product
        grouped = {}
        for result in store_results:
            store_id = result["store_id"]
            store_name = result["store_name"]
            
            for product in result["products"]:
                # Create grouping key
                brand = norm_text(product.get("brand"))
                name = norm_name(product.get("name"))
                quantity = norm_quantity(product.get("quantity") or product.get("size"))
                gkey = f"{brand}|{name}|{quantity}"
                
                # Initialize canonical product if needed
                if gkey not in grouped:
                    grouped[gkey] = {
                        "canonical_product": {
                            "name": product.get("name"),
                            "brand": product.get("brand"),
                            "quantity": product.get("quantity") or product.get("size"),
                            "size": product.get("quantity") or product.get("size"),
                            "images": [],
                            "description": product.get("description"),
                            "category": product.get("category")
                    },
                    "offers": []
                }
                
                # Helper function to check if image is Wegmans logo
                def is_wegmans_logo(image_url: Optional[str]) -> bool:
                    if not image_url:
                        return False
                    image_lower = image_url.lower()
                    return 'wegmans-og-share-img' in image_lower or '53100' in image_url
                
                # Add image to canonical product if not already there (filter out Wegmans logos)
                if product.get("image_url") and not is_wegmans_logo(product["image_url"]):
                    canonical_images = grouped[gkey]["canonical_product"]["images"]
                    if product["image_url"] not in canonical_images:
                        canonical_images.append(product["image_url"])
                
                # Add additional images (filter out Wegmans logos)
                if product.get("additional_images"):
                    for img in product["additional_images"]:
                        if not is_wegmans_logo(img):
                            canonical_images = grouped[gkey]["canonical_product"]["images"]
                            if img not in canonical_images:
                                canonical_images.append(img)
                
                # Add offer
                grouped[gkey]["offers"].append({
                    "store_id": store_id,
                    "store_name": store_name,
                    "price": product.get("price"),
                    "currency": product.get("currency", "USD"),
                    "quantity": product.get("quantity") or product.get("size"),
                    "availability": product.get("availability"),
                    "product_url": product.get("product_url"),
                    "image_url": product.get("image_url"),
                    "source": [product.get("source", "exa_structured")],
                    "address": product.get("store_address"),
                    "city": product.get("store_city"),
                    "state": product.get("store_state"),
                    "zipcode": product.get("store_zipcode") or zipcode
                })

        logger.info(f"📊 Grouped {len(grouped)} unique products from {total_products} total products")

        # Hybrid image extraction: Exa batch + HTML scraper fallback
        async def derive_image_from_product_url(product_url: Optional[str], exa_image: Optional[str] = None) -> Optional[str]:
            """Derive image URL from product URL pattern (fallback method with validation)"""
            # Priority 1: Use Exa's image field if available (most reliable)
            if exa_image:
                return exa_image
            
            if not product_url:
                return None
            try:
                url = product_url.lower()
                
                # Target: Try different image CDN formats
                if "target.com" in url and "/a-" in url:
                    try:
                        pid = product_url.split("/A-")[1].split("/")[0]
                        # Try multiple Target image formats
                        formats = [
                            f"https://target.scene7.com/is/image/Target/{pid}?wid=1200&hei=1200&qlt=80&fmt=webp",
                            f"https://target.scene7.com/is/image/Target/{pid}?wid=800&hei=800&qlt=80&fmt=webp",
                            f"https://target.scene7.com/is/image/Target/{pid}"
                        ]
                        # Return first format (will validate later)
                        return formats[0]
                    except Exception:
                        pass
                
                # Walmart: Extract product ID from URL
                if "walmart.com" in url and "/ip/" in url:
                    try:
                        match = re.search(r'/ip/[^/]+/(\d+)', url)
                        if match:
                            product_id = match.group(1)
                            # Try multiple Walmart CDN patterns
                            formats = [
                                f"https://i5.walmartimages.com/asr/{product_id}.jpeg?odnHeight=612&odnWidth=612&odnBg=FFFFFF",
                                f"https://i5.walmartimages.com/asr/{product_id}.jpeg",
                                f"https://i5.walmartimages.com/seo/{product_id}.jpeg"
                            ]
                            return formats[0]
                    except Exception:
                        pass
                
                return None
            except Exception:
                return None

        # Collect all product URLs that need images
        # Also filter out Wegmans logo images that might have been incorrectly set
        urls_needing_images = []
        url_to_offer_map = {}  # Map product_url -> list of (group_key, offer_index)
        
        def is_wegmans_logo_image(image_url: Optional[str]) -> bool:
            """Check if image URL is a Wegmans logo/share image"""
            if not image_url:
                return False
            image_lower = image_url.lower()
            return 'wegmans-og-share-img' in image_lower or '53100' in image_url
        
        for group_key, group in grouped.items():
            for offer_idx, offer in enumerate(group["offers"]):
                product_url = offer.get("product_url")
                image_url = offer.get("image_url")
                
                # If image is Wegmans logo, mark as needing replacement
                if image_url and is_wegmans_logo_image(image_url):
                    logger.debug(f"🔄 Filtering out Wegmans logo image: {image_url[:80]}...")
                    offer["image_url"] = None  # Clear the logo image
                
                # For Wegmans, always fetch product pages to get real images (even if image_url exists)
                # This ensures we get product images from the actual product page, not search results
                is_wegmans = product_url and 'wegmans.com' in product_url.lower() and '/shop/product/' in product_url.lower()
                
                # Add to list if no image OR if it's a Wegmans product (to fetch from product page)
                if product_url and (not offer.get("image_url") or is_wegmans):
                    if product_url not in url_to_offer_map:
                        url_to_offer_map[product_url] = []
                        urls_needing_images.append(product_url)
                    url_to_offer_map[product_url].append((group_key, offer_idx))

        # PRIORITY 1: Use Exa-provided images (already set from search results)
        # (Already handled - images from search are already in offers)

        # PRIORITY 2: Batch Exa get_contents for missing images
        exa_image_results = {}
        if urls_needing_images and exa_client.is_available():
            logger.info(f"🖼️ Fetching {len(urls_needing_images)} images via Exa batch extraction...")
            try:
                exa_image_results = await exa_client.get_product_images_batch(
                    urls_needing_images,
                    max_concurrent=5  # Rate limit Exa API calls
                )
                logger.info(f"✅ Exa batch extraction complete: {sum(1 for v in exa_image_results.values() if v)}/{len(exa_image_results)} images found")
            except Exception as e:
                logger.warning(f"⚠️ Exa batch image extraction failed: {e}")

        # Update offers with Exa images
        for product_url, image_url in exa_image_results.items():
            if image_url and product_url in url_to_offer_map:
                for group_key, offer_idx in url_to_offer_map[product_url]:
                    grouped[group_key]["offers"][offer_idx]["image_url"] = image_url

        # PRIORITY 3: AI scraper for Wegmans products (more reliable than HTML parsing)
        remaining_urls = [url for url in urls_needing_images if url not in exa_image_results or not exa_image_results[url]]
        ai_image_results = {}
        wegmans_urls = [url for url in remaining_urls if 'wegmans.com' in url.lower() and '/shop/product/' in url.lower()]
        
        # Always try AI scraper first if available, but don't block if it's not
        if wegmans_urls and ai_scraper.is_available():
            logger.info(f"🤖 Using AI scraper to extract images from {len(wegmans_urls)} Wegmans product pages...")
            try:
                async def extract_with_ai(url: str):
                    try:
                        data = await ai_scraper.extract_product_data(url, store_name="Wegmans")
                        image_url = data.get("image_url")
                        if image_url:
                            logger.debug(f"✅ AI extracted image for {url[:60]}...: {image_url[:80]}...")
                        return image_url
                    except Exception as e:
                        logger.debug(f"AI extraction failed for {url}: {e}")
                        return None
                
                # Process Wegmans URLs with AI scraper (limit concurrent to avoid rate limits)
                semaphore = asyncio.Semaphore(3)
                async def process_wegmans_url(url: str):
                    async with semaphore:
                        image_url = await extract_with_ai(url)
                        if image_url:
                            ai_image_results[url] = image_url
                
                await asyncio.gather(*[process_wegmans_url(url) for url in wegmans_urls[:10]])  # Limit to 10
                logger.info(f"✅ AI scraper complete: {sum(1 for v in ai_image_results.values() if v)}/{len(ai_image_results)} images found")
            except Exception as e:
                logger.warning(f"⚠️ AI image extraction failed: {e}")
        elif wegmans_urls:
            logger.info(f"⚠️ AI scraper not available (no API keys), will use HTML scraper for {len(wegmans_urls)} Wegmans URLs")
        
        # Update offers with AI scraper images
        for product_url, image_url in ai_image_results.items():
            if image_url and product_url in url_to_offer_map:
                # Filter out Wegmans logos (AI should handle this, but double-check)
                if 'wegmans-og-share-img' not in image_url.lower() and '53100' not in image_url:
                    for group_key, offer_idx in url_to_offer_map[product_url]:
                        grouped[group_key]["offers"][offer_idx]["image_url"] = image_url
                        logger.debug(f"✅ Updated offer image from AI scraper: {image_url[:80]}...")
                else:
                    logger.debug(f"🔄 Filtered out Wegmans logo from AI scraper: {image_url[:80]}...")
        
        # PRIORITY 4: HTML scraper for remaining missing images (non-Wegmans or fallback)
        # Also include Wegmans URLs that didn't get AI extraction (fallback)
        remaining_urls = [url for url in remaining_urls if url not in ai_image_results or not ai_image_results[url]]
        # Also add ALL Wegmans URLs that need images (even if AI was attempted)
        wegmans_urls_for_html = [url for url in urls_needing_images if 'wegmans.com' in url.lower() and '/shop/product/' in url.lower() and (url not in ai_image_results or not ai_image_results[url])]
        remaining_urls = list(set(remaining_urls + wegmans_urls_for_html))
        
        logger.info(f"📋 Image extraction status: Exa={len(exa_image_results)}, AI={len(ai_image_results)}, Remaining={len(remaining_urls)} (Wegmans={len(wegmans_urls_for_html)})")
        
        html_image_results = {}
        if remaining_urls:
            logger.info(f"🖼️ Fetching {len(remaining_urls)} images via HTML scraper (including {len(wegmans_urls_for_html)} Wegmans URLs)...")
            logger.info(f"📋 Sample URLs: {remaining_urls[:2]}")
            try:
                async with HTMLImageExtractor() as html_extractor:
                    html_image_results = await html_extractor.extract_images_batch(
                        remaining_urls,
                        max_concurrent=10  # Can do more concurrent requests with direct HTML scraping
                    )
                found_count = sum(1 for v in html_image_results.values() if v)
                logger.info(f"✅ HTML scraper complete: {found_count}/{len(html_image_results)} images found")
                # Log Wegmans-specific results
                wegmans_html_results = {url: img for url, img in html_image_results.items() if 'wegmans.com' in url.lower()}
                if wegmans_html_results:
                    wegmans_found = sum(1 for v in wegmans_html_results.values() if v)
                    logger.info(f"✅ Wegmans HTML extraction: {wegmans_found}/{len(wegmans_html_results)} images found")
                    # Log specific results
                    for url, img in list(wegmans_html_results.items())[:3]:
                        if img:
                            logger.info(f"  ✅ {url[:60]}... -> {img[:80]}...")
                        else:
                            logger.warning(f"  ❌ {url[:60]}... -> No image found")
            except Exception as e:
                logger.error(f"⚠️ HTML image extraction failed: {e}", exc_info=True)

        # Update offers with HTML scraper images
        for product_url, image_url in html_image_results.items():
            if image_url and product_url in url_to_offer_map:
                # Filter out Wegmans logos
                if 'wegmans-og-share-img' not in image_url.lower() and '53100' not in image_url:
                    for group_key, offer_idx in url_to_offer_map[product_url]:
                        grouped[group_key]["offers"][offer_idx]["image_url"] = image_url
                        logger.info(f"✅ Updated offer image from HTML scraper for {product_url[:60]}...: {image_url[:80]}...")
                else:
                    logger.debug(f"🔄 Filtered out Wegmans logo from HTML scraper: {image_url[:80]}...")

        # PRIORITY 5: URL pattern matching with validation (last resort)
        remaining_urls = [url for url in remaining_urls if url not in html_image_results or not html_image_results[url]]
        if remaining_urls:
            logger.info(f"🖼️ Trying URL pattern matching for {len(remaining_urls)} products...")
            # Use aiohttp for validation
            import aiohttp
            async with aiohttp.ClientSession() as session:
                async def validate_derived_image(url: str) -> Optional[str]:
                    derived = await derive_image_from_product_url(url)
                    if derived:
                        # Validate the derived URL
                        try:
                            async with session.head(derived, allow_redirects=True, timeout=aiohttp.ClientTimeout(total=5)) as response:
                                if response.status == 200:
                                    content_type = response.headers.get('Content-Type', '').lower()
                                    if content_type.startswith('image/') or any(ext in derived.lower() for ext in ['.jpg', '.jpeg', '.png', '.webp', '.gif']):
                                        return derived
                        except Exception:
                            pass
                    return None
                
                semaphore = asyncio.Semaphore(10)
                async def process_url(url: str):
                    async with semaphore:
                        validated = await validate_derived_image(url)
                        if validated and url in url_to_offer_map:
                            for group_key, offer_idx in url_to_offer_map[url]:
                                grouped[group_key]["offers"][offer_idx]["image_url"] = validated
                
                await asyncio.gather(*[process_url(url) for url in remaining_urls])

        # Final enrichment: collect all images and update canonical products
        async def enrich_group_final(group: Dict[str, Any]) -> None:
            canonical = group["canonical_product"]
            image_set = set()

            # Collect all images from offers, filtering out Wegmans logos
            def is_wegmans_logo_image(image_url: Optional[str]) -> bool:
                """Check if image URL is a Wegmans logo/share image"""
                if not image_url:
                    return False
                image_lower = image_url.lower()
                return 'wegmans-og-share-img' in image_lower or '53100' in image_url

            for offer in group["offers"]:
                img_url = offer.get("image_url")
                if img_url and not is_wegmans_logo_image(img_url):
                    image_set.add(img_url)
                elif img_url:
                    logger.debug(f"🔄 Filtered out Wegmans logo in enrich_group_final: {img_url[:80]}...")

            # Update canonical images (filtered)
            canonical["images"] = list(image_set) if image_set else []
            if canonical["images"]:
                logger.debug(f"✅ Collected {len(canonical['images'])} images for canonical product: {canonical.get('name', 'Unknown')[:50]}")
            else:
                logger.debug(f"⚠️ No images collected for canonical product: {canonical.get('name', 'Unknown')[:50]} (offers: {len(group['offers'])})")

            # Backfill any remaining missing offer image_urls with primary image
            if canonical["images"]:
                primary = canonical["images"][0]
                for offer in group["offers"]:
                    if not offer.get("image_url") or is_wegmans_logo_image(offer.get("image_url")):
                        offer["image_url"] = primary

        # Final enrichment pass
        await asyncio.gather(*(enrich_group_final(g) for g in grouped.values()))

        # Optional: Enhance descriptions with AI if they're missing or too basic
        if ai_scraper.is_available() and refresh:
            logger.info("🤖 Enhancing product descriptions with AI")
            try:
                # Enhance descriptions for products with missing or short descriptions
                async def enhance_description_for_group(group: Dict[str, Any]) -> None:
                    canonical = group.get("canonical_product", {})
                    current_desc = canonical.get("description", "")
                    
                    # Enhance if description is missing, too short, or too basic
                    if not current_desc or len(current_desc) < 80 or "Fresh" in current_desc and len(current_desc) < 100:
                        enhanced = await ai_scraper.enhance_product_description(
                            canonical.get("name", ""),
                            canonical.get("brand"),
                            canonical.get("quantity"),
                            current_desc if current_desc else None
                        )
                        if enhanced:
                            canonical["description"] = enhanced
                            logger.debug(f"✅ Enhanced description for {canonical.get('name', 'Unknown')[:50]}")
                
                # Enhance descriptions concurrently (limit to avoid too many API calls)
                groups_to_enhance = [g for g in list(grouped.values())[:5] if not g.get("canonical_product", {}).get("description") or len(g.get("canonical_product", {}).get("description", "")) < 80]
                if groups_to_enhance:
                    await asyncio.gather(*(enhance_description_for_group(g) for g in groups_to_enhance))
                    
            except Exception as e:
                logger.warning(f"Description enhancement failed: {e}")

        # Optional: Enrich with AI scraper for missing prices (if available)
        if ai_scraper.is_available() and refresh:
            logger.info("🤖 Using AI scraper to enrich products with prices")
            try:
                # Collect all offers that need price enrichment
                offers_to_enrich = []
                for result in grouped.values():
                    for offer in result.get("offers", []):
                        if offer.get("product_url") and offer.get("price") is None:
                            offers_to_enrich.append(offer)
                
                if offers_to_enrich:
                    # Enrich offers with prices (limit to 10 for performance)
                    enriched_offers = await ai_scraper.enrich_products_with_prices(
                        offers_to_enrich[:10],  # Limit to 10 to control cost/time
                        max_concurrent=3
                    )
                    
                    # Update offers with enriched data
                    offer_map = {o.get("product_url"): o for o in enriched_offers}
                    for result in grouped.values():
                        canonical = result.get("canonical_product", {})
                        for offer in result.get("offers", []):
                            url = offer.get("product_url")
                            if url and url in offer_map:
                                enriched = offer_map[url]
                                if enriched.get("price") is not None:
                                    offer["price"] = enriched["price"]
                                    offer["currency"] = enriched.get("currency", "USD")
                                    if enriched.get("price_text"):
                                        offer["price_text"] = enriched["price_text"]
                                
                                # Enhance description if available and better
                                if enriched.get("description") and len(enriched.get("description", "")) > 50:
                                    # Use AI-generated description if it's more detailed
                                    if not canonical.get("description") or len(canonical.get("description", "")) < len(enriched.get("description", "")):
                                        canonical["description"] = enriched["description"]
                                
                                offer["source"].append("ai_scraper")
                    
                    logger.info(f"✅ Enriched {len(enriched_offers)} offers with AI scraper")
                    
            except Exception as e:
                logger.warning(f"AI scraper enrichment failed: {e}")

        # Fetch store locations for all retailers
        logger.info(f"🔍 Fetching store locations for {len(considered_store_ids)} retailers")
        store_locations_cache = {}
        
        async def fetch_store_locations(store_id: str):
            """Fetch store locations for a retailer"""
            try:
                store_name = to_store_name(store_id)
                stores = await exa_client.search_stores_in_zipcode(store_name, zipcode)
                if stores:
                    # Use the first store found (closest match)
                    store_locations_cache[store_id] = stores[0]
                    logger.debug(f"✅ Found store location for {store_name}: {stores[0].get('store_name', 'Unknown')}")
                else:
                    logger.debug(f"⚠️ No store location found for {store_name} near {zipcode}")
            except Exception as e:
                logger.warning(f"⚠️ Failed to fetch store location for {store_id}: {e}")
        
        # Fetch store locations concurrently
        await asyncio.gather(*[fetch_store_locations(sid) for sid in considered_store_ids], return_exceptions=True)
        
        # Get coordinates for the zipcode to use for store locations
        geocoding_service = get_geocoding_service()
        geo_city, geo_state, geo_lat, geo_lng = await geocoding_service.get_location_from_zipcode(zipcode)
        logger.info(f"📍 Geocoded {zipcode}: city={geo_city}, state={geo_state}, lat={geo_lat}, lng={geo_lng}")
        
        # Transform to enhanced format
        async def transform_to_enhanced_format(grouped_results: Dict[str, Any], stores_considered: List[str], query: str, zipcode: str, store_locations: Dict[str, Dict[str, Any]], stores_available: List[str] = None, zipcode_lat: float = None, zipcode_lng: float = None) -> Dict[str, Any]:
            """Transform grouped results to enhanced response format"""
            from datetime import datetime
            
            enhanced_results = []
            search_timestamp = datetime.utcnow().isoformat() + "Z"
            scraped_at = datetime.utcnow().isoformat() + "Z"
            
            for group in grouped_results.values():
                canonical = group.get("canonical_product", {})
                offers = group.get("offers", [])
                
                # Extract product images
                images = []
                for idx, img_url in enumerate(canonical.get("images", []) or []):
                    if img_url:
                        images.append({
                            "url": img_url,
                            "is_primary": idx == 0
                        })
                
                # Extract category path from description/name
                category_path = []
                if canonical.get("category"):
                    category_path = [canonical["category"]]
                elif "milk" in (canonical.get("name") or "").lower():
                    category_path = ["Dairy & Eggs", "Milk"]
                elif "egg" in (canonical.get("name") or "").lower():
                    category_path = ["Dairy & Eggs", "Eggs"]
                elif "bread" in (canonical.get("name") or "").lower():
                    category_path = ["Bakery", "Bread"]
                
                # Extract retailer SKU from product URL
                retailer_sku = None
                for offer in offers:
                    product_url = offer.get("product_url", "")
                    if "target.com" in product_url and "/A-" in product_url:
                        try:
                            retailer_sku = product_url.split("/A-")[1].split("/")[0]
                            break
                        except:
                            pass
                    elif "walmart.com" in product_url and "/ip/" in product_url:
                        try:
                            match = re.search(r'/ip/[^/]+/(\d+)', product_url)
                            if match:
                                retailer_sku = match.group(1)
                                break
                        except:
                            pass
                
                # Transform offers
                enhanced_offers = []
                for offer in offers:
                    store_id = offer.get("store_id", "")
                    store_name = offer.get("store_name", "")
                    
                    # Determine fulfillment options
                    fulfillment = []
                    if store_id in ["target", "walmart"]:
                        fulfillment = ["PICKUP", "DELIVERY"]
                    else:
                        fulfillment = ["IN_STORE"]
                    
                    # Determine prices first (needed for Wegmans availability check)
                    regular_price = None
                    sale_price = None
                    price = offer.get("price")
                    
                    # Determine availability
                    availability = offer.get("availability", "CHECK_STORE")
                    
                    # Handle standardized availability formats (from partner APIs)
                    if availability in ["IN_STOCK", "OUT_OF_STOCK", "LOW_STOCK", "CHECK_STORE"]:
                        # Already in correct format, use as-is
                        pass
                    elif availability and "stock" in availability.lower():
                        if "out" in availability.lower():
                            availability = "OUT_OF_STOCK"
                        elif "low" in availability.lower():
                            availability = "LOW_STOCK"
                        else:
                            availability = "IN_STOCK"
                    elif availability and availability.lower() == "in stock":
                        availability = "IN_STOCK"
                    elif store_id in ["kroger", "marianos"]:
                        # Kroger/Mariano's API provides accurate store-specific availability
                        # If we have availability from API, trust it (already handled above)
                        # Otherwise fall back to CHECK_STORE
                        if availability not in ["IN_STOCK", "OUT_OF_STOCK"]:
                            availability = "CHECK_STORE"
                    elif store_id == "wegmans":
                        # For Wegmans: If product has price and is store-filtered, assume IN_STOCK
                        # Wegmans shows products filtered by zipcode/store, so if it appears, it's available
                        if price:
                            availability = "IN_STOCK"
                        elif offer.get("product_url") and "wegmans.com/shop/product/" in offer.get("product_url", ""):
                            # If it's a valid Wegmans product URL, assume available (store-filtered)
                            availability = "IN_STOCK"
                        else:
                            availability = "CHECK_STORE"
                    elif store_id == "aldi":
                        # For ALDI: If product has price, assume IN_STOCK
                        # ALDI shows products with prices when available
                        if price:
                            availability = "IN_STOCK"
                        elif offer.get("product_url") and "aldi.us/product/" in offer.get("product_url", "") and "/products/" not in offer.get("product_url", ""):
                            # If it's a valid ALDI product URL (not category page), assume available
                            availability = "IN_STOCK"
                        else:
                            availability = "CHECK_STORE"
                    else:
                        availability = "CHECK_STORE"
                    
                    # Set regular_price from price
                    if price:
                        if isinstance(price, (int, float)):
                            regular_price = float(price)
                            # Assume no sale price for now
                    
                    # Get store location details from cache
                    store_location = store_locations.get(store_id, {})
                    
                    # Extract retailer_store_id from store location
                    retailer_store_id = None
                    if store_location:
                        # Try to get retailer_store_id from location data (this is the actual store ID)
                        retailer_store_id = store_location.get("retailer_store_id")
                        # If not found, try store_id (but this is usually the retailer name, not store ID)
                        if not retailer_store_id and store_location.get("store_id") and store_location.get("store_id") != store_id:
                            retailer_store_id = store_location.get("store_id")
                    
                    # Use store location data if available, otherwise fall back to offer data
                    store_address = store_location.get("address") or offer.get("address")
                    store_city = store_location.get("city") or offer.get("city")
                    store_state = store_location.get("state") or offer.get("state")
                    store_zipcode = store_location.get("zipcode") or offer.get("zipcode") or zipcode
                    
                    # Get full store name from location if available
                    # Avoid duplication: if store_location name contains the store_name, prefer store_name
                    location_store_name = store_location.get("store_name") or ""
                    if location_store_name and store_name and store_name.lower() in location_store_name.lower():
                        # Location name already contains store name (e.g., "Mariano's Mariano's"), use just store_name
                        full_store_name = store_name
                    else:
                        full_store_name = location_store_name or store_name
                    
                    # Create store info with coordinates
                    store_info = StoreInfoDetailed(
                        retailer=store_id,
                        retailer_store_id=retailer_store_id,
                        store_name=full_store_name,
                        address=store_address,
                        city=store_city,
                        state=store_state,
                        zipcode=store_zipcode,
                        latitude=zipcode_lat,
                        longitude=zipcode_lng
                    )
                    
                    enhanced_offer_dict = {
                        "store": store_info.model_dump(exclude_none=True),
                        "product_url": offer.get("product_url", ""),
                        "fulfillment": fulfillment,
                        "availability": availability,
                        "inventory_count": None,
                        "regular_price": regular_price,
                        "sale_price": sale_price,
                        "price_updated_at": scraped_at if price else None,
                        "promo_badge": None
                    }
                    enhanced_offers.append(enhanced_offer_dict)
                
                # Create enhanced product result
                enhanced_product_dict = {
                    "upc": None,
                    "retailer_sku": retailer_sku,
                    "name": canonical.get("name", "Unknown Product"),
                    "brand": canonical.get("brand"),
                    "category_path": category_path,
                    "description": canonical.get("description"),
                    "size": canonical.get("quantity") or canonical.get("size"),
                    "package_quantity": canonical.get("quantity") or canonical.get("size"),
                    "images": images,
                    "nutrition": None,
                    "offers": enhanced_offers,
                    "source": "scraper_v2",
                    "scraped_at": scraped_at
                }
                enhanced_results.append(enhanced_product_dict)
            
            meta = {
                "api_version": "2.1.0",
                "cache": {"hit": False},
                "stores_searched": stores_considered,
            }
            
            if stores_available:
                meta["stores_available"] = stores_available
            
            return {
                "query": query,
                "zipcode": zipcode,
                "search_timestamp": search_timestamp,
                "results": enhanced_results,
                "stores_considered": stores_considered,
                "meta": meta
            }
        
        # Create both formats
        standard_response = {
            "query": query,
            "zipcode": zipcode,
            "stores_considered": considered_store_ids,
            "results": list(grouped.values()),
            "source": "exa_structured_aggregate"
        }
        
        enhanced_response = await transform_to_enhanced_format(grouped, considered_store_ids, query, zipcode, store_locations_cache, stores_available=all_available_store_ids, zipcode_lat=geo_lat, zipcode_lng=geo_lng)

        # Apply limit to results
        if limit and len(enhanced_response.get("results", [])) > limit:
            enhanced_response["results"] = enhanced_response["results"][:limit]

        # Cache the results (store enhanced format for future use)
        logger.info(f"cache_miss aggregate zip={zipcode} q='{query}' -> setting cache")
        if cache:
            await cache.set_json(cache_key, enhanced_response, ttl_seconds=60 * 15)
        
        # Return enhanced format
        return enhanced_response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Aggregate product search failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port, reload=True)
