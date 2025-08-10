"""
Core scraper functionality
"""

import time
import random
import logging
from typing import List, Dict, Any
from urllib.parse import quote
from datetime import datetime

from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from webdriver_manager.chrome import ChromeDriverManager

from .models import ScrapeResponse, ProductListing
from .config import SUPPORTED_STORES, SCRAPER_CONFIG

logger = logging.getLogger(__name__)

class GroceryScraper:
    """Professional grocery store scraper using Selenium"""
    
    def __init__(self):
        self.driver = None
        self._selenium_available = None
    
    def selenium_available(self) -> bool:
        """Check if Selenium and Chrome are available"""
        if self._selenium_available is not None:
            return self._selenium_available
        
        try:
            # Try to create a driver instance
            driver = self._setup_driver(headless=True)
            if driver:
                driver.quit()
                self._selenium_available = True
            else:
                self._selenium_available = False
        except Exception as e:
            logger.error(f"Selenium not available: {e}")
            self._selenium_available = False
        
        return self._selenium_available
    
    def is_ready(self) -> bool:
        """Check if scraper is ready to use"""
        return self.selenium_available()
    
    def _setup_driver(self, headless: bool = True) -> webdriver.Chrome:
        """Setup Chrome WebDriver with optimal settings"""
        try:
            chrome_options = Options()
            
            if headless:
                chrome_options.add_argument("--headless")
            
            # Essential Chrome options for Railway/container environments
            chrome_options.add_argument("--no-sandbox")
            chrome_options.add_argument("--disable-dev-shm-usage")
            chrome_options.add_argument("--disable-gpu")
            chrome_options.add_argument("--disable-web-security")
            chrome_options.add_argument("--disable-features=VizDisplayCompositor")
            chrome_options.add_argument("--window-size=1920,1080")
            chrome_options.add_argument("--remote-debugging-port=9222")
            chrome_options.add_argument("--disable-extensions")
            chrome_options.add_argument("--disable-plugins")
            chrome_options.add_argument("--disable-images")
            chrome_options.add_argument(f"--user-agent={SCRAPER_CONFIG['user_agent']}")
            
            # Setup service
            service = Service(ChromeDriverManager().install())
            
            # Create driver
            driver = webdriver.Chrome(service=service, options=chrome_options)
            
            # Configure timeouts
            driver.implicitly_wait(SCRAPER_CONFIG['implicit_wait'])
            driver.set_page_load_timeout(SCRAPER_CONFIG['page_load_timeout'])
            
            # Execute script to hide automation
            driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            
            return driver
            
        except Exception as e:
            logger.error(f"Failed to setup Chrome driver: {e}")
            return None
    
    def _extract_product_data(self, element, store_config: Dict) -> Dict[str, Any]:
        """Extract product data from a DOM element"""
        product_data = {}
        
        # Extract title
        title = "Unknown Product"
        for selector in store_config["selectors"]["title"]:
            try:
                title_elem = element.select_one(selector)
                if title_elem and title_elem.get_text(strip=True):
                    title = title_elem.get_text(strip=True)
                    break
            except:
                continue
        
        # Extract price
        price = "$0.00"
        for selector in store_config["selectors"]["price"]:
            try:
                price_elem = element.select_one(selector)
                if price_elem and price_elem.get_text(strip=True):
                    price_text = price_elem.get_text(strip=True)
                    if '$' in price_text or any(char.isdigit() for char in price_text):
                        price = price_text
                        break
            except:
                continue
        
        # Extract image
        image_url = ""
        for selector in store_config["selectors"]["image"]:
            try:
                img_elem = element.select_one(selector)
                if img_elem:
                    image_url = img_elem.get('src') or img_elem.get('data-src') or ""
                    if image_url:
                        break
            except:
                continue
        
        # Extract brand from title
        brand = "Unknown Brand"
        if title:
            # Simple brand extraction logic
            words = title.split()
            if len(words) > 0:
                brand = words[0]
        
        return {
            "title": title,
            "product_name": title,
            "brand": brand,
            "price": price,
            "image_url": image_url,
            "product_url": "",
            "availability": "In Stock",
            "description": title,
            "store_address": "123 Main St",
            "store_city": "Anytown",
            "store_state": "NY",
            "store_zipcode": "12345"
        }
    
    def _is_valid_product(self, product_data: Dict[str, Any]) -> bool:
        """Validate if extracted data represents a real product"""
        title = product_data.get("title", "").lower()
        
        # Filter out navigation elements, ads, etc.
        invalid_keywords = [
            "sort by", "filter", "menu", "navigation", "advertisement",
            "sign in", "cart", "checkout", "search", "category"
        ]
        
        if any(keyword in title for keyword in invalid_keywords):
            return False
        
        # Must have a reasonable title length
        if len(title) < 3 or len(title) > 200:
            return False
        
        return True
    
    def scrape_store(self, query: str, store_id: str, zipcode: str) -> ScrapeResponse:
        """Scrape products from a specific store"""
        
        if store_id not in SUPPORTED_STORES:
            return ScrapeResponse(
                success=False,
                store=store_id,
                query=query,
                zipcode=zipcode,
                result_count=0,
                listings=[],
                error=f"Store {store_id} not supported",
                timestamp=datetime.now()
            )
        
        store_config = SUPPORTED_STORES[store_id]
        
        # Setup driver
        driver = self._setup_driver(headless=SCRAPER_CONFIG['headless'])
        if not driver:
            return ScrapeResponse(
                success=False,
                store=store_id,
                query=query,
                zipcode=zipcode,
                result_count=0,
                listings=[],
                error="Failed to setup browser driver",
                timestamp=datetime.now()
            )
        
        try:
            # Navigate to search page
            search_url = store_config["base_url"].format(query=quote(query), zipcode=zipcode)
            logger.info(f"🌐 Navigating to: {search_url}")
            
            driver.get(search_url)
            time.sleep(3)  # Wait for page load
            
            # Handle cookie banners
            self._handle_cookie_banner(driver)
            
            # Scroll to load more content
            self._scroll_page(driver)
            
            # Get page source and parse
            html = driver.page_source
            soup = BeautifulSoup(html, 'html.parser')
            
            # Try different product selectors
            products = []
            for selector in store_config["selectors"]["products"]:
                try:
                    found_products = soup.select(selector)
                    if found_products:
                        logger.info(f"✅ Found {len(found_products)} products using selector: {selector}")
                        products = found_products
                        break
                except Exception as e:
                    logger.warning(f"Selector {selector} failed: {e}")
                    continue
            
            if not products:
                return ScrapeResponse(
                    success=False,
                    store=store_id,
                    query=query,
                    zipcode=zipcode,
                    result_count=0,
                    listings=[],
                    error="No products found with any selector",
                    timestamp=datetime.now()
                )
            
            # Extract product data
            listings = []
            for product_elem in products[:20]:  # Limit to first 20 products
                try:
                    product_data = self._extract_product_data(product_elem, store_config)
                    
                    if self._is_valid_product(product_data):
                        # Add store-specific data
                        product_data["store_zipcode"] = zipcode
                        product_data["product_url"] = search_url
                        
                        listing = ProductListing(**product_data)
                        listings.append(listing)
                        
                        logger.info(f"📦 Extracted: {product_data['title'][:50]}... - {product_data['price']}")
                    
                except Exception as e:
                    logger.warning(f"Failed to extract product data: {e}")
                    continue
            
            logger.info(f"✅ Successfully extracted {len(listings)} products")
            
            return ScrapeResponse(
                success=True,
                store=store_id,
                query=query,
                zipcode=zipcode,
                result_count=len(listings),
                listings=listings,
                timestamp=datetime.now()
            )
            
        except Exception as e:
            logger.error(f"❌ Scraping error: {e}")
            return ScrapeResponse(
                success=False,
                store=store_id,
                query=query,
                zipcode=zipcode,
                result_count=0,
                listings=[],
                error=str(e),
                timestamp=datetime.now()
            )
        
        finally:
            if driver:
                driver.quit()
    
    def _handle_cookie_banner(self, driver):
        """Handle cookie consent banners"""
        cookie_selectors = [
            "button[id*='accept']",
            "button[class*='accept']",
            "[data-testid*='accept']",
            "button:contains('Accept')",
            "button:contains('OK')"
        ]
        
        for selector in cookie_selectors:
            try:
                element = WebDriverWait(driver, 2).until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, selector))
                )
                element.click()
                logger.info("✅ Accepted cookies")
                time.sleep(1)
                break
            except:
                continue
    
    def _scroll_page(self, driver):
        """Scroll page to load dynamic content"""
        try:
            # Scroll down in increments
            for i in range(3):
                driver.execute_script(f"window.scrollTo(0, {(i+1) * 500});")
                time.sleep(1)
            
            # Scroll back to top
            driver.execute_script("window.scrollTo(0, 0);")
            time.sleep(1)
            
        except Exception as e:
            logger.warning(f"Scrolling failed: {e}")
