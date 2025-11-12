"""
Unified Partner API Client - Routes to official APIs when available, falls back to Exa
"""
import logging
from typing import List, Dict, Any, Optional
from .target_api_client import TargetAPIClient
from .kroger_api_client import KrogerAPIClient
from .walmart_api_client import WalmartAPIClient

logger = logging.getLogger(__name__)

class PartnerAPIClient:
    """Unified client that uses official partner APIs when available"""
    
    # Map of store IDs to their API clients
    STORE_API_MAP = {
        "target": "target",
        "kroger": "kroger",
        "walmart": "walmart",
    }
    
    def __init__(self):
        """Initialize partner API clients"""
        self.target_client = TargetAPIClient()
        self.kroger_client = KrogerAPIClient()
        self.walmart_client = WalmartAPIClient()
        
        # Log availability
        logger.info(f"📡 Partner APIs: Target={self.target_client.is_available()}, "
                   f"Kroger={self.kroger_client.is_available()}, "
                   f"Walmart={self.walmart_client.is_available()}")
    
    def has_partner_api(self, store_id: str) -> bool:
        """Check if a store has an official partner API"""
        store_id_lower = store_id.lower()
        
        if store_id_lower == "target":
            return self.target_client.is_available()
        elif store_id_lower == "kroger":
            return self.kroger_client.is_available()
        elif store_id_lower == "walmart":
            return self.walmart_client.is_available()
        
        return False
    
    async def search_products(
        self,
        store_id: str,
        query: str,
        zipcode: Optional[str] = None,
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """
        Search products using official partner API if available
        
        Args:
            store_id: Store identifier (target, kroger, walmart)
            query: Product search query
            zipcode: Optional zipcode for location-based search
            limit: Maximum number of results
            
        Returns:
            List of product dictionaries in standard format
        """
        store_id_lower = store_id.lower()
        
        try:
            products = []
            
            if store_id_lower == "target" and self.target_client.is_available():
                logger.info(f"🎯 Using Target official API for '{query}'")
                if zipcode:
                    products = await self.target_client.search_products_multiple_stores(
                        query=query,
                        zipcode=zipcode,
                        limit_per_store=limit // 3  # Distribute across stores
                    )
                else:
                    # Without zipcode, we can't use Target API (requires store_id)
                    logger.warning("Target API requires zipcode for store lookup")
                    return []
            
            elif store_id_lower == "kroger" and self.kroger_client.is_available():
                logger.info(f"🛒 Using Kroger official API for '{query}'")
                if zipcode:
                    products = await self.kroger_client.search_products_multiple_stores(
                        query=query,
                        zipcode=zipcode,
                        limit_per_store=limit // 3  # Distribute across stores
                    )
                else:
                    # Without zipcode, we can't use Kroger API (requires store_id)
                    logger.warning("Kroger API requires zipcode for store lookup")
                    return []
            
            elif store_id_lower == "walmart" and self.walmart_client.is_available():
                logger.info(f"🏪 Using Walmart official API for '{query}'")
                # Walmart API doesn't require zipcode/store_id for basic search
                products = await self.walmart_client.search_products(
                    query=query,
                    limit=limit
                )
            
            else:
                # No partner API available for this store
                logger.debug(f"No partner API available for {store_id}, will use Exa fallback")
                return []
            
            # Normalize product format to match Exa format
            return self._normalize_product_format(products, store_id)
                
        except Exception as e:
            logger.error(f"Error using partner API for {store_id}: {e}", exc_info=True)
            return []
    
    def _normalize_product_format(self, products: List[Dict[str, Any]], store_id: str) -> List[Dict[str, Any]]:
        """Normalize product format from partner APIs to match Exa format"""
        normalized = []
        for product in products:
            # Convert source from list to string if needed
            if isinstance(product.get("source"), list):
                product["source"] = ", ".join(product["source"]) if product["source"] else "partner_api"
            elif not product.get("source"):
                product["source"] = "partner_api"
            
            # Ensure all required fields exist
            normalized_product = {
                "name": product.get("name", ""),
                "brand": product.get("brand"),
                "price": product.get("price"),
                "currency": product.get("currency", "USD"),
                "quantity": product.get("quantity"),
                "size": product.get("size"),
                "availability": product.get("availability", "Check Store"),
                "product_url": product.get("product_url"),
                "image_url": product.get("image_url"),
                "store_name": product.get("store_name", store_id),
                "store_zipcode": product.get("store_zipcode"),
                "description": product.get("description"),
                "category": product.get("category"),
                "source": product.get("source", "partner_api"),
                "upc": product.get("upc"),
            }
            normalized.append(normalized_product)
        return normalized

