#!/bin/bash

# Test script for the updated aggregate endpoint with address information
# Make sure your API is running on localhost:8000

echo "🧪 Testing Aggregate Endpoint with Address Information"
echo "=================================================="

# Test 1: Basic product search with addresses
echo "Test 1: Basic product search - Organic Milk"
curl -X GET "http://localhost:8000/products/aggregate?query=organic%20milk&zipcode=10001&radius_miles=10" \
  -H "Accept: application/json" \
  -w "\n\nHTTP Status: %{http_code}\nResponse Time: %{time_total}s\n" \
  | jq '.'

echo -e "\n" 

# Test 2: Search with specific stores
echo "Test 2: Search with specific stores - Whole Foods and Trader Joe's"
curl -X GET "http://localhost:8000/products/aggregate?query=avocado&zipcode=90210&stores=whole_foods,trader_joes" \
  -H "Accept: application/json" \
  -w "\n\nHTTP Status: %{http_code}\nResponse Time: %{time_total}s\n" \
  | jq '.'

echo -e "\n"

# Test 3: Enhanced search with Exa integration
echo "Test 3: Enhanced search with Exa integration - Coffee"
curl -X GET "http://localhost:8000/products/aggregate?query=coffee&zipcode=60601&enhance=true" \
  -H "Accept: application/json" \
  -w "\n\nHTTP Status: %{http_code}\nResponse Time: %{time_total}s\n" \
  | jq '.'

echo -e "\n"

# Test 4: Different zipcode to test address variation
echo "Test 4: Different location - San Francisco"
curl -X GET "http://localhost:8000/products/aggregate?query=bread&zipcode=94102&radius_miles=5" \
  -H "Accept: application/json" \
  -w "\n\nHTTP Status: %{http_code}\nResponse Time: %{time_total}s\n" \
  | jq '.'

echo -e "\n"

# Test 5: Refresh cache to ensure fresh data
echo "Test 5: Force refresh to get latest data"
curl -X GET "http://localhost:8000/products/aggregate?query=bananas&zipcode=10001&refresh=true" \
  -H "Accept: application/json" \
  -w "\n\nHTTP Status: %{http_code}\nResponse Time: %{time_total}s\n" \
  | jq '.'

echo -e "\n"

# Test 6: Check specific address fields in response
echo "Test 6: Verify address fields in response"
curl -X GET "http://localhost:8000/products/aggregate?query=eggs&zipcode=10001" \
  -H "Accept: application/json" \
  -w "\n\nHTTP Status: %{http_code}\nResponse Time: %{time_total}s\n" \
  | jq '.results[0].offers[] | {store_name, store_id, address, price}'

echo -e "\n"

# Test 7: Health check to verify services
echo "Test 7: Health check"
curl -X GET "http://localhost:8000/health" \
  -H "Accept: application/json" \
  -w "\n\nHTTP Status: %{http_code}\nResponse Time: %{time_total}s\n" \
  | jq '.'

echo -e "\n"

# Test 8: Store discovery to see available stores
echo "Test 8: Store discovery"
curl -X GET "http://localhost:8000/sonar/stores/10001" \
  -H "Accept: application/json" \
  -w "\n\nHTTP Status: %{http_code}\nResponse Time: %{time_total}s\n" \
  | jq '.'

echo -e "\n"

echo "✅ Testing complete!"
echo "Check the responses above to verify that:"
echo "1. Each offer includes an 'address' field"
echo "2. Addresses are populated with actual store locations"
echo "3. The response structure includes the new address information"
