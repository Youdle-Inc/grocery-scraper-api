# Instacart API Integration

This document describes the Instacart Developer Platform API integration that replaces the previous Exa API integration.

## Overview

The Grocery Scraper API now uses Instacart's Developer Platform API as the primary data source for grocery product search. This provides:

- **Real-time pricing**: Current prices from Instacart's marketplace
- **Location-scoped results**: Products scoped to user's zipcode
- **Real-time availability**: Accurate stock status (IN_STOCK, OUT_OF_STOCK, LOW_STOCK)
- **Comprehensive retailer coverage**: Access to Instacart's partner retailers
- **Product images**: High-quality product images included in responses
- **Deep links**: Direct links to Instacart marketplace for checkout

## Setup

### 1. Get Instacart API Key

1. Visit [Instacart Developer Platform](https://docs.instacart.com/developer_platform_api/)
2. Sign up for developer access
3. Create an application
4. Obtain your API key

### 2. Configure Environment

Add to your `.env` file:
```bash
INSTACART_API_KEY=your_api_key_here
```

### 3. Install Dependencies

No additional dependencies required! Instacart API uses standard HTTP requests via `aiohttp` (already included).

## API Usage

### Product Search

```python
from scraper.instacart_client import InstacartClient

client = InstacartClient()
products = await client.search_products_structured(
    query="milk",
    zipcode="60601",
    store_name="Target",  # Optional
    num_results=10
)
```

### Store Discovery

```python
stores = await client.search_stores_in_zipcode(
    store_chain="Target",
    zipcode="60601"
)
```

## Data Normalization

Instacart API responses are normalized to match our internal schema:

- **Product ID**: Prefixed with `ic_` (e.g., `ic_123456`)
- **Availability**: Mapped to our enum (IN_STOCK, OUT_OF_STOCK, LOW_STOCK, CHECK_STORE)
- **Price**: Extracted from price object with currency
- **Images**: Primary image URL from images array
- **Product URL**: Instacart marketplace deeplink
- **Store Info**: Retailer name, ID, and location data

## Rate Limits

Instacart API has per-second rate limits. The client handles this gracefully:
- Rate limit errors (429) return empty results with warning logs
- Caching reduces API calls (15 min TTL for products, 1 hour for retailers)
- Concurrent requests are limited via semaphores

## Caching Strategy

- **Product searches**: 15 minutes TTL (real-time pricing)
- **Retailer lookups**: 1 hour TTL (relatively static)
- **Store locations**: 1 hour TTL

## Error Handling

The client handles various error scenarios:

- **Missing API key**: Returns empty results, logs warning
- **Rate limits**: Returns empty results, logs warning
- **Network errors**: Retries with exponential backoff (max 3 retries)
- **Invalid zipcode**: Returns empty results, logs warning
- **Unsupported location**: Returns empty results, doesn't fail entire request

## Migration from Exa

All Exa references have been replaced:
- `ExaStructuredClient` → `InstacartClient`
- `EXA_API_KEY` → `INSTACART_API_KEY`
- Exa-specific methods removed
- Image extraction simplified (Instacart provides images)

## Supported Retailers

Instacart supports many retailers including:
- Target
- Walmart
- Kroger
- Safeway/Albertsons
- Publix
- H-E-B
- ALDI
- Whole Foods Market
- Sprouts
- And many more...

Retailer availability varies by location. Use the `get_retailers(zipcode)` method to see available retailers for a specific zipcode.

## API Endpoints

The Instacart client uses these endpoints:
- `GET /v1/retailers?zipcode={zipcode}&country=US` - Get available retailers
- `GET /v1/products/search?query={query}&zipcode={zipcode}&country=US` - Search products

See [Instacart API Documentation](https://docs.instacart.com/developer_platform_api/api/overview/) for full details.

## Best Practices

1. **Always provide zipcode**: Instacart requires location scoping
2. **Cache retailer lookups**: Don't fetch retailers on every request
3. **Respect rate limits**: Use semaphores to limit concurrent requests
4. **Handle errors gracefully**: Instacart failures shouldn't break your app
5. **Use appropriate TTLs**: Balance freshness with API usage

## Troubleshooting

### "Instacart client not available"
- Check that `INSTACART_API_KEY` is set in `.env`
- Verify API key is valid
- Check API key has proper permissions

### Empty results
- Verify zipcode is valid 5-digit US zipcode
- Check if retailers are available for that zipcode
- Review logs for API errors

### Rate limit errors
- Reduce concurrent requests
- Increase caching TTL
- Implement request queuing

## Support

For Instacart API issues:
- [Instacart Developer Platform Docs](https://docs.instacart.com/developer_platform_api/)
- [Instacart API Support](https://docs.instacart.com/developer_platform_api/api/overview/)

