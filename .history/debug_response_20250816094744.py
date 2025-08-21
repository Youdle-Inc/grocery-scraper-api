#!/usr/bin/env python3
"""
Debug script to see raw Sonar API response
"""

import asyncio
import os
from dotenv import load_dotenv
from scraper.sonar_client import SonarClient

# Load environment variables
load_dotenv()

async def debug_response():
    """Debug the raw response from Sonar API"""
    
    sonar_client = SonarClient()
    
    if not sonar_client.is_available():
        print("❌ Sonar client not available")
        return
    
    print("🔍 Testing Sonar API response...")
    
    try:
        # Get the raw response
        query = sonar_client._create_store_query("60622")
        print(f"Query: {query}")
        print("\n" + "="*50 + "\n")
        
        response = await sonar_client._make_sonar_request(query)
        print(f"Raw Response:\n{response}")
        print("\n" + "="*50 + "\n")
        
        # Try to parse it
        stores = sonar_client._parse_store_response(response, "60622")
        print(f"Parsed stores: {len(stores)}")
        for store in stores:
            print(f"- {store.store_name}: {store.address}")
            
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    asyncio.run(debug_response())
