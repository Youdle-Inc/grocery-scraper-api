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
    website: Optional[str] = None
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


# === Response models for FastAPI endpoints ===

class HealthServiceStatus(BaseModel):
    exa_api: str

class HealthResponse(BaseModel):
    status: str
    timestamp: str
    version: str
    services: HealthServiceStatus

class StoreLocationLite(BaseModel):
    store_id: str
    store_name: str
    address: Optional[str] = None
    services: Optional[List[str]] = None
    status: Optional[str] = None
    zipcode: Optional[str] = None
    website: Optional[str] = None
    location: Optional[Dict[str, Optional[str]]] = None

class StoresResponse(BaseModel):
    zipcode: str
    stores_found: int
    search_timestamp: str
    stores: List[StoreLocationLite]
    source: str
    api_version: str
    cache: Optional[Dict[str, Any]] = None

class StoreDetailsResponse(BaseModel):
    store_name: str
    location: str
    details: Dict[str, Any]
    source: str

class ProductLite(BaseModel):
    name: Optional[str] = None
    price: Optional[float | str] = None
    currency: Optional[str] = "USD"
    quantity: Optional[str] = None  # Product size/quantity (e.g., "1 gallon", "64 oz")
    availability: Optional[str] = None
    category: Optional[str] = None
    brand: Optional[str] = None
    size: Optional[str] = None  # Deprecated - use quantity instead
    description: Optional[str] = None
    image_url: Optional[str] = None
    additional_images: Optional[List[str]] = None
    product_url: Optional[str] = None
    
    # Store information
    store_name: Optional[str] = None
    store_address: Optional[str] = None
    store_city: Optional[str] = None
    store_state: Optional[str] = None
    store_zipcode: Optional[str] = None
    
    # Product details
    nutritional_info: Optional[Dict[str, Any]] = None
    ingredients: Optional[List[str]] = None
    allergens: Optional[List[str]] = None
    online_available: Optional[bool] = None
    in_store_only: Optional[bool] = None
    reviews_count: Optional[int | str] = None
    rating: Optional[float | str] = None
    
    # Metadata
    source: Optional[str] = "exa_structured"

class ProductsSearchResponse(BaseModel):
    query: str
    store_name: str
    location: str
    products_found: int
    search_timestamp: str
    products: List[ProductLite]
    source: str
    api_version: str

class Offer(BaseModel):
    store_id: str
    store_name: str
    price: Optional[float | str] = None
    currency: Optional[str] = "USD"
    quantity: Optional[str] = None
    availability: Optional[str] = None
    product_url: Optional[str] = None
    image_url: Optional[str] = None
    source: List[str]
    
    # Store location details
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    zipcode: Optional[str] = None

class CanonicalProduct(BaseModel):
    name: Optional[str] = None
    brand: Optional[str] = None
    quantity: Optional[str] = None  # Product size/quantity
    size: Optional[str] = None  # Deprecated - use quantity
    images: List[str] = []
    description: Optional[str] = None
    category: Optional[str] = None

class AggregateResult(BaseModel):
    canonical_product: CanonicalProduct
    offers: List[Offer]

class AggregateResponse(BaseModel):
    query: str
    zipcode: str
    stores_considered: List[str]
    results: List[AggregateResult]
    source: str
    cache: Optional[Dict[str, Any]] = None

# New models for enhanced response structure
class ProductImage(BaseModel):
    url: str
    is_primary: bool = True

class NutritionInfo(BaseModel):
    calories: Optional[int] = None
    serving_size: Optional[str] = None
    servings_per_container: Optional[int] = None

class StoreInfoDetailed(BaseModel):
    retailer: str
    retailer_store_id: Optional[str] = None
    store_name: str
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    zipcode: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None

class OfferEnhanced(BaseModel):
    store: StoreInfoDetailed
    product_url: str
    fulfillment: List[str] = []  # PICKUP, DELIVERY, IN_STORE
    availability: str = "CHECK_STORE"  # IN_STOCK, LOW_STOCK, OUT_OF_STOCK, CHECK_STORE
    inventory_count: Optional[int] = None
    regular_price: Optional[float] = None
    sale_price: Optional[float] = None
    price_updated_at: Optional[str] = None
    promo_badge: Optional[str] = None

class ProductResultEnhanced(BaseModel):
    upc: Optional[str] = None
    retailer_sku: Optional[str] = None
    name: str
    brand: Optional[str] = None
    category_path: List[str] = []
    description: Optional[str] = None
    size: Optional[str] = None
    package_quantity: Optional[str] = None
    images: List[ProductImage] = []
    nutrition: Optional[NutritionInfo] = None
    offers: List[OfferEnhanced] = []
    source: str = "scraper_v2"
    scraped_at: Optional[str] = None

class AggregateResponseEnhanced(BaseModel):
    query: str
    zipcode: str
    search_timestamp: str
    results: List[ProductResultEnhanced]
    stores_considered: List[str]
    meta: Dict[str, Any]
