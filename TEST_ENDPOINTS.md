# API Endpoint Testing Guide

## Prerequisites
Make sure your server is running:
```bash
source venv/bin/activate
python main.py
```

Or if using uvicorn:
```bash
uvicorn main:app --host 0.0.0.0 --port 8000
```

---

## 1. Health Check
Check if the API is running and services are available.

```bash
curl http://localhost:8000/health
```

**Expected Response:**
```json
{
  "status": "healthy",
  "timestamp": "2025-10-28T...",
  "version": "2.0.0",
  "services": {
    "exa_api": "available"
  }
}
```

---

## 2. Root Endpoint (HTML)
Get API documentation homepage.

```bash
curl http://localhost:8000/
```

---

## 3. API Info (JSON)
Get API information in JSON format.

```bash
curl http://localhost:8000/api
```

**Expected Response:**
```json
{
  "name": "Grocery Scraper API",
  "version": "2.0.0",
  "description": "AI-powered grocery product discovery...",
  "endpoints": {...},
  "features": [...]
}
```

---

## 4. Store Search by ZIP Code
Find grocery stores in a specific ZIP code.

### Basic store search:
```bash
curl "http://localhost:8000/stores/60601"
```

### Search for specific store chain:
```bash
curl "http://localhost:8000/stores/60601?store_chain=Target"
```

**Expected Response:**
```json
{
  "zipcode": "60601",
  "stores_found": 10,
  "search_timestamp": "2025-10-28T...",
  "stores": [
    {
      "store_id": "target",
      "store_name": "Target",
      "address": "123 Main St",
      "services": ["in-store"],
      "status": "active",
      "zipcode": "60601",
      "location": {
        "zipcode": "60601",
        "city": "Chicago",
        "state": "IL"
      }
    }
  ],
  "source": "exa_structured",
  "api_version": "2.0.0"
}
```

---

## 5. Product Search
Search for products at grocery stores.

### Basic product search:
```bash
curl "http://localhost:8000/products/search?query=milk&zipcode=60601"
```

### Search at specific store:
```bash
curl "http://localhost:8000/products/search?query=milk&store_name=Target&zipcode=60601"
```

### Search with more results:
```bash
curl "http://localhost:8000/products/search?query=eggs&store_name=Walmart&zipcode=60601&num_results=10"
```

### Force refresh (bypass cache):
```bash
curl "http://localhost:8000/products/search?query=bread&zipcode=60601&refresh=true"
```

**Expected Response:**
```json
{
  "query": "milk",
  "store_name": "Target",
  "location": "60601",
  "products_found": 5,
  "search_timestamp": "2025-10-28T...",
  "products": [
    {
      "name": "Milk - Good & Gather™",
      "brand": "Target",
      "price": null,
      "currency": "USD",
      "quantity": "0.5 Gallon",
      "availability": "Check Store",
      "image_url": "https://target.scene7.com/is/image/Target/94602358?wid=800&hei=800&qlt=80&fmt=webp",
      "product_url": "https://www.target.com/p/milk-good-gather/-/A-94602358",
      "store_name": "Target",
      "store_zipcode": "60601",
      "description": "...",
      "source": "exa_structured"
    }
  ],
  "source": "exa_structured",
  "api_version": "2.0.0"
}
```

---

## 6. Aggregate Product Search
Compare products across multiple stores.

### Basic aggregate search:
```bash
curl "http://localhost:8000/products/aggregate?query=milk&zipcode=60601"
```

### Search specific stores:
```bash
curl "http://localhost:8000/products/aggregate?query=eggs&zipcode=60601&stores=target,walmart"
```

### With custom radius:
```bash
curl "http://localhost:8000/products/aggregate?query=bread&zipcode=60601&radius_miles=15"
```

### Force refresh:
```bash
curl "http://localhost:8000/products/aggregate?query=cheese&zipcode=60601&refresh=true"
```

**Expected Response:**
```json
{
  "query": "milk",
  "zipcode": "60601",
  "stores_considered": ["target", "walmart", "whole_foods", "kroger", "aldi"],
  "results": [
    {
      "canonical_product": {
        "name": "Organic Whole Milk",
        "brand": "Horizon",
        "quantity": "1 Gallon",
        "images": [
          "https://target.scene7.com/is/image/Target/12345678?wid=800&hei=800",
          "https://i5.walmartimages.com/asr/87654321"
        ],
        "description": "...",
        "category": "Dairy"
      },
      "offers": [
        {
          "store_id": "target",
          "store_name": "Target",
          "price": 5.99,
          "currency": "USD",
          "quantity": "1 Gallon",
          "availability": "Check Store",
          "product_url": "https://www.target.com/p/...",
          "image_url": "https://target.scene7.com/...",
          "address": "123 Main St",
          "city": "Chicago",
          "state": "IL",
          "zipcode": "60601"
        },
        {
          "store_id": "walmart",
          "store_name": "Walmart",
          "price": 4.99,
          "currency": "USD",
          "quantity": "1 Gallon",
          "availability": "Check Store",
          "product_url": "https://www.walmart.com/ip/...",
          "image_url": "https://i5.walmartimages.com/..."
        }
      ]
    }
  ],
  "source": "exa_structured_aggregate"
}
```

---

## Pretty Print JSON (Optional)

Add ` | jq` or ` | python -m json.tool` to format the output:

```bash
curl "http://localhost:8000/health" | jq
```

```bash
curl "http://localhost:8000/products/search?query=milk&zipcode=60601" | python -m json.tool
```

---

## Test All Endpoints at Once

```bash
#!/bin/bash
echo "Testing all endpoints..."

echo "\n1. Health Check"
curl -s http://localhost:8000/health | python -m json.tool

echo "\n\n2. API Info"
curl -s http://localhost:8000/api | python -m json.tool

echo "\n\n3. Store Search (ZIP: 60601)"
curl -s "http://localhost:8000/stores/60601" | python -m json.tool

echo "\n\n4. Product Search (milk at Target)"
curl -s "http://localhost:8000/products/search?query=milk&store_name=Target&zipcode=60601&num_results=3" | python -m json.tool

echo "\n\n5. Aggregate Search (eggs)"
curl -s "http://localhost:8000/products/aggregate?query=eggs&zipcode=60601&stores=target,walmart" | python -m json.tool

echo "\n\nAll tests complete!"
```

Save as `test_all.sh`, make executable with `chmod +x test_all.sh`, then run: `./test_all.sh`

---

## Available Stores

You can search these stores by name:
- Target
- Walmart
- Whole Foods
- Kroger
- Safeway
- ALDI
- Costco
- Trader Joe's
- Sam's Club

## ZIP Codes for Testing

- **60601** - Chicago, IL
- **10001** - New York, NY
- **90001** - Los Angeles, CA
- **94102** - San Francisco, CA
- **02108** - Boston, MA
