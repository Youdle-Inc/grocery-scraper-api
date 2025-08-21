#!/usr/bin/env python3
"""
Debug script to see why image URLs aren't appearing in product search.
"""

import asyncio
import os
from dotenv import load_dotenv
from scraper.sonar_client import SonarClient

# Load environment variables
load_dotenv()

async def debug_image_urls():
    """Debug why image URLs aren't appearing"""
    
    # Initialize Sonar client
    sonar_client = SonarClient()
    
    if not sonar_client.is_available():
        print("❌ Sonar client not available. Please set PERPLEXITY_API_KEY environment variable.")
        return
    
    print("🔍 Debugging image URL parsing...")
    
    try:
        # Test query
        query = "oat milk"
        store = "Target"
        location = "Chicago, IL"
        
        # Get the raw response first
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
        
        print("📄 Raw Sonar Response:")
        print("=" * 80)
        raw_response = await sonar_client._make_sonar_request(search_query)
        print(raw_response)
        print("=" * 80)
        
        # Check if IMAGE_URL appears in the response
        if "IMAGE_URL:" in raw_response:
            print("✅ IMAGE_URL field found in raw response!")
        else:
            print("❌ IMAGE_URL field NOT found in raw response")
        
        # Check for any URLs in the response
        import re
        url_pattern = r'https?://[^\s]+'
        urls = re.findall(url_pattern, raw_response)
        if urls:
            print(f"✅ Found {len(urls)} URLs in response:")
            for url in urls:
                print(f"   {url}")
        else:
            print("❌ No URLs found in response")
        
        # Now test the parsed response
        print("\n🔧 Testing parsed response:")
        products = await sonar_client.search_products(query, store, location)
        
        print(f"✅ Found {len(products)} products")
        for i, product in enumerate(products[:2], 1):  # Show first 2 products
            print(f"\nProduct {i}:")
            for key, value in product.items():
                print(f"  {key}: {value}")
            
            if 'image_url' in product:
                print(f"  🖼️  Image URL: {product['image_url']}")
            else:
                print(f"  ❌ No image URL in parsed product")
            
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    asyncio.run(debug_image_urls())
