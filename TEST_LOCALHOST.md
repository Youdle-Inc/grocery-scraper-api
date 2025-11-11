# Localhost Testing Commands

## 🚀 Quick Start

Make sure your server is running:
```bash
cd /Users/kayajones/projects/grocery-scraper-api
source venv/bin/activate  # if using venv
python3 -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

Or run the full test suite:
```bash
./test_localhost.sh
```

---

## 📋 Individual Test Commands

### 1. Health Check
```bash
curl -s "http://localhost:8000/health" | python3 -m json.tool
```

### 2. API Info
```bash
curl -s "http://localhost:8000/api" | python3 -m json.tool
```

### 3. Find Stores by ZIP Code
```bash
# All stores in ZIP code
curl -s "http://localhost:8000/stores/60601" | python3 -m json.tool

# Specific store chain
curl -s "http://localhost:8000/stores/60601?store_chain=Target" | python3 -m json.tool
```

### 4. Product Search
```bash
# Basic search
curl -s "http://localhost:8000/products/search?query=milk&zipcode=60601&num_results=5" | python3 -m json.tool

# Specific store
curl -s "http://localhost:8000/products/search?query=eggs&store_name=Target&zipcode=60601&num_results=3" | python3 -m json.tool

# With refresh (bypass cache)
curl -s "http://localhost:8000/products/search?query=bread&zipcode=60601&num_results=5&refresh=true" | python3 -m json.tool
```

### 5. Aggregate Products (Compare Across Stores)
```bash
# Basic aggregate (top 5 stores)
curl -s "http://localhost:8000/products/aggregate?query=milk&zipcode=60601&limit=3&refresh=true" | python3 -m json.tool

# Specific stores
curl -s "http://localhost:8000/products/aggregate?query=eggs&zipcode=60601&stores=target,walmart&limit=2&refresh=true" | python3 -m json.tool

# All 28 stores (slower)
curl -s "http://localhost:8000/products/aggregate?query=bread&zipcode=60601&all_stores=true&limit=2&refresh=true" | python3 -m json.tool

# With custom radius
curl -s "http://localhost:8000/products/aggregate?query=steak&zipcode=60601&radius_miles=15&limit=3&refresh=true" | python3 -m json.tool
```

### 6. Streaming API (Real-time Results)
```bash
# Stream results as they come in
curl -N "http://localhost:8000/products/aggregate/stream?query=steak&zipcode=60601&stores=target,walmart&limit=3&refresh=true"

# Stream with all stores
curl -N "http://localhost:8000/products/aggregate/stream?query=milk&zipcode=60601&all_stores=true&limit=2&refresh=true"
```

---

## 🔍 Testing Specific Features

### Test Store Address Extraction
```bash
curl -s "http://localhost:8000/products/aggregate?query=milk&zipcode=60601&limit=1&refresh=true" | python3 -m json.tool | grep -A 10 '"store":'
```

### Test Price Extraction
```bash
curl -s "http://localhost:8000/products/aggregate?query=eggs&zipcode=60601&limit=3&refresh=true" | python3 -m json.tool | grep -E '"price"|"currency"'
```

### Test Availability Detection
```bash
curl -s "http://localhost:8000/products/aggregate?query=bread&zipcode=60601&limit=3&refresh=true" | python3 -m json.tool | grep -E '"availability"'
```

### Test Store Location Data
```bash
curl -s "http://localhost:8000/stores/60601?store_chain=Target" | python3 -m json.tool | grep -A 5 '"address"'
```

---

## 📊 View Specific Fields

### View Only Product Names and Prices
```bash
curl -s "http://localhost:8000/products/aggregate?query=milk&zipcode=60601&limit=3&refresh=true" | python3 -m json.tool | grep -E '"name"|"price"|"store_name"' | head -20
```

### View Store Information Only
```bash
curl -s "http://localhost:8000/products/aggregate?query=eggs&zipcode=60601&limit=1&refresh=true" | python3 -m json.tool | grep -A 15 '"store_info"'
```

### Count Results
```bash
curl -s "http://localhost:8000/products/aggregate?query=milk&zipcode=60601&limit=10&refresh=true" | python3 -m json.tool | grep -c '"canonical_product"'
```

---

## 🧪 Test Different ZIP Codes

```bash
# New York
curl -s "http://localhost:8000/products/aggregate?query=milk&zipcode=10001&limit=3&refresh=true" | python3 -m json.tool

# Los Angeles
curl -s "http://localhost:8000/products/aggregate?query=milk&zipcode=90001&limit=3&refresh=true" | python3 -m json.tool

# Chicago (default)
curl -s "http://localhost:8000/products/aggregate?query=milk&zipcode=60601&limit=3&refresh=true" | python3 -m json.tool
```

---

## 🎯 Test Different Products

```bash
# Produce
curl -s "http://localhost:8000/products/aggregate?query=bananas&zipcode=60601&limit=3&refresh=true" | python3 -m json.tool

# Meat
curl -s "http://localhost:8000/products/aggregate?query=chicken+breast&zipcode=60601&limit=3&refresh=true" | python3 -m json.tool

# Dairy
curl -s "http://localhost:8000/products/aggregate?query=cheese&zipcode=60601&limit=3&refresh=true" | python3 -m json.tool

# Snacks
curl -s "http://localhost:8000/products/aggregate?query=chips&zipcode=60601&limit=3&refresh=true" | python3 -m json.tool
```

---

## ⚡ Performance Testing

### Test Response Time
```bash
time curl -s "http://localhost:8000/products/aggregate?query=milk&zipcode=60601&limit=3&refresh=true" > /dev/null
```

### Test Cached Response Time
```bash
# First request (cache miss)
time curl -s "http://localhost:8000/products/aggregate?query=milk&zipcode=60601&limit=3" > /dev/null

# Second request (cache hit - should be faster)
time curl -s "http://localhost:8000/products/aggregate?query=milk&zipcode=60601&limit=3" > /dev/null
```

---

## 🐛 Debug Mode

### Check Server Logs
The server should be running with `--reload` flag, so logs will appear in the terminal where you started it.

### Test with Verbose Output
```bash
curl -v "http://localhost:8000/health"
```

### Check API Documentation
Open in browser:
```
http://localhost:8000/
```

---

## 📝 Notes

- Use `refresh=true` to bypass cache and get fresh results
- Use `limit` to control number of results (default: 50, max: 100)
- Use `stores` parameter to search specific stores: `stores=target,walmart,kroger`
- Use `all_stores=true` to search all 28 supported stores (slower)
- Streaming API (`/products/aggregate/stream`) returns results incrementally
- ZIP code is required for aggregate endpoint
- Store name is optional for product search

