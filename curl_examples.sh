#!/bin/bash

# 🚀 Grocery Scraper API - Curl Test Examples
# Test the optimized prompt strategies

echo "🚀 Testing Grocery Scraper API with Optimized Prompts"
echo "=================================================="

# Set base URL
BASE_URL="http://localhost:8000"

echo ""
echo "🏥 1. Testing API Health"
echo "------------------------"
curl -s "$BASE_URL/health" | jq '.' || echo "❌ Health check failed"

echo ""
echo "📊 2. Testing API Info"
echo "---------------------"
curl -s "$BASE_URL/" | jq '.name, .version, .features' || echo "❌ API info failed"

echo ""
echo "🏪 3. Testing Store Discovery"
echo "----------------------------"
echo "Target stores in NYC:"
curl -s "$BASE_URL/stores/10001?store_chain=Target" | jq '.stores_found, .stores[0].store_name' || echo "❌ Store search failed"

echo ""
echo "Whole Foods in Beverly Hills:"
curl -s "$BASE_URL/stores/90210?store_chain=Whole%20Foods" | jq '.stores_found' || echo "❌ Store search failed"

echo ""
echo "🛒 4. Testing Product Searches with Different Contexts"
echo "----------------------------------------------------"

echo ""
echo "🧪 Test 1: Price Comparison - Dairy"
echo "Query: cheap organic milk"
curl -s "$BASE_URL/products/search?query=cheap%20organic%20milk&store_name=Whole%20Foods&zipcode=10001&context=price_comparison" | jq '.products_found, .products[0].name, .products[0].price' || echo "❌ Product search failed"

echo ""
echo "🧪 Test 2: Availability - Produce"
echo "Query: fresh organic apples"
curl -s "$BASE_URL/products/search?query=fresh%20organic%20apples&store_name=Target&zipcode=10001&context=availability" | jq '.products_found, .products[0].name, .products[0].availability' || echo "❌ Product search failed"

echo ""
echo "🧪 Test 3: Nutritional - Meat"
echo "Query: organic grass-fed beef"
curl -s "$BASE_URL/products/search?query=organic%20grass-fed%20beef&store_name=Whole%20Foods&zipcode=10001&context=nutritional" | jq '.products_found, .products[0].name, .products[0].brand' || echo "❌ Product search failed"

echo ""
echo "🧪 Test 4: Brand Comparison - Frozen"
echo "Query: frozen pizza brands"
curl -s "$BASE_URL/products/search?query=frozen%20pizza%20brands&store_name=Walmart&zipcode=10001&context=brand_comparison" | jq '.products_found, .products[0].name, .products[0].brand' || echo "❌ Product search failed"

echo ""
echo "🧪 Test 5: Seasonal - Generic"
echo "Query: pumpkin spice seasonal"
curl -s "$BASE_URL/products/search?query=pumpkin%20spice%20seasonal&store_name=Target&zipcode=10001&context=seasonal" | jq '.products_found, .products[0].name' || echo "❌ Product search failed"

echo ""
echo "🔄 6. Testing Aggregate Search"
echo "-----------------------------"
echo "Aggregate: organic milk across multiple stores"
curl -s "$BASE_URL/products/aggregate?query=organic%20milk&zipcode=10001&stores=target,walmart,whole_foods" | jq '.results | length, .[0].canonical_product.name, .[0].offers | length' || echo "❌ Aggregate search failed"

echo ""
echo "Aggregate: fresh salmon across stores"
curl -s "$BASE_URL/products/aggregate?query=fresh%20salmon&zipcode=90210&stores=whole_foods,target" | jq '.results | length, .[0].canonical_product.name' || echo "❌ Aggregate search failed"

echo ""
echo "🎯 7. Testing Auto-Detection (No Context Specified)"
echo "------------------------------------------------"
echo "Auto-detect context for 'cheap milk':"
curl -s "$BASE_URL/products/search?query=cheap%20milk&store_name=Walmart&zipcode=10001" | jq '.products_found, .source' || echo "❌ Auto-detection failed"

echo ""
echo "Auto-detect context for 'organic apples available':"
curl -s "$BASE_URL/products/search?query=organic%20apples%20available&store_name=Target&zipcode=10001" | jq '.products_found, .source' || echo "❌ Auto-detection failed"

echo ""
echo "🎉 Test Examples Complete!"
echo "========================="
echo "Check the results above to see:"
echo "✅ Context-aware prompts working"
echo "✅ Category-specific data extraction"
echo "✅ Enhanced validation and formatting"
echo "✅ Better search results"
echo "✅ Confidence scoring"
