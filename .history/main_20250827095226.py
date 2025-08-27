#!/usr/bin/env python3
"""
Grocery Scraper API
A professional FastAPI service for scraping grocery store product data
"""

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from typing import List, Optional
import asyncio
import os
from datetime import datetime
import logging

# Import our scraper modules
from scraper.models import StoreInfo
from scraper.sonar_client import SonarClient
from scraper.location_service import LocationService
from scraper.cache import Cache, stores_key, products_key
from scraper.serper_client import SerperClient

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
    redoc_url="/redoc"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure for your domain in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize services
sonar_client = SonarClient()
location_service = LocationService()
cache = Cache()

@app.on_event("startup")
async def startup_event():
    """Initialize the API on startup"""
    logger.info("🚀 Starting Grocery Scraper API with Sonar Integration...")
    logger.info(f"🔍 Sonar available: {sonar_client.is_available()}")

@app.get("/")
async def root():
    """Root endpoint with API information"""
    return {
        "name": "Grocery Scraper API",
        "version": "1.0.0",
        "description": "AI-powered grocery product discovery with real URLs and images",
        "endpoints": {
            "health": "/health",
            "stores": "/sonar/stores/search",
            "products": "/sonar/products/search"
        },
        "features": [
            "AI-powered product search",
            "Real product URLs and images",
            "Store discovery",
            "Smart product matching"
        ]
    }

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "version": "1.0.0",
        "services": {
            "perplexity_sonar": "available" if sonar_client.is_available() else "unavailable",
            "serper_dev": "available" if os.getenv("SERPER_API_KEY") else "unavailable"
        }
    }





@app.get("/sonar/test/{zipcode}")
async def test_sonar(zipcode: str):
    """Test Perplexity Sonar store discovery for a zipcode"""
    try:
        stores = await sonar_client.search_stores(zipcode)
        return {
            "zipcode": zipcode,
            "stores_found": len(stores),
            "stores": [
                {
                    "store_id": store.store_id,
                    "store_name": store.store_name,
                    "address": store.address,
                    "services": store.services,
                    "status": store.status
                }
                for store in stores
            ],
            "sonar_available": sonar_client.is_available()
        }
    except Exception as e:
        return {
            "zipcode": zipcode,
            "error": str(e),
            "sonar_available": sonar_client.is_available()
        }

@app.get("/sonar/stores/{zipcode}")
async def get_sonar_stores(zipcode: str, chains: Optional[str] = None):
    """Get stores discovered via Perplexity Sonar for a zipcode"""
    try:
        # Try cache first
        key = stores_key(zipcode)
        cached = await cache.get_json(key)
        if cached:
            logger.info(f"cache_hit stores zip={zipcode}")
            # Optional filter by chains (comma-separated canonical IDs)
            if chains:
                requested = {c.strip().lower() for c in chains.split(',') if c.strip()}
                filtered = [s for s in cached.get("stores", []) if s.get("store_id") in requested]
                return {**cached, "stores": filtered, "stores_found": len(filtered), "cache": {"hit": True}}
            return {**cached, "cache": {"hit": True}}

        if not sonar_client.is_available():
            raise HTTPException(
                status_code=503,
                detail="Sonar client not available - check API key configuration"
            )
        
        stores = await sonar_client.search_stores(zipcode)
        response_payload = {
            "zipcode": zipcode,
            "stores_found": len(stores),
            "search_timestamp": datetime.now().isoformat(),
            "stores": [
                {
                    "store_id": store.store_id,
                    "store_name": store.store_name,
                    "address": store.address,
                    "services": store.services,
                    "status": store.status,
                    "zipcode": store.zipcode,
                    "website": getattr(store, 'website', None),
                    "location": {
                        "zipcode": store.zipcode,
                        "city": extract_city_from_address(store.address) if store.address else None,
                        "state": extract_state_from_address(store.address) if store.address else None
                    }
                }
                for store in stores
            ],
            "source": "perplexity_sonar",
            "api_version": "1.0.0"
        }
        # Cache the unfiltered payload
        logger.info(f"cache_miss stores zip={zipcode} -> setting cache")
        await cache.set_json(key, response_payload, ttl_seconds=60*60*24)
        # Apply filter on the response if requested
        if chains:
            requested = {c.strip().lower() for c in chains.split(',') if c.strip()}
            filtered = [s for s in response_payload.get("stores", []) if s.get("store_id") in requested]
            return {**response_payload, "stores": filtered, "stores_found": len(filtered), "cache": {"hit": False}}
        return {**response_payload, "cache": {"hit": False}}
    except Exception as e:
        logger.error(f"❌ Sonar store search failed: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Sonar search failed: {str(e)}"
        )
    
    # Cache set outside try to avoid swallowing HTTPException
    finally:
        try:
            if 'stores' in locals():
                payload = {
                    "zipcode": zipcode,
                    "stores_found": len(stores),
                    "search_timestamp": datetime.now().isoformat(),
                    "stores": [
                        {
                            "store_id": store.store_id,
                            "store_name": store.store_name,
                            "address": store.address,
                            "services": store.services,
                            "status": store.status,
                            "zipcode": store.zipcode,
                            "website": getattr(store, 'website', None),
                            "location": {
                                "zipcode": store.zipcode,
                                "city": extract_city_from_address(store.address) if store.address else None,
                                "state": extract_state_from_address(store.address) if store.address else None
                            }
                        }
                        for store in stores
                    ],
                    "source": "perplexity_sonar",
                    "api_version": "1.0.0"
                }
                await cache.set_json(stores_key(zipcode), payload, ttl_seconds=60*60*24)
        except Exception:
            pass
    


@app.get("/sonar/store/{store_name}/details")
async def get_sonar_store_details(store_name: str, location: Optional[str] = None, zipcode: Optional[str] = None):
    """Get detailed information about a specific store via Sonar"""
    try:
        if not sonar_client.is_available():
            raise HTTPException(
                status_code=503,
                detail="Sonar client not available - check API key configuration"
            )
        # Prefer zipcode if provided
        resolved_location = location or zipcode or ""
        if not resolved_location:
            raise HTTPException(status_code=400, detail="Provide either location or zipcode")

        details = await sonar_client.get_store_details(store_name, resolved_location)
        return {
            "store_name": store_name,
            "location": resolved_location,
            "details": details,
            "source": "perplexity_sonar"
        }
    except Exception as e:
        logger.error(f"❌ Sonar store details failed: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Store details search failed: {str(e)}"
        )

@app.get("/sonar/products/search")
async def search_sonar_products(query: str, store_name: str, location: Optional[str] = None, zipcode: Optional[str] = None, enhance: bool = False):
    """Search for products at a specific store using Sonar"""
    try:
        if not sonar_client.is_available():
            raise HTTPException(
                status_code=503,
                detail="Sonar client not available - check API key configuration"
            )
        # Prefer zipcode if provided
        resolved_location = location or zipcode or ""
        if not resolved_location:
            raise HTTPException(status_code=400, detail="Provide either location or zipcode")

        products = await sonar_client.search_products(query, store_name, resolved_location, enhance)
        return {
            "query": query,
            "store_name": store_name,
            "location": resolved_location,
            "products_found": len(products),
            "search_timestamp": datetime.now().isoformat(),
            "products": [
                {
                    "name": product.get("name", "Unknown Product"),
                    "price": product.get("price"),
                    "availability": product.get("availability", "Unknown"),
                    "category": product.get("category"),
                    "brand": product.get("brand"),
                    "size": product.get("size"),
                    "description": product.get("description"),
                    "image_url": product.get("image_url"),
                    "product_url": product.get("product_url"),
                    "nutritional_info": product.get("nutritional_info"),
                    "ingredients": product.get("ingredients"),
                    "allergens": product.get("allergens"),
                    "online_available": product.get("online_available"),
                    "in_store_only": product.get("in_store_only"),
                    "reviews_count": product.get("reviews_count"),
                    "rating": product.get("rating")
                }
                for product in products
            ],
            "source": "perplexity_sonar",
            "api_version": "1.0.0"
        }
    except Exception as e:
        logger.error(f"❌ Sonar product search failed: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Product search failed: {str(e)}"
        )

@app.get("/sonar/status")
async def get_sonar_status():
    """Get Sonar client status and configuration"""
    return {
        "available": sonar_client.is_available(),
        "api_key_configured": sonar_client.api_key is not None,
        "cache_enabled": len(sonar_client._cache) > 0,
        "cache_size": len(sonar_client._cache),
        "base_url": sonar_client.base_url
    }

@app.get("/products/aggregate")
async def aggregate_products(
    query: str,
    zipcode: str,
    radius_miles: int = 10,
    stores: Optional[str] = None,
    enhance: bool = False
):
    """Product-first search across multiple stores in a zipcode with caching."""
    try:
        # Validate zipcode
        import re
        if not re.match(r"^\d{5}$", zipcode):
            raise HTTPException(status_code=400, detail="Invalid zipcode format")

        # Determine store set
        user_store_ids = []
        if stores:
            user_store_ids = [s.strip().lower() for s in stores.split(",") if s.strip()]

        # Resolve nearby stores (filtered) unless user explicitly specifies stores
        nearby = await location_service.get_nearby_stores(zipcode)
        considered_store_ids: list[str] = []
        if user_store_ids:
            # Prefer user-provided stores regardless of discovery coverage
            considered_store_ids = user_store_ids[:10]
        else:
            considered_store_ids = [s.store_id for s in nearby][:10]

        # Cache lookup for aggregated products
        key = products_key(zipcode, query, considered_store_ids, enhance)
        cached = await cache.get_json(key)
        if cached:
            logger.info(f"cache_hit aggregate zip={zipcode} q='{query}'")
            # Near-stale refresh: if TTL < 20% of full, refresh in background
            ttl = await cache.ttl_seconds(key)
            try:
                is_near_stale = isinstance(ttl, int) and ttl > 0 and ttl < (60 * 60 * 4 * 0.2)
            except Exception:
                is_near_stale = False
            if is_near_stale:
                async def _refresh():
                    try:
                        # Trigger a background refresh by re-running aggregation path
                        pass  # Placeholder for Phase 2 background task system
                    except Exception:
                        pass
                # Fire-and-forget (no background task runner here)
                # await _refresh()  # intentionally not awaited
            return {**cached, "cache": {"hit": True, "near_stale": bool(is_near_stale)}}

        # Fan out per store with concurrency limits and per-store timeout
        semaphore = asyncio.Semaphore(10)

        # Map canonical store_id to a human-friendly store name for Sonar/Serper prompts
        def to_store_name(store_id: str) -> str:
            mapping = {
                "whole_foods": "Whole Foods Market",
                "sams_club": "Sam's Club",
                "trader_joes": "Trader Joe's",
                "ahold_delhaize": "Stop & Shop",
            }
            if store_id in mapping:
                return mapping[store_id]
            return store_id.replace("_", " ").title()

        async def fetch_store(store_id: str):
            async with semaphore:
                return await asyncio.wait_for(
                    sonar_client.search_products(query, to_store_name(store_id), zipcode, enhance),
                    timeout=20
                )

        tasks = [fetch_store(sid) for sid in considered_store_ids]
        raw_results = await asyncio.gather(*tasks, return_exceptions=True)

        # Normalize into offers
        all_offers = []
        serper = SerperClient()
        for idx, res in enumerate(raw_results):
            if isinstance(res, Exception):
                logger.warning(f"aggregate_store_error store={considered_store_ids[idx]} err={res}")
                continue
            store_id = considered_store_ids[idx]
            store_name = to_store_name(store_id)
            products = res or []
            # Serper fallback if Sonar returned nothing
            if not products and serper.is_available():
                try:
                    serper_products = await serper.search_shopping_products(query, store_name, "United States")
                    for sp in serper_products:
                        all_offers.append({
                            "store_id": store_id,
                            "store_name": store_name,
                            "name": sp.get("name"),
                            "brand": None,
                            "size": None,
                            "price": sp.get("price"),
                            "availability": sp.get("availability"),
                            "image_url": sp.get("image_url"),
                            "product_url": sp.get("product_url"),
                            "source": ["serper_shopping"]
                        })
                except Exception as e:
                    logger.warning(f"serper_fallback_error store={store_id} err={e}")
                continue
            for p in products:
                all_offers.append({
                    "store_id": store_id,
                    "store_name": store_name,
                    "name": p.get("name"),
                    "brand": p.get("brand"),
                    "size": p.get("size"),
                    "price": p.get("price"),
                    "availability": p.get("availability"),
                    "image_url": p.get("image_url"),
                    "product_url": p.get("product_url"),
                    "source": ["perplexity_sonar"]
                })

        # Improved normalization and aggregation by (brand, normalized_name, normalized_size)
        def norm_text(s: Optional[str]) -> str:
            return (s or "").lower().strip()

        def norm_name(name: Optional[str]) -> str:
            n = norm_text(name)
            # remove common stop words and punctuation dashes
            for token in ["brand", "original", "the"]:
                n = n.replace(f" {token} ", " ")
            n = n.replace("-", " ")
            n = " ".join(n.split())
            return n

        def norm_size(size: Optional[str]) -> str:
            s = norm_text(size)
            s = s.replace("fluid ounces", "fl oz").replace("fluid ounce", "fl oz").replace("ounces", "oz").replace("ounce", "oz")
            s = s.replace("fl. oz", "fl oz").replace("fl-oz", "fl oz")
            s = s.replace("packs", "pack").replace(" ct", " count").replace("ct", "count")
            s = " ".join(s.split())
            return s

        grouped = {}
        for o in all_offers:
            key_parts = (norm_text(o.get("brand")), norm_name(o.get("name")), norm_size(o.get("size")))
            gkey = "|".join(key_parts)
            if gkey not in grouped:
                grouped[gkey] = {
                    "canonical_product": {
                        "name": o.get("name"),
                        "brand": o.get("brand"),
                        "size": o.get("size"),
                        "images": [o.get("image_url")] if o.get("image_url") else []
                    },
                    "offers": []
                }
            grouped[gkey]["offers"].append({
                "store_id": o["store_id"],
                "store_name": o["store_name"],
                "price": o.get("price"),
                "availability": o.get("availability"),
                "product_url": o.get("product_url"),
                "source": o.get("source", [])
            })

        response = {
            "query": query,
            "zipcode": zipcode,
            "stores_considered": considered_store_ids,
            "results": list(grouped.values()),
            "source": "aggregate(sonar)"
        }

        logger.info(f"cache_miss aggregate zip={zipcode} q='{query}' -> setting cache")
        await cache.set_json(key, response, ttl_seconds=60 * 60 * 4)
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
