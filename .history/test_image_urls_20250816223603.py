#!/usr/bin/env python3
"""
Test script to check if image URLs are being returned in product search responses.
"""

import asyncio
import os
from dotenv import load_dotenv
from scraper.sonar_client import SonarClient

# Load environment variables
load_dotenv()

async def test_product_search_with_images():
    """Test product search to see if image URLs are included"""
    
    # Initialize Sonar client
    sonar_client = SonarClient()
    
    if not sonar_client.is_available():
        print("❌ Sonar client not available. Please set PERPLEXITY_API_KEY environment variable.")
        return
    
    print("🔍 Testing product search with image URLs...")
    
    # Test queries that might have images
    test_queries = [
        ("organic bananas", "Whole Foods", "Chicago, IL"),
        ("oat milk", "Target", "Chicago, IL"),
        ("chicken breast", "Walmart", "Chicago, IL"),
        ("organic eggs", "Trader Joe's", "Chicago, IL")
    ]
    
    for query, store, location in test_queries:
        print(f"\n📦 Searching for: {query} at {store}")
        print("=" * 50)
        
        try:
            # Get raw response first
            search_query = f"""Find current product information for "{query}" at {store} in {location}.

Return results in this EXACT format (one product per section, separated by blank lines):

PRODUCT: [Product Name]
BRAND: [Brand Name]
PRICE: [Price with $ symbol, or "Price not available"]
SIZE: [Size/quantity, e.g., "32 oz", "1 gallon", "12 pack"]
CATEGORY: [Product category, e.g., "Dairy", "Beverages", "Organic"]
AVAILABILITY: [in stock/out of stock/limited]
DESCRIPTION: [Brief product description]
IMAGE_URL: [Product image URL if available, or "N/A"]
DEALS: [Any current deals, discounts, or "None"]

Focus on current availability, accurate pricing, product images, and any active promotions. If no products found, return "No products found for this search.""""
            
            raw_response = await sonar_client._make_sonar_request(search_query)
            print("📄 Raw Sonar Response:")
            print(raw_response)
            print("\n" + "="*50)
            
            # Now test the parsed response
            products = await sonar_client.search_products(query, store, location)
            
            print(f"✅ Found {len(products)} products")
            for i, product in enumerate(products, 1):
                print(f"\nProduct {i}:")
                for key, value in product.items():
                    print(f"  {key}: {value}")
                
                # Check if image URL is present
                if 'image_url' in product:
                    print(f"  🖼️  Image URL: {product['image_url']}")
                else:
                    print(f"  ❌ No image URL found")
            
        except Exception as e:
            print(f"❌ Error testing {query}: {e}")
        
        print("\n" + "="*50)

if __name__ == "__main__":
    asyncio.run(test_product_search_with_images())
