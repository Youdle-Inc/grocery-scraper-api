#!/usr/bin/env python3
"""
Test script for the hybrid scraper functionality.
Demonstrates how Sonar discovery + web scraping enrichment works together.
"""

import asyncio
import os
from dotenv import load_dotenv
from scraper.sonar_client import SonarClient
from scraper.hybrid_scraper import HybridScraper

# Load environment variables
load_dotenv()

async def test_hybrid_scraper():
    """Test the hybrid scraper functionality"""
    
    print("🔍 Testing Hybrid Scraper (Sonar + Web Scraping)")
    print("=" * 60)
    
    # Initialize Sonar client
    sonar_client = SonarClient()
    
    if not sonar_client.is_available():
        print("❌ Sonar client not available. Please set PERPLEXITY_API_KEY environment variable.")
        return
    
    print("✅ Sonar client available")
    
    # Test stores and queries
    test_cases = [
        ("Target", "oat milk", "Chicago, IL"),
        ("Walmart", "organic bananas", "Chicago, IL"),
        ("Whole Foods", "almond milk", "Chicago, IL"),
        ("Trader Joe's", "organic eggs", "Chicago, IL")
    ]
    
    for store_name, query, location in test_cases:
        print(f"\n🛒 Testing: {query} at {store_name}")
        print("-" * 40)
        
        try:
            # Get products from Sonar
            print(f"🔍 Searching Sonar for '{query}' at {store_name}...")
            products = await sonar_client.search_products(query, store_name, location)
            
            if not products:
                print("❌ No products found")
                continue
            
            print(f"✅ Found {len(products)} products from Sonar")
            
            # Show first product before enhancement
            first_product = products[0]
            print(f"\n📦 First product (Sonar only):")
            print(f"   Name: {first_product.get('name', 'N/A')}")
            print(f"   Brand: {first_product.get('brand', 'N/A')}")
            print(f"   Price: {first_product.get('price', 'N/A')}")
            print(f"   Image URL: {first_product.get('image_url', 'None')}")
            
            # Test hybrid enhancement
            print(f"\n🔧 Testing hybrid enhancement...")
            hybrid_scraper = HybridScraper()
            enhanced_products = await hybrid_scraper.enhance_products(products, store_name)
            
            # Show enhanced product
            enhanced_product = enhanced_products[0]
            print(f"\n📦 Enhanced product (Sonar + Scraping):")
            print(f"   Name: {enhanced_product.get('name', 'N/A')}")
            print(f"   Brand: {enhanced_product.get('brand', 'N/A')}")
            print(f"   Price: {enhanced_product.get('price', 'N/A')}")
            print(f"   Image URL: {enhanced_product.get('image_url', 'None')}")
            print(f"   Nutritional Info: {enhanced_product.get('nutritional_info', 'N/A')}")
            print(f"   Ingredients: {enhanced_product.get('ingredients', 'N/A')}")
            print(f"   Allergens: {enhanced_product.get('allergens', 'N/A')}")
            print(f"   Online Available: {enhanced_product.get('online_available', 'N/A')}")
            print(f"   In Store Only: {enhanced_product.get('in_store_only', 'N/A')}")
            
            # Check what new fields were added
            original_keys = set(first_product.keys())
            enhanced_keys = set(enhanced_product.keys())
            new_fields = enhanced_keys - original_keys
            
            if new_fields:
                print(f"\n✨ New fields added by hybrid scraper:")
                for field in new_fields:
                    print(f"   - {field}: {enhanced_product.get(field, 'N/A')}")
            else:
                print(f"\n⚠️ No new fields added")
            
        except Exception as e:
            print(f"❌ Error testing {store_name}: {e}")
        
        print("\n" + "=" * 60)

async def test_store_specific_scrapers():
    """Test individual store scrapers"""
    
    print("\n🧪 Testing Store-Specific Scrapers")
    print("=" * 50)
    
    test_product = "Oatly Oat Milk"
    test_brand = "Oatly"
    
    stores = [
        "Target",
        "Walmart", 
        "Whole Foods",
        "Trader Joe's",
        "Kroger",
        "Safeway"
    ]
    
    for store_name in stores:
        print(f"\n🏪 Testing {store_name} scraper...")
        
        try:
            hybrid_scraper = HybridScraper()
            scraper = hybrid_scraper.get_store_scraper(store_name)
            
            details = await scraper.get_product_details(test_product, test_brand, store_name)
            
            print(f"   Image URL: {details.get('image_url', 'None')}")
            print(f"   Online Available: {details.get('online_available', 'N/A')}")
            print(f"   In Store Only: {details.get('in_store_only', 'N/A')}")
            
        except Exception as e:
            print(f"   ❌ Error: {e}")

if __name__ == "__main__":
    asyncio.run(test_hybrid_scraper())
    asyncio.run(test_store_specific_scrapers())

