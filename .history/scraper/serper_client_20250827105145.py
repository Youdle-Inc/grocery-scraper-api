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
        self.base_url = "https://google.serper.dev/search"
        
        if not self.api_key:
            logger.warning("⚠️ No SERPER_API_KEY found in .env file")
            self._available = False
        else:
            logger.info("✅ Serper.dev client initialized")
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
            
            # Serper.dev uses POST with JSON body
            headers = {
                'X-API-KEY': self.api_key,
                'Content-Type': 'application/json'
            }
            
            data = {
                'q': search_query,
                'gl': 'us',
                'hl': 'en',
                'num': 20,
                'type': 'shopping'  # For Google Shopping results
            }
            
            logger.info(f"🔍 Searching Serper for: {search_query}")
            
            # Make the request
            response = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: requests.post(self.base_url, headers=headers, json=data, timeout=30)
            )
            
            if response.status_code == 200:
                data = response.json()
                products = self._parse_shopping_results(data, store_name)
                logger.info(f"✅ Found {len(products)} products via Serper")
                return products
            elif response.status_code == 401:
                logger.error("❌ Invalid Serper.dev API key - please check your account and regenerate the key")
                return []
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
            
            # Serper.dev uses POST with JSON body
            headers = {
                'X-API-KEY': self.api_key,
                'Content-Type': 'application/json'
            }
            
            data = {
                'q': search_query,
                'gl': 'us',
                'hl': 'en',
                'num': 10,
                'type': 'images'  # For Google Images results
            }
            
            logger.info(f"🖼️ Searching Serper images for: {search_query}")
            
            # Make the request
            response = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: requests.post(self.base_url, headers=headers, json=data, timeout=30)
            )
            
            if response.status_code == 200:
                data = response.json()
                image_urls = self._parse_image_results(data)
                logger.info(f"✅ Found {len(image_urls)} images via Serper")
                return image_urls
            elif response.status_code == 401:
                logger.error("❌ Invalid Serper.dev API key - please check your account and regenerate the key")
                return []
            else:
                logger.error(f"❌ Serper image search error: {response.status_code}")
                return []
                
        except Exception as e:
            logger.error(f"❌ Serper image search failed: {e}")
            return []
    
    def _parse_shopping_results(self, data: Dict[str, Any], store_name: str = None) -> List[Dict[str, Any]]:
        """Parse Serper.dev shopping search results"""
        products = []
        
        try:
            shopping_results = data.get('shopping', [])
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
            
            for result in shopping_results:
                product = {
                    'name': result.get('title', ''),
                    'price': self._extract_price(result.get('price', '')),
                    'currency': 'USD',  # Serper.dev doesn't provide currency separately
                    'product_url': result.get('link', ''),
                    'image_url': result.get('imageUrl', ''),
                    'source': result.get('source', ''),
                    'rating': result.get('rating', None),
                    'reviews_count': result.get('ratingCount', None),
                    'availability': 'In Stock',  # Assume in stock for Google Shopping results
                    'shipping': 'Free shipping',  # Default assumption
                    'condition': 'New',
                    'serper_product_id': result.get('productId', ''),
                    'serper_source': 'serper_shopping'
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
            logger.error(f"❌ Failed to parse Serper shopping results: {e}")
        
        return products
    
    def _parse_image_results(self, data: Dict[str, Any]) -> List[str]:
        """Parse Serper.dev image search results"""
        image_urls = []
        
        try:
            image_results = data.get('images', [])
            
            for result in image_results:
                image_url = result.get('imageUrl', '')
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
    
    def _get_demo_shopping_results(self, query: str, store_name: str = None) -> List[Dict[str, Any]]:
        """Get demo shopping results when API key is invalid"""
        logger.info("🎭 Using demo mode for shopping results")
        
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
                    'rating': 4.5,
                    'reviews_count': 1250,
                    'availability': 'In Stock',
                    'shipping': 'Free shipping',
                    'condition': 'New',
                    'serper_product_id': 'demo_123456',
                    'serper_source': 'serper_demo'
                },
                {
                    'name': '2% Reduced Fat Milk - 1 Gallon',
                    'price': 3.79,
                    'currency': 'USD',
                    'product_url': 'https://www.target.com/p/2-percent-milk-1-gallon/-/A-87654321',
                    'image_url': 'https://target.scene7.com/is/image/Target/GUEST_2percent-milk-1gal',
                    'source': 'Target',
                    'rating': 4.3,
                    'reviews_count': 890,
                    'availability': 'In Stock',
                    'shipping': 'Free shipping',
                    'condition': 'New',
                    'serper_product_id': 'demo_876543',
                    'serper_source': 'serper_demo'
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
                    'rating': 4.7,
                    'reviews_count': 2100,
                    'availability': 'In Stock',
                    'shipping': 'Free shipping',
                    'condition': 'New',
                    'serper_product_id': 'demo_111111',
                    'serper_source': 'serper_demo'
                },
                {
                    'name': 'Silk Original Oat Milk - 59 oz',
                    'price': 5.99,
                    'currency': 'USD',
                    'product_url': 'https://www.target.com/p/silk-original-oat-milk-59oz/-/A-22222222',
                    'image_url': 'https://target.scene7.com/is/image/Target/GUEST_silk-oat-59oz',
                    'source': 'Target',
                    'rating': 4.4,
                    'reviews_count': 1560,
                    'availability': 'In Stock',
                    'shipping': 'Free shipping',
                    'condition': 'New',
                    'serper_product_id': 'demo_222222',
                    'serper_source': 'serper_demo'
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
                    'rating': 4.0,
                    'reviews_count': 500,
                    'availability': 'In Stock',
                    'shipping': 'Free shipping',
                    'condition': 'New',
                    'serper_product_id': 'demo_generic',
                    'serper_source': 'serper_demo'
                }
            ]
        
        # Filter by store if specified
        if store_name:
            demo_products = [p for p in demo_products if store_name.lower() in p['source'].lower()]
        
        return demo_products
    
    def _get_demo_image_results(self, query: str) -> List[str]:
        """Get demo image results when API key is invalid"""
        logger.info("🎭 Using demo mode for image results")
        
        # Return some realistic demo image URLs
        demo_images = [
            'https://target.scene7.com/is/image/Target/GUEST_demo-product-1',
            'https://target.scene7.com/is/image/Target/GUEST_demo-product-2',
            'https://target.scene7.com/is/image/Target/GUEST_demo-product-3'
        ]
        
        return demo_images
