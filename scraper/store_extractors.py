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
                    if product:
                        products.append(product)
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
                    if product:
                        products.append(product)
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
                    if product:
                        products.append(product)
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
                    if product:
                        products.append(product)
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
                    if product:
                        products.append(product)
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
    }
    
    return extractors.get(store_id.lower(), StoreProductExtractor())

