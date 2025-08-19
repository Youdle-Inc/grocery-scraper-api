#!/usr/bin/env python3
"""
Setup script for Serper API integration
"""

import os
import sys
from dotenv import load_dotenv

def setup_serper():
    """Guide user through Serper API setup"""
    
    print("🚀 Setting up Serper API Integration")
    print("=" * 50)
    
    # Check if .env file exists
    if not os.path.exists('.env'):
        print("❌ No .env file found. Please run setup_sonar.py first to create it.")
        return False
    
    # Load existing environment variables
    load_dotenv()
    
    # Check if SERPER_API_KEY already exists
    existing_key = os.getenv("SERPER_API_KEY")
    if existing_key:
        print(f"✅ SERPER_API_KEY already configured: {existing_key[:10]}...")
        return True
    
    print("\n📋 Serper API Setup Instructions:")
    print("1. Go to https://serpwow.com/")
    print("2. Sign up for a free account")
    print("3. Get your API key from the dashboard")
    print("4. The free tier includes 100 searches per month")
    
    print("\n🔑 Enter your Serper API key:")
    api_key = input("API Key: ").strip()
    
    if not api_key:
        print("❌ No API key provided")
        return False
    
    # Validate API key format (basic check)
    if not api_key.startswith(('demo', 'live_')):
        print("⚠️  Warning: API key doesn't match expected format")
        print("   Expected format: 'demo' or 'live_...'")
        continue_setup = input("Continue anyway? (y/n): ").lower()
        if continue_setup != 'y':
            return False
    
    # Save to .env file
    try:
        with open('.env', 'a') as f:
            f.write(f"\n# Serper API Key\nSERPER_API_KEY={api_key}\n")
        
        print("✅ SERPER_API_KEY saved to .env file")
        
        # Test the API key
        print("\n🧪 Testing Serper API key...")
        if test_serper_api(api_key):
            print("✅ Serper API key is working!")
            return True
        else:
            print("❌ Serper API key test failed")
            return False
            
    except Exception as e:
        print(f"❌ Failed to save API key: {e}")
        return False

def test_serper_api(api_key):
    """Test the Serper API key with a simple search"""
    try:
        import requests
        
        params = {
            'api_key': api_key,
            'engine': 'google',
            'search_type': 'shopping',
            'q': 'test product',
            'gl': 'us',
            'hl': 'en',
            'num': 1
        }
        
        response = requests.get('https://api.serpwow.com/live/search', params=params, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            if 'shopping_results' in data:
                print(f"   Found {len(data['shopping_results'])} test results")
                return True
            else:
                print(f"   No shopping results found: {data}")
                return False
        else:
            print(f"   API error: {response.status_code} - {response.text}")
            return False
            
    except Exception as e:
        print(f"   Test failed: {e}")
        return False

if __name__ == "__main__":
    success = setup_serper()
    if success:
        print("\n🎉 Serper API setup completed successfully!")
        print("\n📖 Next steps:")
        print("1. Restart your API server")
        print("2. Test with: curl 'http://localhost:8000/sonar/products/search?query=milk&store_name=Target&location=Chicago,IL'")
        print("3. The API will now automatically enhance products with real URLs and images from Serper")
    else:
        print("\n❌ Serper API setup failed")
        sys.exit(1)
