# 🚀 Getting Started Guide

This guide will walk you through setting up the Grocery Scraper API from scratch, including obtaining API keys and testing the integration.

## 📋 Prerequisites

- **Python 3.8+** installed on your system
- **Git** for cloning the repository
- **A terminal/command prompt** for running commands
- **Internet connection** for downloading dependencies and API access

## 🛠️ Step 1: Project Setup

### Clone the Repository
```bash
git clone <your-repository-url>
cd grocery-scraper-api
```

### Create Virtual Environment
```bash
# Create a virtual environment
python -m venv venv

# Activate the virtual environment
# On macOS/Linux:
source venv/bin/activate

# On Windows:
venv\Scripts\activate
```

### Install Dependencies
```bash
pip install -r requirements.txt
```

## 🔑 Step 2: API Key Setup

You'll need two API keys for full functionality:

### 2.1 Perplexity Sonar API Key

**What it does**: Provides AI-powered product search and store discovery

1. **Sign up for Perplexity AI**:
   - Go to [https://www.perplexity.ai/](https://www.perplexity.ai/)
   - Create an account or sign in

2. **Get your API key**:
   - Navigate to your account settings
   - Find the API section
   - Generate a new API key
   - Copy the key (it starts with `pplx-`)

3. **Test your key**:
   ```bash
   curl -X POST "https://api.perplexity.ai/chat/completions" \
     -H "Authorization: Bearer YOUR_API_KEY" \
     -H "Content-Type: application/json" \
     -d '{
       "model": "llama-3.1-sonar-small-128k-online",
       "messages": [{"role": "user", "content": "Hello"}]
     }'
   ```

### 2.2 Serper.dev API Key

**What it does**: Provides real product URLs and images from Google Shopping

1. **Sign up for Serper.dev**:
   - Go to [https://serper.dev/](https://serper.dev/)
   - Create an account

2. **Get your API key**:
   - After signing up, you'll get free credits
   - Your API key will be displayed in your dashboard
   - Copy the key (it's a long string of characters)

3. **Test your key**:
   ```bash
   curl -X POST "https://google.serper.dev/search" \
     -H "X-API-KEY: YOUR_API_KEY" \
     -H "Content-Type: application/json" \
     -d '{"q":"milk","gl":"us","hl":"en","num":1,"type":"shopping"}'
   ```

## ⚙️ Step 3: Environment Configuration

### Create Environment File
Create a `.env` file in the project root:

```bash
# Create the .env file
touch .env
```

### Add Your API Keys
Edit the `.env` file and add your API keys:

```env
# Perplexity Sonar API Key (required)
PERPLEXITY_API_KEY=pplx-your-perplexity-api-key-here

# Serper.dev API Key (required for real product URLs and images)
SERPER_API_KEY=your-serper-api-key-here
```

**Important**: 
- Don't include quotes around the API keys
- Don't add spaces around the `=` sign
- Make sure there are no extra characters or spaces

### Verify Environment Setup
```bash
# Test that your environment variables are loaded
python -c "import os; from dotenv import load_dotenv; load_dotenv(); print('PERPLEXITY_API_KEY:', '✅' if os.getenv('PERPLEXITY_API_KEY') else '❌'); print('SERPER_API_KEY:', '✅' if os.getenv('SERPER_API_KEY') else '❌')"
```

## 🚀 Step 4: Start the API Server

### Start the Server
```bash
# Make sure your virtual environment is activated
source venv/bin/activate

# Start the FastAPI server
uvicorn main:app --host 0.0.0.0 --port 8000
```

You should see output like:
```
INFO:     Started server process [12345]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
```

### Verify Server is Running
```bash
# Test the health endpoint
curl http://localhost:8000/health
```

You should get a response like:
```json
{
  "status": "healthy",
  "timestamp": "2025-08-19T15:42:58.731850",
  "version": "1.0.0"
}
```

## 🧪 Step 5: Test the API

### Test Store Discovery
```bash
# Find stores in a location
curl "http://localhost:8000/sonar/stores/search?location=Chicago,IL" | python -m json.tool
```

Expected response:
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
    }
  ],
  "source": "perplexity_sonar"
}
```

### Test Product Search
```bash
# Search for products with real URLs and images
curl "http://localhost:8000/sonar/products/search?query=milk&store_name=Target&location=Chicago,IL" | python -m json.tool
```

Expected response:
```json
{
  "query": "milk",
  "store_name": "Target",
  "location": "Chicago, IL",
  "products_found": 8,
  "search_timestamp": "2025-08-19T15:42:58.731850",
  "products": [
    {
      "name": "Organic 2% Reduced Fat Milk - 1 gallon",
      "price": 9.19,
      "availability": "in stock",
      "category": "Dairy",
      "brand": "Good & Gather™",
      "size": "1 gallon",
      "description": "Organic 2% reduced fat milk, USDA certified organic",
      "image_url": "https://encrypted-tbn1.gstatic.com/shopping?q=tbn:ANd9GcQ77QBCxGp6Fl572X73iaEEaL5qnAB5nse4cjxqaNTr0Hqi8FVhC5xGni3IMPlWoh58k-yhTqQPooAnLWDuwh0R9ucDakiD0Q",
      "product_url": "https://google.com/shopping/product/2512895342606972574?gl=us",
      "rating": 4.5,
      "reviews_count": 1250
    }
  ],
  "source": "perplexity_sonar + serper_dev"
}
```

## 🔍 Step 6: Troubleshooting

### Common Issues

#### 1. "No module named 'aiohttp'"
```bash
# Solution: Install missing dependency
pip install aiohttp
```

#### 2. "Invalid Perplexity API key"
- Check that your API key starts with `pplx-`
- Verify the key is correctly copied to the `.env` file
- Test the key directly with the curl command above

#### 3. "Invalid Serper.dev API key"
- Verify your API key is correctly copied
- Check that you have credits in your Serper.dev account
- Test the key directly with the curl command above

#### 4. "ModuleNotFoundError"
```bash
# Solution: Make sure virtual environment is activated
source venv/bin/activate
pip install -r requirements.txt
```

#### 5. "Port 8000 already in use"
```bash
# Solution: Use a different port
uvicorn main:app --host 0.0.0.0 --port 8001

# Or kill the existing process
pkill -f uvicorn
```

### Debug Mode
For detailed logging, start the server with debug mode:
```bash
uvicorn main:app --host 0.0.0.0 --port 8000 --log-level debug
```

## 📚 Step 7: API Documentation

### Interactive Documentation
Once your server is running, visit:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

### Available Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | API information |
| `/health` | GET | Health check |
| `/sonar/stores/search` | GET | Find stores in a location |
| `/sonar/products/search` | GET | Search for products |

### Example API Calls

#### Find Stores
```bash
curl "http://localhost:8000/sonar/stores/search?location=New%20York,NY"
```

#### Search Products
```bash
curl "http://localhost:8000/sonar/products/search?query=organic%20bananas&store_name=Whole%20Foods&location=San%20Francisco,CA"
```

#### Search with URL Encoding
```bash
curl "http://localhost:8000/sonar/products/search?query=$(echo -n 'almond milk' | jq -sRr @uri)&store_name=$(echo -n 'Trader Joes' | jq -sRr @uri)&location=$(echo -n 'Los Angeles,CA' | jq -sRr @uri)"
```

## 🎯 Step 8: Integration Examples

### Python Integration
```python
import requests
import json

# Search for products
response = requests.get(
    "http://localhost:8000/sonar/products/search",
    params={
        "query": "oat milk",
        "store_name": "Target",
        "location": "Chicago,IL"
    }
)

products = response.json()
print(f"Found {products['products_found']} products")

for product in products['products']:
    print(f"- {product['name']}: ${product['price']}")
    print(f"  Image: {product['image_url']}")
    print(f"  URL: {product['product_url']}")
```

### JavaScript/Node.js Integration
```javascript
const axios = require('axios');

async function searchProducts() {
    try {
        const response = await axios.get('http://localhost:8000/sonar/products/search', {
            params: {
                query: 'oat milk',
                store_name: 'Target',
                location: 'Chicago,IL'
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

## 🔧 Step 9: Production Deployment

### Environment Variables for Production
```env
# Production settings
PERPLEXITY_API_KEY=your-production-perplexity-key
SERPER_API_KEY=your-production-serper-key
PORT=8000
HOST=0.0.0.0
```

### Docker Deployment
```bash
# Build the Docker image
docker build -t grocery-scraper-api .

# Run the container
docker run -p 8000:8000 --env-file .env grocery-scraper-api
```

### Systemd Service (Linux)
Create `/etc/systemd/system/grocery-api.service`:
```ini
[Unit]
Description=Grocery Scraper API
After=network.target

[Service]
Type=simple
User=your-user
WorkingDirectory=/path/to/grocery-scraper-api
Environment=PATH=/path/to/grocery-scraper-api/venv/bin
ExecStart=/path/to/grocery-scraper-api/venv/bin/uvicorn main:app --host 0.0.0.0 --port 8000
Restart=always

[Install]
WantedBy=multi-user.target
```

Enable and start the service:
```bash
sudo systemctl enable grocery-api
sudo systemctl start grocery-api
```

## 🎉 Congratulations!

You've successfully set up the Grocery Scraper API! You now have:

- ✅ **AI-powered product search** with Perplexity Sonar
- ✅ **Real product URLs and images** with Serper.dev
- ✅ **Store discovery** in any location
- ✅ **Fast, reliable API** ready for production use

## 📞 Need Help?

- **Documentation**: Check the main README.md
- **Issues**: Create an issue on GitHub
- **API Keys**: Contact Perplexity AI or Serper.dev support
- **Code Questions**: Check the inline comments in the source code

---

**Happy coding! 🚀**
