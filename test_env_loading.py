#!/usr/bin/env python3
"""
Test script to verify environment loading and API functionality
"""

import os
import sys
from dotenv import load_dotenv

def test_env_loading():
    """Test environment variable loading"""
    print("🧪 Testing Environment Loading")
    print("=" * 40)
    
    # Load environment variables
    load_dotenv()
    
    # Check if EXA_API_KEY is loaded
    exa_key = os.getenv("EXA_API_KEY")
    print(f"✅ EXA_API_KEY loaded: {bool(exa_key)}")
    if exa_key:
        print(f"   Key: {exa_key[:10]}...")
    else:
        print("   ❌ EXA_API_KEY not found")
        return False
    
    return True

def test_exa_client():
    """Test ExaStructuredClient initialization"""
    print("\n🔍 Testing ExaStructuredClient")
    print("-" * 40)
    
    try:
        from scraper.exa_structured_client import ExaStructuredClient
        
        # Initialize client
        client = ExaStructuredClient()
        
        print(f"✅ Client initialized: {client is not None}")
        print(f"✅ Client available: {client.is_available()}")
        print(f"✅ API key loaded: {bool(client.api_key)}")
        print(f"✅ Exa client object: {client._client is not None}")
        
        if client._client:
            print(f"   Exa client type: {type(client._client)}")
        
        return client.is_available()
        
    except Exception as e:
        print(f"❌ Error initializing client: {e}")
        return False

def test_api_endpoints():
    """Test API endpoints"""
    print("\n🌐 Testing API Endpoints")
    print("-" * 40)
    
    try:
        import requests
        
        # Test health endpoint
        response = requests.get("http://localhost:8000/health", timeout=5)
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Health endpoint: {data.get('status', 'unknown')}")
            print(f"   Exa API status: {data.get('services', {}).get('exa_api', 'unknown')}")
        else:
            print(f"❌ Health endpoint failed: {response.status_code}")
            return False
        
        # Test root endpoint
        response = requests.get("http://localhost:8000/", timeout=5)
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Root endpoint: {data.get('name', 'unknown')}")
        else:
            print(f"❌ Root endpoint failed: {response.status_code}")
            return False
        
        return True
        
    except requests.exceptions.ConnectionError:
        print("❌ API not running - start it with: python main.py")
        return False
    except Exception as e:
        print(f"❌ Error testing endpoints: {e}")
        return False

def main():
    """Run all tests"""
    print("🚀 Grocery Scraper API - Environment & Client Test")
    print("=" * 60)
    
    # Test environment loading
    env_ok = test_env_loading()
    if not env_ok:
        print("\n❌ Environment loading failed")
        return
    
    # Test ExaStructuredClient
    client_ok = test_exa_client()
    if not client_ok:
        print("\n❌ ExaStructuredClient failed")
        return
    
    # Test API endpoints
    api_ok = test_api_endpoints()
    if not api_ok:
        print("\n❌ API endpoints failed")
        return
    
    print("\n🎉 All tests passed!")
    print("✅ Environment variables loaded correctly")
    print("✅ ExaStructuredClient working")
    print("✅ API endpoints responding")

if __name__ == "__main__":
    main()
