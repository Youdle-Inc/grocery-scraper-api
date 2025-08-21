#!/usr/bin/env python3
"""
Serper API Client for getting real product URLs and image links
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

class SerperClient:
    """Client for Serper API to get real product URLs and image links"""
    
    def __init__(self):
        self.api_key = os.getenv("SERPER_API_KEY")
        self.base_url = "https://api.serpwow.com/live/search"
        
        if not self.api_key:
            logger.warning("⚠️ No SERPER_API_KEY found in .env file")
            self._available = False
        else:
            # Check if it's a demo key
            if self.api_key == "demo":
                logger.info("✅ Serper client initialized (DEMO MODE)")
                self._available = True
            else:
                logger.info("✅ Serper client initialized")
                self._available = True
    
    def is_available(self) -> bool:
        """Check if Serper API is available"""
        return self._available and self.api_key is not None
    
    async def search_shopping_products(self, query: str, store_name: str = None, location: str = "United States") -> List[Dict[str, Any]]:
        """
        Search for products using Google Shopping via Serper API
        
        Args:
            query: Product search query
            store_name: Optional store name to filter results
            location: Geographic location for search
            
        Returns:
            List of products with real URLs and image links
        """
        if not self.is_available():
            logger.warning("⚠️ Serper API not available")
            return []
        
        try:
            # Build search query with store name if provided
            search_query = query
            if store_name:
                search_query = f"{query} {store_name}"
            
            params = {
                'api_key': self.api_key,
                'engine': 'google',
                'search_type': 'shopping',
                'q': search_query,
                'location': location,
                'gl': 'us',
                'hl': 'en',
                'num': 20  # Get more results for better matching
            }
            
            logger.info(f"🔍 Searching Serper for: {search_query}")
            
            # Make the request
            response = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: requests.get(self.base_url, params=params, timeout=30)
            )
            
            if response.status_code == 200:
                data = response.json()
                products = self._parse_shopping_results(data, store_name)
                logger.info(f"✅ Found {len(products)} products via Serper")
                return products
            else:
                logger.error(f"❌ Serper API error: {response.status_code} - {response.text}")
                return []
                
        except Exception as e:
            logger.error(f"❌ Serper search failed: {e}")
            return []
    
    async def search_product_images(self, query: str, store_name: str = None) -> List[str]:
        """
        Search for product images using Google Images via Serper API
        
        Args:
            query: Product search query
            store_name: Optional store name to filter results
            
        Returns:
            List of image URLs
        """
        if not self.is_available():
            return []
        
        try:
            # Build search query
            search_query = query
            if store_name:
                search_query = f"{query} {store_name} product"
            
            params = {
                'api_key': self.api_key,
                'engine': 'google',
                'search_type': 'images',
                'q': search_query,
                'gl': 'us',
                'hl': 'en',
                'images_size': 'large',
                'num': 10
            }
            
            logger.info(f"🖼️ Searching Serper images for: {search_query}")
            
            # Make the request
            response = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: requests.get(self.base_url, params=params, timeout=30)
            )
            
            if response.status_code == 200:
                data = response.json()
                image_urls = self._parse_image_results(data)
                logger.info(f"✅ Found {len(image_urls)} images via Serper")
                return image_urls
            else:
                logger.error(f"❌ Serper image search error: {response.status_code}")
                return []
                
        except Exception as e:
            logger.error(f"❌ Serper image search failed: {e}")
            return []
    
    def _parse_shopping_results(self, data: Dict[str, Any], store_name: str = None) -> List[Dict[str, Any]]:
        """Parse Serper shopping search results"""
        products = []
        
        try:
            shopping_results = data.get('shopping_results', [])
            
            for result in shopping_results:
                product = {
                    'name': result.get('title', ''),
                    'price': self._extract_price(result.get('price', '')),
                    'currency': result.get('currency', 'USD'),
                    'product_url': result.get('product_link', ''),
                    'image_url': result.get('image', ''),
                    'source': result.get('source', ''),
                    'rating': result.get('rating', None),
                    'reviews_count': result.get('reviews', None),
                    'availability': result.get('availability', 'Unknown'),
                    'shipping': result.get('shipping', ''),
                    'condition': result.get('condition', 'New'),
                    'serper_product_id': result.get('product_id', ''),
                    'serper_source': 'serper_shopping'
                }
                
                # Filter by store if specified
                if store_name and store_name.lower() not in product['source'].lower():
                    continue
                
                products.append(product)
                
        except Exception as e:
            logger.error(f"❌ Failed to parse Serper shopping results: {e}")
        
        return products
    
    def _parse_image_results(self, data: Dict[str, Any]) -> List[str]:
        """Parse Serper image search results"""
        image_urls = []
        
        try:
            image_results = data.get('image_results', [])
            
            for result in image_results:
                image_url = result.get('image_url', '')
                if image_url and image_url.startswith('http'):
                    image_urls.append(image_url)
                    
        except Exception as e:
            logger.error(f"❌ Failed to parse Serper image results: {e}")
        
        return image_urls
    
    def _extract_price(self, price_str: str) -> Optional[float]:
        """Extract numeric price from price string"""
        try:
            if not price_str:
                return None
            
            # Remove currency symbols and extract number
            import re
            price_match = re.search(r'[\d,]+\.?\d*', price_str.replace(',', ''))
            if price_match:
                return float(price_match.group())
            
            return None
        except:
            return None
    
    async def enhance_products_with_serper(self, products: List[Dict[str, Any]], store_name: str, location: str = "United States") -> List[Dict[str, Any]]:
        """
        Enhance products from Perplexity with real URLs and images from Serper
        
        Args:
            products: List of products from Perplexity
            store_name: Store name for filtering
            location: Geographic location
            
        Returns:
            Enhanced products with real URLs and images
        """
        if not self.is_available():
            logger.warning("⚠️ Serper API not available, skipping enhancement")
            return products
        
        enhanced_products = []
        
        for product in products:
            enhanced_product = product.copy()
            product_name = product.get('name', '')
            
            try:
                # Search for this specific product
                serper_products = await self.search_shopping_products(product_name, store_name, location)
                
                # Find best match
                best_match = self._find_best_product_match(product, serper_products)
                
                if best_match:
                    # Enhance with Serper data
                    enhanced_product.update({
                        'product_url': best_match.get('product_url', enhanced_product.get('product_url')),
                        'image_url': best_match.get('image_url', enhanced_product.get('image_url')),
                        'serper_product_id': best_match.get('serper_product_id'),
                        'serper_source': best_match.get('serper_source'),
                        'real_price': best_match.get('price'),
                        'real_currency': best_match.get('currency'),
                        'real_rating': best_match.get('rating'),
                        'real_reviews_count': best_match.get('reviews_count'),
                        'real_availability': best_match.get('availability'),
                        'real_shipping': best_match.get('shipping'),
                        'real_condition': best_match.get('condition')
                    })
                    
                    logger.info(f"✅ Enhanced {product_name} with Serper data")
                else:
                    # Try to get just images if no product match
                    image_urls = await self.search_product_images(product_name, store_name)
                    if image_urls:
                        enhanced_product['image_url'] = image_urls[0]
                        enhanced_product['serper_source'] = 'serper_images'
                        logger.info(f"🖼️ Added image for {product_name}")
                
            except Exception as e:
                logger.warning(f"⚠️ Failed to enhance {product_name}: {e}")
            
            enhanced_products.append(enhanced_product)
        
        return enhanced_products
    
    def _find_best_product_match(self, perplexity_product: Dict[str, Any], serper_products: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """Find the best matching product between Perplexity and Serper results"""
        if not serper_products:
            return None
        
        product_name = perplexity_product.get('name', '').lower()
        product_brand = perplexity_product.get('brand', '').lower()
        
        best_match = None
        best_score = 0
        
        for serper_product in serper_products:
            serper_name = serper_product.get('name', '').lower()
            
            # Calculate similarity score
            name_words = set(product_name.split())
            serper_words = set(serper_name.split())
            
            # Count common words
            common_words = name_words.intersection(serper_words)
            score = len(common_words) / max(len(name_words), len(serper_words))
            
            # Bonus for brand match
            if product_brand and product_brand in serper_name:
                score += 0.3
            
            # Bonus for exact name match
            if product_name in serper_name or serper_name in product_name:
                score += 0.5
            
            if score > best_score and score > 0.2:  # At least 20% match
                best_score = score
                best_match = serper_product
        
        return best_match
