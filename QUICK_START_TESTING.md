# Quick Start Guide - Testing Universal Search API Locally

## Step 1: Install Dependencies

```bash
cd /Users/kayajones/projects/grocery-scraper-api
pip install -r requirements.txt
```

Or install manually:
```bash
pip install fastapi uvicorn pydantic python-dotenv redis exa-py
```

## Step 2: Set Environment Variables

Make sure you have a `.env` file with:
```
EXA_API_KEY=your_exa_api_key_here
```

## Step 3: Start the Server

```bash
cd /Users/kayajones/projects/grocery-scraper-api
python3 -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

The server will start at: `http://localhost:8000`

---

## Quick Test Commands

### 1. Health Check
```bash
curl http://localhost:8000/health | python3 -m json.tool
```

### 2. Check API Version (should be 3.0.0)
```bash
curl http://localhost:8000/api | python3 -m json.tool | grep version
```

### 3. Test Universal Search - Basic Query
```bash
curl "http://localhost:8000/products/search?query=milk&zipcode=60601&num_results=5" | python3 -m json.tool
```

**Look for:**
- `"api_version": "3.0.0"`
- `"source": "universal_search"`
- `"query_analysis"` field with intent, entities
- `"search_metadata"` with strategies_used

### 4. Test Brand Detection
```bash
curl "http://localhost:8000/products/search?query=kellogg%27s+cereal&zipcode=38125&num_results=3" | python3 -m json.tool | grep -A 10 "query_analysis"
```

**Expected:** `"intent": "BRAND_SEARCH"` and `"has_brand": "kellogg"`

### 5. Test Category Detection
```bash
curl "http://localhost:8000/products/search?query=dairy&zipcode=60601&num_results=3" | python3 -m json.tool | grep -A 10 "query_analysis"
```

**Expected:** `"intent": "CATEGORY_BROWSE"` and `"has_category": "dairy"`

### 6. Test Attribute Detection
```bash
curl "http://localhost:8000/products/search?query=organic+milk&zipcode=60601&num_results=3" | python3 -m json.tool | grep -A 10 "query_analysis"
```

**Expected:** `"intent": "ATTRIBUTE_FILTER"` and `"has_attribute": ["organic"]`

### 7. Test Aggregate Search
```bash
curl "http://localhost:8000/products/aggregate?query=eggs&zipcode=38125&stores=target,walmart,whole_foods&limit=5" | python3 -m json.tool | head -80
```

### 8. Test Store Display Names
```bash
curl "http://localhost:8000/products/aggregate?query=milk&zipcode=38125&stores=target,walmart,kroger,heb,trader_joes&limit=3" | python3 -m json.tool | grep "store_name"
```

**Expected:** Proper display names like "Target", "Walmart", "Kroger", "H-E-B", "Trader Joe's"

---

## Full Test Suite

Run all tests at once:

```bash
#!/bin/bash

BASE="http://localhost:8000"

echo "=== Testing Universal Search API ==="
echo ""

echo "1. Health:"
curl -s "$BASE/health" | python3 -m json.tool
echo ""

echo "2. API Info:"
curl -s "$BASE/api" | python3 -m json.tool | head -20
echo ""

echo "3. Basic Search (milk):"
curl -s "$BASE/products/search?query=milk&zipcode=60601&num_results=3" | python3 -m json.tool | head -50
echo ""

echo "4. Brand Search (kellogg's):"
curl -s "$BASE/products/search?query=kellogg%27s+cereal&zipcode=38125&num_results=3" | python3 -m json.tool | head -50
echo ""

echo "5. Category Search (dairy):"
curl -s "$BASE/products/search?query=dairy&zipcode=60601&num_results=3" | python3 -m json.tool | head -50
echo ""

echo "6. Attribute Search (organic):"
curl -s "$BASE/products/search?query=organic+milk&zipcode=60601&num_results=3" | python3 -m json.tool | head -50
echo ""

echo "7. Aggregate Search (eggs):"
curl -s "$BASE/products/aggregate?query=eggs&zipcode=38125&stores=target,walmart&limit=3" | python3 -m json.tool | head -60
echo ""

echo "=== Tests Complete ==="
```

Save as `test.sh`, make executable: `chmod +x test.sh`, then run: `./test.sh`

---

## What to Look For in Responses

### ✅ Success Indicators:

1. **API Version**: Should be `3.0.0`
2. **Source**: Should be `universal_search`
3. **Query Analysis**: Should include:
   - `intent` (PRODUCT_SEARCH, BRAND_SEARCH, CATEGORY_BROWSE, ATTRIBUTE_FILTER)
   - `entities` (brand, category, attributes, product_name)
   - `optimal_queries` (primary, expanded, category_based, brand_based)
4. **Search Metadata**: Should include:
   - `strategies_used` (number of search strategies)
   - `duration_seconds` (search time)
5. **Store Names**: All stores should have proper display names
6. **Result Ranking**: Results should have `relevance_score` and be sorted

### ❌ Issues to Watch For:

- Missing `query_analysis` field → Universal search not working
- `api_version` still `2.0.0` → Old code running
- `source` is `exa_structured` instead of `universal_search` → Not using universal search
- No `search_metadata` → Universal search not integrated

---

## Troubleshooting

### Server won't start:
```bash
# Check if port 8000 is in use
lsof -i :8000

# Use different port
python3 -m uvicorn main:app --host 0.0.0.0 --port 8001 --reload
```

### Import errors:
```bash
# Install all dependencies
pip install fastapi uvicorn pydantic python-dotenv redis exa-py
```

### EXA_API_KEY missing:
```bash
# Check .env file exists
cat .env

# Or set in environment
export EXA_API_KEY=your_key_here
```

### Check server logs:
The server will show:
- `🔍 Universal search: 'query' | Intent: ... | Brand: ... | Category: ...`
- `✅ Primary search: X results`
- `✅ Expanded search: X results`
- `🔍 Query analysis: {...}`

---

## Expected Response Example

```json
{
  "query": "milk",
  "store_name": "All Stores",
  "location": "60601",
  "products_found": 5,
  "search_timestamp": "2025-11-10T18:00:00",
  "products": [
    {
      "name": "Whole Milk Gallon",
      "brand": "Target",
      "price": 3.99,
      "relevance_score": 25.5,
      ...
    }
  ],
  "source": "universal_search",
  "api_version": "3.0.0",
  "query_analysis": {
    "intent": "PRODUCT_SEARCH",
    "entities": {
      "category": "dairy",
      "product_name": "milk"
    }
  },
  "search_metadata": {
    "strategies_used": 2,
    "duration_seconds": 1.234
  }
}
```

