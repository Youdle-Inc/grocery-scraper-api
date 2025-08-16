#!/usr/bin/env python3
"""
Grocery Scraper API
A professional FastAPI service for scraping grocery store product data
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
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

# Initialize Sonar client
sonar_client = SonarClient()

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
        "description": "Professional API for discovering grocery stores using Perplexity Sonar",
        "docs": "/docs",
        "sonar_available": sonar_client.is_available(),
        "endpoints": {
            "health": "/health",
            "sonar": {
                "status": "/sonar/status",
                "stores": "/sonar/stores/{zipcode}",
                "store_details": "/sonar/store/{store_name}/details",
                "product_search": "/sonar/products/search",
                "test": "/sonar/test/{zipcode}"
            }
        }
    }

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    sonar_ready = sonar_client.is_available()
    return {
        "status": "healthy" if sonar_ready else "degraded",
        "timestamp": datetime.now(),
        "sonar_ready": sonar_ready,
        "api_key_configured": sonar_client.api_key is not None
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
async def get_sonar_stores(zipcode: str):
    """Get stores discovered via Perplexity Sonar for a zipcode"""
    try:
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
