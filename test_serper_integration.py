#!/usr/bin/env python3
"""
Test script to demonstrate Serper API integration
"""

import asyncio
import json
import os
from dotenv import load_dotenv
from scraper.serper_client import SerperClient

load_dotenv()

async def test_serper_integration():
    """Test the Serper API integration"""
    
    print("🧪 Testing Serper API Integration")
    print("=" * 50)
    
    # Initialize Serper client
    serper_client = SerperClient()
    
    if not serper_client.is_available():
        print("❌ Serper API not available. Please run setup_serper.py first.")
        return
    
    # Test shopping search
    print("\n🔍 Testing Shopping Search...")
    products = await serper_client.search_shopping_products("oat milk", "Target", "United States")
    
    if products:
        print(f"✅ Found {len(products)} products")
        for i, product in enumerate(products[:3]):  # Show first 3
            print(f"\n  {i+1}. {product['name']}")
            print(f"     Price: ${product.get('price', 'N/A')}")
            print(f"     URL: {product.get('product_url', 'N/A')}")
            print(f"     Image: {product.get('image_url', 'N/A')}")
            print(f"     Source: {product.get('source', 'N/A')}")
    else:
        print("❌ No products found")
    
    # Test image search
    print("\n🖼️ Testing Image Search...")
    images = await serper_client.search_product_images("oat milk", "Target")
    
    if images:
        print(f"✅ Found {len(images)} images")
        for i, image_url in enumerate(images[:3]):  # Show first 3
            print(f"  {i+1}. {image_url}")
    else:
        print("❌ No images found")
    
    # Test product enhancement
    print("\n🔗 Testing Product Enhancement...")
    
    # Mock Perplexity products
    mock_products = [
        {
            "name": "Oatly Oat Milk Original",
            "price": 4.49,
            "brand": "Oatly",
            "size": "32 oz",
            "description": "Original oat milk, creamy and delicious"
        },
        {
            "name": "Silk Original Oat Milk",
            "price": 6.29,
            "brand": "Silk",
            "size": "59 fl oz",
            "description": "Creamy original oat milk"
        }
    ]
    
    enhanced_products = await serper_client.enhance_products_with_serper(
        mock_products, "Target", "United States"
    )
    
    print(f"✅ Enhanced {len(enhanced_products)} products")
    for i, product in enumerate(enhanced_products):
        print(f"\n  {i+1}. {product['name']}")
        print(f"     Original Price: ${product.get('price', 'N/A')}")
        print(f"     Real Price: ${product.get('real_price', 'N/A')}")
        print(f"     Product URL: {product.get('product_url', 'N/A')}")
        print(f"     Image URL: {product.get('image_url', 'N/A')}")
        print(f"     Serper Source: {product.get('serper_source', 'N/A')}")

if __name__ == "__main__":
    asyncio.run(test_serper_integration())

