# Universal Grocery Search API - Local Testing cURL Commands

## Server URL: http://localhost:8000

---

## 1. Health Check
```bash
curl http://localhost:8000/health | python3 -m json.tool
```

---

## 2. API Info (Check Version 3.0.0)
```bash
curl http://localhost:8000/api | python3 -m json.tool
```

---

## 3. Basic Product Search (Universal Search)
```bash
# Simple product search
curl "http://localhost:8000/products/search?query=milk&zipcode=60601&num_results=5" | python3 -m json.tool

# Check for query_analysis in response
curl "http://localhost:8000/products/search?query=milk&zipcode=60601&num_results=5" | python3 -m json.tool | grep -A 10 "query_analysis"
```

---

## 4. Brand Search (Should detect BRAND_SEARCH intent)
```bash
curl "http://localhost:8000/products/search?query=kellogg%27s+cereal&zipcode=38125&num_results=5" | python3 -m json.tool

# Check intent detection
curl "http://localhost:8000/products/search?query=kellogg%27s+cereal&zipcode=38125&num_results=5" | python3 -m json.tool | grep -A 5 "intent"
```

---

## 5. Category Search (Should detect CATEGORY_BROWSE intent)
```bash
curl "http://localhost:8000/products/search?query=organic+produce&zipcode=10001&num_results=5" | python3 -m json.tool

# Check category detection
curl "http://localhost:8000/products/search?query=dairy&zipcode=60601&num_results=5" | python3 -m json.tool | grep -A 5 "category"
```

---

## 6. Attribute Filter Search (Should detect ATTRIBUTE_FILTER intent)
```bash
curl "http://localhost:8000/products/search?query=gluten-free+bread&zipcode=90210&num_results=5" | python3 -m json.tool

# Check attribute detection
curl "http://localhost:8000/products/search?query=organic+milk&zipcode=60601&num_results=5" | python3 -m json.tool | grep -A 5 "attributes"
```

---

## 7. Query Expansion Test (Synonyms)
```bash
# Test "soda" - should expand to "pop", "soft drink"
curl "http://localhost:8000/products/search?query=soda&zipcode=60601&num_results=5" | python3 -m json.tool

# Check expansions in query_analysis
curl "http://localhost:8000/products/search?query=soda&zipcode=60601&num_results=5" | python3 -m json.tool | grep -A 10 "expansions"
```

---

## 8. Store-Specific Search
```bash
# Search at Target
curl "http://localhost:8000/products/search?query=eggs&store_name=Target&zipcode=38125&num_results=5" | python3 -m json.tool

# Search at Walmart
curl "http://localhost:8000/products/search?query=milk&store_name=Walmart&zipcode=38125&num_results=5" | python3 -m json.tool

# Search at Whole Foods
curl "http://localhost:8000/products/search?query=organic+bananas&store_name=Whole+Foods&zipcode=60601&num_results=5" | python3 -m json.tool
```

---

## 9. Multi-Store Aggregate Search
```bash
# Compare eggs across Target, Walmart, Whole Foods
curl "http://localhost:8000/products/aggregate?query=eggs&zipcode=38125&stores=target,walmart,whole_foods&limit=10" | python3 -m json.tool

# Compare milk across all stores
curl "http://localhost:8000/products/aggregate?query=milk&zipcode=60601&limit=5" | python3 -m json.tool
```

---

## 10. Test All 28 Stores (Store Discovery)
```bash
# Find stores in Memphis
curl "http://localhost:8000/stores/38125" | python3 -m json.tool

# Find Target stores in Memphis
curl "http://localhost:8000/stores/38125?store_chain=Target" | python3 -m json.tool

# Find Walmart stores in Chicago
curl "http://localhost:8000/stores/60601?store_chain=Walmart" | python3 -m json.tool
```

---

## 11. Test Store Display Names
```bash
# Test various store IDs in aggregate endpoint
curl "http://localhost:8000/products/aggregate?query=milk&zipcode=38125&stores=target,walmart,kroger,costco,aldi,whole_foods,trader_joes&limit=5" | python3 -m json.tool | grep -A 3 "store_name"
```

---

## 12. Test Query Understanding Features

### Brand Detection
```bash
curl "http://localhost:8000/products/search?query=coca+cola&zipcode=60601&num_results=3" | python3 -m json.tool | grep -A 5 "has_brand"
```

### Category Detection
```bash
curl "http://localhost:8000/products/search?query=chicken+breast&zipcode=38125&num_results=3" | python3 -m json.tool | grep -A 5 "has_category"
```

### Attribute Detection
```bash
curl "http://localhost:8000/products/search?query=cage-free+eggs&zipcode=60601&num_results=3" | python3 -m json.tool | grep -A 5 "has_attribute"
```

---

## 13. Test Search Metadata
```bash
# Check search strategies used
curl "http://localhost:8000/products/search?query=milk&zipcode=60601&num_results=5" | python3 -m json.tool | grep -A 5 "search_metadata"

# Check search duration
curl "http://localhost:8000/products/search?query=organic+eggs&zipcode=38125&num_results=5" | python3 -m json.tool | grep -A 3 "duration"
```

---

## 14. Test Result Ranking (Check relevance_score)
```bash
# Results should be sorted by relevance
curl "http://localhost:8000/products/search?query=milk&zipcode=60601&num_results=5" | python3 -m json.tool | grep -A 2 "relevance_score"
```

---

## 15. Test Cache Bypass
```bash
# First request (cache miss)
curl "http://localhost:8000/products/search?query=milk&zipcode=60601&num_results=5" | python3 -m json.tool | grep "cache"

# Second request (cache hit)
curl "http://localhost:8000/products/search?query=milk&zipcode=60601&num_results=5" | python3 -m json.tool | grep "cache"

# Force refresh
curl "http://localhost:8000/products/search?query=milk&zipcode=60601&num_results=5&refresh=true" | python3 -m json.tool | grep "cache"
```

---

## 16. Comprehensive Test Suite

### Test All Query Types
```bash
# Product search
curl "http://localhost:8000/products/search?query=milk&zipcode=60601&num_results=3" | python3 -m json.tool > test_product_search.json

# Brand search
curl "http://localhost:8000/products/search?query=kellogg%27s+cereal&zipcode=38125&num_results=3" | python3 -m json.tool > test_brand_search.json

# Category search
curl "http://localhost:8000/products/search?query=dairy&zipcode=60601&num_results=3" | python3 -m json.tool > test_category_search.json

# Attribute search
curl "http://localhost:8000/products/search?query=organic+milk&zipcode=60601&num_results=3" | python3 -m json.tool > test_attribute_search.json

# Aggregate search
curl "http://localhost:8000/products/aggregate?query=eggs&zipcode=38125&stores=target,walmart&limit=5" | python3 -m json.tool > test_aggregate_search.json
```

---

## Quick Test Script

Save this as `test_api.sh`:

```bash
#!/bin/bash

BASE_URL="http://localhost:8000"

echo "=== Testing Universal Grocery Search API ==="
echo ""

echo "1. Health Check:"
curl -s "$BASE_URL/health" | python3 -m json.tool
echo ""

echo "2. API Version:"
curl -s "$BASE_URL/api" | python3 -m json.tool | grep version
echo ""

echo "3. Basic Search (milk):"
curl -s "$BASE_URL/products/search?query=milk&zipcode=60601&num_results=3" | python3 -m json.tool | head -30
echo ""

echo "4. Brand Search (kellogg's cereal):"
curl -s "$BASE_URL/products/search?query=kellogg%27s+cereal&zipcode=38125&num_results=3" | python3 -m json.tool | head -30
echo ""

echo "5. Aggregate Search (eggs):"
curl -s "$BASE_URL/products/aggregate?query=eggs&zipcode=38125&stores=target,walmart&limit=3" | python3 -m json.tool | head -40
echo ""

echo "=== Tests Complete ==="
```

Make it executable:
```bash
chmod +x test_api.sh
./test_api.sh
```

---

## Expected Response Structure (v3.0.0)

```json
{
  "query": "milk",
  "store_name": "All Stores",
  "location": "60601",
  "products_found": 5,
  "search_timestamp": "2025-11-10T18:00:00",
  "products": [...],
  "source": "universal_search",
  "api_version": "3.0.0",
  "query_analysis": {
    "intent": "PRODUCT_SEARCH",
    "entities": {
      "brand": null,
      "category": "dairy",
      "attributes": [],
      "quantity": null,
      "product_name": "milk"
    },
    "optimal_queries": {
      "primary": "milk grocery product",
      "expanded": ["milk", "dairy milk", "cow milk"],
      "exact": "milk",
      "category_based": "dairy milk",
      "brand_based": null
    }
  },
  "search_metadata": {
    "strategies_used": 2,
    "duration_seconds": 1.234,
    "zipcode": "60601",
    "store_filter": null
  }
}
```

---

## Tips for Testing

1. **Check API Version**: Should show `3.0.0` in responses
2. **Check Query Analysis**: Every search should include `query_analysis` field
3. **Check Search Metadata**: Should show `strategies_used` and `duration_seconds`
4. **Check Store Names**: All stores should have proper display names
5. **Check Ranking**: Results should be sorted by relevance (highest first)
6. **Check Deduplication**: No duplicate products in results

---

## Troubleshooting

If server isn't running:
```bash
cd /Users/kayajones/projects/grocery-scraper-api
python3 -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

If you get import errors:
```bash
pip install -r requirements.txt
```

Check logs for query analysis:
```bash
# Server logs will show:
# 🔍 Universal search: 'milk' | Intent: PRODUCT_SEARCH | Brand: None | Category: dairy
# ✅ Primary search: 5 results
# 🔍 Query analysis: {...}
```

