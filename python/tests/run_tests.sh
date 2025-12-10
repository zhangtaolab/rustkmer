#!/bin/bash
# Test runner script for RustKmer Python bindings

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo -e "${YELLOW}Running RustKmer Python Test Suite${NC}"
echo "=========================================="

# Function to run a category of tests
run_tests() {
    local category=$1
    local marker=$2
    echo -e "\n${YELLOW}Running $category tests...${NC}"

    if [ -n "$marker" ]; then
        python -m pytest -m "$marker" --cov=../rustkmer --cov-report=term-missing "$SCRIPT_DIR"
    else
        python -m pytest --cov=../rustkmer --cov-report=term-missing "$SCRIPT_DIR"
    fi
}

# Check if we're in .venv
if [[ "$VIRTUAL_ENV" != *"rustkmer"* ]]; then
    echo -e "${RED}Error: Tests must be run in .venv environment${NC}"
    echo "Please run: source .venv/bin/activate && python tests/run_tests.sh"
    exit 1
fi

# Run all tests by default
if [ $# -eq 0 ]; then
    run_tests "All" ""
else
    case "$1" in
        unit)
            run_tests "Unit" "not integration and not performance and not compatibility"
            ;;
        integration)
            run_tests "Integration" "integration"
            ;;
        performance)
            run_tests "Performance" "performance"
            ;;
        compatibility)
            run_tests "Compatibility" "compatibility"
            ;;
        *)
            echo "Usage: $0 [unit|integration|performance|compatibility]"
            exit 1
            ;;
    esac
fi

echo -e "\n${GREEN}Test execution completed!${NC}"