"""
Perplexity Sonar client for dynamic store discovery
Enhanced implementation with proper API formatting and error handling
"""

import os
import logging
import asyncio
from typing import List, Dict, Optional, Any
from datetime import datetime, timedelta
import json
import re

import requests
from requests.exceptions import RequestException, Timeout
from dotenv import load_dotenv

from .models import StoreLocation
from .google_image_search import GoogleImageSearch
from .hybrid_scraper import HybridScraper

# Load environment variables from .env file
load_dotenv()

logger = logging.getLogger(__name__)

class SonarClient:
    """Enhanced client for Perplexity Sonar API"""
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.environ.get("PERPLEXITY_API_KEY")
        self._cache = {}
        self._cache_duration = timedelta(hours=1)  # Cache for 1 hour
        self.base_url = "https://api.perplexity.ai/chat/completions"
        
        if not self.api_key:
            logger.warning("⚠️ No Perplexity API key found. Sonar features will be disabled.")
            return
            
        logger.info("✅ Perplexity Sonar client initialized")
    
    def is_available(self) -> bool:
        """Check if Sonar client is available"""
        return self.api_key is not None
    
    async def search_stores(self, zipcode: str) -> List[StoreLocation]:
        """Search for grocery stores in a zipcode using Sonar"""
        if not self.is_available():
            logger.warning("Sonar client not available, using fallback")
            return []
        
        # Check cache first
        cache_key = f"stores_{zipcode}"
        if cache_key in self._cache:
            cached_data = self._cache[cache_key]
            if datetime.now() - cached_data["timestamp"] < self._cache_duration:
                logger.info(f"Using cached store data for {zipcode}")
                return cached_data["stores"]
        
        try:
            # Create Sonar query
            query = self._create_store_query(zipcode)
            logger.info(f"🔍 Searching Sonar for stores in {zipcode}")
            
            # Make Sonar request
            response_data = await self._make_sonar_request(query)
            
            # Parse response
            stores = self._parse_store_response(response_data["content"], zipcode)
            
            # Cache the results
            self._cache[cache_key] = {
                "stores": stores,
                "timestamp": datetime.now()
            }
            
            logger.info(f"✅ Found {len(stores)} stores via Sonar for {zipcode}")
            return stores
            
        except Exception as e:
            logger.error(f"❌ Sonar search failed for {zipcode}: {e}")
            return []
    
    async def get_store_details(self, store_name: str, location: str) -> Dict[str, Any]:
        """Get detailed information about a specific store"""
        if not self.is_available():
            return {}
        
        try:
            query = f"""Find detailed information about {store_name} in {location}. 
            Please provide:
            1. Current store hours (day by day)
            2. Available services (delivery, pickup, curbside, in-store shopping)
            3. Contact information (phone number, website)
            4. Store address
            5. Any special features or notes
            
            Format the response as structured data."""
            
            response_data = await self._make_sonar_request(query)
            return self._parse_store_details(response_data["content"])
            
        except Exception as e:
            logger.error(f"❌ Failed to get store details for {store_name}: {e}")
            return {}
    
    async def search_products(self, query: str, store_name: str, location: str, enhance: bool = False) -> List[Dict[str, Any]]:
        """Search for products at a specific store using Sonar"""
        if not self.is_available():
            return []
        
        try:
            search_query = f"""Find current product information for "{query}" at {store_name} in {location}.

IMPORTANT: Include product image URLs when available. Search for actual product images from the store's website or product listings.

Return results in this EXACT format (one product per section, separated by blank lines):

PRODUCT: [Product Name]
BRAND: [Brand Name]
PRICE: [Price with $ symbol, or "Price not available"]
SIZE: [Size/quantity, e.g., "32 oz", "1 gallon", "12 pack"]
CATEGORY: [Product category, e.g., "Dairy", "Beverages", "Organic"]
AVAILABILITY: [in stock/out of stock/limited]
DESCRIPTION: [Brief product description]
IMAGE_URL: [Actual product image URL from store website, or "N/A" if not found]
DEALS: [Any current deals, discounts, or "None"]

Example format:
PRODUCT: Oatly Oat Milk Original
BRAND: Oatly
PRICE: $4.99
SIZE: 64 oz
CATEGORY: Dairy Alternatives
AVAILABILITY: in stock
DESCRIPTION: Original oat milk, creamy and delicious
IMAGE_URL: https://target.scene7.com/is/image/Target/12345678
DEALS: Buy 2 get 1 free

PRODUCT: Chobani Oat Milk
BRAND: Chobani
PRICE: $3.99
SIZE: 52 oz
CATEGORY: Dairy Alternatives
AVAILABILITY: in stock
DESCRIPTION: Zero sugar oat milk
IMAGE_URL: https://www.target.com/p/chobani-oat-milk/-/A-12345678
DEALS: 20% off this week

CRITICAL: Always include the IMAGE_URL field for each product. Search the store's website or product listings to find actual image URLs. If you cannot find a specific image URL, use "N/A" but still include the IMAGE_URL field.

Focus on current availability, accurate pricing, and finding actual product images from the store's website."""
            
            response_data = await self._make_sonar_request(search_query)
            
            # Debug the response data structure
            logger.info(f"🔍 Response data type: {type(response_data)}")
            if isinstance(response_data, dict):
                logger.info(f"🔍 Response data keys: {list(response_data.keys())}")
            else:
                logger.info(f"🔍 Response data is not a dict: {response_data[:100] if isinstance(response_data, str) else str(response_data)[:100]}")
            
            # Handle both old and new response formats
            if isinstance(response_data, dict):
                content = response_data.get("content", "")
                citations = response_data.get("citations", [])
                search_results = response_data.get("search_results", [])
            else:
                # Fallback to old format (string response)
                content = response_data
                citations = []
                search_results = []
            
            products = self._parse_product_response(content)
            
            logger.info(f"🔍 Response data keys: {list(response_data.keys())}")
            logger.info(f"🔍 Citations count: {len(citations)}")
            logger.info(f"🔍 Search results count: {len(search_results)}")
            if citations:
                logger.info(f"🔍 Sample citations: {citations[:2]}")
            if search_results:
                logger.info(f"🔍 Sample search results: {search_results[:2]}")
            
            real_urls = self._extract_real_product_urls(citations, search_results)
            
            # Debug logging
            logger.info(f"🔍 Found {len(real_urls)} real URLs: {list(real_urls.keys())}")
            logger.info(f"🔍 Products to match: {[p.get('name', '') for p in products]}")
            
            # Enhance products with real URLs
            products = self._enhance_products_with_real_urls(products, real_urls)
            
            # Enhance products with hybrid scraping (images + additional data) - OPTIONAL
            # Only enable if explicitly requested
            if enhance:
                try:
                    logger.info("🔍 Enhancing products with hybrid scraping...")
                    
                    # First try Google image search if available
                    google_searcher = GoogleImageSearch()
                    if google_searcher.is_available():
                        logger.info("🖼️ Adding Google image search...")
                        products = await google_searcher.enhance_products_with_images(products)
                    
                    # Then enhance with store-specific scraping
                    hybrid_scraper = HybridScraper()
                    products = await hybrid_scraper.enhance_products(products, store_name)
                    
                    logger.info("✅ Hybrid enhancement completed")
                    
                except Exception as e:
                    logger.warning(f"⚠️ Hybrid enhancement failed: {e}")
            else:
                logger.info("⚡ Hybrid scraping disabled - use ?enhance=true to enable")
            
            return products
            
        except Exception as e:
            logger.error(f"❌ Failed to search products for {query} at {store_name}: {e}")
            return []
    
    def _extract_real_product_urls(self, citations: List[str], search_results: List[Dict[str, Any]]) -> Dict[str, str]:
        """Extract real product URLs from Perplexity API response"""
        real_urls = {}
        
        # Extract from citations
        for citation in citations:
            if "target.com/p/" in citation or "walmart.com/ip/" in citation or "amazon.com/dp/" in citation:
                # Extract product name from URL
                product_name = self._extract_product_name_from_url(citation)
                if product_name:
                    real_urls[product_name.lower()] = citation
        
        # Extract from search results
        for result in search_results:
            url = result.get("url", "")
            if "target.com/p/" in url or "walmart.com/ip/" in url or "amazon.com/dp/" in url:
                product_name = self._extract_product_name_from_url(url)
                if product_name:
                    real_urls[product_name.lower()] = url
        
        logger.info(f"🔗 Found {len(real_urls)} real product URLs")
        return real_urls
    
    def _extract_product_name_from_url(self, url: str) -> str:
        """Extract product name from store URL"""
        try:
            if "target.com/p/" in url:
                # Extract from Target URL: /p/product-name/-/A-123456
                parts = url.split("/p/")
                if len(parts) > 1:
                    product_part = parts[1].split("/-/")[0]
                    return product_part.replace("-", " ").title()
            
            elif "walmart.com/ip/" in url:
                # Extract from Walmart URL: /ip/product-name/123456
                parts = url.split("/ip/")
                if len(parts) > 1:
                    product_part = parts[1].split("/")[0]
                    return product_part.replace("-", " ").title()
            
            elif "amazon.com/dp/" in url:
                # For Amazon, we'll use the ASIN as the identifier
                parts = url.split("/dp/")
                if len(parts) > 1:
                    asin = parts[1].split("/")[0]
                    return f"Amazon Product {asin}"
        
        except Exception as e:
            logger.debug(f"Failed to extract product name from URL {url}: {e}")
        
        return ""
    
    def _enhance_products_with_real_urls(self, products: List[Dict[str, Any]], real_urls: Dict[str, str]) -> List[Dict[str, Any]]:
        """Enhance products with real URLs from Perplexity API"""
        enhanced_products = []
        
        for product in products:
            enhanced_product = product.copy()
            product_name = product.get("name", "").lower()
            
            # Try to find matching real URL with improved matching
            best_match = None
            best_score = 0
            
            for url_key, real_url in real_urls.items():
                # Calculate similarity score
                product_words = set(product_name.split())
                url_words = set(url_key.split())
                
                # Count common words
                common_words = product_words.intersection(url_words)
                score = len(common_words) / max(len(product_words), len(url_words))
                
                if score > best_score and score > 0.3:  # At least 30% match
                    best_score = score
                    best_match = real_url
            
            if best_match:
                enhanced_product["product_url"] = best_match
                
                # Try to extract image URL from the same source
                if "target.com" in best_match:
                    # Extract Target product ID and create image URL
                    if "/A-" in best_match:
                        product_id = best_match.split("/A-")[1].split("/")[0]
                        enhanced_product["image_url"] = f"https://target.scene7.com/is/image/Target/{product_id}?wid=1200&hei=1200&qlt=80&fmt=webp"
                
                elif "walmart.com" in best_match:
                    # Extract Walmart product ID and create image URL
                    if "/ip/" in best_match:
                        product_id = best_match.split("/ip/")[1].split("/")[1]
                        enhanced_product["image_url"] = f"https://i5.walmartimages.com/asr/{product_id}.jpeg"
            
            enhanced_products.append(enhanced_product)
        
        return enhanced_products
    
    def _create_store_query(self, zipcode: str) -> str:
        """Create a Sonar query for finding grocery stores"""
        return f"""Find all grocery stores and supermarkets serving zip code {zipcode}.

Return results in this EXACT format (one store per section, separated by blank lines):

STORE: [Store Name]
ADDRESS: [Complete street address with city, state, zip]
SERVICES: [comma-separated list: delivery, pickup, curbside, in-store]
WEBSITE: [full URL if available, or "N/A"]
STATUS: [open/closed/temporarily closed]

Example format:
STORE: Giant Eagle
ADDRESS: 123 Main Street, Pittsburgh, PA 15213
SERVICES: delivery, pickup, curbside, in-store
WEBSITE: https://www.gianteagle.com
STATUS: open

STORE: Walmart
ADDRESS: 456 Oak Avenue, Pittsburgh, PA 15213
SERVICES: delivery, pickup, curbside, in-store
WEBSITE: https://www.walmart.com
STATUS: open

Focus on major chains: Walmart, Target, Kroger, Safeway, Publix, Whole Foods, Trader Joe's, ALDI, Wegmans, Giant Eagle, Meijer, Hy-Vee, Food Lion, Stop & Shop, and local grocery stores. Provide accurate addresses and current service availability."""
    
    async def _make_sonar_request(self, query: str) -> str:
        """Make a request to Perplexity Sonar API with proper error handling"""
        try:
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            
            # Use the latest Sonar model
            data = {
        'model': 'sonar',               
          "messages": [
                    {
                        "role": "user",
                        "content": query
                    }
                ],
                "max_tokens": 2048,
                "temperature": 0.1,  # Lower temperature for more consistent results
                "top_p": 0.9,
                "stream": False
            }
            
            # Make the request with timeout
            response = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: requests.post(
                    self.base_url, 
                    headers=headers, 
                    json=data, 
                    timeout=45
                )
            )
            
            # Handle different response status codes
            if response.status_code == 200:
                result = response.json()
                if "choices" in result and len(result["choices"]) > 0:
                    # Return both content and metadata (citations, search_results)
                    return {
                        "content": result["choices"][0]["message"]["content"],
                        "citations": result.get("citations", []),
                        "search_results": result.get("search_results", [])
                    }
                else:
                    raise Exception("Invalid response format from Perplexity API")
                    
            elif response.status_code == 401:
                raise Exception("Invalid API key - please check your Perplexity API key")
            elif response.status_code == 429:
                raise Exception("Rate limit exceeded - please wait before making more requests")
            elif response.status_code == 400:
                error_msg = response.json().get("error", {}).get("message", "Bad request")
                raise Exception(f"Bad request: {error_msg}")
            else:
                raise Exception(f"API error: {response.status_code} - {response.text}")
                
        except Timeout:
            logger.error("❌ Request timeout")
            raise Exception("Request timeout - please try again")
        except RequestException as e:
            logger.error(f"❌ Network error: {e}")
            raise Exception(f"Network error: {e}")
        except Exception as e:
            logger.error(f"❌ Sonar request failed: {e}")
            raise
    
    def _parse_store_response(self, response: str, zipcode: str) -> List[StoreLocation]:
        """Enhanced parsing of Sonar response to extract store information"""
        stores = []
        
        try:
            # First, try to extract structured data
            stores = self._extract_structured_stores(response, zipcode)
            
            # If no structured data found, fall back to pattern matching
            if not stores:
                stores = self._extract_stores_by_patterns(response, zipcode)
            
            # Remove duplicates based on store_id
            unique_stores = {}
            for store in stores:
                if store.store_id not in unique_stores:
                    unique_stores[store.store_id] = store
            
            stores = list(unique_stores.values())
            
        except Exception as e:
            logger.error(f"❌ Failed to parse Sonar response: {e}")
        
        return stores
    
    def _extract_structured_stores(self, response: str, zipcode: str) -> List[StoreLocation]:
        """Extract store information from structured response"""
        stores = []
        
        # Split response into sections
        sections = response.split('\n\n')
        
        for section in sections:
            lines = section.strip().split('\n')
            current_store = None
            
            for line in lines:
                line = line.strip()
                if not line:
                    continue
                
                # Look for STORE: pattern
                if line.startswith('STORE:'):
                    store_name = line.replace('STORE:', '').strip()
                    if store_name and store_name != '[Store Name]' and len(store_name) > 0:
                        if current_store:
                            stores.append(current_store)
                        
                        # Create clean store ID
                        store_id = self._create_store_id(store_name)
                        current_store = StoreLocation(
                            store_id=store_id,
                            store_name=store_name,
                            zipcode=zipcode,
                            status="active"
                        )
                    continue
                
                # Look for ADDRESS: pattern
                if line.startswith('ADDRESS:') and current_store:
                    address = line.replace('ADDRESS:', '').strip()
                    if address and address != '[Complete street address with city, state, zip]' and not address.startswith('-') and len(address) > 0:
                        current_store.address = address
                    continue
                
                # Look for SERVICES: pattern
                if line.startswith('SERVICES:') and current_store:
                    services_text = line.replace('SERVICES:', '').strip()
                    if services_text and services_text != '[comma-separated list: delivery, pickup, curbside, in-store]' and len(services_text) > 0:
                        services = self._parse_services_from_text(services_text)
                        if services:
                            current_store.services = services
                    continue
                
                # Look for WEBSITE: pattern
                if line.startswith('WEBSITE:') and current_store:
                    website = line.replace('WEBSITE:', '').strip()
                    if website and website != '[full URL if available, or "N/A"]' and website != 'N/A' and len(website) > 0:
                        current_store.website = website
                    continue
                
                # Look for STATUS: pattern
                if line.startswith('STATUS:') and current_store:
                    status = line.replace('STATUS:', '').strip()
                    if status and status != '[open/closed/temporarily closed]' and len(status) > 0:
                        current_store.status = status
                    continue
            
            # Add the last store from this section
            if current_store:
                stores.append(current_store)
        
        # If no structured stores found, try fallback parsing
        if not stores:
            stores = self._extract_stores_by_patterns(response, zipcode)
        
        return stores
    
    def _create_store_id(self, store_name: str) -> str:
        """Create a clean store ID from store name"""
        # Remove special characters and convert to lowercase
        clean_name = store_name.lower()
        clean_name = clean_name.replace(' ', '_').replace('-', '_').replace('\'', '').replace('&', 'and')
        clean_name = ''.join(c for c in clean_name if c.isalnum() or c == '_')
        
        # Remove duplicate underscores
        clean_name = '_'.join(filter(None, clean_name.split('_')))
        
        return clean_name
    
    def _parse_services_from_text(self, services_text: str) -> List[str]:
        """Parse services from text like 'delivery, pickup, curbside'"""
        if not services_text:
            return []
        
        # Split by comma and clean up
        services = []
        for service in services_text.split(','):
            service = service.strip().lower()
            if service in ['delivery', 'pickup', 'curbside', 'in-store', 'online']:
                services.append(service)
        
        return services
    
    def _extract_store_name(self, line: str) -> Optional[str]:
        """Extract store name from a line of text"""
        # Common grocery store patterns
        store_patterns = [
            r'\bGiant Eagle\b', r'\bWegmans\b', r'\bALDI\b', r'\bAlbertsons\b', 
            r'\bShopRite\b', r'\bWalmart\b', r'\bTarget\b', r'\bKroger\b', 
            r'\bSafeway\b', r'\bPublix\b', r'\bWhole Foods\b', r'\bTrader Joe\'s\b',
            r'\bSprouts\b', r'\bFood Lion\b', r'\bMeijer\b', r'\bHy-Vee\b',
            r'\bStop & Shop\b', r'\bGiant\b', r'\bShoppers\b', r'\bHarris Teeter\b'
        ]
        
        for pattern in store_patterns:
            match = re.search(pattern, line, re.IGNORECASE)
            if match:
                return match.group(0)
        
        return None
    
    def _is_address_line(self, line: str) -> bool:
        """Check if a line contains an address"""
        address_indicators = [
            'street', 'avenue', 'ave', 'road', 'rd', 'boulevard', 'blvd',
            'drive', 'dr', 'lane', 'ln', 'way', 'court', 'ct', 'place', 'pl'
        ]
        
        line_lower = line.lower()
        return any(indicator in line_lower for indicator in address_indicators)
    
    def _extract_services_from_line(self, line: str) -> List[str]:
        """Extract services from a line of text"""
        services = []
        line_lower = line.lower()
        
        service_mapping = {
            'delivery': 'delivery',
            'pickup': 'pickup',
            'curbside': 'curbside',
            'in-store': 'in-store',
            'instore': 'in-store',
            'online ordering': 'online',
            'online': 'online'
        }
        
        for keyword, service in service_mapping.items():
            if keyword in line_lower:
                services.append(service)
        
        return services
    
    def _extract_stores_by_patterns(self, text: str, zipcode: str) -> List[StoreLocation]:
        """Fallback method to extract stores using pattern matching"""
        stores = []
        
        # Common grocery store names
        store_names = [
            'Giant Eagle', 'Wegmans', 'ALDI', 'Albertsons', 'ShopRite',
            'Walmart', 'Target', 'Kroger', 'Safeway', 'Publix',
            'Whole Foods', 'Trader Joe\'s', 'Sprouts', 'Food Lion',
            'Meijer', 'Hy-Vee', 'Stop & Shop', 'Giant', 'Shoppers', 'Harris Teeter'
        ]
        
        text_lower = text.lower()
        
        for store_name in store_names:
            if store_name.lower() in text_lower:
                store_id = store_name.lower().replace(' ', '').replace('\'', '').replace('-', '')
                store = StoreLocation(
                    store_id=store_id,
                    store_name=store_name,
                    zipcode=zipcode,
                    status="active"
                )
                stores.append(store)
        
        return stores
    
    def _parse_store_details(self, response: str) -> Dict[str, Any]:
        """Enhanced parsing of store details from Sonar response"""
        details = {
            'hours': {},
            'services': [],
            'contact': {},
            'address': '',
            'features': []
        }
        
        try:
            lines = response.split('\n')
            
            for line in lines:
                line = line.strip()
                if not line:
                    continue
                
                # Extract hours
                if any(day in line.lower() for day in ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday']):
                    day_hours = self._extract_day_hours(line)
                    if day_hours:
                        details['hours'].update(day_hours)
                
                # Extract services
                services = self._extract_services_from_line(line)
                if services:
                    details['services'].extend(services)
                
                # Extract contact info
                if any(contact in line.lower() for contact in ['phone', 'contact', 'call', 'website']):
                    contact_info = self._extract_contact_info(line)
                    if contact_info:
                        details['contact'].update(contact_info)
                
                # Extract address
                if self._is_address_line(line) and not details['address']:
                    details['address'] = line
                
                # Extract features
                if any(feature in line.lower() for feature in ['pharmacy', 'bakery', 'deli', 'floral', 'fuel']):
                    details['features'].append(line.strip())
            
            # Remove duplicates
            details['services'] = list(set(details['services']))
            details['features'] = list(set(details['features']))
                
        except Exception as e:
            logger.error(f"❌ Failed to parse store details: {e}")
        
        return details
    
    def _extract_day_hours(self, line: str) -> Dict[str, str]:
        """Extract store hours for a specific day"""
        hours = {}
        
        days = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday']
        
        for day in days:
            if day in line.lower():
                # Extract time pattern (e.g., "9 AM - 9 PM")
                time_pattern = r'(\d{1,2}(?::\d{2})?\s*(?:AM|PM|am|pm)\s*[-–]\s*\d{1,2}(?::\d{2})?\s*(?:AM|PM|am|pm))'
                time_match = re.search(time_pattern, line)
                if time_match:
                    hours[day] = time_match.group(1)
                else:
                    hours[day] = line.strip()
                break
        
        return hours
    
    def _extract_contact_info(self, line: str) -> Dict[str, str]:
        """Extract contact information from a line"""
        contact = {}
        
        # Extract phone number
        phone_pattern = r'(\d{3}[-.\s]?\d{3}[-.\s]?\d{4})'
        phone_match = re.search(phone_pattern, line)
        if phone_match:
            contact['phone'] = phone_match.group(1)
        
        # Extract website
        website_pattern = r'https?://[^\s]+'
        website_match = re.search(website_pattern, line)
        if website_match:
            contact['website'] = website_match.group(0)
        
        return contact
    
    def _parse_product_response(self, response: str) -> List[Dict[str, Any]]:
        """Parse product search response from Sonar"""
        products = []
        
        try:
            # Check if no products found
            if "no products found" in response.lower():
                return []
            
            # Split response into sections
            sections = response.split('\n\n')
            
            for section in sections:
                lines = section.strip().split('\n')
                current_product = {}
                
                for line in lines:
                    line = line.strip()
                    if not line:
                        continue
                    
                    # Look for PRODUCT: pattern
                    if line.startswith('PRODUCT:'):
                        product_name = line.replace('PRODUCT:', '').strip()
                        if product_name and product_name != '[Product Name]' and len(product_name) > 0:
                            current_product['name'] = product_name
                        continue
                    
                    # Look for BRAND: pattern
                    if line.startswith('BRAND:'):
                        brand = line.replace('BRAND:', '').strip()
                        if brand and brand != '[Brand Name]' and len(brand) > 0:
                            current_product['brand'] = brand
                        continue
                    
                    # Look for PRICE: pattern
                    if line.startswith('PRICE:'):
                        price_text = line.replace('PRICE:', '').strip()
                        if price_text and price_text != '[Price with $ symbol, or "Price not available"]' and len(price_text) > 0:
                            # Extract price value
                            price_match = re.search(r'\$(\d+\.?\d*)', price_text)
                            if price_match:
                                current_product['price'] = float(price_match.group(1))
                            else:
                                current_product['price'] = price_text
                        continue
                    
                    # Look for SIZE: pattern
                    if line.startswith('SIZE:'):
                        size = line.replace('SIZE:', '').strip()
                        if size and size != '[Size/quantity, e.g., "32 oz", "1 gallon", "12 pack"]' and len(size) > 0:
                            current_product['size'] = size
                        continue
                    
                    # Look for CATEGORY: pattern
                    if line.startswith('CATEGORY:'):
                        category = line.replace('CATEGORY:', '').strip()
                        if category and category != '[Product category, e.g., "Dairy", "Beverages", "Organic"]' and len(category) > 0:
                            current_product['category'] = category
                        continue
                    
                    # Look for AVAILABILITY: pattern
                    if line.startswith('AVAILABILITY:'):
                        availability = line.replace('AVAILABILITY:', '').strip()
                        if availability and availability != '[in stock/out of stock/limited]' and len(availability) > 0:
                            current_product['availability'] = availability
                        continue
                    
                    # Look for DESCRIPTION: pattern
                    if line.startswith('DESCRIPTION:'):
                        description = line.replace('DESCRIPTION:', '').strip()
                        if description and description != '[Brief product description]' and len(description) > 0:
                            current_product['description'] = description
                        continue
                    
                    # Look for IMAGE_URL: pattern
                    if line.startswith('IMAGE_URL:'):
                        image_url = line.replace('IMAGE_URL:', '').strip()
                        if image_url and image_url != '[Product image URL if available, or "N/A"]' and image_url != 'N/A' and len(image_url) > 0:
                            current_product['image_url'] = image_url
                        continue
                    
                    # Look for any URLs in the line that might be image URLs
                    url_pattern = r'https?://[^\s]+\.(?:jpg|jpeg|png|gif|webp|svg)'
                    url_match = re.search(url_pattern, line, re.IGNORECASE)
                    if url_match and 'image_url' not in current_product:
                        current_product['image_url'] = url_match.group(0)
                        continue
                    
                    # Look for DEALS: pattern
                    if line.startswith('DEALS:'):
                        deals = line.replace('DEALS:', '').strip()
                        if deals and deals != '[Any current deals, discounts, or "None"]' and len(deals) > 0:
                            current_product['deals'] = deals
                        continue
                
                # Add the product if it has at least a name
                if current_product and 'name' in current_product:
                    products.append(current_product)
            
            # If no structured products found, try fallback parsing
            if not products:
                products = self._parse_products_by_patterns(response)
                
        except Exception as e:
            logger.error(f"❌ Failed to parse product response: {e}")
        
        return products
    
    def _parse_products_by_patterns(self, response: str) -> List[Dict[str, Any]]:
        """Fallback parsing for product information using pattern matching"""
        products = []
        
        try:
            lines = response.split('\n')
            current_product = {}
            
            for line in lines:
                line = line.strip()
                if not line:
                    if current_product and 'name' in current_product:
                        products.append(current_product)
                        current_product = {}
                    continue
                
                # Look for product names (lines that might be product names)
                if any(brand in line.lower() for brand in ['oatly', 'chobani', 'silk', 'almond', 'soy', 'milk']):
                    if not current_product.get('name'):
                        current_product['name'] = line
                    continue
                
                # Look for prices
                price_pattern = r'\$(\d+\.?\d*)'
                price_match = re.search(price_pattern, line)
                if price_match:
                    current_product['price'] = float(price_match.group(1))
                    continue
                
                # Look for availability
                if any(status in line.lower() for status in ['in stock', 'available', 'out of stock', 'unavailable', 'limited']):
                    current_product['availability'] = line
                    continue
                
                # Look for deals/discounts
                if any(deal in line.lower() for deal in ['discount', 'sale', 'off', 'deal', 'promotion']):
                    current_product['deals'] = line
                    continue
                
                # Look for size information
                size_pattern = r'(\d+\s*(?:oz|ounce|gallon|pack|count|fl oz|ml|l))'
                size_match = re.search(size_pattern, line, re.IGNORECASE)
                if size_match:
                    current_product['size'] = size_match.group(1)
                    continue
                
                # Look for image URLs
                image_pattern = r'https?://[^\s]+\.(?:jpg|jpeg|png|gif|webp|svg)'
                image_match = re.search(image_pattern, line, re.IGNORECASE)
                if image_match:
                    current_product['image_url'] = image_match.group(0)
                    continue
                
                # Look for any URLs that might be product pages (which often have images)
                url_pattern = r'https?://[^\s]+'
                url_match = re.search(url_pattern, line)
                if url_match and 'image_url' not in current_product:
                    url = url_match.group(0)
                    # If it's a product page URL, we can use it as a placeholder
                    if any(domain in url.lower() for domain in ['target.com', 'walmart.com', 'amazon.com', 'kroger.com']):
                        current_product['image_url'] = url
                        continue
            
            # Add the last product
            if current_product and 'name' in current_product:
                products.append(current_product)
                
        except Exception as e:
            logger.error(f"❌ Failed to parse products by patterns: {e}")
        
        return products
