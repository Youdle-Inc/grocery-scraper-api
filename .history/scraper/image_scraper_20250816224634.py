#!/usr/bin/env python3
"""
Lightweight image scraper for product images.
Uses multiple sources to find product images when Sonar doesn't provide them.
"""

import asyncio
import aiohttp
import re
import logging
from typing import Optional, List, Dict, Any
from urllib.parse import quote_plus
import json

logger = logging.getLogger(__name__)

class ImageScraper:
    """Lightweight image scraper for product images"""
    
    def __init__(self):
        self.session = None
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
    
    async def __aenter__(self):
        """Async context manager entry"""
        self.session = aiohttp.ClientSession(headers=self.headers)
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        if self.session:
            await self.session.close()
    
    async def find_product_image(self, product_name: str, brand: str = None, store_name: str = None) -> Optional[str]:
        """
        Find product image from multiple sources
        
        Args:
            product_name: Name of the product
            brand: Brand name (optional)
            store_name: Store name (optional)
        
        Returns:
            Image URL if found, None otherwise
        """
        try:
            # Try multiple sources
            sources = [
                self._search_google_images,
                self._search_target_images,
                self._search_walmart_images,
                self._search_amazon_images
            ]
            
            for source_func in sources:
                try:
                    image_url = await source_func(product_name, brand, store_name)
                    if image_url:
                        logger.info(f"✅ Found image for {product_name}: {image_url}")
                        return image_url
                except Exception as e:
                    logger.debug(f"❌ Source {source_func.__name__} failed: {e}")
                    continue
            
            logger.info(f"❌ No image found for {product_name}")
            return None
            
        except Exception as e:
            logger.error(f"❌ Image search failed for {product_name}: {e}")
            return None
    
    async def _search_google_images(self, product_name: str, brand: str = None, store_name: str = None) -> Optional[str]:
        """Search Google Images for product"""
        try:
            # Create search query
            search_query = f"{product_name}"
            if brand:
                search_query += f" {brand}"
            if store_name:
                search_query += f" {store_name}"
            
            # Use a simple approach - in production you'd use Google Custom Search API
            # For now, we'll use a placeholder that could be enhanced
            logger.debug(f"🔍 Would search Google Images for: {search_query}")
            return None
            
        except Exception as e:
            logger.debug(f"❌ Google Images search failed: {e}")
            return None
    
    async def _search_target_images(self, product_name: str, brand: str = None, store_name: str = None) -> Optional[str]:
        """Search Target website for product images"""
        try:
            if not self.session:
                return None
            
            # Create search URL for Target
            search_query = quote_plus(f"{product_name}")
            if brand:
                search_query += f"%20{brand}"
            
            search_url = f"https://www.target.com/s?searchTerm={search_query}"
            
            # In a real implementation, you'd scrape the search results
            # For now, we'll return a placeholder
            logger.debug(f"🔍 Would search Target for: {search_url}")
            return None
            
        except Exception as e:
            logger.debug(f"❌ Target search failed: {e}")
            return None
    
    async def _search_walmart_images(self, product_name: str, brand: str = None, store_name: str = None) -> Optional[str]:
        """Search Walmart website for product images"""
        try:
            if not self.session:
                return None
            
            # Create search URL for Walmart
            search_query = quote_plus(f"{product_name}")
            if brand:
                search_query += f"%20{brand}"
            
            search_url = f"https://www.walmart.com/search?q={search_query}"
            
            # In a real implementation, you'd scrape the search results
            logger.debug(f"🔍 Would search Walmart for: {search_url}")
            return None
            
        except Exception as e:
            logger.debug(f"❌ Walmart search failed: {e}")
            return None
    
    async def _search_amazon_images(self, product_name: str, brand: str = None, store_name: str = None) -> Optional[str]:
        """Search Amazon for product images"""
        try:
            if not self.session:
                return None
            
            # Create search URL for Amazon
            search_query = quote_plus(f"{product_name}")
            if brand:
                search_query += f"%20{brand}"
            
            search_url = f"https://www.amazon.com/s?k={search_query}"
            
            # In a real implementation, you'd scrape the search results
            logger.debug(f"🔍 Would search Amazon for: {search_url}")
            return None
            
        except Exception as e:
            logger.debug(f"❌ Amazon search failed: {e}")
            return None
    
    async def enhance_products_with_images(self, products: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Enhance a list of products with image URLs
        
        Args:
            products: List of product dictionaries
        
        Returns:
            Enhanced products with image URLs
        """
        enhanced_products = []
        
        for product in products:
            enhanced_product = product.copy()
            
            # Skip if already has image URL
            if 'image_url' in product and product['image_url']:
                enhanced_products.append(enhanced_product)
                continue
            
            # Try to find image
            product_name = product.get('name', '')
            brand = product.get('brand', '')
            
            image_url = await self.find_product_image(product_name, brand)
            if image_url:
                enhanced_product['image_url'] = image_url
            
            enhanced_products.append(enhanced_product)
        
        return enhanced_products

# Utility function for easy use
async def find_product_image(product_name: str, brand: str = None, store_name: str = None) -> Optional[str]:
    """Convenience function to find a product image"""
    async with ImageScraper() as scraper:
        return await scraper.find_product_image(product_name, brand, store_name)

async def enhance_products_with_images(products: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Convenience function to enhance products with images"""
    async with ImageScraper() as scraper:
        return await scraper.enhance_products_with_images(products)
