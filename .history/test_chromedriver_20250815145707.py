#!/usr/bin/env python3
"""
Test ChromeDriver setup
"""

import os
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

def test_chromedriver():
    """Test ChromeDriver setup"""
    try:
        print("Testing ChromeDriver setup...")
        
        # Setup Chrome options
        options = Options()
        options.add_argument("--headless=new")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        
        # Try using ChromeDriverManager
        print("Installing ChromeDriver...")
        chromedriver_path = ChromeDriverManager().install()
        print(f"ChromeDriver path: {chromedriver_path}")
        
        # Fix the path if it's pointing to the wrong file
        if "THIRD_PARTY_NOTICES" in chromedriver_path:
            # Replace with the correct chromedriver path
            correct_path = chromedriver_path.replace("THIRD_PARTY_NOTICES.chromedriver", "chromedriver")
            print(f"Fixing path to: {correct_path}")
            chromedriver_path = correct_path
        
        # Check if the file exists and is executable
        if os.path.exists(chromedriver_path):
            print(f"✅ ChromeDriver exists at: {chromedriver_path}")
            if os.access(chromedriver_path, os.X_OK):
                print("✅ ChromeDriver is executable")
            else:
                print("❌ ChromeDriver is not executable")
                # Make it executable
                os.chmod(chromedriver_path, 0o755)
                print("✅ Made ChromeDriver executable")
        else:
            print(f"❌ ChromeDriver not found at: {chromedriver_path}")
            return False
        
        # Setup service
        service = Service(chromedriver_path)
        
        # Create driver
        print("Creating Chrome driver...")
        driver = webdriver.Chrome(service=service, options=options)
        
        # Test basic functionality
        print("Testing basic functionality...")
        driver.get("https://www.google.com")
        title = driver.title
        print(f"✅ Successfully loaded page: {title}")
        
        # Clean up
        driver.quit()
        print("✅ ChromeDriver test successful!")
        return True
        
    except Exception as e:
        print(f"❌ ChromeDriver test failed: {e}")
        return False

if __name__ == "__main__":
    test_chromedriver()
