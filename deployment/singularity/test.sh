#!/bin/bash
# Timestamp: "2025-11-25 20:00:00 (ywatanabe)"
# File: ./deployment/singularity/test.sh
# ============================================
# Test SciTeX User Workspace Singularity Container
# ============================================

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SIF_FILE="$SCRIPT_DIR/scitex-user-workspace.sif"

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${GREEN}============================================${NC}"
echo -e "${GREEN}Testing SciTeX User Workspace Container${NC}"
echo -e "${GREEN}============================================${NC}"
echo -e ""

# Check if container exists
if [ ! -f "$SIF_FILE" ]; then
    echo -e "${RED}Error: Container image not found: $SIF_FILE${NC}"
    echo -e "Build it first with: sudo ./build.sh"
    exit 1
fi

echo -e "Testing image: ${GREEN}$SIF_FILE${NC}"
echo -e "Image size: ${GREEN}$(du -h "$SIF_FILE" | cut -f1)${NC}"
echo -e ""

# Test counter
TESTS_PASSED=0
TESTS_FAILED=0

run_test() {
    local test_name="$1"
    local test_cmd="$2"

    echo -e -n "Testing $test_name... "

    if eval "$test_cmd" > /dev/null 2>&1; then
        echo -e "${GREEN}✓ PASS${NC}"
        ((TESTS_PASSED++))
        return 0
    else
        echo -e "${RED}✗ FAIL${NC}"
        ((TESTS_FAILED++))
        return 1
    fi
}

echo -e "${YELLOW}Running tests...${NC}"
echo -e ""

# Test 1: Basic execution
run_test "Basic execution" "singularity exec $SIF_FILE python --version"

# Test 2: NumPy
run_test "NumPy import" "singularity exec $SIF_FILE python -c 'import numpy'"

# Test 3: Pandas
run_test "Pandas import" "singularity exec $SIF_FILE python -c 'import pandas'"

# Test 4: Matplotlib
run_test "Matplotlib import" "singularity exec $SIF_FILE python -c 'import matplotlib'"

# Test 5: Scikit-learn
run_test "Scikit-learn import" "singularity exec $SIF_FILE python -c 'import sklearn'"

# Test 6: Jupyter
run_test "Jupyter import" "singularity exec $SIF_FILE python -c 'import jupyter'"

# Test 7: Workspace directory
run_test "Workspace directory" "singularity exec $SIF_FILE ls /workspace"

# Test 8: Secure execution (--contain)
run_test "Secure execution (--contain)" "singularity exec --contain $SIF_FILE python -c 'print(\"OK\")'"

# Test 9: Clean environment (--cleanenv)
run_test "Clean environment (--cleanenv)" "singularity exec --cleanenv $SIF_FILE python -c 'print(\"OK\")'"

# Test 10: No home (--no-home)
run_test "No home mount (--no-home)" "singularity exec --no-home $SIF_FILE python -c 'print(\"OK\")'"

# Test 11: Simple computation
echo -e -n "Testing simple computation... "
RESULT=$(singularity exec $SIF_FILE python -c 'print(2 + 2)')
if [ "$RESULT" = "4" ]; then
    echo -e "${GREEN}✓ PASS${NC}"
    ((TESTS_PASSED++))
else
    echo -e "${RED}✗ FAIL (got: $RESULT)${NC}"
    ((TESTS_FAILED++))
fi

# Test 12: NumPy computation
echo -e -n "Testing NumPy computation... "
RESULT=$(singularity exec $SIF_FILE python -c 'import numpy as np; print(int(np.sum([1,2,3])))')
if [ "$RESULT" = "6" ]; then
    echo -e "${GREEN}✓ PASS${NC}"
    ((TESTS_PASSED++))
else
    echo -e "${RED}✗ FAIL (got: $RESULT)${NC}"
    ((TESTS_FAILED++))
fi

# Test 13: Workspace binding
echo -e -n "Testing workspace binding... "
TEST_DIR=$(mktemp -d)
echo -e "test content" > "$TEST_DIR/test.txt"
RESULT=$(singularity exec --bind "$TEST_DIR:/workspace" $SIF_FILE cat /workspace/test.txt)
rm -rf "$TEST_DIR"
if [ "$RESULT" = "test content" ]; then
    echo -e "${GREEN}✓ PASS${NC}"
    ((TESTS_PASSED++))
else
    echo -e "${RED}✗ FAIL${NC}"
    ((TESTS_FAILED++))
fi

# Test 14: UID preservation
echo -e -n "Testing UID preservation... "
CONTAINER_UID=$(singularity exec $SIF_FILE id -u)
HOST_UID=$(id -u)
if [ "$CONTAINER_UID" = "$HOST_UID" ]; then
    echo -e "${GREEN}✓ PASS (UID: $HOST_UID)${NC}"
    ((TESTS_PASSED++))
else
    echo -e "${RED}✗ FAIL (container UID: $CONTAINER_UID, host UID: $HOST_UID)${NC}"
    ((TESTS_FAILED++))
fi

echo -e ""
echo -e "${GREEN}============================================${NC}"
echo -e "${GREEN}Test Results${NC}"
echo -e "${GREEN}============================================${NC}"
echo -e "Tests passed: ${GREEN}$TESTS_PASSED${NC}"
if [ $TESTS_FAILED -gt 0 ]; then
    echo -e "Tests failed: ${RED}$TESTS_FAILED${NC}"
else
    echo -e "Tests failed: ${GREEN}$TESTS_FAILED${NC}"
fi
echo -e ""

if [ $TESTS_FAILED -eq 0 ]; then
    echo -e "${GREEN}All tests passed! Container is ready to use.${NC}"
    echo -e ""
    echo -e "${GREEN}Next steps:${NC}"
    echo -e "1. Copy to production: sudo cp $SIF_FILE /app/deployment/singularity/"
    echo -e "2. Test with Django: python manage.py test apps.code_app.tests.test_singularity"
    echo -e "3. Deploy to NAS"
    echo -e ""
    exit 0
else
    echo -e "${RED}Some tests failed. Please review the errors above.${NC}"
    exit 1
fi

# EOF
