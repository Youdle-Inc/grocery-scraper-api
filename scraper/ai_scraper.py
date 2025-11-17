#!/usr/bin/env python3
"""
AI-Powered Product Scraper
Uses direct HTTP requests + BeautifulSoup for fast HTML parsing and AI (OpenAI/Anthropic) for structured data extraction.
Much faster than Playwright - no browser needed!
"""

import asyncio
import os
import logging
import json
import aiohttp
from typing import Dict, List, Any, Optional, Tuple
from dotenv import load_dotenv
from datetime import datetime
from bs4 import BeautifulSoup

load_dotenv()
logger = logging.getLogger(__name__)


class AIScraper:
    """
    Universal AI-powered scraper for ANY grocery store.
    Uses fast HTTP requests + BeautifulSoup for HTML parsing + AI (OpenAI/Anthropic) 
    for structured data extraction.
    
    Works with:
    - Target, Walmart, Kroger, Whole Foods, Safeway, ALDI, Costco, Trader Joe's, etc.
    - Any grocery store website - adapts to different layouts automatically
    - Much faster than Playwright (no browser needed!)
    """
    
    def __init__(self):
        """Initialize AI scraper with optional LLM API keys"""
        self.openai_key = os.getenv("OPENAI_API_KEY")
        self.anthropic_key = os.getenv("ANTHROPIC_API_KEY")
        self.use_anthropic = bool(self.anthropic_key)
        self.use_openai = bool(self.openai_key)
        self.session = None
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1'
        }
        
        if not self.use_openai and not self.use_anthropic:
            logger.warning("⚠️ No LLM API key found (OPENAI_API_KEY or ANTHROPIC_API_KEY). AI extraction will be limited.")
        else:
            llm_provider = "Anthropic" if self.use_anthropic else "OpenAI"
            logger.info(f"✅ AI Scraper initialized (Fast HTTP mode) with {llm_provider}")
    
    async def __aenter__(self):
        """Async context manager entry"""
        self.session = aiohttp.ClientSession(headers=self.headers, timeout=aiohttp.ClientTimeout(total=10))
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        if self.session:
            await self.session.close()
    
    async def extract_product_data(
        self,
        product_url: str,
        store_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Extract product data from a product URL using fast HTTP + AI extraction.
        
        Args:
            product_url: URL of the product page
            store_name: Optional store name for context
        
        Returns:
            Dictionary with extracted product data (price, description, etc.)
        """
        if not self.session:
            self.session = aiohttp.ClientSession(headers=self.headers, timeout=aiohttp.ClientTimeout(total=10))
        
        try:
            # Fast HTTP request (no browser!)
            logger.debug(f"🌐 Fetching product page: {product_url}")
            async with self.session.get(product_url, allow_redirects=True) as response:
                if response.status != 200:
                    logger.warning(f"HTTP {response.status} for {product_url}")
                    return {}
                
                html = await response.text()
            
            # Parse HTML with BeautifulSoup (fast!)
            page_content = await self._extract_page_content(html, product_url, store_name)
            
            # Use AI to extract structured data
            extracted_data = await self._extract_with_ai(page_content, product_url, store_name)
            
            return extracted_data
                    
        except asyncio.TimeoutError:
            logger.error(f"⏱️ Timeout fetching {product_url}")
            return {}
        except Exception as e:
            logger.error(f"❌ Error scraping {product_url}: {e}")
            return {}
    
    async def _extract_page_content(
        self,
        html: str,
        url: str,
        store_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """Extract relevant content from HTML (fast!)"""
        try:
            soup = BeautifulSoup(html, 'html.parser')
            
            # Remove script and style elements
            for script in soup(["script", "style", "noscript"]):
                script.decompose()
            
            # Get title
            title = soup.find('title')
            title_text = title.get_text() if title else ""
            
            # Get main content
            main = soup.find('main') or soup.find('body') or soup
            text = main.get_text(separator=' ', strip=True)
            
            # Find price candidates (universal selectors for any grocery store)
            price_candidates = []
            price_selectors = [
                # Generic selectors
                '[data-test*="price"]',
                '[class*="price"]',
                '[id*="price"]',
                '[data-testid*="price"]',
                '.price',
                '[itemprop="price"]',
                '[data-test="product-price"]',
                '[class*="ProductPrice"]',
                # Store-specific selectors
                '[class*="Price"]',
                '[class*="cost"]',
                '[class*="amount"]',
                '[aria-label*="price"]',
                '[data-automation-id*="price"]',
                # Common patterns
                'span:contains("$")',
                'div:contains("$")',
                '[class*="pricing"]',
                '[class*="purchase"]'
            ]
            
            for selector in price_selectors:
                try:
                    elements = soup.select(selector)
                    for el in elements[:5]:  # Limit per selector
                        text_content = el.get_text(strip=True)
                        if text_content and ('$' in text_content or any(c.isdigit() for c in text_content)):
                            price_candidates.append(text_content)
                            if len(price_candidates) >= 15:
                                break
                    if len(price_candidates) >= 15:
                        break
                except:
                    continue
            
            # Find image URLs (for AI to extract product images)
            image_urls = []
            # Check og:image meta tag
            og_image = soup.find('meta', property='og:image')
            if og_image and og_image.get('content'):
                img_url = og_image['content']
                if img_url.startswith(('http://', 'https://')):
                    image_urls.append(img_url)
            
            # Find img tags with product-related classes
            img_tags = soup.find_all('img')
            for img in img_tags[:20]:  # Limit to first 20
                src = img.get('src') or img.get('data-src') or img.get('data-lazy-src')
                if src:
                    # Resolve relative URLs
                    if src.startswith('//'):
                        src = 'https:' + src
                    elif src.startswith('/'):
                        from urllib.parse import urljoin
                        src = urljoin(url, src)
                    
                    if src.startswith(('http://', 'https://')):
                        # Exclude logos and icons
                        src_lower = src.lower()
                        if not any(exclude in src_lower for exclude in ['logo', 'icon', 'favicon', 'sprite', 'wegmans-og-share-img', '53100']):
                            image_urls.append(src)
            
            # Get HTML snippet for context
            html_snippet = str(main)[:10000] if main else ""
            
            return {
                "text": text[:5000],  # Limit text size
                "html_snippet": html_snippet[:10000],
                "title": title_text,
                "url": url,
                "price_candidates": list(set(price_candidates))[:10],  # Deduplicate
                "image_urls": list(set(image_urls))[:15]  # Deduplicate and limit
            }
            
        except Exception as e:
            logger.error(f"Error extracting page content: {e}")
            return {"text": "", "html_snippet": "", "title": "", "url": url, "price_candidates": []}
    
    async def _extract_with_ai(
        self,
        page_content: Dict[str, Any],
        product_url: str,
        store_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """Use AI to extract structured product data from page content"""
        
        if not self.use_openai and not self.use_anthropic:
            # Fallback: simple regex extraction
            return self._extract_with_regex(page_content)
        
        # Prepare prompt for AI
        prompt = self._build_extraction_prompt(page_content, product_url, store_name)
        
        try:
            if self.use_anthropic:
                return await self._extract_with_anthropic(prompt)
            elif self.use_openai:
                return await self._extract_with_openai(prompt)
        except Exception as e:
            logger.error(f"AI extraction failed: {e}, falling back to regex")
            return self._extract_with_regex(page_content)
    
    def _build_extraction_prompt(
        self,
        page_content: Dict[str, Any],
        product_url: str,
        store_name: Optional[str] = None
    ) -> str:
        """Build prompt for AI extraction - Universal for any grocery store"""
        price_candidates = "\n".join(page_content.get("price_candidates", [])[:5])
        
        # Detect store type from URL for context
        store_hint = ""
        if "target.com" in product_url.lower():
            store_hint = "Target - prices are usually in format $X.XX"
        elif "walmart.com" in product_url.lower():
            store_hint = "Walmart - look for price in various formats"
        elif "kroger.com" in product_url.lower():
            store_hint = "Kroger - prices may include per-unit pricing"
        elif "wholefoodsmarket.com" in product_url.lower():
            store_hint = "Whole Foods - may have organic pricing"
        
        return f"""Extract structured product information from ANY grocery store product page.
This is a UNIVERSAL grocery store scraper - adapt to the store's layout.

URL: {product_url}
Store: {store_name or "Unknown"}
{store_hint}

Page Title: {page_content.get("title", "")}

Page Text (first 4000 chars):
{page_content.get("text", "")[:4000]}

Image URLs Found in HTML (may contain product images):
{chr(10).join(page_content.get("image_urls", [])[:10]) if page_content.get("image_urls") else "None found - look for img tags with product images"}

Price Candidates Found (may contain the actual price):
{price_candidates if price_candidates else "None found - search the page text carefully"}

Extract the following information and return ONLY valid JSON (no markdown, no code blocks):
{{
    "price": <number or null - extract the main/current price, ignore sale prices unless it's the only price>,
    "currency": "USD",
    "price_text": "<exact price string as shown on page>",
    "original_price": <number or null - if there's a sale, the original price>,
    "sale_price": <number or null - if on sale>,
    "unit_price": "<string or null - e.g., '$0.50 per oz' or null>",
    "name": "<product name - the main product title>",
    "brand": "<brand name or null>",
    "quantity": "<size/quantity like '1 gallon', '12ct', '16 oz' or null>",
    "description": "<detailed product description - include key features, nutritional benefits, ingredients highlights, and what makes this product special. Write 2-3 sentences that would be useful for shoppers. If no detailed description available, use null>",
    "image_url": "<direct URL to the main product image - extract from img tags, og:image, or JSON-LD. Exclude logos, icons, and store branding images. Must be a full HTTP/HTTPS URL>",
    "availability": "<in stock/out of stock/available for pickup/available for delivery/check store or null>",
    "rating": <number 1-5 or null>,
    "reviews_count": <number or null>,
    "sku": "<product SKU or null>",
    "upc": "<UPC code or null>"
}}

Critical Instructions:
- Extract price as a number (e.g., 4.99 for $4.99, 12.50 for $12.50)
- Look for the CURRENT/CURRENT price - ignore "was" prices unless no current price found
- If price not found after careful search, use null
- Price extraction is CRITICAL - be thorough
- For description: Extract detailed product information including key features, nutritional benefits, ingredients, and what makes this product special. Write 2-3 informative sentences that help shoppers understand the product. If only basic info available, create a helpful description from the product name and available details.
- Adapt to different store layouts (Target, Walmart, Kroger, Whole Foods, etc.)
- Store names may be in title, brand field, or product name
- Return valid JSON only - no markdown formatting"""
    
    async def _extract_with_anthropic(self, prompt: str) -> Dict[str, Any]:
        """Extract using Anthropic Claude"""
        try:
            import anthropic
            
            client = anthropic.Anthropic(api_key=self.anthropic_key)
            
            message = client.messages.create(
                model="claude-3-5-sonnet-20241022",
                max_tokens=500,
                temperature=0.1,  # Low temperature for accuracy
                messages=[{
                    "role": "user",
                    "content": prompt
                }]
            )
            
            content = message.content[0].text if message.content else ""
            
            # Parse JSON response
            return self._parse_ai_response(content)
            
        except ImportError:
            logger.error("anthropic package not installed. Install with: pip install anthropic")
            return {}
        except Exception as e:
            logger.error(f"Anthropic API error: {e}")
            return {}
    
    async def _extract_with_openai(self, prompt: str) -> Dict[str, Any]:
        """Extract using OpenAI GPT"""
        try:
            from openai import AsyncOpenAI
            
            client = AsyncOpenAI(api_key=self.openai_key)
            
            response = await client.chat.completions.create(
                model="gpt-4o-mini",  # Fast and cost-effective
                messages=[{
                    "role": "user",
                    "content": prompt
                }],
                temperature=0.1,
                max_tokens=500,
                response_format={"type": "json_object"}  # Force JSON response
            )
            
            content = response.choices[0].message.content
            
            # Parse JSON response
            return self._parse_ai_response(content)
            
        except ImportError:
            logger.error("openai package not installed. Install with: pip install openai")
            return {}
        except Exception as e:
            logger.error(f"OpenAI API error: {e}")
            return {}
    
    def _parse_ai_response(self, content: str) -> Dict[str, Any]:
        """Parse AI response and extract JSON"""
        try:
            # Remove markdown code blocks if present
            content = content.strip()
            if content.startswith("```json"):
                content = content[7:]
            if content.startswith("```"):
                content = content[3:]
            if content.endswith("```"):
                content = content[:-3]
            content = content.strip()
            
            # Parse JSON
            data = json.loads(content)
            
            # Validate and clean data (universal format for any grocery store)
            result = {
                "price": self._parse_price(data.get("price")),
                "currency": data.get("currency", "USD"),
                "price_text": data.get("price_text"),
                "original_price": self._parse_price(data.get("original_price")),
                "sale_price": self._parse_price(data.get("sale_price")),
                "unit_price": data.get("unit_price"),
                "name": data.get("name"),
                "brand": data.get("brand"),
                "quantity": data.get("quantity"),
                "description": data.get("description"),
                "image_url": self._validate_image_url(data.get("image_url")),
                "availability": data.get("availability"),
                "rating": self._parse_float(data.get("rating")),
                "reviews_count": self._parse_int(data.get("reviews_count")),
                "sku": data.get("sku"),
                "upc": data.get("upc"),
                "source": "ai_scraper_universal",
                "extracted_at": datetime.now().isoformat()
            }
            
            return result
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse AI response as JSON: {e}")
            logger.debug(f"Response content: {content[:200]}")
            return {}
        except Exception as e:
            logger.error(f"Error parsing AI response: {e}")
            return {}
    
    def _extract_with_regex(self, page_content: Dict[str, Any]) -> Dict[str, Any]:
        """Fallback: Extract price using regex patterns"""
        import re
        
        text = page_content.get("text", "")
        price_candidates = page_content.get("price_candidates", [])
        
        # Try to extract price
        price = None
        price_text = None
        
        # First try price candidates
        for candidate in price_candidates:
            match = re.search(r'\$?(\d+\.\d{2})', candidate)
            if match:
                try:
                    price = float(match.group(1))
                    price_text = candidate.strip()
                    break
                except:
                    pass
        
        # If not found, search in full text
        if not price:
            price_match = re.search(r'\$(\d+\.\d{2})', text)
            if price_match:
                try:
                    price = float(price_match.group(1))
                    price_text = f"${price:.2f}"
                except:
                    pass
        
            return {
                "price": price,
                "currency": "USD",
                "price_text": price_text,
                "original_price": None,
                "sale_price": None,
                "unit_price": None,
                "name": None,
                "brand": None,
                "quantity": None,
                "description": None,
                "availability": None,
                "rating": None,
                "reviews_count": None,
                "sku": None,
                "upc": None,
                "source": "regex_fallback",
                "extracted_at": datetime.now().isoformat()
            }
    
    def _parse_price(self, value: Any) -> Optional[float]:
        """Parse price value"""
        if value is None:
            return None
        if isinstance(value, (int, float)):
            return float(value)
        if isinstance(value, str):
            import re
            match = re.search(r'(\d+\.?\d*)', value)
            if match:
                try:
                    return float(match.group(1))
                except:
                    pass
        return None
    
    def _parse_float(self, value: Any) -> Optional[float]:
        """Parse float value"""
        if value is None:
            return None
        try:
            return float(value)
        except:
            return None
    
    def _parse_int(self, value: Any) -> Optional[int]:
        """Parse int value"""
        if value is None:
            return None
        try:
            return int(value)
        except:
            return None
    
    async def enhance_product_description(
        self,
        product_name: str,
        brand: Optional[str] = None,
        quantity: Optional[str] = None,
        existing_description: Optional[str] = None
    ) -> Optional[str]:
        """
        Use AI to generate or enhance a product description.
        Creates detailed, shopper-friendly descriptions.
        """
        if not self.use_openai and not self.use_anthropic:
            return None
        
        try:
            # Build prompt for description generation
            prompt = f"""Create a detailed, informative product description for a grocery store product.

Product Name: {product_name}
Brand: {brand or 'Unknown'}
Size/Quantity: {quantity or 'Not specified'}
Existing Description: {existing_description or 'None'}

Create a 2-3 sentence description that includes:
- Key features and benefits
- Nutritional highlights (if applicable)
- What makes this product special or useful
- Any notable attributes (organic, natural, etc.)

Write in a clear, informative style that would help shoppers make a decision.
Return ONLY the description text, no JSON, no markdown, just the description."""
            
            if self.use_anthropic:
                import anthropic
                client = anthropic.Anthropic(api_key=self.anthropic_key)
                message = client.messages.create(
                    model="claude-3-5-sonnet-20241022",
                    max_tokens=200,
                    temperature=0.3,
                    messages=[{"role": "user", "content": prompt}]
                )
                description = message.content[0].text if message.content else None
            elif self.use_openai:
                from openai import AsyncOpenAI
                client = AsyncOpenAI(api_key=self.openai_key)
                response = await client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.3,
                    max_tokens=200
                )
                description = response.choices[0].message.content
            
            if description:
                description = description.strip()
                # Remove markdown if present
                description = description.replace('**', '').replace('*', '')
                if len(description) > 50:
                    return description
            
            return None
            
        except Exception as e:
            logger.debug(f"Failed to enhance description: {e}")
            return None
    
    async def enrich_products_with_prices(
        self,
        products: List[Dict[str, Any]],
        max_concurrent: int = 10  # Can do more with HTTP vs Playwright
    ) -> List[Dict[str, Any]]:
        """
        Enrich a list of products with prices by scraping their product URLs.
        Fast HTTP mode - much faster than Playwright!
        
        Args:
            products: List of product dictionaries with product_url
            max_concurrent: Maximum concurrent scraping requests (default 10, was 5 with Playwright)
        
        Returns:
            List of enriched products
        """
        # Ensure session exists
        if not self.session:
            self.session = aiohttp.ClientSession(headers=self.headers, timeout=aiohttp.ClientTimeout(total=10))
        
        semaphore = asyncio.Semaphore(max_concurrent)
        
        async def enrich_product(product: Dict[str, Any]) -> Dict[str, Any]:
            async with semaphore:
                product_url = product.get("product_url")
                if not product_url:
                    return product
                
                # Skip if already has price
                if product.get("price") is not None:
                    return product
                
                try:
                    extracted = await self.extract_product_data(
                        product_url,
                        product.get("store_name")
                    )
                    
                    # Merge extracted data (only update if we got new data)
                    if extracted.get("price") is not None:
                        product["price"] = extracted["price"]
                        product["currency"] = extracted.get("currency", "USD")
                        if extracted.get("price_text"):
                            product["price_text"] = extracted["price_text"]
                    
                    # Update other fields if available
                    for key in ["availability", "rating", "reviews_count"]:
                        if extracted.get(key) and not product.get(key):
                            product[key] = extracted[key]
                    
                    # Enhance description if available (AI-generated descriptions are usually better)
                    if extracted.get("description") and len(extracted.get("description", "")) > 50:
                        product["description"] = extracted["description"]
                    elif not product.get("description") or len(product.get("description", "")) < 50:
                        # Generate description if missing or too short
                        enhanced_desc = await self.enhance_product_description(
                            product.get("name", ""),
                            product.get("brand"),
                            product.get("quantity"),
                            product.get("description")
                        )
                        if enhanced_desc:
                            product["description"] = enhanced_desc
                    
                    logger.info(f"✅ Enriched product: {product.get('name', 'Unknown')} - Price: ${extracted.get('price')}")
                    
                except Exception as e:
                    logger.debug(f"Failed to enrich product {product_url}: {e}")
                
                return product
        
        # Enrich all products concurrently
        enriched = await asyncio.gather(*[enrich_product(p) for p in products])
        return list(enriched)
    
    def is_available(self) -> bool:
        """Check if AI scraper is available"""
        # Only need LLM API key - no browser needed!
        return bool(self.use_openai or self.use_anthropic)

