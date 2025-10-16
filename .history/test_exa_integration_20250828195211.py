#!/usr/bin/env python3
"""
Test script for Exa API integration
"""

import asyncio
import os
import sys
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

async def test_exa_client():
    """Test Exa client functionality"""
    print("🧪 Testing Exa API Client...")
    
    try:
        from scraper.exa_client import ExaClient
        
        # Initialize client
        client = ExaClient()
        
        print(f"✅ Client initialized: {client.is_available()}")
        print(f"   API Key configured: {bool(client.api_key)}")
        
        if not client.is_available():
            print("❌ Exa client not available. Please check EXA_API_KEY in .env")
            return False
        
        # Test search functionality
        print("\n🔍 Testing product search...")
        query = "organic milk"
        store_name = "Target"
        
        products = await client.search_products(query, store_name, "United States")
        
        print(f"✅ Search completed: {len(products)} products found")
        
        if products:
            print("\n📋 Sample product:")
            product = products[0]
            print(f"   Name: {product.get('name', 'N/A')}")
            print(f"   Price: {product.get('price', 'N/A')}")
            print(f"   URL: {product.get('product_url', 'N/A')}")
            print(f"   Image: {product.get('image_url', 'N/A')}")
            print(f"   Source: {product.get('exa_source', 'N/A')}")
        
        # Test contents functionality
        print("\n📄 Testing contents retrieval...")
        if products and products[0].get('product_url'):
            urls = [products[0]['product_url']]
            contents = await client.get_contents(urls)
            print(f"✅ Contents retrieved: {len(contents)} items")
        
        return True
        
    except ImportError as e:
        print(f"❌ Import error: {e}")
        return False
    except Exception as e:
        print(f"❌ Test error: {e}")
        return False

async def test_exa_with_perplexity():
    """Test Exa integration with Perplexity Sonar"""
    print("\n🔄 Testing Exa + Perplexity integration...")
    
    try:
        from scraper.exa_client import ExaClient
        from scraper.sonar_client import SonarClient
        
        exa_client = ExaClient()
        sonar_client = SonarClient()
        
        if not exa_client.is_available():
            print("❌ Exa client not available")
            return False
        
        if not sonar_client.is_available():
            print("❌ Sonar client not available")
            return False
        
        # Get products from Sonar
        print("🔍 Getting products from Perplexity Sonar...")
        sonar_products = await sonar_client.search_products("milk", "Target", "10001", enhance=False)
        
        if not sonar_products:
            print("❌ No products from Sonar")
            return False
        
        print(f"✅ Got {len(sonar_products)} products from Sonar")
        
        # Enhance with Exa
        print("🔧 Enhancing products with Exa...")
        enhanced_products = await exa_client.enhance_products_with_exa(
            sonar_products, "Target", "United States"
        )
        
        print(f"✅ Enhanced {len(enhanced_products)} products")
        
        # Show enhancement results
        if enhanced_products:
            print("\n📋 Enhanced product sample:")
            product = enhanced_products[0]
            print(f"   Name: {product.get('name', 'N/A')}")
            print(f"   Original URL: {product.get('product_url', 'N/A')}")
            print(f"   Enhanced URL: {product.get('product_url', 'N/A')}")
            print(f"   Enhanced Image: {product.get('image_url', 'N/A')}")
            print(f"   Exa Source: {product.get('exa_source', 'N/A')}")
        
        return True
        
    except Exception as e:
        print(f"❌ Integration test error: {e}")
        return False

async def main():
    """Main test function"""
    print("=" * 60)
    print("🔍 Exa API Integration Test")
    print("=" * 60)
    
    # Test basic Exa client
    exa_success = await test_exa_client()
    
    if exa_success:
        # Test integration with Perplexity
        integration_success = await test_exa_with_perplexity()
        
        if integration_success:
            print("\n🎉 All tests passed! Exa API integration is working correctly.")
        else:
            print("\n⚠️ Basic Exa client works, but integration test failed.")
    else:
        print("\n❌ Exa client test failed. Please check your configuration.")
    
    print("\n" + "=" * 60)

if __name__ == "__main__":
    asyncio.run(main())
