"""
Product matching and similarity service
Prepares for vector search integration
"""

import logging
import re
from typing import List, Dict, Optional, Tuple
from difflib import SequenceMatcher
from .models import ProductListing

logger = logging.getLogger(__name__)

class ProductMatcher:
    """Service for product matching, similarity, and alternatives"""
    
    def __init__(self):
        # Product synonyms and alternatives (will be enhanced with vector search)
        self.product_synonyms = self._initialize_synonyms()
        self.product_categories = self._initialize_categories()
        
    def _initialize_synonyms(self) -> Dict[str, List[str]]:
        """Initialize product synonyms and alternatives"""
        return {
            "milk": ["dairy", "milk alternative", "plant milk", "almond milk", "soy milk", "oat milk"],
            "bread": ["loaf", "sandwich bread", "artisan bread", "whole grain", "sourdough"],
            "eggs": ["egg", "farm fresh eggs", "organic eggs", "large eggs", "extra large eggs"],
            "banana": ["bananas", "organic banana", "fair trade banana"],
            "apple": ["apples", "organic apple", "gala apple", "fuji apple", "honeycrisp"],
            "chicken": ["chicken breast", "chicken thighs", "organic chicken", "free range chicken"],
            "beef": ["ground beef", "steak", "organic beef", "grass fed beef"],
            "rice": ["white rice", "brown rice", "basmati rice", "jasmine rice", "organic rice"],
            "pasta": ["spaghetti", "penne", "fettuccine", "organic pasta", "whole grain pasta"],
            "cheese": ["cheddar", "mozzarella", "parmesan", "organic cheese", "artisan cheese"],
            "yogurt": ["greek yogurt", "organic yogurt", "plant based yogurt", "dairy free yogurt"],
            "cereal": ["breakfast cereal", "organic cereal", "granola", "oatmeal"],
            "soup": ["canned soup", "organic soup", "broth", "stock"],
            "sauce": ["pasta sauce", "marinara", "organic sauce", "tomato sauce"],
            "snack": ["chips", "crackers", "nuts", "organic snack", "healthy snack"]
        }
    
    def _initialize_categories(self) -> Dict[str, List[str]]:
        """Initialize product categories"""
        return {
            "dairy": ["milk", "cheese", "yogurt", "butter", "cream", "ice cream"],
            "produce": ["fruits", "vegetables", "organic produce", "fresh produce"],
            "meat": ["chicken", "beef", "pork", "fish", "seafood", "organic meat"],
            "pantry": ["rice", "pasta", "sauce", "soup", "canned goods", "condiments"],
            "bakery": ["bread", "pastries", "cakes", "cookies", "artisan bread"],
            "beverages": ["water", "juice", "soda", "coffee", "tea", "plant milk"],
            "snacks": ["chips", "crackers", "nuts", "candy", "organic snacks"],
            "frozen": ["frozen meals", "frozen vegetables", "ice cream", "frozen pizza"]
        }
    
    def calculate_similarity(self, query: str, product_title: str) -> float:
        """Calculate similarity score between query and product title"""
        query_lower = query.lower().strip()
        title_lower = product_title.lower().strip()
        
        # Exact match
        if query_lower == title_lower:
            return 1.0
        
        # Contains match
        if query_lower in title_lower or title_lower in query_lower:
            return 0.9
        
        # Word-based similarity
        query_words = set(query_lower.split())
        title_words = set(title_lower.split())
        
        if query_words and title_words:
            intersection = query_words.intersection(title_words)
            union = query_words.union(title_words)
            jaccard_similarity = len(intersection) / len(union) if union else 0
            
            # Sequence similarity
            sequence_similarity = SequenceMatcher(None, query_lower, title_lower).ratio()
            
            # Combined score
            return max(jaccard_similarity, sequence_similarity)
        
        return 0.0
    
    def find_alternatives(self, query: str, products: List[ProductListing]) -> List[ProductListing]:
        """Find alternative products for a given query"""
        query_lower = query.lower().strip()
        alternatives = []
        
        # Get synonyms for the query
        synonyms = self.product_synonyms.get(query_lower, [])
        
        for product in products:
            title_lower = product.product_name.lower()
            
            # Check if product matches any synonyms
            for synonym in synonyms:
                if synonym in title_lower or title_lower in synonym:
                    product.match_type = "alternative"
                    product.confidence_score = 0.7
                    alternatives.append(product)
                    break
        
        return alternatives[:5]  # Limit to top 5 alternatives
    
    def enhance_product_data(self, product: ProductListing, query: str) -> ProductListing:
        """Enhance product data with matching information"""
        similarity = self.calculate_similarity(query, product.product_name)
        product.confidence_score = similarity
        
        # Determine match type
        if similarity >= 0.9:
            product.match_type = "exact"
        elif similarity >= 0.7:
            product.match_type = "similar"
        else:
            product.match_type = "alternative"
        
        # Add categories
        product.categories = self._get_product_categories(product.product_name)
        
        return product
    
    def _get_product_categories(self, product_name: str) -> List[str]:
        """Get categories for a product"""
        name_lower = product_name.lower()
        categories = []
        
        for category, keywords in self.product_categories.items():
            for keyword in keywords:
                if keyword in name_lower:
                    categories.append(category)
                    break
        
        return categories
    
    def filter_by_confidence(self, products: List[ProductListing], min_confidence: float = 0.5) -> List[ProductListing]:
        """Filter products by confidence score"""
        return [p for p in products if p.confidence_score and p.confidence_score >= min_confidence]
    
    def sort_by_relevance(self, products: List[ProductListing]) -> List[ProductListing]:
        """Sort products by relevance (confidence score)"""
        return sorted(products, key=lambda p: p.confidence_score or 0, reverse=True)
    
    def get_product_synonyms(self, query: str) -> List[str]:
        """Get synonyms for a product query"""
        return self.product_synonyms.get(query.lower(), [])
    
    def suggest_queries(self, partial_query: str) -> List[str]:
        """Suggest queries based on partial input"""
        suggestions = []
        partial_lower = partial_query.lower()
        
        for main_term, synonyms in self.product_synonyms.items():
            if partial_lower in main_term:
                suggestions.append(main_term)
            
            for synonym in synonyms:
                if partial_lower in synonym:
                    suggestions.append(synonym)
        
        return list(set(suggestions))[:10]  # Limit to 10 suggestions
