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
        """Extract products from Wegmans search results HTML
        
        Wegmans HTML structure (as of Dec 2024):
        - Products are in a <ul> (list) element
        - Each product is in a <li> (listitem) element
        - Product info is in buttons with aria-labels containing "Price is:"
        - Product name in <h3>, price in "Price is:" text, size before price
        """
        products = []
        
        try:
            soup = BeautifulSoup(html, 'html.parser')
            
            # Primary method: Find product list items
            # Wegmans uses <ul> with <li> elements for product cards
            # Each product card has a button with aria-label containing "Price is:"
            product_lists = soup.select('ul')
            
            for product_list in product_lists:
                # Find all list items that contain product buttons
                list_items = product_list.select('li')
                
                for item in list_items:
                    # Check if this list item contains a product (has "Price is:" in text)
                    item_text = item.get_text()
                    if 'Price is:' not in item_text:
                        continue
                    
                    try:
                        product = self._extract_product(item, store_id)
                        if product and self._is_valid_individual_product(product):
                            products.append(product)
                            logger.debug(f"Extracted Wegmans product: {product.get('name', 'Unknown')[:50]}")
                        elif product:
                            logger.debug(f"Filtered out invalid Wegmans product: {product.get('name', 'Unknown')[:50]}...")
                    except Exception as e:
                        logger.debug(f"Failed to extract Wegmans product from list item: {e}")
                        continue
                
                # If we found products in this list, stop looking
                if products:
                    logger.debug(f"Found {len(products)} Wegmans products from list items")
                    break
            
            # Fallback: Try JSON-LD structured data (may still be present)
            if not products:
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
            
            # Fallback: Try generic product selectors (for older page versions)
            if not products:
                product_selectors = [
                    '[class*="product"]',
                    '[data-testid*="product"]',
                    '[class*="ProductCard"]',
                    '[class*="product-card"]',
                ]
                
                for selector in product_selectors:
                    cards = soup.select(selector)
                    if cards:
                        logger.debug(f"Trying fallback selector: {selector}, found {len(cards)} elements")
                        for card in cards[:20]:  # Limit to first 20
                            # Skip if no "Price is:" in text (not a product card)
                            if 'Price is:' not in card.get_text():
                                continue
                            try:
                                product = self._extract_product(card, store_id)
                                if product and self._is_valid_individual_product(product):
                                    products.append(product)
                            except Exception as e:
                                logger.debug(f"Failed to extract Wegmans product: {e}")
                                continue
                        if products:
                            break  # If we found products, stop trying other selectors
            
            # Fallback: Try to extract from script tags that might contain product data
            if not products:
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
                                except:
                                    continue
                        except Exception:
                            continue
            
            # Final fallback: Try to extract from plain text (Exa returns text content, not HTML)
            # This handles cases where the content is rendered as plain text
            if not products:
                text_products = self._extract_products_from_text(html, store_id)
                if text_products:
                    products.extend(text_products)
                    logger.debug(f"Extracted {len(text_products)} Wegmans products from plain text")
            
            logger.info(f"Extracted {len(products)} products from Wegmans content")
            
        except Exception as e:
            logger.error(f"Failed to parse Wegmans content: {e}")
        
        return products
    
    def _extract_products_from_text(self, text: str, store_id: str) -> List[Dict[str, Any]]:
        """Extract products from plain text content (Exa returns text, not HTML)
        
        Wegmans text structure from Exa:
        - Product blocks separated by product names
        - Each block contains: name, size, "Price is: $X.XX/ea", "Unit price is: ($X.XX/unit)"
        - Rating info: "X.X out of 5 stars. N reviews"
        - Availability: "May not be available", "See Store Associate"
        """
        products = []
        
        # Check if this looks like Wegmans product text
        if 'Price is:' not in text and 'price is:' not in text.lower():
            return products
        
        # Primary approach: Use regex to find product patterns directly
        # Pattern: Product name followed by size followed by price
        # Example: "Wegmans Just Tea Cinnamon Chai Herbal Tea Bags\n20 ct.\nPrice is: $2.99/ea"
        # Allow newlines between components
        product_pattern = re.compile(
            r'([A-Z][^\n$]{5,100}?)\s*\n\s*'  # Product name (starts with capital, 5-100 chars, ends at newline)
            r'(\d+(?:\.\d+)?\s*(?:oz|fl\.?\s*oz|ct|ounce|gallon|gal|lb|pack|pk|count)\.?)\s*\n\s*'  # Size on next line
            r'Price is:\s*\$?([\d,]+\.?\d*)/ea'  # Price
            r'(?:\s*\n?\s*Unit price is:\s*\(([^)]+)\))?',  # Unit price (optional)
            re.IGNORECASE | re.MULTILINE
        )
        
        for match in product_pattern.finditer(text):
            try:
                name = match.group(1).strip()
                size = match.group(2).strip()
                price_str = match.group(3).replace(',', '')
                unit_price = match.group(4).strip() if match.group(4) else None
                
                # Check if name starts with availability indicator (like "May not be available")
                availability = 'In Stock'
                if name.lower().startswith('may not be available'):
                    availability = 'Limited Availability'
                    # Remove the availability prefix from name
                    name = re.sub(r'^may not be available\s*', '', name, flags=re.IGNORECASE).strip()
                elif name.lower().startswith('see store associate'):
                    availability = 'Check Store'
                    name = re.sub(r'^see store associate\s*', '', name, flags=re.IGNORECASE).strip()
                
                price = self._normalize_price(price_str)
                
                if name and price:
                    # Generate a product URL that won't be filtered as a category page
                    # Use /shop/product/ format with a slug based on product name
                    name_slug = re.sub(r'[^a-z0-9]+', '-', name.lower()).strip('-')
                    product = {
                        'store_id': store_id,
                        'store_name': 'Wegmans',
                        'name': name,
                        'price': price,
                        'price_display': f"${price_str}/ea",
                        'price_per_unit': unit_price,
                        'size': size,
                        'image_url': None,
                        'product_url': f"https://www.wegmans.com/shop/product/{name_slug}",
                        'availability': availability,
                        'rating': None,
                        'review_count': None
                    }
                    
                    # Also check surrounding text for availability indicators (if not already set)
                    if availability == 'In Stock':
                        # Only look at text AFTER this product's match up to next product
                        block_end = min(len(text), match.end() + 150)
                        # Find the next product (next "Price is:" occurrence after this one)
                        next_price = text.find('Price is:', match.end())
                        if next_price > 0:
                            block_end = min(block_end, next_price)
                        surrounding_text = text[match.end():block_end]
                        
                        if 'See Store Associate' in surrounding_text:
                            product['availability'] = 'Check Store'
                    
                    # Extract rating if present (look after the price until next product)
                    block_end = min(len(text), match.end() + 150)
                    next_price = text.find('Price is:', match.end())
                    if next_price > 0:
                        block_end = min(block_end, next_price)
                    rating_text = text[match.end():block_end]
                    
                    rating_match_inner = re.search(r'(\d+\.?\d*)\s*out of 5 stars\.?\s*(?:(\d+)\s*reviews?)?', rating_text, re.IGNORECASE)
                    if rating_match_inner:
                        try:
                            product['rating'] = float(rating_match_inner.group(1))
                            if rating_match_inner.group(2):
                                product['review_count'] = int(rating_match_inner.group(2))
                        except (ValueError, TypeError):
                            pass
                    
                    # Extract brand
                    brand, cleaned_name = self._extract_brand_from_name(product['name'])
                    product['brand'] = brand
                    if brand:
                        product['name'] = cleaned_name
                    
                    if self._is_valid_individual_product(product):
                        products.append(product)
            except Exception as e:
                logger.debug(f"Failed to extract product from pattern match: {e}")
                continue
        
        return products
    
    def _extract_product_from_text_block(self, block: str, store_id: str) -> Optional[Dict[str, Any]]:
        """Extract a single product from a text block"""
        product = {
            'store_id': store_id,
            'store_name': 'Wegmans',
            'name': None,
            'price': None,
            'price_display': None,
            'price_per_unit': None,
            'size': None,
            'image_url': None,
            'product_url': None,
            'availability': 'In Stock',
            'rating': None,
            'review_count': None
        }
        
        # Extract price from "Price is: $X.XX/ea"
        price_match = re.search(r'Price is:\s*\$?([\d,]+\.?\d*)/ea', block, re.IGNORECASE)
        if price_match:
            price_str = price_match.group(1).replace(',', '')
            product['price'] = self._normalize_price(price_str)
            product['price_display'] = f"${price_str}/ea"
        
        # Extract unit price from "Unit price is: ($X.XX/unit)"
        unit_price_match = re.search(r'Unit price is:\s*\(([^)]+)\)', block, re.IGNORECASE)
        if unit_price_match:
            product['price_per_unit'] = unit_price_match.group(1).strip()
        
        # Extract size (e.g., "20 ct.", "32 fl. oz.", "8.72 ounce")
        size_match = re.search(r'(\d+(?:\.\d+)?\s*(?:oz|fl\.?\s*oz|ct|ounce|gallon|gal|lb|pack|pk|count)\.?)', block, re.IGNORECASE)
        if size_match:
            product['size'] = size_match.group(1).strip()
        
        # Extract product name - text before the size or price, starting with capital letter
        # Try to find name by looking at text before price
        lines = block.split('\n')
        for line in lines:
            line = line.strip()
            # Skip empty lines, lines with just numbers, price lines, etc.
            if not line or line.startswith('$') or 'Price is:' in line or 'Unit price is:' in line:
                continue
            if re.match(r'^[\d\s.,]+$', line):  # Skip number-only lines
                continue
            if 'out of 5 stars' in line.lower():  # Skip rating lines
                continue
            if len(line) > 10 and line[0].isupper():
                # This could be a product name
                # Clean it up - remove size info if present at end
                name = re.sub(r'\s+\d+(?:\.\d+)?\s*(?:oz|fl\.?\s*oz|ct|ounce|gallon|gal|lb|pack|pk|count)\.?\s*$', '', line, flags=re.IGNORECASE)
                if len(name) > 5:
                    product['name'] = name.strip()
                    break
        
        # Extract availability
        if 'May not be available' in block:
            product['availability'] = 'Limited Availability'
        elif 'See Store Associate' in block:
            product['availability'] = 'Check Store'
        
        # Extract rating and reviews
        rating_match = re.search(r'(\d+\.?\d*)\s*out of 5 stars\.?\s*(?:(\d+)\s*reviews?)?', block, re.IGNORECASE)
        if rating_match:
            try:
                product['rating'] = float(rating_match.group(1))
                if rating_match.group(2):
                    product['review_count'] = int(rating_match.group(2))
            except (ValueError, TypeError):
                pass
        
        # Generate product URL
        if product['name']:
            name_slug = re.sub(r'[^a-z0-9]+', '-', product['name'].lower()).strip('-')
            product['product_url'] = f"https://www.wegmans.com/shop/product/{name_slug}"
        
        # Extract brand
        if product['name']:
            brand, cleaned_name = self._extract_brand_from_name(product['name'])
            product['brand'] = brand
            if brand:
                product['name'] = cleaned_name
        
        # Return only if we have name and price
        if product['name'] and product['price']:
            return product
        
        return None
    
    def _extract_product(self, card, store_id: str) -> Optional[Dict[str, Any]]:
        """Extract a single product from Wegmans product card
        
        Wegmans HTML structure (as of Dec 2024):
        - Product cards are in <li> (listitem) elements
        - Product name is in <h3> heading within <figure>
        - Size/quantity is in a generic element (e.g., "20 ct.")
        - Price is in text with "Price is:" label (e.g., "$2.99/ea")
        - Unit price is in text with "Unit price is:" label (e.g., "($0.15/ct.)")
        - Image is in <figure> element
        - Availability indicators: "May not be available", "See Store Associate"
        - Rating/reviews: "X.X out of 5 stars. N reviews"
        """
        product = {
            'store_id': store_id,
            'store_name': 'Wegmans',
            'name': None,
            'price': None,
            'price_display': None,
            'price_per_unit': None,
            'size': None,
            'image_url': None,
            'product_url': None,
            'availability': 'In Stock',
            'rating': None,
            'review_count': None
        }
        
        # Get the full card text for parsing
        card_text = card.get_text()
        
        # Check if this is a product card by looking for "Price is:" in the text
        if 'Price is:' not in card_text:
            return None
        
        # Extract product name from h3 heading
        name_el = card.select_one('h3')
        if name_el:
            product['name'] = name_el.get_text(strip=True)
        
        # Fallback: Try to extract name from button aria-label
        # Format: "[Product Name] [Size] Price is: $X.XX/ea..."
        if not product['name']:
            button_el = card.select_one('button[aria-label*="Price is:"]')
            if button_el:
                aria_label = button_el.get('aria-label', '')
                # Extract product name (everything before the size/price)
                name_match = re.match(r'^(.+?)\s+\d+(?:\.\d+)?\s*(?:oz|fl\.?\s*oz|ct|ounce|gallon|gal|lb|pack|pk)\.?\s+Price is:', aria_label, re.IGNORECASE)
                if name_match:
                    product['name'] = name_match.group(1).strip()
                else:
                    # Try simpler extraction - everything before "Price is:"
                    simple_match = re.match(r'^(.+?)\s+Price is:', aria_label)
                    if simple_match:
                        product['name'] = simple_match.group(1).strip()
        
        # Extract size/quantity (e.g., "20 ct.", "32 fl. oz.", "8.72 ounce")
        size_match = re.search(r'(\d+(?:\.\d+)?\s*(?:oz|fl\.?\s*oz|ct|ounce|gallon|gal|lb|pack|pk|count)\.?)', card_text, re.IGNORECASE)
        if size_match:
            product['size'] = size_match.group(1).strip()
        
        # Extract price from "Price is:" text (format: "Price is:$X.XX/ea")
        price_match = re.search(r'Price is:\s*\$?([\d,]+\.?\d*)/ea', card_text)
        if price_match:
            price_str = price_match.group(1).replace(',', '')
            product['price'] = self._normalize_price(price_str)
            product['price_display'] = f"${price_str}/ea"
        
        # Extract unit price from "Unit price is:" text (format: "Unit price is:($X.XX/ct.)")
        unit_price_match = re.search(r'Unit price is:\s*\(([^)]+)\)', card_text)
        if unit_price_match:
            product['price_per_unit'] = unit_price_match.group(1).strip()
        
        # Extract image from figure element
        figure_el = card.select_one('figure')
        if figure_el:
            img_el = figure_el.select_one('img')
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
        
        # Fallback: try any img in the card
        if not product['image_url']:
            img_el = card.select_one('img')
            if img_el:
                src = img_el.get('src') or img_el.get('data-src') or img_el.get('data-lazy-src')
                if src:
                    if src.startswith('//'):
                        src = 'https:' + src
                    elif src.startswith('/'):
                        src = f"https://www.wegmans.com{src}"
                    if src and 'wegmans-og-share-img' not in src.lower() and '53100' not in src:
                        product['image_url'] = src
        
        # Extract availability status
        if 'May not be available' in card_text:
            product['availability'] = 'Limited Availability'
        elif 'See Store Associate' in card_text:
            product['availability'] = 'Check Store'
        elif 'Out of stock' in card_text.lower() or 'out of stock' in card_text.lower():
            product['availability'] = 'Out of Stock'
        else:
            product['availability'] = 'In Stock'
        
        # Extract rating and reviews (format: "X.X out of 5 stars. N reviews" or "X.X out of 5 stars.")
        rating_match = re.search(r'(\d+\.?\d*)\s*out of 5 stars\.?\s*(?:(\d+)\s*reviews?)?', card_text, re.IGNORECASE)
        if rating_match:
            try:
                product['rating'] = float(rating_match.group(1))
            except (ValueError, TypeError):
                pass
            if rating_match.group(2):
                try:
                    product['review_count'] = int(rating_match.group(2))
                except (ValueError, TypeError):
                    pass
        
        # Try alternative rating format: "(N)" after star rating
        if not product['review_count']:
            review_count_match = re.search(r'"(\d+\.?\d*)"\s*\((\d+)\)', card_text)
            if review_count_match:
                try:
                    if not product['rating']:
                        product['rating'] = float(review_count_match.group(1))
                    product['review_count'] = int(review_count_match.group(2))
                except (ValueError, TypeError):
                    pass
        
        # Extract product URL/link - Wegmans product pages are at /shop/product/{id}-{name}
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
        
        # Try to construct URL from product name if not found
        if not product['product_url'] and product['name']:
            # Construct URL from product name
            # Format: /shop/product/{name-slug}
            name_slug = re.sub(r'[^a-z0-9]+', '-', product['name'].lower()).strip('-')
            product['product_url'] = f"https://www.wegmans.com/shop/product/{name_slug}"
        
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

