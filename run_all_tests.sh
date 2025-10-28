#!/bin/bash
# Test all API endpoints

PORT=8000
BASE_URL="http://localhost:$PORT"

echo "=========================================="
echo "Testing Grocery Scraper API Endpoints"
echo "=========================================="
echo ""

echo "1️⃣  Testing Health Endpoint"
echo "----------------------------------------"
curl -s "$BASE_URL/health" | python -m json.tool
echo ""
echo ""

echo "2️⃣  Testing API Info"
echo "----------------------------------------"
curl -s "$BASE_URL/api" | python -m json.tool | head -30
echo ""
echo ""

echo "3️⃣  Testing Store Search (ZIP: 60601)"
echo "----------------------------------------"
curl -s "$BASE_URL/stores/60601" | python -m json.tool | head -40
echo ""
echo ""

echo "4️⃣  Testing Product Search (milk at Target)"
echo "----------------------------------------"
curl -s "$BASE_URL/products/search?query=milk&store_name=Target&zipcode=60601&num_results=2" | python -m json.tool | head -50
echo ""
echo ""

echo "5️⃣  Testing Aggregate Search (eggs - Target & Walmart)"
echo "----------------------------------------"
curl -s "$BASE_URL/products/aggregate?query=eggs&zipcode=60601&stores=target,walmart" | python -m json.tool | head -60
echo ""
echo ""

echo "=========================================="
echo "✅ All endpoint tests complete!"
echo "=========================================="
