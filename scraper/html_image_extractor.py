#!/usr/bin/env python3
"""
HTML Image Extractor for Grocery Store Product Pages
Extracts product images directly from HTML using store-specific parsers and universal fallbacks.
"""

import asyncio
import aiohttp
import re
import json
import logging
from typing import Optional, List, Dict, Any
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse

logger = logging.getLogger(__name__)


class HTMLImageExtractor:
    """Extract product images from HTML with store-specific parsers"""
    
    def __init__(self):
        self.session = None
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1'
        }
    
    async def __aenter__(self):
        """Async context manager entry"""
        self.session = aiohttp.ClientSession(
            headers=self.headers,
            timeout=aiohttp.ClientTimeout(total=10)
        )
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        if self.session:
            await self.session.close()
    
    async def extract_image_from_url(self, product_url: str) -> Optional[str]:
        """
        Extract product image URL from a product page URL.
        Uses store-specific parsers when available, falls back to universal parser.
        
        Args:
            product_url: URL of the product page
            
        Returns:
            Direct image URL if found, None otherwise
        """
        if not product_url:
            return None
        
        try:
            # Detect store from URL
            store = self._detect_store(product_url)
            
            # Fetch HTML
            if not self.session:
                self.session = aiohttp.ClientSession(
                    headers=self.headers,
                    timeout=aiohttp.ClientTimeout(total=10)
                )
            
            logger.debug(f"🌐 Fetching HTML for image extraction: {product_url[:80]}...")
            async with self.session.get(product_url, allow_redirects=True) as response:
                if response.status != 200:
                    logger.debug(f"HTTP {response.status} for {product_url}")
                    return None
                
                html = await response.text()
            
            # Use store-specific parser
            if store == "target":
                image_url = await self._extract_target_image(html, product_url)
            elif store == "walmart":
                image_url = await self._extract_walmart_image(html, product_url)
            elif store == "kroger":
                image_url = await self._extract_kroger_image(html, product_url)
            elif store == "whole_foods":
                image_url = await self._extract_whole_foods_image(html, product_url)
            else:
                # Universal parser for other stores
                image_url = await self._extract_universal_image(html, product_url)
            
            # Validate image URL if found
            if image_url:
                is_valid = await self._validate_image_url(image_url)
                if is_valid:
                    logger.info(f"✅ Extracted valid image URL: {image_url[:80]}...")
                    return image_url
                else:
                    logger.debug(f"⚠️ Image URL failed validation: {image_url[:80]}...")
                    # For Walmart, try multiple URL formats before giving up
                    if store == "walmart":
                        # Try alternative formats
                        import re
                        product_id_match = re.search(r'/ip/[^/]+/(\d+)', product_url)
                        if product_id_match:
                            product_id = product_id_match.group(1)
                            alt_formats = [
                                f"https://i5.walmartimages.com/asr/{product_id}.jpeg?odnHeight=612&odnWidth=612&odnBg=FFFFFF",
                                f"https://i5.walmartimages.com/asr/{product_id}.jpeg",
                            ]
                            for alt_url in alt_formats:
                                if await self._validate_image_url(alt_url):
                                    logger.info(f"✅ Found valid alternative Walmart image: {alt_url[:80]}...")
                                    return alt_url
                    
                    # Try universal parser as fallback if store-specific failed
                    if store != "unknown":
                        logger.debug(f"Trying universal parser as fallback...")
                        universal_image = await self._extract_universal_image(html, product_url)
                        if universal_image:
                            if await self._validate_image_url(universal_image):
                                return universal_image
                            # If validation fails but URL looks reasonable, return it anyway
                            # (some CDNs don't respond to HEAD requests properly)
                            if universal_image.startswith('http') and any(ext in universal_image.lower() for ext in ['.jpg', '.jpeg', '.png', '.webp', '.gif']):
                                logger.debug(f"Returning unvalidated but reasonable-looking image URL: {universal_image[:80]}...")
                                return universal_image
            
            # Last resort: return unvalidated but reasonable-looking URL if found
            if image_url and image_url.startswith('http') and any(ext in image_url.lower() for ext in ['.jpg', '.jpeg', '.png', '.webp', '.gif']):
                logger.debug(f"Returning unvalidated but reasonable-looking image URL: {image_url[:80]}...")
                return image_url
            
            return None
            
        except asyncio.TimeoutError:
            logger.debug(f"⏱️ Timeout fetching {product_url}")
            return None
        except Exception as e:
            logger.debug(f"❌ Error extracting image from {product_url}: {e}")
            return None
    
    def _detect_store(self, url: str) -> str:
        """Detect store from URL"""
        url_lower = url.lower()
        if "target.com" in url_lower:
            return "target"
        elif "walmart.com" in url_lower:
            return "walmart"
        elif "kroger.com" in url_lower:
            return "kroger"
        elif "wholefoodsmarket.com" in url_lower or "wholefoods.com" in url_lower:
            return "whole_foods"
        else:
            return "unknown"
    
    async def _extract_target_image(self, html: str, url: str) -> Optional[str]:
        """Extract image from Target product page"""
        try:
            soup = BeautifulSoup(html, 'html.parser')
            
            # Method 1: JSON-LD structured data
            json_ld_scripts = soup.find_all('script', type='application/ld+json')
            for script in json_ld_scripts:
                try:
                    data = json.loads(script.string)
                    if isinstance(data, dict):
                        # Check for image in product data
                        image = data.get('image') or data.get('@graph', [{}])[0].get('image')
                        if image:
                            if isinstance(image, list) and len(image) > 0:
                                image = image[0]
                            if isinstance(image, dict):
                                image = image.get('url') or image.get('@id')
                            if image and isinstance(image, str) and image.startswith('http'):
                                return image
                except (json.JSONDecodeError, KeyError, IndexError):
                    continue
            
            # Method 2: og:image meta tag
            og_image = soup.find('meta', property='og:image')
            if og_image and og_image.get('content'):
                image_url = og_image['content']
                if image_url.startswith('http'):
                    return image_url
            
            # Method 3: Find Scene7 image URLs in HTML
            # Target uses Scene7 CDN: target.scene7.com/is/image/Target/{product_id}
            scene7_pattern = r'https?://target\.scene7\.com/is/image/Target/[A-Z0-9]+(?:\?[^"\s<>]+)?'
            matches = re.findall(scene7_pattern, html)
            if matches:
                # Prefer webp format with high quality
                for match in matches:
                    if 'fmt=webp' in match or 'qlt=80' in match:
                        return match
                return matches[0]  # Return first match if no webp found
            
            # Method 4: Extract product ID and construct Scene7 URL
            # Target URLs: /p/product-name/-/A-{product_id}
            product_id_match = re.search(r'/A-([A-Z0-9]+)', url)
            if product_id_match:
                product_id = product_id_match.group(1)
                # Try different Scene7 formats
                formats = [
                    f"https://target.scene7.com/is/image/Target/{product_id}?wid=1200&hei=1200&qlt=80&fmt=webp",
                    f"https://target.scene7.com/is/image/Target/{product_id}?wid=800&hei=800&qlt=80&fmt=webp",
                    f"https://target.scene7.com/is/image/Target/{product_id}"
                ]
                # Return first format (will validate later)
                return formats[0]
            
            return None
            
        except Exception as e:
            logger.debug(f"Target image extraction failed: {e}")
            return None
    
    async def _extract_walmart_image(self, html: str, url: str) -> Optional[str]:
        """Extract image from Walmart product page"""
        try:
            soup = BeautifulSoup(html, 'html.parser')
            
            # Method 1: JSON-LD structured data
            json_ld_scripts = soup.find_all('script', type='application/ld+json')
            for script in json_ld_scripts:
                try:
                    data = json.loads(script.string)
                    if isinstance(data, dict):
                        image = data.get('image')
                        if image:
                            if isinstance(image, list) and len(image) > 0:
                                image = image[0]
                            if isinstance(image, dict):
                                image = image.get('url') or image.get('@id')
                            if image and isinstance(image, str) and image.startswith('http'):
                                return image
                except (json.JSONDecodeError, KeyError, IndexError):
                    continue
            
            # Method 2: og:image meta tag
            og_image = soup.find('meta', property='og:image')
            if og_image and og_image.get('content'):
                image_url = og_image['content']
                if image_url.startswith('http'):
                    return image_url
            
            # Method 3: Find Walmart CDN image URLs
            # Walmart uses: i5.walmartimages.com, i5.walmartimages.com/asr/, etc.
            walmart_patterns = [
                r'https?://i\d+\.walmartimages\.com/[^\s"\'\)\]\}]+\.(?:jpg|jpeg|png|webp|gif)(?:\?[^\s"\'\)\]\}]*)?',
                r'https?://i\d+\.walmartimages\.com/asr/[^\s"\'\)\]\}]+\.(?:jpg|jpeg|png|webp|gif)',
            ]
            for pattern in walmart_patterns:
                matches = re.findall(pattern, html, re.IGNORECASE)
                if matches:
                    # Prefer high-res images
                    for match in matches:
                        if 'odnHeight=612' in match or 'odnWidth=612' in match:
                            return match.rstrip('.,;!?)').split(')')[0].split(']')[0].split('}')[0].split('"')[0].split("'")[0]
                    return matches[0].rstrip('.,;!?)').split(')')[0].split(']')[0].split('}')[0].split('"')[0].split("'")[0]
            
            # Method 4: Look for image URLs in data attributes and scripts
            # Walmart sometimes embeds image URLs in data attributes
            img_tags = soup.find_all('img', {'data-testid': re.compile('product-image|hero-image|product-hero', re.I)})
            for img in img_tags[:5]:  # Check first 5 matches
                src = img.get('src') or img.get('data-src') or img.get('data-lazy-src') or img.get('data-hi-res-src')
                if src and 'walmartimages.com' in src.lower():
                    if src.startswith('//'):
                        src = 'https:' + src
                    elif src.startswith('/'):
                        src = 'https://www.walmart.com' + src
                    if src.startswith('http'):
                        return src
            
            # Method 5: Extract product ID and construct Walmart CDN URL
            # Walmart URLs: /ip/product-name/{product_id}
            product_id_match = re.search(r'/ip/[^/]+/(\d+)', url)
            if product_id_match:
                product_id = product_id_match.group(1)
                # Try different Walmart CDN formats (order matters - try most likely first)
                formats = [
                    f"https://i5.walmartimages.com/seo/{product_id}.jpeg",
                    f"https://i5.walmartimages.com/asr/{product_id}.jpeg?odnHeight=612&odnWidth=612&odnBg=FFFFFF",
                    f"https://i5.walmartimages.com/asr/{product_id}.jpeg",
                    f"https://i5.walmartimages.com/dfw/4ff9c6c9-{product_id}/k2-_default.{product_id}.v1.jpg",  # Another common format
                ]
                # Return first format (will validate later)
                return formats[0]
            
            return None
            
        except Exception as e:
            logger.debug(f"Walmart image extraction failed: {e}")
            return None
    
    async def _extract_kroger_image(self, html: str, url: str) -> Optional[str]:
        """Extract image from Kroger product page"""
        try:
            soup = BeautifulSoup(html, 'html.parser')
            
            # Method 1: JSON-LD structured data
            json_ld_scripts = soup.find_all('script', type='application/ld+json')
            for script in json_ld_scripts:
                try:
                    data = json.loads(script.string)
                    if isinstance(data, dict):
                        image = data.get('image')
                        if image:
                            if isinstance(image, list) and len(image) > 0:
                                image = image[0]
                            if isinstance(image, dict):
                                image = image.get('url') or image.get('@id')
                            if image and isinstance(image, str) and image.startswith('http'):
                                return image
                except (json.JSONDecodeError, KeyError, IndexError):
                    continue
            
            # Method 2: og:image meta tag
            og_image = soup.find('meta', property='og:image')
            if og_image and og_image.get('content'):
                image_url = og_image['content']
                if image_url.startswith('http'):
                    return image_url
            
            # Method 3: Find Kroger CDN images
            kroger_patterns = [
                r'https?://[^"\s<>]+\.kroger\.com/[^\s"\'\)\]\}]+\.(?:jpg|jpeg|png|webp|gif)',
                r'https?://images\.kroger\.com/[^\s"\'\)\]\}]+\.(?:jpg|jpeg|png|webp|gif)',
            ]
            for pattern in kroger_patterns:
                matches = re.findall(pattern, html, re.IGNORECASE)
                if matches:
                    return matches[0]
            
            return None
            
        except Exception as e:
            logger.debug(f"Kroger image extraction failed: {e}")
            return None
    
    async def _extract_whole_foods_image(self, html: str, url: str) -> Optional[str]:
        """Extract image from Whole Foods product page"""
        try:
            soup = BeautifulSoup(html, 'html.parser')
            
            # Method 1: JSON-LD structured data
            json_ld_scripts = soup.find_all('script', type='application/ld+json')
            for script in json_ld_scripts:
                try:
                    data = json.loads(script.string)
                    if isinstance(data, dict):
                        image = data.get('image')
                        if image:
                            if isinstance(image, list) and len(image) > 0:
                                image = image[0]
                            if isinstance(image, dict):
                                image = image.get('url') or image.get('@id')
                            if image and isinstance(image, str) and image.startswith('http'):
                                return image
                except (json.JSONDecodeError, KeyError, IndexError):
                    continue
            
            # Method 2: og:image meta tag
            og_image = soup.find('meta', property='og:image')
            if og_image and og_image.get('content'):
                image_url = og_image['content']
                if image_url.startswith('http'):
                    return image_url
            
            # Method 3: Amazon CDN (Whole Foods is owned by Amazon)
            amazon_patterns = [
                r'https?://[^"\s<>]+\.ssl-images-amazon\.com/[^\s"\'\)\]\}]+\.(?:jpg|jpeg|png|webp|gif)',
                r'https?://images-na\.ssl-images-amazon\.com/[^\s"\'\)\]\}]+\.(?:jpg|jpeg|png|webp|gif)',
            ]
            for pattern in amazon_patterns:
                matches = re.findall(pattern, html, re.IGNORECASE)
                if matches:
                    return matches[0]
            
            return None
            
        except Exception as e:
            logger.debug(f"Whole Foods image extraction failed: {e}")
            return None
    
    async def _extract_universal_image(self, html: str, url: str) -> Optional[str]:
        """Universal image extractor for any store"""
        try:
            soup = BeautifulSoup(html, 'html.parser')
            
            # Method 1: og:image meta tag (most reliable universal method)
            og_image = soup.find('meta', property='og:image')
            if og_image and og_image.get('content'):
                image_url = og_image['content']
                if image_url.startswith('http'):
                    return image_url
            
            # Method 2: JSON-LD structured data
            json_ld_scripts = soup.find_all('script', type='application/ld+json')
            for script in json_ld_scripts:
                try:
                    data = json.loads(script.string)
                    if isinstance(data, dict):
                        image = data.get('image')
                        if image:
                            if isinstance(image, list) and len(image) > 0:
                                image = image[0]
                            if isinstance(image, dict):
                                image = image.get('url') or image.get('@id')
                            if image and isinstance(image, str) and image.startswith('http'):
                                return image
                except (json.JSONDecodeError, KeyError, IndexError):
                    continue
            
            # Method 3: Find img tags with product-related classes/ids
            product_image_selectors = [
                'img[class*="product"]',
                'img[id*="product"]',
                'img[data-test*="product"]',
                'img[class*="main"]',
                'img[class*="primary"]',
                'img[class*="hero"]',
            ]
            
            for selector in product_image_selectors:
                imgs = soup.select(selector)
                for img in imgs[:3]:  # Check first 3 matches
                    src = img.get('src') or img.get('data-src') or img.get('data-lazy-src')
                    if src:
                        # Resolve relative URLs
                        if src.startswith('//'):
                            src = 'https:' + src
                        elif src.startswith('/'):
                            src = urljoin(url, src)
                        
                        if src.startswith('http') and self._looks_like_product_image(src):
                            return src
            
            # Method 4: Find all img tags and filter for product images
            all_imgs = soup.find_all('img')
            for img in all_imgs:
                src = img.get('src') or img.get('data-src') or img.get('data-lazy-src')
                if src and self._looks_like_product_image(src):
                    if src.startswith('//'):
                        src = 'https:' + src
                    elif src.startswith('/'):
                        src = urljoin(url, src)
                    if src.startswith('http'):
                        return src
            
            return None
            
        except Exception as e:
            logger.debug(f"Universal image extraction failed: {e}")
            return None
    
    def _looks_like_product_image(self, url: str) -> bool:
        """Check if URL looks like a product image (not logo, icon, etc.)"""
        url_lower = url.lower()
        
        # Exclude common non-product images
        exclude_patterns = [
            'logo', 'icon', 'favicon', 'sprite', 'button', 'banner',
            'social', 'facebook', 'twitter', 'instagram', 'pinterest',
            'cart', 'search', 'menu', 'nav', 'header', 'footer',
            'ad', 'advertisement', 'promo', 'badge'
        ]
        
        for pattern in exclude_patterns:
            if pattern in url_lower:
                return False
        
        # Include common product image patterns
        include_patterns = [
            'product', 'item', 'image', 'photo', 'picture',
            'cdn', 'static', 'media', 'assets'
        ]
        
        for pattern in include_patterns:
            if pattern in url_lower:
                return True
        
        # If URL has reasonable dimensions in path or looks like CDN, include it
        if any(cdn in url_lower for cdn in ['cdn', 'static', 'media', 'images', 'assets']):
            # Check if it's not obviously an icon (very small dimensions)
            if not any(size in url_lower for size in ['16x16', '32x32', '64x64', 'icon']):
                return True
        
        return False
    
    async def _validate_image_url(self, image_url: str) -> bool:
        """
        Validate that an image URL actually exists and returns a valid image.
        Uses HTTP HEAD request for efficiency.
        """
        if not image_url or not image_url.startswith('http'):
            return False
        
        try:
            if not self.session:
                self.session = aiohttp.ClientSession(
                    headers=self.headers,
                    timeout=aiohttp.ClientTimeout(total=5)
                )
            
            async with self.session.head(image_url, allow_redirects=True) as response:
                if response.status == 200:
                    content_type = response.headers.get('Content-Type', '').lower()
                    # Check if it's an image content type
                    if content_type.startswith('image/'):
                        return True
                    # Some CDNs don't set content-type correctly, check URL extension
                    if any(ext in image_url.lower() for ext in ['.jpg', '.jpeg', '.png', '.webp', '.gif']):
                        return True
            
            return False
            
        except Exception as e:
            logger.debug(f"Image validation failed for {image_url[:80]}...: {e}")
            return False
    
    async def extract_images_batch(self, product_urls: List[str], max_concurrent: int = 10) -> Dict[str, Optional[str]]:
        """
        Extract images from multiple product URLs concurrently.
        
        Args:
            product_urls: List of product page URLs
            max_concurrent: Maximum concurrent requests
            
        Returns:
            Dictionary mapping product_url -> image_url (or None if not found)
        """
        semaphore = asyncio.Semaphore(max_concurrent)
        results = {}
        
        async def extract_one(url: str):
            async with semaphore:
                image_url = await self.extract_image_from_url(url)
                results[url] = image_url
        
        await asyncio.gather(*[extract_one(url) for url in product_urls])
        return results

