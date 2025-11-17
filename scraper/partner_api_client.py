"""
Unified Partner API Client - Routes to official APIs when available, falls back to Exa
"""
import logging
from typing import List, Dict, Any, Optional
from .target_api_client import TargetAPIClient
from .kroger_api_client import KrogerAPIClient
from .walmart_api_client import WalmartAPIClient

logger = logging.getLogger(__name__)

def is_chicago_area_zipcode(zipcode: Optional[str]) -> bool:
    """
    Check if a zipcode is in the Chicago metropolitan area (Illinois)
    Mariano's operates exclusively in Illinois, primarily in the Chicago metropolitan area
    
    Chicago area zip codes:
    - 60000-60999: Northern suburbs (Cook, Lake, DuPage, Kane, McHenry counties)
    - 60601-60699: Chicago city
    """
    if not zipcode or len(zipcode) != 5:
        return False
    
    try:
        zip_int = int(zipcode)
        # Chicago city: 60601-60699
        if 60601 <= zip_int <= 60699:
            return True
        # Northern suburbs: 60000-60999
        if 60000 <= zip_int <= 60999:
            return True
        return False
    except ValueError:
        return False

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
        elif store_id_lower == "marianos" or store_id_lower == "mariano's":
            # Mariano's uses Kroger API (same parent company)
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
            
            elif (store_id_lower == "kroger" or store_id_lower == "marianos" or store_id_lower == "mariano's") and self.kroger_client.is_available():
                # Check if this should be Mariano's (Chicago area) or Kroger
                is_marianos = False
                if store_id_lower == "marianos" or store_id_lower == "mariano's":
                    is_marianos = True
                elif store_id_lower == "kroger" and zipcode and is_chicago_area_zipcode(zipcode):
                    # If searching Kroger in Chicago area, use Mariano's branding
                    is_marianos = True
                    logger.info(f"📍 Chicago area zipcode detected ({zipcode}), using Mariano's branding")
                
                if is_marianos:
                    logger.info(f"🛒 Using Kroger API (Mariano's branding) for '{query}' in Chicago area")
                else:
                    logger.info(f"🛒 Using Kroger official API for '{query}'")
                
                if zipcode:
                    products = await self.kroger_client.search_products_multiple_stores(
                        query=query,
                        zipcode=zipcode,
                        limit_per_store=limit // 3  # Distribute across stores
                    )
                    
                    # If Mariano's, update store_name and product URLs in products
                    if is_marianos:
                        for product in products:
                            # Update store_name to Mariano's
                            if product.get("store_name") == "Kroger":
                                product["store_name"] = "Mariano's"
                            # Also update any chain references
                            if "chain" in product and product["chain"] == "Kroger":
                                product["chain"] = "Mariano's"
                            # Convert Kroger URLs to Mariano's URLs
                            product_url = product.get("product_url", "")
                            if product_url and "kroger.com" in product_url:
                                product["product_url"] = product_url.replace("kroger.com", "marianos.com")
                else:
                    # Without zipcode, we can't use Kroger API (requires store_id)
                    logger.warning("Kroger/Mariano's API requires zipcode for store lookup")
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
            # Handle Mariano's store_id mapping
            normalized_store_id = store_id.lower()
            if normalized_store_id == "marianos" or normalized_store_id == "mariano's":
                normalized_store_id = "marianos"  # Use consistent format
            elif normalized_store_id == "kroger" and zipcode and is_chicago_area_zipcode(zipcode):
                normalized_store_id = "marianos"  # Map Kroger in Chicago to Mariano's
            
            return self._normalize_product_format(products, normalized_store_id)
                
        except Exception as e:
            logger.error(f"Error using partner API for {store_id}: {e}", exc_info=True)
            return []
    
    def _normalize_product_format(self, products: List[Dict[str, Any]], store_id: str) -> List[Dict[str, Any]]:
        """Normalize product format from partner APIs to match Exa format"""
        normalized = []
        # Map store_id to display name
        store_display_name = store_id
        if store_id.lower() == "marianos":
            store_display_name = "Mariano's"
        elif store_id.lower() == "kroger":
            store_display_name = "Kroger"
        elif store_id.lower() == "target":
            store_display_name = "Target"
        elif store_id.lower() == "walmart":
            store_display_name = "Walmart"
        
        for product in products:
            # Convert source from list to string if needed
            if isinstance(product.get("source"), list):
                product["source"] = ", ".join(product["source"]) if product["source"] else "partner_api"
            elif not product.get("source"):
                product["source"] = "partner_api"
            
            # Use product's store_name if available, otherwise use store_display_name
            product_store_name = product.get("store_name") or store_display_name
            
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
                "store_name": product_store_name,
                "store_zipcode": product.get("store_zipcode"),
                "description": product.get("description"),
                "category": product.get("category"),
                "source": product.get("source", "partner_api"),
                "upc": product.get("upc"),
            }
            normalized.append(normalized_product)
        return normalized

