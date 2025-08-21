#!/bin/bash

echo "🧪 Testing Grocery Store Discovery API"
echo "======================================"

# Test 1: Health check
echo "1. Health Check:"
curl -s "http://localhost:8000/health" | jq .

# Test 2: Sonar status
echo -e "\n2. Sonar Status:"
curl -s "http://localhost:8000/sonar/status" | jq .

# Test 3: Discover stores in Chicago
echo -e "\n3. Discover Stores in 60622:"
curl -s "http://localhost:8000/sonar/stores/60622" | jq .

# Test 4: Search for oat milk at Jewel
echo -e "\n4. Search Oat Milk at Jewel:"
curl -s "http://localhost:8000/sonar/products/search?query=oat%20milk&store_name=Jewel-Osco%20W%20Division%20St&location=Chicago,%20IL" | jq .

# Test 5: Search for milk at Mariano's
echo -e "\n5. Search Milk at Mariano's:"
curl -s "http://localhost:8000/sonar/products/search?query=milk&store_name=Mariano's%20Ukrainian%20Village&location=Chicago,%20IL" | jq .

# Test 6: Get store details
echo -e "\n6. Get Jewel Store Details:"
curl -s "http://localhost:8000/sonar/store/Jewel-Osco%20W%20Division%20St/details?location=Chicago,%20IL" | jq .

echo -e "\n✅ All tests completed!"
