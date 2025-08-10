# Grocery Scraper API

A professional FastAPI service for scraping real grocery store product data using Selenium.

## 🚀 Features

- **Real Data Scraping** - Uses Selenium to scrape actual grocery websites
- **Multiple Stores** - Supports Giant Eagle, Wegmans, ALDI, Albertsons, ShopRite
- **Professional API** - FastAPI with automatic OpenAPI documentation
- **Production Ready** - Docker support, health checks, error handling
- **Type Safe** - Full Pydantic model validation

## 📁 Project Structure

```
grocery-scraper-api/
├── main.py                 # FastAPI application entry point
├── requirements.txt        # Python dependencies
├── Dockerfile             # Container configuration
├── README.md              # This file
├── scraper/               # Scraper package
│   ├── __init__.py        # Package initialization
│   ├── core.py            # Core scraping logic
│   ├── models.py          # Pydantic models
│   └── config.py          # Store configurations
└── tests/                 # Test files (optional)
```

## 🛠️ Installation

### Local Development

1. **Clone and setup:**
   ```bash
   cd grocery-scraper-api
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   pip install -r requirements.txt
   ```

2. **Run the API:**
   ```bash
   uvicorn main:app --reload
   ```

3. **Access the API:**
   - API: http://localhost:8000
   - Documentation: http://localhost:8000/docs
   - Alternative docs: http://localhost:8000/redoc

### Docker

```bash
docker build -t grocery-scraper-api .
docker run -p 8000:8000 grocery-scraper-api
```

## 🌐 API Endpoints

### Core Endpoints

- `GET /` - API information
- `GET /health` - Health check
- `GET /stores` - List supported stores
- `POST /scrape` - Scrape products (main endpoint)
- `GET /scrape` - Scrape products (GET version)
- `GET /test/{store}` - Quick test for a store

### Example Usage

**Scrape products:**
```bash
curl -X POST "http://localhost:8000/scrape" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "milk",
    "store": "gianteagle",
    "zipcode": "15213"
  }'
```

**Quick test:**
```bash
curl "http://localhost:8000/scrape?query=milk&store=gianteagle&zipcode=15213"
```

## 🏪 Supported Stores

| Store | Status | Products Found | Notes |
|-------|--------|----------------|-------|
| Giant Eagle | ✅ Working | ~11 products | Best performance |
| Wegmans | ✅ Working | ~6 products | Reliable |
| ALDI | ✅ Working | ~15 products | Good variety |
| Albertsons | ⚠️ Limited | Variable | May have restrictions |
| ShopRite | ⚠️ Limited | Variable | May have restrictions |

## 📊 Response Format

```json
{
  "success": true,
  "store": "gianteagle",
  "query": "milk",
  "zipcode": "15213",
  "result_count": 11,
  "scraper_type": "real",
  "timestamp": "2024-01-07T12:00:00",
  "listings": [
    {
      "title": "Giant Eagle 2% Reduced Fat Milk",
      "product_name": "Giant Eagle 2% Reduced Fat Milk",
      "brand": "Giant Eagle",
      "price": "$3.99",
      "image_url": "https://...",
      "availability": "In Stock",
      "description": "Giant Eagle 2% Reduced Fat Milk"
    }
  ]
}
```

## 🚀 Deployment

### Render.com (Recommended)

1. Push this folder to GitHub
2. Connect to Render.com
3. Create new Web Service
4. Configure:
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `uvicorn main:app --host 0.0.0.0 --port $PORT`

### Railway

```bash
railway login
railway init
railway up
```

### Heroku

```bash
echo "web: uvicorn main:app --host 0.0.0.0 --port \$PORT" > Procfile
heroku create your-scraper-api
git push heroku main
```

## 🧪 Testing

**Test health:**
```bash
curl http://localhost:8000/health
```

**Test stores:**
```bash
curl http://localhost:8000/stores
```

**Test scraping:**
```bash
curl "http://localhost:8000/test/gianteagle"
```

## ⚙️ Configuration

### Environment Variables

- `PORT` - Server port (default: 8000)
- `CHROME_BIN` - Chrome binary path (for Docker)
- `DISPLAY` - Display for headless mode (for Docker)

### Scraper Settings

Edit `scraper/config.py` to modify:
- Store configurations
- Selectors
- Timeouts
- User agents

## 🔧 Development

### Adding New Stores

1. Add store config to `scraper/config.py`
2. Test selectors with browser dev tools
3. Update `SUPPORTED_STORES` dictionary
4. Test with `/test/{store}` endpoint

### Debugging

- Check logs for scraping details
- Use `/health` endpoint to verify Selenium
- Test individual stores with `/test/{store}`
- Enable non-headless mode for visual debugging

## 📝 License

MIT License - feel free to use in your projects!

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## 📞 Support

- Check the `/docs` endpoint for API documentation
- Review logs for debugging information
- Ensure Chrome is installed for Selenium functionality
