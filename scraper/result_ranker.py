"""
Result Ranking and Relevance Scoring Service
Ranks search results by relevance to user query
"""

from typing import Dict, List, Optional
import re
from difflib import SequenceMatcher

class ResultRanker:
    """Rank and score search results by relevance"""
    
    def __init__(self, query_understanding):
        """Initialize with query understanding service"""
        self.query_understanding = query_understanding
    
    def rank_results(
        self,
        results: List[Dict],
        query: str,
        query_analysis: Optional[Dict] = None
    ) -> List[Dict]:
        """Rank results by relevance to query"""
        if not results:
            return []
        
        # Analyze query if not provided
        if query_analysis is None:
            query_analysis = self.query_understanding.analyze(query)
        
        # Score each result
        scored_results = []
        for result in results:
            score = self._calculate_relevance_score(result, query, query_analysis)
            result['relevance_score'] = score
            scored_results.append(result)
        
        # Sort by score (highest first)
        ranked = sorted(scored_results, key=lambda x: x.get('relevance_score', 0), reverse=True)
        
        return ranked
    
    def _calculate_relevance_score(
        self,
        result: Dict,
        query: str,
        query_analysis: Dict
    ) -> float:
        """Calculate relevance score for a result"""
        score = 0.0
        query_lower = query.lower()
        
        # Get result fields
        name = (result.get('name') or result.get('product_name') or '').lower()
        brand = (result.get('brand') or '').lower()
        description = (result.get('description') or '').lower()
        category = (result.get('category') or '').lower()
        
        # 1. Exact name match (highest priority)
        if query_lower in name:
            score += 20.0
        elif query_analysis['cleaned'] in name:
            score += 15.0
        
        # 2. Token matching (all tokens in name)
        query_tokens = set(query_analysis['tokens'])
        name_tokens = set(name.split())
        matched_tokens = query_tokens.intersection(name_tokens)
        if matched_tokens:
            score += len(matched_tokens) * 3.0
        
        # 3. Brand matching
        if query_analysis['has_brand']:
            query_brand = query_analysis['has_brand'].lower()
            if query_brand in brand:
                score += 10.0
            elif brand and query_brand in name:
                score += 7.0
        
        # 4. Category matching
        if query_analysis['has_category']:
            query_category = query_analysis['has_category'].lower()
            if query_category in category:
                score += 8.0
            elif query_category in name or query_category in description:
                score += 5.0
        
        # 5. Attribute matching
        if query_analysis['has_attribute']:
            for attr in query_analysis['has_attribute']:
                attr_lower = attr.lower()
                if attr_lower in name:
                    score += 5.0
                elif attr_lower in description:
                    score += 3.0
        
        # 6. Quantity matching
        if query_analysis['has_quantity']:
            quantity = query_analysis['has_quantity'].lower()
            if quantity in name:
                score += 4.0
        
        # 7. String similarity (fuzzy matching)
        similarity = self._string_similarity(query_lower, name)
        score += similarity * 5.0
        
        # 8. Description relevance
        if description:
            desc_score = self._calculate_description_score(description, query_analysis)
            score += desc_score * 2.0
        
        # 9. Data completeness bonus
        if result.get('price'):
            score += 2.0
        if result.get('image_url'):
            score += 1.5
        if result.get('store_name'):
            score += 1.0
        if result.get('availability'):
            score += 0.5
        
        # 10. Product name extraction matching
        product_name = self.query_understanding._extract_product_name(query)
        if product_name and product_name in name:
            score += 6.0
        
        return score
    
    def _string_similarity(self, str1: str, str2: str) -> float:
        """Calculate string similarity using SequenceMatcher"""
        return SequenceMatcher(None, str1, str2).ratio()
    
    def _calculate_description_score(self, description: str, query_analysis: Dict) -> float:
        """Calculate how well description matches query"""
        score = 0.0
        desc_lower = description.lower()
        
        # Check for query tokens in description
        query_tokens = set(query_analysis['tokens'])
        desc_tokens = set(desc_lower.split())
        matched = query_tokens.intersection(desc_tokens)
        if matched:
            score += len(matched) * 0.5
        
        # Check for brand
        if query_analysis['has_brand']:
            if query_analysis['has_brand'].lower() in desc_lower:
                score += 1.0
        
        # Check for attributes
        if query_analysis['has_attribute']:
            for attr in query_analysis['has_attribute']:
                if attr.lower() in desc_lower:
                    score += 0.5
        
        return min(score, 5.0)  # Cap at 5.0
    
    def deduplicate_results(
        self,
        results: List[Dict],
        similarity_threshold: float = 0.85
    ) -> List[Dict]:
        """Remove duplicate results based on name and URL similarity"""
        if not results:
            return []
        
        unique_results = []
        seen_urls = set()
        seen_names = {}
        
        for result in results:
            url = result.get('product_url') or result.get('url') or ''
            name = (result.get('name') or result.get('product_name') or '').lower()
            
            # Skip if URL already seen
            if url and url in seen_urls:
                continue
            
            # Check name similarity with existing results
            is_duplicate = False
            for seen_name, seen_result in seen_names.items():
                similarity = self._string_similarity(name, seen_name)
                if similarity >= similarity_threshold:
                    # Keep the one with higher relevance score
                    if result.get('relevance_score', 0) > seen_result.get('relevance_score', 0):
                        unique_results.remove(seen_result)
                        seen_names.pop(seen_name)
                        break
                    else:
                        is_duplicate = True
                        break
            
            if not is_duplicate:
                unique_results.append(result)
                if url:
                    seen_urls.add(url)
                if name:
                    seen_names[name] = result
        
        return unique_results
    
    def merge_results(
        self,
        result_sets: List[List[Dict]],
        query: str,
        limit: Optional[int] = None
    ) -> List[Dict]:
        """Merge multiple result sets, deduplicate, and rank"""
        # Flatten all results
        all_results = []
        for result_set in result_sets:
            all_results.extend(result_set)
        
        if not all_results:
            return []
        
        # Deduplicate
        unique_results = self.deduplicate_results(all_results)
        
        # Rank by relevance
        ranked_results = self.rank_results(unique_results, query)
        
        # Apply limit
        if limit:
            ranked_results = ranked_results[:limit]
        
        return ranked_results

