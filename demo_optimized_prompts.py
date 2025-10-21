#!/usr/bin/env python3
"""
Demo script showing the improved prompt optimization
"""

import asyncio
from scraper.exa_structured_client import ExaStructuredClient
from scraper.prompt_templates import GroceryPrompts
from scraper.context_prompts import ContextPrompts

def demo_prompt_optimization():
    """Demonstrate the prompt optimization features"""
    
    print("🚀 Grocery Scraper API - Prompt Optimization Demo")
    print("=" * 60)
    
    # Initialize client
    client = ExaStructuredClient()
    
    # Demo queries with different intents
    demo_queries = [
        "cheap organic milk",
        "fresh salmon available now", 
        "compare brand yogurt options",
        "seasonal pumpkin spice latte",
        "healthy breakfast cereal"
    ]
    
    print("\n📊 Prompt Optimization Analysis:")
    print("-" * 40)
    
    for i, query in enumerate(demo_queries, 1):
        print(f"\n🔍 Query {i}: '{query}'")
        
        # Detect category and context
        category = client._detect_product_category(query)
        context = client._detect_search_context(query)
        
        print(f"   📦 Category: {category}")
        print(f"   🎯 Context: {context}")
        
        # Get optimized prompt
        prompt = client._get_optimized_prompt(query)
        
        # Show prompt characteristics
        print(f"   📝 Prompt Length: {len(prompt)} characters")
        print(f"   ✅ Has Validation: {'Validation requirements' in prompt}")
        print(f"   🎯 Category Focus: {category in prompt}")
        print(f"   🔍 Context Focus: {context.replace('_', ' ').title() in prompt}")
        
        # Show search query template
        search_query = GroceryPrompts.build_enhanced_query(query, "Target", "10001", category)
        print(f"   🔍 Search Query: {search_query}")
    
    print("\n" + "=" * 60)
    print("📚 Available Prompt Templates:")
    print("-" * 40)
    
    # Show available categories
    categories = ["dairy", "produce", "meat", "frozen", "organic"]
    print("\n📦 Product Categories:")
    for category in categories:
        prompt = GroceryPrompts.get_category_prompt(category)
        print(f"   {category.title()}: {len(prompt)} chars")
    
    # Show available contexts
    contexts = ["price_comparison", "availability", "nutritional", "brand_comparison", "seasonal"]
    print("\n🎯 Search Contexts:")
    for context in contexts:
        prompt = ContextPrompts.get_context_prompt(context)
        print(f"   {context.replace('_', ' ').title()}: {len(prompt)} chars")
    
    print("\n" + "=" * 60)
    print("🎉 Key Improvements:")
    print("-" * 40)
    print("✅ Context-aware prompts based on user intent")
    print("✅ Category-specific data extraction")
    print("✅ Enhanced validation requirements")
    print("✅ Better search query templates")
    print("✅ Confidence scoring for data quality")
    print("✅ Automatic context and category detection")
    
    print("\n🚀 Your API is now much smarter!")
    print("   - Better data quality")
    print("   - More accurate results")
    print("   - Context-aware responses")
    print("   - Category-specific details")

if __name__ == "__main__":
    demo_prompt_optimization()
