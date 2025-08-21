"""
Pydantic models for the Grocery Scraper API
"""

from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime
from enum import Enum

class ScraperType(str, Enum):
    """Types of scraping methods"""
    REAL = "real"
    CACHED = "cached"
    SIMILAR = "similar"

class ProductListing(BaseModel):
    """Model for a single product listing"""
    title: str
    product_name: str
    brand: Optional[str] = None
    price: str
    image_url: Optional[str] = None
    product_url: Optional[str] = None
    availability: str = "In Stock"
    description: Optional[str] = None
    store_address: Optional[str] = None
    store_city: Optional[str] = None
    store_state: Optional[str] = None
    store_zipcode: Optional[str] = None
    
    # New fields for enhanced matching
    confidence_score: Optional[float] = Field(None, ge=0.0, le=1.0)
    match_type: Optional[str] = None  # "exact", "similar", "alternative"
    alternatives: Optional[List[str]] = None
    categories: Optional[List[str]] = None
    nutrition_info: Optional[Dict[str, Any]] = None

class StoreLocation(BaseModel):
    """Model for store location information"""
    store_id: str
    store_name: str
    distance_miles: Optional[float] = None
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    zipcode: Optional[str] = None
    phone: Optional[str] = None
    hours: Optional[Dict[str, str]] = None
    services: Optional[List[str]] = None  # delivery, pickup, etc.
    status: str = "active"

class LocationQuery(BaseModel):
    """Model for location-based product queries"""
    query: str
    zipcode: str
    radius_miles: Optional[int] = Field(10, ge=1, le=50)
    max_results: Optional[int] = Field(20, ge=1, le=100)
    include_alternatives: Optional[bool] = True
    min_confidence: Optional[float] = Field(0.5, ge=0.0, le=1.0)

class ScrapeRequest(BaseModel):
    """Model for scraping request"""
    query: str
    store: str
    zipcode: str

class ScrapeResponse(BaseModel):
    """Model for scraping response"""
    success: bool
    store: str
    query: str
    zipcode: str
    result_count: int
    listings: List[ProductListing]
    error: Optional[str] = None
    timestamp: datetime
    scraper_type: str = "real"
    
    # New fields for enhanced responses
    total_stores_searched: Optional[int] = None
    search_duration_ms: Optional[int] = None
    cache_hit: Optional[bool] = None
    alternatives_found: Optional[int] = None

class StoreInfo(BaseModel):
    """Model for store information"""
    store_id: str
    store_name: str
    supported: bool
    status: str
    description: Optional[str] = None
    coverage_areas: Optional[List[str]] = None  # zipcode ranges or regions

class LocationSearchResponse(BaseModel):
    """Model for location-based search response"""
    success: bool
    query: str
    zipcode: str
    stores_found: int
    total_products: int
    store_results: Dict[str, ScrapeResponse]  # store_id -> results
    best_matches: List[ProductListing]  # top products across all stores
    alternatives: List[ProductListing]  # alternative products
    search_metadata: Dict[str, Any]
    timestamp: datetime
