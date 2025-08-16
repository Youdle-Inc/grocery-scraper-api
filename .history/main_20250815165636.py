#!/usr/bin/env python3
"""
Grocery Scraper API
A professional FastAPI service for scraping grocery store product data
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
import asyncio
import os
from datetime import datetime
import logging

# Import our scraper modules
from scraper.models import StoreInfo
from scraper.sonar_client import SonarClient

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

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

# Initialize scrapers
scraper = GroceryScraper()
enhanced_scraper = EnhancedScraper()

@app.on_event("startup")
async def startup_event():
    """Initialize the scraper on startup"""
    logger.info("🚀 Starting Grocery Scraper API...")
    logger.info(f"🏪 Supported stores: {list(SUPPORTED_STORES.keys())}")

@app.get("/")
async def root():
    """Root endpoint with API information"""
    return {
        "name": "Grocery Scraper API",
        "version": "1.0.0",
        "description": "Professional API for scraping real grocery store product data",
        "docs": "/docs",
        "supported_stores": len(SUPPORTED_STORES),
        "working_stores": ["gianteagle", "wegmans", "aldi"],
        "endpoints": {
            "scrape": "/scrape",
            "stores": "/stores",
            "health": "/health",
            "test": "/test/{store}",
            "search_location": "/search/location",
            "coverage": "/coverage",
            "suggest": "/suggest",
            "synonyms": "/synonyms/{query}",
            "services": "/services/{store_id}",
            "sonar": {
                "test": "/sonar/test/{zipcode}",
                "stores": "/sonar/stores/{zipcode}",
                "store_details": "/sonar/store/{store_name}/details",
                "product_search": "/sonar/products/search",
                "status": "/sonar/status"
            }
        }
    }

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    scraper_ready = scraper.is_ready()
    return {
        "status": "healthy" if scraper_ready else "degraded",
        "timestamp": datetime.now(),
        "scraper_ready": scraper_ready,
        "selenium_available": scraper.selenium_available(),
        "supported_stores": len(SUPPORTED_STORES)
    }

@app.get("/stores", response_model=List[StoreInfo])
async def get_supported_stores():
    """Get list of supported stores"""
    return [
        StoreInfo(
            store_id=store_id,
            store_name=info["name"],
            supported=True,
            status=info["status"],
            description=info["description"]
        )
        for store_id, info in SUPPORTED_STORES.items()
    ]

@app.post("/scrape", response_model=ScrapeResponse)
async def scrape_products(request: ScrapeRequest):
    """
    Scrape products from a grocery store
    
    - **query**: Search term (e.g., "milk", "bread", "eggs")
    - **store**: Store ID (use /stores to see supported stores)
    - **zipcode**: ZIP code for store location
    """
    
    # Validate store
    if request.store not in SUPPORTED_STORES:
        raise HTTPException(
            status_code=400,
            detail=f"Store '{request.store}' not supported. Use /stores to see supported stores."
        )
    
    # Check scraper readiness
    if not scraper.is_ready():
        raise HTTPException(
            status_code=503,
            detail="Scraper not ready. Please check system dependencies."
        )
    
    logger.info(f"🔍 Scraping {request.store} for '{request.query}' in {request.zipcode}")
    
    try:
        # Perform scraping
        results = await asyncio.get_event_loop().run_in_executor(
            None,
            scraper.scrape_store,
            request.query,
            request.store,
            request.zipcode
        )
        
        return results
        
    except Exception as e:
        logger.error(f"❌ Scraping failed: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Scraping failed: {str(e)}"
        )

@app.get("/scrape")
async def scrape_products_get(query: str, store: str, zipcode: str):
    """GET version of scrape endpoint for easy testing"""
    request = ScrapeRequest(query=query, store=store, zipcode=zipcode)
    return await scrape_products(request)

@app.get("/test/{store}")
async def test_store(store: str):
    """Quick test endpoint for a specific store"""
    if store not in SUPPORTED_STORES:
        raise HTTPException(
            status_code=400, 
            detail=f"Store '{store}' not supported"
        )
    
    request = ScrapeRequest(query="milk", store=store, zipcode="15213")
    return await scrape_products(request)

# Enhanced location-based search endpoints
@app.post("/search/location", response_model=LocationSearchResponse)
async def search_by_location(query: LocationQuery):
    """
    Search for products across multiple stores in a location
    
    - **query**: Product search term (e.g., "almond milk", "organic bread")
    - **zipcode**: ZIP code for location
    - **radius_miles**: Search radius in miles (default: 10)
    - **max_results**: Maximum number of results (default: 20)
    - **include_alternatives**: Include alternative products (default: true)
    - **min_confidence**: Minimum confidence score (default: 0.5)
    """
    return await enhanced_scraper.search_by_location(query)

@app.get("/search/location")
async def search_by_location_get(
    query: str, 
    zipcode: str, 
    radius_miles: int = 10,
    max_results: int = 20,
    include_alternatives: bool = True,
    min_confidence: float = 0.5
):
    """GET version of location-based search for easy testing"""
    location_query = LocationQuery(
        query=query,
        zipcode=zipcode,
        radius_miles=radius_miles,
        max_results=max_results,
        include_alternatives=include_alternatives,
        min_confidence=min_confidence
    )
    return await enhanced_scraper.search_by_location(location_query)

@app.get("/coverage")
async def get_store_coverage():
    """Get store coverage information by zipcode ranges"""
    return enhanced_scraper.get_store_coverage()

@app.get("/suggest")
async def suggest_queries(partial: str):
    """Get query suggestions based on partial input"""
    suggestions = enhanced_scraper.suggest_queries(partial)
    return {
        "partial": partial,
        "suggestions": suggestions,
        "count": len(suggestions)
    }

@app.get("/synonyms/{query}")
async def get_product_synonyms(query: str):
    """Get synonyms and alternatives for a product query"""
    synonyms = enhanced_scraper.get_product_synonyms(query)
    return {
        "query": query,
        "synonyms": synonyms,
        "count": len(synonyms)
    }

@app.get("/services/{store_id}")
async def get_store_services(store_id: str):
    """Get available services for a store (delivery, pickup, etc.)"""
    services = enhanced_scraper.get_store_services(store_id)
    return {
        "store_id": store_id,
        "services": services,
        "count": len(services)
    }

@app.get("/sonar/test/{zipcode}")
async def test_sonar(zipcode: str):
    """Test Perplexity Sonar store discovery for a zipcode"""
    try:
        stores = await enhanced_scraper.location_service.get_stores_for_zipcode(zipcode)
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
            "sonar_available": enhanced_scraper.location_service.sonar_client.is_available()
        }
    except Exception as e:
        return {
            "zipcode": zipcode,
            "error": str(e),
            "sonar_available": enhanced_scraper.location_service.sonar_client.is_available()
        }

@app.get("/sonar/stores/{zipcode}")
async def get_sonar_stores(zipcode: str):
    """Get stores discovered via Perplexity Sonar for a zipcode"""
    try:
        sonar_client = enhanced_scraper.location_service.sonar_client
        if not sonar_client.is_available():
            raise HTTPException(
                status_code=503,
                detail="Sonar client not available - check API key configuration"
            )
        
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
                    "status": store.status,
                    "zipcode": store.zipcode
                }
                for store in stores
            ],
            "source": "perplexity_sonar"
        }
    except Exception as e:
        logger.error(f"❌ Sonar store search failed: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Sonar search failed: {str(e)}"
        )

@app.get("/sonar/store/{store_name}/details")
async def get_sonar_store_details(store_name: str, location: str):
    """Get detailed information about a specific store via Sonar"""
    try:
        sonar_client = enhanced_scraper.location_service.sonar_client
        if not sonar_client.is_available():
            raise HTTPException(
                status_code=503,
                detail="Sonar client not available - check API key configuration"
            )
        
        details = await sonar_client.get_store_details(store_name, location)
        return {
            "store_name": store_name,
            "location": location,
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
async def search_sonar_products(query: str, store_name: str, location: str):
    """Search for products at a specific store using Sonar"""
    try:
        sonar_client = enhanced_scraper.location_service.sonar_client
        if not sonar_client.is_available():
            raise HTTPException(
                status_code=503,
                detail="Sonar client not available - check API key configuration"
            )
        
        products = await sonar_client.search_products(query, store_name, location)
        return {
            "query": query,
            "store_name": store_name,
            "location": location,
            "products_found": len(products),
            "products": products,
            "source": "perplexity_sonar"
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
    sonar_client = enhanced_scraper.location_service.sonar_client
    return {
        "available": sonar_client.is_available(),
        "api_key_configured": sonar_client.api_key is not None,
        "cache_enabled": len(sonar_client._cache) > 0,
        "cache_size": len(sonar_client._cache),
        "base_url": sonar_client.base_url
    }

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port, reload=True)
