"""
Universal Grocery Search Service
Orchestrates multi-strategy search across stores with optimal query understanding
"""

from typing import Dict, List, Optional
import asyncio
import logging
from datetime import datetime

from scraper.query_understanding import QueryUnderstanding
from scraper.result_ranker import ResultRanker
from scraper.exa_structured_client import ExaStructuredClient

logger = logging.getLogger(__name__)

class UniversalGrocerySearch:
    """Universal grocery search with multi-strategy approach"""
    
    def __init__(self, exa_client: ExaStructuredClient):
        """Initialize universal search service"""
        self.exa_client = exa_client
        self.query_understanding = QueryUnderstanding()
        self.result_ranker = ResultRanker(self.query_understanding)
    
    async def search(
        self,
        query: str,
        zipcode: Optional[str] = None,
        store_name: Optional[str] = None,
        num_results: int = 20,
        limit: Optional[int] = None,
        context: Optional[str] = None
    ) -> Dict:
        """
        Universal search with query understanding and multi-strategy approach
        
        Args:
            query: User search query
            zipcode: Optional zipcode for location filtering
            store_name: Optional store name filter
            num_results: Number of results per strategy
            limit: Final result limit
            context: Additional context
            
        Returns:
            Search results with metadata
        """
        start_time = datetime.now()
        
        # 1. Understand query
        query_analysis = self.query_understanding.analyze(query)
        optimal_queries = self.query_understanding.build_optimal_query(query, zipcode, store_name)
        
        logger.info(f"🔍 Universal search: '{query}' | Intent: {query_analysis['intent']} | Brand: {query_analysis['has_brand']} | Category: {query_analysis['has_category']}")
        
        # 2. Multi-strategy search
        result_sets = []
        
        # Strategy 1: Primary enhanced query (always run)
        try:
            primary_results = await self._search_with_exa(
                optimal_queries['primary'],
                zipcode,
                store_name,
                num_results
            )
            result_sets.append(primary_results)
            logger.info(f"✅ Primary search: {len(primary_results)} results")
        except Exception as e:
            logger.warning(f"⚠️ Primary search failed: {e}")
        
        # Strategy 2: Expanded queries (if primary didn't yield enough)
        if len(primary_results) < num_results // 2 and optimal_queries['expanded']:
            try:
                expanded_results = await self._search_expanded_queries(
                    optimal_queries['expanded'],
                    zipcode,
                    store_name,
                    num_results // 2
                )
                result_sets.append(expanded_results)
                logger.info(f"✅ Expanded search: {len(expanded_results)} results")
            except Exception as e:
                logger.warning(f"⚠️ Expanded search failed: {e}")
        
        # Strategy 3: Category-based (if category detected)
        if optimal_queries['category_based'] and query_analysis['has_category']:
            try:
                category_results = await self._search_with_exa(
                    optimal_queries['category_based'],
                    zipcode,
                    store_name,
                    num_results // 2
                )
                result_sets.append(category_results)
                logger.info(f"✅ Category search: {len(category_results)} results")
            except Exception as e:
                logger.warning(f"⚠️ Category search failed: {e}")
        
        # Strategy 4: Brand-based (if brand detected)
        if optimal_queries['brand_based'] and query_analysis['has_brand']:
            try:
                brand_results = await self._search_with_exa(
                    optimal_queries['brand_based'],
                    zipcode,
                    store_name,
                    num_results // 2
                )
                result_sets.append(brand_results)
                logger.info(f"✅ Brand search: {len(brand_results)} results")
            except Exception as e:
                logger.warning(f"⚠️ Brand search failed: {e}")
        
        # 3. Merge, deduplicate, and rank
        final_results = self.result_ranker.merge_results(
            result_sets,
            query,
            limit or num_results
        )
        
        # 4. Calculate search metadata
        search_duration = (datetime.now() - start_time).total_seconds()
        
        return {
            "query": query,
            "query_analysis": {
                "intent": query_analysis['intent'],
                "entities": self.query_understanding.extract_entities(query),
                "optimal_queries": optimal_queries
            },
            "results": final_results,
            "total": len(final_results),
            "search_metadata": {
                "strategies_used": len(result_sets),
                "duration_seconds": round(search_duration, 3),
                "zipcode": zipcode,
                "store_filter": store_name
            }
        }
    
    async def _search_with_exa(
        self,
        search_query: str,
        zipcode: Optional[str],
        store_name: Optional[str],
        num_results: int
    ) -> List[Dict]:
        """Search using Exa API"""
        if not self.exa_client.is_available():
            return []
        
        try:
            products = await self.exa_client.search_products_structured(
                query=search_query,
                store_name=store_name,
                zipcode=zipcode,
                num_results=num_results,
                include_location=True
            )
            return products
        except Exception as e:
            logger.error(f"❌ Exa search failed: {e}")
            return []
    
    async def _search_expanded_queries(
        self,
        expanded_queries: List[str],
        zipcode: Optional[str],
        store_name: Optional[str],
        num_results_per_query: int
    ) -> List[Dict]:
        """Search with multiple expanded queries in parallel"""
        if not expanded_queries:
            return []
        
        # Run expanded queries in parallel
        tasks = [
            self._search_with_exa(query, zipcode, store_name, num_results_per_query)
            for query in expanded_queries
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Flatten results and filter exceptions
        all_results = []
        for result in results:
            if isinstance(result, list):
                all_results.extend(result)
            elif isinstance(result, Exception):
                logger.warning(f"⚠️ Expanded query failed: {result}")
        
        return all_results
    
    async def search_aggregate(
        self,
        query: str,
        zipcode: str,
        store_ids: Optional[List[str]] = None,
        limit: Optional[int] = None
    ) -> Dict:
        """
        Aggregate search across multiple stores with universal search
        
        This enhances the existing aggregate endpoint with query understanding
        """
        # Understand query
        query_analysis = self.query_understanding.analyze(query)
        optimal_queries = self.query_understanding.build_optimal_query(query, zipcode)
        
        # Use primary enhanced query for aggregate search
        enhanced_query = optimal_queries['primary']
        
        # Delegate to existing aggregate logic but with enhanced query
        # This will be integrated into main.py
        return {
            "query": query,
            "enhanced_query": enhanced_query,
            "query_analysis": query_analysis
        }

