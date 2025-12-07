#!/bin/bash
# =============================================================================
# Multi-Tenant Isolation Test Runner
# =============================================================================
# This script runs comprehensive isolation tests to verify multi-tenant security.
# 
# Usage:
#   ./scripts/run_isolation_tests.sh [options]
#
# Options:
#   --quick     Run only critical tests (faster)
#   --verbose   Show detailed output
#   --report    Generate HTML report
#   --clean     Clean up test data after running
#
# =============================================================================

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
TEST_DIR="$PROJECT_ROOT/source/dataagent-server/tests/test_multi_tenant"
REPORT_DIR="$PROJECT_ROOT/reports/isolation-tests"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")

# Default options
QUICK_MODE=false
VERBOSE=false
GENERATE_REPORT=false
CLEAN_AFTER=false

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --quick)
            QUICK_MODE=true
            shift
            ;;
        --verbose)
            VERBOSE=true
            shift
            ;;
        --report)
            GENERATE_REPORT=true
            shift
            ;;
        --clean)
            CLEAN_AFTER=true
            shift
            ;;
        *)
            echo "Unknown option: $1"
            exit 1
            ;;
    esac
done

# =============================================================================
# Functions
# =============================================================================

print_header() {
    echo ""
    echo -e "${BLUE}=============================================================================${NC}"
    echo -e "${BLUE}  $1${NC}"
    echo -e "${BLUE}=============================================================================${NC}"
    echo ""
}

print_status() {
    if [ "$2" == "pass" ]; then
        echo -e "${GREEN}✅ $1${NC}"
    elif [ "$2" == "fail" ]; then
        echo -e "${RED}❌ $1${NC}"
    elif [ "$2" == "warn" ]; then
        echo -e "${YELLOW}⚠️  $1${NC}"
    else
        echo -e "${BLUE}ℹ️  $1${NC}"
    fi
}

init_test_environment() {
    print_header "Initializing Test Environment"
    
    # Create test directories
    TEST_BASE="/tmp/dataagent-test"
    mkdir -p "$TEST_BASE/workspaces/test_alice/knowledge"
    mkdir -p "$TEST_BASE/workspaces/test_bob/knowledge"
    mkdir -p "$TEST_BASE/users/test_alice/rules"
    mkdir -p "$TEST_BASE/users/test_alice/agent"
    mkdir -p "$TEST_BASE/users/test_bob/rules"
    mkdir -p "$TEST_BASE/users/test_bob/agent"
    mkdir -p "$TEST_BASE/mcp"
    
    print_status "Created test directories" "pass"
    
    # Initialize test database
    if [ -f "$TEST_DIR/test_data/init_test_db.sql" ]; then
        sqlite3 "$TEST_BASE/test_isolation.db" < "$TEST_DIR/test_data/init_test_db.sql"
        print_status "Initialized test database" "pass"
    fi
    
    # Copy test data files
    if [ -d "$TEST_DIR/test_data/alice" ]; then
        cp -r "$TEST_DIR/test_data/alice/"* "$TEST_BASE/users/test_alice/" 2>/dev/null || true
        print_status "Copied Alice's test data" "pass"
    fi
    
    if [ -d "$TEST_DIR/test_data/bob" ]; then
        cp -r "$TEST_DIR/test_data/bob/"* "$TEST_BASE/users/test_bob/" 2>/dev/null || true
        print_status "Copied Bob's test data" "pass"
    fi
    
    echo ""
    print_status "Test environment ready at: $TEST_BASE" "info"
}

run_tests() {
    print_header "Running Isolation Tests"
    
    cd "$PROJECT_ROOT/source/dataagent-server"
    
    # Build pytest arguments
    PYTEST_ARGS="-v"
    
    if [ "$VERBOSE" == "true" ]; then
        PYTEST_ARGS="$PYTEST_ARGS -s"
    fi
    
    if [ "$GENERATE_REPORT" == "true" ]; then
        mkdir -p "$REPORT_DIR"
        PYTEST_ARGS="$PYTEST_ARGS --html=$REPORT_DIR/report_$TIMESTAMP.html --self-contained-html"
    fi
    
    if [ "$QUICK_MODE" == "true" ]; then
        # Run only critical tests
        PYTEST_ARGS="$PYTEST_ARGS -m 'not slow'"
    fi
    
    # Run tests
    echo "Running: pytest tests/test_multi_tenant/ $PYTEST_ARGS"
    echo ""
    
    if pytest tests/test_multi_tenant/ $PYTEST_ARGS; then
        TEST_RESULT="pass"
    else
        TEST_RESULT="fail"
    fi
    
    return $([ "$TEST_RESULT" == "pass" ] && echo 0 || echo 1)
}

generate_summary() {
    print_header "Test Summary"
    
    echo "Test Categories:"
    echo "  - Filesystem Isolation"
    echo "  - MCP Isolation"
    echo "  - Rules Isolation"
    echo "  - Memory Isolation"
    echo "  - Skills Isolation"
    echo ""
    
    if [ "$TEST_RESULT" == "pass" ]; then
        print_status "All isolation tests PASSED" "pass"
        echo ""
        echo -e "${GREEN}✅ Multi-tenant isolation is working correctly${NC}"
        echo -e "${GREEN}✅ User A cannot access User B's resources${NC}"
        echo -e "${GREEN}✅ Path traversal attacks are blocked${NC}"
        echo -e "${GREEN}✅ Cross-tenant access is denied${NC}"
    else
        print_status "Some isolation tests FAILED" "fail"
        echo ""
        echo -e "${RED}❌ SECURITY ISSUE: Multi-tenant isolation may be compromised${NC}"
        echo -e "${RED}❌ Please review the test output above for details${NC}"
    fi
    
    if [ "$GENERATE_REPORT" == "true" ]; then
        echo ""
        print_status "Report generated: $REPORT_DIR/report_$TIMESTAMP.html" "info"
    fi
}

cleanup() {
    if [ "$CLEAN_AFTER" == "true" ]; then
        print_header "Cleaning Up"
        rm -rf /tmp/dataagent-test
        print_status "Removed test data" "pass"
    fi
}

# =============================================================================
# Main
# =============================================================================

main() {
    print_header "Multi-Tenant Isolation Test Suite"
    
    echo "Configuration:"
    echo "  Quick Mode: $QUICK_MODE"
    echo "  Verbose: $VERBOSE"
    echo "  Generate Report: $GENERATE_REPORT"
    echo "  Clean After: $CLEAN_AFTER"
    echo ""
    
    # Initialize
    init_test_environment
    
    # Run tests
    if run_tests; then
        TEST_RESULT="pass"
    else
        TEST_RESULT="fail"
    fi
    
    # Summary
    generate_summary
    
    # Cleanup
    cleanup
    
    # Exit with appropriate code
    if [ "$TEST_RESULT" == "pass" ]; then
        exit 0
    else
        exit 1
    fi
}

main "$@"
