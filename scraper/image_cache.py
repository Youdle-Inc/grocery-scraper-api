#!/usr/bin/env python3
"""
Product Image Cache with Fuzzy Matching
Caches product images and uses fuzzy matching to reuse images for similar products.
"""

import re
import logging
from typing import Optional, Dict, Any, List
from difflib import SequenceMatcher
from scraper.cache import Cache

logger = logging.getLogger(__name__)


class ProductImageCache:
    """Cache product images with fuzzy matching for similar products"""
    
    def __init__(self, cache: Cache):
        self.cache = cache
        self.similarity_threshold = 0.85  # 85% similarity to reuse image
    
    def _normalize_product_key(self, name: str, brand: Optional[str] = None, size: Optional[str] = None) -> str:
        """Create a normalized key for product matching"""
        # Normalize name
        normalized_name = re.sub(r'[^\w\s]', '', name.lower())
        normalized_name = re.sub(r'\s+', ' ', normalized_name).strip()
        
        # Remove common words
        stop_words = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by'}
        words = [w for w in normalized_name.split() if w not in stop_words and len(w) > 2]
        normalized_name = ' '.join(words)
        
        # Add brand if available
        if brand:
            normalized_brand = re.sub(r'[^\w\s]', '', brand.lower()).strip()
            normalized_name = f"{normalized_brand} {normalized_name}"
        
        # Add size if available (normalized)
        if size:
            normalized_size = self._normalize_size(size)
            if normalized_size:
                normalized_name = f"{normalized_name} {normalized_size}"
        
        return normalized_name
    
    def _normalize_size(self, size: str) -> str:
        """Normalize product size for matching"""
        if not size:
            return ""
        
        size_lower = size.lower()
        # Normalize common size variations
        size_lower = size_lower.replace('fluid ounces', 'fl oz')
        size_lower = size_lower.replace('fluid ounce', 'fl oz')
        size_lower = size_lower.replace('fl. oz', 'fl oz')
        size_lower = size_lower.replace('fl-oz', 'fl oz')
        size_lower = size_lower.replace('ounces', 'oz')
        size_lower = size_lower.replace('ounce', 'oz')
        size_lower = size_lower.replace('gallons', 'gal')
        size_lower = size_lower.replace('gallon', 'gal')
        size_lower = size_lower.replace('pounds', 'lb')
        size_lower = size_lower.replace('pound', 'lb')
        size_lower = size_lower.replace('count', 'ct')
        size_lower = size_lower.replace('pack', 'pk')
        
        # Remove extra whitespace
        size_lower = re.sub(r'\s+', ' ', size_lower).strip()
        return size_lower
    
    def _calculate_similarity(self, str1: str, str2: str) -> float:
        """Calculate similarity between two strings (0.0 to 1.0)"""
        return SequenceMatcher(None, str1.lower(), str2.lower()).ratio()
    
    async def get_cached_image(
        self, 
        name: str, 
        brand: Optional[str] = None, 
        size: Optional[str] = None,
        store: Optional[str] = None
    ) -> Optional[str]:
        """
        Get cached image URL using fuzzy matching
        
        Args:
            name: Product name
            brand: Brand name (optional)
            size: Product size/quantity (optional)
            store: Store name (optional)
            
        Returns:
            Cached image URL if similar product found, None otherwise
        """
        try:
            # Create normalized key for this product
            product_key = self._normalize_product_key(name, brand, size)
            
            # Get all cached product images
            cache_key = "product_images:index"
            cached_products = await self.cache.get_json(cache_key) or {}
            
            if not cached_products:
                return None
            
            # Try exact match first (fastest)
            if product_key in cached_products:
                cached = cached_products[product_key]
                logger.debug(f"✅ Exact match found for '{name}': {cached.get('image_url', '')[:50]}...")
                return cached.get('image_url')
            
            # Try fuzzy matching
            best_match = None
            best_similarity = 0.0
            
            for cached_key, cached_data in cached_products.items():
                similarity = self._calculate_similarity(product_key, cached_key)
                
                # Prefer matches from same store if store is specified
                if store and cached_data.get('store') == store.lower():
                    similarity += 0.1  # Boost similarity for same store
                
                if similarity > best_similarity:
                    best_similarity = similarity
                    best_match = cached_data
            
            # Return if similarity is above threshold
            if best_match and best_similarity >= self.similarity_threshold:
                logger.info(f"✅ Fuzzy match found for '{name}' (similarity: {best_similarity:.2f}): {best_match.get('image_url', '')[:50]}...")
                return best_match.get('image_url')
            
            logger.debug(f"⚠️ No match found for '{name}' (best similarity: {best_similarity:.2f})")
            return None
            
        except Exception as e:
            logger.warning(f"Failed to get cached image: {e}")
            return None
    
    async def cache_image(
        self,
        name: str,
        image_url: str,
        brand: Optional[str] = None,
        size: Optional[str] = None,
        store: Optional[str] = None,
        product_url: Optional[str] = None
    ) -> None:
        """
        Cache a product image for future fuzzy matching
        
        Args:
            name: Product name
            image_url: Image URL to cache
            brand: Brand name (optional)
            size: Product size/quantity (optional)
            store: Store name (optional)
            product_url: Product URL (optional)
        """
        try:
            if not image_url:
                return
            
            # Create normalized key
            product_key = self._normalize_product_key(name, brand, size)
            
            # Get existing cache
            cache_key = "product_images:index"
            cached_products = await self.cache.get_json(cache_key) or {}
            
            # Add/update entry
            cached_products[product_key] = {
                'image_url': image_url,
                'name': name,
                'brand': brand,
                'size': size,
                'store': store.lower() if store else None,
                'product_url': product_url,
                'cached_at': None  # Could add timestamp if needed
            }
            
            # Limit cache size to prevent memory issues (keep most recent 1000)
            if len(cached_products) > 1000:
                # Remove oldest entries (simple FIFO - could be improved)
                keys_to_remove = list(cached_products.keys())[:-1000]
                for key in keys_to_remove:
                    del cached_products[key]
            
            # Save back to cache (24 hour TTL)
            await self.cache.set_json(cache_key, cached_products, ttl_seconds=60*60*24)
            
            logger.debug(f"💾 Cached image for '{name}': {image_url[:50]}...")
            
        except Exception as e:
            logger.warning(f"Failed to cache image: {e}")
    
    async def cache_images_batch(
        self,
        products: List[Dict[str, Any]]
    ) -> None:
        """
        Cache multiple product images at once
        
        Args:
            products: List of product dicts with name, image_url, brand, size, etc.
        """
        for product in products:
            if product.get('image_url'):
                await self.cache_image(
                    name=product.get('name', ''),
                    image_url=product['image_url'],
                    brand=product.get('brand'),
                    size=product.get('size') or product.get('quantity'),
                    store=product.get('store_name'),
                    product_url=product.get('product_url')
                )
    
    async def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        try:
            cache_key = "product_images:index"
            cached_products = await self.cache.get_json(cache_key) or {}
            
            return {
                'total_cached': len(cached_products),
                'similarity_threshold': self.similarity_threshold
            }
        except Exception as e:
            logger.warning(f"Failed to get cache stats: {e}")
            return {'total_cached': 0, 'similarity_threshold': self.similarity_threshold}


