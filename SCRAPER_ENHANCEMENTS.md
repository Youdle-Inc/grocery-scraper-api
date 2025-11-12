# 🚀 Scraper Enhancements - Store-Specific Extractors

## Overview

We've enhanced the grocery scraper with **store-specific HTML extractors** based on real-world analysis of how major grocery stores structure their product data. This makes our scraper **AMAZING** by extracting precise product information using the exact selectors each store uses.

## What We Built

### 1. Store-Specific Extractors (`scraper/store_extractors.py`)

Created specialized extractors for each major grocery store that know exactly how to parse product cards:

- **KrogerExtractor** - Uses `data-testid` attributes for precise extraction
- **WalmartExtractor** - Uses `data-item-id` and aria-labels
- **TargetExtractor** - Uses `data-test` attributes
- **WholeFoodsExtractor** - Uses class-based selectors
- **SafewayExtractor** - Uses class-based selectors

### 2. Enhanced Data Extraction

Each extractor now captures:

✅ **Product Name** - Full product title  
✅ **Brand** - Extracted and separated from product name  
✅ **Price** - Numeric price value  
✅ **Price Display** - Price as displayed (e.g., "$2.79")  
✅ **Price Per Unit** - Unit price (e.g., "$0.02/fl oz")  
✅ **Size/Quantity** - Product size (e.g., "1 gal", "64 fl oz")  
✅ **Variants** - Available sizes/flavors (e.g., "3 more sizes | 6 more flavors")  
✅ **Product Image** - Direct image URL  
✅ **Product Link** - Full product page URL  
✅ **Rating** - Customer rating (when available)  
✅ **Review Count** - Number of reviews (when available)  
✅ **Availability** - Stock status  

## How It Works

### Integration Flow

1. **Exa API Search** - Searches for products using Exa's neural search
2. **Store Detection** - Automatically detects store from URL
3. **Extractor Selection** - Chooses the right extractor for the store
4. **HTML Parsing** - Parses product cards using store-specific selectors
5. **Data Enhancement** - Combines extracted data with Exa summaries
6. **Normalization** - Normalizes data to common format

### Example: Kroger Extraction

```python
# Kroger uses data-testid attributes
product_card = soup.select('[data-testid^="product-card"]')

# Extract price from value attribute
price = card.select_one('[data-testid="product-item-unit-price"]').get('value')

# Extract price per unit
price_per_unit = card.select_one('[data-testid="product-item-sizing"]').get_text()

# Extract variants
variants = card.select_one('[data-testid="product-variant-text"]').get_text()
```

### Example: Walmart Extraction

```python
# Walmart uses data-item-id
product_item = soup.select('[data-item-id]')

# Extract name from button aria-label
name_button = item.select_one('button[aria-label*="Sign in to add to Favorites list"]')
name = re.search(r'Sign in to add to Favorites list,\s*(.+)', aria_label).group(1)

# Extract rating from data-value attribute
rating = item.select_one('[data-testid="product-ratings"]').get('data-value')
```

## Key Features

### 🎯 Precision Extraction
- Uses exact CSS selectors from each store
- Extracts structured data attributes (`data-testid`, `data-value`, etc.)
- Handles store-specific HTML patterns

### 🔄 Fallback Strategy
- Tries store-specific extractor first
- Falls back to standard Exa extraction if extractor fails
- Combines best data from both sources

### 📊 Enhanced Data Fields
- **Price Per Unit**: "$0.02/fl oz", "$/lb"
- **Variants**: "3 more sizes | 6 more flavors"
- **Ratings & Reviews**: Customer ratings and review counts
- **Brand Separation**: Extracts brand from product name

### 🛡️ Robust Error Handling
- Gracefully handles missing fields
- Validates extracted data
- Logs extraction failures for debugging

## Usage

The extractors are automatically used when:
1. Exa returns HTML content from search results
2. The store can be detected from the URL
3. The HTML content is substantial (>500 chars)

### Manual Usage

```python
from scraper.store_extractors import get_extractor

# Get extractor for a store
extractor = get_extractor('kroger')

# Extract products from HTML
products = extractor.extract_products(html_content, 'kroger')

# Each product has:
# - name, brand, price, price_per_unit
# - size, variants, image_url, product_url
# - rating, review_count, availability
```

## Supported Stores

| Store | Extractor | Key Selectors |
|-------|-----------|---------------|
| Kroger | `KrogerExtractor` | `data-testid="product-card-*"` |
| Walmart | `WalmartExtractor` | `data-item-id`, `data-testid="product-ratings"` |
| Target | `TargetExtractor` | `data-test="product-card"` |
| Whole Foods | `WholeFoodsExtractor` | `class*="ProductCard"` |
| Safeway | `SafewayExtractor` | `class*="ProductCard"` |

## Benefits

### 🚀 Performance
- Faster extraction using direct HTML parsing
- No need for multiple API calls per product
- Efficient batch processing

### 🎯 Accuracy
- Uses exact selectors from real store pages
- Extracts structured data attributes
- Handles store-specific patterns

### 📈 Completeness
- Captures more fields (price per unit, variants, ratings)
- Better brand extraction
- More accurate size/quantity parsing

### 🔧 Maintainability
- Store-specific extractors are isolated
- Easy to add new stores
- Clear separation of concerns

## Future Enhancements

- [ ] Add extractors for more stores (ALDI, Costco, Trader Joe's)
- [ ] Support for product detail page extraction
- [ ] Enhanced variant parsing (extract all available sizes/flavors)
- [ ] Image quality optimization
- [ ] Caching of extraction patterns

## Testing

To test the extractors:

```python
# Test Kroger extractor
from scraper.store_extractors import KrogerExtractor

extractor = KrogerExtractor()
# Load HTML from Kroger search results page
with open('kroger_search_results.html', 'r') as f:
    html = f.read()

products = extractor.extract_products(html, 'kroger')
print(f"Extracted {len(products)} products")
for product in products:
    print(f"- {product['name']}: ${product['price']} ({product['price_per_unit']})")
```

## Notes

- Extractors work best with search results pages
- Product detail pages may need different extraction logic
- Some stores may require authentication or have anti-scraping measures
- HTML structure may change over time - extractors should be updated accordingly


