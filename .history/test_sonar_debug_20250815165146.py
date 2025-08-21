#!/usr/bin/env python3
"""
Debug script to test Perplexity Sonar API directly
"""

import asyncio
import os
import requests
import json
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

async def test_sonar_api():
    """Test the Sonar API directly"""
    
    api_key = os.environ.get("PERPLEXITY_API_KEY")
    if not api_key:
        print("❌ No API key found")
        return
    
    print(f"🔑 API Key: {api_key[:10]}...")
    
    # Test different model names
    models_to_test = [
        "sonar-small-online",
        "sonar",
        "llama-3.1-sonar-small-128k-online",
        "sonar-small",
        "sonar-large-online"
    ]
    
    for model in models_to_test:
        print(f"\n🧪 Testing model: {model}")
        
        try:
            url = "https://api.perplexity.ai/chat/completions"
            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            }
            
            data = {
                "model": model,
                "messages": [
                    {
                        "role": "user",
                        "content": "Find grocery stores in zipcode 60622. List them in this format:\n\nSTORE: [Name]\nADDRESS: [Address]\nSERVICES: [services]\nSTATUS: [status]"
                    }
                ],
                "max_tokens": 1024,
                "temperature": 0.1
            }
            
            response = requests.post(url, headers=headers, json=data, timeout=30)
            
            if response.status_code == 200:
                result = response.json()
                content = result["choices"][0]["message"]["content"]
                print(f"✅ Model {model} works!")
                print(f"Response preview: {content[:200]}...")
                break
            else:
                print(f"❌ Model {model} failed: {response.status_code}")
                print(f"Error: {response.text}")
                
        except Exception as e:
            print(f"❌ Model {model} error: {e}")

if __name__ == "__main__":
    asyncio.run(test_sonar_api())
