"""
Grocery Scraper Package
Professional web scraping for grocery stores
"""

from .models import StoreInfo
from .config import SUPPORTED_STORES

# Fast JavaScript Scraper for JS-rendered sites
try:
    from .js_scraper import (
        FastJSScraper,
        HybridScraper,
        scrape_js_page,
        scrape_smart,
        close_browser_pool,
    )
    JS_SCRAPER_AVAILABLE = True
except ImportError:
    JS_SCRAPER_AVAILABLE = False

__version__ = "1.0.0"
__all__ = [
    "StoreInfo", 
    "SUPPORTED_STORES",
    "FastJSScraper",
    "HybridScraper",
    "scrape_js_page",
    "scrape_smart",
    "close_browser_pool",
    "JS_SCRAPER_AVAILABLE",
]
