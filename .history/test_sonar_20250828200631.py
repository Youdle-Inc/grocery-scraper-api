#!/usr/bin/env python3
"""
Test script for the Grocery Scraper API with Perplexity Sonar and Exa API integration.
"""

import requests
import json
import time
from typing import Dict, Any

# API base URL
BASE_URL = "http://localhost:8000"

def test_health_check():
    """Test the health check endpoint."""
    print("🏥 Testing Health Check...")
    
    try:
        response = requests.get(f"{BASE_URL}/health")
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Health check passed: {data['status']}")
            print(f"   Version: {data['version']}")
            print(f"   Timestamp: {data['timestamp']}")
            return True
        else:
            print(f"❌ Health check failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Health check error: {e}")
        return False

def test_api_info():
    """Test the API information endpoint."""
    print("\n📊 Testing API Information...")
    
    try:
        response = requests.get(f"{BASE_URL}/")
        if response.status_code == 200:
            data = response.json()
            print(f"✅ API info retrieved: {data['name']} v{data['version']}")
            print(f"   Description: {data['description']}")
            print(f"   Features: {', '.join(data['features'])}")
            return True
        else:
            print(f"❌ API info failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ API info error: {e}")
        return False

def test_store_discovery(location: str = "Chicago, IL"):
    """Test store discovery functionality."""
    print(f"\n🏪 Testing Store Discovery for: {location}")
    
    try:
        response = requests.get(f"{BASE_URL}/sonar/stores/search", params={"location": location})
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Found {data['stores_found']} stores in {data['location']}")
            
            for i, store in enumerate(data['stores'][:3], 1):  # Show first 3 stores
                print(f"   {i}. {store['store_name']}")
                print(f"      Address: {store['address']}")
                print(f"      Services: {', '.join(store['services'])}")
                print(f"      Website: {store.get('website', 'N/A')}")
            
            return data['stores']
        else:
            print(f"❌ Store discovery failed: {response.status_code}")
            print(f"   Response: {response.text}")
            return []
    except Exception as e:
        print(f"❌ Store discovery error: {e}")
        return []

def test_product_search(query: str, store_name: str, location: str):
    """Test product search functionality."""
    print(f"\n🛒 Testing Product Search: '{query}' at {store_name} in {location}")
    
    try:
        response = requests.get(
            f"{BASE_URL}/sonar/products/search",
            params={
                "query": query,
                "store_name": store_name,
                "location": location
            }
        )
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Found {data['products_found']} products")
            print(f"   Search timestamp: {data['search_timestamp']}")
            print(f"   Data sources: {data['source']}")
            
            # Show first 3 products with details
            for i, product in enumerate(data['products'][:3], 1):
                print(f"\n   {i}. {product['name']}")
                print(f"      Price: ${product['price']}")
                print(f"      Brand: {product['brand']}")
                print(f"      Size: {product['size']}")
                print(f"      Category: {product['category']}")
                print(f"      Availability: {product['availability']}")
                
                # Check for real URLs and images
                if product.get('image_url'):
                    print(f"      🖼️  Image URL: {product['image_url'][:80]}...")
                else:
                    print(f"      🖼️  Image URL: Not available")
                
                if product.get('product_url'):
                    print(f"      🔗 Product URL: {product['product_url']}")
                else:
                    print(f"      🔗 Product URL: Not available")
                
                if product.get('rating'):
                    print(f"      ⭐ Rating: {product['rating']} ({product.get('reviews_count', 0)} reviews)")
                
                if product.get('description'):
                    print(f"      📝 Description: {product['description'][:100]}...")
            
            return data['products']
        else:
            print(f"❌ Product search failed: {response.status_code}")
            print(f"   Response: {response.text}")
            return []
    except Exception as e:
        print(f"❌ Product search error: {e}")
        return []

def test_serper_integration():
    """Test Serper.dev integration specifically."""
    print(f"\n🔗 Testing Serper.dev Integration...")
    
    # Test with a simple product search that should trigger Serper.dev
    products = test_product_search("milk", "Target", "Chicago, IL")
    
    if products:
        # Check if we got real URLs and images
        real_urls = sum(1 for p in products if p.get('product_url'))
        real_images = sum(1 for p in products if p.get('image_url'))
        
        print(f"\n📊 Serper.dev Integration Results:")
        print(f"   Products with real URLs: {real_urls}/{len(products)}")
        print(f"   Products with real images: {real_images}/{len(products)}")
        
        if real_urls > 0 and real_images > 0:
            print("✅ Serper.dev integration working correctly!")
            return True
        else:
            print("⚠️  Serper.dev integration may have issues")
            return False
    else:
        print("❌ Serper.dev integration test failed")
        return False

def run_comprehensive_test():
    """Run a comprehensive test of all API functionality."""
    print("🚀 Starting Comprehensive API Test")
    print("=" * 50)
    
    # Test basic functionality
    health_ok = test_health_check()
    info_ok = test_api_info()
    
    if not health_ok:
        print("❌ Health check failed - API may not be running")
        return False
    
    # Test store discovery
    stores = test_store_discovery("New York, NY")
    
    if stores:
        # Test product search with the first store found
        first_store = stores[0]
        products = test_product_search(
            "organic bananas", 
            first_store['store_name'], 
            "New York, NY"
        )
        
        # Test Serper.dev integration
        serper_ok = test_serper_integration()
        
        # Summary
        print("\n" + "=" * 50)
        print("📋 Test Summary:")
        print(f"   Health Check: {'✅' if health_ok else '❌'}")
        print(f"   API Info: {'✅' if info_ok else '❌'}")
        print(f"   Store Discovery: {'✅' if stores else '❌'} ({len(stores)} stores)")
        print(f"   Product Search: {'✅' if products else '❌'} ({len(products) if products else 0} products)")
        print(f"   Serper.dev Integration: {'✅' if serper_ok else '❌'}")
        
        return all([health_ok, info_ok, stores, products, serper_ok])
    else:
        print("❌ Store discovery failed - cannot test product search")
        return False

def test_specific_scenarios():
    """Test specific scenarios and edge cases."""
    print("\n🎯 Testing Specific Scenarios")
    print("=" * 50)
    
    scenarios = [
        {
            "name": "Oat Milk at Target",
            "query": "oat milk",
            "store": "Target",
            "location": "Chicago, IL"
        },
        {
            "name": "Organic Bananas at Whole Foods",
            "query": "organic bananas",
            "store": "Whole Foods",
            "location": "San Francisco, CA"
        },
        {
            "name": "Almond Milk at Trader Joe's",
            "query": "almond milk",
            "store": "Trader Joe's",
            "location": "Los Angeles, CA"
        }
    ]
    
    for scenario in scenarios:
        print(f"\n🧪 Testing: {scenario['name']}")
        products = test_product_search(
            scenario['query'],
            scenario['store'],
            scenario['location']
        )
        
        if products:
            # Check for real data
            real_urls = sum(1 for p in products if p.get('product_url'))
            real_images = sum(1 for p in products if p.get('image_url'))
            print(f"   ✅ Found {len(products)} products with {real_urls} real URLs and {real_images} real images")
        else:
            print(f"   ❌ No products found")
        
        time.sleep(1)  # Small delay between requests

if __name__ == "__main__":
    print("🛒 Grocery Scraper API Test Suite")
    print("Testing Perplexity Sonar + Serper.dev Integration")
    print("=" * 60)
    
    # Run comprehensive test
    success = run_comprehensive_test()
    
    if success:
        print("\n🎉 All tests passed! Your API is working correctly.")
        print("\n🔗 Next steps:")
        print("   - Check the interactive docs at http://localhost:8000/docs")
        print("   - Try different product searches")
        print("   - Test with your own applications")
    else:
        print("\n❌ Some tests failed. Check the output above for details.")
        print("\n🔧 Troubleshooting:")
        print("   - Make sure the API server is running")
        print("   - Check your API keys in the .env file")
        print("   - Verify network connectivity")
    
    # Run specific scenarios
    test_specific_scenarios()
    
    print("\n🏁 Test suite completed!")

