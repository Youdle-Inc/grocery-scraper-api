#!/usr/bin/env python3
"""
Advanced prompt templates for grocery product search optimization
"""

class GroceryPrompts:
    """Specialized prompts for different grocery product categories"""
    
    # Base product search prompt
    PRODUCT_SEARCH_BASE = """Extract detailed grocery product information from store websites. Focus on: product name, brand, exact price in USD, quantity/size (e.g., '64 fl oz', '1 gallon'), availability status, store name and full address, customer ratings and review counts. Ensure price is numeric and quantity includes units. Prioritize current, in-stock products with clear pricing."""
    
    # Category-specific prompts
    DAIRY_PROMPT = """Extract dairy product information including: product name, brand, exact price, size/quantity (gallons, quarts, pints, ounces), expiration date if available, organic/conventional status, fat content (whole, 2%, 1%, skim), availability status, store location, and customer ratings. Focus on milk, cheese, yogurt, butter products."""
    
    PRODUCE_PROMPT = """Extract fresh produce information including: product name, brand (if applicable), exact price per pound or unit, weight/quantity, organic/conventional status, freshness indicators, seasonal availability, store location, and customer ratings. Focus on fruits, vegetables, herbs."""
    
    MEAT_PROMPT = """Extract meat and poultry information including: product name, brand, exact price per pound, weight/quantity, cut type, grade (if applicable), organic/grass-fed status, packaging type, expiration date, availability status, store location, and customer ratings."""
    
    FROZEN_PROMPT = """Extract frozen food information including: product name, brand, exact price, package size/quantity, serving size, preparation instructions, storage requirements, expiration date, availability status, store location, and customer ratings."""
    
    ORGANIC_PROMPT = """Extract organic product information including: product name, brand, exact price, size/quantity, organic certification details, USDA organic seal, ingredient list, availability status, store location, and customer ratings. Verify organic certification status."""
    
    # Store location prompts
    STORE_LOCATION_BASE = """Extract complete grocery store location information. Focus on: exact store name, full street address, city, state, ZIP code, phone number, operating hours, available services (delivery, pickup, curbside, in-store shopping). Ensure address is complete and properly formatted with city, state, and ZIP code."""
    
    # Enhanced search query templates
    SEARCH_QUERY_TEMPLATES = {
        "dairy": "{query} dairy products at {store} near {zipcode}",
        "produce": "{query} fresh produce at {store} near {zipcode}",
        "meat": "{query} meat poultry at {store} near {zipcode}",
        "frozen": "{query} frozen foods at {store} near {zipcode}",
        "organic": "{query} organic products at {store} near {zipcode}",
        "generic": "{query} at {store} near {zipcode}"
    }
    
    @classmethod
    def get_category_prompt(cls, category: str) -> str:
        """Get category-specific prompt"""
        prompts = {
            "dairy": cls.DAIRY_PROMPT,
            "produce": cls.PRODUCE_PROMPT,
            "meat": cls.MEAT_PROMPT,
            "frozen": cls.FROZEN_PROMPT,
            "organic": cls.ORGANIC_PROMPT
        }
        return prompts.get(category.lower(), cls.PRODUCT_SEARCH_BASE)
    
    @classmethod
    def get_search_query_template(cls, category: str) -> str:
        """Get category-specific search query template"""
        return cls.SEARCH_QUERY_TEMPLATES.get(category.lower(), cls.SEARCH_QUERY_TEMPLATES["generic"])
    
    @classmethod
    def build_enhanced_query(cls, query: str, store: str, zipcode: str, category: str = None) -> str:
        """Build enhanced search query with category context"""
        template = cls.get_search_query_template(category or "generic")
        return template.format(query=query, store=store, zipcode=zipcode)
