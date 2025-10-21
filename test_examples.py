#!/usr/bin/env python3
"""
Comprehensive test examples for the optimized grocery scraper API
"""

import asyncio
import requests
import json
from datetime import datetime

# API base URL
BASE_URL = "http://localhost:8000"

def test_api_endpoints():
    """Test all API endpoints with different scenarios"""
    
    print("🚀 Testing Grocery Scraper API with Optimized Prompts")
    print("=" * 60)
    
    # Test cases with different contexts and categories
    test_cases = [
        {
            "name": "Price Comparison - Dairy",
            "endpoint": "/products/search",
            "params": {
                "query": "cheap organic milk",
                "store_name": "Whole Foods",
                "zipcode": "10001",
                "context": "price_comparison"
            },
            "expected_category": "dairy",
            "expected_context": "price_comparison"
        },
        {
            "name": "Availability - Produce",
            "endpoint": "/products/search", 
            "params": {
                "query": "fresh organic apples",
                "store_name": "Target",
                "zipcode": "10001",
                "context": "availability"
            },
            "expected_category": "produce",
            "expected_context": "availability"
        },
        {
            "name": "Nutritional - Meat",
            "endpoint": "/products/search",
            "params": {
                "query": "organic grass-fed beef",
                "store_name": "Whole Foods",
                "zipcode": "10001",
                "context": "nutritional"
            },
            "expected_category": "meat",
            "expected_context": "nutritional"
        },
        {
            "name": "Brand Comparison - Frozen",
            "endpoint": "/products/search",
            "params": {
                "query": "frozen pizza brands",
                "store_name": "Walmart",
                "zipcode": "10001",
                "context": "brand_comparison"
            },
            "expected_category": "frozen",
            "expected_context": "brand_comparison"
        },
        {
            "name": "Seasonal - Generic",
            "endpoint": "/products/search",
            "params": {
                "query": "pumpkin spice seasonal",
                "store_name": "Target",
                "zipcode": "10001",
                "context": "seasonal"
            },
            "expected_category": "generic",
            "expected_context": "seasonal"
        }
    ]
    
    # Test store discovery
    print("\n🏪 Testing Store Discovery:")
    print("-" * 40)
    
    store_tests = [
        {"zipcode": "10001", "store_chain": "Target"},
        {"zipcode": "90210", "store_chain": "Whole Foods"},
        {"zipcode": "60601", "store_chain": "Walmart"}
    ]
    
    for store_test in store_tests:
        try:
            response = requests.get(f"{BASE_URL}/stores/{store_test['zipcode']}", 
                                 params={"store_chain": store_test['store_chain']})
            if response.status_code == 200:
                data = response.json()
                print(f"✅ {store_test['store_chain']} in {store_test['zipcode']}: {data['stores_found']} stores found")
            else:
                print(f"❌ {store_test['store_chain']} in {store_test['zipcode']}: {response.status_code}")
        except Exception as e:
            print(f"❌ {store_test['store_chain']} in {store_test['zipcode']}: {e}")
    
    # Test product searches
    print("\n🛒 Testing Product Searches:")
    print("-" * 40)
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n🧪 Test {i}: {test_case['name']}")
        print(f"   Query: {test_case['params']['query']}")
        print(f"   Store: {test_case['params']['store_name']}")
        print(f"   Context: {test_case['expected_context']}")
        print(f"   Category: {test_case['expected_category']}")
        
        try:
            response = requests.get(f"{BASE_URL}{test_case['endpoint']}", 
                                 params=test_case['params'])
            
            if response.status_code == 200:
                data = response.json()
                products_found = data.get('products_found', 0)
                source = data.get('source', 'unknown')
                cache_hit = data.get('cache', {}).get('hit', False)
                
                print(f"   ✅ Success: {products_found} products found")
                print(f"   📊 Source: {source}")
                print(f"   💾 Cache: {'Hit' if cache_hit else 'Miss'}")
                
                # Show sample product data
                if data.get('products') and len(data['products']) > 0:
                    product = data['products'][0]
                    print(f"   📦 Sample Product:")
                    print(f"      Name: {product.get('name', 'N/A')}")
                    print(f"      Price: ${product.get('price', 'N/A')}")
                    print(f"      Brand: {product.get('brand', 'N/A')}")
                    print(f"      Quantity: {product.get('quantity', 'N/A')}")
                    print(f"      Store: {product.get('store_name', 'N/A')}")
                    print(f"      Confidence: {product.get('confidence_score', 'N/A')}")
            else:
                print(f"   ❌ Error: {response.status_code} - {response.text}")
                
        except Exception as e:
            print(f"   ❌ Exception: {e}")
    
    # Test aggregate search
    print("\n🔄 Testing Aggregate Search:")
    print("-" * 40)
    
    aggregate_tests = [
        {"query": "organic milk", "zipcode": "10001", "stores": "target,walmart,whole_foods"},
        {"query": "fresh salmon", "zipcode": "90210", "stores": "whole_foods,target"},
        {"query": "frozen pizza", "zipcode": "60601", "stores": "walmart,target,kroger"}
    ]
    
    for i, test in enumerate(aggregate_tests, 1):
        print(f"\n🔄 Aggregate Test {i}: {test['query']} in {test['zipcode']}")
        try:
            response = requests.get(f"{BASE_URL}/products/aggregate", params=test)
            if response.status_code == 200:
                data = response.json()
                results_count = len(data.get('results', []))
                stores_considered = data.get('stores_considered', [])
                source = data.get('source', 'unknown')
                
                print(f"   ✅ Success: {results_count} product groups found")
                print(f"   🏪 Stores: {', '.join(stores_considered)}")
                print(f"   📊 Source: {source}")
                
                # Show sample aggregated product
                if data.get('results') and len(data['results']) > 0:
                    result = data['results'][0]
                    canonical = result.get('canonical_product', {})
                    offers = result.get('offers', [])
                    
                    print(f"   📦 Sample Product: {canonical.get('name', 'N/A')}")
                    print(f"      Brand: {canonical.get('brand', 'N/A')}")
                    print(f"      Offers: {len(offers)} stores")
                    
                    for offer in offers[:2]:  # Show first 2 offers
                        print(f"         {offer.get('store_name', 'N/A')}: ${offer.get('price', 'N/A')}")
            else:
                print(f"   ❌ Error: {response.status_code}")
        except Exception as e:
            print(f"   ❌ Exception: {e}")

def test_prompt_detection():
    """Test prompt optimization detection"""
    
    print("\n🧠 Testing Prompt Detection:")
    print("-" * 40)
    
    # Import the client to test detection
    try:
        from scraper.exa_structured_client import ExaStructuredClient
        from scraper.context_prompts import ContextPrompts
        
        client = ExaStructuredClient()
        
        test_queries = [
            "cheap organic milk",
            "fresh salmon available",
            "compare yogurt brands", 
            "healthy breakfast options",
            "seasonal pumpkin spice"
        ]
        
        for query in test_queries:
            category = client._detect_product_category(query)
            context = client._detect_search_context(query)
            prompt = client._get_optimized_prompt(query)
            
            print(f"🔍 '{query}'")
            print(f"   📦 Category: {category}")
            print(f"   🎯 Context: {context}")
            print(f"   📝 Prompt: {len(prompt)} chars")
            print()
            
    except ImportError as e:
        print(f"❌ Could not import client: {e}")

def test_api_health():
    """Test API health and services"""
    
    print("\n🏥 Testing API Health:")
    print("-" * 40)
    
    try:
        # Test root endpoint
        response = requests.get(f"{BASE_URL}/")
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Root endpoint: {data.get('name', 'Unknown')} v{data.get('version', 'Unknown')}")
            print(f"   Features: {len(data.get('features', []))} available")
        else:
            print(f"❌ Root endpoint: {response.status_code}")
        
        # Test health endpoint
        response = requests.get(f"{BASE_URL}/health")
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Health check: {data.get('status', 'Unknown')}")
            services = data.get('services', {})
            for service, status in services.items():
                print(f"   {service}: {status}")
        else:
            print(f"❌ Health check: {response.status_code}")
            
    except Exception as e:
        print(f"❌ Health check failed: {e}")

def main():
    """Run all tests"""
    
    print("🚀 Grocery Scraper API - Comprehensive Test Suite")
    print("=" * 60)
    print(f"⏰ Test started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # Test API health first
    test_api_health()
    
    # Test prompt detection
    test_prompt_detection()
    
    # Test all endpoints
    test_api_endpoints()
    
    print("\n" + "=" * 60)
    print("🎉 Test suite completed!")
    print("📊 Check the results above to see how the optimized prompts perform.")

if __name__ == "__main__":
    main()
