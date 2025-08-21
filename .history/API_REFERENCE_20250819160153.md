# 📚 API Reference

Complete reference for the Grocery Scraper API endpoints, parameters, and responses.

## 🔗 Base URL

```
http://localhost:8000
```

## 📋 Authentication

No authentication is required for the API endpoints. API keys are configured server-side via environment variables.

## 🏪 Store Discovery

### Find Stores in a Location

**Endpoint:** `GET /sonar/stores/search`

**Description:** Discover grocery stores in a specific location using AI-powered search.

**Parameters:**

| Parameter | Type | Required | Description | Example |
|-----------|------|----------|-------------|---------|
| `location` | string | ✅ | City, state, or zipcode | `"Chicago,IL"` |

**Example Request:**
```bash
curl "http://localhost:8000/sonar/stores/search?location=Chicago,IL"
```

**Example Response:**
```json
{
  "location": "Chicago, IL",
  "stores_found": 3,
  "stores": [
    {
      "store_id": "target",
      "store_name": "Target",
      "address": "123 Main St, Chicago, IL 60601",
      "services": ["delivery", "pickup", "in-store"],
      "status": "active",
      "website": "https://www.target.com"
    },
    {
      "store_id": "walmart",
      "store_name": "Walmart",
      "address": "456 Oak Ave, Chicago, IL 60602",
      "services": ["delivery", "pickup", "in-store"],
      "status": "active",
      "website": "https://www.walmart.com"
    }
  ],
  "source": "perplexity_sonar"
}
```

**Response Fields:**

| Field | Type | Description |
|-------|------|-------------|
| `location` | string | The searched location |
| `stores_found` | integer | Number of stores found |
| `stores` | array | Array of store objects |
| `source` | string | Data source identifier |

**Store Object Fields:**

| Field | Type | Description |
|-------|------|-------------|
| `store_id` | string | Unique store identifier |
| `store_name` | string | Store name |
| `address` | string | Store address |
| `services` | array | Available services (delivery, pickup, in-store) |
| `status` | string | Store status (active, inactive) |
| `website` | string | Store website URL |

## 🛒 Product Search

### Search for Products

**Endpoint:** `GET /sonar/products/search`

**Description:** Search for products at a specific store with real URLs and images.

**Parameters:**

| Parameter | Type | Required | Description | Example |
|-----------|------|----------|-------------|---------|
| `query` | string | ✅ | Product search query | `"oat milk"` |
| `store_name` | string | ✅ | Store name to search | `"Target"` |
| `location` | string | ✅ | Store location | `"Chicago,IL"` |

**Example Request:**
```bash
curl "http://localhost:8000/sonar/products/search?query=oat%20milk&store_name=Target&location=Chicago,IL"
```

**Example Response:**
```json
{
  "query": "oat milk",
  "store_name": "Target",
  "location": "Chicago, IL",
  "products_found": 6,
  "search_timestamp": "2025-08-19T15:42:58.731850",
  "products": [
    {
      "name": "Oatly Original Oatmilk",
      "price": 4.99,
      "availability": "in stock",
      "category": "Dairy Alternatives",
      "brand": "Oatly",
      "size": "64 oz",
      "description": "Original oat milk, creamy and delicious",
      "image_url": "https://encrypted-tbn1.gstatic.com/shopping?q=tbn:ANd9GcQ77QBCxGp6Fl572X73iaEEaL5qnAB5nse4cjxqaNTr0Hqi8FVhC5xGni3IMPlWoh58k-yhTqQPooAnLWDuwh0R9ucDakiD0Q",
      "product_url": "https://google.com/shopping/product/2512895342606972574?gl=us",
      "rating": 4.5,
      "reviews_count": 1250,
      "nutritional_info": null,
      "ingredients": null,
      "allergens": null,
      "online_available": null,
      "in_store_only": null
    }
  ],
  "source": "perplexity_sonar + serper_dev"
}
```

**Response Fields:**

| Field | Type | Description |
|-------|------|-------------|
| `query` | string | The search query |
| `store_name` | string | The store name |
| `location` | string | The store location |
| `products_found` | integer | Number of products found |
| `search_timestamp` | string | ISO timestamp of the search |
| `products` | array | Array of product objects |
| `source` | string | Data sources used |

**Product Object Fields:**

| Field | Type | Description |
|-------|------|-------------|
| `name` | string | Product name |
| `price` | float | Product price in USD |
| `availability` | string | Stock availability status |
| `category` | string | Product category |
| `brand` | string | Brand name |
| `size` | string | Product size/volume |
| `description` | string | Product description |
| `image_url` | string | **Real product image URL** (from Google Shopping) |
| `product_url` | string | **Real product page URL** (from Google Shopping) |
| `rating` | float | Customer rating (1-5) |
| `reviews_count` | integer | Number of customer reviews |
| `nutritional_info` | object | Nutritional information (when available) |
| `ingredients` | array | Product ingredients (when available) |
| `allergens` | array | Allergen information (when available) |
| `online_available` | boolean | Available for online purchase |
| `in_store_only` | boolean | In-store only availability |

## 🏥 Health Check

### Check API Health

**Endpoint:** `GET /health`

**Description:** Check the health status of the API and its dependencies.

**Example Request:**
```bash
curl "http://localhost:8000/health"
```

**Example Response:**
```json
{
  "status": "healthy",
  "timestamp": "2025-08-19T15:42:58.731850",
  "version": "1.0.0",
  "services": {
    "perplexity_sonar": "available",
    "serper_dev": "available"
  }
}
```

**Response Fields:**

| Field | Type | Description |
|-------|------|-------------|
| `status` | string | Overall health status |
| `timestamp` | string | Current timestamp |
| `version` | string | API version |
| `services` | object | Status of external services |

## 📊 API Information

### Get API Information

**Endpoint:** `GET /`

**Description:** Get basic information about the API.

**Example Request:**
```bash
curl "http://localhost:8000/"
```

**Example Response:**
```json
{
  "name": "Grocery Scraper API",
  "version": "1.0.0",
  "description": "AI-powered grocery product discovery with real URLs and images",
  "endpoints": {
    "health": "/health",
    "stores": "/sonar/stores/search",
    "products": "/sonar/products/search"
  },
  "features": [
    "AI-powered product search",
    "Real product URLs and images",
    "Store discovery",
    "Smart product matching"
  ]
}
```

## 🔍 Error Responses

### Error Format

All error responses follow this format:

```json
{
  "error": "Error message",
  "detail": "Detailed error information",
  "status_code": 400,
  "timestamp": "2025-08-19T15:42:58.731850"
}
```

### Common Error Codes

| Status Code | Description | Common Causes |
|-------------|-------------|---------------|
| `400` | Bad Request | Invalid parameters, missing required fields |
| `401` | Unauthorized | Invalid API keys |
| `404` | Not Found | Endpoint not found |
| `422` | Validation Error | Invalid parameter format |
| `500` | Internal Server Error | Server-side error, API service issues |
| `503` | Service Unavailable | External API services unavailable |

### Example Error Responses

**Missing Required Parameter:**
```json
{
  "error": "Missing required parameter",
  "detail": "Parameter 'query' is required for product search",
  "status_code": 400,
  "timestamp": "2025-08-19T15:42:58.731850"
}
```

**Invalid API Key:**
```json
{
  "error": "Invalid API key",
  "detail": "The provided Perplexity API key is invalid",
  "status_code": 401,
  "timestamp": "2025-08-19T15:42:58.731850"
}
```

**Service Unavailable:**
```json
{
  "error": "Service temporarily unavailable",
  "detail": "Serper.dev API is currently unavailable",
  "status_code": 503,
  "timestamp": "2025-08-19T15:42:58.731850"
}
```

## 📝 Usage Examples

### Python Examples

#### Search for Products
```python
import requests

# Search for oat milk at Target
response = requests.get(
    "http://localhost:8000/sonar/products/search",
    params={
        "query": "oat milk",
        "store_name": "Target",
        "location": "Chicago,IL"
    }
)

if response.status_code == 200:
    data = response.json()
    print(f"Found {data['products_found']} products")
    
    for product in data['products']:
        print(f"- {product['name']}: ${product['price']}")
        print(f"  Image: {product['image_url']}")
        print(f"  URL: {product['product_url']}")
else:
    print(f"Error: {response.status_code} - {response.text}")
```

#### Find Stores
```python
import requests

# Find stores in New York
response = requests.get(
    "http://localhost:8000/sonar/stores/search",
    params={"location": "New York,NY"}
)

if response.status_code == 200:
    data = response.json()
    print(f"Found {data['stores_found']} stores")
    
    for store in data['stores']:
        print(f"- {store['store_name']}: {store['address']}")
        print(f"  Services: {', '.join(store['services'])}")
```

### JavaScript Examples

#### Search for Products
```javascript
const axios = require('axios');

async function searchProducts() {
    try {
        const response = await axios.get('http://localhost:8000/sonar/products/search', {
            params: {
                query: 'organic bananas',
                store_name: 'Whole Foods',
                location: 'San Francisco,CA'
            }
        });
        
        console.log(`Found ${response.data.products_found} products`);
        response.data.products.forEach(product => {
            console.log(`- ${product.name}: $${product.price}`);
            console.log(`  Image: ${product.image_url}`);
            console.log(`  URL: ${product.product_url}`);
        });
    } catch (error) {
        console.error('Error:', error.response?.data || error.message);
    }
}

searchProducts();
```

#### Find Stores
```javascript
const axios = require('axios');

async function findStores() {
    try {
        const response = await axios.get('http://localhost:8000/sonar/stores/search', {
            params: { location: 'Los Angeles,CA' }
        });
        
        console.log(`Found ${response.data.stores_found} stores`);
        response.data.stores.forEach(store => {
            console.log(`- ${store.store_name}: ${store.address}`);
            console.log(`  Services: ${store.services.join(', ')}`);
        });
    } catch (error) {
        console.error('Error:', error.response?.data || error.message);
    }
}

findStores();
```

### cURL Examples

#### Search for Milk at Target
```bash
curl -X GET "http://localhost:8000/sonar/products/search" \
  -G \
  -d "query=milk" \
  -d "store_name=Target" \
  -d "location=Chicago,IL" \
  | python -m json.tool
```

#### Find Stores in Boston
```bash
curl -X GET "http://localhost:8000/sonar/stores/search" \
  -G \
  -d "location=Boston,MA" \
  | python -m json.tool
```

#### URL-Encoded Search
```bash
curl "http://localhost:8000/sonar/products/search?query=$(echo -n 'almond milk' | jq -sRr @uri)&store_name=$(echo -n 'Trader Joes' | jq -sRr @uri)&location=$(echo -n 'Los Angeles,CA' | jq -sRr @uri)"
```

## 🔧 Rate Limits

Currently, there are no rate limits on the API endpoints. However, the underlying services (Perplexity Sonar and Serper.dev) may have their own rate limits:

- **Perplexity Sonar**: Check your account limits
- **Serper.dev**: Check your account credits

## 📈 Performance

- **Response Time**: Typically < 5 seconds for product searches
- **Concurrent Requests**: Supports multiple simultaneous requests
- **Caching**: Intelligent caching reduces API calls
- **Timeout**: 30-second timeout for external API calls

## 🔒 Security

- **API Keys**: Stored securely in environment variables
- **Input Validation**: All inputs are validated using Pydantic models
- **Error Sanitization**: Error messages don't expose sensitive information
- **HTTPS**: Use HTTPS in production environments

---

**For more information, see the [Getting Started Guide](GETTING_STARTED.md) and [README](README.md).**
