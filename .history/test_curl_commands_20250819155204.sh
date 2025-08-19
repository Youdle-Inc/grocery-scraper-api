#!/bin/bash

# Grocery Scraper API - Quick Test Commands
# Test the API with curl commands

echo "🛒 Grocery Scraper API - Quick Test Commands"
echo "============================================="
echo ""

# Base URL
BASE_URL="http://localhost:8000"

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to run a test
run_test() {
    local test_name="$1"
    local url="$2"
    local description="$3"
    
    echo -e "${BLUE}🧪 Testing: ${test_name}${NC}"
    echo -e "${YELLOW}Description:${NC} ${description}"
    echo -e "${YELLOW}URL:${NC} ${url}"
    echo ""
    
    # Run the curl command
    response=$(curl -s "$url")
    
    # Check if the response is valid JSON
    if echo "$response" | python -m json.tool >/dev/null 2>&1; then
        echo -e "${GREEN}✅ Success!${NC}"
        echo "$response" | python -m json.tool | head -20
    else
        echo -e "${RED}❌ Failed or invalid JSON${NC}"
        echo "$response"
    fi
    
    echo ""
    echo "----------------------------------------"
    echo ""
}

# Test 1: Health Check
run_test "Health Check" \
    "${BASE_URL}/health" \
    "Check if the API is running and healthy"

# Test 2: API Information
run_test "API Information" \
    "${BASE_URL}/" \
    "Get basic information about the API"

# Test 3: Store Discovery - Chicago
run_test "Store Discovery - Chicago" \
    "${BASE_URL}/sonar/stores/search?location=Chicago,IL" \
    "Find grocery stores in Chicago"

# Test 4: Store Discovery - New York
run_test "Store Discovery - New York" \
    "${BASE_URL}/sonar/stores/search?location=New%20York,NY" \
    "Find grocery stores in New York"

# Test 5: Product Search - Milk at Target
run_test "Product Search - Milk at Target" \
    "${BASE_URL}/sonar/products/search?query=milk&store_name=Target&location=Chicago,IL" \
    "Search for milk at Target in Chicago (tests Serper.dev integration)"

# Test 6: Product Search - Oat Milk at Whole Foods
run_test "Product Search - Oat Milk at Whole Foods" \
    "${BASE_URL}/sonar/products/search?query=oat%20milk&store_name=Whole%20Foods&location=San%20Francisco,CA" \
    "Search for oat milk at Whole Foods in San Francisco"

# Test 7: Product Search - Organic Bananas at Trader Joe's
run_test "Product Search - Organic Bananas at Trader Joe's" \
    "${BASE_URL}/sonar/products/search?query=organic%20bananas&store_name=Trader%20Joes&location=Los%20Angeles,CA" \
    "Search for organic bananas at Trader Joe's in Los Angeles"

# Test 8: Product Search - Almond Milk at Walmart
run_test "Product Search - Almond Milk at Walmart" \
    "${BASE_URL}/sonar/products/search?query=almond%20milk&store_name=Walmart&location=Austin,TX" \
    "Search for almond milk at Walmart in Austin"

# Test 9: Product Search - Bread at Safeway
run_test "Product Search - Bread at Safeway" \
    "${BASE_URL}/sonar/products/search?query=bread&store_name=Safeway&location=Seattle,WA" \
    "Search for bread at Safeway in Seattle"

# Test 10: Product Search - Eggs at Kroger
run_test "Product Search - Eggs at Kroger" \
    "${BASE_URL}/sonar/products/search?query=eggs&store_name=Kroger&location=Atlanta,GA" \
    "Search for eggs at Kroger in Atlanta"

echo -e "${GREEN}🎉 All tests completed!${NC}"
echo ""
echo -e "${BLUE}📊 Summary:${NC}"
echo "   - Health Check: Basic API functionality"
echo "   - Store Discovery: AI-powered store finding"
echo "   - Product Search: Real URLs and images via Serper.dev"
echo ""
echo -e "${BLUE}🔗 Interactive Documentation:${NC}"
echo "   - Swagger UI: ${BASE_URL}/docs"
echo "   - ReDoc: ${BASE_URL}/redoc"
echo ""
echo -e "${BLUE}📚 Documentation:${NC}"
echo "   - README.md: Main documentation"
echo "   - GETTING_STARTED.md: Setup guide"
echo "   - API_REFERENCE.md: Complete API reference"
echo ""
echo -e "${YELLOW}💡 Tips:${NC}"
echo "   - Check the 'image_url' and 'product_url' fields for real data"
echo "   - Look for 'source: perplexity_sonar + serper_dev' in responses"
echo "   - Test with different stores and products"
echo "   - Use URL encoding for special characters in queries"

