"""
Search Insights Generator
Generates Perplexity-like overviews and follow-up query suggestions
"""

import logging
from typing import List, Dict, Any, Optional
from datetime import datetime

logger = logging.getLogger(__name__)

class SearchInsightsGenerator:
    """Generate search insights: overviews and follow-up queries"""
    
    def generate_overview(
        self,
        query: str,
        results: List[Dict[str, Any]],
        stores_considered: List[str],
        zipcode: str
    ) -> str:
        """
        Generate a natural language overview of the search results
        
        Args:
            query: Original search query
            results: List of product results
            stores_considered: List of store IDs searched
            zipcode: ZIP code used
            
        Returns:
            Overview text summarizing the search results
        """
        if not results:
            return f"No products found for '{query}' in the searched stores near {zipcode}."
        
        # Extract key statistics
        total_products = len(results)
        stores_with_results = set()
        price_ranges = []
        brands_found = set()
        categories_found = set()
        
        for result in results:
            # Track stores
            for offer in result.get("offers", []):
                store_id = offer.get("store", {}).get("retailer")
                if store_id:
                    stores_with_results.add(store_id)
            
            # Track prices
            for offer in result.get("offers", []):
                price = offer.get("regular_price") or offer.get("sale_price")
                if price:
                    price_ranges.append(float(price))
            
            # Track brands
            if result.get("brand"):
                brands_found.add(result["brand"])
            
            # Track categories
            category_path = result.get("category_path", [])
            if category_path:
                categories_found.add(category_path[-1] if isinstance(category_path, list) else category_path)
        
        # Build overview
        overview_parts = []
        
        # Main finding
        overview_parts.append(f"Found {total_products} product{'s' if total_products != 1 else ''} for '{query}'")
        
        # Stores
        if stores_with_results:
            store_count = len(stores_with_results)
            overview_parts.append(f"across {store_count} store{'s' if store_count != 1 else ''}")
        
        # Price range
        if price_ranges:
            min_price = min(price_ranges)
            max_price = max(price_ranges)
            if min_price == max_price:
                overview_parts.append(f"at ${min_price:.2f}")
            else:
                overview_parts.append(f"ranging from ${min_price:.2f} to ${max_price:.2f}")
        
        # Brands
        if brands_found and len(brands_found) <= 5:
            brands_list = ", ".join(sorted(list(brands_found))[:5])
            overview_parts.append(f"including brands like {brands_list}")
        
        # Categories
        if categories_found:
            categories_list = ", ".join(sorted(list(categories_found))[:3])
            overview_parts.append(f"in categories: {categories_list}")
        
        # Location
        overview_parts.append(f"near {zipcode}")
        
        overview = ". ".join(overview_parts) + "."
        
        return overview
    
    def generate_follow_up_queries(
        self,
        query: str,
        results: List[Dict[str, Any]],
        stores_considered: List[str]
    ) -> List[str]:
        """
        Generate follow-up query suggestions based on search results
        
        Args:
            query: Original search query
            results: List of product results
            stores_considered: List of store IDs searched
            
        Returns:
            List of suggested follow-up queries
        """
        suggestions = []
        
        # Extract insights from results
        brands_found = set()
        categories_found = set()
        attributes_found = set()
        
        for result in results:
            # Extract brands
            if result.get("brand"):
                brands_found.add(result["brand"])
            
            # Extract categories
            category_path = result.get("category_path", [])
            if category_path:
                if isinstance(category_path, list):
                    categories_found.update(category_path)
                else:
                    categories_found.add(category_path)
            
            # Extract attributes from name/description
            name = (result.get("name") or "").lower()
            desc = (result.get("description") or "").lower()
            text = f"{name} {desc}"
            
            # Common attributes
            if "organic" in text:
                attributes_found.add("organic")
            if "gluten-free" in text or "gluten free" in text:
                attributes_found.add("gluten-free")
            if "cage-free" in text or "cage free" in text:
                attributes_found.add("cage-free")
            if "free-range" in text or "free range" in text:
                attributes_found.add("free-range")
            if "grass-fed" in text or "grass fed" in text:
                attributes_found.add("grass-fed")
            if "non-gmo" in text or "non gmo" in text:
                attributes_found.add("non-GMO")
            if "vegan" in text:
                attributes_found.add("vegan")
            if "dairy-free" in text or "dairy free" in text:
                attributes_found.add("dairy-free")
        
        # Generate suggestions
        
        # 1. Related products in same category
        if categories_found:
            for category in list(categories_found)[:2]:
                if category and isinstance(category, str) and category.lower() != query.lower():
                    suggestions.append(f"{category.lower()}")
        
        # 2. Brand-specific queries
        if brands_found:
            for brand in list(brands_found)[:2]:
                suggestions.append(f"{brand} {query}")
        
        # 3. Attribute variations
        if attributes_found:
            for attr in list(attributes_found)[:2]:
                suggestions.append(f"{attr} {query}")
        
        # 4. Related products (semantic)
        related_products = self._get_related_products(query)
        suggestions.extend(related_products[:2])
        
        # 5. Store-specific queries
        if len(stores_considered) > 1:
            for store in stores_considered[:2]:
                store_display = store.replace("_", " ").title()
                suggestions.append(f"{query} at {store_display}")
        
        # 6. Price-focused queries
        suggestions.append(f"cheapest {query}")
        suggestions.append(f"best deals on {query}")
        
        # Remove duplicates and limit
        unique_suggestions = []
        seen = set()
        for sug in suggestions:
            if not sug or not isinstance(sug, str):
                continue
            sug_lower = sug.lower().strip()
            if sug_lower and sug_lower not in seen and sug_lower != query.lower():
                seen.add(sug_lower)
                unique_suggestions.append(sug)
                if len(unique_suggestions) >= 6:
                    break
        
        return unique_suggestions
    
    def _get_related_products(self, query: str) -> List[str]:
        """Get semantically related products"""
        query_lower = query.lower()
        
        # Product relationships
        relationships = {
            "eggs": ["milk", "butter", "cheese", "yogurt"],
            "milk": ["eggs", "butter", "cheese", "yogurt", "cream"],
            "bread": ["butter", "jam", "peanut butter"],
            "chicken": ["beef", "pork", "turkey"],
            "bananas": ["apples", "oranges", "grapes"],
            "cereal": ["milk", "yogurt"],
            "pasta": ["sauce", "cheese"],
            "rice": ["beans", "chicken"],
            "coffee": ["tea", "cream", "sugar"],
            "soda": ["juice", "water", "sports drinks"]
        }
        
        # Check for matches
        for key, related in relationships.items():
            if key in query_lower:
                return related
        
        # Default related products
        return ["milk", "bread", "eggs", "chicken", "bananas"]

