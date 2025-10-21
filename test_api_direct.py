#!/usr/bin/env python3
"""
Test the API directly to see what's happening with the health endpoint
"""

import asyncio
import os
from dotenv import load_dotenv
from fastapi import FastAPI
from scraper.exa_structured_client import ExaStructuredClient

# Load environment variables
load_dotenv()

# Create a simple FastAPI app
app = FastAPI()

# Initialize the client (like in main.py)
exa_client = ExaStructuredClient()

@app.get("/test-health")
async def test_health():
    """Test health endpoint logic"""
    print(f"🔍 Test - exa_client: {exa_client}")
    print(f"🔍 Test - exa_client._client: {exa_client._client}")
    print(f"🔍 Test - exa_client.api_key: {bool(exa_client.api_key)}")
    print(f"🔍 Test - exa_client.is_available(): {exa_client.is_available()}")
    
    exa_status = "available" if exa_client.is_available() else "unavailable"
    
    return {
        "exa_client_object": str(exa_client),
        "exa_client_client": str(exa_client._client),
        "exa_client_api_key": bool(exa_client.api_key),
        "exa_client_available": exa_client.is_available(),
        "exa_status": exa_status
    }

if __name__ == "__main__":
    import uvicorn
    print("🚀 Starting test API...")
    print(f"🔍 Initial client status: {exa_client.is_available()}")
    uvicorn.run(app, host="0.0.0.0", port=8001)
