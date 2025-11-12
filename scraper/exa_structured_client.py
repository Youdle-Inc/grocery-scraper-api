#!/usr/bin/env python3
"""
Enhanced Exa API Client with structured data extraction for grocery products.
Uses Exa's search and contents APIs to get structured product information.
"""

import asyncio
import os
import logging
import re
import json
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
        # For better product results, make query more specific
        # Add common product variations to get individual product pages
        
        # Detect if query is a liquid product (milk, juice, etc.) that uses gallons
        liquid_products = ["milk", "juice", "water", "soda", "beer", "wine"]
        is_liquid = any(liquid in query.lower() for liquid in liquid_products)
        
        if store_name and store_name != "grocery store":
            if len(query.split()) == 1 and is_liquid:  # Single word liquid product like "milk"
                # Expand to find specific products with size
                base_query = f"{query} gallon {store_name} product"
            elif len(query.split()) == 1:  # Single word non-liquid product like "bread"
                # Just add store name, don't add "gallon"
                base_query = f"{query} {store_name} product"
            else:
                base_query = f"{query} {store_name}"
        else:
            if len(query.split()) == 1 and is_liquid:
                base_query = f"{query} gallon grocery product"
            elif len(query.split()) == 1:
                base_query = f"{query} grocery product"
            else:
                base_query = f"{query} grocery"
        
        # Add location information if zipcode is provided
        if zipcode:
            # Get city/state from zipcode for better location context
            city, state = self._get_city_state_from_zipcode(zipcode)
            if city and state:
                # Use city, state, and zipcode for best location filtering
                base_query = f"{base_query} near {city} {state} zipcode {zipcode}"
            else:
                # For unknown zipcodes, use explicit zipcode location filtering
                # Exa understands zipcodes well, so this should still work effectively
                base_query = f"{base_query} location zipcode {zipcode} in {zipcode}"

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
            
            # Search with text content extraction - get more text for better descriptions
            # Note: Exa's search_and_contents doesn't support summary parameter
            # Use get_contents with summary for individual URLs if needed
            search_options = {
                "query": search_query,
                "num_results": min(num_results * 3, 50),  # Request 3x to account for filtering
                "type": "neural",  # Neural search for semantic matching
                "text": {"max_characters": 3000}  # Get more text content for better descriptions
                # Note: extras/image_links is only available in get_contents, not search_and_contents
            }
            
            logger.debug(f"Exa search options: {search_options}")

            # Add domain filter if store specified
            if store_name:
                domain = self._get_store_domain(store_name)
                if domain:
                    search_options["include_domains"] = [domain]

            # Execute search
            try:
                logger.info(f"📡 Calling Exa API with query: {search_query}")
                response = await asyncio.get_event_loop().run_in_executor(
                    None,
                    lambda: self._client.search_and_contents(**search_options)
                )
                
                if not response:
                    logger.warning("⚠️ Exa returned None response")
                    return []
                
                logger.info(f"📥 Exa response received: {type(response)}")
                
                # Process results
                products = await self._process_search_results(response, store_name, zipcode)
            except Exception as e:
                logger.error(f"❌ Exa API call failed: {e}", exc_info=True)
                return []

            # Limit to requested number
            products = products[:num_results]

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
    
    def _is_product_page(self, url: str, title: str) -> bool:
        """Check if URL is an actual product page, not a category/search page"""
        if not url:
            return False

        # Filter out obvious search and category pages
        exclude_patterns = [
            '/search',
            '/category',
            '/browse',
            '/s/',  # Target search pages
            '/c/',  # Target category pages
            '?Nao=',  # Pagination
            'Page ',  # Page indicators in title
        ]

        url_lower = url.lower()
        for pattern in exclude_patterns:
            if pattern in url_lower or pattern in title:
                return False

        # Check for product page indicators
        product_indicators = [
            '/p/',  # Target product pages
            '/ip/',  # Walmart individual product pages
            '/A-',  # Target product ID
            '/product/',  # Generic product pages
            '/products/',  # Generic products pages
            '/item/',  # Item pages
            '/store/',  # Store pages (might be product pages)
        ]

        for indicator in product_indicators:
            if indicator in url_lower:
                return True
        
        # If URL contains common store domains and doesn't look like a search page, assume it might be a product
        store_domains = ['target.com', 'walmart.com', 'wholefoodsmarket.com', 'kroger.com', 'aldi.us']
        if any(domain in url_lower for domain in store_domains):
            # If it's not clearly a search/category page, give it a chance
            if not any(exclude in url_lower for exclude in ['/search', '/category', '/browse', '/s/', '/c/']):
                return True

        return False

    async def _process_search_results(
        self,
        response: Any,
        store_name: Optional[str],
        zipcode: Optional[str]
    ) -> List[Dict[str, Any]]:
        """Process Exa search results into structured product data"""
        products = []

        try:
            results = getattr(response, "results", [])
            logger.info(f"🔍 Processing {len(results)} results from Exa")

            for idx, result in enumerate(results):
                try:
                    # Check if this is an actual product page
                    url = getattr(result, "url", "")
                    title = getattr(result, "title", "")

                    if not url:
                        logger.debug(f"Skipping result {idx}: No URL")
                        continue
                    
                    logger.debug(f"Result {idx}: {title[:60]}... | URL: {url[:80]}...")

                    if not self._is_product_page(url, title):
                        logger.debug(f"Skipping non-product page: {title[:60]}... (URL: {url[:60]}...)")
                        # For now, let's be less strict and include results that might be products
                        # Only skip obvious search/category pages
                        if any(exclude in url.lower() for exclude in ['/search', '/category', '/browse', '/s/', '/c/']):
                            logger.debug(f"Definitely skipping search/category page: {url[:60]}...")
                            continue

                    # Extract product data (skip async image extraction during batch for performance)
                    product = await self._extract_product_data(result, store_name, zipcode, extract_images_async=False)
                    
                    # If no image found and we have a product URL, try async extraction
                    # This is important because search_and_contents doesn't return image_links
                    if product and not product.get("image_url") and product.get("product_url"):
                        try:
                            logger.debug(f"🖼️ No image found for {product.get('name', 'Unknown')[:50]}, trying async extraction...")
                            extracted_image = await self.get_product_image_url(product["product_url"])
                            if extracted_image:
                                product["image_url"] = extracted_image
                                logger.info(f"✅ Got image via async extraction for {product.get('name', 'Unknown')[:50]}: {extracted_image[:80]}...")
                            else:
                                logger.debug(f"⚠️ Async extraction returned no image for {product.get('product_url', 'Unknown')[:80]}...")
                        except Exception as e:
                            logger.debug(f"Failed async image extraction: {e}")
                    
                    if product:
                        products.append(product)
                        logger.debug(f"✅ Added product: {product.get('name', 'Unknown')[:50]}...")
                    else:
                        logger.debug(f"⚠️ Failed to extract product data from: {title[:50]}...")
                except Exception as e:
                    logger.warning(f"⚠️ Failed to process result {idx}: {e}")
                    continue

            logger.info(f"✅ Processed {len(results)} results, extracted {len(products)} products")
        except Exception as e:
            logger.error(f"❌ Failed to process search results: {e}")

        return products
    
    
    def _clean_exa_summary(self, summary: str) -> Optional[str]:
        """Clean and format Exa AI-generated summary"""
        if not summary:
            return None
        
        import re
        # Exa summaries are usually clean, but remove any artifacts
        summary = re.sub(r'\[skip to [^\]]+\]', '', summary, flags=re.IGNORECASE)
        summary = re.sub(r'\[[^\]]+\]\([^\)]+\)', '', summary)
        summary = re.sub(r'https?://[^\s]+', '', summary)
        summary = re.sub(r'\s+', ' ', summary).strip()
        
        # Limit length but keep informative
        if len(summary) > 500:
            sentences = summary.split('. ')
            result = []
            for sentence in sentences:
                if len('. '.join(result + [sentence])) <= 500:
                    result.append(sentence)
                else:
                    break
            summary = '. '.join(result) + '.' if result else summary[:497] + '...'
        
        return summary if len(summary) > 20 else None
    
    def _extract_product_description(self, text: str, title: str) -> Optional[str]:
        """Extract clean, meaningful product description from text"""
        if not text:
            return None
        
        import re
        
        # Aggressive cleaning - remove all navigation/UI elements
        text = re.sub(r'\[skip to [^\]]+\]', '', text, flags=re.IGNORECASE)
        text = re.sub(r'\[[^\]]+\]\([^\)]+\)', '', text)  # Remove markdown links
        text = re.sub(r'https?://[^\s]+', '', text)  # Remove URLs
        text = re.sub(r'Target Circle[™®]?|Registry|Wish List|Weekly Ad|Find Stores|Categories|Deals|New & featured|Pickup|delivery', '', text, flags=re.IGNORECASE)
        text = re.sub(r'Robot or human\?.*?Thank You!', '', text, flags=re.IGNORECASE | re.DOTALL)
        text = re.sub(r'Sponsored|Add to cart|Add to list|Sign in|Shipping|Return this item|Eligible for|At a glance|About this item|Details|Label info', '', text, flags=re.IGNORECASE)
        text = re.sub(r'Specifications & Returns|Q&A|Additional product information|recommendations|Load all content|Discover more options|Loading content|Buy it again|Frequently bought together|Gue', '', text, flags=re.IGNORECASE)
        text = re.sub(r'registries and s|## |###|Your views|This product is featured|Featured products|ratings & reviews|Disclaimer|Get top|latest trends', '', text, flags=re.IGNORECASE)  # Remove markdown headers and navigation
        text = re.sub(r'and at once|sts also viewed', '', text, flags=re.IGNORECASE)
        text = re.sub(r'\( \( search|! ! !|# #|###', '', text)  # Remove weird formatting
        text = re.sub(r'\$\d+\.\d+/[^\s]+', '', text)  # Remove unit prices like "$9.07/fluid ounce"
        text = re.sub(r'out of 5 stars|reviews?\s*\d+', '', text, flags=re.IGNORECASE)  # Remove rating text
        text = re.sub(r'Gluten Free|Sponsored|Search', '', text, flags=re.IGNORECASE)
        text = re.sub(r'Only at [a-z\s]+', '', text, flags=re.IGNORECASE)  # Remove "Only at target"
        text = re.sub(r'Free & easy returns.*?days', '', text, flags=re.IGNORECASE | re.DOTALL)  # Remove return policy
        text = re.sub(r'by mail or in store|for a full refund', '', text, flags=re.IGNORECASE)
        # Fix formatting issues
        text = re.sub(r'Fat Content(\d+)', r'Fat Content: \1%', text, flags=re.IGNORECASE)  # Fix "Fat Content1" -> "Fat Content: 1%"
        text = re.sub(r'Fat Content:\s*(\d+)%\s*Percent', r'Fat Content: \1%', text, flags=re.IGNORECASE)  # Fix "Fat Content: 1% Percent" -> "Fat Content: 1%"
        text = re.sub(r'Size(\d+\.?\d*)', r'Size: \1', text, flags=re.IGNORECASE)  # Fix "Size0.5" -> "Size: 0.5"
        text = re.sub(r'-{2,}', ' ', text)  # Replace multiple dashes with space
        text = re.sub(r'\s+-\s+-\s+', ' ', text)  # Fix " - - " patterns
        text = re.sub(r'\s+-\s+$', '', text)  # Remove trailing dashes
        text = re.sub(r'Percent\s*-\s*-', 'Percent', text, flags=re.IGNORECASE)  # Fix "Percent - -"
        text = re.sub(r'Gallon\s*-\s*-', 'Gallon', text, flags=re.IGNORECASE)  # Fix "Gallon - -"
        text = re.sub(r'\s+', ' ', text)  # Normalize whitespace
        # Final cleanup - remove any remaining "Only at" patterns
        text = re.sub(r'Only at\s+\w+', '', text, flags=re.IGNORECASE)
        
        # Look for actual product description patterns
        # Pattern 1: "About this item" or "Details" sections
        about_match = re.search(r'(?:about|details|description|overview|product info)[\s:]+(.+?)(?:sponsored|additional|discover|more|$)', text, re.IGNORECASE | re.DOTALL)
        if about_match:
            desc_text = about_match.group(1)
            # Clean it further
            desc_text = re.sub(r'\s+', ' ', desc_text).strip()
            if len(desc_text) > 30:
                # Take first 200 chars
                desc_text = desc_text[:200] if len(desc_text) <= 200 else desc_text[:197] + '...'
                return desc_text
        
        # Pattern 2: Look for sentences with product keywords
        sentences = re.split(r'[.!?]\s+', text)
        meaningful_sentences = []
        
        skip_patterns = [
            r'^skip to|^terms of use|^privacy policy|^activate and hold|^thank you',
            r'^banner|^cookie|^javascript|^enable|^loading|^return|^eligible',
            r'^sponsored|^add to|^sign in|^shipping|^free|^easy',
            r'^\s*$|^[^\w]*$|^[()\[\]{}]+$',  # Empty or only symbols
            r'^\d+\.\d+$|^\d+$'  # Just numbers
        ]
        
        product_keywords = [
            'organic', 'whole', 'fat', 'reduced', 'low fat', 'skim', 'fresh', 'natural',
            'pasteurized', 'homogenized', 'vitamin', 'calcium', 'protein', 'nutrition',
            'ingredients', 'allergen', 'contains', 'gluten', 'dairy', 'cage free',
            'free range', 'grade a', 'large', 'extra large', 'gallon', 'fluid ounce',
            'wheat', 'whole grain', 'sliced', 'enriched', 'fortified'
        ]
        
        for sentence in sentences:
            sentence = sentence.strip()
            if not sentence or len(sentence) < 15:
                continue
            
            # Skip navigation/UI text
            skip = False
            for pattern in skip_patterns:
                if re.search(pattern, sentence, re.IGNORECASE):
                    skip = True
                    break
            
            if skip:
                continue
            
            # Must not contain navigation chars or junk text
            if any(char in sentence for char in ['[', ']', '{', '}', 'http', 'www.', '* * *']):
                continue
            
            # Skip sentences with navigation words
            junk_words = ['specifications', 'returns', 'q&a', 'additional', 'recommendations', 
                         'loading', 'discover', 'buy it again', 'frequently bought', 'featured',
                         'ratings & reviews', 'disclaimer', 'get top', 'latest trends', 
                         'and at once', 'also viewed', 'your views', 'target finds']
            sentence_lower = sentence.lower()
            if any(junk in sentence_lower for junk in junk_words):
                continue
            
            # Check if it contains product keywords or looks like descriptive content
            has_keywords = any(keyword in sentence_lower for keyword in product_keywords)
            is_descriptive = len(sentence) > 40 and not re.search(r'^\d+', sentence) and not re.search(r'^\s*[*#]', sentence)
            
            if has_keywords or is_descriptive:
                # Clean sentence
                sentence = re.sub(r'\s+', ' ', sentence).strip()
                sentence = re.sub(r'\s*[*#]+\s*', ' ', sentence)  # Remove asterisks and hashes
                if len(sentence) > 20:  # Only add if meaningful length
                    meaningful_sentences.append(sentence)
                
                # Limit to 2-3 best sentences
                if len(meaningful_sentences) >= 3:
                    break
        
        if meaningful_sentences:
            description = '. '.join(meaningful_sentences)
            description = re.sub(r'\s+', ' ', description).strip()
            
            # Final cleanup - remove all remaining formatting issues
            description = re.sub(r'\s+-\s+-\s+', ' ', description)  # Remove " - - " patterns
            description = re.sub(r'\s+-\s+$', '', description)  # Remove trailing dashes
            description = re.sub(r'^\s*-\s*', '', description)  # Remove leading dashes
            description = re.sub(r'^[^\w]+|[^\w]+$', '', description)  # Remove leading/trailing non-word chars
            description = re.sub(r'\s+', ' ', description).strip()  # Final whitespace normalization
            
            if len(description) > 20:
                # Limit length
                if len(description) > 300:
                    description = description[:297] + '...'
                return description
        
        # Fallback: Generate description from title if we have product info
        if title and len(title) > 5:
            # Try to create a simple description from title
            title_lower = title.lower()
            desc_parts = []
            
            if 'organic' in title_lower:
                desc_parts.append('Organic product')
            if any(word in title_lower for word in ['milk', 'dairy']):
                desc_parts.append('Fresh dairy product')
            if any(word in title_lower for word in ['egg', 'eggs']):
                desc_parts.append('Fresh eggs')
            if any(word in title_lower for word in ['bread']):
                desc_parts.append('Fresh baked bread')
            
            if desc_parts:
                return '. '.join(desc_parts) + '.'
        
        return None
    
    async def _get_availability_from_exa(self, url: Optional[str]) -> Optional[str]:
        """
        Get availability status from Exa using structured extraction.
        This makes an API call to Exa to get structured availability data.
        
        Returns availability string or None if extraction fails.
        """
        if not url or not self.is_available():
            return None
        
        try:
            # Define schema focused on availability
            availability_schema = {
                "type": "object",
                "properties": {
                    "availability": {
                        "type": "string",
                        "description": "Stock availability status. Extract exact status from page: 'in stock', 'out of stock', 'sold out', 'available', 'unavailable', 'low stock', 'limited availability', 'check store', 'available for pickup', 'available for delivery'. Be precise - look for stock status indicators, 'add to cart' buttons (usually means in stock), 'out of stock' messages, or inventory warnings."
                    }
                },
                "required": ["availability"]
            }
            
            response = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: self._client.get_contents(
                    [url],
                    text=True,
                    summary={
                        "query": "Extract the product availability/stock status from this product page. Look for indicators like 'in stock', 'out of stock', 'add to cart', 'sold out', 'available for pickup', 'available for delivery', or inventory warnings. Return the exact availability status.",
                        "schema": availability_schema
                    }
                )
            )
            
            if response and response.results:
                result = response.results[0]
                if hasattr(result, "summary") and result.summary:
                    # Parse the summary JSON to get availability
                    try:
                        summary_data = json.loads(result.summary)
                        exa_availability = summary_data.get("availability", "").strip()
                        if exa_availability:
                            # Normalize the availability value
                            exa_avail_lower = exa_availability.lower()
                            if "out" in exa_avail_lower or "sold out" in exa_avail_lower or "unavailable" in exa_avail_lower:
                                return "Out of Stock"
                            elif "low" in exa_avail_lower or "limited" in exa_avail_lower:
                                return "Low Stock"
                            elif "in stock" in exa_avail_lower or "available" in exa_avail_lower:
                                return "In Stock"
                            else:
                                return exa_availability  # Return as-is if it's a valid status
                    except (json.JSONDecodeError, AttributeError):
                        # If summary is not JSON, try to extract from text
                        pass
            
            return None
        except Exception as e:
            logger.debug(f"Failed to get availability from Exa for {url[:80]}...: {e}")
            return None
    
    def _extract_availability(self, text: str, title: str, url: Optional[str] = None) -> str:
        """
        Extract product availability status from page text content.
        
        Returns one of: "In Stock", "Out of Stock", "Low Stock", "Check Store"
        """
        if not text:
            return "Check Store"
        
        text_lower = text.lower()
        title_lower = title.lower() if title else ""
        combined_text = f"{text_lower} {title_lower}"
        
        # Patterns for out of stock
        out_of_stock_patterns = [
            r'out\s+of\s+stock',
            r'currently\s+unavailable',
            r'not\s+available',
            r'unavailable',
            r'sold\s+out',
            r'no\s+longer\s+available',
            r'discontinued',
            r'temporarily\s+unavailable',
            r'backorder',
            r'pre-order',
        ]
        
        # Patterns for in stock
        in_stock_patterns = [
            r'in\s+stock',
            r'available\s+now',
            r'ready\s+to\s+ship',
            r'add\s+to\s+cart',  # Usually means in stock
            r'buy\s+now',
            r'ships\s+from',
            r'available\s+for',
        ]
        
        # Patterns for low stock
        low_stock_patterns = [
            r'low\s+stock',
            r'only\s+\d+\s+left',
            r'few\s+left',
            r'limited\s+availability',
            r'limited\s+stock',
            r'only\s+\d+\s+in\s+stock',
        ]
        
        # Check for out of stock first (highest priority)
        for pattern in out_of_stock_patterns:
            if re.search(pattern, combined_text, re.IGNORECASE):
                return "Out of Stock"
        
        # Check for low stock
        for pattern in low_stock_patterns:
            if re.search(pattern, combined_text, re.IGNORECASE):
                return "Low Stock"
        
        # Check for in stock
        for pattern in in_stock_patterns:
            if re.search(pattern, combined_text, re.IGNORECASE):
                return "In Stock"
        
        # Store-specific availability indicators
        if url:
            url_lower = url.lower()
            # Target-specific patterns
            if "target.com" in url_lower:
                # Target often shows "Check Store" or "Available for pickup/delivery"
                if any(phrase in text_lower for phrase in ["pickup", "delivery", "shipping"]):
                    return "In Stock"
            
            # Walmart-specific patterns
            if "walmart.com" in url_lower:
                if any(phrase in text_lower for phrase in ["add to cart", "free pickup", "free delivery"]):
                    return "In Stock"
        
        # Default: Check Store (when we can't determine)
        return "Check Store"
    
    async def _extract_product_data(
        self,
        result: Any,
        store_name: Optional[str],
        zipcode: Optional[str],
        extract_images_async: bool = False
    ) -> Optional[Dict[str, Any]]:
        """Extract structured product data from a single result"""
        try:
            import re

            # Get title and URL
            title = getattr(result, "title", "Unknown Product")
            url = getattr(result, "url", None)
            text = getattr(result, "text", "")[:3000] if hasattr(result, "text") else ""
            
            # Try to get Exa summary for better description (if available)
            exa_summary = None
            if hasattr(result, "summary") and result.summary:
                exa_summary = result.summary
                logger.debug(f"✅ Got Exa summary for {title[:50]}")

            # Extract price from text content using regex
            price = None
            # Look for price with dollar sign first
            price_with_dollar = re.search(r'\$(\d+\.\d{2})', text)
            if price_with_dollar:
                try:
                    price = float(price_with_dollar.group(1))
                except:
                    pass

            # If no price found, look for decimal numbers in reasonable range
            if not price:
                all_decimals = re.findall(r'\b(\d+\.\d{2})\b', text)
                for decimal in all_decimals:
                    try:
                        potential_price = float(decimal)
                        if 0.50 <= potential_price <= 500:
                            price = potential_price
                            break
                    except:
                        continue

            # Extract brand from title or text
            brand = None
            common_brands = ["Horizon", "Organic Valley", "Oatly", "Silk", "Chobani", "Target", "365", "Kirkland", "Great Value"]
            for brand_name in common_brands:
                if brand_name.lower() in title.lower() or brand_name.lower() in text.lower():
                    brand = brand_name
                    break

            # Extract quantity/size
            quantity = None
            size_patterns = [
                r'(\d+\.?\d*\s*(?:oz|fl oz|gallon|quart|liter|lb|count|ct|pack))',
                r'(\d+\.?\d*\s*(?:ounce|fluid ounce))',
            ]
            for pattern in size_patterns:
                match = re.search(pattern, text, re.IGNORECASE)
                if match:
                    quantity = match.group(1)
                    break

            # Extract image URLs - prioritize Exa-extracted images
            image_url = None
            
            # Priority 1: Check for image_links in extras (Exa-extracted product images)
            # This is like Exa "right-clicking" the image and copying the URL
            if hasattr(result, "extras") and result.extras:
                # Try both snake_case and camelCase for compatibility
                image_links = getattr(result.extras, "image_links", None) or getattr(result.extras, "imageLinks", None)
                if image_links and len(image_links) > 0:
                    image_url = image_links[0]
                    logger.debug(f"✅ Got image from Exa image_links: {image_url[:80]}...")
            
            # Priority 2: Check Exa's image field (may be thumbnail or page image)
            if not image_url and hasattr(result, "image") and result.image:
                image_url = result.image
                logger.debug(f"✅ Using Exa image field: {image_url[:80]}...")

            # Detect store from URL
            detected_store = store_name
            if url:
                if "target.com" in url:
                    detected_store = "Target"
                    # Fallback: Try to extract Target image URL if Exa didn't provide one
                    if not image_url:
                        # Try to find GUEST ID pattern in text (Target images often have GUEST IDs in HTML)
                        guest_match = re.search(r'GUEST_[a-f0-9\-]+', text, re.IGNORECASE)
                        if guest_match:
                            guest_id = guest_match.group(0)
                            image_url = f"https://target.scene7.com/is/image/Target/{guest_id}?wid=1200&hei=1200&qlt=80"
                        elif extract_images_async:
                            # Only do async extraction if explicitly requested (not during batch processing)
                            try:
                                extracted_image = await self.get_product_image_url(url)
                                if extracted_image:
                                    image_url = extracted_image
                            except Exception as e:
                                logger.debug(f"Failed to extract Target image: {e}")
                elif "walmart.com" in url:
                    detected_store = "Walmart"
                    # Fallback: Try to extract Walmart image URL
                    if not image_url:
                        # Try to find Walmart image pattern in text - be more precise
                        # Match URLs but stop at common delimiters like ), ], }, ", '
                        walmart_img_patterns = [
                            # Match full URL with query params, stopping at ) or other delimiters
                            r'https?://i\d+\.walmartimages\.com/[^\s"\'\)\]\}\s]+\.(?:jpg|jpeg|png|webp|gif)(?:\?[^\s"\'\)\]\}]*)?',
                            # Match without query params
                            r'https?://i\d+\.walmartimages\.com/[^\s"\'\)\]\}]+\.(?:jpg|jpeg|png|webp|gif)',
                        ]
                        for pattern in walmart_img_patterns:
                            walmart_img_match = re.search(pattern, text, re.IGNORECASE)
                            if walmart_img_match:
                                # Extract the match and clean it up
                                raw_url = walmart_img_match.group(0)
                                # Remove trailing punctuation and invalid characters
                                image_url = raw_url.rstrip('.,;!?)').split(')')[0].split(']')[0].split('}')[0].split('"')[0].split("'")[0]
                                # Validate it's still a valid URL
                                if image_url.startswith('http') and '.' in image_url:
                                    logger.debug(f"✅ Extracted Walmart image from text: {image_url[:80]}...")
                                    break
                                else:
                                    image_url = None
                        # If still no image, try async extraction
                        if not image_url and extract_images_async:
                            try:
                                extracted_image = await self.get_product_image_url(url)
                                if extracted_image:
                                    image_url = extracted_image
                                    logger.debug(f"✅ Got Walmart image via async extraction: {image_url[:80]}...")
                            except Exception as e:
                                logger.debug(f"Failed to extract Walmart image: {e}")
                elif "wholefoodsmarket.com" in url:
                    detected_store = "Whole Foods"
                elif "kroger.com" in url:
                    detected_store = "Kroger"
                elif "aldi.us" in url:
                    detected_store = "ALDI"

            # Clean and extract meaningful description
            # Prefer Exa summary (AI-generated, much better quality)
            if exa_summary:
                description = self._clean_exa_summary(exa_summary)
            else:
                # Fallback to text extraction
                description = self._extract_product_description(text, title)
            
            # Extract availability from Exa (preferred) or fallback to text extraction
            availability = None
            
            # Priority 1: Try to get availability from Exa summary if available
            if exa_summary:
                try:
                    # Check if summary contains availability info
                    summary_lower = exa_summary.lower()
                    if any(phrase in summary_lower for phrase in ["in stock", "out of stock", "available", "unavailable", "sold out"]):
                        # Try to extract from summary
                        availability = self._extract_availability(exa_summary, title, url)
                        if availability and availability != "Check Store":
                            logger.debug(f"✅ Got availability from Exa summary: {availability}")
                except Exception as e:
                    logger.debug(f"Failed to extract availability from Exa summary: {e}")
            
            # Priority 2: If not found, try to get from Exa structured extraction (async call)
            if not availability or availability == "Check Store":
                try:
                    exa_availability = await self._get_availability_from_exa(url)
                    if exa_availability:
                        availability = exa_availability
                        logger.debug(f"✅ Got availability from Exa structured extraction: {availability}")
                except Exception as e:
                    logger.debug(f"Failed to get availability from Exa: {e}")
            
            # Priority 3: Fallback to text extraction
            if not availability or availability == "Check Store":
                try:
                    availability = self._extract_availability(text, title, url)
                except Exception as e:
                    logger.debug(f"Failed to extract availability from text: {e}")
                    availability = "Check Store"
            
            # Build product object
            product = {
                "name": title,
                "brand": brand,
                "price": price,
                "currency": "USD",
                "quantity": quantity,
                "availability": availability,
                "image_url": image_url,
                "product_url": url,
                "description": description,
                "category": None,
                "rating": None,
                "reviews_count": None,
                "store_name": detected_store,
                "store_zipcode": zipcode,
                "source": "exa_structured"
            }

            return product

        except Exception as e:
            logger.error(f"❌ Failed to extract product data: {e}")
            return None
    
    async def get_product_image_url(self, product_url: str) -> Optional[str]:
        """
        Extract the actual product image URL from a product page using Exa.
        This is like "right-clicking the image and copying the image URL".
        
        Args:
            product_url: URL of the product page
            
        Returns:
            Direct image URL if found, None otherwise
        """
        if not self.is_available() or not product_url:
            return None
        
        try:
            # Use get_contents to extract image URLs from the product page
            # This is like "right-clicking the image and copying the image URL"
            response = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: self._client.get_contents(
                    [product_url],
                    extras={
                        "image_links": 1  # Get the main product image URL
                    }
                )
            )
            
            if response and response.results:
                result = response.results[0]
                
                # Check for image_links in extras (Exa-extracted product images)
                if hasattr(result, "extras") and result.extras:
                    # Try both snake_case and camelCase for compatibility
                    image_links = getattr(result.extras, "image_links", None) or getattr(result.extras, "imageLinks", None)
                    if image_links and len(image_links) > 0:
                        image_url = image_links[0]
                        logger.info(f"✅ Extracted image URL from {product_url}: {image_url[:80]}...")
                        return image_url
                
                # Fallback: check if Exa returned an image field
                if hasattr(result, "image") and result.image:
                    logger.info(f"✅ Using Exa image field: {result.image[:80]}...")
                    return result.image
            
            return None
            
        except Exception as e:
            logger.debug(f"Failed to extract image URL from {product_url}: {e}")
            return None
    
    async def get_product_images_batch(
        self,
        product_urls: List[str],
        max_concurrent: int = 5
    ) -> Dict[str, Optional[str]]:
        """
        Extract product image URLs from multiple product pages concurrently using Exa.
        More efficient than calling get_product_image_url() multiple times.
        
        Args:
            product_urls: List of product page URLs
            max_concurrent: Maximum concurrent Exa API calls (default: 5 to respect rate limits)
            
        Returns:
            Dictionary mapping product_url -> image_url (or None if not found)
        """
        if not self.is_available() or not product_urls:
            return {url: None for url in product_urls}
        
        results = {}
        semaphore = asyncio.Semaphore(max_concurrent)
        
        async def extract_image(url: str):
            async with semaphore:
                try:
                    image_url = await self.get_product_image_url(url)
                    # Validate image URL if found
                    if image_url:
                        is_valid = await self._validate_image_url(image_url)
                        if is_valid:
                            results[url] = image_url
                        else:
                            logger.debug(f"⚠️ Exa image URL failed validation: {image_url[:80]}...")
                            results[url] = None
                    else:
                        results[url] = None
                except Exception as e:
                    logger.debug(f"Failed to extract image for {url}: {e}")
                    results[url] = None
        
        await asyncio.gather(*[extract_image(url) for url in product_urls])
        return results
    
    async def _validate_image_url(self, image_url: str) -> bool:
        """
        Validate that an image URL actually exists and returns a valid image.
        Uses HTTP HEAD request for efficiency.
        """
        if not image_url or not image_url.startswith('http'):
            return False
        
        try:
            import aiohttp
            async with aiohttp.ClientSession() as session:
                async with session.head(image_url, allow_redirects=True, timeout=aiohttp.ClientTimeout(total=5)) as response:
                    if response.status == 200:
                        content_type = response.headers.get('Content-Type', '').lower()
                        # Check if it's an image content type
                        if content_type.startswith('image/'):
                            return True
                        # Some CDNs don't set content-type correctly, check URL extension
                        if any(ext in image_url.lower() for ext in ['.jpg', '.jpeg', '.png', '.webp', '.gif']):
                            return True
            
            return False
            
        except Exception as e:
            logger.debug(f"Image validation failed for {image_url[:80]}...: {e}")
            return False
    
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
                    extras={
                        "image_links": 1  # Also extract image URL
                    },
                    summary={
                        "query": "Extract comprehensive grocery product details from the product page. Focus on: complete product name and brand, exact price, detailed quantity/size, full description, ingredients list, nutritional facts, allergens, customer ratings and review counts, availability status. Ensure all data is current and accurate from the product page.",
                        "schema": detail_schema
                    }
                )
            )
            
            if response and response.results:
                result = response.results[0]
                # Allow async image extraction for individual product details
                return await self._extract_product_data(result, None, None, extract_images_async=True)
            
            return None
            
        except Exception as e:
            logger.error(f"❌ Failed to get product details: {e}")
            return None
    
    def _get_city_state_from_zipcode(self, zipcode: str) -> tuple:
        """Get city and state from zipcode (basic lookup for common ZIPs)"""
        # Basic ZIP code to city/state mapping for common areas
        zip_mapping = {
            "60601": ("Chicago", "IL"), "60602": ("Chicago", "IL"), "60603": ("Chicago", "IL"),
            "60604": ("Chicago", "IL"), "60605": ("Chicago", "IL"), "60606": ("Chicago", "IL"),
            "60607": ("Chicago", "IL"), "60608": ("Chicago", "IL"), "60609": ("Chicago", "IL"),
            "60610": ("Chicago", "IL"), "60611": ("Chicago", "IL"), "60612": ("Chicago", "IL"),
            "60613": ("Chicago", "IL"), "60614": ("Chicago", "IL"), "60615": ("Chicago", "IL"),
            "60616": ("Chicago", "IL"), "60617": ("Chicago", "IL"), "60618": ("Chicago", "IL"),
            "60619": ("Chicago", "IL"), "60620": ("Chicago", "IL"), "60621": ("Chicago", "IL"),
            "60622": ("Chicago", "IL"), "60623": ("Chicago", "IL"), "60624": ("Chicago", "IL"),
            "60625": ("Chicago", "IL"), "60626": ("Chicago", "IL"), "60628": ("Chicago", "IL"),
            "60629": ("Chicago", "IL"), "60630": ("Chicago", "IL"), "60631": ("Chicago", "IL"),
            "60632": ("Chicago", "IL"), "60633": ("Chicago", "IL"), "60634": ("Chicago", "IL"),
            "60636": ("Chicago", "IL"), "60637": ("Chicago", "IL"), "60638": ("Chicago", "IL"),
            "60639": ("Chicago", "IL"), "60640": ("Chicago", "IL"), "60641": ("Chicago", "IL"),
            "60642": ("Chicago", "IL"), "60643": ("Chicago", "IL"), "60644": ("Chicago", "IL"),
            "60645": ("Chicago", "IL"), "60646": ("Chicago", "IL"), "60647": ("Chicago", "IL"),
            "60649": ("Chicago", "IL"), "60651": ("Chicago", "IL"), "60652": ("Chicago", "IL"),
            "60653": ("Chicago", "IL"), "60654": ("Chicago", "IL"), "60655": ("Chicago", "IL"),
            "60656": ("Chicago", "IL"), "60657": ("Chicago", "IL"), "60659": ("Chicago", "IL"),
            "60660": ("Chicago", "IL"), "60661": ("Chicago", "IL"),
            "10001": ("New York", "NY"), "10002": ("New York", "NY"), "10003": ("New York", "NY"),
            "10004": ("New York", "NY"), "10005": ("New York", "NY"),
            "38125": ("Memphis", "TN"), "38103": ("Memphis", "TN"), "38104": ("Memphis", "TN"),
            "38105": ("Memphis", "TN"), "38106": ("Memphis", "TN"), "38107": ("Memphis", "TN"),
            "38108": ("Memphis", "TN"), "38109": ("Memphis", "TN"), "38111": ("Memphis", "TN"),
            "38112": ("Memphis", "TN"), "38113": ("Memphis", "TN"), "38114": ("Memphis", "TN"),
            "38115": ("Memphis", "TN"), "38116": ("Memphis", "TN"), "38117": ("Memphis", "TN"),
            "38118": ("Memphis", "TN"), "38119": ("Memphis", "TN"), "38120": ("Memphis", "TN"),
            "38122": ("Memphis", "TN"), "38126": ("Memphis", "TN"), "38127": ("Memphis", "TN"),
            "38128": ("Memphis", "TN"), "38130": ("Memphis", "TN"), "38131": ("Memphis", "TN"),
            "38132": ("Memphis", "TN"), "38133": ("Memphis", "TN"), "38134": ("Memphis", "TN"),
            "38135": ("Memphis", "TN"), "38138": ("Memphis", "TN"), "38139": ("Memphis", "TN"),
            "90001": ("Los Angeles", "CA"), "90002": ("Los Angeles", "CA"),
            "94102": ("San Francisco", "CA"), "94103": ("San Francisco", "CA"),
            "02108": ("Boston", "MA"), "02109": ("Boston", "MA"),
        }
        return zip_mapping.get(zipcode, (None, None))

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
            # Get default city/state from zipcode
            default_city, default_state = self._get_city_state_from_zipcode(zipcode)
            # Build store location search query - explicitly request full address information
            # Make it very clear we need complete address details
            if default_city and default_state:
                search_query = f"{store_chain} store locations in {default_city} {default_state} zipcode {zipcode} with complete address details: street number, street name, city, state, zipcode. Find store location pages that show the full physical address near {zipcode}"
            else:
                search_query = f"{store_chain} store locations in zipcode {zipcode} area with complete address details: street number, street name, city, state, zipcode. Find store location pages that show the full physical address near zipcode {zipcode}"
            domain = self._get_store_domain(store_chain)
            
            # Define store location schema
            store_schema = {
                "type": "object",
                "properties": {
                    "store_name": {"type": "string"},
                    "address": {"type": "string", "description": "Complete street address with street number and name (e.g., '95 E Houston St')"},
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
                "text": {"max_characters": 5000}  # Get more text to find address information
            }

            if domain:
                search_options["include_domains"] = [domain]
            
            response = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: self._client.search_and_contents(**search_options)
            )
            
            stores = []
            for result in getattr(response, "results", []):
                # Extract address info from text content
                import re
                # Get more text to find address information (increased from 2000 to 5000)
                text = getattr(result, "text", "")[:5000] if hasattr(result, "text") else ""
                title = getattr(result, "title", "")
                url = getattr(result, "url", "")
                
                # Log for debugging
                logger.debug(f"Processing store location result: {title[:80]}... | URL: {url[:80]}...")

                # Initialize address variables
                address = None
                city = None
                state = None
                store_zip = zipcode
                retailer_store_id = None
                
                # Try to get structured address data using get_contents if URL is available
                # This gives us better structured data extraction with explicit prompts
                if url:
                    try:
                        detail_response = await asyncio.get_event_loop().run_in_executor(
                            None,
                            lambda: self._client.get_contents(
                                [url],
                                text={"max_characters": 5000},
                                summary={
                                    "query": f"Extract the complete store address for this {store_chain} store location. Find the full street address including street number, street name, city, state, and zipcode. Format should be like '95 E Houston St, New York, NY 10002'. Also extract the retailer store ID if available.",
                                    "schema": {
                                        "type": "object",
                                        "properties": {
                                            "address": {"type": "string", "description": "Complete street address with number and name (e.g., '95 E Houston St')"},
                                            "city": {"type": "string"},
                                            "state": {"type": "string"},
                                            "zipcode": {"type": "string"},
                                            "retailer_store_id": {"type": "string", "description": "Store ID number if available"}
                                        }
                                    }
                                }
                            )
                        )
                        
                        if detail_response and detail_response.results:
                            detail_result = detail_response.results[0]
                            # Get enhanced text from detailed response
                            detail_text = getattr(detail_result, "text", "")[:5000] if hasattr(detail_result, "text") else ""
                            if detail_text:
                                text = detail_text  # Use detailed text for extraction
                            
                            # Try to parse structured data from summary if available
                            if hasattr(detail_result, "summary") and detail_result.summary:
                                import json
                                try:
                                    # Summary might be JSON or structured text
                                    summary_text = detail_result.summary
                                    logger.debug(f"Got summary from Exa: {summary_text[:200]}...")
                                    
                                    # Try to extract JSON from summary - handle nested objects
                                    # Look for JSON object with multiple lines
                                    json_match = re.search(r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}', summary_text, re.DOTALL)
                                    if json_match:
                                        try:
                                            parsed_data = json.loads(json_match.group(0))
                                            logger.debug(f"Parsed JSON data: {parsed_data}")
                                            if parsed_data.get("address"):
                                                address = parsed_data["address"]
                                                logger.debug(f"✅ Extracted address from summary: {address}")
                                            if parsed_data.get("city"):
                                                city = parsed_data["city"]
                                            if parsed_data.get("state"):
                                                state = parsed_data["state"]
                                            if parsed_data.get("zipcode"):
                                                store_zip = parsed_data["zipcode"]
                                            if parsed_data.get("retailer_store_id"):
                                                retailer_store_id = parsed_data["retailer_store_id"]
                                                logger.debug(f"✅ Extracted retailer_store_id from summary: {retailer_store_id}")
                                        except json.JSONDecodeError:
                                            # Try to extract values using regex if JSON parsing fails
                                            address_match = re.search(r'"address"\s*:\s*"([^"]+)"', summary_text)
                                            if address_match:
                                                address = address_match.group(1)
                                            city_match = re.search(r'"city"\s*:\s*"([^"]+)"', summary_text)
                                            if city_match:
                                                city = city_match.group(1)
                                            state_match = re.search(r'"state"\s*:\s*"([^"]+)"', summary_text)
                                            if state_match:
                                                state = state_match.group(1)
                                            zipcode_match = re.search(r'"zipcode"\s*:\s*"([^"]+)"', summary_text)
                                            if zipcode_match:
                                                store_zip = zipcode_match.group(1)
                                            store_id_match = re.search(r'"retailer_store_id"\s*:\s*"([^"]+)"', summary_text)
                                            if store_id_match:
                                                retailer_store_id = store_id_match.group(1)
                                except Exception as parse_error:
                                    logger.debug(f"Could not parse summary: {parse_error}")
                                    # Continue with text extraction
                    except Exception as e:
                        logger.debug(f"Failed to get detailed address for {url}: {e}")

                # Extract full address from text (using enhanced text from get_contents if available)
                # Look for address patterns like "123 Main St, City, ST 12345"
                # Improved pattern to handle various address formats
                address_patterns = [
                    # Full address with directional: "95 E Houston St, New York, NY 10002"
                    r'(\d+\s+[NSEWnsew]\.?\s+[A-Za-z\s]+(?:Street|St|Avenue|Ave|Road|Rd|Boulevard|Blvd|Drive|Dr|Lane|Ln|Way|Court|Ct|Place|Pl|Parkway|Pkwy)[.,]?)\s*[,\s]+\s*([A-Za-z][A-Za-z\s]+?)\s*,\s*([A-Z]{2})\s+(\d{5})',
                    # Full address: "123 Main St, City, ST 12345" or "95 E Houston St, New York, NY 10002"
                    r'(\d+\s+[A-Za-z\s\.]+(?:Street|St|Avenue|Ave|Road|Rd|Boulevard|Blvd|Drive|Dr|Lane|Ln|Way|Court|Ct|Place|Pl|Parkway|Pkwy)[.,]?)\s*[,\s]+\s*([A-Za-z][A-Za-z\s]+?)\s*,\s*([A-Z]{2})\s+(\d{5})',
                    # Address with abbreviations: "95 E Houston St, New York, NY 10002"
                    r'(\d+\s+[A-Za-z\s\.]+(?:St|Ave|Rd|Blvd|Dr|Ln)[.,]?)\s*[,\s]+\s*([A-Za-z][A-Za-z\s]+?)\s*,\s*([A-Z]{2})\s+(\d{5})',
                    # Address with directional only: "95 E Houston St"
                    r'(\d+\s+[NSEWnsew]\.?\s+[A-Za-z\s]+(?:St|Street|Ave|Avenue|Rd|Road|Blvd|Boulevard|Dr|Drive|Ln|Lane)[.,]?)',
                    # Address without directional: "95 Houston St"
                    r'(\d+\s+[A-Za-z\s]+(?:St|Street|Ave|Avenue|Rd|Road|Blvd|Boulevard|Dr|Drive|Ln|Lane)[.,]?)',
                    # Without full address: "City, ST 12345"
                    r'([A-Za-z][A-Za-z\s]+?)\s*,\s*([A-Z]{2})\s+(\d{5})',
                ]
                
                for pattern in address_patterns:
                    match = re.search(pattern, text)
                    if match:
                        if len(match.groups()) == 4:  # Full address pattern
                            potential_address = match.group(1).strip()
                            potential_city = match.group(2).strip()
                            potential_state = match.group(3).strip()
                            potential_zip = match.group(4)
                            
                            # Only use if it looks like a valid address
                            if not address and re.match(r'^\d+\s+[A-Za-z]', potential_address):
                                address = potential_address.rstrip(',. ')  # Clean trailing punctuation
                            if not city:
                                city = potential_city
                            if not state:
                                state = potential_state
                            if not store_zip or store_zip == zipcode:
                                store_zip = potential_zip
                        elif len(match.groups()) == 3:  # City, state pattern
                            if not city:
                                city = match.group(1).strip()
                            if not state:
                                state = match.group(2).strip()
                            if not store_zip or store_zip == zipcode:
                                store_zip = match.group(3)
                        elif len(match.groups()) == 1:  # Just address
                            potential_address = match.group(1).strip()
                            if not address and re.match(r'^\d+\s+[A-Za-z]', potential_address):
                                address = potential_address.rstrip(',. ')  # Clean trailing punctuation
                        break

                # Extract from title if available (e.g., "Target - Chicago" or "Whole Foods Market Bowery")
                if not city and " - " in title:
                    parts = title.split(" - ")
                    if len(parts) > 1:
                        location_part = parts[1].strip()
                        # Clean up location - remove duplicates like "New YorkNew York"
                        location_part = re.sub(r'([A-Z][a-z]+)\1', r'\1', location_part)
                        city = location_part
                
                # Also check for store name patterns like "Whole Foods Market Bowery" or "Target - Lower East Side"
                if "Whole Foods" in title or "whole foods" in title.lower():
                    # Try to extract location from title
                    title_lower = title.lower()
                    if "bowery" in title_lower:
                        city = "New York"
                        # Try to extract Bowery address (95 E Houston St)
                        bowery_address = re.search(r'(\d+\s+[Ee]\.?\s+[Hh]ouston\s+[Ss]t)', text, re.IGNORECASE)
                        if bowery_address:
                            address = bowery_address.group(1).strip()
                    elif "east houston" in title_lower or "e houston" in title_lower:
                        city = "New York"
                        # Extract street name for address - try multiple patterns
                        street_patterns = [
                            r'(\d+\s+[Ee]\.?\s+[Hh]ouston\s+[Ss]t)',  # "95 E Houston St"
                            r'(\d+\s+[Ee]ast\s+[Hh]ouston\s+[Ss]t)',  # "95 East Houston St"
                            r'(\d+\s+[Ee]\.?\s+[Hh]ouston)',  # "95 E Houston"
                        ]
                        for pattern in street_patterns:
                            street_match = re.search(pattern, text, re.IGNORECASE)
                            if street_match:
                                address = street_match.group(1).strip()
                                break

                # Clean up city name - remove any street name parts that got mixed in
                if city:
                    # Remove common street suffixes if they appear at the start
                    city = re.sub(r'^(East|West|North|South|Upper|Lower)\s+([A-Za-z]+)\s+(St|Street|Ave|Avenue)', '', city, flags=re.IGNORECASE)
                    # Remove duplicates like "New YorkNew York" -> "New York"
                    city = re.sub(r'([A-Z][a-z]+)\1', r'\1', city)
                    # Remove trailing street names
                    city = re.sub(r'\s+(St|Street|Ave|Avenue|Rd|Road)\s*$', '', city, flags=re.IGNORECASE)
                    city = city.strip()

                # Use default city/state if not found
                if not city or len(city) < 2:
                    city = default_city
                if not state:
                    state = default_state

                # Try to extract retailer_store_id from URL or text if not already found
                if not retailer_store_id and url:
                    # Whole Foods: look for store ID in URL or text
                    if "wholefoodsmarket.com" in url:
                        # Whole Foods URLs might have store IDs
                        store_id_match = re.search(r'store[_-]?id[=:]?(\d+)', text, re.IGNORECASE)
                        if store_id_match:
                            retailer_store_id = store_id_match.group(1)
                        # Or try to extract from URL
                        url_match = re.search(r'/stores/(\d+)', url, re.IGNORECASE)
                        if url_match:
                            retailer_store_id = url_match.group(1)
                    
                    # Target: extract store number
                    elif "target.com" in url:
                        store_num_match = re.search(r'store[_-]?(\d+)', text, re.IGNORECASE)
                        if store_num_match:
                            retailer_store_id = store_num_match.group(1)
                    
                    # Walmart: extract store number
                    elif "walmart.com" in url:
                        store_num_match = re.search(r'store[_-]?(\d+)', text, re.IGNORECASE)
                        if store_num_match:
                            retailer_store_id = store_num_match.group(1)
                
                # Build store name - try to get specific location name
                location_name = store_chain
                
                # Extract location identifier from title (e.g., "Bowery", "Lower East Side", etc.)
                location_identifier = None
                
                # Check for Whole Foods specific patterns
                if "whole foods" in store_chain.lower() or "wholefoods" in store_chain.lower():
                    # Look for location identifiers in title
                    if "bowery" in title.lower():
                        location_identifier = "Bowery"
                    elif "east houston" in title.lower():
                        # Extract street address for name
                        street_match = re.search(r'(\d+\s+[Ee]ast\s+[Hh]ouston)', text, re.IGNORECASE)
                        if street_match:
                            location_identifier = street_match.group(1).strip()
                        else:
                            location_identifier = "East Houston"
                    elif " - " in title:
                        parts = title.split(" - ")
                        if len(parts) > 1:
                            location_identifier = parts[1].strip()
                            # Clean up location identifier
                            location_identifier = re.sub(r'New York.*', '', location_identifier, flags=re.IGNORECASE)
                            location_identifier = location_identifier.strip()
                
                # For other stores, extract from title
                elif " - " in title:
                    parts = title.split(" - ")
                    if len(parts) > 1:
                        location_identifier = parts[1].strip()
                        # Remove city name if it's duplicated
                        location_identifier = re.sub(r'\s*New York.*$', '', location_identifier, flags=re.IGNORECASE)
                        location_identifier = location_identifier.strip()
                
                # Build final store name
                if location_identifier:
                    location_name = f"{store_chain} {location_identifier}"
                elif city and city != default_city and city != "New York":
                    location_name = f"{store_chain} {city}"
                elif city == "New York" and address:
                    # Use address for location if we have it
                    location_name = f"{store_chain} {address}"
                
                stores.append({
                    "store_id": store_chain.lower().replace(" ", "_"),
                    "retailer_store_id": retailer_store_id,
                    "store_name": location_name,
                    "address": address.rstrip(',. ') if address else None,  # Clean trailing punctuation
                    "city": city,
                    "state": state,
                    "zipcode": store_zip,
                    "phone": None,
                    "hours": None,
                    "services": ["in-store"],
                    "status": "active",
                    "source": "exa_structured"
                })
            
            logger.info(f"✅ Found {len(stores)} {store_chain} locations near {zipcode}")
            return stores
            
        except Exception as e:
            logger.error(f"❌ Store location search failed: {e}")
            return []

