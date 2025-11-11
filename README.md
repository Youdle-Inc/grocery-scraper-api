# 🛒 Grocery Scraper API

A powerful grocery product discovery API that uses **Serper API** (Google Search) for real-time product search with pricing, availability, and location-scoped results across 28+ major retailers.

**🌐 Live API**: https://grocery-scraper-api.vercel.app

**📖 API Documentation**: https://grocery-scraper-api.vercel.app/swagger

## 🚀 Quick Reference

```bash
# Health check
curl https://grocery-scraper-api.vercel.app/health

# Find stores in any ZIP code
curl "https://grocery-scraper-api.vercel.app/stores/60601"

# Search products with location filtering
curl "https://grocery-scraper-api.vercel.app/products/search?query=milk&zipcode=60601"

# Compare products across stores
curl "https://grocery-scraper-api.vercel.app/products/aggregate?query=eggs&zipcode=60601&limit=10"
```

See [TEST_LOCALHOST.md](./TEST_LOCALHOST.md) for comprehensive testing examples.

## ✨ Features

### 🤖 Real-Time Product Discovery
- **Serper API Integration**: Google-powered search across 28+ major retailers
- **Smart Product Matching**: Intelligent matching of product names and descriptions
- **Real-time Store Discovery**: Find grocery stores in any location with detailed information
- **Enhanced Address Extraction**: Accurate street addresses, cities, and states from search results
- **Robust Price Extraction**: Multiple regex patterns to extract prices from various formats

### 🔗 Real Product Data
- **Real Product URLs**: Direct links to store product pages
- **High-Quality Images**: Product images from store CDNs (800x800+ resolution)
- **Live Pricing**: Real-time prices extracted from search results
- **Real-Time Availability**: Current stock status (IN_STOCK, OUT_OF_STOCK, LOW_STOCK, CHECK_STORE)
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
│   FastAPI App   │───▶│   Serper API     │
│                 │    │   (Google Search)│
└─────────────────┘    └─────────────────┘
         │                       │
         ▼                       ▼
┌─────────────────┐    ┌─────────────────┐
│   Product       │    │   Store          │
│   Matching      │    │   Discovery      │
│   & Ranking     │    │   & Address      │
└─────────────────┘    │   Extraction     │
                       └─────────────────┘
         │
         ▼
┌─────────────────┐
│   AI Scraper    │───▶ Price & Availability
│   (Enrichment)  │    Enhancement
└─────────────────┘
```

## 🚀 Quick Start

### 1. Clone and Setup
```bash
git clone https://github.com/Youdle-Inc/grocery-scraper-api.git
cd grocery-scraper-api
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Configure API Keys
Create a `.env` file in the project root:
```bash
# Required: Serper API Key (Google Search API)
SERPER_API_KEY=your_serper_api_key_here

# Optional: OpenAI API Key (for AI product validation and enrichment)
OPENAI_API_KEY=your_openai_api_key_here

# Optional: Anthropic API Key (alternative to OpenAI)
ANTHROPIC_API_KEY=your_anthropic_api_key_here
```

**Getting a Serper API Key:**
1. Sign up for [Serper API](https://serper.dev/)
2. Get your API key from the dashboard
3. Add it to your `.env` file

### 3. Run the API
```bash
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
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

See [TEST_LOCALHOST.md](./TEST_LOCALHOST.md) for comprehensive testing commands.

## 📚 API Endpoints

### Health Check
```http
GET /health
```
Check API status and service availability.

**Example:**
```bash
curl "http://localhost:8000/health"
```

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
curl "http://localhost:8000/stores/60601"
curl "http://localhost:8000/stores/60601?store_chain=Target"
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
curl "http://localhost:8000/products/search?query=milk&zipcode=60601"
curl "http://localhost:8000/products/search?query=organic+eggs&store_name=Target&zipcode=60601&num_results=10"
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
curl "http://localhost:8000/products/aggregate?query=eggs&zipcode=60601"

# Compare with limit
curl "http://localhost:8000/products/aggregate?query=eggs&zipcode=60601&limit=10"

# Compare specific stores only
curl "http://localhost:8000/products/aggregate?query=milk&zipcode=60601&stores=target,walmart"

# Search all 28 supported stores
curl "http://localhost:8000/products/aggregate?query=eggs&zipcode=60601&all_stores=true"

# Stream results in real-time (for web apps)
curl -N "http://localhost:8000/products/aggregate/stream?query=eggs&zipcode=60601&stores=target,walmart"
```

### Streaming API (Real-time Results)
```http
GET /products/aggregate/stream?query={product}&zipcode={zipcode}&stores={optional}&limit={optional}
```
Stream product results as they come in from each store using Server-Sent Events (SSE).

**Example:**
```bash
curl -N "http://localhost:8000/products/aggregate/stream?query=steak&zipcode=60601&stores=target,walmart&limit=3"
```

## 🏬 Supported Stores

The API supports 28+ major grocery retailers:

**National Chains:**
- Target • Walmart • Whole Foods • Kroger • Safeway • ALDI • Costco
- Trader Joe's • Sam's Club • Amazon Fresh • Meijer • WinCo Foods
- BJ's Wholesale Club • Dollar General • Dollar Tree

**Regional Chains:**
- Publix • H-E-B • Hy-Vee • Wegmans • Sprouts Farmers Market
- Giant Eagle • Price Chopper • Albertsons • Vons • Jewel-Osco
- Food Lion • Giant • Harris Teeter • Hannaford • Stop & Shop

## 🔧 Configuration

### Environment Variables

| Variable | Description | Required | Example |
|----------|-------------|----------|---------|
| `SERPER_API_KEY` | Serper API key (Google Search) | ✅ | `80ff8a83e123...` |
| `OPENAI_API_KEY` | OpenAI API key (for AI product validation) | ⚠️ Optional | `sk-proj-...` |
| `ANTHROPIC_API_KEY` | Anthropic API key (alternative to OpenAI) | ⚠️ Optional | `sk-ant-...` |

### API Response Fields

#### Product Fields
- `name`: Product name
- `price`: Current price (float)
- `currency`: Currency code (default: USD)
- `availability`: Stock status (IN_STOCK, OUT_OF_STOCK, LOW_STOCK, CHECK_STORE)
- `category`: Product category
- `brand`: Brand name
- `size` / `quantity`: Product size/volume
- `description`: Product description
- `image_url`: **Real product image URL** (high-quality, 800x800+)
- `product_url`: **Real product page URL** (direct link to store)
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
    - `product_url`: Direct link to product page
    - `regular_price`: Regular price
    - `sale_price`: Sale price (if on sale)
    - `fulfillment`: Array of fulfillment options (PICKUP, DELIVERY, IN_STORE)
    - `availability`: Stock availability status
- `overview`: Natural language summary of search results (Perplexity-style)
- `follow_up_queries`: Suggested related searches (array of query strings)

## 🛠️ Development

### Project Structure
```
grocery-scraper-api/
├── main.py                      # FastAPI application
├── scraper/
│   ├── serper_client.py        # Serper API integration
│   ├── universal_search.py      # Universal search orchestration
│   ├── availability_checker.py  # Availability detection
│   ├── ai_scraper.py            # AI-powered data enrichment
│   ├── product_validator.py     # Product validation
│   ├── models.py                 # Pydantic models
│   └── config.py                 # Configuration
├── requirements.txt             # Python dependencies
├── .env                          # Environment variables
├── test_localhost.sh            # Test script
└── TEST_LOCALHOST.md            # Testing guide
```

### Key Components

#### SerperClient (`scraper/serper_client.py`)
- Handles Serper API communication
- Extracts product information from Google Search results
- Manages store discovery and product search
- Enhanced address and price extraction

#### UniversalGrocerySearch (`scraper/universal_search.py`)
- Orchestrates multi-store product searches
- Handles query expansion and result aggregation
- Manages concurrent API calls

#### AvailabilityChecker (`scraper/availability_checker.py`)
- Checks product availability status
- Uses HTML scraping and AI for detection
- Returns IN_STOCK, OUT_OF_STOCK, LOW_STOCK statuses

#### ProductValidator (`scraper/product_validator.py`)
- AI-powered product data quality validation
- Filters out generic/placeholder products
- Validates product specificity, price authenticity, and URL validity

## 🔍 How It Works

### 1. Product Search Flow
1. **User Request**: Search for "milk" in ZIP code 60601
2. **Query Construction**: Builds optimized search queries with store filters
3. **Serper API**: Google Search finds products with names, prices, descriptions
4. **Data Extraction**: Extracts structured data (price, brand, quantity, address) using regex patterns
5. **Smart Matching**: Matches products by name similarity across stores
6. **AI Enrichment**: Optional AI scraper enhances missing prices and availability
7. **Response**: Returns structured data with real URLs and images

### 2. Store Discovery Flow
1. **User Request**: Find stores in ZIP code "60601"
2. **Location Query**: Builds location-aware search query
3. **Serper API**: Google Search discovers grocery stores in the specified area
4. **Address Extraction**: Extracts street addresses, cities, and states using regex
5. **Response**: Returns store details with accurate addresses

### 3. Aggregate Products Flow
1. **User Request**: Compare "eggs" across stores in ZIP code 60601
2. **Multi-Store Search**: Searches each store chain concurrently
3. **Location Filtering**: Each search includes location context
4. **Product Grouping**: Groups identical products together
5. **Store Matching**: Matches products to stores with accurate addresses
6. **Availability Checking**: Checks stock status for each product
7. **AI Validation**: Validates products are real (not generic placeholders)
8. **Response**: Returns grouped products with offers from multiple stores

## 🎯 Use Cases

- **E-commerce Integration**: Add real product data to your shopping apps
- **Price Comparison**: Compare prices across multiple stores in any location
- **Location-Based Shopping**: Find products available in specific ZIP codes
- **Inventory Management**: Check product availability and pricing by location
- **Market Research**: Analyze product offerings and pricing trends by region
- **Mobile Apps**: Power grocery shopping and price comparison apps
- **Multi-Store Comparison**: Find the best deals across retailers in one request

## 🚀 Performance

- **Response Time**: < 5 seconds for product searches
- **Concurrent Requests**: Supports multiple simultaneous searches
- **Caching**: Intelligent caching reduces API calls
- **Error Handling**: Graceful fallbacks for failed requests
- **Streaming**: Real-time results via Server-Sent Events

## 🔒 Security

- **API Keys**: Stored securely in environment variables
- **No Hardcoded Secrets**: All sensitive data in `.env` file
- **Input Validation**: Pydantic models validate all inputs
- **Error Sanitization**: Safe error messages without sensitive data

## ✨ Recent Updates

### Version 3.0.0
- ✅ **Serper API Integration**: Google-powered search across 28+ stores
- ✅ **Enhanced Address Extraction**: Accurate street addresses, cities, and states
- ✅ **Robust Price Extraction**: Multiple regex patterns for various price formats
- ✅ **Automatic Availability Detection**: Real-time stock status checking
- ✅ **Perplexity-Style Insights**: Overview summaries and follow-up query suggestions
- ✅ **Streaming API**: Real-time results via Server-Sent Events (`/products/aggregate/stream`)
- ✅ **URL Location Enhancement**: Product URLs include zipcode parameters
- ✅ **All Stores Parameter**: Option to search all 28 stores with `all_stores=true`
- ✅ **Universal Search**: AI-powered query understanding and multi-strategy search
- ✅ **AI Product Validation**: Automatically filters out generic/placeholder products

## 📈 Future Enhancements

- [ ] **Price History**: Track price changes over time
- [ ] **Nutritional Data**: Add nutritional information for products
- [ ] **Inventory Alerts**: Notify when products come back in stock
- [ ] **Multi-language Support**: Support for international stores
- [ ] **Advanced Filtering**: Filter by price range, brand, etc.
- [ ] **Webhook Support**: Real-time product updates
- [ ] **Distance Calculation**: Calculate distance from user location to stores

## 📚 Documentation

- [API Documentation](./API_DOCUMENTATION.md) - Complete API reference
- [Setup Guide](./SETUP_GUIDE.md) - Detailed setup instructions
- [Architecture](./ARCHITECTURE.md) - System architecture overview
- [Testing Guide](./TEST_LOCALHOST.md) - Comprehensive testing commands

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
- **API Keys**: Get help with Serper API setup at [serper.dev](https://serper.dev)

---

**Built with ❤️ using FastAPI and Serper API**
