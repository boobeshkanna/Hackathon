#!/bin/bash

# Integration Test Runner Script
# This script sets up the environment and runs integration tests

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}=== Vernacular Artisan Catalog Integration Tests ===${NC}"
echo ""

# Check if .env file exists
if [ ! -f .env ]; then
    echo -e "${RED}Error: .env file not found${NC}"
    echo "Please create .env file from .env.example"
    exit 1
fi

# Load environment variables
source .env

# Check AWS credentials
echo -e "${YELLOW}Checking AWS credentials...${NC}"
if ! aws sts get-caller-identity > /dev/null 2>&1; then
    echo -e "${RED}Error: AWS credentials not configured${NC}"
    echo "Please run: aws configure"
    exit 1
fi

echo -e "${GREEN}✓ AWS credentials configured${NC}"
echo ""

# Check Python dependencies
echo -e "${YELLOW}Checking Python dependencies...${NC}"
if ! python -c "import boto3, pytest, requests, fastapi" > /dev/null 2>&1; then
    echo -e "${YELLOW}Installing dependencies...${NC}"
    pip install -r requirements.txt
fi

echo -e "${GREEN}✓ Dependencies installed${NC}"
echo ""

# Parse command line arguments
TEST_SUITE="all"
VERBOSE="-v"
CAPTURE_OUTPUT="-s"

while [[ $# -gt 0 ]]; do
    case $1 in
        --suite)
            TEST_SUITE="$2"
            shift 2
            ;;
        --quiet)
            VERBOSE=""
            CAPTURE_OUTPUT=""
            shift
            ;;
        --setup-only)
            SETUP_ONLY=true
            shift
            ;;
        --teardown-only)
            TEARDOWN_ONLY=true
            shift
            ;;
        --help)
            echo "Usage: $0 [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  --suite <name>      Run specific test suite (all|e2e|component)"
            echo "  --quiet             Run tests without verbose output"
            echo "  --setup-only        Only set up test environment"
            echo "  --teardown-only     Only tear down test environment"
            echo "  --help              Show this help message"
            echo ""
            echo "Examples:"
            echo "  $0                          # Run all tests"
            echo "  $0 --suite e2e              # Run end-to-end tests only"
            echo "  $0 --suite component        # Run component tests only"
            echo "  $0 --setup-only             # Set up environment only"
            exit 0
            ;;
        *)
            echo -e "${RED}Unknown option: $1${NC}"
            echo "Use --help for usage information"
            exit 1
            ;;
    esac
done

# Setup only mode
if [ "$SETUP_ONLY" = true ]; then
    echo -e "${YELLOW}Setting up test environment...${NC}"
    python tests/integration/test_environment_setup.py setup
    echo -e "${GREEN}✓ Test environment setup complete${NC}"
    exit 0
fi

# Teardown only mode
if [ "$TEARDOWN_ONLY" = true ]; then
    echo -e "${YELLOW}Tearing down test environment...${NC}"
    python tests/integration/test_environment_setup.py teardown
    echo -e "${GREEN}✓ Test environment teardown complete${NC}"
    exit 0
fi

# Determine which tests to run
case $TEST_SUITE in
    all)
        TEST_PATH="tests/integration/"
        echo -e "${YELLOW}Running all integration tests...${NC}"
        ;;
    e2e)
        TEST_PATH="tests/integration/test_end_to_end_flows.py"
        echo -e "${YELLOW}Running end-to-end flow tests...${NC}"
        ;;
    component)
        TEST_PATH="tests/integration/test_component_integration.py"
        echo -e "${YELLOW}Running component integration tests...${NC}"
        ;;
    *)
        echo -e "${RED}Error: Unknown test suite: $TEST_SUITE${NC}"
        echo "Valid options: all, e2e, component"
        exit 1
        ;;
esac

echo ""

# Run tests
if pytest $TEST_PATH $VERBOSE $CAPTURE_OUTPUT --tb=short; then
    echo ""
    echo -e "${GREEN}=== All tests passed! ===${NC}"
    exit 0
else
    echo ""
    echo -e "${RED}=== Some tests failed ===${NC}"
    exit 1
fi
