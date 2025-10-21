#!/usr/bin/env python3
"""
Context-aware prompts for different search scenarios
"""

class ContextPrompts:
    """Prompts that adapt based on search context and user intent"""
    
    # Price comparison focused
    PRICE_COMPARISON = """Extract product information for price comparison. Focus on: exact product name, brand, current price in USD, quantity/size, store name, availability status, and any current promotions or discounts. Ensure price data is accurate and current for comparison purposes."""
    
    # Availability focused
    AVAILABILITY_FOCUSED = """Extract product availability information. Focus on: product name, brand, current availability status (in stock, out of stock, limited), store name and location, quantity available, restock information, and alternative products if unavailable."""
    
    # Nutritional focus
    NUTRITIONAL_FOCUSED = """Extract product information with nutritional details. Focus on: product name, brand, price, quantity, complete ingredient list, nutritional facts (calories, protein, carbs, fat), allergens, dietary restrictions (vegan, gluten-free, etc.), and health claims."""
    
    # Brand comparison
    BRAND_COMPARISON = """Extract product information for brand comparison. Focus on: product name, brand, price, quantity/size, product description, key features, customer ratings, review counts, and any brand-specific attributes or certifications."""
    
    # Seasonal/limited time
    SEASONAL_FOCUSED = """Extract seasonal or limited-time product information. Focus on: product name, brand, price, quantity, seasonal availability, limited-time offers, expiration dates, special packaging, and any time-sensitive promotions."""
    
    @classmethod
    def get_context_prompt(cls, context: str) -> str:
        """Get context-specific prompt"""
        prompts = {
            "price_comparison": cls.PRICE_COMPARISON,
            "availability": cls.AVAILABILITY_FOCUSED,
            "nutritional": cls.NUTRITIONAL_FOCUSED,
            "brand_comparison": cls.BRAND_COMPARISON,
            "seasonal": cls.SEASONAL_FOCUSED
        }
        return prompts.get(context.lower(), cls.PRICE_COMPARISON)
    
    @classmethod
    def detect_search_context(cls, query: str) -> str:
        """Detect search context from user query"""
        query_lower = query.lower()
        
        # Price comparison indicators
        if any(word in query_lower for word in ["cheap", "price", "cost", "expensive", "budget", "deal", "sale"]):
            return "price_comparison"
        
        # Availability indicators
        if any(word in query_lower for word in ["available", "stock", "in stock", "out of stock", "find"]):
            return "availability"
        
        # Nutritional indicators
        if any(word in query_lower for word in ["organic", "healthy", "nutrition", "ingredients", "calories", "sugar", "fat"]):
            return "nutritional"
        
        # Brand comparison indicators
        if any(word in query_lower for word in ["brand", "compare", "vs", "versus", "alternative", "option"]):
            return "brand_comparison"
        
        # Seasonal indicators
        if any(word in query_lower for word in ["seasonal", "limited", "special", "holiday", "christmas", "thanksgiving"]):
            return "seasonal"
        
        return "price_comparison"  # Default
