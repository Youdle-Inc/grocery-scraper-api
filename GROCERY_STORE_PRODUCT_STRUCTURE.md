# Grocery Store Product Data Structure Analysis

This document outlines how major grocery stores structure and display product information after a search query. This analysis informs how we should extract product data in our scraper.

## Common Product Data Fields Across Stores

Based on analysis of Kroger, Walmart, Target, Whole Foods, and Safeway, here are the common fields that should be extracted:

### Core Product Information
1. **Product Name** - Full product name/title
2. **Price** - Current price (often includes sale price)
3. **Price Per Unit** - Unit price (e.g., "$0.02/fl oz", "$/lb")
4. **Size/Quantity** - Product size (e.g., "1 gal", "64 fl oz", "Half Gallon")
5. **Brand** - Brand name (e.g., "Kroger®", "Great Value", "Horizon Organic")
6. **Product Image** - Product image URL
7. **Product Link** - Direct link to product page
8. **Variants** - Available sizes/flavors (e.g., "3 more sizes | 6 more flavors")
9. **Rating** - Customer rating (if available)
10. **Review Count** - Number of reviews (if available)
11. **Availability** - In-stock status
12. **SKU/Product ID** - Unique product identifier

## Store-Specific Structures

### 1. Kroger (kroger.com)

**Product Card Selector:** `[data-testid^="product-card"]`

**Data Structure:**
```javascript
{
  name: "Kroger® 2% Reduced Fat Milk Gallon",
  price: "2.79",  // from [data-testid="product-item-unit-price"] value attribute
  pricePerUnit: "$0.02/fl oz",  // from [data-testid="product-item-sizing"]
  size: "1 gal |",  // from [data-testid="product-item-sizing"]
  variants: "3 more sizes | 6 more flavors",  // from [data-testid="product-variant-text"]
  image: "https://www.kroger.com/product/images/medium/front/0001111041700",
  imageAlt: "Kroger® 2% Reduced Fat Milk Gallon",
  link: "/p/kroger-2-reduced-fat-milk-gallon/0001111041700?fulfillment=PICKUP",
  ariaLabel: "Kroger® 2% Reduced Fat Milk Gallon"  // from product card aria-label
}
```

**Key Selectors:**
- Product cards: `[data-testid^="product-card"]`
- Price: `[data-testid="product-item-unit-price"]` (has `value` attribute)
- Price per unit: `[data-testid="product-item-sizing"]` (first occurrence)
- Size: `[data-testid="product-item-sizing"]` (second occurrence)
- Variants: `[data-testid="product-variant-text"]`
- Image: `[data-testid="product-image-loaded"]`
- Product name: `aria-label` attribute on product card

**Notes:**
- Uses structured data attributes (`data-testid`)
- Price stored in `value` attribute of price element
- Product name available in `aria-label` on card
- Variants indicate additional sizes/flavors available

---

### 2. Walmart (walmart.com)

**Product Card Selector:** `[data-item-id]`

**Data Structure:**
```javascript
{
  name: "Almond Breeze Original Almond Milk, 64 oz",
  price: "$3.48current price $3.48",  // from price element text
  pricePerUnit: "12.4 ¢/fl oz",  // sometimes included in price text
  rating: "4.5",  // from [data-testid="product-ratings"] data-value attribute
  reviews: "343",  // from [data-testid="product-reviews"] data-value attribute
  image: "https://i5.walmartimages.com/seo/...",
  link: "https://www.walmart.com/ip/...",
  itemId: "43982130"  // from data-item-id attribute
}
```

**Key Selectors:**
- Product items: `[data-item-id]`
- Product name: Extracted from `button[aria-label*="Sign in to add to Favorites list"]` aria-label
- Price: `[data-automation-id="product-price"]` or `[class*="price"]`
- Rating: `[data-testid="product-ratings"]` (has `data-value` attribute)
- Reviews: `[data-testid="product-reviews"]` (has `data-value` attribute)
- Image: `img` tag within product item
- Link: `a[href*="/ip/"]`

**Notes:**
- Product name embedded in button aria-label: "Sign in to add to Favorites list, PRODUCT NAME"
- Uses `data-item-id` for unique product identification
- Rating and review count stored in `data-value` attributes
- Price may include unit price in the same text

---

### 3. Target (target.com)

**Product Card Selector:** Various (needs investigation)

**Data Structure:**
```javascript
{
  name: "Product Name",
  price: "$X.XX",
  pricePerUnit: "$X.XX/unit",
  rating: "X.X",
  image: "https://...",
  link: "/p/..."
}
```

**Key Selectors:**
- Product cards: `[data-test="product-card"]` (may vary)
- Product name: `[data-test="product-title"]`
- Price: `[data-test="product-price"]`
- Price per unit: `[data-test="product-price-per-unit"]`
- Rating: `[data-test="product-rating"]`
- Image: `img` tag
- Link: `a[href*="/p/"]`

**Notes:**
- Uses `data-test` attributes for testing/automation
- Structure similar to other stores but selectors may differ

---

### 4. Whole Foods (wholefoodsmarket.com)

**Product Card Selector:** `[class*="ProductCard"]`, `article`

**Data Structure:**
```javascript
{
  name: "Product Name",
  price: "$X.XX",
  pricePerUnit: "$X.XX/unit",
  image: "https://...",
  link: "/products/..."
}
```

**Key Selectors:**
- Product cards: `[class*="ProductCard"]`, `article`
- Product name: `h3`, `h2`, `[class*="title"]`
- Price: `[class*="price"]`, `[class*="Price"]`
- Image: `img` tag
- Link: `a` tag

**Notes:**
- Uses class-based selectors
- May require more flexible extraction

---

### 5. Safeway (safeway.com)

**Product Card Selector:** Various (needs investigation)

**Data Structure:**
```javascript
{
  name: "Product Name",
  price: "$X.XX",
  pricePerUnit: "$X.XX/unit",
  image: "https://...",
  link: "/shop/..."
}
```

**Key Selectors:**
- Product cards: `[class*="ProductCard"]`, `[class*="product-card"]`
- Product name: `h3`, `h2`, `[class*="title"]`
- Price: `[class*="price"]`, `[data-testid*="price"]`
- Image: `img` tag
- Link: `a` tag

**Notes:**
- Similar structure to other stores
- May require store-specific extraction logic

---

## Recommended Data Extraction Strategy

### Universal Extraction Pattern

For each store, extract the following fields:

```python
{
    "name": str,              # Product full name
    "brand": str,             # Brand name (extracted from name or separate field)
    "price": float,           # Current price (numeric)
    "price_display": str,     # Price as displayed (e.g., "$2.79")
    "price_per_unit": str,    # Unit price (e.g., "$0.02/fl oz")
    "size": str,              # Product size (e.g., "1 gal", "64 fl oz")
    "quantity": str,          # Quantity/package info
    "image_url": str,         # Product image URL
    "product_url": str,       # Full product page URL
    "variants": str,          # Available variants (sizes/flavors)
    "rating": float,          # Customer rating (if available)
    "review_count": int,      # Number of reviews (if available)
    "availability": str,      # In-stock status
    "sku": str,               # Product SKU/ID
    "store": str,             # Store name
    "store_id": str           # Store identifier
}
```

### Extraction Priority

1. **High Priority (Always Extract):**
   - Product name
   - Price
   - Product image
   - Product link

2. **Medium Priority (Extract if Available):**
   - Price per unit
   - Size/quantity
   - Brand
   - Variants

3. **Low Priority (Nice to Have):**
   - Rating
   - Review count
   - Availability status
   - SKU

### Store-Specific Extraction Functions

Each store should have its own extraction function that:
1. Identifies product cards using store-specific selectors
2. Extracts fields using store-specific selectors
3. Normalizes data to common format
4. Handles edge cases (missing fields, different formats)

### Data Normalization

After extraction, normalize:
- **Price**: Convert to float, handle currency symbols
- **Price per unit**: Standardize format (e.g., "$/fl oz", "$/lb")
- **Size**: Normalize units (e.g., "gal" → "gallon", "fl oz" → "fluid ounces")
- **Brand**: Extract from product name or separate field
- **Product name**: Clean and normalize (remove extra whitespace, special characters)

## Implementation Recommendations

1. **Use Store-Specific Extractors**: Each store has unique HTML structure, so create separate extraction functions
2. **Fallback Selectors**: Use multiple selector strategies per field to handle changes
3. **Data Validation**: Validate extracted data (e.g., price is numeric, image URL is valid)
4. **Error Handling**: Handle missing fields gracefully
5. **Caching**: Cache extraction patterns and selectors per store
6. **Testing**: Test extraction with real search results from each store

## Example Extraction Code Structure

```python
class ProductExtractor:
    def __init__(self, store_id: str):
        self.store_id = store_id
        self.selectors = self._get_selectors(store_id)
    
    def extract_products(self, html: str) -> List[Dict]:
        """Extract products from HTML"""
        soup = BeautifulSoup(html, 'html.parser')
        product_cards = self._find_product_cards(soup)
        
        products = []
        for card in product_cards:
            product = {
                'name': self._extract_name(card),
                'price': self._extract_price(card),
                'price_per_unit': self._extract_price_per_unit(card),
                'size': self._extract_size(card),
                'image_url': self._extract_image(card),
                'product_url': self._extract_link(card),
                'store': self.store_id
            }
            products.append(product)
        
        return products
    
    def _get_selectors(self, store_id: str) -> Dict:
        """Get store-specific selectors"""
        selectors = {
            'kroger': {
                'product_card': '[data-testid^="product-card"]',
                'name': 'aria-label',
                'price': '[data-testid="product-item-unit-price"]',
                'price_per_unit': '[data-testid="product-item-sizing"]',
                'image': '[data-testid="product-image-loaded"]',
                'link': 'a[href*="/p/"]'
            },
            'walmart': {
                'product_card': '[data-item-id]',
                'name': 'button[aria-label*="Sign in to add to Favorites list"]',
                'price': '[data-automation-id="product-price"]',
                'rating': '[data-testid="product-ratings"]',
                'image': 'img',
                'link': 'a[href*="/ip/"]'
            },
            # ... other stores
        }
        return selectors.get(store_id, {})
```

## Next Steps

1. Implement store-specific extractors for each major grocery store
2. Test extraction with real search results
3. Normalize extracted data to common format
4. Handle edge cases and missing data
5. Add validation and error handling
6. Optimize extraction performance

