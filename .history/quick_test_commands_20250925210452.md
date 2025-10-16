# Quick Test Commands for Aggregate Endpoint with Addresses

## Basic Tests

### 1. Simple Product Search
```bash
curl -X GET "http://localhost:8000/products/aggregate?query=organic%20milk&zipcode=10001" \
  -H "Accept: application/json" | jq '.'
```

### 2. Search with Specific Stores
```bash
curl -X GET "http://localhost:8000/products/aggregate?query=avocado&zipcode=90210&stores=whole_foods,trader_joes" \
  -H "Accept: application/json" | jq '.'
```

### 3. Enhanced Search (with Exa)
```bash
curl -X GET "http://localhost:8000/products/aggregate?query=coffee&zipcode=60601&enhance=true" \
  -H "Accept: application/json" | jq '.'
```

### 4. Different Location
```bash
curl -X GET "http://localhost:8000/products/aggregate?query=bread&zipcode=94102" \
  -H "Accept: application/json" | jq '.'
```

### 5. Force Refresh
```bash
curl -X GET "http://localhost:8000/products/aggregate?query=bananas&zipcode=10001&refresh=true" \
  -H "Accept: application/json" | jq '.'
```

## Address-Specific Tests

### 6. Check Address Fields Only
```bash
curl -X GET "http://localhost:8000/products/aggregate?query=eggs&zipcode=10001" \
  -H "Accept: application/json" | jq '.results[0].offers[] | {store_name, store_id, address, price}'
```

### 7. Verify All Offers Have Addresses
```bash
curl -X GET "http://localhost:8000/products/aggregate?query=apples&zipcode=10001" \
  -H "Accept: application/json" | jq '.results[] | {canonical_product: .canonical_product.name, offers: [.offers[] | {store_name, address}]}'
```

## Service Health Checks

### 8. Health Check
```bash
curl -X GET "http://localhost:8000/health" \
  -H "Accept: application/json" | jq '.'
```

### 9. Store Discovery
```bash
curl -X GET "http://localhost:8000/sonar/stores/10001" \
  -H "Accept: application/json" | jq '.'
```

### 10. Sonar Status
```bash
curl -X GET "http://localhost:8000/sonar/status" \
  -H "Accept: application/json" | jq '.'
```

## Expected Response Structure

The response should now include address information in each offer:

```json
{
  "query": "organic milk",
  "zipcode": "10001",
  "stores_considered": ["whole_foods", "trader_joes"],
  "results": [
    {
      "canonical_product": {
        "name": "Organic Whole Milk",
        "brand": "Horizon",
        "size": "1 gallon",
        "images": ["https://example.com/milk.jpg"]
      },
      "offers": [
        {
          "store_id": "whole_foods",
          "store_name": "Whole Foods Market",
          "price": "$4.99",
          "availability": "In Stock",
          "product_url": "https://wholefoods.com/milk",
          "source": ["perplexity_sonar"],
          "address": "123 Main St, New York, NY 10001"
        }
      ]
    }
  ],
  "source": "aggregate(sonar)",
  "cache": {"hit": false}
}
```

## Notes

- Make sure your API is running on `localhost:8000`
- Ensure you have the required API keys configured (PERPLEXITY_API_KEY, EXA_API_KEY)
- The `address` field will be populated when store details are successfully retrieved from Sonar
- If address fetching fails, the field will be empty but the endpoint will still work
- Use `jq` for better JSON formatting (install with `brew install jq` on macOS)
