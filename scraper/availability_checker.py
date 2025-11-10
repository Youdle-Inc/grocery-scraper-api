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
from scraper.exa_structured_client import ExaStructuredClient
from scraper.ai_scraper import AIScraper

logger = logging.getLogger(__name__)

class AvailabilityChecker:
    """Check product availability by fetching product pages with multiple methods"""
    
    def __init__(self, exa_client: ExaStructuredClient):
        self.exa_client = exa_client
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
        if not self.exa_client.is_available():
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
    
    async def _check_single_availability(self, product_url: str) -> str:
        """Check availability for a single product URL using multiple methods"""
        if not product_url:
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
        
        # Method 2: Try Exa structured extraction
        try:
            availability = await self._check_with_exa(product_url)
            if availability != "CHECK_STORE":
                logger.info(f"✅ Exa found availability: {availability}")
                return availability
        except Exception as e:
            logger.debug(f"Exa availability check failed: {e}")
        
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
    
    async def _check_with_exa(self, product_url: str) -> str:
        """Check availability using Exa structured extraction"""
        if not hasattr(self.exa_client, '_client') or not self.exa_client._client:
            return "CHECK_STORE"
        
        availability_schema = {
            "type": "object",
            "properties": {
                "availability": {
                    "type": "string",
                    "description": "Exact stock status from page: 'in stock', 'out of stock', 'sold out', 'available', 'unavailable', 'low stock', 'add to cart', 'check store', etc. Look for stock status indicators, add to cart buttons, out of stock messages."
                }
            },
            "required": ["availability"]
        }
        
        response = await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: self.exa_client._client.get_contents(
                [product_url],
                text={"max_characters": 3000},
                summary={
                    "query": "Extract ONLY the product availability/stock status from this page. Look for: 'in stock', 'out of stock', 'sold out', 'available', 'unavailable', 'add to cart' button (means in stock), 'out of stock' message, inventory warnings, stock status indicators. Be very thorough.",
                    "schema": availability_schema
                }
            )
        )
        
        if response and response.results:
            result = response.results[0]
            availability_text = None
            
            # Try structured data first
            if hasattr(result, "structured") and result.structured:
                structured = result.structured
                if isinstance(structured, dict):
                    availability_text = structured.get("availability")
                elif hasattr(structured, "availability"):
                    availability_text = getattr(structured, "availability", None)
            
            # Fall back to text extraction
            if not availability_text:
                text = getattr(result, "text", "")[:2000] if hasattr(result, "text") else ""
                # Look for availability patterns
                patterns = [
                    r'(?:in stock|out of stock|sold out|available|unavailable|low stock)',
                    r'(?:add to cart|add to bag|buy now|purchase)',
                    r'(?:currently unavailable|temporarily unavailable)',
                ]
                for pattern in patterns:
                    match = re.search(pattern, text, re.IGNORECASE)
                    if match:
                        availability_text = match.group(0)
                        break
            
            if availability_text:
                return self.exa_client.parse_availability(availability_text)
        
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
                        'button:contains("Add to Cart")',
                        'button:contains("Add to Bag")',
                        'button:contains("Buy Now")',
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
                return self.exa_client.parse_availability(availability_text)
        except Exception as e:
            logger.debug(f"AI scraper availability check failed: {e}")
        
        return "CHECK_STORE"

