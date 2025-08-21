"""
Pydantic models for the Grocery Scraper API
"""

from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

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

class StoreInfo(BaseModel):
    """Model for store information"""
    store_id: str
    store_name: str
    supported: bool
    status: str
    description: Optional[str] = None
