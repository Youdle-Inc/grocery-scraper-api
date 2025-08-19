#!/usr/bin/env python3
"""
Simple test to see raw Sonar API response for product search.
"""

import asyncio
import os
from dotenv import load_dotenv
from scraper.sonar_client import SonarClient

# Load environment variables
load_dotenv()

async def test_raw_response():
    """Test to see raw Sonar API response"""
    
    # Initialize Sonar client
    sonar_client = SonarClient()
    
    if not sonar_client.is_available():
        print("❌ Sonar client not available. Please set PERPLEXITY_API_KEY environment variable.")
        return
    
    print("🔍 Testing raw Sonar response for product search...")
    
    try:
        # Test query
        query = "oat milk"
        store = "Target"
        location = "Chicago, IL"
        
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
        
        # Check if response contains image URLs
        if "IMAGE_URL:" in raw_response:
            print("✅ IMAGE_URL field found in response!")
        else:
            print("❌ IMAGE_URL field not found in response")
        
        if "http" in raw_response and any(ext in raw_response.lower() for ext in ['.jpg', '.jpeg', '.png', '.gif']):
            print("✅ Image URLs found in response!")
        else:
            print("❌ No image URLs found in response")
            
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    asyncio.run(test_raw_response())
