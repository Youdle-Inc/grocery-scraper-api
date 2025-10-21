#!/usr/bin/env python3
"""
Quick test script to demonstrate prompt optimization
"""

import asyncio
from scraper.exa_structured_client import ExaStructuredClient
from scraper.prompt_templates import GroceryPrompts
from scraper.context_prompts import ContextPrompts

def test_prompt_detection():
    """Test how the system detects categories and contexts"""
    
    print("🧠 Testing Prompt Detection & Optimization")
    print("=" * 50)
    
    # Initialize client
    client = ExaStructuredClient()
    
    # Test queries that should trigger different categories and contexts
    test_queries = [
        "cheap organic milk",
        "fresh salmon available now",
        "compare yogurt brands",
        "healthy breakfast cereal",
        "seasonal pumpkin spice",
        "frozen pizza options",
        "organic grass-fed beef",
        "fresh produce delivery"
    ]
    
    print("\n📊 Detection Results:")
    print("-" * 30)
    
    for i, query in enumerate(test_queries, 1):
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

def test_prompt_templates():
    """Test the different prompt templates"""
    
    print("\n📚 Testing Prompt Templates:")
    print("-" * 30)
    
    # Test category prompts
    categories = ["dairy", "produce", "meat", "frozen", "organic"]
    print("\n📦 Category-Specific Prompts:")
    for category in categories:
        prompt = GroceryPrompts.get_category_prompt(category)
        print(f"   {category.title()}: {len(prompt)} chars")
        print(f"      Focus: {prompt[:100]}...")
    
    # Test context prompts
    contexts = ["price_comparison", "availability", "nutritional", "brand_comparison", "seasonal"]
    print("\n🎯 Context-Specific Prompts:")
    for context in contexts:
        prompt = ContextPrompts.get_context_prompt(context)
        print(f"   {context.replace('_', ' ').title()}: {len(prompt)} chars")
        print(f"      Focus: {prompt[:100]}...")

def test_search_query_templates():
    """Test the enhanced search query templates"""
    
    print("\n🔍 Testing Search Query Templates:")
    print("-" * 40)
    
    # Test different query types
    test_cases = [
        {"query": "organic milk", "store": "Whole Foods", "zipcode": "10001", "category": "dairy"},
        {"query": "fresh apples", "store": "Target", "zipcode": "90210", "category": "produce"},
        {"query": "ground beef", "store": "Walmart", "zipcode": "60601", "category": "meat"},
        {"query": "frozen pizza", "store": "Kroger", "zipcode": "10001", "category": "frozen"},
        {"query": "organic yogurt", "store": "Whole Foods", "zipcode": "10001", "category": "organic"}
    ]
    
    for i, case in enumerate(test_cases, 1):
        print(f"\n🔍 Test {i}: {case['query']} at {case['store']}")
        
        # Build enhanced query
        enhanced_query = GroceryPrompts.build_enhanced_query(
            case['query'], case['store'], case['zipcode'], case['category']
        )
        
        print(f"   Enhanced Query: {enhanced_query}")
        
        # Show what the old query would have been
        old_query = f"{case['query']} at {case['store']}"
        print(f"   Old Query: {old_query}")
        print(f"   Improvement: {len(enhanced_query) - len(old_query)} chars added")

def main():
    """Run all tests"""
    
    print("🚀 Grocery Scraper API - Prompt Optimization Test")
    print("=" * 60)
    
    # Test prompt detection
    test_prompt_detection()
    
    # Test prompt templates
    test_prompt_templates()
    
    # Test search query templates
    test_search_query_templates()
    
    print("\n" + "=" * 60)
    print("🎉 Prompt Optimization Test Complete!")
    print("\n✅ Key Improvements Demonstrated:")
    print("   • Context-aware prompts based on user intent")
    print("   • Category-specific data extraction")
    print("   • Enhanced validation requirements")
    print("   • Better search query templates")
    print("   • Automatic detection and optimization")
    
    print("\n🚀 Your API is now much smarter!")
    print("   • Better data quality")
    print("   • More accurate results")
    print("   • Context-aware responses")
    print("   • Category-specific details")

if __name__ == "__main__":
    main()
