# Quick Test Commands

## Start the Server
```bash
cd /Users/kayajones/projects/grocery-scraper-api
source venv/bin/activate
python3 -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

## Test Commands

### 1. Health Check
```bash
curl "http://localhost:8000/health" | python3 -m json.tool
```

### 2. Product Search (Single Store)
```bash
curl "http://localhost:8000/products/search?query=milk&store_name=Target&num_results=5" | python3 -m json.tool
```

### 3. Product Search (All Stores)
```bash
curl "http://localhost:8000/products/search?query=milk&num_results=5" | python3 -m json.tool
```

### 4. Aggregate Search (Multiple Stores)
```bash
curl "http://localhost:8000/products/aggregate?query=milk&zipcode=60601&limit=5" | python3 -m json.tool
```

### 5. Aggregate with All Stores
```bash
curl "http://localhost:8000/products/aggregate?query=milk&zipcode=60601&all_stores=true&limit=10" | python3 -m json.tool
```

### 6. Streaming Endpoint
```bash
curl -N "http://localhost:8000/products/aggregate/stream?query=milk&zipcode=60601&limit=5"
```

### 7. Test Different Products
```bash
# Bread
curl "http://localhost:8000/products/aggregate?query=bread&zipcode=60601&limit=3" | python3 -m json.tool

# Eggs  
curl "http://localhost:8000/products/aggregate?query=eggs&zipcode=60601&limit=3" | python3 -m json.tool

# Chicken
curl "http://localhost:8000/products/aggregate?query=chicken&zipcode=60601&limit=3" | python3 -m json.tool
```

## Troubleshooting

If you get "Internal Server Error":
1. Check if server is running: `ps aux | grep uvicorn`
2. Check server logs for errors
3. Make sure you're in the venv: `source venv/bin/activate`
4. Restart server: `pkill -f uvicorn` then start again

If you get "Connection refused":
- Server isn't running - start it with the command above

If results are empty:
- This is normal - Serper may not find products for all queries
- Try different products or stores
- Check the API key is set correctly

