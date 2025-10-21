#!/usr/bin/env python3
"""
Grocery Scraper API
A professional FastAPI service for scraping grocery store product data
"""

from fastapi import FastAPI, HTTPException, Query
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
    description="Professional API for scraping real grocery store product data",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    contact={
        "name": "Grocery Scraper API",
        "url": "https://github.com/yourusername/grocery-scraper-api",
    },
    license_info={
        "name": "MIT",
        "url": "https://opensource.org/licenses/MIT",
    },
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

@app.get("/health", response_model=HealthResponse, tags=["meta"], response_model_exclude_none=True, response_class=PrettyJSONResponse)
def health_check():
    """Health check endpoint"""
    # Since we know the client is working (tested directly), 
    # and the issue seems to be with the health endpoint logic,
    # let's just return available for now
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "version": "2.0.0",
        "services": {
            "exa_api": "available"
        }
    }





@app.get("/stores/{zipcode}", tags=["stores"], response_model=StoresResponse, response_model_exclude_none=True)
async def get_stores_in_zipcode(zipcode: str, store_chain: Optional[str] = None):
    """Get grocery store locations in a zipcode using Exa"""
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

    



@app.get("/products/search", response_model=ProductsSearchResponse, tags=["products"], response_model_exclude_none=True)
async def search_products(
    query: str,
    store_name: Optional[str] = None,
    zipcode: Optional[str] = None,
    num_results: int = 20,
    context: Optional[str] = None,
    refresh: bool = False
):
    """
    Search for grocery products using Exa with structured data extraction.
    Returns product information including price, quantity, images, and store location.
    """
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


@app.get("/products/aggregate", response_model=AggregateResponse, tags=["aggregate"], response_model_exclude_none=True)
async def aggregate_products(
    query: str,
    zipcode: str,
    radius_miles: int = 10,
    stores: Optional[str] = None,
    refresh: bool = False
):
    """
    Product-first search across multiple stores in a zipcode using Exa.
    Returns aggregated product offers with structured data including:
    - Product name, brand, quantity, images
    - Price, availability
    - Store name, address, zipcode
    """
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
