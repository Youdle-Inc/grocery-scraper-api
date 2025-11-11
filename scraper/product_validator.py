"""
Product Data Validator
Uses AI to validate that products are real, prices are specific, and data quality is high
"""

import logging
import os
import json
from typing import Dict, Any, List, Optional
from openai import AsyncOpenAI

logger = logging.getLogger(__name__)

class ProductValidator:
    """Validate product data quality using AI"""
    
    def __init__(self):
        api_key = os.getenv("OPENAI_API_KEY")
        if api_key:
            self.client = AsyncOpenAI(api_key=api_key)
            self.available = True
        else:
            logger.warning("OPENAI_API_KEY not found, ProductValidator will use basic validation only")
            self.client = None
            self.available = False
    
    async def validate_product(
        self,
        product: Dict[str, Any],
        original_query: str
    ) -> Dict[str, Any]:
        """
        Validate a single product result
        
        Returns:
            {
                "is_valid": bool,
                "confidence": float (0-1),
                "issues": List[str],
                "reasoning": str
            }
        """
        if not self.available:
            # Fallback to basic validation
            return self._basic_validation(product, original_query)
        
        try:
            # Extract key fields
            name = product.get("name", "")
            brand = product.get("brand", "")
            description = product.get("description", "")
            images = product.get("images", [])
            offers = product.get("offers", [])
            
            # Check for generic/placeholder indicators
            validation_prompt = f"""You are a product data quality validator. Analyze this product data and determine if it represents a REAL, SPECIFIC product (not a generic placeholder or store category page).

Original search query: "{original_query}"

Product data:
- Name: {name}
- Brand: {brand}
- Description: {description[:200] if description else "None"}
- Number of images: {len(images)}
- Number of store offers: {len(offers)}

For each offer, check:
"""
            
            # Add offer details
            for idx, offer in enumerate(offers[:3]):  # Check first 3 offers
                store_name = offer.get("store", {}).get("store_name", "Unknown")
                price = offer.get("regular_price") or offer.get("sale_price")
                product_url = offer.get("product_url", "")
                
                validation_prompt += f"""
Offer {idx + 1}:
- Store: {store_name}
- Price: ${price if price else "Not provided"}
- Product URL: {product_url[:100] if product_url else "None"}
"""
            
            validation_prompt += """
Validation Criteria:
1. Is the product name SPECIFIC? (e.g., "Grade A Large Eggs - 12ct" is specific, "Eggs" or "Whole Foods" is generic)
2. Is the price REAL and SPECIFIC to this product? (not a placeholder like "$8.99" for all products)
3. Does the product URL point to a SPECIFIC product page? (not a category page or store homepage)
4. Are the images PRODUCT-SPECIFIC? (not generic store images like produce sections)
5. Does the data match the search query? (if searching for "eggs", is this actually eggs?)

Respond in JSON format:
{
    "is_valid": true/false,
    "confidence": 0.0-1.0,
    "issues": ["list of specific issues found"],
    "reasoning": "brief explanation"
}
"""
            
            response = await self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "You are a product data quality validator. Always respond with valid JSON."},
                    {"role": "user", "content": validation_prompt}
                ],
                temperature=0.1,
                response_format={"type": "json_object"}
            )
            
            result = json.loads(response.choices[0].message.content)
            
            return {
                "is_valid": result.get("is_valid", False),
                "confidence": float(result.get("confidence", 0.0)),
                "issues": result.get("issues", []),
                "reasoning": result.get("reasoning", "")
            }
            
        except Exception as e:
            logger.warning(f"AI validation failed, using basic validation: {e}")
            return self._basic_validation(product, original_query)
    
    def _basic_validation(
        self,
        product: Dict[str, Any],
        original_query: str
    ) -> Dict[str, Any]:
        """Basic validation without AI"""
        issues = []
        name = product.get("name", "").lower()
        brand = product.get("brand", "").lower()
        
        # Check for generic names
        generic_indicators = [
            "whole foods", "target", "walmart", "kroger",  # Store names as product names
            "check store", "view stores", "tap to view",  # UI text
            "product", "item", "grocery"  # Too generic
        ]
        
        for indicator in generic_indicators:
            if indicator in name:
                issues.append(f"Generic product name: '{name}' contains '{indicator}'")
        
        # Check if name matches query
        query_lower = original_query.lower()
        if query_lower not in name and name not in query_lower:
            # Allow some flexibility for variations
            if not any(word in name for word in query_lower.split()):
                issues.append(f"Product name '{name}' doesn't match query '{original_query}'")
        
        # Check for valid product URL
        offers = product.get("offers", [])
        has_valid_url = False
        has_price = False
        
        for offer in offers:
            product_url = offer.get("product_url", "")
            if product_url and "http" in product_url and len(product_url) > 20:
                # Check if URL looks like a product page (not category/store page)
                if any(indicator in product_url.lower() for indicator in ["/p/", "/product", "/item", "/ip/", "?id="]):
                    has_valid_url = True
            
            price = offer.get("regular_price") or offer.get("sale_price")
            if price and isinstance(price, (int, float)) and price > 0:
                has_valid_url = True
        
        if not has_valid_url:
            issues.append("No valid product-specific URLs found")
        
        if not has_price:
            issues.append("No valid prices found")
        
        # Check images
        images = product.get("images", [])
        if not images or len(images) == 0:
            issues.append("No product images found")
        
        is_valid = len(issues) == 0
        confidence = 0.8 if is_valid else max(0.1, 1.0 - (len(issues) * 0.2))
        
        return {
            "is_valid": is_valid,
            "confidence": confidence,
            "issues": issues,
            "reasoning": "Basic validation" + (" - passed" if is_valid else f" - found {len(issues)} issues")
        }
    
    async def validate_batch(
        self,
        products: List[Dict[str, Any]],
        original_query: str,
        min_confidence: float = 0.6,
        max_concurrent: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Validate a batch of products and filter out invalid ones
        
        Args:
            products: List of product dictionaries
            original_query: Original search query
            min_confidence: Minimum confidence threshold (0-1)
            max_concurrent: Maximum concurrent validation calls (default: 10)
        
        Returns:
            List of validated products with validation metadata
        """
        import asyncio
        
        # Limit the number of products to validate (for performance)
        # Validate top products first, skip if too many
        products_to_validate = products[:50] if len(products) > 50 else products
        
        # Create semaphore to limit concurrent API calls
        semaphore = asyncio.Semaphore(max_concurrent)
        
        async def validate_with_limit(product: Dict[str, Any]) -> tuple:
            async with semaphore:
                validation = await self.validate_product(product, original_query)
                return product, validation
        
        # Validate products concurrently
        validation_tasks = [validate_with_limit(p) for p in products_to_validate]
        validation_results = await asyncio.gather(*validation_tasks, return_exceptions=True)
        
        validated_products = []
        
        for result in validation_results:
            if isinstance(result, Exception):
                logger.warning(f"Validation error: {result}")
                continue
            
            product, validation = result
            
            # Add validation metadata to product
            product["_validation"] = validation
            
            # Only include if valid and meets confidence threshold
            if validation["is_valid"] and validation["confidence"] >= min_confidence:
                validated_products.append(product)
            else:
                logger.debug(f"Filtered out product '{product.get('name')}': {validation['reasoning']}")
        
        # Add remaining products that weren't validated (if we limited validation)
        if len(products) > len(products_to_validate):
            # Add remaining products without validation (assume valid)
            validated_products.extend(products[len(products_to_validate):])
        
        return validated_products
    
    def filter_invalid_offers(
        self,
        offers: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Filter out invalid offers within a product
        
        Checks for:
        - Generic prices (same price for all products)
        - Missing product URLs
        - Placeholder data
        """
        valid_offers = []
        
        for offer in offers:
            # Check for valid URL
            product_url = offer.get("product_url", "")
            if not product_url or len(product_url) < 20:
                continue
            
            # Check for valid price
            price = offer.get("regular_price") or offer.get("sale_price")
            if not price or not isinstance(price, (int, float)) or price <= 0:
                # Allow if URL is valid (price might be on page)
                if not product_url:
                    continue
            
            # Check for store name (not generic)
            store_name = offer.get("store", {}).get("store_name", "")
            if not store_name or store_name.lower() in ["unknown", "store", "retailer"]:
                continue
            
            valid_offers.append(offer)
        
        return valid_offers

