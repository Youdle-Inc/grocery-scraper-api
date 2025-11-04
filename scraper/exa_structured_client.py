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
        # For better product results, make query more specific
        # Add common product variations to get individual product pages
        if store_name and store_name != "grocery store":
            if len(query.split()) == 1:  # Single word like "milk"
                # Expand to find specific products
                base_query = f"{query} gallon {store_name} product"
            else:
                base_query = f"{query} {store_name}"
        else:
            if len(query.split()) == 1:
                base_query = f"{query} gallon grocery product"
            else:
                base_query = f"{query} grocery"

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

        # Filter out search and category pages
        exclude_patterns = [
            '/s/',  # Target search pages
            '/c/',  # Target category pages
            '/browse/',  # Walmart browse pages
            '?Nao=',  # Pagination
            'Page ',  # Page indicators in title
        ]

        for pattern in exclude_patterns:
            if pattern in url or pattern in title:
                return False

        # Check for product page indicators
        product_indicators = [
            '/p/',  # Target product pages
            '/ip/',  # Walmart individual product pages
            '/A-',  # Target product ID
        ]

        for indicator in product_indicators:
            if indicator in url:
                return True

        return False

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
                    # Check if this is an actual product page
                    url = getattr(result, "url", "")
                    title = getattr(result, "title", "")

                    if not self._is_product_page(url, title):
                        logger.debug(f"Skipping non-product page: {title}")
                        continue

                    product = self._extract_product_data(result, store_name, zipcode)
                    if product:
                        products.append(product)
                except Exception as e:
                    logger.warning(f"⚠️ Failed to process result: {e}")
                    continue

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
    
    def _extract_product_data(
        self,
        result: Any,
        store_name: Optional[str],
        zipcode: Optional[str]
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

            # Extract image URLs
            image_url = None
            if hasattr(result, "image") and result.image:
                image_url = result.image

            # Detect store from URL and generate image if possible
            detected_store = store_name
            if url:
                if "target.com" in url:
                    detected_store = "Target"
                    # Generate Target product image from URL
                    # Target URLs format: /p/product-name/-/A-12345678
                    if not image_url:
                        match = re.search(r'/A-(\d+)', url)
                        if match:
                            product_id = match.group(1)
                            # Target Scene7 image CDN format
                            image_url = f"https://target.scene7.com/is/image/Target/{product_id}?wid=800&hei=800&qlt=80&fmt=webp"
                elif "walmart.com" in url:
                    detected_store = "Walmart"
                    # Try to extract Walmart product ID and construct image
                    if not image_url:
                        match = re.search(r'/ip/[^/]+/(\d+)', url)
                        if match:
                            product_id = match.group(1)
                            # Walmart image CDN format (may not always work)
                            image_url = f"https://i5.walmartimages.com/asr/{product_id}"
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
            
            # Build product object
            product = {
                "name": title,
                "brand": brand,
                "price": price,
                "currency": "USD",
                "quantity": quantity,
                "availability": "Check Store",
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
                "text": True
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
                text = getattr(result, "text", "")[:2000] if hasattr(result, "text") else ""
                title = getattr(result, "title", "")

                # Try to extract full address from text
                address = None
                city = None
                state = None
                store_zip = zipcode

                # Look for address patterns like "123 Main St, City, ST 12345"
                address_pattern = r'(\d+\s+[A-Za-z\s]+(?:Street|St|Avenue|Ave|Road|Rd|Boulevard|Blvd|Drive|Dr|Lane|Ln|Way|Court|Ct|Place|Pl)[.,]?\s*(?:#\d+)?)[,\s]+([A-Za-z\s]+)[,\s]+([A-Z]{2})\s+(\d{5})'
                match = re.search(address_pattern, text)
                if match:
                    address = match.group(1).strip()
                    city = match.group(2).strip()
                    state = match.group(3).strip()
                    store_zip = match.group(4)
                else:
                    # Try simpler pattern for city, state
                    city_state_pattern = r'([A-Za-z\s]+),\s*([A-Z]{2})\s+(\d{5})'
                    match = re.search(city_state_pattern, text)
                    if match:
                        city = match.group(1).strip()
                        state = match.group(2).strip()
                        store_zip = match.group(3)

                # Extract from title if available (e.g., "Target - Chicago")
                if not city and " - " in title:
                    parts = title.split(" - ")
                    if len(parts) > 1:
                        city = parts[1].strip()

                # Use default city/state if not found
                if not city:
                    city = default_city
                if not state:
                    state = default_state

                stores.append({
                    "store_id": store_chain.lower().replace(" ", "_"),
                    "store_name": store_chain,
                    "address": address,
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

