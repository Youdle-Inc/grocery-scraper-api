# Partner API Integration Setup

This document explains how to set up the official grocery store partner APIs (Target, Kroger, Walmart) for use in the grocery-scraper-api.

## Overview

The grocery-scraper-api now supports **official partner APIs** for Target, Kroger, and Walmart. When available, these APIs are used instead of Exa web scraping, providing:

- ✅ **More reliable results** - Official APIs have better data quality
- ✅ **Faster responses** - Direct API calls are faster than web scraping
- ✅ **Better coverage** - Official APIs have access to more product data
- ✅ **Automatic fallback** - Falls back to Exa if partner API is unavailable or returns no results

## Supported Stores

| Store | API Type | Status |
|-------|----------|--------|
| **Target** | RapidAPI (via RapidAPI marketplace) | ✅ Supported |
| **Kroger** | Official OAuth2 API | ✅ Supported |
| **Walmart** | Affiliate/Partner API | ✅ Supported |

## Environment Variables

Add these to your `.env` file:

### Target API (RapidAPI)

```bash
# Target RapidAPI Key
RAPIDAPI=your_rapidapi_key

# RapidAPI Host
RAPID_API_HOST=target1.p.rapidapi.com
```

**How to get Target API keys:**
1. Sign up at [RapidAPI](https://rapidapi.com/)
2. Subscribe to the "Target" API (search for "target1" or "Target API")
3. Copy your API key(s) from the RapidAPI dashboard

### Kroger API

```bash
# Kroger OAuth2 Credentials
KROGER_CLIENT_ID=your_kroger_client_id
KROGER_CLIENT_SECRET=your_kroger_client_secret
```

**How to get Kroger API credentials:**
1. Go to [Kroger Developer Portal](https://developer.kroger.com/)
2. Create a developer account
3. Create a new application
4. Get your Client ID and Client Secret
5. Request access to the Product API

### Walmart API

```bash
# Walmart Affiliate API
# Only Consumer ID is required - private key has a built-in fallback
WALMART_CONSUMER_ID=your_walmart_consumer_id

# Optional: Set your own private key if you have one
# WALMART_PRIVATE_KEY="-----BEGIN RSA PRIVATE KEY-----\n...\n-----END RSA PRIVATE KEY-----"
```

**How to get Walmart API credentials:**
1. Sign up for [Walmart Affiliate Program](https://affiliates.walmart.com/)
2. Apply for API access
3. Get your Consumer ID from the Walmart Developer Portal
4. **Note**: The private key is optional - the code includes a fallback key that matches your TypeScript implementation. Only set `WALMART_PRIVATE_KEY` if you want to use a different key.

**Quick Setup:**
- Just set `WALMART_CONSUMER_ID` - that's all you need!
- The private key will use the same one from your TypeScript code automatically

## How It Works

### Automatic Routing

The system automatically routes requests to the appropriate API:

1. **Check if partner API is available** - Checks if API keys are configured
2. **Try partner API first** - Uses official API if available
3. **Fallback to Exa** - If partner API:
   - Is not configured
   - Returns no results
   - Encounters an error

### Example Flow

```python
# For Target store:
if partner_api_client.has_partner_api("target"):
    products = await partner_api_client.search_products("target", "milk", "60601")
    if not products:
        # Fallback to Exa
        products = await exa_client.search_products_structured(...)
```

## API Behavior

### Target API
- **Requires zipcode** - Needs zipcode to find stores
- **Multi-store search** - Searches multiple Target stores near zipcode
- **Returns**: Product name, price, availability, images, TCIN (Target product ID)

### Kroger API
- **Requires zipcode** - Needs zipcode to find stores  
- **OAuth2 authentication** - Automatically handles token refresh
- **Multi-store search** - Searches multiple Kroger stores near zipcode
- **Returns**: Product name, brand, price, UPC, images

### Walmart API
- **No zipcode required** - Searches walmart.com directly
- **RSA signature auth** - Uses RSA signatures for authentication
- **Returns**: Product name, price, ratings, images, item ID

## Testing

Test the integration:

```bash
# Test Target API (requires zipcode)
curl "http://localhost:8000/products/aggregate?query=milk&zipcode=60601&stores=target"

# Test Kroger API (requires zipcode)
curl "http://localhost:8000/products/aggregate?query=milk&zipcode=60601&stores=kroger"

# Test Walmart API (no zipcode needed)
curl "http://localhost:8000/products/aggregate?query=milk&stores=walmart"

# Test all three together
curl "http://localhost:8000/products/aggregate?query=milk&zipcode=60601&stores=target,kroger,walmart"
```

## Logging

The system logs which API is being used:

```
🎯 Using official Target API
✅ Target partner API returned 15 products
```

Or if falling back:

```
⚠️ Target partner API returned no results, falling back to Exa
🔍 Using Exa API for Target
```

## Troubleshooting

### Target API returns zero results
- Check that `PRODSIGHT1_KEY` or other keys are set
- Verify `RAPID_API_HOST` is correct
- Check RapidAPI subscription status
- Ensure zipcode is provided (required for Target)

### Kroger API authentication fails
- Verify `KROGER_CLIENT_ID` and `KROGER_CLIENT_SECRET` are correct
- Check that your Kroger developer account has API access
- Ensure OAuth2 scope includes `product.compact`

### Walmart API signature errors
- Verify `WALMART_CONSUMER_ID` is correct
- Check that `WALMART_PRIVATE_KEY` includes full RSA key with headers
- Ensure private key format is correct (with `\n` line breaks)

### All APIs unavailable
- System will automatically fall back to Exa API
- Check that `EXA_API_KEY` is set
- Partner APIs are optional - Exa will handle all stores

## Benefits

✅ **Better Target results** - Official API should fix the "zero results" issue  
✅ **More reliable** - Official APIs are more stable than web scraping  
✅ **Faster** - Direct API calls are faster than Exa web search  
✅ **Backward compatible** - Falls back to Exa if APIs unavailable  

## Next Steps

1. Add API keys to your `.env` file
2. Restart the API server
3. Test with the curl commands above
4. Check logs to see which API is being used
5. Monitor results - partner APIs should return more products than Exa alone

