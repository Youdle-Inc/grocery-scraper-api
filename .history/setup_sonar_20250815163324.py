#!/usr/bin/env python3
"""
Setup script for Perplexity Sonar integration
Helps users configure the API key and test the integration
"""

import os
import sys
import asyncio
from pathlib import Path

def check_environment():
    """Check if the environment is properly configured"""
    print("🔍 Checking environment configuration...")
    
    # Check Python version
    if sys.version_info < (3, 7):
        print("❌ Python 3.7+ required")
        return False
    
    print(f"✅ Python {sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}")
    
    # Check if we're in the right directory
    if not Path("main.py").exists():
        print("❌ Please run this script from the project root directory")
        return False
    
    print("✅ Project structure looks good")
    
    # Check dependencies
    try:
        import requests
        print("✅ requests library available")
    except ImportError:
        print("❌ requests library not found. Run: pip install -r requirements.txt")
        return False
    
    return True

def setup_api_key():
    """Help user set up the Perplexity API key"""
    print("\n🔑 Setting up Perplexity API Key")
    print("=" * 40)
    
    # Check if API key is already set
    api_key = os.environ.get("PERPLEXITY_API_KEY")
    if api_key:
        print(f"✅ API key already configured: {api_key[:10]}...")
        return True
    
    print("To use Perplexity Sonar integration, you need an API key:")
    print("1. Sign up at https://www.perplexity.ai/")
    print("2. Navigate to API settings")
    print("3. Generate an API key")
    print()
    
    # Ask user for API key
    api_key = input("Enter your Perplexity API key (or press Enter to skip): ").strip()
    
    if not api_key:
        print("⚠️  No API key provided. Sonar features will be disabled.")
        return False
    
    # Validate API key format
    if not api_key.startswith("pplx-"):
        print("⚠️  API key should start with 'pplx-'. Please check your key.")
        return False
    
    # Save to .env file
    env_file = Path(".env")
    if env_file.exists():
        # Read existing .env file
        with open(env_file, "r") as f:
            content = f.read()
        
        # Check if PERPLEXITY_API_KEY already exists
        if "PERPLEXITY_API_KEY" in content:
            # Update existing key
            lines = content.split("\n")
            for i, line in enumerate(lines):
                if line.startswith("PERPLEXITY_API_KEY="):
                    lines[i] = f"PERPLEXITY_API_KEY={api_key}"
                    break
            content = "\n".join(lines)
        else:
            # Add new key
            content += f"\nPERPLEXITY_API_KEY={api_key}"
    else:
        # Create new .env file
        content = f"PERPLEXITY_API_KEY={api_key}"
    
    # Write .env file
    with open(env_file, "w") as f:
        f.write(content)
    
    print(f"✅ API key saved to .env file")
    
    # Set environment variable for current session
    os.environ["PERPLEXITY_API_KEY"] = api_key
    
    return True

async def test_integration():
    """Test the Sonar integration"""
    print("\n🧪 Testing Sonar Integration")
    print("=" * 30)
    
    try:
        from scraper.sonar_client import SonarClient
        
        sonar_client = SonarClient()
        
        if not sonar_client.is_available():
            print("❌ Sonar client not available")
            return False
        
        print("✅ Sonar client initialized")
        
        # Test with a simple zipcode
        test_zipcode = "15213"  # Pittsburgh
        print(f"🔍 Testing store discovery for {test_zipcode}...")
        
        stores = await sonar_client.search_stores(test_zipcode)
        
        if stores:
            print(f"✅ Found {len(stores)} stores:")
            for store in stores[:3]:  # Show first 3 stores
                print(f"  - {store.store_name}")
            if len(stores) > 3:
                print(f"  ... and {len(stores) - 3} more")
        else:
            print("⚠️  No stores found (this might be normal for some zipcodes)")
        
        return True
        
    except Exception as e:
        print(f"❌ Integration test failed: {e}")
        return False

def show_next_steps():
    """Show next steps for the user"""
    print("\n🎉 Setup Complete!")
    print("=" * 20)
    print("Next steps:")
    print("1. Start the API server:")
    print("   uvicorn main:app --host 0.0.0.0 --port 8000 --reload")
    print()
    print("2. Test the Sonar endpoints:")
    print("   curl http://localhost:8000/sonar/status")
    print("   curl http://localhost:8000/sonar/stores/15213")
    print()
    print("3. Run the test suite:")
    print("   python test_sonar.py")
    print()
    print("4. View API documentation:")
    print("   http://localhost:8000/docs")

async def main():
    """Main setup function"""
    print("🚀 Perplexity Sonar Setup")
    print("=" * 30)
    
    # Check environment
    if not check_environment():
        return
    
    # Setup API key
    api_key_configured = setup_api_key()
    
    # Test integration if API key is configured
    if api_key_configured:
        integration_works = await test_integration()
        if not integration_works:
            print("⚠️  Integration test failed, but setup is complete")
    else:
        print("⚠️  Skipping integration test (no API key)")
    
    # Show next steps
    show_next_steps()

if __name__ == "__main__":
    asyncio.run(main())
