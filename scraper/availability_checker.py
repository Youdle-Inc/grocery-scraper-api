"""
Enhanced Availability Checker
Fetches availability directly from product pages using multiple methods
"""

import asyncio
import logging
import re
import aiohttp
from typing import Dict, List, Optional
from bs4 import BeautifulSoup
from scraper.serper_client import SerperClient
from scraper.ai_scraper import AIScraper

logger = logging.getLogger(__name__)

class AvailabilityChecker:
    """Check product availability by fetching product pages with multiple methods"""
    
    def __init__(self, serper_client: SerperClient):
        self.serper_client = serper_client
        self.ai_scraper = AIScraper()
    
    async def check_availability_batch(
        self,
        product_urls: List[str],
        max_concurrent: int = 5
    ) -> Dict[str, str]:
        """
        Check availability for multiple products in parallel using multiple methods
        
        Returns:
            Dict mapping product_url -> availability status
        """
        if not self.serper_client.is_available():
            return {}
        
        results = {}
        
        # Process in batches to avoid overwhelming the API
        for i in range(0, len(product_urls), max_concurrent):
            batch = product_urls[i:i + max_concurrent]
            tasks = [self._check_single_availability(url) for url in batch]
            batch_results = await asyncio.gather(*tasks, return_exceptions=True)
            
            for url, result in zip(batch, batch_results):
                if isinstance(result, Exception):
                    logger.warning(f"⚠️ Failed to check availability for {url}: {result}")
                    results[url] = "CHECK_STORE"
                else:
                    results[url] = result
        
        return results
    
    def _is_product_url(self, url: str) -> bool:
        """Check if URL is from a known grocery store domain"""
        if not url:
            return False
        
        url_lower = url.lower()
        
        # Only allow URLs from known grocery store domains
        allowed_domains = [
            'target.com',
            'walmart.com',
            'kroger.com',
            'costco.com',
            'albertsons.com',
            'safeway.com',
            'publix.com',
            'heb.com',
            'aldi.us',
            'samsclub.com',
            'wholefoodsmarket.com',
            'meijer.com',
            'wincofoods.com',
            'bjs.com',
            'dollargeneral.com',
            'dollartree.com',
            'traderjoes.com',
            'hy-vee.com',
            'wegmans.com',
            'sprouts.com',
            'gianteagle.com',
            'amazon.com',  # Amazon Fresh
            'amazon.com/alm',  # Amazon Fresh category
            'origin-d8.wholefoodsmarket.com',  # Whole Foods product pages
        ]
        
        # Check if URL is from an allowed grocery store domain
        is_grocery_store = False
        for domain in allowed_domains:
            if domain in url_lower:
                is_grocery_store = True
                break
        
        if not is_grocery_store:
            return False
        
        # Skip non-product pages (category pages, search pages, etc.)
        skip_patterns = [
            '/c/',  # Category pages
            '/browse/',
            '/q/',  # Query/search pages
            '/search',
            '/search?',
            '/tp/',  # Topic pages
            '/blog/',
            '/article/',
            '/store-locator',
            '/find-stores',
            '/locations',
            '/sl/',  # Store locator
        ]
        
        # Allow /ip/ if it looks like a product ID (has numbers)
        if '/ip/' in url_lower:
            # Check if it has a product ID pattern (numbers after /ip/)
            if re.search(r'/ip/[^/]+/\d+', url_lower):
                return True  # This is a product page
            return False  # This is a category/topic page
        
        # Skip if it matches any skip pattern
        for pattern in skip_patterns:
            if pattern in url_lower:
                return False
        
        # Must have product indicators
        product_indicators = [
            '/p/',  # Product pages
            '/product',
            '/item',
            '/ip/',  # Item/product pages
            '?id=',
            '/dp/',  # Amazon product pages
            '/gp/product',
        ]
        
        has_product_indicator = any(indicator in url_lower for indicator in product_indicators)
        
        return has_product_indicator
    
    async def _check_single_availability(self, product_url: str) -> str:
        """Check availability for a single product URL using multiple methods"""
        if not product_url:
            return "CHECK_STORE"
        
        # Skip non-product URLs (YouTube, Reddit, blogs, etc.)
        if not self._is_product_url(product_url):
            logger.debug(f"⏭️ Skipping non-product URL: {product_url[:80]}...")
            return "CHECK_STORE"
        
        logger.info(f"🔍 Checking availability for: {product_url[:80]}...")
        
        # Method 1: Try HTML scraping first (most reliable for button detection)
        try:
            availability = await self._check_with_html(product_url)
            if availability != "CHECK_STORE":
                logger.info(f"✅ HTML found availability: {availability}")
                return availability
        except Exception as e:
            logger.debug(f"HTML availability check failed: {e}")
        
        # Method 2: Instacart products already include availability, so skip Exa check
        # Instacart provides real-time availability data
        
        # Method 3: Try AI scraper
        try:
            availability = await self._check_with_ai_scraper(product_url)
            if availability != "CHECK_STORE":
                logger.info(f"✅ AI scraper found availability: {availability}")
                return availability
        except Exception as e:
            logger.debug(f"AI scraper availability check failed: {e}")
        
        logger.warning(f"⚠️ Could not determine availability for: {product_url[:80]}...")
        return "CHECK_STORE"
    
    async def _check_with_html(self, product_url: str) -> str:
        """Check availability by scraping HTML directly for stock indicators"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    product_url,
                    timeout=aiohttp.ClientTimeout(total=10),
                    headers={
                        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                        "Accept-Language": "en-US,en;q=0.9"
                    }
                ) as response:
                    if response.status != 200:
                        return "CHECK_STORE"
                    
                    html = await response.text()
                    soup = BeautifulSoup(html, 'html.parser')
                    html_lower = html.lower()
                    
                    # Method 1: Check for out of stock indicators in text
                    out_of_stock_indicators = [
                        'out of stock',
                        'sold out',
                        'unavailable',
                        'not available',
                        'currently unavailable',
                        'temporarily unavailable',
                        'no longer available',
                        'outofstock',
                        'oos',
                        'stock: 0',
                        'inventory: 0',
                        'not in stock',
                        'unavailable for',
                        'discontinued'
                    ]
                    
                    for indicator in out_of_stock_indicators:
                        if indicator in html_lower:
                            # Check if it's not in a comment or script tag
                            text_content = soup.get_text().lower()
                            if indicator in text_content:
                                return "OUT_OF_STOCK"
                    
                    # Method 2: Look for "Add to Cart" buttons (strongest indicator of in stock)
                    add_to_cart_selectors = [
                        'button[data-test*="add-to-cart"]',
                        'button[data-test*="addToCart"]',
                        'button[aria-label*="add to cart" i]',
                        'button:-soup-contains("Add to Cart")',
                        'button:-soup-contains("Add to Bag")',
                        'button:-soup-contains("Buy Now")',
                        'a[data-test*="add-to-cart"]',
                        '[class*="add-to-cart"]',
                        '[class*="addToCart"]',
                        '[id*="add-to-cart"]',
                        '[id*="addToCart"]'
                    ]
                    
                    for selector in add_to_cart_selectors:
                        try:
                            elements = soup.select(selector)
                            for element in elements:
                                # Check if button is not disabled
                                if element.get('disabled') is None and 'disabled' not in str(element.get('class', [])).lower():
                                    text = element.get_text().lower()
                                    if any(word in text for word in ['add', 'cart', 'bag', 'buy', 'purchase']):
                                        return "IN_STOCK"
                        except:
                            continue
                    
                    # Method 3: Look for button text directly
                    buttons = soup.find_all(['button', 'a', 'span'], string=re.compile(r'add to cart|add to bag|buy now|purchase', re.I))
                    for button in buttons:
                        if button.get('disabled') is None:
                            return "IN_STOCK"
                    
                    # Method 4: Check for in stock text indicators
                    in_stock_text_patterns = [
                        r'in stock',
                        r'available now',
                        r'available for',
                        r'ready to ship',
                        r'ships in',
                        r'add to cart',
                        r'add to bag'
                    ]
                    
                    page_text = soup.get_text().lower()
                    for pattern in in_stock_text_patterns:
                        if re.search(pattern, page_text):
                            # Make sure it's not in a disabled context
                            if 'out of stock' not in page_text and 'unavailable' not in page_text:
                                return "IN_STOCK"
                    
                    # Method 5: Check for low stock indicators
                    low_stock_indicators = [
                        'low stock',
                        'limited availability',
                        'few left',
                        'only a few',
                        'running low',
                        'limited quantity'
                    ]
                    
                    for indicator in low_stock_indicators:
                        if indicator in page_text:
                            return "LOW_STOCK"
                    
                    # Method 6: Store-specific checks
                    if 'target.com' in product_url.lower():
                        # Target-specific: Check for "Pick it up" or "Ship it" buttons
                        if 'pick it up' in html_lower or 'ship it' in html_lower:
                            return "IN_STOCK"
                        # Check for Target's out of stock class
                        if soup.find(class_=re.compile(r'out.*stock|unavailable', re.I)):
                            return "OUT_OF_STOCK"
                    
                    elif 'walmart.com' in product_url.lower():
                        # Walmart-specific: Check for "Add to cart" button
                        add_buttons = soup.find_all(['button', 'a'], string=re.compile(r'add to cart', re.I))
                        if add_buttons:
                            return "IN_STOCK"
                        # Check for out of stock message
                        if soup.find(string=re.compile(r'out of stock|unavailable', re.I)):
                            return "OUT_OF_STOCK"
        
        except Exception as e:
            logger.debug(f"HTML availability check failed for {product_url}: {e}")
        
        return "CHECK_STORE"
    
    async def _check_with_ai_scraper(self, product_url: str) -> str:
        """Check availability using AI scraper"""
        try:
            # Use AI scraper to extract availability
            result = await self.ai_scraper.scrape_product_page(product_url)
            if result and result.get("availability"):
                availability_text = result["availability"]
                return self.serper_client.parse_availability(availability_text)
        except Exception as e:
            logger.debug(f"AI scraper availability check failed: {e}")
        
        return "CHECK_STORE"

