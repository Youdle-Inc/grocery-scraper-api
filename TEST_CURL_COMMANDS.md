# Curl Commands for Testing Grocery Scraper API

Base URL: `https://grocery-scraper-api.vercel.app`

## 1. Health Check

```bash
# Basic health check
curl https://grocery-scraper-api.vercel.app/health

# Pretty print JSON response
curl https://grocery-scraper-api.vercel.app/health | jq
```

## 2. API Information

```bash
# Get API information
curl https://grocery-scraper-api.vercel.app/api

# Pretty print JSON response
curl https://grocery-scraper-api.vercel.app/api | jq
```

## 3. Find Stores by ZIP Code

```bash
# Find all stores in ZIP code 60601 (Chicago)
curl "https://grocery-scraper-api.vercel.app/stores/60601"

# Find only Target stores in ZIP code 60601
curl "https://grocery-scraper-api.vercel.app/stores/60601?store_chain=Target"

# Find Walmart stores in ZIP code 10001 (New York)
curl "https://grocery-scraper-api.vercel.app/stores/10001?store_chain=Walmart"

# Pretty print JSON response
curl "https://grocery-scraper-api.vercel.app/stores/60601" | jq
```

## 4. Search Products

```bash
# Basic product search
curl "https://grocery-scraper-api.vercel.app/products/search?query=milk"

# Search for milk in a specific ZIP code
curl "https://grocery-scraper-api.vercel.app/products/search?query=milk&zipcode=60601"

# Search for organic eggs at Target
curl "https://grocery-scraper-api.vercel.app/products/search?query=organic+eggs&store_name=Target&zipcode=60601"

# Search for bread with more results
curl "https://grocery-scraper-api.vercel.app/products/search?query=bread&num_results=30"

# Search with refresh (bypass cache)
curl "https://grocery-scraper-api.vercel.app/products/search?query=milk&zipcode=60601&refresh=true"

# Pretty print JSON response
curl "https://grocery-scraper-api.vercel.app/products/search?query=milk&zipcode=60601" | jq

# More examples:
curl "https://grocery-scraper-api.vercel.app/products/search?query=whole+wheat+bread&store_name=Walmart&zipcode=10001"
curl "https://grocery-scraper-api.vercel.app/products/search?query=chicken+breast&zipcode=90210&num_results=15"
curl "https://grocery-scraper-api.vercel.app/products/search?query=organic+bananas&store_name=Whole+Foods&zipcode=60601"
```

## 5. Aggregate Products (Compare Across Stores)

```bash
# Compare eggs across all stores in ZIP code 60601
curl "https://grocery-scraper-api.vercel.app/products/aggregate?query=eggs&zipcode=60601"

# Compare eggs with limit (return only 10 products)
curl "https://grocery-scraper-api.vercel.app/products/aggregate?query=eggs&zipcode=60601&limit=10"

# Compare milk at Target and Walmart only
curl "https://grocery-scraper-api.vercel.app/products/aggregate?query=milk&zipcode=60601&stores=target,walmart"

# Compare bread with custom radius
curl "https://grocery-scraper-api.vercel.app/products/aggregate?query=bread&zipcode=10001&radius_miles=15"

# Aggregate with refresh (bypass cache)
curl "https://grocery-scraper-api.vercel.app/products/aggregate?query=eggs&zipcode=60601&refresh=true"

# Limit results to top 5 products
curl "https://grocery-scraper-api.vercel.app/products/aggregate?query=eggs&zipcode=60601&limit=5"

# Pretty print JSON response
curl "https://grocery-scraper-api.vercel.app/products/aggregate?query=eggs&zipcode=60601" | jq

# More examples:
curl "https://grocery-scraper-api.vercel.app/products/aggregate?query=chicken+breast&zipcode=90210&stores=target,walmart,kroger"
curl "https://grocery-scraper-api.vercel.app/products/aggregate?query=organic+milk&zipcode=60601&stores=whole_foods,target"
curl "https://grocery-scraper-api.vercel.app/products/aggregate?query=bananas&zipcode=10001&radius_miles=20"
```

## 6. Using with Headers (for debugging)

```bash
# Include verbose output to see request/response headers
curl -v "https://grocery-scraper-api.vercel.app/health"

# Include response headers
curl -i "https://grocery-scraper-api.vercel.app/products/search?query=milk&zipcode=60601"

# Include request/response headers and timing
curl -w "\nTime: %{time_total}s\n" "https://grocery-scraper-api.vercel.app/products/search?query=milk&zipcode=60601"
```

## 7. Save Responses to Files

```bash
# Save health check response
curl "https://grocery-scraper-api.vercel.app/health" -o health_response.json

# Save product search response
curl "https://grocery-scraper-api.vercel.app/products/search?query=milk&zipcode=60601" -o milk_search.json

# Save aggregate response
curl "https://grocery-scraper-api.vercel.app/products/aggregate?query=eggs&zipcode=60601" -o eggs_aggregate.json
```

## 8. Testing Different ZIP Codes

```bash
# New York City (10001)
curl "https://grocery-scraper-api.vercel.app/stores/10001"
curl "https://grocery-scraper-api.vercel.app/products/search?query=milk&zipcode=10001"

# Los Angeles (90210)
curl "https://grocery-scraper-api.vercel.app/stores/90210"
curl "https://grocery-scraper-api.vercel.app/products/search?query=bread&zipcode=90210"

# Chicago (60601)
curl "https://grocery-scraper-api.vercel.app/stores/60601"
curl "https://grocery-scraper-api.vercel.app/products/aggregate?query=eggs&zipcode=60601"

# San Francisco (94102)
curl "https://grocery-scraper-api.vercel.app/stores/94102"
curl "https://grocery-scraper-api.vercel.app/products/search?query=organic+chicken&zipcode=94102"
```

## Quick Test Script

Save this as `test_api.sh`:

```bash
#!/bin/bash

BASE_URL="https://grocery-scraper-api.vercel.app"

echo "=== Health Check ==="
curl -s "$BASE_URL/health" | jq

echo -e "\n=== API Info ==="
curl -s "$BASE_URL/api" | jq

echo -e "\n=== Stores in 60601 ==="
curl -s "$BASE_URL/stores/60601" | jq '.stores_found, .stores[0:2]'

echo -e "\n=== Search Products: milk ==="
curl -s "$BASE_URL/products/search?query=milk&zipcode=60601" | jq '.products_found, .products[0:2]'

echo -e "\n=== Aggregate: eggs ==="
curl -s "$BASE_URL/products/aggregate?query=eggs&zipcode=60601" | jq '.results | length, .[0]'
```

Make it executable and run:
```bash
chmod +x test_api.sh
./test_api.sh
```

