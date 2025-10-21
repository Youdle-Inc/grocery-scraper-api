#!/usr/bin/env python3
"""
Simple test runner for the grocery scraper API
"""

import subprocess
import sys
import time
import requests

def check_api_running():
    """Check if the API is running"""
    try:
        response = requests.get("http://localhost:8000/health", timeout=5)
        return response.status_code == 200
    except:
        return False

def start_api():
    """Start the API in the background"""
    print("🚀 Starting Grocery Scraper API...")
    try:
        # Start the API in the background
        process = subprocess.Popen([
            sys.executable, "main.py"
        ], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        
        # Wait a moment for the API to start
        time.sleep(3)
        
        # Check if it's running
        if check_api_running():
            print("✅ API started successfully!")
            return process
        else:
            print("❌ API failed to start")
            return None
    except Exception as e:
        print(f"❌ Error starting API: {e}")
        return None

def run_tests():
    """Run all the test examples"""
    
    print("🧪 Running Grocery Scraper API Tests")
    print("=" * 50)
    
    # Check if API is already running
    if check_api_running():
        print("✅ API is already running!")
        api_process = None
    else:
        # Start the API
        api_process = start_api()
        if not api_process:
            print("❌ Could not start API. Please start it manually:")
            print("   python main.py")
            return
    
    try:
        print("\n🧠 Testing Prompt Detection...")
        subprocess.run([sys.executable, "quick_test.py"], check=True)
        
        print("\n📊 Testing API Endpoints...")
        subprocess.run([sys.executable, "test_examples.py"], check=True)
        
        print("\n🔍 Testing with Curl...")
        subprocess.run(["./curl_examples.sh"], check=True)
        
        print("\n🎉 All tests completed successfully!")
        
    except subprocess.CalledProcessError as e:
        print(f"❌ Test failed: {e}")
    except KeyboardInterrupt:
        print("\n⏹️ Tests interrupted by user")
    finally:
        # Clean up
        if api_process:
            print("\n🛑 Stopping API...")
            api_process.terminate()
            api_process.wait()

if __name__ == "__main__":
    run_tests()
