"""
URL Location Enhancer
Adds location/zipcode parameters to product URLs for stores that support it
"""

import logging
from typing import Optional
from urllib.parse import urlparse, parse_qs, urlencode, urlunparse

logger = logging.getLogger(__name__)

class URLLocationEnhancer:
    """Enhance product URLs with location parameters"""
    
    @staticmethod
    def enhance_url_with_location(product_url: str, zipcode: Optional[str] = None, store_id: Optional[str] = None) -> str:
        """
        Add location parameters to product URLs for stores that support it
        
        Args:
            product_url: Original product URL
            zipcode: ZIP code to add to URL
            store_id: Store identifier (target, walmart, etc.)
            
        Returns:
            Enhanced URL with location parameters if supported, original URL otherwise
        """
        if not product_url or not zipcode:
            return product_url
        
        store_id_lower = (store_id or "").lower()
        url_lower = product_url.lower()
        
        try:
            parsed = urlparse(product_url)
            query_params = parse_qs(parsed.query)
            
            # Target: Add zipcode parameter
            if 'target.com' in url_lower or store_id_lower == 'target':
                # Target uses ?zip=ZIPCODE parameter
                query_params['zip'] = [zipcode]
                new_query = urlencode(query_params, doseq=True)
                enhanced_url = urlunparse((
                    parsed.scheme,
                    parsed.netloc,
                    parsed.path,
                    parsed.params,
                    new_query,
                    parsed.fragment
                ))
                logger.debug(f"✅ Enhanced Target URL with zipcode: {zipcode}")
                return enhanced_url
            
            # Walmart: Add zipcode parameter
            elif 'walmart.com' in url_lower or store_id_lower == 'walmart':
                # Walmart uses ?zipCode=ZIPCODE parameter
                query_params['zipCode'] = [zipcode]
                new_query = urlencode(query_params, doseq=True)
                enhanced_url = urlunparse((
                    parsed.scheme,
                    parsed.netloc,
                    parsed.path,
                    parsed.params,
                    new_query,
                    parsed.fragment
                ))
                logger.debug(f"✅ Enhanced Walmart URL with zipcode: {zipcode}")
                return enhanced_url
            
            # Kroger: Add zipcode parameter
            elif 'kroger.com' in url_lower or store_id_lower == 'kroger':
                # Kroger uses ?zipcode=ZIPCODE parameter
                query_params['zipcode'] = [zipcode]
                new_query = urlencode(query_params, doseq=True)
                enhanced_url = urlunparse((
                    parsed.scheme,
                    parsed.netloc,
                    parsed.path,
                    parsed.params,
                    new_query,
                    parsed.fragment
                ))
                logger.debug(f"✅ Enhanced Kroger URL with zipcode: {zipcode}")
                return enhanced_url
            
            # Whole Foods: Add zipcode parameter
            elif 'wholefoodsmarket.com' in url_lower or store_id_lower == 'whole_foods':
                # Whole Foods uses ?zip=ZIPCODE parameter
                query_params['zip'] = [zipcode]
                new_query = urlencode(query_params, doseq=True)
                enhanced_url = urlunparse((
                    parsed.scheme,
                    parsed.netloc,
                    parsed.path,
                    parsed.params,
                    new_query,
                    parsed.fragment
                ))
                logger.debug(f"✅ Enhanced Whole Foods URL with zipcode: {zipcode}")
                return enhanced_url
            
            # Safeway/Albertsons: Add zipcode parameter
            elif any(domain in url_lower for domain in ['safeway.com', 'albertsons.com']) or store_id_lower in ['safeway', 'albertsons']:
                # Safeway uses ?zipcode=ZIPCODE parameter
                query_params['zipcode'] = [zipcode]
                new_query = urlencode(query_params, doseq=True)
                enhanced_url = urlunparse((
                    parsed.scheme,
                    parsed.netloc,
                    parsed.path,
                    parsed.params,
                    new_query,
                    parsed.fragment
                ))
                logger.debug(f"✅ Enhanced Safeway/Albertsons URL with zipcode: {zipcode}")
                return enhanced_url
            
            # For other stores, return original URL
            # (They may require location to be set via cookies/session)
            return product_url
            
        except Exception as e:
            logger.debug(f"Failed to enhance URL with location: {e}")
            return product_url

