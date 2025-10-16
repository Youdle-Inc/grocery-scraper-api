# 🔍 Exa API Setup Guide

This guide will help you set up Exa API integration for the Grocery Scraper API.

## What is Exa API?

Exa is a search engine made for AIs that provides:
- **Web Search**: Find webpages using embeddings-based or keyword search
- **Content Retrieval**: Get clean, parsed HTML from search results
- **Real URLs**: Direct links to product pages and images
- **AI-Optimized**: Designed specifically for AI applications

## 🚀 Quick Setup

### 1. Get Exa API Key

1. Visit [https://exa.ai](https://exa.ai)
2. Create an account or sign in
3. Go to your API dashboard
4. Generate a new API key
5. Copy the API key

### 2. Configure Your Environment

#### Option A: Use the Setup Script (Recommended)
```bash
python setup_exa.py
```

#### Option B: Manual Configuration
Add to your `.env` file:
```bash
EXA_API_KEY=your_exa_api_key_here
```

### 3. Test the Integration
```bash
python test_exa_integration.py
```

## 🔧 API Configuration

### Environment Variables
- `EXA_API_KEY`: Your Exa API key (required)

### API Endpoints Used
- **Search**: `POST https://api.exa.ai/search` - Find products and web pages
- **Contents**: `POST https://api.exa.ai/contents` - Get parsed content from URLs

## 📋 Features

### Product Search
- Search for products across multiple stores
- Get real product URLs and images
- Extract pricing information
- Filter by store domains

### Content Enhancement
- Enhance Perplexity Sonar results with real URLs
- Get high-quality product images
- Extract detailed product information
- Fallback when Sonar results are limited

### Store Integration
- Target (target.com)
- Walmart (walmart.com)
- Whole Foods Market (wholefoodsmarket.com)
- ALDI (aldi.us)
- Costco (costco.com)
- Kroger (kroger.com)

## 🧪 Testing

### Basic Test
```bash
python setup_exa.py test
```

### Full Integration Test
```bash
python test_exa_integration.py
```

### API Health Check
```bash
curl "http://localhost:8000/health"
```

Expected response:
```json
{
  "status": "healthy",
  "services": {
    "perplexity_sonar": "available",
    "exa_api": "available"
  }
}
```

## 🔍 Usage Examples

### Search Products
```python
from scraper.exa_client import ExaClient

client = ExaClient()
products = await client.search_products("organic milk", "Target", "United States")
```

### Enhance Perplexity Results
```python
# Get products from Perplexity Sonar
sonar_products = await sonar_client.search_products("milk", "Target", "10001")

# Enhance with Exa
enhanced_products = await exa_client.enhance_products_with_exa(
    sonar_products, "Target", "United States"
)
```

### Get Content from URLs
```python
urls = ["https://www.target.com/p/product-123"]
contents = await client.get_contents(urls)
```

## 🚨 Troubleshooting

### Common Issues

#### "Exa API not available"
- Check that `EXA_API_KEY` is set in your `.env` file
- Verify the API key is valid at [exa.ai](https://exa.ai)
- Ensure the key has sufficient credits

#### "Invalid API key"
- Regenerate your API key at [exa.ai](https://exa.ai)
- Check for extra spaces or characters in the key
- Verify the key format

#### "No products found"
- Try a different search query
- Check if the store domain is supported
- Verify your search location

### Debug Mode
Enable debug logging by setting the log level:
```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

## 📊 Rate Limits

Exa API has rate limits based on your plan:
- **Free Tier**: Limited requests per month
- **Pro Tier**: Higher limits with priority processing
- **Enterprise**: Custom limits and dedicated support

Check your usage at [exa.ai](https://exa.ai) dashboard.

## 🔄 Migration from Serper

If you're migrating from Serper.dev:

1. **Replace API Key**: Change `SERPER_API_KEY` to `EXA_API_KEY`
2. **Update Imports**: The code has been updated automatically
3. **Test Integration**: Run the test scripts to verify functionality
4. **Monitor Performance**: Exa may have different response times

## 📚 Additional Resources

- [Exa API Documentation](https://docs.exa.ai)
- [Python SDK](https://github.com/exa-labs/exa-py)
- [API Reference](https://docs.exa.ai/reference/search)
- [Examples](https://docs.exa.ai/examples)

## 🆘 Support

- **Exa Support**: [support@exa.ai](mailto:support@exa.ai)
- **Documentation**: [docs.exa.ai](https://docs.exa.ai)
- **Community**: [Discord](https://discord.gg/exa)

---

**Note**: This integration replaces the previous Serper.dev integration with Exa API for enhanced web search capabilities and better AI-optimized results.
