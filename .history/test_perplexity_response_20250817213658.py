#!/usr/bin/env python3
"""
Test script to see the full Perplexity API response format
"""

import asyncio
import json
import os
import requests
from dotenv import load_dotenv

load_dotenv()

async def test_perplexity_response():
    """Test the full Perplexity API response to see if it includes citations/sources"""
    
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
            
            print("\n📋 FULL API RESPONSE:")
            print("=" * 50)
            print(json.dumps(result, indent=2))
            print("=" * 50)
            
            # Check for citations/sources
            if "citations" in result:
                print("\n🎯 CITATIONS FOUND:")
                print(json.dumps(result["citations"], indent=2))
            
            if "usage" in result:
                print("\n📊 USAGE INFO:")
                print(json.dumps(result["usage"], indent=2))
            
            # Check the choices structure
            if "choices" in result and len(result["choices"]) > 0:
                choice = result["choices"][0]
                print(f"\n📝 MESSAGE CONTENT LENGTH: {len(choice['message']['content'])}")
                
                # Check if there are any additional fields in the message
                print(f"\n🔍 MESSAGE KEYS: {list(choice['message'].keys())}")
                
                # Check if there are any additional fields in the choice
                print(f"🔍 CHOICE KEYS: {list(choice.keys())}")
                
        else:
            print(f"❌ API Error: {response.status_code}")
            print(response.text)
            
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    asyncio.run(test_perplexity_response())
