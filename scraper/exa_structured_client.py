#!/usr/bin/env python3
"""
Enhanced Exa API Client with structured data extraction for grocery products.
Uses Exa's search and contents APIs to get structured product information.
"""

import asyncio
import os
import logging
from typing import Dict, List, Any, Optional
from dotenv import load_dotenv

try:
    from exa_py import Exa
except ImportError:
    Exa = None

load_dotenv()
logger = logging.getLogger(__name__)


class ExaStructuredClient:
    """Enhanced Exa client for structured grocery product data extraction"""
    
    # Store domain mapping for search optimization
    STORE_DOMAINS = {
        "target": "target.com",
        "walmart": "walmart.com",
        "whole_foods": "wholefoodsmarket.com",
        "whole foods": "wholefoodsmarket.com",
        "aldi": "aldi.us",
        "costco": "costco.com",
        "kroger": "kroger.com",
        "sams_club": "samsclub.com",
        "trader_joes": "traderjoes.com",
        "trader joe's": "traderjoes.com",
        "safeway": "safeway.com",
        "albertsons": "albertsons.com",
        "publix": "publix.com",
        "heb": "heb.com",
        "wegmans": "wegmans.com",
    }
    
    def __init__(self, api_key: Optional[str] = None):
        """Initialize Exa client"""
        self.api_key = api_key or os.getenv("EXA_API_KEY")
        self._client = None
        
        if not self.api_key:
            logger.warning("⚠️ No EXA_API_KEY found in environment")
        else:
            try:
                if Exa:
                    self._client = Exa(self.api_key)
                    logger.info("✅ Exa structured client initialized")
                else:
                    logger.warning("⚠️ exa_py not installed")
            except Exception as e:
                logger.error(f"❌ Failed to initialize Exa client: {e}")
    
    def is_available(self) -> bool:
        """Check if Exa client is available"""
        return self._client is not None
    
    def _get_store_domain(self, store_name: str) -> Optional[str]:
        """Get domain for store name"""
        return self.STORE_DOMAINS.get(store_name.lower().strip())
    
    async def search_products_structured(
        self,
        query: str,
        store_name: Optional[str] = None,
        zipcode: Optional[str] = None,
        num_results: int = 20,
        include_location: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Search for grocery products with structured data extraction
        
        Args:
            query: Product search query
            store_name: Optional store name to filter results
            zipcode: Optional zipcode for location-based results
            num_results: Number of results to return
            include_location: Whether to include store location data
            
        Returns:
            List of structured product data
        """
        if not self.is_available():
            logger.warning("⚠️ Exa client not available")
            return []
        
        try:
            # Build search query
            search_query = self._build_search_query(query, store_name, zipcode)
            
            # Define structured schema for product data
            product_schema = {
                "type": "object",
                "properties": {
                    "product_name": {
                        "type": "string",
                        "description": "Name of the product"
                    },
                    "brand": {
                        "type": "string",
                        "description": "Brand name of the product"
                    },
                    "price": {
                        "type": "number",
                        "description": "Price in USD"
                    },
                    "currency": {
                        "type": "string",
                        "description": "Currency code (USD)"
                    },
                    "quantity": {
                        "type": "string",
                        "description": "Product quantity or size (e.g., '1 gallon', '64 oz', '12 pack')"
                    },
                    "availability": {
                        "type": "string",
                        "description": "Stock availability status"
                    },
                    "store_name": {
                        "type": "string",
                        "description": "Name of the store selling the product"
                    },
                    "store_address": {
                        "type": "string",
                        "description": "Full store address"
                    },
                    "store_zipcode": {
                        "type": "string",
                        "description": "Store ZIP code"
                    },
                    "store_city": {
                        "type": "string",
                        "description": "Store city"
                    },
                    "store_state": {
                        "type": "string",
                        "description": "Store state"
                    },
                    "category": {
                        "type": "string",
                        "description": "Product category"
                    },
                    "description": {
                        "type": "string",
                        "description": "Product description"
                    },
                    "rating": {
                        "type": "number",
                        "description": "Customer rating (1-5)"
                    },
                    "reviews_count": {
                        "type": "number",
                        "description": "Number of customer reviews"
                    }
                },
                "required": ["product_name", "price"]
            }
            
            logger.info(f"🔍 Searching Exa for: {search_query}")
            
            # Search with structured data extraction
            search_options = {
                "query": search_query,
                "num_results": num_results,
                "type": "keyword",  # Use keyword search for product discovery
                "text": {"max_characters": 2000},
                "summary": {
                    "query": "Extract detailed product information including name, brand, price, quantity/size, availability, store details, and customer ratings",
                    "schema": product_schema
                },
                "extras": {"imageLinks": 5}  # Get multiple image links
            }
            
            # Add domain filter if store specified
            if store_name:
                domain = self._get_store_domain(store_name)
                if domain:
                    search_options["include_domains"] = [domain]
            
            # Execute search
            response = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: self._client.search_and_contents(**search_options)
            )
            
            # Process results
            products = self._process_search_results(response, store_name, zipcode)
            
            logger.info(f"✅ Found {len(products)} products via Exa")
            return products
            
        except Exception as e:
            logger.error(f"❌ Exa structured search failed: {e}")
            return []
    
    def _build_search_query(self, query: str, store_name: Optional[str], zipcode: Optional[str]) -> str:
        """Build optimized search query"""
        parts = [query]
        
        if store_name:
            parts.append(store_name)
        
        # Add product-specific keywords to improve results
        if any(keyword in query.lower() for keyword in ["milk", "bread", "eggs", "cheese", "butter"]):
            parts.append("grocery store")
        
        return " ".join(parts)
    
    def _process_search_results(
        self,
        response: Any,
        store_name: Optional[str],
        zipcode: Optional[str]
    ) -> List[Dict[str, Any]]:
        """Process Exa search results into structured product data"""
        products = []
        
        try:
            results = getattr(response, "results", [])
            
            for result in results:
                try:
                    product = self._extract_product_data(result, store_name, zipcode)
                    if product:
                        products.append(product)
                except Exception as e:
                    logger.warning(f"⚠️ Failed to process result: {e}")
                    continue
            
        except Exception as e:
            logger.error(f"❌ Failed to process search results: {e}")
        
        return products
    
    def _extract_product_data(
        self,
        result: Any,
        store_name: Optional[str],
        zipcode: Optional[str]
    ) -> Optional[Dict[str, Any]]:
        """Extract structured product data from a single result"""
        try:
            # Get structured summary data
            summary = getattr(result, "summary", {})
            if isinstance(summary, str):
                # If summary is a string, try to parse as dict
                import json
                try:
                    summary = json.loads(summary)
                except:
                    summary = {}
            
            # Extract basic data
            product_name = summary.get("product_name") or getattr(result, "title", "Unknown Product")
            price = summary.get("price")
            
            # Parse price if it's a string
            if isinstance(price, str):
                import re
                price_match = re.search(r'[\d.]+', price.replace(',', ''))
                price = float(price_match.group()) if price_match else None
            
            # Extract image URLs
            image_url = None
            additional_images = []
            
            # Try to get image from result
            if getattr(result, "image", None):
                image_url = result.image
            
            # Try to get images from extras
            if hasattr(result, "extras") and result.extras:
                image_links = result.extras.get("imageLinks", [])
                if image_links and not image_url:
                    image_url = image_links[0]
                if len(image_links) > 1:
                    additional_images = image_links[1:4]
            
            # Build product object
            product = {
                "name": product_name,
                "brand": summary.get("brand"),
                "price": price,
                "currency": summary.get("currency") or "USD",
                "quantity": summary.get("quantity"),
                "availability": summary.get("availability") or "In Stock",
                "image_url": image_url,
                "product_url": getattr(result, "url", None),
                "description": summary.get("description") or getattr(result, "text", "")[:500],
                "category": summary.get("category"),
                "rating": summary.get("rating"),
                "reviews_count": summary.get("reviews_count"),
                "source": "exa_structured"
            }
            
            # Add store information
            extracted_store_name = summary.get("store_name") or store_name
            if extracted_store_name:
                product["store_name"] = extracted_store_name
            
            # Add location information
            product["store_address"] = summary.get("store_address")
            product["store_city"] = summary.get("store_city")
            product["store_state"] = summary.get("store_state")
            product["store_zipcode"] = summary.get("store_zipcode") or zipcode
            
            # Add additional images if available
            if additional_images:
                product["additional_images"] = additional_images
            
            return product
            
        except Exception as e:
            logger.error(f"❌ Failed to extract product data: {e}")
            return None
    
    async def get_product_details(self, url: str) -> Optional[Dict[str, Any]]:
        """
        Get detailed product information from a specific URL
        
        Args:
            url: Product page URL
            
        Returns:
            Structured product details
        """
        if not self.is_available():
            return None
        
        try:
            # Define detailed schema
            detail_schema = {
                "type": "object",
                "properties": {
                    "product_name": {"type": "string"},
                    "brand": {"type": "string"},
                    "price": {"type": "number"},
                    "quantity": {"type": "string"},
                    "description": {"type": "string"},
                    "ingredients": {"type": "array", "items": {"type": "string"}},
                    "nutrition_facts": {"type": "object"},
                    "allergens": {"type": "array", "items": {"type": "string"}},
                    "rating": {"type": "number"},
                    "reviews_count": {"type": "number"},
                    "availability": {"type": "string"}
                }
            }
            
            response = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: self._client.get_contents(
                    [url],
                    text=True,
                    summary={
                        "query": "Extract comprehensive product information including ingredients, nutrition, and customer reviews",
                        "schema": detail_schema
                    }
                )
            )
            
            if response and response.results:
                result = response.results[0]
                return self._extract_product_data(result, None, None)
            
            return None
            
        except Exception as e:
            logger.error(f"❌ Failed to get product details: {e}")
            return None
    
    async def search_stores_in_zipcode(self, store_chain: str, zipcode: str) -> List[Dict[str, Any]]:
        """
        Search for specific store locations in a zipcode
        
        Args:
            store_chain: Store chain name (e.g., "Target", "Walmart")
            zipcode: ZIP code to search
            
        Returns:
            List of store locations with addresses
        """
        if not self.is_available():
            return []
        
        try:
            # Build store location search query
            search_query = f"{store_chain} store locations near {zipcode}"
            domain = self._get_store_domain(store_chain)
            
            # Define store location schema
            store_schema = {
                "type": "object",
                "properties": {
                    "store_name": {"type": "string"},
                    "address": {"type": "string"},
                    "city": {"type": "string"},
                    "state": {"type": "string"},
                    "zipcode": {"type": "string"},
                    "phone": {"type": "string"},
                    "hours": {"type": "object"},
                    "services": {"type": "array", "items": {"type": "string"}}
                }
            }
            
            search_options = {
                "query": search_query,
                "num_results": 10,
                "type": "keyword",
                "summary": {
                    "query": "Extract store location details including address, city, state, zipcode, phone, and services",
                    "schema": store_schema
                }
            }
            
            if domain:
                search_options["include_domains"] = [domain]
            
            response = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: self._client.search_and_contents(**search_options)
            )
            
            stores = []
            for result in getattr(response, "results", []):
                summary = getattr(result, "summary", {})
                if isinstance(summary, dict):
                    stores.append({
                        "store_id": store_chain.lower().replace(" ", "_"),
                        "store_name": summary.get("store_name") or store_chain,
                        "address": summary.get("address"),
                        "city": summary.get("city"),
                        "state": summary.get("state"),
                        "zipcode": summary.get("zipcode") or zipcode,
                        "phone": summary.get("phone"),
                        "hours": summary.get("hours"),
                        "services": summary.get("services") or ["in-store"],
                        "status": "active",
                        "source": "exa_structured"
                    })
            
            logger.info(f"✅ Found {len(stores)} {store_chain} locations near {zipcode}")
            return stores
            
        except Exception as e:
            logger.error(f"❌ Store location search failed: {e}")
            return []

