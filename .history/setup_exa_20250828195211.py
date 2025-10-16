#!/usr/bin/env python3
"""
Setup script for Exa API integration
"""

import os
import sys
from dotenv import load_dotenv

def setup_exa_api():
    """Setup Exa API key in .env file"""
    
    print("🔧 Setting up Exa API integration...")
    print()
    
    # Check if .env file exists
    if not os.path.exists('.env'):
        print("❌ No .env file found. Please create one first.")
        print("   You can copy from .env.example if available.")
        return False
    
    # Load existing .env
    load_dotenv()
    
    # Check if EXA_API_KEY already exists
    existing_key = os.getenv('EXA_API_KEY')
    if existing_key:
        print(f"✅ EXA_API_KEY already configured: {existing_key[:8]}...")
        response = input("Do you want to update it? (y/N): ").strip().lower()
        if response != 'y':
            print("Keeping existing key.")
            return True
    
    print()
    print("📋 Exa API Setup Instructions:")
    print("1. Visit https://exa.ai and create an account")
    print("2. Go to your API dashboard")
    print("3. Generate a new API key")
    print("4. Copy the API key")
    print()
    
    # Get API key from user
    api_key = input("Enter your Exa API key: ").strip()
    
    if not api_key:
        print("❌ No API key provided. Setup cancelled.")
        return False
    
    # Validate API key format (basic check)
    if len(api_key) < 10:
        print("❌ API key seems too short. Please check and try again.")
        return False
    
    # Update .env file
    try:
        # Read existing .env content
        with open('.env', 'r') as f:
            lines = f.readlines()
        
        # Check if EXA_API_KEY already exists in file
        key_exists = False
        for i, line in enumerate(lines):
            if line.startswith('EXA_API_KEY='):
                lines[i] = f'EXA_API_KEY={api_key}\n'
                key_exists = True
                break
        
        # Add new key if it doesn't exist
        if not key_exists:
            lines.append(f'EXA_API_KEY={api_key}\n')
        
        # Write back to .env
        with open('.env', 'w') as f:
            f.writelines(lines)
        
        print("✅ EXA_API_KEY successfully added to .env file!")
        print()
        print("🚀 You can now use Exa API integration in your grocery scraper!")
        print()
        print("📝 Next steps:")
        print("1. Test the integration: python -c \"from scraper.exa_client import ExaClient; print('Exa client available:', ExaClient().is_available())\"")
        print("2. Run your API: python main.py")
        print("3. Test an endpoint: curl 'http://localhost:8000/health'")
        
        return True
        
    except Exception as e:
        print(f"❌ Error updating .env file: {e}")
        return False

def test_exa_integration():
    """Test Exa API integration"""
    print("🧪 Testing Exa API integration...")
    
    try:
        from scraper.exa_client import ExaClient
        
        client = ExaClient()
        
        if client.is_available():
            print("✅ Exa client is available and configured!")
            print(f"   API Key: {client.api_key[:8]}...")
            return True
        else:
            print("❌ Exa client is not available.")
            print("   Please check your EXA_API_KEY in .env file.")
            return False
            
    except ImportError as e:
        print(f"❌ Import error: {e}")
        return False
    except Exception as e:
        print(f"❌ Test error: {e}")
        return False

if __name__ == "__main__":
    print("=" * 50)
    print("🔍 Exa API Setup for Grocery Scraper")
    print("=" * 50)
    print()
    
    if len(sys.argv) > 1 and sys.argv[1] == "test":
        success = test_exa_integration()
        sys.exit(0 if success else 1)
    
    success = setup_exa_api()
    if success:
        print()
        print("🎉 Setup completed successfully!")
    else:
        print()
        print("❌ Setup failed. Please try again.")
        sys.exit(1)
