#!/usr/bin/env python3
"""
Debug script to test real URL extraction from Perplexity API
"""

import asyncio
import json
import os
import requests
from dotenv import load_dotenv

load_dotenv()

async def debug_real_urls():
    """Debug the real URL extraction functionality"""
    
    api_key = os.getenv("PERPLEXITY_API_KEY")
    if not api_key:
        print("❌ No PERPLEXITY_API_KEY found in .env file")
        return
    
    base_url = "https://api.perplexity.ai/chat/completions"
    
    # Test query for grocery products
    query = """Find current product information for "oat milk" at Target in Chicago, IL.

Return results in this EXACT format (one product per section, separated by blank lines):

PRODUCT: [Product Name]
BRAND: [Brand Name]
PRICE: [Price with $ symbol, or "Price not available"]
SIZE: [Size/quantity, e.g., "32 oz", "1 gallon", "12 pack"]
CATEGORY: [Product category, e.g., "Dairy", "Beverages", "Organic"]
AVAILABILITY: [in stock/out of stock/limited]
DESCRIPTION: [Brief product description]
IMAGE_URL: [Actual product image URL from store website, or "N/A" if not found]
DEALS: [Any current deals, discounts, or "None"]"""
    
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    data = {
        "model": "sonar",
        "messages": [
            {
                "role": "user",
                "content": query
            }
        ],
        "max_tokens": 2048,
        "temperature": 0.1,
        "top_p": 0.9,
        "stream": False
    }
    
    try:
        print("🔍 Making Perplexity API request...")
        response = requests.post(base_url, headers=headers, json=data, timeout=45)
        
        if response.status_code == 200:
            result = response.json()
            
            # Extract citations and search results
            citations = result.get("citations", [])
            search_results = result.get("search_results", [])
            
            print(f"\n🎯 CITATIONS ({len(citations)}):")
            for i, citation in enumerate(citations):
                print(f"  {i+1}. {citation}")
            
            print(f"\n🔍 SEARCH RESULTS ({len(search_results)}):")
            for i, result in enumerate(search_results):
                print(f"  {i+1}. {result.get('title', 'No title')}")
                print(f"     URL: {result.get('url', 'No URL')}")
                print(f"     Date: {result.get('date', 'No date')}")
                print()
            
            # Test URL extraction
            print("🔗 TESTING URL EXTRACTION:")
            
            def extract_product_name_from_url(url: str) -> str:
                """Extract product name from store URL"""
                try:
                    if "target.com/p/" in url:
                        # Extract from Target URL: /p/product-name/-/A-123456
                        parts = url.split("/p/")
                        if len(parts) > 1:
                            product_part = parts[1].split("/-/")[0]
                            return product_part.replace("-", " ").title()
                    
                    elif "walmart.com/ip/" in url:
                        # Extract from Walmart URL: /ip/product-name/123456
                        parts = url.split("/ip/")
                        if len(parts) > 1:
                            product_part = parts[1].split("/")[0]
                            return product_part.replace("-", " ").title()
                    
                    elif "amazon.com/dp/" in url:
                        # For Amazon, we'll use the ASIN as the identifier
                        parts = url.split("/dp/")
                        if len(parts) > 1:
                            asin = parts[1].split("/")[0]
                            return f"Amazon Product {asin}"
                
                except Exception as e:
                    print(f"    ❌ Failed to extract product name from URL {url}: {e}")
                
                return ""
            
            real_urls = {}
            
            # Extract from citations
            for citation in citations:
                if "target.com/p/" in citation or "walmart.com/ip/" in citation or "amazon.com/dp/" in citation:
                    product_name = extract_product_name_from_url(citation)
                    if product_name:
                        real_urls[product_name.lower()] = citation
                        print(f"    ✅ Found product: {product_name} -> {citation}")
            
            # Extract from search results
            for result in search_results:
                url = result.get("url", "")
                if "target.com/p/" in url or "walmart.com/ip/" in url or "amazon.com/dp/" in url:
                    product_name = extract_product_name_from_url(url)
                    if product_name:
                        real_urls[product_name.lower()] = url
                        print(f"    ✅ Found product: {product_name} -> {url}")
            
            print(f"\n📊 SUMMARY: Found {len(real_urls)} real product URLs")
            for product_name, url in real_urls.items():
                print(f"    {product_name}: {url}")
                
        else:
            print(f"❌ API Error: {response.status_code}")
            print(response.text)
            
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    asyncio.run(debug_real_urls())

