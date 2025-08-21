"""
Enhanced scraper service with location-based search and product matching
"""

import time
import logging
import asyncio
from typing import List, Dict, Optional
from datetime import datetime

from .core import GroceryScraper
from .location_service import LocationService
from .product_matcher import ProductMatcher
from .models import (
    LocationQuery, LocationSearchResponse, ScrapeResponse, 
    ProductListing, StoreLocation
)

logger = logging.getLogger(__name__)

class EnhancedScraper:
    """Enhanced scraper with location-based search and product matching"""
    
    def __init__(self):
        self.scraper = GroceryScraper()
        self.location_service = LocationService()
        self.product_matcher = ProductMatcher()
        
    async def search_by_location(self, query: LocationQuery) -> LocationSearchResponse:
        """Search for products across multiple stores in a location"""
        start_time = time.time()
        
        # Validate zipcode
        if not self.location_service.validate_zipcode(query.zipcode):
            return LocationSearchResponse(
                success=False,
                query=query.query,
                zipcode=query.zipcode,
                stores_found=0,
                total_products=0,
                store_results={},
                best_matches=[],
                alternatives=[],
                search_metadata={"error": "Invalid zipcode format"},
                timestamp=datetime.now()
            )
        
        # Get stores for the zipcode
        stores = self.location_service.get_nearby_stores(
            query.zipcode, 
            query.radius_miles
        )
        
        if not stores:
            return LocationSearchResponse(
                success=False,
                query=query.query,
                zipcode=query.zipcode,
                stores_found=0,
                total_products=0,
                store_results={},
                best_matches=[],
                alternatives=[],
                search_metadata={"error": "No stores found in this area"},
                timestamp=datetime.now()
            )
        
        logger.info(f"Searching {len(stores)} stores for '{query.query}' in {query.zipcode}")
        
        # Scrape each store
        store_results = {}
        all_products = []
        
        for store in stores:
            try:
                # Scrape the store
                scrape_response = await self._scrape_store(
                    query.query, 
                    store.store_id, 
                    query.zipcode
                )
                
                if scrape_response.success:
                    # Enhance product data with matching information
                    enhanced_products = []
                    for product in scrape_response.listings:
                        enhanced_product = self.product_matcher.enhance_product_data(
                            product, query.query
                        )
                        enhanced_products.append(enhanced_product)
                    
                    # Update the response with enhanced products
                    scrape_response.listings = enhanced_products
                    scrape_response.result_count = len(enhanced_products)
                    
                    store_results[store.store_id] = scrape_response
                    all_products.extend(enhanced_products)
                    
            except Exception as e:
                logger.error(f"Error scraping {store.store_id}: {e}")
                continue
        
        # Process results
        search_duration = int((time.time() - start_time) * 1000)
        
        # Filter by confidence
        filtered_products = self.product_matcher.filter_by_confidence(
            all_products, query.min_confidence
        )
        
        # Sort by relevance
        sorted_products = self.product_matcher.sort_by_relevance(filtered_products)
        
        # Get best matches
        best_matches = sorted_products[:query.max_results]
        
        # Find alternatives if requested
        alternatives = []
        if query.include_alternatives:
            alternatives = self.product_matcher.find_alternatives(
                query.query, all_products
            )
        
        # Create search metadata
        search_metadata = {
            "search_duration_ms": search_duration,
            "stores_searched": len(stores),
            "stores_with_results": len(store_results),
            "total_products_found": len(all_products),
            "products_after_filtering": len(filtered_products),
            "min_confidence": query.min_confidence,
            "alternatives_found": len(alternatives)
        }
        
        return LocationSearchResponse(
            success=True,
            query=query.query,
            zipcode=query.zipcode,
            stores_found=len(stores),
            total_products=len(best_matches),
            store_results=store_results,
            best_matches=best_matches,
            alternatives=alternatives,
            search_metadata=search_metadata,
            timestamp=datetime.now()
        )
    
    async def _scrape_store(self, query: str, store_id: str, zipcode: str) -> ScrapeResponse:
        """Scrape a single store"""
        try:
            # Use the existing scraper
            results = await asyncio.get_event_loop().run_in_executor(
                None,
                self.scraper.scrape_store,
                query,
                store_id,
                zipcode
            )
            return results
            
        except Exception as e:
            logger.error(f"Error scraping {store_id}: {e}")
            return ScrapeResponse(
                success=False,
                store=store_id,
                query=query,
                zipcode=zipcode,
                result_count=0,
                listings=[],
                error=str(e),
                timestamp=datetime.now()
            )
    
    def get_store_coverage(self) -> Dict[str, List[str]]:
        """Get store coverage information"""
        return self.location_service.get_store_coverage_info()
    
    def suggest_queries(self, partial_query: str) -> List[str]:
        """Suggest queries based on partial input"""
        return self.product_matcher.suggest_queries(partial_query)
    
    def get_product_synonyms(self, query: str) -> List[str]:
        """Get synonyms for a product query"""
        return self.product_matcher.get_product_synonyms(query)
    
    def get_store_services(self, store_id: str) -> List[str]:
        """Get available services for a store"""
        return self.location_service.get_store_services(store_id)
