# Exa Migration Guide

## Overview

This API has been migrated from Perplexity Sonar to **Exa Search API** for more reliable and structured grocery product data.

## What Changed

### ✅ New Features
- **Structured Data Extraction**: All product data now includes:
  - Product name, brand, price, currency
  - Quantity/size (e.g., "1 gallon", "64 oz")
  - Product images (primary + additional)
  - Store information (name, address, city, state, ZIP code)
  - Availability status
  - Product URLs
  
- **Improved Accuracy**: Exa's structured extraction provides more consistent and reliable data
- **Better Image Quality**: Multiple product images with higher quality
- **Location Data**: Every product includes store location details

### 🔄 Updated Endpoints

| Old Endpoint | New Endpoint | Changes |
|-------------|-------------|---------|
| `/sonar/stores/{zipcode}` | `/stores/{zipcode}` | Now uses Exa for store discovery |
| `/sonar/products/search` | `/products/search` | Structured data with all required fields |
| `/products/aggregate` | `/products/aggregate` | Enhanced with store addresses and complete product info |

### ❌ Removed Endpoints
- `/sonar/test/{zipcode}` - No longer needed
- `/sonar/store/{store_name}/details` - Merged into main endpoints
- `/sonar/status` - Removed (Sonar no longer used)
- `/exa/products/search` - Merged into `/products/search`

## API Usage Examples

### 1. Search Products

```bash
curl "http://localhost:8000/products/search?query=oat%20milk&store_name=Target&zipcode=10001&num_results=20"
```

**Response includes:**
```json
{
  "query": "oat milk",
  "store_name": "Target",
  "location": "10001",
  "products_found": 15,
  "products": [
    {
      "name": "Oatly Original Oat Milk",
      "brand": "Oatly",
      "price": 4.99,
      "currency": "USD",
      "quantity": "64 fl oz",
      "availability": "In Stock",
      "image_url": "https://...",
      "product_url": "https://...",
      "store_name": "Target",
      "store_address": "123 Main St, New York, NY 10001",
      "store_zipcode": "10001",
      "store_city": "New York",
      "store_state": "NY",
      "source": "exa_structured"
    }
  ],
  "source": "exa_structured",
  "api_version": "2.0.0"
}
```

### 2. Aggregate Search Across Stores

```bash
curl "http://localhost:8000/products/aggregate?query=organic%20milk&zipcode=10001"
```

**Response includes:**
```json
{
  "query": "organic milk",
  "zipcode": "10001",
  "stores_considered": ["target", "walmart", "whole_foods", "kroger", "aldi"],
  "results": [
    {
      "canonical_product": {
        "name": "Organic Whole Milk",
        "brand": "Horizon",
        "quantity": "1 gallon",
        "images": ["https://...", "https://..."],
        "description": "Organic whole milk from pasture-raised cows"
      },
      "offers": [
        {
          "store_id": "target",
          "store_name": "Target",
          "price": 5.99,
          "currency": "USD",
          "quantity": "1 gallon",
          "availability": "In Stock",
          "product_url": "https://...",
          "image_url": "https://...",
          "address": "123 Main St",
          "city": "New York",
          "state": "NY",
          "zipcode": "10001"
        },
        {
          "store_id": "walmart",
          "store_name": "Walmart",
          "price": 5.49,
          ...
        }
      ]
    }
  ]
}
```

### 3. Find Stores

```bash
curl "http://localhost:8000/stores/10001?store_chain=Target"
```

## Required Environment Variables

```bash
# Required
EXA_API_KEY=your_exa_api_key_here

# Optional (for caching)
REDIS_HOST=localhost
REDIS_PORT=6379

# CORS (optional)
CORS_ALLOW_ORIGINS=*
```

## Data Fields Reference

### Product Fields
- `name` (string): Product name
- `brand` (string): Brand name
- `price` (number): Price in USD
- `currency` (string): Currency code (default: "USD")
- `quantity` (string): Product size/quantity (e.g., "1 gallon", "64 oz", "12 pack")
- `availability` (string): Stock status
- `image_url` (string): Primary product image URL
- `additional_images` (array): Additional product images
- `product_url` (string): Link to product page
- `description` (string): Product description
- `category` (string): Product category
- `rating` (number): Customer rating (1-5)
- `reviews_count` (number): Number of reviews

### Store Fields
- `store_name` (string): Store name
- `store_address` (string): Full street address
- `store_city` (string): City
- `store_state` (string): State abbreviation
- `store_zipcode` (string): ZIP code

## Testing

Run the test script to verify your Exa API key and test the functionality:

```bash
python test_exa_structured.py
```

## Migration Notes

### If you were using the old API:

1. **Update your API keys**: Remove `PERPLEXITY_API_KEY` and add `EXA_API_KEY`
2. **Update endpoint URLs**: Use the new endpoint paths
3. **Update response parsing**: The response structure now includes more fields
4. **Check data fields**: `quantity` field is now separate from `size`

### Benefits of Migration:

- ✅ **More structured data**: Consistent JSON schemas
- ✅ **Better image quality**: Multiple high-quality product images
- ✅ **Complete store info**: Every product includes store location
- ✅ **Improved accuracy**: Exa's AI-powered extraction
- ✅ **Faster responses**: Optimized caching and concurrent queries

## Support

For issues or questions:
1. Check your `EXA_API_KEY` is set correctly
2. Review the API documentation at `/docs`
3. Run the test script: `python test_exa_structured.py`
4. Check logs for detailed error messages

