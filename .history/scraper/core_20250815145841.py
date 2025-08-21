"""
Enhanced core scraper functionality with LLM integration
"""

import time
import random
import logging
import os
import json
import re
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

# User agents for anti-detection
USER_AGENTS = [
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.3 Safari/605.1.15"
]

class GroceryScraper:
    """Enhanced grocery store scraper with LLM integration"""
    
    def __init__(self):
        self.driver = None
        self._selenium_available = None
    
    def selenium_available(self) -> bool:
        """Check if Selenium and Chrome are available"""
        if self._selenium_available is not None:
            return self._selenium_available
        
        try:
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
        """Setup Chrome WebDriver with stealth and anti-detection"""
        try:
            options = Options()
            user_agent = random.choice(USER_AGENTS)
            options.add_argument(f"user-agent={user_agent}")
            
            if headless:
                options.add_argument("--headless=new")
            
            # Enhanced anti-detection options
            options.add_argument("--no-sandbox")
            options.add_argument("--disable-dev-shm-usage")
            options.add_argument("--disable-gpu")
            options.add_argument("--disable-blink-features=AutomationControlled")
            options.add_experimental_option("excludeSwitches", ["enable-automation"])
            options.add_experimental_option('useAutomationExtension', False)
            options.add_argument("--disable-extensions")
            options.add_argument("--disable-plugins-discovery")
            options.add_argument("--disable-web-security")
            options.add_argument("--window-size=1920,1080")
            
            # Setup service
            chromedriver_path = os.environ.get('CHROMEDRIVER_PATH', '/usr/local/bin/chromedriver')
            if os.path.exists(chromedriver_path):
                service = Service(chromedriver_path)
            else:
                # Fix webdriver-manager bug that returns wrong file path
                chromedriver_path = ChromeDriverManager().install()
                if "THIRD_PARTY_NOTICES" in chromedriver_path:
                    chromedriver_path = chromedriver_path.replace("THIRD_PARTY_NOTICES.chromedriver", "chromedriver")
                
                # Ensure the chromedriver is executable
                if os.path.exists(chromedriver_path) and not os.access(chromedriver_path, os.X_OK):
                    os.chmod(chromedriver_path, 0o755)
                
                service = Service(chromedriver_path)
            
            driver = webdriver.Chrome(service=service, options=options)
            
            # Configure timeouts
            driver.implicitly_wait(SCRAPER_CONFIG['implicit_wait'])
            driver.set_page_load_timeout(SCRAPER_CONFIG['page_load_timeout'])
            
            # Apply stealth techniques if available
            try:
                from selenium_stealth import stealth
                stealth(driver,
                        languages=["en-US", "en"],
                        vendor="Google Inc.",
                        platform="MacIntel",
                        webgl_vendor="Intel Inc.",
                        renderer="Intel Iris OpenGL Engine",
                        fix_hairline=True)
                logger.info("✅ Applied stealth techniques")
            except ImportError:
                logger.warning("⚠️ selenium-stealth not available, using basic setup")
            except Exception as e:
                logger.warning(f"⚠️ Error applying stealth: {e}")
            
            # Execute script to hide automation
            driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            
            return driver
            
        except Exception as e:
            logger.error(f"Failed to setup Chrome driver: {e}")
            return None
    
    def _extract_with_llm(self, html: str, query: str, store_id: str, zipcode: str) -> List[Dict]:
        """Extract products using LLM (Groq API)"""
        try:
            # Import LLM dependencies
            import html2text
            from groq import Groq
            
            logger.info("🤖 Using LLM to extract product data...")
            
            # Convert HTML to markdown
            converter = html2text.HTML2Text()
            converter.ignore_links = False
            converter.ignore_images = True
            markdown = converter.handle(html)
            
            # Trim to token limit (rough estimate: 4 chars = 1 token)
            max_chars = 8000
            if len(markdown) > max_chars:
                markdown = markdown[:max_chars]
                logger.info(f"⚠️ Trimmed markdown to {max_chars} characters")
            
            # Setup Groq client
            api_key = os.environ.get("GROQ_API_KEY")
            if not api_key:
                logger.error("❌ No GROQ_API_KEY environment variable found")
                return []
            
            client = Groq(api_key=api_key)
            
            # Create system message
            system_message = f"""You are extracting grocery products from a {store_id} store webpage.
Search query: "{query}"
Store zipcode: {zipcode}

Extract ONLY actual {query} products from the page content. Return a JSON object with this EXACT format:

{{
  "listings": [
    {{
      "title": "Full product name",
      "product_name": "Full product name",
      "brand": "Brand name",
      "price": "$X.XX",
      "image_url": "https://image-url-if-found",
      "availability": "In Stock",
      "description": "Product description"
    }}
  ]
}}

Rules:
- Only include products that match the search query "{query}"
- Extract real prices (like $3.99, $2.49), never use $0.00
- If no price is visible, use "Price not available"
- Include brand names when visible
- Return valid JSON only, no extra text"""

            # Make API call
            completion = client.chat.completions.create(
                messages=[
                    {"role": "system", "content": system_message},
                    {"role": "user", "content": markdown}
                ],
                model="llama3-8b-8192",
                temperature=0.1
            )
            
            response = completion.choices[0].message.content
            logger.info("✅ Received LLM response")
            
            # Clean and parse JSON response
            response = self._clean_json_response(response)
            parsed = json.loads(response)
            
            products = parsed.get("listings", [])
            logger.info(f"✅ LLM extracted {len(products)} products")
            
            return products
            
        except ImportError as e:
            logger.error(f"❌ Missing LLM dependencies: {e}")
            return []
        except json.JSONDecodeError as e:
            logger.error(f"❌ Failed to parse LLM JSON response: {e}")
            return []
        except Exception as e:
            logger.error(f"❌ LLM extraction failed: {e}")
            return []
    
    def _clean_json_response(self, response: str) -> str:
        """Clean up common JSON formatting issues in LLM responses"""
        # Extract JSON from markdown code blocks if present
        json_match = re.search(r'(?:json)?\s*(\{.*\})\s*', response, re.DOTALL)
        if json_match:
            response = json_match.group(1)
        
        # Fix trailing commas
        response = re.sub(r',\s*}', '}', response)
        response = re.sub(r',\s*]', ']', response)
        
        # Fix missing quotes around keys (basic cases)
        response = re.sub(r'([{,]\s*)(\w+)(\s*:)', r'\1"\2"\3', response)
        
        return response.strip()
    
    def _extract_products_traditional(self, soup: BeautifulSoup, store_config: Dict) -> List[Dict]:
        """Traditional CSS selector-based extraction"""
        products = []
        
        # Try different product selectors
        for selector in store_config["selectors"]["products"]:
            try:
                elements = soup.select(selector)
                if elements:
                    logger.info(f"✅ Found {len(elements)} products with selector: {selector}")
                    
                    for element in elements[:20]:  # Limit to first 20
                        product_data = self._extract_product_data(element, store_config)
                        if self._is_valid_product(product_data):
                            products.append(product_data)
                    
                    if products:
                        break
                        
            except Exception as e:
                logger.warning(f"Selector {selector} failed: {e}")
                continue
        
        return products
    
    def _extract_product_data(self, element, store_config: Dict) -> Dict[str, Any]:
        """Extract product data from a DOM element using CSS selectors"""
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
        price = "Price not available"
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
            "description": title
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
        """Enhanced scrape with LLM fallback"""
        
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
            time.sleep(3)
            
            # Handle cookie banners
            self._handle_cookie_banner(driver)
            
            # Scroll to load more content
            self._scroll_page(driver)
            
            # Get page source and parse
            html = driver.page_source
            soup = BeautifulSoup(html, 'html.parser')
            
            # Try traditional extraction first
            logger.info("🔍 Trying traditional CSS selector extraction...")
            products = self._extract_products_traditional(soup, store_config)
            
            # If traditional extraction fails or finds few products, use LLM
            if len(products) < 3:
                logger.info("🤖 Traditional extraction found few products, trying LLM...")
                llm_products = self._extract_with_llm(html, query, store_id, zipcode)
                
                # Use LLM results if they're better
                if len(llm_products) > len(products):
                    products = llm_products
                    logger.info(f"✅ Using LLM results: {len(llm_products)} products")
            
            if not products:
                return ScrapeResponse(
                    success=False,
                    store=store_id,
                    query=query,
                    zipcode=zipcode,
                    result_count=0,
                    listings=[],
                    error="No products found with any extraction method",
                    timestamp=datetime.now()
                )
            
            # Convert to ProductListing objects
            listings = []
            for product_data in products:
                try:
                    # Ensure required fields
                    product_data.setdefault("store_zipcode", zipcode)
                    product_data.setdefault("product_url", search_url)
                    product_data.setdefault("store_address", "123 Main St")
                    product_data.setdefault("store_city", "Anytown")
                    product_data.setdefault("store_state", "NY")
                    
                    listing = ProductListing(**product_data)
                    listings.append(listing)
                    
                    logger.info(f"📦 Added: {product_data.get('title', 'Unknown')[:50]}... - {product_data.get('price', 'No price')}")
                    
                except Exception as e:
                    logger.warning(f"Failed to parse product data: {e}")
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
            for i in range(3):
                driver.execute_script(f"window.scrollTo(0, {(i+1) * 500});")
                time.sleep(1)
            
            driver.execute_script("window.scrollTo(0, 0);")
            time.sleep(1)
            
        except Exception as e:
            logger.warning(f"Scrolling failed: {e}")

