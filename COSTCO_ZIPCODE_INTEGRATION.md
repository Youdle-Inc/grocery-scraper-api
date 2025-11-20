# Costco Zipcode Integration

## Overview
Ensured that Costco product searches use the user's zipcode to filter products by warehouse/delivery location, ensuring accurate availability and pricing.

## Changes Made

### 1. Enhanced Search Query (`scraper/exa_structured_client.py`)

**Location**: `_build_enhanced_query()` method

Added Costco-specific zipcode handling in the search query builder:

```python
# For Costco, explicitly include zipcode in search to ensure location-based results
# Costco filters products by warehouse/delivery location based on zipcode
if store_name and store_name.lower() == "costco":
    # Costco search URLs can include zipcode parameter: /s?keyword={query}&zipcode={zipcode}
    # This ensures products shown are available for that location
    base_query = f"{base_query} site:costco.com/s?keyword= zipcode {zipcode} warehouse {zipcode}"
```

**Purpose**: 
- Tells Exa to search for Costco pages that include the zipcode
- Ensures search results are location-specific
- Helps Exa find the correct warehouse/delivery location pages

### 2. URL Processing (`scraper/exa_structured_client.py`)

**Location**: `_extract_product_data()` method

Added zipcode parameter injection into Costco search URLs:

```python
# Costco needs zipcode in search URLs to show location-specific products and availability
# Costco filters products by warehouse/delivery location based on zipcode
if zipcode and url and 'costco.com' in url.lower():
    # Add zipcode parameter to Costco search URLs
    # Format: /s?keyword={query}&zipcode={zipcode}
    if '/s?' in url.lower() or '/s?keyword=' in url.lower():
        updated_url = self._add_or_replace_query_param(url, "zipcode", zipcode)
        if updated_url != url:
            logger.debug(f"🔄 Added Costco zipcode ({zipcode}) to search URL for location-based results")
            url = updated_url
```

**Purpose**:
- Automatically adds `zipcode={zipcode}` parameter to Costco search URLs
- Ensures when we scrape Costco search pages, they're filtered by location
- Similar to how Wegmans URLs get store context added

### 3. CostcoExtractor Notes (`scraper/store_extractors.py`)

Added documentation note that zipcode handling is done at the Exa client level:

```python
# Note: Product detail pages don't need zipcode, but search pages do
# The zipcode is already handled in the Exa client when processing search URLs
```

## How It Works

### Flow:
1. **User Request**: User searches for products with zipcode (e.g., `query=eggs&zipcode=60601&stores=costco`)

2. **Search Query Building**: 
   - Exa client builds enhanced query with Costco-specific zipcode context
   - Query includes: `eggs costco site:costco.com/s?keyword= zipcode 60601 warehouse 60601`

3. **Exa Search**: 
   - Exa searches for Costco pages matching the query
   - Results include Costco search pages and product pages

4. **URL Processing**:
   - When processing results, if URL is a Costco search page (`/s?keyword=`), zipcode parameter is added
   - Example: `https://www.costco.com/s?keyword=eggs` → `https://www.costco.com/s?keyword=eggs&zipcode=60601`

5. **Product Extraction**:
   - CostcoExtractor extracts products from search result pages
   - Products shown are filtered by the zipcode (warehouse/delivery location)

## Benefits

1. **Accurate Availability**: Products shown are actually available at/near the user's zipcode
2. **Correct Pricing**: Prices reflect the warehouse/delivery location for that zipcode
3. **Better User Experience**: Users see products they can actually purchase
4. **Location-Specific Results**: Different warehouses may have different products/prices

## Testing

To verify zipcode integration works:

1. **Test Search**: 
   ```bash
   curl "http://localhost:8000/products/aggregate?query=eggs&zipcode=60601&stores=costco&limit=5"
   ```

2. **Check Logs**: Look for log messages:
   - `🔄 Added Costco zipcode (60601) to search URL for location-based results`
   - Search query should include zipcode context

3. **Verify URLs**: Check that product URLs or search URLs include zipcode parameter when appropriate

## Notes

- **Product Detail Pages**: Individual product pages (`/product/{id}.html`) don't need zipcode in URL
- **Search Pages**: Search result pages (`/s?keyword=...`) benefit from zipcode parameter
- **Session/Cookies**: Costco may also use cookies/session to track warehouse, but URL parameter ensures correct results
- **Fallback**: If zipcode isn't provided, Costco will show default/national results

## Future Enhancements

1. **Warehouse Detection**: Could detect nearest Costco warehouse from zipcode and use warehouse ID
2. **Delivery vs Warehouse**: Distinguish between warehouse pickup and delivery options
3. **Availability Checking**: Verify product availability at specific warehouse locations
4. **Price Variation**: Handle price differences between warehouses


