#!/usr/bin/env python3
"""
Setup script for Google Custom Search API integration.
This helps users configure the Google API for product image enhancement.
"""

import os
import sys
from dotenv import load_dotenv

def setup_google_api():
    """Guide user through Google API setup"""
    
    print("🖼️ Google Custom Search API Setup for Product Images")
    print("=" * 60)
    print()
    print("This will help you set up Google Custom Search API to enhance")
    print("product search results with actual product images.")
    print()
    print("You'll need:")
    print("1. Google Cloud Console account")
    print("2. Custom Search API enabled")
    print("3. API key and Search Engine ID")
    print()
    
    # Check if already configured
    load_dotenv()
    api_key = os.environ.get("GOOGLE_API_KEY")
    search_engine_id = os.environ.get("GOOGLE_SEARCH_ENGINE_ID")
    
    if api_key and search_engine_id:
        print("✅ Google API already configured!")
        print(f"   API Key: {api_key[:10]}...")
        print(f"   Search Engine ID: {search_engine_id}")
        print()
        response = input("Do you want to reconfigure? (y/N): ").lower()
        if response != 'y':
            print("Setup cancelled.")
            return
    
    print("📋 Setup Instructions:")
    print()
    print("1. Go to Google Cloud Console: https://console.cloud.google.com/")
    print("2. Create a new project or select existing one")
    print("3. Enable the Custom Search API")
    print("4. Create credentials (API Key)")
    print("5. Go to Custom Search Engine: https://cse.google.com/")
    print("6. Create a new search engine")
    print("7. Enable 'Image Search'")
    print("8. Get your Search Engine ID")
    print()
    
    # Get API Key
    print("🔑 Enter your Google API Key:")
    api_key = input("API Key: ").strip()
    
    if not api_key:
        print("❌ API Key is required!")
        return
    
    # Get Search Engine ID
    print()
    print("🔍 Enter your Custom Search Engine ID:")
    search_engine_id = input("Search Engine ID: ").strip()
    
    if not search_engine_id:
        print("❌ Search Engine ID is required!")
        return
    
    # Save to .env file
    env_file = ".env"
    env_content = ""
    
    # Read existing .env file
    if os.path.exists(env_file):
        with open(env_file, 'r') as f:
            env_content = f.read()
    
    # Update or add Google API settings
    lines = env_content.split('\n') if env_content else []
    updated_lines = []
    
    # Remove existing Google API settings
    for line in lines:
        if not line.startswith("GOOGLE_API_KEY=") and not line.startswith("GOOGLE_SEARCH_ENGINE_ID="):
            updated_lines.append(line)
    
    # Add new settings
    updated_lines.append(f"GOOGLE_API_KEY={api_key}")
    updated_lines.append(f"GOOGLE_SEARCH_ENGINE_ID={search_engine_id}")
    
    # Write back to .env file
    with open(env_file, 'w') as f:
        f.write('\n'.join(updated_lines))
    
    print()
    print("✅ Google API configuration saved to .env file!")
    print()
    print("🔧 Next steps:")
    print("1. Restart your API server")
    print("2. Test with: curl 'http://localhost:8000/sonar/products/search?query=milk&store_name=Target&location=Chicago,IL'")
    print("3. Check if products now include image_url fields")
    print()
    print("📚 For more help:")
    print("- Google Custom Search API docs: https://developers.google.com/custom-search")
    print("- Custom Search Engine setup: https://cse.google.com/")

def test_google_api():
    """Test the Google API configuration"""
    
    print("🧪 Testing Google API Configuration")
    print("=" * 40)
    
    load_dotenv()
    api_key = os.environ.get("GOOGLE_API_KEY")
    search_engine_id = os.environ.get("GOOGLE_SEARCH_ENGINE_ID")
    
    if not api_key or not search_engine_id:
        print("❌ Google API not configured!")
        print("Run setup first: python setup_google_images.py")
        return
    
    print("✅ Google API configured")
    print(f"   API Key: {api_key[:10]}...")
    print(f"   Search Engine ID: {search_engine_id}")
    
    # Test the API
    try:
        import asyncio
        from scraper.google_image_search import GoogleImageSearch
        
        async def test_search():
            async with GoogleImageSearch() as searcher:
                if searcher.is_available():
                    print("✅ Google Image Search is available")
                    
                    # Test a simple search
                    image_url = await searcher.search_product_image("oat milk", "Oatly")
                    if image_url:
                        print(f"✅ Test search successful: {image_url}")
                    else:
                        print("⚠️ Test search returned no results (this might be normal)")
                else:
                    print("❌ Google Image Search not available")
        
        asyncio.run(test_search())
        
    except Exception as e:
        print(f"❌ Test failed: {e}")

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "test":
        test_google_api()
    else:
        setup_google_api()
