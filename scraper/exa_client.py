#!/usr/bin/env python3
"""
Exa API Client for getting real product URLs and image links
"""

import asyncio
import json
import os
import requests
from typing import Dict, List, Any, Optional
from urllib.parse import quote_plus
from dotenv import load_dotenv
import logging

load_dotenv()

logger = logging.getLogger(__name__)

class ExaClient:
    """Client for Exa API to get real product URLs and image links"""
    
    def __init__(self):
        self.api_key = os.getenv("EXA_API_KEY")
        self.base_url = "https://api.exa.ai"
        
        if not self.api_key:
            logger.warning("⚠️ No EXA_API_KEY found in .env file")
            self._available = False
        else:
            logger.info("✅ Exa API client initialized")
            self._available = True
    
    def is_available(self) -> bool:
        """Check if Exa API is available"""
        return self._available and self.api_key is not None
    
    async def search_products(self, query: str, store_name: str = None, location: str = "United States") -> List[Dict[str, Any]]:
        """
        Search for products using Exa API
        
        Args:
            query: Product search query
            store_name: Optional store name to filter results
            location: Geographic location for search
            
        Returns:
            List of products with real URLs and image links
        """
        if not self.is_available():
            logger.warning("⚠️ Exa API not available")
            return []
        
        try:
            # Build search query with store name if provided
            search_query = query
            domain_map = {
                "Target": "target.com",
                "Walmart": "walmart.com",
                "Whole Foods Market": "wholefoodsmarket.com",
                "Whole Foods": "wholefoodsmarket.com",
                "ALDI": "aldi.us",
                "Costco": "costco.com",
                "Kroger": "kroger.com",
                "kroger": "kroger.com",
                "target": "target.com",
                "walmart": "walmart.com",
                "whole_foods": "wholefoodsmarket.com",
                "aldi": "aldi.us",
                "costco": "costco.com",
            }
            if store_name:
                domain = domain_map.get(store_name, None)
                if domain:
                    search_query = f"{query} site:{domain}"
                else:
                    search_query = f"{query} {store_name}"
            
            # Exa API uses POST with JSON body
            headers = {
                'Authorization': f'Bearer {self.api_key}',
                'Content-Type': 'application/json'
            }
            
            data = {
                'query': search_query,
                'numResults': 20,
                'includeDomains': [],
                'excludeDomains': [],
                'useAutoprompt': True,
                'type': 'keyword'  # Use keyword search for product discovery
            }
            
            logger.info(f"🔍 Searching Exa for: {search_query}")
            
            # Make the request
            response = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: requests.post(f"{self.base_url}/search", headers=headers, json=data, timeout=30)
            )
            
            if response.status_code == 200:
                data = response.json()
                products = self._parse_search_results(data, store_name)
                logger.info(f"✅ Found {len(products)} products via Exa")
                return products
            elif response.status_code == 401:
                logger.error("❌ Invalid Exa API key - please check your account and regenerate the key")
                return []
            else:
                logger.error(f"❌ Exa API error: {response.status_code} - {response.text}")
                return []
                
        except Exception as e:
            logger.error(f"❌ Exa search failed: {e}")
            return []
    
    async def get_contents(self, urls: List[str]) -> List[Dict[str, Any]]:
        """
        Get contents from URLs using Exa API
        
        Args:
            urls: List of URLs to get contents from
            
        Returns:
            List of content objects with parsed data
        """
        if not self.is_available():
            return []
        
        try:
            headers = {
                'Authorization': f'Bearer {self.api_key}',
                'Content-Type': 'application/json'
            }
            
            data = {
                'urls': urls,
                'includeImages': True,
                'includeLinks': True
            }
            
            logger.info(f"📄 Getting contents for {len(urls)} URLs via Exa")
            
            response = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: requests.post(f"{self.base_url}/contents", headers=headers, json=data, timeout=30)
            )
            
            if response.status_code == 200:
                data = response.json()
                return data.get('contents', [])
            else:
                logger.error(f"❌ Exa contents error: {response.status_code}")
                return []
                
        except Exception as e:
            logger.error(f"❌ Exa contents failed: {e}")
            return []
    
    def _parse_search_results(self, data: Dict[str, Any], store_name: str = None) -> List[Dict[str, Any]]:
        """Parse Exa search results"""
        products = []
        
        try:
            results = data.get('results', [])
            # Determine expected domain if store filter provided
            expected_domain = None
            if store_name:
                domain_map = {
                    "target": "target.com",
                    "walmart": "walmart.com",
                    "whole foods market": "wholefoodsmarket.com",
                    "whole foods": "wholefoodsmarket.com",
                    "whole_foods": "wholefoodsmarket.com",
                    "aldi": "aldi.us",
                    "costco": "costco.com",
                    "kroger": "kroger.com",
                }
                expected_domain = domain_map.get(store_name.lower())
            
            for result in results:
                # Extract product information from search result
                product = {
                    'name': result.get('title', ''),
                    'price': self._extract_price(result.get('text', '')),
                    'currency': 'USD',
                    'product_url': result.get('url', ''),
                    'image_url': result.get('imageUrl', ''),
                    'source': result.get('source', ''),
                    'description': result.get('text', ''),
                    'availability': 'In Stock',  # Assume in stock for search results
                    'exa_source': 'exa_search'
                }
                
                # Filter by store domain if specified
                if expected_domain:
                    try:
                        from urllib.parse import urlparse
                        netloc = urlparse(product['product_url']).netloc or ""
                        if expected_domain not in netloc:
                            continue
                    except Exception:
                        continue
                
                products.append(product)
                
        except Exception as e:
            logger.error(f"❌ Failed to parse Exa search results: {e}")
        
        return products
    
    def _extract_price(self, text: str) -> Optional[float]:
        """Extract numeric price from text"""
        try:
            if not text:
                return None
            
            # Remove currency symbols and extract number
            import re
            price_match = re.search(r'[\d,]+\.?\d*', text.replace(',', ''))
            if price_match:
                return float(price_match.group())
            
            return None
        except:
            return None
    
    async def enhance_products_with_exa(self, products: List[Dict[str, Any]], store_name: str, location: str = "United States") -> List[Dict[str, Any]]:
        """
        Enhance products from Perplexity with real URLs and images from Exa
        
        Args:
            products: List of products from Perplexity
            store_name: Store name for filtering
            location: Geographic location
            
        Returns:
            Enhanced products with real URLs and images
        """
        if not self.is_available():
            logger.warning("⚠️ Exa API not available, skipping enhancement")
            return products
        
        enhanced_products = []
        
        for product in products:
            enhanced_product = product.copy()
            product_name = product.get('name', '')
            
            try:
                # Search for this specific product
                exa_products = await self.search_products(product_name, store_name, location)
                
                # Find best match
                best_match = self._find_best_product_match(product, exa_products)
                
                if best_match:
                    # Enhance with Exa data
                    enhanced_product.update({
                        'product_url': best_match.get('product_url', enhanced_product.get('product_url')),
                        'image_url': best_match.get('image_url', enhanced_product.get('image_url')),
                        'exa_source': best_match.get('exa_source'),
                        'real_price': best_match.get('price'),
                        'real_currency': best_match.get('currency'),
                        'real_description': best_match.get('description'),
                        'real_availability': best_match.get('availability')
                    })
                    
                    logger.info(f"✅ Enhanced {product_name} with Exa data")
                
            except Exception as e:
                logger.warning(f"⚠️ Failed to enhance {product_name}: {e}")
            
            enhanced_products.append(enhanced_product)
        
        return enhanced_products
    
    def _find_best_product_match(self, perplexity_product: Dict[str, Any], exa_products: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """Find the best matching product between Perplexity and Exa results"""
        if not exa_products:
            return None
        
        product_name = perplexity_product.get('name', '').lower()
        product_brand = perplexity_product.get('brand', '').lower()
        
        best_match = None
        best_score = 0
        
        for exa_product in exa_products:
            exa_name = exa_product.get('name', '').lower()
            
            # Calculate similarity score
            name_words = set(product_name.split())
            exa_words = set(exa_name.split())
            
            # Count common words
            common_words = name_words.intersection(exa_words)
            score = len(common_words) / max(len(name_words), len(exa_words))
            
            # Bonus for brand match
            if product_brand and product_brand in exa_name:
                score += 0.3
            
            # Bonus for exact name match
            if product_name in exa_name or exa_name in product_name:
                score += 0.5
            
            if score > best_score and score > 0.2:  # At least 20% match
                best_score = score
                best_match = exa_product
        
        return best_match
    
    def _get_demo_search_results(self, query: str, store_name: str = None) -> List[Dict[str, Any]]:
        """Get demo search results when API key is invalid"""
        logger.info("🎭 Using demo mode for search results")
        
        # Generate realistic demo data based on the query
        demo_products = []
        
        if "milk" in query.lower():
            demo_products = [
                {
                    'name': 'Organic Whole Milk - 1 Gallon',
                    'price': 4.99,
                    'currency': 'USD',
                    'product_url': 'https://www.target.com/p/organic-whole-milk-1-gallon/-/A-12345678',
                    'image_url': 'https://target.scene7.com/is/image/Target/GUEST_organic-milk-1gal',
                    'source': 'Target',
                    'description': 'Organic whole milk from pasture-raised cows',
                    'availability': 'In Stock',
                    'exa_source': 'exa_demo'
                },
                {
                    'name': '2% Reduced Fat Milk - 1 Gallon',
                    'price': 3.79,
                    'currency': 'USD',
                    'product_url': 'https://www.target.com/p/2-percent-milk-1-gallon/-/A-87654321',
                    'image_url': 'https://target.scene7.com/is/image/Target/GUEST_2percent-milk-1gal',
                    'source': 'Target',
                    'description': '2% reduced fat milk, great for everyday use',
                    'availability': 'In Stock',
                    'exa_source': 'exa_demo'
                }
            ]
        elif "oat" in query.lower():
            demo_products = [
                {
                    'name': 'Oatly Original Oat Milk - 32 oz',
                    'price': 4.49,
                    'currency': 'USD',
                    'product_url': 'https://www.target.com/p/oatly-original-oat-milk-32oz/-/A-11111111',
                    'image_url': 'https://target.scene7.com/is/image/Target/GUEST_oatly-original-32oz',
                    'source': 'Target',
                    'description': 'Original oat milk made from Swedish oats',
                    'availability': 'In Stock',
                    'exa_source': 'exa_demo'
                },
                {
                    'name': 'Silk Original Oat Milk - 59 oz',
                    'price': 5.99,
                    'currency': 'USD',
                    'product_url': 'https://www.target.com/p/silk-original-oat-milk-59oz/-/A-22222222',
                    'image_url': 'https://target.scene7.com/is/image/Target/GUEST_silk-oat-59oz',
                    'source': 'Target',
                    'description': 'Original oat milk with a creamy texture',
                    'availability': 'In Stock',
                    'exa_source': 'exa_demo'
                }
            ]
        else:
            # Generic demo product
            demo_products = [
                {
                    'name': f'{query.title()} - Demo Product',
                    'price': 9.99,
                    'currency': 'USD',
                    'product_url': f'https://www.target.com/p/{query.lower().replace(" ", "-")}/-/A-demo123',
                    'image_url': 'https://target.scene7.com/is/image/Target/GUEST_demo-product',
                    'source': 'Target',
                    'description': f'Demo product for {query}',
                    'availability': 'In Stock',
                    'exa_source': 'exa_demo'
                }
            ]
        
        # Filter by store if specified
        if store_name:
            demo_products = [p for p in demo_products if store_name.lower() in p['source'].lower()]
        
        return demo_products

