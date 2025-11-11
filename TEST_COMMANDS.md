# API Testing Commands

## Prerequisites
Make sure the server is running:
```bash
cd /Users/kayajones/projects/grocery-scraper-api
source venv/bin/activate
python3 -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

## Health Check
```bash
curl "http://localhost:8000/health" | python3 -m json.tool
```

## Product Search Endpoint

### Basic search (all stores)
```bash
curl "http://localhost:8000/products/search?query=milk&num_results=5" | python3 -m json.tool
```

### Search with store filter
```bash
curl "http://localhost:8000/products/search?query=milk&store_name=Target&num_results=5" | python3 -m json.tool
```

### Search with zipcode
```bash
curl "http://localhost:8000/products/search?query=milk&zipcode=60601&num_results=5" | python3 -m json.tool
```

### Search with store and zipcode
```bash
curl "http://localhost:8000/products/search?query=milk&store_name=Walmart&zipcode=60601&num_results=5" | python3 -m json.tool
```

## Product Aggregate Endpoint

### Basic aggregate search (top 5 stores)
```bash
curl "http://localhost:8000/products/aggregate?query=milk&zipcode=60601&limit=5" | python3 -m json.tool
```

### Aggregate search with all stores
```bash
curl "http://localhost:8000/products/aggregate?query=milk&zipcode=60601&all_stores=true&limit=10" | python3 -m json.tool
```

### Aggregate search for specific product
```bash
curl "http://localhost:8000/products/aggregate?query=bread&zipcode=60601&limit=3" | python3 -m json.tool
```

### Aggregate search for eggs
```bash
curl "http://localhost:8000/products/aggregate?query=eggs&zipcode=60601&limit=3" | python3 -m json.tool
```

### Aggregate search for organic products
```bash
curl "http://localhost:8000/products/aggregate?query=organic%20milk&zipcode=60601&limit=5" | python3 -m json.tool
```

## Streaming Aggregate Endpoint (SSE)

### Stream results as they come in
```bash
curl -N "http://localhost:8000/products/aggregate/stream?query=milk&zipcode=60601&limit=5"
```

### Stream with all stores
```bash
curl -N "http://localhost:8000/products/aggregate/stream?query=milk&zipcode=60601&all_stores=true&limit=10"
```

## Pretty Print Examples

### Save to file and view
```bash
curl "http://localhost:8000/products/aggregate?query=milk&zipcode=60601&limit=3" | python3 -m json.tool > results.json
cat results.json
```

### View specific fields only
```bash
curl "http://localhost:8000/products/aggregate?query=milk&zipcode=60601&limit=3" | python3 -c "import sys, json; data=json.load(sys.stdin); [print(f\"{r['name']} - {r.get('offers', [{}])[0].get('regular_price', 'N/A')}\") for r in data.get('results', [])]"
```

## Test Different Stores

### Target
```bash
curl "http://localhost:8000/products/search?query=chicken&store_name=Target&num_results=3" | python3 -m json.tool
```

### Walmart
```bash
curl "http://localhost:8000/products/search?query=chicken&store_name=Walmart&num_results=3" | python3 -m json.tool
```

### Whole Foods
```bash
curl "http://localhost:8000/products/search?query=organic%20chicken&store_name=Whole%20Foods&num_results=3" | python3 -m json.tool
```

### Kroger
```bash
curl "http://localhost:8000/products/search?query=chicken&store_name=Kroger&num_results=3" | python3 -m json.tool
```

### ALDI
```bash
curl "http://localhost:8000/products/search?query=chicken&store_name=ALDI&num_results=3" | python3 -m json.tool
```

## Quick Test Script

Save this as `test_api.sh`:
```bash
#!/bin/bash

BASE_URL="http://localhost:8000"

echo "=== Health Check ==="
curl -s "$BASE_URL/health" | python3 -m json.tool | head -20

echo -e "\n=== Search: Milk ==="
curl -s "$BASE_URL/products/search?query=milk&num_results=3" | python3 -m json.tool | head -40

echo -e "\n=== Aggregate: Milk ==="
curl -s "$BASE_URL/products/aggregate?query=milk&zipcode=60601&limit=2" | python3 -m json.tool | head -60
```

Make it executable and run:
```bash
chmod +x test_api.sh
./test_api.sh
```

