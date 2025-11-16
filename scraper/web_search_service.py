#!/usr/bin/env python3
"""
Web Search Service for Price Verification
Uses Exa API to search the web and extract accurate product prices
"""

import os
import logging
import re
import json
from typing import Dict, Optional, Any, List
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)


class WebSearchService:
    """Service for web search-based price verification and product data extraction"""
    
    def __init__(self, exa_client=None):
        """
        Initialize web search service
        
        Args:
            exa_client: ExaStructuredClient instance (optional, will create if not provided)
        """
        self.exa_client = exa_client
        
    async def verify_product_price(
        self,
        product_url: str,
        product_name: Optional[str] = None,
        store_name: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Verify and extract accurate price from a product URL using web search
        
        Args:
            product_url: URL of the product page
            product_name: Name of the product (for better search context)
            store_name: Store name (for better search context)
            
        Returns:
            Dict with verified price and other product data, or None if extraction fails
        """
        if not self.exa_client or not self.exa_client.is_available():
            logger.warning("Exa client not available for web search")
            return None
        
        try:
            # Use Exa's structured extraction to get price from the product page
            # Pass store_name for better extraction accuracy
            price = await self.exa_client._get_price_from_exa(product_url, store_name=store_name)
            
            if price:
                logger.info(f"✅ Verified price from {product_url}: ${price}")
                return {
                    "price": price,
                    "currency": "USD",
                    "source": "web_search",
                    "url": product_url
                }
            else:
                logger.debug(f"Could not extract price from {product_url}")
                return None
                
        except Exception as e:
            logger.error(f"Error verifying price for {product_url}: {e}")
            return None
    
    async def search_and_extract_product_data(
        self,
        query: str,
        store_name: Optional[str] = None,
        zipcode: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Search the web for products and extract structured data
        
        Args:
            query: Product search query
            store_name: Optional store name filter
            zipcode: Optional zipcode for location-based results
            
        Returns:
            List of product dictionaries with verified prices
        """
        if not self.exa_client or not self.exa_client.is_available():
            logger.warning("Exa client not available for web search")
            return []
        
        try:
            # Use existing Exa structured search
            products = await self.exa_client.search_products_structured(
                query=query,
                store_name=store_name,
                zipcode=zipcode,
                num_results=20
            )
            
            # Enhance products with verified prices
            enhanced_products = []
            for product in products:
                product_url = product.get("product_url")
                if product_url and not product.get("price"):
                    # Try to verify price from product URL
                    verified_data = await self.verify_product_price(
                        product_url=product_url,
                        product_name=product.get("name"),
                        store_name=store_name
                    )
                    if verified_data:
                        product["price"] = verified_data["price"]
                        product["price_source"] = "web_search_verified"
                
                enhanced_products.append(product)
            
            return enhanced_products
            
        except Exception as e:
            logger.error(f"Error in web search: {e}")
            return []
    
    async def batch_verify_prices(
        self,
        products: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Verify prices for multiple products in batch
        
        Args:
            products: List of product dictionaries with product_url
            
        Returns:
            List of products with verified prices
        """
        import asyncio
        
        # Create tasks for parallel price verification
        tasks = []
        for product in products:
            product_url = product.get("product_url")
            if product_url and not product.get("price"):
                task = self.verify_product_price(
                    product_url=product_url,
                    product_name=product.get("name"),
                    store_name=product.get("store_name")
                )
                tasks.append((product, task))
        
        # Execute all verifications in parallel
        results = await asyncio.gather(*[task for _, task in tasks], return_exceptions=True)
        
        # Update products with verified prices
        for i, ((product, _), result) in enumerate(zip(tasks, results)):
            if isinstance(result, dict) and result.get("price"):
                product["price"] = result["price"]
                product["price_source"] = "web_search_verified"
                logger.debug(f"✅ Verified price for {product.get('name', 'Unknown')}: ${result['price']}")
        
        return products

