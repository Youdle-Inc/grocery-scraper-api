#!/usr/bin/env python3
"""
Google Custom Search API integration for product images.
This provides a more reliable way to find product images.
"""

import asyncio
import aiohttp
import logging
import os
from typing import Optional, List, Dict, Any
from urllib.parse import quote_plus
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

logger = logging.getLogger(__name__)

class GoogleImageSearch:
    """Google Custom Search API for product images"""
    
    def __init__(self):
        self.api_key = os.environ.get("GOOGLE_API_KEY")
        self.search_engine_id = os.environ.get("GOOGLE_SEARCH_ENGINE_ID")
        self.base_url = "https://www.googleapis.com/customsearch/v1"
        self.session = None
    
    async def __aenter__(self):
        """Async context manager entry"""
        self.session = aiohttp.ClientSession()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        if self.session:
            await self.session.close()
    
    def is_available(self) -> bool:
        """Check if Google API is configured"""
        return bool(self.api_key and self.search_engine_id)
    
    async def search_product_image(self, product_name: str, brand: str = None, store_name: str = None) -> Optional[str]:
        """
        Search for product image using Google Custom Search API
        
        Args:
            product_name: Name of the product
            brand: Brand name (optional)
            store_name: Store name (optional)
        
        Returns:
            Image URL if found, None otherwise
        """
        if not self.is_available():
            logger.warning("⚠️ Google API not configured. Set GOOGLE_API_KEY and GOOGLE_SEARCH_ENGINE_ID")
            return None
        
        try:
            # Build search query
            search_query = f"{product_name}"
            if brand:
                search_query += f" {brand}"
            if store_name:
                search_query += f" {store_name}"
            
            # Add image search terms
            search_query += " product image"
            
            # Make API request
            params = {
                'key': self.api_key,
                'cx': self.search_engine_id,
                'q': search_query,
                'searchType': 'image',
                'num': 1,  # Get first result
                'safe': 'active'
            }
            
            async with self.session.get(self.base_url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    
                    if 'items' in data and len(data['items']) > 0:
                        image_url = data['items'][0]['link']
                        logger.info(f"✅ Found Google image for {product_name}: {image_url}")
                        return image_url
                    else:
                        logger.info(f"❌ No Google images found for {product_name}")
                        return None
                else:
                    logger.error(f"❌ Google API error: {response.status}")
                    return None
                    
        except Exception as e:
            logger.error(f"❌ Google image search failed for {product_name}: {e}")
            return None
    
    async def enhance_products_with_images(self, products: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Enhance a list of products with Google image URLs
        
        Args:
            products: List of product dictionaries
        
        Returns:
            Enhanced products with image URLs
        """
        if not self.is_available():
            logger.warning("⚠️ Google API not configured, skipping image enhancement")
            return products
        
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
            
            image_url = await self.search_product_image(product_name, brand)
            if image_url:
                enhanced_product['image_url'] = image_url
            
            enhanced_products.append(enhanced_product)
        
        return enhanced_products

# Utility functions
async def search_product_image(product_name: str, brand: str = None, store_name: str = None) -> Optional[str]:
    """Convenience function to search for a product image"""
    async with GoogleImageSearch() as searcher:
        return await searcher.search_product_image(product_name, brand, store_name)

async def enhance_products_with_google_images(products: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Convenience function to enhance products with Google images"""
    async with GoogleImageSearch() as searcher:
        return await searcher.enhance_products_with_images(products)

