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

from .models import StoreLocation

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
            response = await self._make_sonar_request(query)
            
            # Parse response
            stores = self._parse_store_response(response, zipcode)
            
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
            
            response = await self._make_sonar_request(query)
            return self._parse_store_details(response)
            
        except Exception as e:
            logger.error(f"❌ Failed to get store details for {store_name}: {e}")
            return {}
    
    async def search_products(self, query: str, store_name: str, location: str) -> List[Dict[str, Any]]:
        """Search for products at a specific store using Sonar"""
        if not self.is_available():
            return []
        
        try:
            search_query = f"""Find current product information for "{query}" at {store_name} in {location}.
            Please provide:
            1. Product names and descriptions
            2. Current prices (if available)
            3. Availability status
            4. Any special offers or deals
            5. Product categories or departments
            
            Focus on accurate, current information."""
            
            response = await self._make_sonar_request(search_query)
            return self._parse_product_response(response)
            
        except Exception as e:
            logger.error(f"❌ Failed to search products for {query} at {store_name}: {e}")
            return []
    
    def _create_store_query(self, zipcode: str) -> str:
        """Create a Sonar query for finding grocery stores"""
        return f"""Find all major grocery stores and supermarkets that serve zip code {zipcode}.

Please provide a comprehensive list in this exact format:

STORE: [Store Name]
ADDRESS: [Full street address]
SERVICES: [delivery, pickup, curbside, in-store]
WEBSITE: [store website if available]
STATUS: [open/closed]

For example:
STORE: Giant Eagle
ADDRESS: 123 Main Street, Pittsburgh, PA 15213
SERVICES: delivery, pickup, curbside
WEBSITE: https://www.gianteagle.com
STATUS: open

Include major chains like Walmart, Target, Kroger, Safeway, Publix, Whole Foods, Trader Joe's, ALDI, Wegmans, Giant Eagle, Meijer, Hy-Vee, Food Lion, Stop & Shop, and any other grocery stores in this area."""
    
    async def _make_sonar_request(self, query: str) -> str:
        """Make a request to Perplexity Sonar API with proper error handling"""
        try:
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            
            # Use the latest Sonar model
            data = {
        'model': 'sonar-small-online',               
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
                    return result["choices"][0]["message"]["content"]
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
                    if store_name:
                        if current_store:
                            stores.append(current_store)
                        
                        store_id = store_name.lower().replace(' ', '').replace('\'', '').replace('-', '')
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
                    if address and not address.startswith('-'):
                        current_store.address = address
                    continue
                
                # Look for SERVICES: pattern
                if line.startswith('SERVICES:') and current_store:
                    services_text = line.replace('SERVICES:', '').strip()
                    services = self._parse_services_from_text(services_text)
                    if services:
                        current_store.services = services
                    continue
                
                # Look for STATUS: pattern
                if line.startswith('STATUS:') and current_store:
                    status = line.replace('STATUS:', '').strip()
                    if status:
                        current_store.status = status
                    continue
            
            # Add the last store from this section
            if current_store:
                stores.append(current_store)
        
        return stores
    
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
            lines = response.split('\n')
            current_product = {}
            
            for line in lines:
                line = line.strip()
                if not line:
                    if current_product:
                        products.append(current_product)
                        current_product = {}
                    continue
                
                # Look for product names
                if any(keyword in line.lower() for keyword in ['brand', 'product', 'item']):
                    current_product['name'] = line
                
                # Look for prices
                price_pattern = r'\$(\d+\.?\d*)'
                price_match = re.search(price_pattern, line)
                if price_match:
                    current_product['price'] = float(price_match.group(1))
                
                # Look for availability
                if any(status in line.lower() for status in ['in stock', 'available', 'out of stock', 'unavailable']):
                    current_product['availability'] = line
            
            # Add the last product
            if current_product:
                products.append(current_product)
                
        except Exception as e:
            logger.error(f"❌ Failed to parse product response: {e}")
        
        return products
