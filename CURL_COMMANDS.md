# 🛒 Grocery Scraper API - cURL Test Commands

## ✅ All Endpoints Tested and Working!

**Server:** `http://localhost:8001` (or port 8000 if available)

---

## 1. 🏥 Health Check
```bash
curl http://localhost:8001/health
```

**Response:**
```json
{
  "status": "healthy",
  "timestamp": "2025-10-28T11:45:16.737109",
  "version": "2.0.0",
  "services": {
    "exa_api": "available"
  }
}
```

---

## 2. 🏪 Store Search

### Find all stores in ZIP code:
```bash
curl "http://localhost:8001/stores/60601"
```

### Find specific store chain:
```bash
curl "http://localhost:8001/stores/60601?store_chain=Target"
```

**Response Sample:**
```json
{
  "zipcode": "60601",
  "stores_found": 44,
  "stores": [
    {
      "store_id": "target",
      "store_name": "Target",
      "services": ["in-store"],
      "status": "active",
      "zipcode": "60601"
    }
  ]
}
```

---

## 3. 🥛 Product Search

### Basic search:
```bash
curl "http://localhost:8001/products/search?query=milk&zipcode=60601"
```

### Search at specific store:
```bash
curl "http://localhost:8001/products/search?query=milk&store_name=Target&zipcode=60601"
```

### Get more results:
```bash
curl "http://localhost:8001/products/search?query=eggs&store_name=Walmart&zipcode=60601&num_results=10"
```

### Force refresh (bypass cache):
```bash
curl "http://localhost:8001/products/search?query=bread&zipcode=60601&refresh=true"
```

**Response Sample:**
```json
{
  "query": "milk",
  "store_name": "Target",
  "location": "60601",
  "products_found": 1,
  "products": [
    {
      "name": "Milk - Good & Gather™",
      "brand": "Target",
      "price": null,
      "currency": "USD",
      "quantity": "0.5 Gallon",
      "image_url": "https://target.scene7.com/is/image/Target/94602358?wid=800&hei=800&qlt=80&fmt=webp",
      "product_url": "https://www.target.com/p/milk-good-gather/-/A-94602358",
      "store_name": "Target",
      "store_zipcode": "60601"
    }
  ]
}
```

---

## 4. 📊 Aggregate Search (Compare across stores)

### Compare products:
```bash
curl "http://localhost:8001/products/aggregate?query=eggs&zipcode=60601"
```

### Compare at specific stores:
```bash
curl "http://localhost:8001/products/aggregate?query=eggs&zipcode=60601&stores=target,walmart"
```

### With radius:
```bash
curl "http://localhost:8001/products/aggregate?query=milk&zipcode=60601&radius_miles=15"
```

**Response Sample:**
```json
{
  "query": "eggs",
  "zipcode": "60601",
  "stores_considered": ["target", "walmart"],
  "results": [
    {
      "canonical_product": {
        "name": "Grade A Large Eggs - 12ct",
        "brand": "Target",
        "quantity": "12ct",
        "images": [
          "https://target.scene7.com/is/image/Target/14713534?wid=800&hei=800&qlt=80&fmt=webp"
        ]
      },
      "offers": [
        {
          "store_id": "target",
          "store_name": "Target",
          "price": null,
          "currency": "USD",
          "product_url": "https://www.target.com/p/...",
          "image_url": "https://target.scene7.com/...",
          "zipcode": "60601"
        }
      ]
    }
  ]
}
```

---

## 🎯 Quick Test Examples

### Test milk products:
```bash
curl "http://localhost:8001/products/search?query=milk&store_name=Target&zipcode=60601&num_results=5"
```

### Test eggs:
```bash
curl "http://localhost:8001/products/search?query=eggs&store_name=Walmart&zipcode=60601&num_results=5"
```

### Test bread:
```bash
curl "http://localhost:8001/products/search?query=whole+wheat+bread&store_name=Target&zipcode=60601"
```

### Test cheese:
```bash
curl "http://localhost:8001/products/search?query=cheddar+cheese&zipcode=10001"
```

---

## 💡 Pro Tips

### Pretty print JSON:
```bash
curl "http://localhost:8001/health" | python -m json.tool
```

### Save response to file:
```bash
curl "http://localhost:8001/products/search?query=milk&zipcode=60601" > response.json
```

### Test with headers:
```bash
curl -H "Content-Type: application/json" "http://localhost:8001/health"
```

### Measure response time:
```bash
curl -w "\nTime: %{time_total}s\n" "http://localhost:8001/health"
```

---

## 🏬 Available Stores

- Target
- Walmart
- Whole Foods
- Kroger
- Safeway
- ALDI
- Costco
- Trader Joe's
- Sam's Club
- Albertsons
- Publix
- H-E-B
- Wegmans

---

## 📍 Test ZIP Codes

- **60601** - Chicago, IL
- **10001** - New York, NY
- **90001** - Los Angeles, CA
- **94102** - San Francisco, CA
- **02108** - Boston, MA
- **75201** - Dallas, TX
- **33101** - Miami, FL
- **98101** - Seattle, WA

---

## ✅ What Each Response Includes

### Product Search Response:
- ✅ Product name
- ✅ Brand name
- ✅ Product URL (clickable link to store page)
- ✅ Product image URL (800x800 high quality)
- ✅ Quantity/size
- ✅ Store name
- ⚠️ Price (when available in page text ~20%)
- Store location (ZIP code)

### Store Search Response:
- ✅ Store name
- ✅ Store ID
- ✅ Services (in-store, delivery, etc.)
- ✅ Status
- ✅ Location (ZIP, city, state when available)

---

## 🚀 Ready for Web App Integration!

All responses include:
- Valid product URLs
- High-quality images
- Structured JSON
- Consistent data format
