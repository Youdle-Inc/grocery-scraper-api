#!/usr/bin/env python3
"""
Test Perplexity Sonar integration
"""

import asyncio
import os
from scraper.sonar_client import SonarClient

async def test_sonar():
    """Test Perplexity Sonar integration"""
    print("Testing Perplexity Sonar integration...")
    
    # Initialize Sonar client
    api_key = "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"
    sonar_client = SonarClient(api_key)
    
    print(f"Sonar available: {sonar_client.is_available()}")
    
    if sonar_client.is_available():
        print("🔍 Testing Sonar store search...")
        try:
            stores = await sonar_client.search_stores("90210")
            print(f"✅ Found {len(stores)} stores via Sonar")
            for store in stores:
                print(f"  - {store.store_name} ({store.store_id})")
                if store.address:
                    print(f"    Address: {store.address}")
                if store.services:
                    print(f"    Services: {store.services}")
        except Exception as e:
            print(f"❌ Sonar test failed: {e}")
    else:
        print("❌ Sonar client not available")

if __name__ == "__main__":
    asyncio.run(test_sonar())
