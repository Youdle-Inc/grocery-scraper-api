"""
Perplexity Sonar client for dynamic store discovery
"""

import os
import logging
import asyncio
from typing import List, Dict, Optional, Any
from datetime import datetime, timedelta
import json

import requests

from .models import StoreLocation

logger = logging.getLogger(__name__)

class SonarClient:
    """Client for Perplexity Sonar API"""
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.environ.get("PERPLEXITY_API_KEY")
        self._cache = {}
        self._cache_duration = timedelta(hours=1)  # Cache for 1 hour
        
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
            query = f"What are the current store hours, services (delivery, pickup, curbside), and contact information for {store_name} in {location}?"
            
            response = await self._make_sonar_request(query)
            return self._parse_store_details(response)
            
        except Exception as e:
            logger.error(f"❌ Failed to get store details for {store_name}: {e}")
            return {}
    
    def _create_store_query(self, zipcode: str) -> str:
        """Create a Sonar query for finding grocery stores"""
        return f"""
        Find all major grocery stores and supermarkets that serve zip code {zipcode}. 
        For each store, provide:
        1. Store name (e.g., Giant Eagle, Wegmans, ALDI, Walmart, Target, etc.)
        2. Store address
        3. Store website or online ordering URL
        4. Available services (delivery, pickup, curbside)
        5. Store hours (if available)
        
        Focus on major grocery chains and supermarkets. Return the information in a structured format.
        """
    
    async def _make_sonar_request(self, query: str) -> str:
        """Make a request to Perplexity Sonar API"""
        try:
            url = "https://api.perplexity.ai/chat/completions"
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            data = {
                "model": "llama-3.1-sonar-small-128k-online",
                "messages": [
                    {
                        "role": "user",
                        "content": query
                    }
                ],
                "max_tokens": 1024
            }
            
            # Make the request
            response = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: requests.post(url, headers=headers, json=data, timeout=30)
            )
            
            if response.status_code == 200:
                result = response.json()
                return result["choices"][0]["message"]["content"]
            else:
                logger.error(f"❌ Perplexity API error: {response.status_code} - {response.text}")
                raise Exception(f"API error: {response.status_code}")
                
        except Exception as e:
            logger.error(f"❌ Sonar request failed: {e}")
            raise
    
    def _parse_store_response(self, response: str, zipcode: str) -> List[StoreLocation]:
        """Parse Sonar response to extract store information"""
        stores = []
        
        try:
            # Try to extract store information from the response
            # This is a simplified parser - you might want to enhance this
            lines = response.split('\n')
            
            current_store = None
            
            for line in lines:
                line = line.strip()
                if not line:
                    continue
                
                # Look for store names (common grocery store patterns)
                store_patterns = [
                    'Giant Eagle', 'Wegmans', 'ALDI', 'Albertsons', 'ShopRite',
                    'Walmart', 'Target', 'Kroger', 'Safeway', 'Publix',
                    'Whole Foods', 'Trader Joe\'s', 'Sprouts', 'Food Lion'
                ]
                
                for pattern in store_patterns:
                    if pattern.lower() in line.lower():
                        # Create new store entry
                        store_id = pattern.lower().replace(' ', '').replace('\'', '')
                        current_store = StoreLocation(
                            store_id=store_id,
                            store_name=pattern,
                            zipcode=zipcode,
                            status="active"
                        )
                        stores.append(current_store)
                        break
                
                # Look for addresses
                if current_store and ('street' in line.lower() or 'ave' in line.lower() or 'rd' in line.lower()):
                    current_store.address = line
                
                # Look for services
                if current_store and any(service in line.lower() for service in ['delivery', 'pickup', 'curbside']):
                    if not current_store.services:
                        current_store.services = []
                    current_store.services.extend([s for s in ['delivery', 'pickup', 'curbside'] if s in line.lower()])
            
            # If no stores found with patterns, try to extract from general text
            if not stores:
                stores = self._extract_stores_from_text(response, zipcode)
            
        except Exception as e:
            logger.error(f"❌ Failed to parse Sonar response: {e}")
        
        return stores
    
    def _extract_stores_from_text(self, text: str, zipcode: str) -> List[StoreLocation]:
        """Extract store information from general text"""
        stores = []
        
        # Common grocery store names
        store_names = [
            'Giant Eagle', 'Wegmans', 'ALDI', 'Albertsons', 'ShopRite',
            'Walmart', 'Target', 'Kroger', 'Safeway', 'Publix',
            'Whole Foods', 'Trader Joe\'s', 'Sprouts', 'Food Lion'
        ]
        
        text_lower = text.lower()
        
        for store_name in store_names:
            if store_name.lower() in text_lower:
                store_id = store_name.lower().replace(' ', '').replace('\'', '')
                store = StoreLocation(
                    store_id=store_id,
                    store_name=store_name,
                    zipcode=zipcode,
                    status="active"
                )
                stores.append(store)
        
        return stores
    
    def _parse_store_details(self, response: str) -> Dict[str, Any]:
        """Parse store details from Sonar response"""
        details = {}
        
        try:
            # Extract hours, services, contact info
            if 'hours' in response.lower():
                details['hours'] = self._extract_hours(response)
            
            if any(service in response.lower() for service in ['delivery', 'pickup', 'curbside']):
                details['services'] = self._extract_services(response)
            
            if any(contact in response.lower() for contact in ['phone', 'contact', 'call']):
                details['contact'] = self._extract_contact(response)
                
        except Exception as e:
            logger.error(f"❌ Failed to parse store details: {e}")
        
        return details
    
    def _extract_hours(self, text: str) -> Dict[str, str]:
        """Extract store hours from text"""
        # Simplified hours extraction
        hours = {}
        lines = text.split('\n')
        
        for line in lines:
            if any(day in line.lower() for day in ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday']):
                # Extract day and hours
                for day in ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday']:
                    if day in line.lower():
                        hours[day] = line.strip()
                        break
        
        return hours
    
    def _extract_services(self, text: str) -> List[str]:
        """Extract available services from text"""
        services = []
        text_lower = text.lower()
        
        if 'delivery' in text_lower:
            services.append('delivery')
        if 'pickup' in text_lower:
            services.append('pickup')
        if 'curbside' in text_lower:
            services.append('curbside')
        
        return services
    
    def _extract_contact(self, text: str) -> str:
        """Extract contact information from text"""
        # Look for phone numbers or contact info
        lines = text.split('\n')
        for line in lines:
            if any(contact in line.lower() for contact in ['phone', 'contact', 'call']):
                return line.strip()
        return ""
