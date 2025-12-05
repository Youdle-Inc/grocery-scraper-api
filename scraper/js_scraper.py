#!/usr/bin/env python3
"""
Fast AI-Powered JavaScript Scraper

High-performance scraper for JavaScript-rendered grocery sites using:
- Playwright for headless browser automation
- Request blocking for speed (images, fonts, trackers)
- Browser context pooling (no cold starts)
- Smart waiting strategies (selector-based, not timeout-based)
- AI extraction for structured data parsing
- Parallel execution with async semaphores

Optimized for: Costco, Target, Walmart, Kroger, Wegmans, and other JS-heavy sites.
"""

import asyncio
import os
import logging
import json
import re
from typing import Dict, List, Any, Optional, Set
from datetime import datetime
from contextlib import asynccontextmanager
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)


# ============================================================================
# CONFIGURATION
# ============================================================================

# Blocked resource types for faster page loads
BLOCKED_RESOURCE_TYPES = {
    'image',      # Product images loaded separately if needed
    'media',      # Videos, audio
    'font',       # Custom fonts
    'stylesheet', # CSS (can be enabled if needed for layout)
}

# Blocked URL patterns (ads, analytics, tracking)
BLOCKED_URL_PATTERNS = [
    '*google-analytics*',
    '*googletagmanager*',
    '*facebook.net*',
    '*doubleclick*',
    '*adsystem*',
    '*adservice*',
    '*tracking*',
    '*pixel*',
    '*analytics*',
    '*hotjar*',
    '*segment*',
    '*amplitude*',
    '*mixpanel*',
    '*newrelic*',
    '*datadome*',
    '*cloudflare-static*',
    '*.woff*',
    '*.woff2*',
    '*.ttf*',
    '*.otf*',
]

# Store-specific configurations for optimal scraping
STORE_CONFIGS = {
    'costco': {
        'wait_selector': '#productList, [class*="product-list"], [class*="ProductTile"]',
        'product_selector': '[data-testid^="ProductTile_"]',
        'timeout_ms': 20000,  # Costco loads slowly
        'needs_js': True,
        'block_images': False,  # Don't block - Costco detects it
        'protected': True,  # Has bot detection
    },
    'target': {
        'wait_selector': '[data-test="product-grid"], [class*="ProductCard"]',
        'product_selector': '[data-test="product-card"]',
        'timeout_ms': 18000,
        'needs_js': True,
        'block_images': False,  # Target also has detection
        'protected': True,
    },
    'walmart': {
        'wait_selector': '[data-item-id], [class*="search-result"]',
        'product_selector': '[data-item-id]',
        'timeout_ms': 18000,
        'needs_js': True,
        'block_images': False,  # Walmart has strong detection
        'protected': True,
    },
    'kroger': {
        'wait_selector': '[data-testid^="product-card"]',
        'product_selector': '[data-testid^="product-card"]',
        'timeout_ms': 12000,
        'needs_js': True,
        'block_images': True,
        'protected': False,
    },
    'wegmans': {
        'wait_selector': '[data-testid="best-price-container"], .component--product-price',  # Wait for price containers
        'product_selector': '[class*="product-card"]',
        'timeout_ms': 15000,
        'needs_js': True,
        'block_images': True,
        'protected': False,
    },
    'whole_foods': {
        'wait_selector': '[class*="ProductCard"]',
        'product_selector': '[class*="ProductCard"]',
        'timeout_ms': 12000,
        'needs_js': True,
        'block_images': True,
        'protected': False,
    },
    'safeway': {
        'wait_selector': '[class*="product-card"]',
        'product_selector': '[class*="product-card"]',
        'timeout_ms': 12000,
        'needs_js': True,
        'block_images': True,
        'protected': False,
    },
    'default': {
        'wait_selector': 'body',
        'product_selector': '[class*="product"]',
        'timeout_ms': 10000,
        'needs_js': True,
        'block_images': True,
        'protected': False,
    }
}


# ============================================================================
# BROWSER POOL - Reusable browser contexts for speed
# ============================================================================

class BrowserPool:
    """
    Maintains a pool of browser contexts for fast page creation.
    Eliminates cold start overhead by reusing browser instances.
    """
    
    def __init__(self, max_contexts: int = 5):
        self.max_contexts = max_contexts
        self._browser = None
        self._playwright = None
        self._lock = asyncio.Lock()
        self._initialized = False
    
    async def initialize(self, browser_type: str = "chromium"):
        """Initialize browser pool (lazy initialization)"""
        if self._initialized:
            return
        
        async with self._lock:
            if self._initialized:
                return
            
            try:
                from playwright.async_api import async_playwright
                
                self._playwright = await async_playwright().start()
                
                # Launch both browsers for fallback
                # Chromium for most sites, Firefox for heavily protected sites
                self._chromium = await self._playwright.chromium.launch(
                    headless=True,
                    args=[
                        '--disable-blink-features=AutomationControlled',  # Hide automation
                        '--disable-dev-shm-usage',
                        '--disable-setuid-sandbox',
                        '--no-sandbox',
                        '--disable-background-timer-throttling',
                        '--disable-backgrounding-occluded-windows',
                        '--disable-renderer-backgrounding',
                        '--disable-infobars',
                        '--window-size=1920,1080',
                        '--start-maximized',
                        '--disable-features=site-per-process',
                        '--enable-features=NetworkService,NetworkServiceInProcess',
                    ]
                )
                
                # Firefox has different fingerprint - useful for heavily protected sites
                try:
                    self._firefox = await self._playwright.firefox.launch(headless=True)
                except Exception as e:
                    logger.warning(f"Firefox not available: {e}. Run: playwright install firefox")
                    self._firefox = None
                
                self._browser = self._chromium  # Default to Chromium
                self._initialized = True
                logger.info("✅ Browser pool initialized (stealth mode)")
                
            except ImportError:
                logger.error("❌ Playwright not installed. Run: pip install playwright && playwright install chromium")
                raise
            except Exception as e:
                logger.error(f"❌ Failed to initialize browser pool: {e}")
                raise
    
    def use_firefox(self):
        """Switch to Firefox browser (for heavily protected sites)"""
        if self._firefox:
            self._browser = self._firefox
            logger.info("🦊 Switched to Firefox browser")
    
    def use_chromium(self):
        """Switch back to Chromium browser"""
        if self._chromium:
            self._browser = self._chromium
            logger.info("🔷 Switched to Chromium browser")
    
    @asynccontextmanager
    async def get_context(self, block_resources: bool = True, stealth_mode: bool = False):
        """Get a browser context from the pool with stealth settings"""
        await self.initialize()
        
        # Rotate user agents to avoid detection
        user_agents = [
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15',
        ]
        import random
        user_agent = random.choice(user_agents)
        
        # Create new context with stealth settings
        context = await self._browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            user_agent=user_agent,
            java_script_enabled=True,
            ignore_https_errors=True,
            bypass_csp=True,
            locale='en-US',
            timezone_id='America/New_York',
            # Add realistic browser properties
            extra_http_headers={
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.9',
                'Accept-Encoding': 'gzip, deflate, br',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1',
                'Sec-Fetch-Dest': 'document',
                'Sec-Fetch-Mode': 'navigate',
                'Sec-Fetch-Site': 'none',
                'Sec-Fetch-User': '?1',
                'Cache-Control': 'max-age=0',
            }
        )
        
        # Apply playwright-stealth for protected stores
        if stealth_mode:
            try:
                from playwright_stealth import stealth_async
                page = await context.new_page()
                await stealth_async(page)
                await page.close()
            except ImportError:
                pass
        
        # Apply additional stealth scripts
        await context.add_init_script("""
            // Hide webdriver
            Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
            
            // Hide automation
            window.chrome = { runtime: {} };
            
            // Hide plugins length
            Object.defineProperty(navigator, 'plugins', { get: () => [1, 2, 3, 4, 5] });
            
            // Hide languages
            Object.defineProperty(navigator, 'languages', { get: () => ['en-US', 'en'] });
            
            // Permissions
            const originalQuery = window.navigator.permissions.query;
            window.navigator.permissions.query = (parameters) => (
                parameters.name === 'notifications' ?
                    Promise.resolve({ state: Notification.permission }) :
                    originalQuery(parameters)
            );
        """)
        
        # Set up request blocking for speed (but not for protected stores)
        if block_resources:
            await context.route('**/*', self._route_handler)
        
        try:
            yield context
        finally:
            await context.close()
    
    async def _route_handler(self, route):
        """Block unnecessary resources for faster page loads"""
        request = route.request
        
        # Block by resource type
        if request.resource_type in BLOCKED_RESOURCE_TYPES:
            await route.abort()
            return
        
        # Block by URL pattern
        url = request.url.lower()
        for pattern in BLOCKED_URL_PATTERNS:
            # Convert glob pattern to simple contains check
            check_str = pattern.replace('*', '').lower()
            if check_str and check_str in url:
                await route.abort()
                return
        
        # Allow the request
        await route.continue_()
    
    async def close(self):
        """Close the browser pool"""
        if hasattr(self, '_chromium') and self._chromium:
            await self._chromium.close()
        if hasattr(self, '_firefox') and self._firefox:
            await self._firefox.close()
        if self._playwright:
            await self._playwright.stop()
        self._initialized = False
        logger.info("🔒 Browser pool closed")


# Global browser pool instance
_browser_pool: Optional[BrowserPool] = None


async def get_browser_pool() -> BrowserPool:
    """Get or create the global browser pool"""
    global _browser_pool
    if _browser_pool is None:
        _browser_pool = BrowserPool()
    return _browser_pool


# ============================================================================
# FAST JS SCRAPER
# ============================================================================

class FastJSScraper:
    """
    High-performance JavaScript scraper with AI extraction.
    
    Features:
    - Fast page rendering with Playwright
    - Request blocking for speed
    - Browser context reuse
    - Smart waiting strategies
    - AI-powered data extraction
    - Parallel execution support
    """
    
    def __init__(self):
        """Initialize the JS scraper with AI capabilities"""
        self.openai_key = os.getenv("OPENAI_API_KEY")
        self.anthropic_key = os.getenv("ANTHROPIC_API_KEY")
        self.use_anthropic = bool(self.anthropic_key)
        self.use_openai = bool(self.openai_key)
        self._pool = None
        
        if not self.use_openai and not self.use_anthropic:
            logger.warning("⚠️ No LLM API key found. AI extraction will be limited.")
        else:
            llm_provider = "Anthropic" if self.use_anthropic else "OpenAI"
            logger.info(f"✅ Fast JS Scraper initialized with {llm_provider}")
    
    async def __aenter__(self):
        """Async context manager entry"""
        self._pool = await get_browser_pool()
        await self._pool.initialize()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        # Don't close the pool - it's global and reusable
        pass
    
    def _get_store_config(self, url: str) -> Dict[str, Any]:
        """Get store-specific configuration from URL"""
        url_lower = url.lower()
        
        for store_id, config in STORE_CONFIGS.items():
            if store_id != 'default' and store_id in url_lower:
                return {**config, 'store_id': store_id}
        
        return {**STORE_CONFIGS['default'], 'store_id': 'unknown'}
    
    async def scrape_search_page(
        self,
        url: str,
        store_name: Optional[str] = None,
        max_products: int = 20,
        retries: int = 2
    ) -> List[Dict[str, Any]]:
        """
        Scrape a search results page for products.
        
        Args:
            url: Search results page URL
            store_name: Optional store name for context
            max_products: Maximum number of products to extract
            retries: Number of retry attempts on failure
        
        Returns:
            List of product dictionaries
        """
        if not self._pool:
            self._pool = await get_browser_pool()
            await self._pool.initialize()
        
        config = self._get_store_config(url)
        store_id = store_name or config['store_id']
        
        # Special handling for stores with strong bot detection
        is_protected_store = config.get('protected', False)
        
        logger.info(f"🔍 Scraping {store_id} search page: {url[:80]}...")
        
        last_error = None
        for attempt in range(retries + 1):
            try:
                # For protected stores: don't block resources and use stealth mode
                block_resources = config['block_images'] and not is_protected_store
                
                async with self._pool.get_context(
                    block_resources=block_resources,
                    stealth_mode=is_protected_store
                ) as context:
                    page = await context.new_page()
                    
                    try:
                        # For protected stores, use slower but more reliable loading
                        wait_until = 'load' if is_protected_store else 'domcontentloaded'
                        timeout = config['timeout_ms'] * 2 if is_protected_store else config['timeout_ms']
                        
                        # Navigate with retry-appropriate timeout
                        await page.goto(url, wait_until=wait_until, timeout=timeout)
                        
                        # For protected stores, add a small random delay (anti-bot)
                        if is_protected_store:
                            import random
                            await asyncio.sleep(random.uniform(1.0, 2.0))
                        
                        # Smart wait for product selector
                        try:
                            await page.wait_for_selector(
                                config['wait_selector'],
                                timeout=config['timeout_ms'],
                                state='visible'
                            )
                            # Longer delay for JS hydration on complex pages
                            await asyncio.sleep(2.0 if is_protected_store else 1.5)
                        except Exception as e:
                            logger.warning(f"⏱️ Selector wait timeout for {config['wait_selector']}: {e}")
                            # Still wait a bit for any content
                            await asyncio.sleep(2.0)
                        
                        # Get rendered HTML
                        html = await page.content()
                        
                        # Extract products using store-specific extractor
                        products = await self._extract_products_from_html(
                            html, store_id, url, max_products
                        )
                        
                        logger.info(f"✅ Extracted {len(products)} products from {store_id}")
                        return products
                        
                    finally:
                        await page.close()
                        
            except Exception as e:
                last_error = e
                error_str = str(e).lower()
                
                # Retry on network errors
                if any(x in error_str for x in ['err_http2', 'timeout', 'net::', 'connection']):
                    if attempt < retries:
                        wait_time = (attempt + 1) * 2  # Exponential backoff
                        logger.warning(f"⚠️ Attempt {attempt + 1} failed, retrying in {wait_time}s: {e}")
                        
                        # Try Firefox for HTTP2 errors (better against bot detection)
                        if 'err_http2' in error_str and hasattr(self._pool, '_firefox') and self._pool._firefox:
                            logger.info("🦊 Switching to Firefox for retry...")
                            self._pool.use_firefox()
                        
                        await asyncio.sleep(wait_time)
                        continue
                
                logger.error(f"❌ Failed to scrape {url}: {e}")
                break
        
        # Reset to Chromium for next scrape
        if hasattr(self._pool, 'use_chromium'):
            self._pool.use_chromium()
        
        logger.error(f"❌ All {retries + 1} attempts failed for {url}")
        return []
    
    async def scrape_product_page(
        self,
        url: str,
        store_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Scrape a single product page for detailed information.
        
        Args:
            url: Product page URL
            store_name: Optional store name for context
        
        Returns:
            Product dictionary with extracted data
        """
        if not self._pool:
            self._pool = await get_browser_pool()
            await self._pool.initialize()
        
        config = self._get_store_config(url)
        store_id = store_name or config['store_id']
        
        logger.debug(f"📦 Scraping {store_id} product page: {url[:80]}...")
        
        try:
            async with self._pool.get_context(block_resources=True) as context:
                page = await context.new_page()
                
                try:
                    # Navigate with domcontentloaded (faster than networkidle)
                    await page.goto(url, wait_until='domcontentloaded', timeout=config['timeout_ms'])
                    
                    # Wait for price element (key indicator page is ready)
                    try:
                        await page.wait_for_selector(
                            '[class*="price"], [data-test*="price"], [data-testid*="price"]',
                            timeout=8000,
                            state='visible'
                        )
                    except:
                        pass  # Continue even if price selector not found
                    
                    # Get rendered HTML
                    html = await page.content()
                    
                    # Use AI to extract structured data
                    product = await self._extract_product_with_ai(html, url, store_id)
                    
                    return product
                    
                finally:
                    await page.close()
                    
        except Exception as e:
            logger.error(f"❌ Failed to scrape product page {url}: {e}")
            return {}
    
    async def scrape_multiple_urls(
        self,
        urls: List[str],
        store_name: Optional[str] = None,
        max_concurrent: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Scrape multiple URLs concurrently with rate limiting.
        
        Args:
            urls: List of URLs to scrape
            store_name: Optional store name
            max_concurrent: Maximum concurrent requests
        
        Returns:
            List of product dictionaries
        """
        if not urls:
            return []
        
        semaphore = asyncio.Semaphore(max_concurrent)
        
        async def scrape_with_limit(url: str) -> Dict[str, Any]:
            async with semaphore:
                # Detect if it's a search page or product page
                if any(x in url.lower() for x in ['/s?', '/search', 'keyword=', 'query=', '/shop/search']):
                    results = await self.scrape_search_page(url, store_name)
                    return {'url': url, 'products': results}
                else:
                    result = await self.scrape_product_page(url, store_name)
                    return {'url': url, 'product': result}
        
        results = await asyncio.gather(*[scrape_with_limit(url) for url in urls])
        return list(results)
    
    async def _extract_products_from_html(
        self,
        html: str,
        store_id: str,
        url: str,
        max_products: int
    ) -> List[Dict[str, Any]]:
        """Extract products from rendered HTML using store extractors"""
        try:
            # Import store extractors
            from scraper.store_extractors import get_extractor
            
            extractor = get_extractor(store_id)
            products = extractor.extract_products(html, store_id)
            
            # Limit results
            products = products[:max_products]
            
            # Add source URL
            for product in products:
                product['source_url'] = url
                product['extracted_at'] = datetime.now().isoformat()
                product['scraper'] = 'fast_js_scraper'
            
            return products
            
        except Exception as e:
            logger.error(f"Failed to extract products: {e}")
            # Fallback to AI extraction if store extractor fails
            return await self._extract_products_with_ai(html, url, store_id, max_products)
    
    async def _extract_products_with_ai(
        self,
        html: str,
        url: str,
        store_id: str,
        max_products: int
    ) -> List[Dict[str, Any]]:
        """Fallback: Use AI to extract products from HTML"""
        if not self.use_openai and not self.use_anthropic:
            return []
        
        # Clean HTML for AI processing
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(html, 'html.parser')
        
        # Remove scripts and styles
        for tag in soup(['script', 'style', 'noscript', 'svg', 'path']):
            tag.decompose()
        
        # Get text content
        text = soup.get_text(separator='\n', strip=True)
        text = text[:15000]  # Limit for AI
        
        prompt = f"""Extract product listings from this {store_id} search results page.

URL: {url}

Page Content:
{text}

Extract up to {max_products} products. Return ONLY valid JSON array (no markdown):
[
    {{
        "name": "<product name>",
        "price": <number or null>,
        "price_display": "<price as shown, e.g. $4.99>",
        "brand": "<brand or null>",
        "size": "<size/quantity or null>",
        "availability": "<in stock/check store/null>",
        "rating": <1-5 or null>,
        "review_count": <number or null>
    }}
]

Return empty array [] if no products found."""

        try:
            if self.use_anthropic:
                return await self._call_anthropic(prompt)
            else:
                return await self._call_openai(prompt)
        except Exception as e:
            logger.error(f"AI extraction failed: {e}")
            return []
    
    async def _extract_product_with_ai(
        self,
        html: str,
        url: str,
        store_id: str
    ) -> Dict[str, Any]:
        """Use AI to extract structured product data from a product page"""
        if not self.use_openai and not self.use_anthropic:
            return {}
        
        # Clean and prepare HTML
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(html, 'html.parser')
        
        # Remove scripts and styles
        for tag in soup(['script', 'style', 'noscript', 'svg', 'path']):
            tag.decompose()
        
        # Get page title
        title = soup.find('title')
        title_text = title.get_text() if title else ""
        
        # Get text content (truncated)
        text = soup.get_text(separator='\n', strip=True)
        text = text[:10000]
        
        # Find price candidates
        price_candidates = []
        for el in soup.select('[class*="price"], [data-test*="price"], [data-testid*="price"]')[:10]:
            price_text = el.get_text(strip=True)
            if price_text and '$' in price_text:
                price_candidates.append(price_text)
        
        # Find image URLs
        image_urls = []
        og_image = soup.find('meta', property='og:image')
        if og_image and og_image.get('content'):
            image_urls.append(og_image['content'])
        
        for img in soup.select('img')[:15]:
            src = img.get('src') or img.get('data-src')
            if src and src.startswith('http') and not any(x in src.lower() for x in ['logo', 'icon', 'sprite']):
                image_urls.append(src)
        
        prompt = f"""Extract product information from this {store_id} product page.

URL: {url}
Page Title: {title_text}

Price Candidates Found:
{chr(10).join(price_candidates[:5]) if price_candidates else "None found"}

Image URLs Found:
{chr(10).join(image_urls[:5]) if image_urls else "None found"}

Page Content:
{text}

Return ONLY valid JSON (no markdown):
{{
    "name": "<product name>",
    "price": <number or null>,
    "currency": "USD",
    "price_text": "<exact price string>",
    "original_price": <number if on sale, else null>,
    "sale_price": <number if on sale, else null>,
    "unit_price": "<e.g., $0.50/oz or null>",
    "brand": "<brand or null>",
    "quantity": "<size like '1 gallon', '16 oz' or null>",
    "description": "<detailed 2-3 sentence description or null>",
    "image_url": "<main product image URL or null>",
    "availability": "<in stock/out of stock/check store>",
    "rating": <1-5 or null>,
    "reviews_count": <number or null>,
    "sku": "<product SKU or null>",
    "upc": "<UPC code or null>"
}}"""

        try:
            if self.use_anthropic:
                result = await self._call_anthropic_single(prompt)
            else:
                result = await self._call_openai_single(prompt)
            
            if result:
                result['source_url'] = url
                result['store_id'] = store_id
                result['extracted_at'] = datetime.now().isoformat()
                result['scraper'] = 'fast_js_scraper_ai'
            
            return result
            
        except Exception as e:
            logger.error(f"AI extraction failed: {e}")
            return {}
    
    async def _call_anthropic(self, prompt: str) -> List[Dict[str, Any]]:
        """Call Anthropic API for list extraction"""
        try:
            import anthropic
            client = anthropic.Anthropic(api_key=self.anthropic_key)
            
            message = client.messages.create(
                model="claude-3-5-sonnet-20241022",
                max_tokens=2000,
                temperature=0.1,
                messages=[{"role": "user", "content": prompt}]
            )
            
            content = message.content[0].text if message.content else "[]"
            return self._parse_json_array(content)
            
        except Exception as e:
            logger.error(f"Anthropic API error: {e}")
            return []
    
    async def _call_anthropic_single(self, prompt: str) -> Dict[str, Any]:
        """Call Anthropic API for single object extraction"""
        try:
            import anthropic
            client = anthropic.Anthropic(api_key=self.anthropic_key)
            
            message = client.messages.create(
                model="claude-3-5-sonnet-20241022",
                max_tokens=800,
                temperature=0.1,
                messages=[{"role": "user", "content": prompt}]
            )
            
            content = message.content[0].text if message.content else "{}"
            return self._parse_json_object(content)
            
        except Exception as e:
            logger.error(f"Anthropic API error: {e}")
            return {}
    
    async def _call_openai(self, prompt: str) -> List[Dict[str, Any]]:
        """Call OpenAI API for list extraction"""
        try:
            from openai import AsyncOpenAI
            client = AsyncOpenAI(api_key=self.openai_key)
            
            response = await client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1,
                max_tokens=2000,
                response_format={"type": "json_object"}
            )
            
            content = response.choices[0].message.content or "[]"
            return self._parse_json_array(content)
            
        except Exception as e:
            logger.error(f"OpenAI API error: {e}")
            return []
    
    async def _call_openai_single(self, prompt: str) -> Dict[str, Any]:
        """Call OpenAI API for single object extraction"""
        try:
            from openai import AsyncOpenAI
            client = AsyncOpenAI(api_key=self.openai_key)
            
            response = await client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1,
                max_tokens=800,
                response_format={"type": "json_object"}
            )
            
            content = response.choices[0].message.content or "{}"
            return self._parse_json_object(content)
            
        except Exception as e:
            logger.error(f"OpenAI API error: {e}")
            return {}
    
    def _parse_json_array(self, content: str) -> List[Dict[str, Any]]:
        """Parse JSON array from AI response"""
        try:
            content = content.strip()
            # Remove markdown code blocks
            if content.startswith("```"):
                content = re.sub(r'^```(?:json)?\n?', '', content)
                content = re.sub(r'\n?```$', '', content)
            content = content.strip()
            
            data = json.loads(content)
            
            # Handle both direct array and wrapped object
            if isinstance(data, list):
                return data
            elif isinstance(data, dict) and 'products' in data:
                return data['products']
            elif isinstance(data, dict):
                return [data]
            
            return []
            
        except json.JSONDecodeError as e:
            logger.error(f"JSON parse error: {e}")
            return []
    
    def _parse_json_object(self, content: str) -> Dict[str, Any]:
        """Parse JSON object from AI response"""
        try:
            content = content.strip()
            # Remove markdown code blocks
            if content.startswith("```"):
                content = re.sub(r'^```(?:json)?\n?', '', content)
                content = re.sub(r'\n?```$', '', content)
            content = content.strip()
            
            data = json.loads(content)
            
            if isinstance(data, dict):
                # Clean and validate data
                result = {}
                for key, value in data.items():
                    if value is not None and value != "null":
                        result[key] = value
                return result
            
            return {}
            
        except json.JSONDecodeError as e:
            logger.error(f"JSON parse error: {e}")
            return {}
    
    def is_available(self) -> bool:
        """Check if JS scraper is available (Playwright installed)"""
        try:
            import playwright
            return True
        except ImportError:
            return False


# ============================================================================
# HYBRID SCRAPER - Chooses best method automatically
# ============================================================================

class HybridScraper:
    """
    Intelligent scraper that automatically chooses the best method:
    - Fast HTTP for server-rendered pages
    - Playwright for JavaScript-rendered pages
    
    Includes automatic detection and fallback logic.
    """
    
    # Stores that require JavaScript rendering
    JS_REQUIRED_STORES = {'costco', 'target', 'walmart', 'kroger', 'wegmans', 'whole_foods', 'safeway'}
    
    # Stores that work with HTTP (server-rendered or API-based)
    HTTP_STORES = {'aldi', 'trader_joes', 'publix'}
    
    def __init__(self):
        self._js_scraper: Optional[FastJSScraper] = None
        self._http_scraper = None  # Will use ai_scraper.AIScraper
    
    async def __aenter__(self):
        """Initialize scrapers"""
        self._js_scraper = FastJSScraper()
        await self._js_scraper.__aenter__()
        
        try:
            from scraper.ai_scraper import AIScraper
            self._http_scraper = AIScraper()
            await self._http_scraper.__aenter__()
        except:
            pass
        
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Cleanup"""
        if self._js_scraper:
            await self._js_scraper.__aexit__(exc_type, exc_val, exc_tb)
        if self._http_scraper:
            await self._http_scraper.__aexit__(exc_type, exc_val, exc_tb)
    
    def _detect_store(self, url: str) -> str:
        """Detect store from URL"""
        url_lower = url.lower()
        
        store_patterns = [
            ('costco', ['costco.com']),
            ('target', ['target.com']),
            ('walmart', ['walmart.com']),
            ('kroger', ['kroger.com']),
            ('wegmans', ['wegmans.com']),
            ('whole_foods', ['wholefoodsmarket.com', 'wholefoods.com']),
            ('safeway', ['safeway.com']),
            ('albertsons', ['albertsons.com']),
            ('aldi', ['aldi.us', 'aldi.com']),
            ('trader_joes', ['traderjoes.com']),
            ('publix', ['publix.com']),
        ]
        
        for store_id, patterns in store_patterns:
            if any(pattern in url_lower for pattern in patterns):
                return store_id
        
        return 'unknown'
    
    def _needs_js(self, url: str) -> bool:
        """Determine if URL needs JavaScript rendering"""
        store = self._detect_store(url)
        return store in self.JS_REQUIRED_STORES or store == 'unknown'
    
    async def scrape(
        self,
        url: str,
        store_name: Optional[str] = None,
        force_js: bool = False
    ) -> Dict[str, Any]:
        """
        Scrape a URL using the best available method.
        
        Args:
            url: URL to scrape
            store_name: Optional store name
            force_js: Force JavaScript rendering even for HTTP-compatible stores
        
        Returns:
            Scraped product data
        """
        store = store_name or self._detect_store(url)
        use_js = force_js or self._needs_js(url)
        
        if use_js and self._js_scraper:
            logger.debug(f"Using JS scraper for {store}")
            
            # Detect page type
            if any(x in url.lower() for x in ['/s?', '/search', 'keyword=', 'query=', '/shop/search']):
                products = await self._js_scraper.scrape_search_page(url, store)
                return {'type': 'search', 'products': products, 'scraper': 'js'}
            else:
                product = await self._js_scraper.scrape_product_page(url, store)
                return {'type': 'product', 'product': product, 'scraper': 'js'}
        
        elif self._http_scraper:
            logger.debug(f"Using HTTP scraper for {store}")
            product = await self._http_scraper.extract_product_data(url, store)
            return {'type': 'product', 'product': product, 'scraper': 'http'}
        
        else:
            logger.error("No scraper available")
            return {'error': 'No scraper available'}
    
    async def scrape_batch(
        self,
        urls: List[str],
        store_name: Optional[str] = None,
        max_concurrent: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Scrape multiple URLs concurrently.
        
        Intelligently batches by scraper type for optimal performance.
        """
        if not urls:
            return []
        
        # Group URLs by scraper type
        js_urls = []
        http_urls = []
        
        for url in urls:
            if self._needs_js(url):
                js_urls.append(url)
            else:
                http_urls.append(url)
        
        results = []
        
        # Scrape JS-required URLs
        if js_urls and self._js_scraper:
            js_results = await self._js_scraper.scrape_multiple_urls(
                js_urls, store_name, max_concurrent
            )
            results.extend(js_results)
        
        # Scrape HTTP-compatible URLs
        if http_urls and self._http_scraper:
            semaphore = asyncio.Semaphore(max_concurrent * 2)  # HTTP can handle more
            
            async def scrape_http(url: str):
                async with semaphore:
                    product = await self._http_scraper.extract_product_data(url)
                    return {'url': url, 'product': product, 'scraper': 'http'}
            
            http_results = await asyncio.gather(*[scrape_http(url) for url in http_urls])
            results.extend(http_results)
        
        return results


# ============================================================================
# CONVENIENCE FUNCTIONS
# ============================================================================

async def scrape_js_page(url: str, store_name: Optional[str] = None) -> Dict[str, Any]:
    """
    Convenience function to scrape a single JS-rendered page.
    
    Usage:
        from scraper.js_scraper import scrape_js_page
        
        result = await scrape_js_page("https://www.costco.com/s?keyword=milk")
    """
    async with FastJSScraper() as scraper:
        if any(x in url.lower() for x in ['/s?', '/search', 'keyword=', 'query=', '/shop/search']):
            return await scraper.scrape_search_page(url, store_name)
        else:
            return await scraper.scrape_product_page(url, store_name)


async def scrape_smart(url: str, store_name: Optional[str] = None) -> Dict[str, Any]:
    """
    Convenience function that automatically chooses the best scraping method.
    
    Usage:
        from scraper.js_scraper import scrape_smart
        
        result = await scrape_smart("https://www.costco.com/some-product.product.123.html")
    """
    async with HybridScraper() as scraper:
        return await scraper.scrape(url, store_name)


async def close_browser_pool():
    """Close the global browser pool"""
    global _browser_pool
    if _browser_pool:
        await _browser_pool.close()
        _browser_pool = None

