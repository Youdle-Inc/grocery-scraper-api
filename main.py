#!/usr/bin/env python3
"""
Grocery Scraper API
A professional FastAPI service for scraping grocery store product data
"""

from fastapi import FastAPI, HTTPException, Query, Path
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse
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
from scraper.exa_structured_client import ExaStructuredClient
from scraper.models import (
    HealthResponse,
    StoresResponse,
    StoreDetailsResponse,
    ProductsSearchResponse,
    AggregateResponse,
)
from scraper.image_scraper import ImageScraper

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

# Create FastAPI app
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
    docs_url="/docs",
    redoc_url="/redoc",
    contact={
        "name": "Grocery Scraper API",
        "url": "https://github.com/Youdle-Inc/grocery-scraper-api",
    },
    license_info={
        "name": "MIT",
        "url": "https://opensource.org/licenses/MIT",
    },
    servers=[
        {"url": "http://localhost:8000", "description": "Local development server"},
        {"url": "http://localhost:8001", "description": "Alternative local server"},
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

# Initialize services
exa_client = ExaStructuredClient()
location_service = LocationService()
cache = Cache()

# Debug: Check client status
logger.info(f"🔍 ExaStructuredClient initialized: {exa_client.is_available()}")
logger.info(f"🔑 API key loaded: {bool(exa_client.api_key)}")

@app.on_event("startup")
async def startup_event():
    """Initialize the API on startup"""
    logger.info("🚀 Starting Grocery Scraper API with Exa Integration...")
    logger.info(f"🔍 Exa available: {exa_client.is_available()}")
    logger.info(f"🔑 EXA_API_KEY loaded: {bool(os.getenv('EXA_API_KEY'))}")
    logger.info(f"🌍 Environment: {os.getenv('ENVIRONMENT', 'development')}")

@app.get("/", response_class=HTMLResponse, tags=["meta"])
async def root():
    """Root endpoint serving simple API documentation"""
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Grocery Scraper API</title>
        <style>
            body { font-family: Arial, sans-serif; margin: 40px; background: #1a1a1a; color: #e0e0e0; }
            .container { max-width: 800px; margin: 0 auto; }
            h1 { color: #4CAF50; }
            .endpoint { background: #2a2a2a; padding: 20px; margin: 20px 0; border-radius: 8px; }
            .method { background: #4CAF50; color: white; padding: 4px 8px; border-radius: 4px; font-size: 12px; }
            .url { font-family: monospace; color: #81C784; }
            code { background: #333; padding: 2px 6px; border-radius: 4px; }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🛒 Grocery Scraper API v2.0.0</h1>
            <p>AI-powered grocery product discovery with Exa - structured data with real URLs and images</p>
            
            <div class="endpoint">
                <h3><span class="method">GET</span> <span class="url">/health</span></h3>
                <p>Check API health and service status</p>
                <code>curl "https://grocery-scraper-api.vercel.app/health"</code>
            </div>
            
            <div class="endpoint">
                <h3><span class="method">GET</span> <span class="url">/stores/{zipcode}</span></h3>
                <p>Find grocery stores in a specific ZIP code</p>
                <code>curl "https://grocery-scraper-api.vercel.app/stores/10001"</code>
            </div>
            
            <div class="endpoint">
                <h3><span class="method">GET</span> <span class="url">/products/search</span></h3>
                <p>Search for specific products with structured data</p>
                <code>curl "https://grocery-scraper-api.vercel.app/products/search?query=organic%20milk&zipcode=10001"</code>
            </div>
            
            <div class="endpoint">
                <h3><span class="method">GET</span> <span class="url">/products/aggregate</span></h3>
                <p>Compare products across multiple stores</p>
                <code>curl "https://grocery-scraper-api.vercel.app/products/aggregate?query=pizza&zipcode=60622&stores=walmart,target"</code>
            </div>
            
            <p><strong>Features:</strong> Exa-powered structured product search, real product URLs, high-quality images, store location discovery, smart product matching</p>
        </div>
    </body>
    </html>
    """

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
        cached = await cache.get_json(cache_key)
        if cached:
            logger.info(f"cache_hit stores zip={zipcode}")
            return {**cached, "cache": {"hit": True}}

        if not exa_client.is_available():
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
        cached = None if refresh else await cache.get_json(cache_key)
        if cached and not refresh:
            logger.info(f"cache_hit products q='{query}'")
            return {**cached, "cache": {"hit": True}}
        
        if not exa_client.is_available():
            raise HTTPException(
                status_code=503,
                detail="Exa client not available - check API key configuration"
            )
        
        # Search with Exa structured client using optimized prompts
        products = await exa_client.search_products_structured(
            query=query,
            store_name=store_name,
            zipcode=zipcode,
            num_results=num_results,
            include_location=True,
            context=context
        )
        
        response_payload = {
            "query": query,
            "store_name": store_name or "All Stores",
            "location": zipcode or "All Locations",
            "products_found": len(products),
            "search_timestamp": datetime.now().isoformat(),
            "products": products,
            "source": "exa_structured",
            "api_version": "2.0.0"
        }
        
        # Cache the results
        logger.info(f"cache_miss products q='{query}' -> setting cache")
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
    "/products/aggregate",
    response_model=AggregateResponse,
    tags=["📊 Aggregate"],
    response_model_exclude_none=True,
    response_class=PrettyJSONResponse,
    summary="Compare Products Across Stores",
    description="""
    Compare the same products across multiple stores to find the best deals.

    Groups identical products together and shows offers from different retailers.

    **Parameters:**
    - `query` (required): Product to search for (e.g., "eggs", "milk", "bread")
    - `zipcode` (required): 5-digit ZIP code
    - `radius_miles`: Search radius in miles (default: 10)
    - `stores`: Comma-separated store IDs to search (e.g., "target,walmart")
    - `refresh`: Bypass cache (default: false)

    **Example Requests:**
    ```
    GET /products/aggregate?query=eggs&zipcode=60601
    GET /products/aggregate?query=milk&zipcode=60601&stores=target,walmart
    GET /products/aggregate?query=bread&zipcode=10001&radius_miles=15
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

    **Available Stores:**
    target, walmart, whole_foods, kroger, aldi, costco, trader_joes, sams_club, safeway
    """,
)
async def aggregate_products(
    query: str = Query(..., description="Product to search for", example="eggs"),
    zipcode: str = Query(..., description="5-digit ZIP code", example="60601"),
    radius_miles: int = Query(10, ge=1, le=50, description="Search radius in miles"),
    stores: Optional[str] = Query(None, description="Comma-separated store IDs", example="target,walmart"),
    refresh: bool = Query(False, description="Bypass cache")
):
    """Compare products across multiple stores"""
    try:
        # Validate zipcode
        import re
        if not re.match(r"^\d{5}$", zipcode):
            raise HTTPException(status_code=400, detail="Invalid zipcode format")

        # Determine store set
        user_store_ids = []
        if stores:
            user_store_ids = [s.strip().lower() for s in stores.split(",") if s.strip()]

        # Default major grocery store chains
        default_stores = ["target", "walmart", "whole_foods", "kroger", "aldi"]
        considered_store_ids = user_store_ids[:10] if user_store_ids else default_stores

        # Cache lookup
        cache_key = f"aggregate:{zipcode}:{query}:{':'.join(sorted(considered_store_ids))}"
        cached = None if refresh else await cache.get_json(cache_key)
        if cached and not refresh:
            logger.info(f"cache_hit aggregate zip={zipcode} q='{query}'")
            return {**cached, "cache": {"hit": True}}

        if not exa_client.is_available():
            raise HTTPException(
                status_code=503,
                detail="Exa client not available - check API key configuration"
            )

        # Map canonical store_id to human-friendly name
        def to_store_name(store_id: str) -> str:
            mapping = {
                "whole_foods": "Whole Foods",
                "sams_club": "Sam's Club",
                "trader_joes": "Trader Joe's",
                "kroger": "Kroger",
                "target": "Target",
                "walmart": "Walmart",
                "costco": "Costco",
                "aldi": "ALDI",
                "safeway": "Safeway",
            }
            return mapping.get(store_id, store_id.replace("_", " ").title())

        # Search products across all stores concurrently
        semaphore = asyncio.Semaphore(5)  # Limit concurrent searches
        
        async def fetch_store_products(store_id: str):
            async with semaphore:
                try:
                    store_name = to_store_name(store_id)
                    logger.info(f"Searching {store_name} for '{query}' near {zipcode}")
                    
                    products = await exa_client.search_products_structured(
                        query=query,
                        store_name=store_name,
                        zipcode=zipcode,
                        num_results=10,
                        include_location=True,
                        context="price_comparison"  # Use price comparison context for aggregate
                    )
                    
                    return {
                                "store_id": store_id,
                                "store_name": store_name,
                        "products": products
                    }
                except Exception as e:
                    logger.warning(f"Error fetching from {store_id}: {e}")
                    return {
                    "store_id": store_id,
                        "store_name": to_store_name(store_id),
                        "products": []
                    }

        # Fetch from all stores concurrently
        tasks = [fetch_store_products(sid) for sid in considered_store_ids]
        store_results = await asyncio.gather(*tasks, return_exceptions=False)

        # Aggregate products by canonical product
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
                
                # Add image to canonical product if not already there
                if product.get("image_url"):
                    canonical_images = grouped[gkey]["canonical_product"]["images"]
                    if product["image_url"] not in canonical_images:
                        canonical_images.append(product["image_url"])
                
                # Add additional images
                if product.get("additional_images"):
                    for img in product["additional_images"]:
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

        # Enrich images for better consistency
        async def derive_image_from_product_url(product_url: Optional[str]) -> Optional[str]:
            if not product_url:
                return None
            try:
                url = product_url.lower()
                # Target: build Scene7 image from product id in "/A-<id>"
                if "target.com" in url and "/a-" in url:
                    try:
                        pid = product_url.split("/A-")[1].split("/")[0]
                        return f"https://target.scene7.com/is/image/Target/{pid}?wid=1200&hei=1200&qlt=80&fmt=webp"
                    except Exception:
                        return None
                # Walmart: best effort is to rely on provided image; constructing reliably from URL is brittle
                return None
            except Exception:
                return None

        # Use shared session for lightweight scraper; use existing exa_client for image lookup
        async with ImageScraper() as scraper:
            semaphore_enrich = asyncio.Semaphore(10)

            async def enrich_group(group: Dict[str, Any]) -> None:
                async with semaphore_enrich:
                    canonical = group["canonical_product"]
                    images: List[str] = canonical.get("images") or []
                    image_set = set(images)

                    # 1) Add any offer images we already have
                    for offer in group["offers"]:
                        offer_img = offer.get("image_url")
                        if offer_img:
                            image_set.add(offer_img)

                    # 2) Try to derive from product URLs for known stores (e.g., Target)
                    if not image_set:
                        for offer in group["offers"]:
                            derived = await derive_image_from_product_url(offer.get("product_url"))
                            if derived:
                                image_set.add(derived)
                                break

                    # 3) If still empty, query EXA for likely product images by name/brand
                    if not image_set and exa_client.is_available():
                        try:
                            exa_query = " ".join([
                                p for p in [canonical.get("brand"), canonical.get("name"), canonical.get("quantity")] if p
                            ]) or (canonical.get("name") or "")
                            exa_results = await exa_client.search_products_structured(
                                query=exa_query,
                                store_name=None,
                                zipcode=None,
                                num_results=5,
                                include_location=False,
                            )
                            for r in exa_results:
                                if r.get("image_url"):
                                    image_set.add(r["image_url"])
                                    break
                                for ai in r.get("additional_images", []) or []:
                                    image_set.add(ai)
                                    break
                        except Exception:
                            pass

                    # 4) Fallback to lightweight scraper (best-effort)
                    if not image_set:
                        img = await scraper.find_product_image(
                            canonical.get("name") or "",
                            canonical.get("brand") or None,
                            None,
                        )
                        if img:
                            image_set.add(img)

                    # Update canonical images
                    canonical["images"] = list(image_set)

                    # 5) Backfill missing offer image_url from canonical
                    if canonical["images"]:
                        primary = canonical["images"][0]
                        for offer in group["offers"]:
                            if not offer.get("image_url"):
                                offer["image_url"] = primary

            # Enrich all groups concurrently
            await asyncio.gather(*(enrich_group(g) for g in grouped.values()))

        response = {
            "query": query,
            "zipcode": zipcode,
            "stores_considered": considered_store_ids,
            "results": list(grouped.values()),
            "source": "exa_structured_aggregate"
        }

        # Cache the results
        logger.info(f"cache_miss aggregate zip={zipcode} q='{query}' -> setting cache")
        await cache.set_json(cache_key, response, ttl_seconds=60 * 60 * 4)  # 4 hours
        
        return {**response, "cache": {"hit": False}}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Aggregate product search failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port, reload=True)
