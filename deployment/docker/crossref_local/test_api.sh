#!/bin/bash
# Test script for CrossRef Local API

set -e

API_URL="${1:-http://localhost:3333}"
TEST_DOI="10.1038/nature12345"

echo "=========================================="
echo "Testing CrossRef Local API"
echo "API URL: $API_URL"
echo "=========================================="
echo ""

# Function to test endpoint
test_endpoint() {
    local name="$1"
    local endpoint="$2"
    local expected_status="${3:-200}"

    echo "Testing: $name"
    echo "URL: $API_URL$endpoint"

    response=$(curl -s -w "\n%{http_code}" "$API_URL$endpoint")
    body=$(echo "$response" | head -n -1)
    status=$(echo "$response" | tail -n 1)

    if [ "$status" -eq "$expected_status" ]; then
        echo "✓ Status: $status (expected $expected_status)"
        echo "Response preview:"
        echo "$body" | head -c 200
        echo "..."
        echo ""
    else
        echo "✗ Status: $status (expected $expected_status)"
        echo "Response:"
        echo "$body"
        echo ""
        exit 1
    fi
}

# 1. Root endpoint
test_endpoint "Root" "/" 200

# 2. Health check
test_endpoint "Health Check" "/health" 200

# 3. Database stats
test_endpoint "Database Stats" "/api/stats/" 200

# 4. Search by DOI
test_endpoint "Search by DOI" "/api/search/?doi=$TEST_DOI" 200

# 5. Search by title
test_endpoint "Search by Title" "/api/search/?title=deep%20learning&limit=5" 200

# 6. Search by year
test_endpoint "Search by Year" "/api/search/?year=2015&limit=5" 200

# 7. Citation graph (may not find data, but API should work)
test_endpoint "Citation Graph" "/api/citations/?doi=$TEST_DOI&depth=1" 200

# 8. Swagger docs
test_endpoint "Swagger Docs" "/docs" 200

echo "=========================================="
echo "All tests passed! ✓"
echo "=========================================="
echo ""
echo "API is ready to use:"
echo "  - Documentation: $API_URL/docs"
echo "  - Health: $API_URL/health"
echo "  - Search: $API_URL/api/search/"
echo ""
