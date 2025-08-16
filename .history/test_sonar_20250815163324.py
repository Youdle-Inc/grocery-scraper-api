#!/usr/bin/env python3
"""
Test script for Perplexity Sonar API integration
Demonstrates the enhanced functionality of the Sonar client
"""

import asyncio
import os
import sys
from datetime import datetime

# Add the project root to the path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from scraper.sonar_client import SonarClient

async def test_sonar_functionality():
    """Test the enhanced Sonar client functionality"""
    
    print("🚀 Testing Perplexity Sonar API Integration")
    print("=" * 50)
    
    # Initialize Sonar client
    sonar_client = SonarClient()
    
    # Check availability
    print(f"✅ Sonar client available: {sonar_client.is_available()}")
    print(f"🔑 API key configured: {sonar_client.api_key is not None}")
    
    if not sonar_client.is_available():
        print("❌ Sonar client not available. Please set PERPLEXITY_API_KEY environment variable.")
        return
    
    # Test zipcode
    test_zipcode = "15213"  # Pittsburgh area
    
    print(f"\n🔍 Testing store discovery for zipcode: {test_zipcode}")
    print("-" * 40)
    
    try:
        # Test store discovery
        stores = await sonar_client.search_stores(test_zipcode)
        
        print(f"✅ Found {len(stores)} stores:")
        for i, store in enumerate(stores, 1):
            print(f"  {i}. {store.store_name}")
            print(f"     ID: {store.store_id}")
            print(f"     Address: {store.address or 'Not available'}")
            print(f"     Services: {', '.join(store.services) if store.services else 'Not available'}")
            print(f"     Status: {store.status}")
            print()
        
        # Test store details for the first store found
        if stores:
            first_store = stores[0]
            print(f"📋 Testing store details for: {first_store.store_name}")
            print("-" * 40)
            
            details = await sonar_client.get_store_details(
                first_store.store_name, 
                f"zipcode {test_zipcode}"
            )
            
            if details:
                print("✅ Store details retrieved:")
                if details.get('hours'):
                    print(f"  Hours: {details['hours']}")
                if details.get('services'):
                    print(f"  Services: {details['services']}")
                if details.get('contact'):
                    print(f"  Contact: {details['contact']}")
                if details.get('address'):
                    print(f"  Address: {details['address']}")
                if details.get('features'):
                    print(f"  Features: {details['features']}")
            else:
                print("❌ No store details found")
            
            # Test product search
            print(f"\n🛒 Testing product search for 'milk' at {first_store.store_name}")
            print("-" * 40)
            
            products = await sonar_client.search_products(
                "milk", 
                first_store.store_name, 
                f"zipcode {test_zipcode}"
            )
            
            if products:
                print(f"✅ Found {len(products)} products:")
                for i, product in enumerate(products, 1):
                    print(f"  {i}. {product.get('name', 'Unknown product')}")
                    if 'price' in product:
                        print(f"     Price: ${product['price']}")
                    if 'availability' in product:
                        print(f"     Availability: {product['availability']}")
                    print()
            else:
                print("❌ No products found")
        
        # Test cache functionality
        print("🔄 Testing cache functionality...")
        start_time = datetime.now()
        cached_stores = await sonar_client.search_stores(test_zipcode)
        cache_time = (datetime.now() - start_time).total_seconds()
        print(f"✅ Cached response time: {cache_time:.2f} seconds")
        
        print(f"📊 Cache size: {len(sonar_client._cache)} entries")
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()

async def test_error_handling():
    """Test error handling scenarios"""
    
    print("\n🧪 Testing Error Handling")
    print("=" * 30)
    
    sonar_client = SonarClient()
    
    if not sonar_client.is_available():
        print("❌ Skipping error handling tests - no API key")
        return
    
    # Test with invalid zipcode
    try:
        print("Testing invalid zipcode...")
        stores = await sonar_client.search_stores("00000")
        print(f"✅ Invalid zipcode handled gracefully: {len(stores)} stores found")
    except Exception as e:
        print(f"❌ Invalid zipcode test failed: {e}")
    
    # Test with empty query
    try:
        print("Testing empty product search...")
        products = await sonar_client.search_products("", "Test Store", "Test Location")
        print(f"✅ Empty query handled gracefully: {len(products)} products found")
    except Exception as e:
        print(f"❌ Empty query test failed: {e}")

def main():
    """Main test function"""
    print("🧪 Perplexity Sonar API Test Suite")
    print("=" * 50)
    
    # Check environment
    api_key = os.environ.get("PERPLEXITY_API_KEY")
    if not api_key:
        print("⚠️  PERPLEXITY_API_KEY not set")
        print("   Set it with: export PERPLEXITY_API_KEY='your-api-key-here'")
        print("   Or create a .env file with: PERPLEXITY_API_KEY=your-api-key-here")
        print()
    
    # Run tests
    asyncio.run(test_sonar_functionality())
    asyncio.run(test_error_handling())
    
    print("\n✅ Test suite completed!")

if __name__ == "__main__":
    main()

