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
            # Optional filter by chains (comma-separated canonical IDs)
            if chains:
                requested = {c.strip().lower() for c in chains.split(',') if c.strip()}
                filtered = [s for s in cached.get("stores", []) if s.get("store_id") in requested]
                return {**cached, "stores": filtered, "stores_found": len(filtered)}
            return cached

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
        await cache.set_json(key, response_payload, ttl_seconds=60*60*24)
        # Apply filter on the response if requested
        if chains:
            requested = {c.strip().lower() for c in chains.split(',') if c.strip()}
            filtered = [s for s in response_payload.get("stores", []) if s.get("store_id") in requested]
            return {**response_payload, "stores": filtered, "stores_found": len(filtered)}
        return response_payload
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

        # Resolve nearby stores (filtered)
        nearby = await location_service.get_nearby_stores(zipcode)
        if user_store_ids:
            nearby = [s for s in nearby if s.store_id in user_store_ids]

        considered_store_ids = [s.store_id for s in nearby][:10]

        # Cache lookup for aggregated products
        key = products_key(zipcode, query, considered_store_ids, enhance)
        cached = await cache.get_json(key)
        if cached:
            return cached

        # Fan out per store
        async def fetch_store(store_id: str, store_name: str):
            products = await sonar_client.search_products(query, store_name, zipcode, enhance)
            return store_id, store_name, products

        tasks = [
            fetch_store(s.store_id, s.store_name)
            for s in nearby[:10]
        ]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Normalize into offers
        all_offers = []
        for res in results:
            if isinstance(res, Exception):
                continue
            store_id, store_name, products = res
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

        # Simple aggregation by (brand, name, size)
        def norm(s: Optional[str]) -> str:
            return (s or "").strip().lower()

        grouped = {}
        for o in all_offers:
            key_parts = (norm(o.get("brand")), norm(o.get("name")), norm(o.get("size")))
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

        await cache.set_json(key, response, ttl_seconds=60 * 60 * 4)
        return response
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Aggregate product search failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port, reload=True)
