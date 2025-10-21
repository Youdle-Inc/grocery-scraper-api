#!/usr/bin/env python3
"""
Test script for optimized prompt strategies
"""

import asyncio
import os
from dotenv import load_dotenv
from scraper.exa_structured_client import ExaStructuredClient
from scraper.prompt_templates import GroceryPrompts
from scraper.context_prompts import ContextPrompts

load_dotenv()

async def test_prompt_optimization():
    """Test the optimized prompt strategies"""
    
    # Initialize client
    client = ExaStructuredClient()
    
    if not client.is_available():
        print("❌ Exa client not available - check EXA_API_KEY")
        return
    
    print("🚀 Testing Optimized Prompt Strategies")
    print("=" * 50)
    
    # Test queries with different contexts and categories
    test_cases = [
        {
            "query": "organic milk",
            "store": "Whole Foods",
            "zipcode": "10001",
            "expected_category": "dairy",
            "expected_context": "nutritional"
        },
        {
            "query": "cheap ground beef",
            "store": "Walmart",
            "zipcode": "10001",
            "expected_category": "meat",
            "expected_context": "price_comparison"
        },
        {
            "query": "fresh apples",
            "store": "Target",
            "zipcode": "10001",
            "expected_category": "produce",
            "expected_context": "availability"
        },
        {
            "query": "frozen pizza",
            "store": "Kroger",
            "zipcode": "10001",
            "expected_category": "frozen",
            "expected_context": "price_comparison"
        }
    ]
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n🧪 Test Case {i}: {test_case['query']}")
        print("-" * 30)
        
        # Test category detection
        detected_category = client._detect_product_category(test_case['query'])
        print(f"📦 Detected Category: {detected_category} (Expected: {test_case['expected_category']})")
        
        # Test context detection
        detected_context = client._detect_search_context(test_case['query'])
        print(f"🎯 Detected Context: {detected_context} (Expected: {test_case['expected_context']})")
        
        # Test prompt generation
        optimized_prompt = client._get_optimized_prompt(test_case['query'])
        print(f"📝 Prompt Length: {len(optimized_prompt)} characters")
        print(f"🔍 Search Query: {GroceryPrompts.build_enhanced_query(test_case['query'], test_case['store'], test_case['zipcode'], detected_category)}")
        
        # Test actual search (commented out to avoid API calls during testing)
        # print(f"🔍 Testing search...")
        # products = await client.search_products_structured(
        #     query=test_case['query'],
        #     store_name=test_case['store'],
        #     zipcode=test_case['zipcode'],
        #     num_results=5,
        #     context=detected_context
        # )
        # print(f"✅ Found {len(products)} products")
    
    print("\n" + "=" * 50)
    print("🎉 Prompt optimization testing complete!")
    
    # Test prompt templates
    print("\n📚 Testing Prompt Templates:")
    print("-" * 30)
    
    categories = ["dairy", "produce", "meat", "frozen", "organic"]
    for category in categories:
        prompt = GroceryPrompts.get_category_prompt(category)
        print(f"📦 {category.title()}: {len(prompt)} chars")
    
    contexts = ["price_comparison", "availability", "nutritional", "brand_comparison", "seasonal"]
    for context in contexts:
        prompt = ContextPrompts.get_context_prompt(context)
        print(f"🎯 {context.replace('_', ' ').title()}: {len(prompt)} chars")

async def test_prompt_combinations():
    """Test different prompt combinations"""
    
    print("\n🔬 Testing Prompt Combinations:")
    print("=" * 50)
    
    # Test different query types
    queries = [
        "cheap organic milk",
        "fresh salmon available",
        "compare brand yogurt",
        "seasonal pumpkin spice",
        "healthy breakfast options"
    ]
    
    for query in queries:
        print(f"\n🔍 Query: '{query}'")
        
        # Test category detection
        category = ExaStructuredClient()._detect_product_category(query)
        context = ContextPrompts.detect_search_context(query)
        
        print(f"   Category: {category}")
        print(f"   Context: {context}")
        
        # Get optimized prompt
        client = ExaStructuredClient()
        prompt = client._get_optimized_prompt(query)
        
        print(f"   Prompt length: {len(prompt)} chars")
        print(f"   Contains validation: {'Validation requirements' in prompt}")
        print(f"   Contains category focus: {category in prompt}")

if __name__ == "__main__":
    asyncio.run(test_prompt_optimization())
    asyncio.run(test_prompt_combinations())
