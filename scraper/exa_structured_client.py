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
from exa_py import Exa
# Prompt templates removed - using inline prompts

load_dotenv()
exa = Exa(os.getenv("EXA_API_KEY"))
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
    
    def _detect_product_category(self, query: str) -> str:
        """Detect product category from search query"""
        query_lower = query.lower()
        
        # Dairy products
        if any(word in query_lower for word in ["milk", "cheese", "yogurt", "butter", "cream", "dairy"]):
            return "dairy"
        
        # Produce
        if any(word in query_lower for word in ["apple", "banana", "orange", "lettuce", "tomato", "onion", "carrot", "produce", "fruit", "vegetable"]):
            return "produce"
        
        # Meat
        if any(word in query_lower for word in ["beef", "chicken", "pork", "fish", "meat", "steak", "ground", "sausage", "bacon"]):
            return "meat"
        
        # Frozen
        if any(word in query_lower for word in ["frozen", "ice cream", "pizza", "frozen dinner", "frozen meal"]):
            return "frozen"
        
        # Organic
        if any(word in query_lower for word in ["organic", "natural", "non-gmo", "free range"]):
            return "organic"
        
        return "generic"
    
    def _get_context_prompt(self, context: str) -> str:
        """Get context-specific prompt"""
        prompts = {
            "store_search": "Find grocery stores and supermarkets in the specified location. Focus on major chains and local stores.",
            "product_search": "Search for specific grocery products and items. Focus on product details, prices, and availability.",
            "generic": "Search for grocery-related information including stores, products, and services."
        }
        return prompts.get(context, prompts["generic"])
    
    def _get_category_prompt(self, category: str) -> str:
        """Get category-specific prompt"""
        prompts = {
            "dairy": "Focus on dairy products like milk, cheese, yogurt, and butter.",
            "produce": "Focus on fresh fruits and vegetables, organic options, and seasonal items.",
            "meat": "Focus on fresh meat, poultry, seafood, and deli items.",
            "bakery": "Focus on bread, pastries, cakes, and baked goods.",
            "organic": "Focus on organic, natural, and health-focused products.",
            "generic": "Search for general grocery products and items."
        }
        return prompts.get(category, prompts["generic"])
    
    def _build_enhanced_query(self, query: str, store_name: str, zipcode: str, category: str) -> str:
        """Build enhanced search query with context"""
        base_query = query
        
        # Add store context if provided
        if store_name and store_name != "grocery store":
            base_query = f"{query} at {store_name}"
        
        # Add location context if provided
        if zipcode:
            base_query = f"{base_query} in {zipcode}"
        
        # Add category context
        if category != "generic":
            base_query = f"{base_query} {category} products"
        
        return base_query
    
    def _detect_search_context(self, query: str) -> str:
        """Detect search context from user query"""
        query_lower = query.lower()
        if any(word in query_lower for word in ['store', 'location', 'near', 'find']):
            return "store_search"
        elif any(word in query_lower for word in ['product', 'item', 'buy', 'price']):
            return "product_search"
        return "generic"
    
    def _get_optimized_prompt(self, query: str, context: str = None) -> str:
        """Get optimized prompt based on query context and category"""
        # Auto-detect context if not provided
        if not context:
            context = self._detect_search_context(query)
        
        # Get context-specific prompt
        context_prompt = self._get_context_prompt(context)
        
        # Get category-specific prompt
        category = self._detect_product_category(query)
        category_prompt = self._get_category_prompt(category)
        
        # Combine context and category prompts
        combined_prompt = f"{context_prompt}\n\nCategory-specific focus: {category_prompt}"
        
        # Add validation instructions
        validation_instructions = """
        
        Validation requirements:
        1. Price must be numeric (e.g., 4.99, not "$4.99")
        2. Quantity must include units (e.g., "64 fl oz", "1 gallon")
        3. Store address must be complete with city, state, ZIP
        4. Availability must be current status
        5. Ratings must be 1-5 scale
        6. If information is incomplete, mark confidence level and provide best available data
        """
        
        return combined_prompt + validation_instructions
    
    async def search_products_structured(
        self,
        query: str,
        store_name: Optional[str] = None,
        zipcode: Optional[str] = None,
        num_results: int = 20,
        include_location: bool = True,
        context: str = None
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
            # Build search query with category-specific template
            category = self._detect_product_category(query)
            search_query = self._build_enhanced_query(query, store_name or "grocery store", zipcode or "", category)
            
            # Get optimized prompt based on context and category
            optimized_prompt = self._get_optimized_prompt(query, context)
            
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
                    },
                    "confidence_score": {
                        "type": "number",
                        "description": "Confidence in data accuracy (0-1)"
                    }
                },
                "required": ["product_name", "price"]
            }
            
            logger.info(f"🔍 Searching Exa for: {search_query} (Category: {category}, Context: {context or 'auto-detected'})")
            
            # Search with minimal options
            search_options = {
                "query": search_query,
                "num_results": num_results,
                "type": "keyword"
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
        """Build optimized search query for better product discovery"""
        parts = [query]
        
        # Add store context for better targeting
        if store_name:
            parts.append(f"at {store_name}")
        
        # Add location context if provided
        if zipcode:
            parts.append(f"near {zipcode}")
        
        # Add grocery-specific keywords to improve results
        grocery_keywords = ["milk", "bread", "eggs", "cheese", "butter", "meat", "produce", "frozen", "organic", "fresh"]
        if any(keyword in query.lower() for keyword in grocery_keywords):
            parts.append("grocery store product")
        
        # Add shopping context for better results
        if not any(word in query.lower() for word in ["buy", "shop", "store", "grocery"]):
            parts.append("buy online")
        
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
                        "query": "Extract comprehensive grocery product details from the product page. Focus on: complete product name and brand, exact price, detailed quantity/size, full description, ingredients list, nutritional facts, allergens, customer ratings and review counts, availability status. Ensure all data is current and accurate from the product page.",
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
                    "query": "Extract complete grocery store location information. Focus on: exact store name, full street address, city, state, ZIP code, phone number, operating hours, available services (delivery, pickup, curbside, in-store shopping). Ensure address is complete and properly formatted with city, state, and ZIP code.",
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

