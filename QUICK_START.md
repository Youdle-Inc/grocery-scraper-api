# Quick Start Guide - Exa Grocery Search API

## 🚀 Get Started in 3 Minutes

### Step 1: Set Up Environment (30 seconds)

Create a `.env` file in the project root:

```bash
# Required
EXA_API_KEY=your_exa_api_key_here

# Optional (for caching)
REDIS_HOST=localhost
REDIS_PORT=6379
```

**Get your Exa API key:** https://exa.ai (sign up if needed)

### Step 2: Install Dependencies (1 minute)

```bash
pip install -r requirements.txt
```

### Step 3: Test It! (30 seconds)

```bash
# Run the test script
python test_exa_structured.py
```

If you see ✅ symbols, you're ready!

### Step 4: Start the API (30 seconds)

```bash
# Start the server
python main.py
```

Visit: http://localhost:8000/docs for interactive API documentation

## 📡 Try Your First Request

### Example 1: Search for Products

```bash
curl "http://localhost:8000/products/search?query=oat%20milk&store_name=Target&zipcode=10001"
```

**Returns:**
```json
{
  "products": [
    {
      "name": "Oatly Original Oat Milk",
      "price": 4.99,
      "quantity": "64 fl oz",
      "image_url": "https://...",
      "store_name": "Target",
      "store_address": "123 Main St, New York, NY 10001",
      "store_zipcode": "10001"
    }
  ]
}
```

### Example 2: Compare Prices Across Stores

```bash
curl "http://localhost:8000/products/aggregate?query=organic%20milk&zipcode=10001"
```

**Returns:**
```json
{
  "results": [
    {
      "canonical_product": {
        "name": "Organic Whole Milk",
        "brand": "Horizon",
        "quantity": "1 gallon"
      },
      "offers": [
        {
          "store_name": "Target",
          "price": 5.99,
          "address": "123 Main St",
          "zipcode": "10001"
        },
        {
          "store_name": "Walmart",
          "price": 5.49,
          "address": "456 Oak Ave",
          "zipcode": "10001"
        }
      ]
    }
  ]
}
```

### Example 3: Find Stores

```bash
curl "http://localhost:8000/stores/10001?store_chain=Walmart"
```

## 🎯 All Your Endpoints

| Endpoint | Purpose | Example |
|----------|---------|---------|
| `GET /` | API info | `curl http://localhost:8000/` |
| `GET /health` | Check status | `curl http://localhost:8000/health` |
| `GET /stores/{zipcode}` | Find stores | `curl http://localhost:8000/stores/10001` |
| `GET /products/search` | Search products | See above |
| `GET /products/aggregate` | Compare prices | See above |

## 📊 What You Get in Every Response

### Product Data
✅ Product name  
✅ Price (USD)  
✅ Currency  
✅ Quantity (e.g., "1 gallon", "64 oz")  
✅ Product image URL  
✅ Product page URL  
✅ Availability status  

### Store Data
✅ Store name  
✅ Store address  
✅ City  
✅ State  
✅ ZIP code  

### Additional Data
✅ Brand name  
✅ Category  
✅ Description  
✅ Customer ratings  
✅ Reviews count  

## 🔧 Common Parameters

### `/products/search`
- `query` (required): Product to search for
- `store_name` (optional): Filter by store (e.g., "Target", "Walmart")
- `zipcode` (optional): Filter by location
- `num_results` (optional): Max results (default: 20)

### `/products/aggregate`
- `query` (required): Product to search for
- `zipcode` (required): Location to search
- `stores` (optional): Comma-separated store IDs (e.g., "target,walmart")
- `refresh` (optional): Skip cache (default: false)

### `/stores/{zipcode}`
- `zipcode` (required): 5-digit ZIP code
- `store_chain` (optional): Filter by chain (e.g., "Target")

## 🎨 Response Format

All responses include:
```json
{
  "query": "your search query",
  "products_found": 10,
  "products": [...],
  "source": "exa_structured",
  "api_version": "2.0.0",
  "cache": {
    "hit": false
  }
}
```

## 💡 Pro Tips

1. **Use specific queries**: "oat milk" works better than just "milk"
2. **Include store names**: Filters results to specific retailers
3. **Check cache status**: `"cache": {"hit": true}` means faster response
4. **Use aggregate**: Compare prices across multiple stores at once
5. **Valid ZIP codes**: Use 5-digit format (e.g., "10001")

## 🐛 Troubleshooting

### "Exa client not available"
```bash
# Check your .env file
cat .env | grep EXA_API_KEY

# Should show: EXA_API_KEY=your_key_here
```

### "No products found"
- Try different search terms
- Check store name spelling
- Verify ZIP code is valid

### "Connection refused"
```bash
# Make sure server is running
python main.py

# Should show: "Uvicorn running on http://0.0.0.0:8000"
```

## 📚 Next Steps

1. ✅ Read the full migration guide: `README_EXA_MIGRATION.md`
2. ✅ Check all changes: `CHANGES_SUMMARY.md`
3. ✅ Explore API docs: http://localhost:8000/docs
4. ✅ Review the code: `scraper/exa_structured_client.py`

## 🎉 You're All Set!

Your grocery search API is now powered by Exa with structured data extraction. Every response includes:
- ✅ Store name, address, and ZIP code
- ✅ Product price and quantity
- ✅ High-quality product images
- ✅ Consistent, structured JSON

**Need help?** Check the documentation at `/docs` or review the test examples in `test_exa_structured.py`

---

**Happy coding! 🚀**

