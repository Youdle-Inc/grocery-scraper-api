# 🛒 Grocery Scraper API

A powerful AI-powered grocery product discovery API that uses **Exa API** for intelligent product search with real URLs and images.

**🌐 Live API**: https://grocery-scraper-api.vercel.app

**📖 API Documentation**: https://grocery-scraper-api.vercel.app/swagger

## 🚀 Quick Reference

```bash
# Health check
curl https://grocery-scraper-api.vercel.app/health

# Find stores in any ZIP code
curl "https://grocery-scraper-api.vercel.app/stores/38125"

# Search products with location filtering
curl "https://grocery-scraper-api.vercel.app/products/search?query=milk&zipcode=38125"

# Compare products across stores
curl "https://grocery-scraper-api.vercel.app/products/aggregate?query=eggs&zipcode=38125&limit=10"
```

See [TEST_CURL_COMMANDS.md](./TEST_CURL_COMMANDS.md) for comprehensive examples.

## ✨ Features

### 🤖 AI-Powered Product Discovery
- **Exa API Integration**: Uses advanced AI to find products across multiple stores
- **Smart Product Matching**: Intelligent matching of product names and descriptions
- **Real-time Store Discovery**: Find grocery stores in any location with detailed information

### 🔗 Real Product Data
- **Real Product URLs**: Direct links to product pages from Exa's web search
- **High-Quality Images**: Product images from web search results (800x800+ resolution)
- **Live Pricing**: Current prices from various retailers
- **Customer Ratings**: Real ratings and review counts
- **Store-Specific Results**: Filter by Target, Walmart, Safeway, and more
- **Multi-Store Comparison**: Compare products across multiple retailers in one request
- **Location-Based Filtering**: Works with any ZIP code for accurate location-based results
- **Perplexity-Style Insights**: Overview summaries and follow-up query suggestions
- **Real-Time Streaming**: Get results as they come in with Server-Sent Events
- **AI Validation**: Automatically filters out generic placeholders and validates product data quality

### 🚀 Performance & Reliability
- **Fast Response Times**: Optimized for quick product searches
- **Robust Error Handling**: Graceful fallbacks and detailed error messages
- **Caching**: Intelligent caching for improved performance
- **Async Processing**: Non-blocking API calls for better scalability

## 🏗️ Architecture

```
┌─────────────────┐    ┌─────────────────┐
│   FastAPI App   │───▶│  Exa API        │
│                 │    │  Web Search     │
└─────────────────┘    └─────────────────┘
         │                       │
         ▼                       ▼
┌─────────────────┐    ┌─────────────────┐
│   Product       │    │   Store          │    │   Real URLs &   │
│   Matching      │    │   Discovery      │    │   Images        │
└─────────────────┘    └──────────────────┘    └─────────────────┘
```

## 🚀 Quick Start

### 1. Clone and Setup
```bash
git clone <your-repo>
cd grocery-scraper-api
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Configure API Keys
Create a `.env` file in the project root:
```bash
# Required: Exa API Key (for real product URLs and images)
EXA_API_KEY=your_exa_api_key_here
```

### 3. Run the API
```bash
uvicorn main:app --host 0.0.0.0 --port 8000
```

### 4. Test the API
```bash
# Find stores in a location
curl "http://localhost:8000/stores/60601"

# Search for products with real URLs and images
curl "http://localhost:8000/products/search?query=milk&zipcode=60601"

# Compare products across all stores
curl "http://localhost:8000/products/aggregate?query=eggs&zipcode=60601&limit=10"
```

## 📚 API Endpoints

### Health Check
```http
GET /health
```
Check API status and service availability.

### Store Discovery
```http
GET /stores/{zipcode}?store_chain={optional}
```
Find grocery stores in a specific ZIP code.

**Parameters:**
- `zipcode` (path, required): 5-digit ZIP code (e.g., 60601, 38125)
- `store_chain` (query, optional): Filter by specific store (e.g., "Target", "Walmart")

**Example:**
```bash
curl "http://localhost:8000/stores/38125"
curl "http://localhost:8000/stores/38125?store_chain=Target"
```

**Example Response:**
```json
{
  "zipcode": "38125",
  "stores_found": 5,
  "stores": [
    {
      "store_id": "target",
      "store_name": "Target",
      "address": "123 Main St, Memphis, TN 38125",
      "services": ["delivery", "pickup", "in-store"],
      "status": "active",
      "zipcode": "38125",
      "location": {
        "zipcode": "38125",
        "city": "Memphis",
        "state": "TN"
      }
    }
  ],
  "source": "exa_structured",
  "api_version": "2.0.0"
}
```

### Product Search
```http
GET /products/search?query={product}&zipcode={zipcode}&store_name={optional}&num_results={optional}
```
Search for products with AI-powered semantic search.

**Parameters:**
- `query` (required): Product search term (e.g., "milk", "organic eggs")
- `zipcode` (optional): 5-digit ZIP code for location-based results
- `store_name` (optional): Filter by store (e.g., "Target", "Walmart")
- `num_results` (optional): Number of results (default: 20, max: 50)
- `refresh` (optional): Bypass cache (default: false)

**Example:**
```bash
curl "http://localhost:8000/products/search?query=milk&zipcode=38125"
curl "http://localhost:8000/products/search?query=organic+eggs&store_name=Target&zipcode=38125&num_results=10"
```

**Example Response:**
```json
{
  "query": "milk",
  "store_name": "All Stores",
  "location": "38125",
  "products_found": 5,
  "search_timestamp": "2025-11-04T20:43:46.843917Z",
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
      "store_zipcode": "38125",
      "availability": "Check Store"
    }
  ],
  "source": "exa_structured",
  "api_version": "2.0.0"
}
```

### Aggregate Products (Compare Across Stores)
```http
GET /products/aggregate?query={product}&zipcode={zipcode}&limit={optional}&stores={optional}
```
Compare the same products across multiple stores to find the best deals.

**Parameters:**
- `query` (required): Product to search for (e.g., "eggs", "milk", "bread")
- `zipcode` (required): 5-digit ZIP code for location-based results
- `limit` (optional): Maximum number of products to return (default: 50, max: 100)
- `stores` (optional): Comma-separated store IDs (e.g., "target,walmart")
- `all_stores` (optional): Search all 28 supported stores instead of default top 5 (default: false)
- `radius_miles` (optional): Search radius in miles (default: 10, max: 50)
- `refresh` (optional): Bypass cache (default: false)

**Example:**
```bash
# Compare eggs across all stores
curl "http://localhost:8000/products/aggregate?query=eggs&zipcode=38125"

# Compare with limit
curl "http://localhost:8000/products/aggregate?query=eggs&zipcode=38125&limit=10"

# Compare specific stores only
curl "http://localhost:8000/products/aggregate?query=milk&zipcode=38125&stores=target,walmart"

# Search all 28 supported stores
curl "http://localhost:8000/products/aggregate?query=eggs&zipcode=38125&all_stores=true"

# Stream results in real-time (for web apps)
curl -N "http://localhost:8000/products/aggregate/stream?query=eggs&zipcode=38125&stores=target,walmart"
```

**Example Response:**
```json
{
  "query": "eggs",
  "zipcode": "38125",
  "search_timestamp": "2025-11-04T20:43:46.843917Z",
  "results": [
    {
      "name": "Vital Farms Pasture Raised Eggs",
      "brand": "Target",
      "category_path": ["Dairy & Eggs", "Eggs"],
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
            "store_name": "Target",
            "address": "123 Main St",
            "city": "Memphis",
            "state": "TN",
            "zipcode": "38125"
          },
          "product_url": "https://www.target.com/p/vital-farms-pasture-raised-eggs/-/A-94684060",
          "fulfillment": ["PICKUP", "DELIVERY"],
          "availability": "CHECK_STORE",
          "regular_price": 6.99
        }
      ],
      "source": "scraper_v2"
    }
  ],
  "stores_considered": ["target", "walmart", "whole_foods", "kroger", "aldi"],
  "overview": "Found 10 products for 'eggs' across 5 stores ranging from $3.99 to $5.99 including brands like Target, Walmart in categories: Dairy & Eggs, Eggs near 38125.",
  "follow_up_queries": [
    "milk",
    "butter",
    "Target eggs",
    "organic eggs",
    "cheapest eggs",
    "best deals on eggs"
  ],
  "meta": {
    "api_version": "2.1.0",
    "cache": {"hit": false}
  }
}
```

## 🔧 Configuration

### Environment Variables

| Variable | Description | Required | Example |
|----------|-------------|----------|---------|
| `EXA_API_KEY` | Exa API key | ✅ | `exa-abc123...` |

### API Response Fields

#### Product Fields
- `name`: Product name
- `price`: Current price (float)
- `currency`: Currency code (default: USD)
- `availability`: Stock status
- `category`: Product category
- `brand`: Brand name
- `size` / `quantity`: Product size/volume
- `description`: Product description
- `image_url`: **Real product image URL** (high-quality, 800x800+)
- `product_url`: **Real product page URL** (direct link to store)
- `rating`: Customer rating (1-5)
- `reviews_count`: Number of reviews
- `store_name`: Store where product is available
- `store_zipcode`: ZIP code of the store location
- `store_address`: Full store address (in aggregate endpoint)

#### Aggregate Response Fields
- `results`: Array of grouped products
  - `name`: Product name
  - `brand`: Brand name
  - `category_path`: Product category hierarchy
  - `images`: Array of product images with `url` and `is_primary` flag
  - `offers`: Array of offers from different stores
    - `store`: Store information (retailer, store_name, address, city, state, zipcode)
    - `product_url`: Direct link to product page (includes location parameters)
    - `regular_price`: Regular price
    - `sale_price`: Sale price (if on sale)
    - `fulfillment`: Array of fulfillment options (PICKUP, DELIVERY, IN_STORE)
    - `availability`: Stock availability status (IN_STOCK, OUT_OF_STOCK, LOW_STOCK, CHECK_STORE)
- `overview`: Natural language summary of search results (Perplexity-style)
- `follow_up_queries`: Suggested related searches (array of query strings)

## 🛠️ Development

### Project Structure
```
grocery-scraper-api/
├── main.py                 # FastAPI application
├── scraper/
│   ├── exa_structured_client.py  # Exa API integration
│   ├── exa_client.py       # Exa API integration
│   ├── models.py           # Pydantic models
│   └── config.py           # Configuration
├── requirements.txt        # Python dependencies
└── .env                    # Environment variables
```

### Key Components

#### ExaStructuredClient (`scraper/exa_structured_client.py`)
- Handles Exa API communication
- Parses AI-generated product information
- Manages store discovery and product search

#### ExaClient (`scraper/exa_client.py`)
- Integrates with Exa API for web search data
- Provides real product URLs and images
- Matches products by name similarity

### Testing
```bash
# Test the API endpoints
python test_sonar.py

# Test Exa API integration
python test_exa_integration.py
```

## 🔍 How It Works

### 1. Product Search Flow
1. **User Request**: Search for "oat milk" in ZIP code 38125
2. **Location Filtering**: Query includes explicit location terms (city, state, zipcode) for accurate results
3. **Exa API**: AI finds products with names, prices, descriptions near the specified location
4. **Structured Data**: Gets real URLs and images from web search
5. **Smart Matching**: Matches products by name similarity
6. **Response**: Returns structured data with real URLs and images from stores in the requested location

### 2. Store Discovery Flow
1. **User Request**: Find stores in ZIP code "38125"
2. **Location Query**: Builds explicit location-aware search query
3. **Exa API**: AI discovers grocery stores in the specified area
4. **Response**: Returns store details with addresses and services from the requested location

### 3. Aggregate Products Flow
1. **User Request**: Compare "eggs" across stores in ZIP code 38125
2. **Multi-Store Search**: Searches each store chain concurrently (Target, Walmart, etc.)
3. **Location Filtering**: Each search includes location context for accurate results
4. **Product Grouping**: Groups identical products together
5. **Store Matching**: Matches products to stores in the requested location
6. **Response**: Returns grouped products with offers from multiple stores

## 🎯 Use Cases

- **E-commerce Integration**: Add real product data to your shopping apps
- **Price Comparison**: Compare prices across multiple stores in any location
- **Location-Based Shopping**: Find products available in specific ZIP codes
- **Inventory Management**: Check product availability and pricing by location
- **Market Research**: Analyze product offerings and pricing trends by region
- **Mobile Apps**: Power grocery shopping and price comparison apps with location awareness
- **Multi-Store Comparison**: Find the best deals across retailers in one request

## 🚀 Performance

- **Response Time**: < 5 seconds for product searches
- **Concurrent Requests**: Supports multiple simultaneous searches
- **Caching**: Intelligent caching reduces API calls
- **Error Handling**: Graceful fallbacks for failed requests

## 🔒 Security

- **API Keys**: Stored securely in environment variables
- **No Hardcoded Secrets**: All sensitive data in `.env` file
- **Input Validation**: Pydantic models validate all inputs
- **Error Sanitization**: Safe error messages without sensitive data

## ✨ Recent Updates

### Version 3.0.0
- ✅ **Perplexity-Style Insights**: Overview summaries and follow-up query suggestions
- ✅ **Streaming API**: Real-time results via Server-Sent Events (`/products/aggregate/stream`)
- ✅ **Enhanced Availability Detection**: Accurate stock status (IN_STOCK, OUT_OF_STOCK, LOW_STOCK)
- ✅ **URL Location Enhancement**: Product URLs include zipcode parameters for location-specific pricing
- ✅ **All Stores Parameter**: Option to search all 28 stores with `all_stores=true`
- ✅ **Universal Search**: AI-powered query understanding and multi-strategy search
- ✅ **28+ Supported Stores**: Comprehensive store coverage
- ✅ **AI Product Validation**: Automatically filters out generic/placeholder products and validates real prices

### Version 2.1.0
- ✅ **Universal Location Filtering**: Works with any ZIP code, not just hardcoded locations
- ✅ **Aggregate Endpoint**: Compare products across multiple stores in one request
- ✅ **Limit Parameter**: Control number of results returned (default: 50, max: 100)
- ✅ **Enhanced Location Queries**: Improved search queries for better location-based filtering
- ✅ **Store Location Matching**: Accurate store-to-product matching by location

## 📈 Future Enhancements

- [ ] **Price History**: Track price changes over time
- [ ] **Nutritional Data**: Add nutritional information for products
- [ ] **Inventory Alerts**: Notify when products come back in stock
- [ ] **Multi-language Support**: Support for international stores
- [ ] **Advanced Filtering**: Filter by price range, brand, etc.
- [ ] **Webhook Support**: Real-time product updates
- [ ] **Distance Calculation**: Calculate distance from user location to stores

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🆘 Support

- **Documentation**: Check this README and inline code comments
- **Issues**: Create an issue on GitHub for bugs or feature requests
- **API Keys**: Get help with Exa API setup

---

**Built with ❤️ using FastAPI and Exa API**

