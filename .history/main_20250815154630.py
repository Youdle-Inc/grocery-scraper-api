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
from scraper.core import GroceryScraper
from scraper.enhanced_scraper import EnhancedScraper
from scraper.models import (
    ScrapeRequest, ScrapeResponse, ProductListing, StoreInfo,
    LocationQuery, LocationSearchResponse
)
from scraper.config import SUPPORTED_STORES

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
            "test": "/test/{store}"
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

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port, reload=True)
