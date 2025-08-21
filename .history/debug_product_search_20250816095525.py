#!/usr/bin/env python3
"""
Debug script to test improved product search parsing
"""

import asyncio
import os
from dotenv import load_dotenv
from scraper.sonar_client import SonarClient

# Load environment variables
load_dotenv()

async def debug_product_search():
    """Debug the improved product search parsing"""
    
    sonar_client = SonarClient()
    
    if not sonar_client.is_available():
        print("❌ Sonar client not available")
        return
    
    print("🔍 Testing improved product search...")
    
    try:
        # Test product search
        products = await sonar_client.search_products(
            "oat milk", 
            "Mariano's Ukrainian Village", 
            "Chicago, IL"
        )
        
        print(f"\nFound {len(products)} products:")
        for i, product in enumerate(products, 1):
            print(f"\n--- Product {i} ---")
            for key, value in product.items():
                print(f"{key}: {value}")
                
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    asyncio.run(debug_product_search())
