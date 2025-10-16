#!/usr/bin/env python3
"""
Test script for Exa Structured Client
Tests the new Exa-powered grocery search API
"""

import asyncio
import os
from dotenv import load_dotenv
from scraper.exa_structured_client import ExaStructuredClient

# Load environment variables
load_dotenv()

async def test_exa_structured_client():
    """Test Exa structured client functionality"""
    
    print("🧪 Testing Exa Structured Client")
    print("=" * 60)
    
    # Initialize client
    client = ExaStructuredClient()
    
    if not client.is_available():
        print("❌ Exa client not available. Please set EXA_API_KEY in .env")
        return
    
    print("✅ Exa structured client initialized")
    print()
    
    # Test 1: Product search with store filter
    print("📦 Test 1: Product search at Target")
    print("-" * 60)
    
    products = await client.search_products_structured(
        query="oat milk",
        store_name="Target",
        zipcode="10001",
        num_results=5,
        include_location=True
    )
    
    print(f"Found {len(products)} products")
    for i, product in enumerate(products, 1):
        print(f"\n{i}. {product.get('name', 'Unknown')}")
        print(f"   Brand: {product.get('brand', 'N/A')}")
        print(f"   Price: ${product.get('price', 'N/A')} {product.get('currency', 'USD')}")
        print(f"   Quantity: {product.get('quantity', 'N/A')}")
        print(f"   Availability: {product.get('availability', 'N/A')}")
        print(f"   Store: {product.get('store_name', 'N/A')}")
        print(f"   Address: {product.get('store_address', 'N/A')}")
        print(f"   ZIP: {product.get('store_zipcode', 'N/A')}")
        print(f"   Image: {product.get('image_url', 'N/A')[:80] if product.get('image_url') else 'N/A'}")
        print(f"   URL: {product.get('product_url', 'N/A')[:80] if product.get('product_url') else 'N/A'}")
    
    print("\n" + "=" * 60)
    
    # Test 2: Generic product search (all stores)
    print("\n📦 Test 2: Generic product search (organic eggs)")
    print("-" * 60)
    
    products = await client.search_products_structured(
        query="organic eggs",
        zipcode="10001",
        num_results=10
    )
    
    print(f"Found {len(products)} products across stores")
    
    # Group by store
    stores = {}
    for product in products:
        store_name = product.get('store_name', 'Unknown')
        if store_name not in stores:
            stores[store_name] = []
        stores[store_name].append(product)
    
    for store_name, store_products in stores.items():
        print(f"\n{store_name}: {len(store_products)} products")
        for product in store_products[:2]:  # Show first 2 from each store
            print(f"  - {product.get('name', 'Unknown')}: ${product.get('price', 'N/A')}")
    
    print("\n" + "=" * 60)
    
    # Test 3: Store location search
    print("\n🏪 Test 3: Store location search")
    print("-" * 60)
    
    stores = await client.search_stores_in_zipcode("Walmart", "10001")
    
    print(f"Found {len(stores)} Walmart stores near 10001")
    for i, store in enumerate(stores[:3], 1):  # Show first 3
        print(f"\n{i}. {store.get('store_name', 'Unknown')}")
        print(f"   Address: {store.get('address', 'N/A')}")
        print(f"   City: {store.get('city', 'N/A')}, {store.get('state', 'N/A')} {store.get('zipcode', 'N/A')}")
        print(f"   Services: {', '.join(store.get('services', []))}")
    
    print("\n" + "=" * 60)
    print("✅ All tests completed!")


async def main():
    """Main test runner"""
    try:
        await test_exa_structured_client()
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())

