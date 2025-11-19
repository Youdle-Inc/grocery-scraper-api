#!/usr/bin/env python3
"""
Store-specific product extractors based on real HTML structure analysis.
Each extractor knows how to parse product cards from specific grocery stores.
"""

import re
import logging
from typing import Dict, List, Optional, Any
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)


class StoreProductExtractor:
    """Base class for store-specific product extractors"""
    
    def extract_products(self, html: str, store_id: str) -> List[Dict[str, Any]]:
        """Extract products from HTML"""
        raise NotImplementedError
    
    def _normalize_price(self, price_text: str) -> Optional[float]:
        """Normalize price text to float"""
        if not price_text:
            return None
        
        # Remove currency symbols and whitespace
        price_text = re.sub(r'[^\d.]', '', price_text)
        try:
            return float(price_text)
        except (ValueError, TypeError):
            return None
    
    def _normalize_price_per_unit(self, unit_text: str) -> Optional[str]:
        """Normalize price per unit text"""
        if not unit_text:
            return None
        
        # Clean up common variations
        unit_text = unit_text.strip()
        unit_text = re.sub(r'\s+', ' ', unit_text)
        return unit_text
    
    def _extract_brand_from_name(self, name: str) -> tuple[Optional[str], str]:
        """Extract brand from product name, return (brand, cleaned_name)"""
        if not name:
            return None, name
        
        # Common brand patterns
        brand_patterns = [
            r'^([A-Z][a-z]+(?:®|™)?)\s+',  # "Kroger® ", "Horizon "
            r'^([A-Z][A-Z\s]+(?:®|™)?)\s+',  # "GREAT VALUE ", "ORGANIC VALLEY "
            r'^([A-Z][a-z]+\s+[A-Z][a-z]+(?:®|™)?)\s+',  # "Whole Foods ", "Trader Joe's "
        ]
        
        for pattern in brand_patterns:
            match = re.match(pattern, name)
            if match:
                brand = match.group(1).strip()
                cleaned_name = name[len(brand):].strip()
                # Remove leading common words
                cleaned_name = re.sub(r'^(the|a|an)\s+', '', cleaned_name, flags=re.IGNORECASE)
                return brand, cleaned_name
        
        return None, name
    
    def _is_valid_individual_product(self, product: Dict[str, Any]) -> bool:
        """
        Validate that a product is an actual individual product, not a category page.
        Returns False for category pages, brand pages, or invalid products.
        """
        if not product:
            return False
        
        name = product.get('name', '').lower()
        product_url = product.get('product_url', '').lower()
        
        # Must have a name
        if not name or len(name) < 3:
            return False
        
        # Category page indicators in name
        category_indicators = [
            'products at', 'products in', 'products from',
            'at target', 'at walmart', 'at kroger', 'at costco',
            'shop all', 'browse', 'view all',
            'brand shop', 'brand store',
            '| costco', '| target', '| walmart', '| kroger',
            'category', 'department', 'section',
            'all products', 'all items', 'all ',
            'paper towels & napkins',  # Category page title
            'paper & plastic products',  # Category page title
            'bulk toilet paper & facial tissue',  # Category page title
        ]
        
        if any(indicator in name for indicator in category_indicators):
            logger.debug(f"Filtering out category page: {name[:60]}...")
            return False
        
        # Gift card indicators
        gift_card_indicators = [
            'gift card', 'giftcard', 'gift-card', 'egift', 'e-gift',
            'digital gift', 'prepaid', 'reloadable', 'gift certificate'
        ]
        
        if any(indicator in name or indicator in product_url for indicator in gift_card_indicators):
            logger.debug(f"Filtering out gift card: {name[:60]}...")
            return False
        
        # URL patterns that indicate category pages
        category_url_patterns = [
            '/category/', '/categories/', '/browse/', '/shop/',
            '/s?keyword=', '/search?', '/c/', '/department/',
            '.html?refine=', '.html?keyword=',  # Costco category pages
        ]
        
        # Allow search URLs if they're product-specific (have product ID)
        if any(pattern in product_url for pattern in category_url_patterns):
            # Check if it's actually a product page (has product ID or .product. in URL)
            if '.product.' not in product_url and '/product/' not in product_url and '/p/' not in product_url and '/ip/' not in product_url:
                logger.debug(f"Filtering out category URL: {product_url[:80]}...")
                return False
        
        # Must have either a product URL or an image (indicates it's a real product)
        if not product_url and not product.get('image_url'):
            logger.debug(f"Filtering out product without URL or image: {name[:60]}...")
            return False
        
        return True


class KrogerExtractor(StoreProductExtractor):
    """Extractor for Kroger.com product cards"""
    
    def extract_products(self, html: str, store_id: str = "kroger") -> List[Dict[str, Any]]:
        """Extract products from Kroger HTML"""
        products = []
        
        try:
            soup = BeautifulSoup(html, 'html.parser')
            
            # Find all product cards using Kroger's data-testid selector
            product_cards = soup.select('[data-testid^="product-card"]')
            
            logger.debug(f"Found {len(product_cards)} Kroger product cards")
            
            for card in product_cards:
                try:
                    product = self._extract_product(card, store_id)
                    if product and self._is_valid_individual_product(product):
                        products.append(product)
                    elif product:
                        logger.debug(f"Filtered out invalid Kroger product: {product.get('name', 'Unknown')[:50]}...")
                except Exception as e:
                    logger.warning(f"Failed to extract Kroger product: {e}")
                    continue
            
        except Exception as e:
            logger.error(f"Failed to parse Kroger HTML: {e}")
        
        return products
    
    def _extract_product(self, card, store_id: str) -> Optional[Dict[str, Any]]:
        """Extract a single product from Kroger product card"""
        product = {
            'store_id': store_id,
            'store_name': 'Kroger',
            'name': None,
            'price': None,
            'price_display': None,
            'price_per_unit': None,
            'size': None,
            'variants': None,
            'image_url': None,
            'product_url': None,
            'rating': None,
            'review_count': None,
            'availability': 'Check Store'
        }
        
        # Extract product name from aria-label
        aria_label = card.get('aria-label', '')
        if aria_label:
            product['name'] = aria_label.strip()
        
        # Extract price from [data-testid="product-item-unit-price"]
        price_el = card.select_one('[data-testid="product-item-unit-price"]')
        if price_el:
            # Try to get value attribute first (numeric)
            price_value = price_el.get('value')
            if price_value:
                product['price'] = self._normalize_price(price_value)
            else:
                # Fallback to text content
                price_text = price_el.get_text(strip=True)
                product['price'] = self._normalize_price(price_text)
                product['price_display'] = price_text
        
        # Extract price per unit from [data-testid="product-item-sizing"]
        sizing_els = card.select('[data-testid="product-item-sizing"]')
        if sizing_els:
            # First occurrence is usually price per unit
            if len(sizing_els) > 0:
                unit_text = sizing_els[0].get_text(strip=True)
                if '$' in unit_text:
                    product['price_per_unit'] = self._normalize_price_per_unit(unit_text)
            
            # Second occurrence is usually size
            if len(sizing_els) > 1:
                size_text = sizing_els[1].get_text(strip=True)
                product['size'] = size_text.strip()
        
        # Extract variants from [data-testid="product-variant-text"]
        variant_el = card.select_one('[data-testid="product-variant-text"]')
        if variant_el:
            product['variants'] = variant_el.get_text(strip=True)
        
        # Extract image from [data-testid="product-image-loaded"]
        img_el = card.select_one('[data-testid="product-image-loaded"]')
        if img_el:
            product['image_url'] = img_el.get('src', '')
            if not product['name'] and img_el.get('alt'):
                product['name'] = img_el.get('alt')
        
        # Extract product link
        link_el = card.select_one('a[href*="/p/"]')
        if link_el:
            href = link_el.get('href', '')
            if href.startswith('/'):
                product['product_url'] = f"https://www.kroger.com{href}"
            else:
                product['product_url'] = href
        
        # Extract brand and clean name
        if product['name']:
            brand, cleaned_name = self._extract_brand_from_name(product['name'])
            product['brand'] = brand
            if brand:
                product['name'] = cleaned_name
        
        # Only return if we have at least name and price
        if product['name'] and product['price']:
            return product
        
        return None


class WalmartExtractor(StoreProductExtractor):
    """Extractor for Walmart.com product cards"""
    
    def extract_products(self, html: str, store_id: str = "walmart") -> List[Dict[str, Any]]:
        """Extract products from Walmart HTML"""
        products = []
        
        try:
            soup = BeautifulSoup(html, 'html.parser')
            
            # Find all product items using Walmart's data-item-id selector
            product_items = soup.select('[data-item-id]')
            
            logger.debug(f"Found {len(product_items)} Walmart product items")
            
            for item in product_items:
                try:
                    product = self._extract_product(item, store_id)
                    if product and self._is_valid_individual_product(product):
                        products.append(product)
                    elif product:
                        logger.debug(f"Filtered out invalid Walmart product: {product.get('name', 'Unknown')[:50]}...")
                except Exception as e:
                    logger.warning(f"Failed to extract Walmart product: {e}")
                    continue
            
        except Exception as e:
            logger.error(f"Failed to parse Walmart HTML: {e}")
        
        return products
    
    def _extract_product(self, item, store_id: str) -> Optional[Dict[str, Any]]:
        """Extract a single product from Walmart product item"""
        product = {
            'store_id': store_id,
            'store_name': 'Walmart',
            'name': None,
            'price': None,
            'price_display': None,
            'price_per_unit': None,
            'size': None,
            'image_url': None,
            'product_url': None,
            'rating': None,
            'review_count': None,
            'availability': 'Check Store',
            'item_id': None
        }
        
        # Extract item ID
        item_id = item.get('data-item-id')
        if item_id:
            product['item_id'] = item_id
        
        # Extract product name from button aria-label
        # Format: "Sign in to add to Favorites list, PRODUCT NAME"
        name_button = item.select_one('button[aria-label*="Sign in to add to Favorites list"]')
        if name_button:
            aria_label = name_button.get('aria-label', '')
            # Extract product name after comma
            match = re.search(r'Sign in to add to Favorites list,\s*(.+)', aria_label)
            if match:
                product['name'] = match.group(1).strip()
        
        # Try alternative name extraction from link
        if not product['name']:
            link_el = item.select_one('a[href*="/ip/"]')
            if link_el:
                product['name'] = link_el.get('aria-label', '').strip() or link_el.get_text(strip=True)
                href = link_el.get('href', '')
                if href.startswith('/'):
                    product['product_url'] = f"https://www.walmart.com{href}"
                else:
                    product['product_url'] = href
        
        # Extract price from [data-automation-id="product-price"] or price class
        price_el = item.select_one('[data-automation-id="product-price"]')
        if not price_el:
            price_el = item.select_one('[class*="price"], [class*="Price"]')
        
        if price_el:
            price_text = price_el.get_text(strip=True)
            product['price_display'] = price_text
            # Extract numeric price
            product['price'] = self._normalize_price(price_text)
            
            # Check if price per unit is in the same text
            if '/' in price_text:
                parts = price_text.split('/')
                if len(parts) > 1:
                    product['price_per_unit'] = parts[-1].strip()
        
        # Extract rating from [data-testid="product-ratings"]
        rating_el = item.select_one('[data-testid="product-ratings"]')
        if rating_el:
            rating_value = rating_el.get('data-value')
            if rating_value:
                try:
                    product['rating'] = float(rating_value)
                except (ValueError, TypeError):
                    pass
        
        # Extract review count from [data-testid="product-reviews"]
        reviews_el = item.select_one('[data-testid="product-reviews"]')
        if reviews_el:
            review_value = reviews_el.get('data-value')
            if review_value:
                try:
                    product['review_count'] = int(review_value)
                except (ValueError, TypeError):
                    pass
        
        # Extract image
        img_el = item.select_one('img')
        if img_el:
            product['image_url'] = img_el.get('src') or img_el.get('data-src', '')
            if not product['name'] and img_el.get('alt'):
                product['name'] = img_el.get('alt')
        
        # Extract link if not already found
        if not product['product_url']:
            link_el = item.select_one('a[href*="/ip/"]')
            if link_el:
                href = link_el.get('href', '')
                if href.startswith('/'):
                    product['product_url'] = f"https://www.walmart.com{href}"
                else:
                    product['product_url'] = href
        
        # Extract brand and clean name
        if product['name']:
            brand, cleaned_name = self._extract_brand_from_name(product['name'])
            product['brand'] = brand
            if brand:
                product['name'] = cleaned_name
        
        # Extract size from name or separate field
        if product['name']:
            size_match = re.search(r'(\d+(?:\.\d+)?\s*(?:oz|fl oz|gallon|gal|lb|count|ct|pack))', product['name'], re.IGNORECASE)
            if size_match:
                product['size'] = size_match.group(1)
        
        # Only return if we have at least name and price
        if product['name'] and product['price']:
            return product
        
        return None


class TargetExtractor(StoreProductExtractor):
    """Extractor for Target.com product cards"""
    
    def extract_products(self, html: str, store_id: str = "target") -> List[Dict[str, Any]]:
        """Extract products from Target HTML"""
        products = []
        
        try:
            soup = BeautifulSoup(html, 'html.parser')
            
            # Try multiple selectors for Target product cards
            selectors = [
                '[data-test="product-card"]',
                '[class*="ProductCard"]',
                '[class*="product-card"]',
                'a[href*="/p/"]'
            ]
            
            product_cards = []
            for selector in selectors:
                cards = soup.select(selector)
                if len(cards) > 5:  # Only use if we find multiple products
                    product_cards = cards
                    break
            
            logger.debug(f"Found {len(product_cards)} Target product cards")
            
            for card in product_cards:
                try:
                    product = self._extract_product(card, store_id)
                    if product and self._is_valid_individual_product(product):
                        products.append(product)
                    elif product:
                        logger.debug(f"Filtered out invalid Target product: {product.get('name', 'Unknown')[:50]}...")
                except Exception as e:
                    logger.warning(f"Failed to extract Target product: {e}")
                    continue
            
        except Exception as e:
            logger.error(f"Failed to parse Target HTML: {e}")
        
        return products
    
    def _extract_product(self, card, store_id: str) -> Optional[Dict[str, Any]]:
        """Extract a single product from Target product card"""
        product = {
            'store_id': store_id,
            'store_name': 'Target',
            'name': None,
            'price': None,
            'price_display': None,
            'price_per_unit': None,
            'image_url': None,
            'product_url': None,
            'rating': None,
            'review_count': None,
            'availability': 'Check Store'
        }
        
        # Extract product name
        name_el = card.select_one('[data-test="product-title"]')
        if not name_el:
            name_el = card.select_one('h3, h2, [class*="title"]')
        
        if name_el:
            product['name'] = name_el.get_text(strip=True)
        
        # Extract price
        price_el = card.select_one('[data-test="product-price"]')
        if not price_el:
            price_el = card.select_one('[class*="price"], [class*="Price"]')
        
        if price_el:
            price_text = price_el.get_text(strip=True)
            product['price_display'] = price_text
            product['price'] = self._normalize_price(price_text)
        
        # Extract price per unit
        unit_price_el = card.select_one('[data-test="product-price-per-unit"]')
        if unit_price_el:
            product['price_per_unit'] = self._normalize_price_per_unit(unit_price_el.get_text(strip=True))
        
        # Extract rating
        rating_el = card.select_one('[data-test="product-rating"]')
        if rating_el:
            rating_text = rating_el.get_text(strip=True)
            rating_match = re.search(r'(\d+\.?\d*)', rating_text)
            if rating_match:
                try:
                    product['rating'] = float(rating_match.group(1))
                except (ValueError, TypeError):
                    pass
        
        # Extract image
        img_el = card.select_one('img')
        if img_el:
            product['image_url'] = img_el.get('src') or img_el.get('data-src', '')
            if not product['name'] and img_el.get('alt'):
                product['name'] = img_el.get('alt')
        
        # Extract link
        link_el = card.select_one('a[href*="/p/"]')
        if link_el:
            href = link_el.get('href', '')
            if href.startswith('/'):
                product['product_url'] = f"https://www.target.com{href}"
            else:
                product['product_url'] = href
        
        # Extract brand and clean name
        if product['name']:
            brand, cleaned_name = self._extract_brand_from_name(product['name'])
            product['brand'] = brand
            if brand:
                product['name'] = cleaned_name
        
        # Only return if we have at least name and price
        if product['name'] and product['price']:
            return product
        
        return None


class WholeFoodsExtractor(StoreProductExtractor):
    """Extractor for Whole Foods Market product cards"""
    
    def extract_products(self, html: str, store_id: str = "whole_foods") -> List[Dict[str, Any]]:
        """Extract products from Whole Foods HTML"""
        products = []
        
        try:
            soup = BeautifulSoup(html, 'html.parser')
            
            # Find product cards
            product_cards = soup.select('[class*="ProductCard"], article, [class*="product-card"]')
            
            logger.debug(f"Found {len(product_cards)} Whole Foods product cards")
            
            for card in product_cards:
                try:
                    product = self._extract_product(card, store_id)
                    if product and self._is_valid_individual_product(product):
                        products.append(product)
                    elif product:
                        logger.debug(f"Filtered out invalid Whole Foods product: {product.get('name', 'Unknown')[:50]}...")
                except Exception as e:
                    logger.warning(f"Failed to extract Whole Foods product: {e}")
                    continue
            
        except Exception as e:
            logger.error(f"Failed to parse Whole Foods HTML: {e}")
        
        return products
    
    def _extract_product(self, card, store_id: str) -> Optional[Dict[str, Any]]:
        """Extract a single product from Whole Foods product card"""
        product = {
            'store_id': store_id,
            'store_name': 'Whole Foods',
            'name': None,
            'price': None,
            'price_display': None,
            'price_per_unit': None,
            'image_url': None,
            'product_url': None,
            'availability': 'Check Store'
        }
        
        # Extract product name
        name_el = card.select_one('h3, h2, [class*="title"], [class*="name"]')
        if name_el:
            product['name'] = name_el.get_text(strip=True)
        
        # Extract price
        price_el = card.select_one('[class*="price"], [class*="Price"]')
        if price_el:
            price_text = price_el.get_text(strip=True)
            product['price_display'] = price_text
            product['price'] = self._normalize_price(price_text)
        
        # Extract image
        img_el = card.select_one('img')
        if img_el:
            product['image_url'] = img_el.get('src') or img_el.get('data-src', '')
            if not product['name'] and img_el.get('alt'):
                product['name'] = img_el.get('alt')
        
        # Extract link
        link_el = card.select_one('a')
        if link_el:
            href = link_el.get('href', '')
            if href.startswith('/'):
                product['product_url'] = f"https://www.wholefoodsmarket.com{href}"
            else:
                product['product_url'] = href
        
        # Extract brand and clean name
        if product['name']:
            brand, cleaned_name = self._extract_brand_from_name(product['name'])
            product['brand'] = brand
            if brand:
                product['name'] = cleaned_name
        
        # Only return if we have at least name and price
        if product['name'] and product['price']:
            return product
        
        return None


class WegmansExtractor(StoreProductExtractor):
    """Extractor for Wegmans.com product cards from search results"""
    
    def extract_products(self, html: str, store_id: str = "wegmans") -> List[Dict[str, Any]]:
        """Extract products from Wegmans search results HTML"""
        products = []
        
        try:
            soup = BeautifulSoup(html, 'html.parser')
            
            # Wegmans search results might be in JSON-LD structured data
            json_ld_scripts = soup.find_all('script', type='application/ld+json')
            for script in json_ld_scripts:
                try:
                    import json
                    data = json.loads(script.string)
                    # Check if it's a product list
                    if isinstance(data, dict) and data.get('@type') == 'ItemList':
                        items = data.get('itemListElement', [])
                        for item in items:
                            if isinstance(item, dict) and item.get('@type') == 'Product':
                                product = self._extract_from_json_ld(item, store_id)
                                if product and self._is_valid_individual_product(product):
                                    products.append(product)
                                elif product:
                                    logger.debug(f"Filtered out invalid Wegmans product: {product.get('name', 'Unknown')[:50]}...")
                except (json.JSONDecodeError, KeyError, TypeError):
                    continue
            
            # Also try to find product cards in HTML
            # Wegmans might use various selectors - try common patterns
            product_selectors = [
                '[class*="product"]',
                '[data-testid*="product"]',
                '[class*="ProductCard"]',
                '[class*="product-card"]',
                '[class*="productTile"]',
                '[class*="product-tile"]',
            ]
            
            for selector in product_selectors:
                cards = soup.select(selector)
                if cards:
                    logger.debug(f"Found {len(cards)} Wegmans product cards with selector: {selector}")
                    for card in cards[:20]:  # Limit to first 20
                        try:
                            product = self._extract_product(card, store_id)
                            if product and self._is_valid_individual_product(product):
                                products.append(product)
                            elif product:
                                logger.debug(f"Filtered out invalid Wegmans product: {product.get('name', 'Unknown')[:50]}...")
                        except Exception as e:
                            logger.debug(f"Failed to extract Wegmans product: {e}")
                            continue
                    if products:
                        break  # If we found products, stop trying other selectors
            
            # Also try to extract from script tags that might contain product data
            script_tags = soup.find_all('script')
            for script in script_tags:
                script_text = script.string or ''
                # Look for product data in JavaScript variables
                if 'product' in script_text.lower() and ('image' in script_text.lower() or 'price' in script_text.lower()):
                    try:
                        # Try to extract JSON-like structures
                        json_matches = re.findall(r'\{[^{}]*"name"[^{}]*"price"[^{}]*\}', script_text, re.IGNORECASE)
                        for match in json_matches[:5]:  # Limit matches
                            try:
                                import json
                                product_data = json.loads(match)
                                if product_data.get('name') or product_data.get('price'):
                                    product = self._extract_from_dict(product_data, store_id)
                                    if product and self._is_valid_individual_product(product):
                                        products.append(product)
                                    elif product:
                                        logger.debug(f"Filtered out invalid Wegmans product: {product.get('name', 'Unknown')[:50]}...")
                            except:
                                continue
                    except Exception:
                        continue
            
        except Exception as e:
            logger.error(f"Failed to parse Wegmans HTML: {e}")
        
        return products
    
    def _extract_product(self, card, store_id: str) -> Optional[Dict[str, Any]]:
        """Extract a single product from Wegmans product card"""
        product = {
            'store_id': store_id,
            'store_name': 'Wegmans',
            'name': None,
            'price': None,
            'price_display': None,
            'price_per_unit': None,
            'image_url': None,
            'product_url': None,
            'availability': 'Check Store'
        }
        
        # Extract product name
        name_el = card.select_one('h3, h2, h4, [class*="title"], [class*="name"], [class*="product-name"]')
        if name_el:
            product['name'] = name_el.get_text(strip=True)
        
        # Also try data attributes
        if not product['name']:
            product['name'] = card.get('data-product-name') or card.get('aria-label')
        
        # Extract price
        price_el = card.select_one('[class*="price"], [class*="Price"], [data-testid*="price"]')
        if price_el:
            price_text = price_el.get_text(strip=True)
            product['price_display'] = price_text
            product['price'] = self._normalize_price(price_text)
        
        # Also try data attributes for price
        if not product['price']:
            price_attr = card.get('data-price') or card.get('data-product-price')
            if price_attr:
                product['price'] = self._normalize_price(price_attr)
                product['price_display'] = f"${product['price']:.2f}" if product['price'] else None
        
        # Extract image
        img_el = card.select_one('img')
        if img_el:
            src = img_el.get('src') or img_el.get('data-src') or img_el.get('data-lazy-src')
            if src:
                # Resolve relative URLs
                if src.startswith('//'):
                    src = 'https:' + src
                elif src.startswith('/'):
                    src = f"https://www.wegmans.com{src}"
                
                # Exclude logo images
                if src and 'wegmans-og-share-img' not in src.lower() and '53100' not in src:
                    product['image_url'] = src
                
                # Use alt text for name if name not found
                if not product['name'] and img_el.get('alt'):
                    product['name'] = img_el.get('alt')
        
        # Extract product URL/link - Wegmans product pages are at /shop/product/{id}-{name}
        # These links are in the product cards and lead to actual product pages (not modals)
        link_el = card.select_one('a[href*="/shop/product/"], a[href*="/product/"]')
        if link_el:
            href = link_el.get('href', '')
            if href.startswith('/'):
                product['product_url'] = f"https://www.wegmans.com{href}"
            elif href.startswith('http'):
                product['product_url'] = href
        
        # Also check if the card itself is a link
        if not product['product_url'] and card.name == 'a':
            href = card.get('href', '')
            if '/shop/product/' in href or '/product/' in href:
                if href.startswith('/'):
                    product['product_url'] = f"https://www.wegmans.com{href}"
                elif href.startswith('http'):
                    product['product_url'] = href
        
        # Also try data attributes for product URL
        if not product['product_url']:
            url_attr = card.get('data-product-url') or card.get('data-href') or card.get('href') or card.get('data-url')
            if url_attr:
                if '/shop/product/' in str(url_attr) or '/product/' in str(url_attr):
                    if str(url_attr).startswith('/'):
                        product['product_url'] = f"https://www.wegmans.com{url_attr}"
                    elif str(url_attr).startswith('http'):
                        product['product_url'] = url_attr
        
        # Try to find product ID in data attributes and construct URL
        if not product['product_url']:
            product_id = card.get('data-product-id') or card.get('data-id') or card.get('id')
            if product_id and product['name']:
                # Construct URL from product ID and name
                # Format: /shop/product/{id}-{name-slug}
                name_slug = re.sub(r'[^a-z0-9]+', '-', product['name'].lower()).strip('-')
                product['product_url'] = f"https://www.wegmans.com/shop/product/{product_id}-{name_slug}"
        
        # Extract brand and clean name
        if product['name']:
            brand, cleaned_name = self._extract_brand_from_name(product['name'])
            product['brand'] = brand
            if brand:
                product['name'] = cleaned_name
        
        # Only return if we have at least name
        if product['name']:
            return product
        
        return None
    
    def _extract_from_json_ld(self, item: Dict[str, Any], store_id: str) -> Optional[Dict[str, Any]]:
        """Extract product from JSON-LD structured data"""
        product = {
            'store_id': store_id,
            'store_name': 'Wegmans',
            'name': item.get('name'),
            'price': None,
            'price_display': None,
            'image_url': None,
            'product_url': item.get('url'),
            'availability': 'Check Store'
        }
        
        # Extract price
        offers = item.get('offers', {})
        if isinstance(offers, dict):
            price = offers.get('price')
            if price:
                product['price'] = float(price) if isinstance(price, (int, float)) else self._normalize_price(str(price))
                product['price_display'] = f"${product['price']:.2f}" if product['price'] else None
        
        # Extract image
        image = item.get('image')
        if image:
            if isinstance(image, list) and len(image) > 0:
                image = image[0]
            if isinstance(image, dict):
                image = image.get('url') or image.get('@id')
            if isinstance(image, str) and 'wegmans-og-share-img' not in image.lower() and '53100' not in image:
                product['image_url'] = image
        
        return product if product['name'] else None
    
    def _extract_from_dict(self, data: Dict[str, Any], store_id: str) -> Optional[Dict[str, Any]]:
        """Extract product from dictionary data"""
        product = {
            'store_id': store_id,
            'store_name': 'Wegmans',
            'name': data.get('name') or data.get('title'),
            'price': self._normalize_price(data.get('price')) if data.get('price') else None,
            'price_display': data.get('price_display') or (f"${data.get('price'):.2f}" if data.get('price') else None),
            'image_url': data.get('image') or data.get('image_url'),
            'product_url': data.get('url') or data.get('product_url'),
            'availability': 'Check Store'
        }
        
        return product if product['name'] else None


class SafewayExtractor(StoreProductExtractor):
    """Extractor for Safeway.com product cards"""
    
    def extract_products(self, html: str, store_id: str = "safeway") -> List[Dict[str, Any]]:
        """Extract products from Safeway HTML"""
        products = []
        
        try:
            soup = BeautifulSoup(html, 'html.parser')
            
            # Find product cards
            product_cards = soup.select('[class*="ProductCard"], [class*="product-card"], [class*="product-item"]')
            
            logger.debug(f"Found {len(product_cards)} Safeway product cards")
            
            for card in product_cards:
                try:
                    product = self._extract_product(card, store_id)
                    if product and self._is_valid_individual_product(product):
                        products.append(product)
                    elif product:
                        logger.debug(f"Filtered out invalid Safeway product: {product.get('name', 'Unknown')[:50]}...")
                except Exception as e:
                    logger.warning(f"Failed to extract Safeway product: {e}")
                    continue
            
        except Exception as e:
            logger.error(f"Failed to parse Safeway HTML: {e}")
        
        return products
    
    def _extract_product(self, card, store_id: str) -> Optional[Dict[str, Any]]:
        """Extract a single product from Safeway product card"""
        product = {
            'store_id': store_id,
            'store_name': 'Safeway',
            'name': None,
            'price': None,
            'price_display': None,
            'price_per_unit': None,
            'image_url': None,
            'product_url': None,
            'availability': 'Check Store'
        }
        
        # Extract product name
        name_el = card.select_one('h3, h2, [class*="title"], [class*="name"], [class*="product-name"]')
        if name_el:
            product['name'] = name_el.get_text(strip=True)
        
        # Extract price
        price_el = card.select_one('[class*="price"], [class*="Price"], [data-testid*="price"]')
        if price_el:
            price_text = price_el.get_text(strip=True)
            product['price_display'] = price_text
            product['price'] = self._normalize_price(price_text)
        
        # Extract image
        img_el = card.select_one('img')
        if img_el:
            product['image_url'] = img_el.get('src') or img_el.get('data-src', '')
            if not product['name'] and img_el.get('alt'):
                product['name'] = img_el.get('alt')
        
        # Extract link
        link_el = card.select_one('a')
        if link_el:
            href = link_el.get('href', '')
            if href.startswith('/'):
                product['product_url'] = f"https://www.safeway.com{href}"
            else:
                product['product_url'] = href
        
        # Extract brand and clean name
        if product['name']:
            brand, cleaned_name = self._extract_brand_from_name(product['name'])
            product['brand'] = brand
            if brand:
                product['name'] = cleaned_name
        
        # Only return if we have at least name and price
        if product['name'] and product['price']:
            return product
        
        return None


class CostcoExtractor(StoreProductExtractor):
    """Extractor for Costco.com product cards"""
    
    def extract_products(self, html: str, store_id: str = "costco") -> List[Dict[str, Any]]:
        """Extract products from Costco HTML"""
        products = []
        
        try:
            soup = BeautifulSoup(html, 'html.parser')
            
            # Find product list container
            product_list = soup.select_one('#productList')
            if not product_list:
                logger.debug("No #productList found in Costco HTML")
                return products
            
            # Find product cards - Costco uses MuiGrid2-grid-xs-4 (updated from grid-xs-3)
            product_cards = product_list.select('> div[class*="MuiGrid2-grid-xs-4"]')
            
            # Fallback: try grid-xs-3 for older pages
            if not product_cards:
                product_cards = product_list.select('> div[class*="MuiGrid2-grid-xs-3"]')
            
            # Fallback: try finding by data-testid
            if not product_cards:
                product_cards = soup.select('[data-testid^="ProductTile_"]')
            
            logger.debug(f"Found {len(product_cards)} Costco product cards")
            
            for card in product_cards:
                try:
                    product = self._extract_product(card, store_id)
                    if product and self._is_valid_individual_product(product):
                        products.append(product)
                    elif product:
                        logger.debug(f"Filtered out invalid Costco product: {product.get('name', 'Unknown')[:50]}...")
                except Exception as e:
                    logger.warning(f"Failed to extract Costco product: {e}")
                    continue
            
        except Exception as e:
            logger.error(f"Failed to parse Costco HTML: {e}")
        
        return products
    
    def _extract_product(self, card, store_id: str) -> Optional[Dict[str, Any]]:
        """Extract a single product from Costco product card"""
        product = {
            'store_id': store_id,
            'store_name': 'Costco',
            'name': None,
            'price': None,
            'price_display': None,
            'price_per_unit': None,
            'size': None,
            'image_url': None,
            'product_url': None,
            'rating': None,
            'review_count': None,
            'availability': 'Check Store',
            'product_id': None
        }
        
        # Extract product ID from data-testid
        testid = card.get('data-testid', '')
        if testid and 'ProductTile_' in testid:
            # Extract ID from "ProductTile_4000200872"
            match = re.search(r'ProductTile_(\d+)', testid)
            if match:
                product['product_id'] = match.group(1)
        
        # Extract product name - try h3 with ProductTile title ID first
        if product['product_id']:
            name_el = card.select_one(f'h3#ProductTile_{product["product_id"]}_title')
            if name_el:
                product['name'] = name_el.get_text(strip=True)
        
        # Fallback: try h3 with id containing ProductTile and title
        if not product['name']:
            name_el = card.select_one('h3[id*="ProductTile"][id*="title"]')
            if name_el:
                product['name'] = name_el.get_text(strip=True)
        
        # Fallback: extract from card text (first line usually has product name)
        if not product['name']:
            card_text_lines = card.get_text().split('\n')
            for line in card_text_lines:
                line = line.strip()
                if line and len(line) > 10 and not line.startswith('$'):
                    product['name'] = line
                    break
        
        # Extract product URL - Costco uses .product. in URL format, not /product/
        # Example: https://www.costco.com/kirkland-signature-paper-towels-2-ply-160-sheets-12-individually-wrapped-rolls.product.100234271.html
        link_el = card.select_one('a[href*=".product."]')
        if not link_el:
            # Fallback: find first link that's not a delivery badge
            all_links = card.select('a')
            for link in all_links:
                href = link.get('href', '')
                if href and '.product.' in href:
                    link_el = link
                    break
                # Also exclude delivery/grocery links
                if href and not any(x in href for x in ['all-costco-grocery', 'grocery-household']):
                    link_el = link
                    break
        
        if link_el:
            href = link_el.get('href', '')
            if href.startswith('/'):
                product['product_url'] = f"https://www.costco.com{href}"
            elif href.startswith('http'):
                product['product_url'] = href
            else:
                product['product_url'] = f"https://www.costco.com/{href}"
            
            # Extract name from link if not already found
            if not product['name']:
                product['name'] = link_el.get_text(strip=True) or link_el.get('aria-label', '').strip()
            
            # Note: Product detail pages don't need zipcode, but search pages do
            # The zipcode is already handled in the Exa client when processing search URLs
        
        # Extract price - try MuiTypography-t5 class first
        price_el = card.select_one('.MuiTypography-t5')
        if price_el:
            price_text = price_el.get_text(strip=True)
            if '$' in price_text:
                product['price_display'] = price_text
                product['price'] = self._normalize_price(price_text)
        
        # Get card text for multiple extractions
        card_text = card.get_text()
        
        # Fallback: use regex on card text content for price
        if not product['price']:
            price_match = re.search(r'\$[\d,]+\.?\d*', card_text)
            if price_match:
                price_text = price_match.group(0)
                product['price_display'] = price_text
                product['price'] = self._normalize_price(price_text)
        
        # Check for "Members Only" - if found and no price, mark availability
        if 'Members Only' in card_text and not product['price']:
            product['availability'] = 'Members Only'
        
        # Extract image - look for Costco CDN images
        img_el = card.select_one('img[src*="bfasset.costco-static.com"]')
        if img_el:
            product['image_url'] = img_el.get('src', '')
            # Use alt text for name if name not found
            if not product['name'] and img_el.get('alt'):
                product['name'] = img_el.get('alt')
        
        # Fallback: try any img with data-testid containing ProductImage
        if not product['image_url']:
            img_container = card.select_one('[data-testid*="ProductImage"]')
            if img_container:
                img_el = img_container.select_one('img')
                if img_el:
                    product['image_url'] = img_el.get('src', '')
        
        # Extract review count - pattern (XX) or (XX,XXX) with commas
        review_match = re.search(r'\((\d{1,3}(?:,\d{3})*)\)', card_text)
        if review_match:
            try:
                # Remove commas and convert to int
                review_str = review_match.group(1).replace(',', '')
                product['review_count'] = int(review_str)
            except (ValueError, TypeError):
                pass
        
        # Extract rating - look for star ratings (usually 5 stars, but we can try to extract)
        # Costco typically shows full stars, so we'd need to count SVG stars or use review data
        # For now, skip rating extraction as it requires SVG parsing
        
        # Extract size/quantity from name
        if product['name']:
            size_match = re.search(r'(\d+(?:\.\d+)?\s*(?:oz|fl oz|gallon|gal|lb|count|ct|pack|pk))', product['name'], re.IGNORECASE)
            if size_match:
                product['size'] = size_match.group(1)
        
        # Extract brand and clean name
        if product['name']:
            brand, cleaned_name = self._extract_brand_from_name(product['name'])
            product['brand'] = brand
            if brand:
                product['name'] = cleaned_name
        
        # Check for badges that might indicate availability
        badge_el = card.select_one('[data-testid*="PillBadge"]')
        if badge_el:
            badge_text = badge_el.get_text(strip=True)
            if 'Online Only' in badge_text:
                # Online only products are available
                if product['availability'] == 'Check Store':
                    product['availability'] = 'Online Only'
        
        # Only return if we have at least name
        # Price may be missing for "Members Only" products
        if product['name']:
            return product
        
        return None


# Factory function to get the right extractor
def get_extractor(store_id: str) -> StoreProductExtractor:
    """Get the appropriate extractor for a store"""
    extractors = {
        'kroger': KrogerExtractor(),
        'walmart': WalmartExtractor(),
        'target': TargetExtractor(),
        'whole_foods': WholeFoodsExtractor(),
        'whole foods': WholeFoodsExtractor(),
        'safeway': SafewayExtractor(),
        'albertsons': SafewayExtractor(),  # Similar structure
        'wegmans': WegmansExtractor(),
        'costco': CostcoExtractor(),
    }
    
    return extractors.get(store_id.lower(), StoreProductExtractor())

