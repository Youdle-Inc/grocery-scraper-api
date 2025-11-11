# 📚 API Documentation

Complete reference for the Grocery Scraper API endpoints.

## Base URL

- **Production**: `https://grocery-scraper-api.vercel.app`
- **Local Development**: `http://localhost:8000`

## Authentication

Currently, the API does not require authentication. API keys are configured server-side via environment variables.

## Endpoints

### Health Check

Check if the API and all services are running properly.

```http
GET /health
```

**Response:**
```json
{
  "status": "healthy",
  "timestamp": "2025-01-15T10:30:00.000000",
  "version": "3.0.0",
  "services": {
    "serper_api": "available"
  }
}
```

**Status Codes:**
- `200`: API is healthy
- `500`: API error

---

### API Information

Get API information and available endpoints.

```http
GET /api
```

**Response:**
```json
{
  "name": "Grocery Scraper API",
  "version": "3.0.0",
  "description": "AI-powered grocery product discovery with Serper - fast Google-powered search across stores",
  "endpoints": {
    "health": "/health",
    "stores": "/stores/{zipcode}",
    "products": "/products/search",
    "aggregate": "/products/aggregate",
    "aggregate_stream": "/products/aggregate/stream"
  },
  "features": [
    "Serper-powered Google search across stores",
    "Real product URLs and high-quality images (800x800+)",
    "Store location discovery (works with any ZIP code)",
    "Smart product matching across multiple stores",
    "Multi-store price comparison",
    "Universal location filtering",
    "Flexible result limits",
    "AI product validation",
    "Perplexity-style insights",
    "Real-time streaming API (Server-Sent Events)",
    "Enhanced availability detection",
    "28+ supported stores",
    "Structured data extraction (price, quantity, address, etc.)"
  ]
}
```

---

### Find Stores by ZIP Code

Find grocery stores in a specific ZIP code.

```http
GET /stores/{zipcode}?store_chain={optional}
```

**Path Parameters:**
- `zipcode` (required): 5-digit ZIP code (e.g., `60601`, `10001`)

**Query Parameters:**
- `store_chain` (optional): Filter by specific store chain (e.g., `Target`, `Walmart`)

**Example Request:**
```bash
curl "http://localhost:8000/stores/60601"
curl "http://localhost:8000/stores/60601?store_chain=Target"
```

**Response:**
```json
{
  "zipcode": "60601",
  "stores_found": 5,
  "stores": [
    {
      "store_id": "target",
      "store_name": "Target",
      "address": "123 Main St, Chicago, IL 60601",
      "city": "Chicago",
      "state": "IL",
      "zipcode": "60601",
      "services": ["in-store", "pickup", "delivery"],
      "status": "active"
    }
  ],
  "source": "serper",
  "api_version": "3.0.0"
}
```

**Response Fields:**
- `zipcode`: Requested ZIP code
- `stores_found`: Number of stores found
- `stores`: Array of store objects
  - `store_id`: Store identifier (e.g., `target`, `walmart`)
  - `store_name`: Display name (e.g., `Target`, `Walmart`)
  - `address`: Full street address
  - `city`: City name
  - `state`: State abbreviation
  - `zipcode`: ZIP code
  - `services`: Available services (e.g., `["in-store", "pickup", "delivery"]`)
  - `status`: Store status (e.g., `active`)

**Status Codes:**
- `200`: Success
- `400`: Invalid ZIP code format
- `500`: Server error

---

### Search Products

Search for grocery products with AI-powered semantic search.

```http
GET /products/search
```

**Query Parameters:**
- `query` (required): Product search term (e.g., `milk`, `organic eggs`)
- `zipcode` (optional): 5-digit ZIP code for location-based results
- `store_name` (optional): Filter by store (e.g., `Target`, `Walmart`)
- `num_results` (optional): Number of results (default: `20`, max: `50`)
- `refresh` (optional): Bypass cache (default: `false`)

**Example Request:**
```bash
curl "http://localhost:8000/products/search?query=milk&zipcode=60601"
curl "http://localhost:8000/products/search?query=organic+eggs&store_name=Target&zipcode=60601&num_results=10"
```

**Response:**
```json
{
  "query": "milk",
  "store_name": "All Stores",
  "location": "60601",
  "products_found": 5,
  "search_timestamp": "2025-01-15T10:30:00.000000Z",
  "products": [
    {
      "name": "Milk - Good & Gather™",
      "brand": "Target",
      "price": 4.99,
      "currency": "USD",
      "quantity": "0.5 Gallon",
      "image_url": "https://target.scene7.com/is/image/Target/94602358?wid=800&hei=800&qlt=80&fmt=webp",
      "product_url": "https://www.target.com/p/milk-good-gather/-/A-94602358",
      "store_name": "Target",
      "store_zipcode": "60601",
      "availability": "IN_STOCK"
    }
  ],
  "source": "serper",
  "api_version": "3.0.0"
}
```

**Response Fields:**
- `query`: Search query
- `store_name`: Store filter applied (or `"All Stores"`)
- `location`: ZIP code used
- `products_found`: Number of products found
- `search_timestamp`: ISO timestamp of search
- `products`: Array of product objects
  - `name`: Product name
  - `brand`: Brand name
  - `price`: Price (float, nullable)
  - `currency`: Currency code (default: `USD`)
  - `quantity`: Product quantity/size
  - `image_url`: Product image URL (800x800+)
  - `product_url`: Direct link to product page
  - `store_name`: Store name
  - `store_zipcode`: Store ZIP code
  - `availability`: Stock status (`IN_STOCK`, `OUT_OF_STOCK`, `LOW_STOCK`, `CHECK_STORE`)

**Status Codes:**
- `200`: Success
- `400`: Invalid parameters
- `500`: Server error

---

### Aggregate Products (Compare Across Stores)

Compare the same products across multiple stores to find the best deals.

```http
GET /products/aggregate
```

**Query Parameters:**
- `query` (required): Product to search for (e.g., `eggs`, `milk`, `bread`)
- `zipcode` (required): 5-digit ZIP code for location-based results
- `limit` (optional): Maximum number of products to return (default: `50`, max: `100`)
- `stores` (optional): Comma-separated store IDs (e.g., `target,walmart`)
- `all_stores` (optional): Search all 28 supported stores instead of default top 5 (default: `false`)
- `radius_miles` (optional): Search radius in miles (default: `10`, max: `50`)
- `refresh` (optional): Bypass cache (default: `false`)

**Example Request:**
```bash
# Compare eggs across all stores
curl "http://localhost:8000/products/aggregate?query=eggs&zipcode=60601"

# Compare with limit
curl "http://localhost:8000/products/aggregate?query=eggs&zipcode=60601&limit=10"

# Compare specific stores only
curl "http://localhost:8000/products/aggregate?query=milk&zipcode=60601&stores=target,walmart"

# Search all 28 supported stores
curl "http://localhost:8000/products/aggregate?query=eggs&zipcode=60601&all_stores=true"
```

**Response:**
```json
{
  "query": "eggs",
  "zipcode": "60601",
  "search_timestamp": "2025-01-15T10:30:00.000000Z",
  "stores_considered": ["target", "walmart", "whole_foods", "kroger", "aldi"],
  "results": [
    {
      "canonical_product": {
        "name": "Grade A Large Eggs - 12ct",
        "brand": "Target",
        "category_path": ["Dairy & Eggs", "Eggs"]
      },
      "images": [
        {
          "url": "https://target.scene7.com/is/image/Target/GUEST_b40d86ca-08ae-4368-9151-ffa842c2ebf8?wid=1200&hei=1200&qlt=80",
          "is_primary": true
        }
      ],
      "offers": [
        {
          "store": {
            "retailer": "target",
            "retailer_store_id": null,
            "store_name": "Target",
            "address": "123 Main St",
            "city": "Chicago",
            "state": "IL",
            "zipcode": "60601"
          },
          "product_url": "https://www.target.com/p/grade-a-large-eggs-12ct/-/A-94684060",
          "fulfillment": ["PICKUP", "DELIVERY"],
          "availability": "IN_STOCK",
          "regular_price": 4.99,
          "sale_price": null
        }
      ],
      "source": "serper"
    }
  ],
  "overview": "Found 10 products for 'eggs' across 5 stores ranging from $3.99 to $5.99 including brands like Target, Walmart in categories: Dairy & Eggs, Eggs near 60601.",
  "follow_up_queries": [
    "milk",
    "butter",
    "Target eggs",
    "organic eggs",
    "cheapest eggs",
    "best deals on eggs"
  ],
  "meta": {
    "api_version": "3.0.0",
    "cache": {
      "hit": false
    }
  }
}
```

**Response Fields:**
- `query`: Search query
- `zipcode`: ZIP code used
- `search_timestamp`: ISO timestamp of search
- `stores_considered`: Array of store IDs searched
- `results`: Array of grouped products
  - `canonical_product`: Product information
    - `name`: Product name
    - `brand`: Brand name
    - `category_path`: Product category hierarchy
  - `images`: Array of product images
    - `url`: Image URL
    - `is_primary`: Whether this is the primary image
  - `offers`: Array of offers from different stores
    - `store`: Store information
      - `retailer`: Store ID
      - `store_name`: Store display name
      - `address`: Street address
      - `city`: City name
      - `state`: State abbreviation
      - `zipcode`: ZIP code
    - `product_url`: Direct link to product page
    - `fulfillment`: Available fulfillment options (`PICKUP`, `DELIVERY`, `IN_STORE`)
    - `availability`: Stock status (`IN_STOCK`, `OUT_OF_STOCK`, `LOW_STOCK`, `CHECK_STORE`)
    - `regular_price`: Regular price (float)
    - `sale_price`: Sale price if on sale (float, nullable)
- `overview`: Natural language summary of search results
- `follow_up_queries`: Suggested related searches
- `meta`: Metadata
  - `api_version`: API version
  - `cache`: Cache information (`hit`: boolean)

**Status Codes:**
- `200`: Success
- `400`: Invalid parameters (e.g., missing zipcode)
- `500`: Server error

---

### Streaming API (Real-time Results)

Stream product results as they come in from each store using Server-Sent Events (SSE).

```http
GET /products/aggregate/stream
```

**Query Parameters:**
- `query` (required): Product to search for
- `zipcode` (required): 5-digit ZIP code
- `stores` (optional): Comma-separated store IDs (e.g., `target,walmart`)
- `limit` (optional): Maximum products per store (default: `10`, max: `50`)
- `refresh` (optional): Bypass cache (default: `false`)
- `all_stores` (optional): Search all 28 stores (default: `false`)

**Example Request:**
```bash
curl -N "http://localhost:8000/products/aggregate/stream?query=steak&zipcode=60601&stores=target,walmart&limit=3"
```

**Response Format (SSE):**
```
data: {"type": "store_complete", "store_name": "Target", "products": [...]}

data: {"type": "store_complete", "store_name": "Walmart", "products": [...]}

data: {"type": "done", "summary": "All stores complete"}
```

**Event Types:**
- `store_complete`: A store has finished searching
  - `store_name`: Store name
  - `products`: Array of products found
- `done`: All stores have finished
  - `summary`: Completion message

**JavaScript Example:**
```javascript
const eventSource = new EventSource(
  '/products/aggregate/stream?query=eggs&zipcode=60601&stores=target,walmart'
);

eventSource.onmessage = (event) => {
  const data = JSON.parse(event.data);
  if (data.type === 'store_complete') {
    console.log('Store completed:', data.store_name);
    console.log('Products:', data.products);
    // Update your UI here!
  } else if (data.type === 'done') {
    console.log('All stores complete!');
    eventSource.close();
  }
};
```

**Status Codes:**
- `200`: Success (streaming)
- `400`: Invalid parameters
- `500`: Server error

---

## Error Responses

All endpoints may return error responses in the following format:

```json
{
  "detail": "Error message describing what went wrong"
}
```

**Common Status Codes:**
- `400`: Bad Request - Invalid parameters
- `404`: Not Found - Endpoint or resource not found
- `500`: Internal Server Error - Server-side error
- `503`: Service Unavailable - External service unavailable

---

## Rate Limiting

Currently, there are no rate limits enforced by the API. However, rate limits may apply from:
- **Serper API**: Check [serper.dev](https://serper.dev) for current limits
- **OpenAI API**: If using AI features, check OpenAI rate limits

---

## Caching

The API uses intelligent caching to improve performance:
- Store locations are cached for 24 hours
- Product searches are cached for 1 hour
- Use `refresh=true` to bypass cache

---

## Best Practices

1. **Use ZIP codes**: Always provide a ZIP code for location-based results
2. **Set reasonable limits**: Use `limit` parameter to control response size
3. **Use streaming**: For web apps, use `/products/aggregate/stream` for better UX
4. **Handle errors**: Always check status codes and handle errors gracefully
5. **Cache responses**: Cache responses client-side when appropriate
6. **Use refresh wisely**: Only use `refresh=true` when you need fresh data

---

## Support

For issues or questions:
- **GitHub Issues**: [Create an issue](https://github.com/Youdle-Inc/grocery-scraper-api/issues)
- **Documentation**: See [README.md](./README.md) for setup instructions

