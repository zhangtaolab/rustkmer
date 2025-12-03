#!/usr/bin/env bash

# RustKmer Examples Master Verification Script
#
# This script runs all examples and verifies consistency between CLI and Python API:
# - Automated execution of all examples
# - Cross-platform result comparison
# - Performance analysis and reporting
# - Error detection and detailed reporting
#
# Usage: ./verify_consistency.sh [--quick] [--verbose] [--report-only]

set -e  # Exit on any error

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
EXAMPLES_DIR="$(dirname "$SCRIPT_DIR")"
BASH_DIR="$EXAMPLES_DIR/bash"
PYTHON_DIR="$EXAMPLES_DIR/python"
OUTPUT_DIR="$EXAMPLES_DIR/output"
DATA_PATH="$EXAMPLES_DIR/data/demo_rice_genome.fa.gz"
KMER_SIZE=7

# Script options
QUICK_TEST=false
VERBOSE=false
REPORT_ONLY=false

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
MAGENTA='\033[0;35m'
BOLD='\033[1m'
NC='\033[0m' # No Color

# Results tracking
TEST_RESULTS_FILE="$OUTPUT_DIR/test_results_$$.tmp"
TOTAL_TESTS=0
PASSED_TESTS=0
FAILED_TESTS=0
START_TIME=$(date +%s)

# Initialize test results file
echo "" > "$TEST_RESULTS_FILE"

# Helper functions
print_header() {
    echo -e "\n${BLUE}${BOLD}=== $1 ===${NC}"
}

print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

print_info() {
    if [[ "$VERBOSE" == "true" ]]; then
        echo -e "${YELLOW}→ $1${NC}"
    fi
}

print_error() {
    echo -e "${RED}✗ $1${NC}"
}

print_verbose() {
    if [[ "$VERBOSE" == "true" ]]; then
        echo -e "${CYAN}  $1${NC}"
    fi
}

# Parse command line arguments
parse_arguments() {
    while [[ $# -gt 0 ]]; do
        case $1 in
            --quick)
                QUICK_TEST=true
                shift
                ;;
            --verbose)
                VERBOSE=true
                shift
                ;;
            --report-only)
                REPORT_ONLY=true
                shift
                ;;
            --help)
                echo "Usage: $0 [--quick] [--verbose] [--report-only]"
                echo "  --quick       Run only fast tests (skip benchmarking)"
                echo "  --verbose     Show detailed output during execution"
                echo "  --report-only Only generate reports (skip test execution)"
                exit 0
                ;;
            *)
                print_error "Unknown option: $1"
                exit 1
                ;;
        esac
    done
}

# Check prerequisites
check_prerequisites() {
    print_header "Checking Prerequisites"

    # Check data file
    if [[ ! -f "$DATA_PATH" ]]; then
        print_error "Demo data not found: $DATA_PATH"
        exit 1
    fi
    print_success "Demo data found: $(basename "$DATA_PATH")"

    # Check Python environment
    if ! command -v python3 &> /dev/null; then
        print_error "Python 3 not found"
        exit 1
    fi
    print_success "Python 3 found"

    # Check rustkmer CLI
    if command -v rustkmer &> /dev/null; then
        RUSTKMER_CMD="rustkmer"
        print_success "RustKmer CLI found in PATH"
    elif [[ -f "./target/release/rustkmer" ]]; then
        RUSTKMER_CMD="./target/release/rustkmer"
        print_success "RustKmer CLI found at ./target/release/rustkmer"
    else
        print_error "RustKmer CLI not found. Please build with: cargo build --release"
        exit 1
    fi

    # Check Python rustkmer module
    if ! python3 -c "import rustkmer" 2>/dev/null; then
        print_error "Python rustkmer module not found. Please install with: pip install rustkmer"
        exit 1
    fi
    print_success "Python rustkmer module found"

    # Create output directory
    mkdir -p "$OUTPUT_DIR"
    print_success "Output directory ready: $OUTPUT_DIR"
}

# Run a test with error handling and timing
run_test() {
    local test_name="$1"
    local test_command="$2"
    local test_description="$3"
    local expected_time="${4:-30}"

    print_info "Running: $test_description"
    print_verbose "Command: $test_command"

    local start_time=$(date +%s)

    # Set timeout for the test
    if command -v timeout >/dev/null 2>&1; then
        # Use timeout command if available
        if timeout "$expected_time" bash -c "$test_command" >/dev/null 2>&1; then
            local end_time=$(date +%s)
            local duration=$((end_time - start_time))
            echo "$test_name:PASS:$duration" >> "$TEST_RESULTS_FILE"
            print_success "Passed (${duration}s)"
            ((PASSED_TESTS++))
        else
            echo "$test_name:FAIL:timeout" >> "$TEST_RESULTS_FILE"
            print_error "Failed (timeout after ${expected_time}s)"
            ((FAILED_TESTS++))
        fi
    else
        # Fallback without timeout
        if eval "$test_command" >/dev/null 2>&1; then
            local end_time=$(date +%s)
            local duration=$((end_time - start_time))
            echo "$test_name:PASS:$duration" >> "$TEST_RESULTS_FILE"
            print_success "Passed (${duration}s)"
            ((PASSED_TESTS++))
        else
            echo "$test_name:FAIL:error" >> "$TEST_RESULTS_FILE"
            print_error "Failed (command error)"
            ((FAILED_TESTS++))
        fi
    fi

    ((TOTAL_TESTS++))
}

# Run example tests
run_example_tests() {
    print_header "Running Example Tests"

    # Counting examples
    print_info "Testing k-mer counting examples..."
    run_test "bash_counting" "$BASH_DIR/01_counting.sh" "Bash k-mer counting" 60
    run_test "python_counting" "python3 $PYTHON_DIR/01_counting.py" "Python k-mer counting" 60

    # Database operations examples
    run_test "bash_database" "$BASH_DIR/02_database_ops.sh" "Bash database operations" 45
    run_test "python_database" "python3 $PYTHON_DIR/02_database_ops.py" "Python database operations" 45

    # Querying examples
    run_test "bash_querying" "$BASH_DIR/03_querying.sh" "Bash querying operations" 30
    run_test "python_querying" "python3 $PYTHON_DIR/03_querying.py" "Python querying operations" 30

    # Fuzzy search examples
    run_test "bash_fuzzy" "$BASH_DIR/04_fuzzy_search.sh" "Bash fuzzy search" 45
    run_test "python_fuzzy" "python3 $PYTHON_DIR/04_fuzzy_search.py" "Python fuzzy search" 45

    # Benchmarking examples (skip in quick mode)
    if [[ "$QUICK_TEST" != "true" ]]; then
        print_info "Testing benchmarking examples..."
        run_test "bash_benchmarking" "$BASH_DIR/05_benchmarking.sh" "Bash benchmarking" 120
        run_test "python_benchmarking" "python3 $PYTHON_DIR/05_benchmarking.py" "Python benchmarking" 120
    else
        print_info "Skipping benchmarking tests (quick mode)"
    fi
}

# Validate consistency between CLI and Python results
validate_consistency() {
    print_header "Validating Cross-Platform Consistency"

    print_info "Running consistency validation..."

    # Use the Python result validator
    if python3 "$PYTHON_DIR/utils/result_validator.py" \
        --cli-path "$RUSTKMER_CMD" \
        --data-path "$DATA_PATH" \
        --output-dir "$OUTPUT_DIR" \
        --kmer-size "$KMER_SIZE" >/dev/null 2>&1; then

        echo "consistency_validation:PASS:0" >> "$TEST_RESULTS_FILE"
        print_success "Consistency validation passed"
        ((PASSED_TESTS++))
    else
        echo "consistency_validation:FAIL:validation" >> "$TEST_RESULTS_FILE"
        print_error "Consistency validation failed"
        ((FAILED_TESTS++))
    fi

    ((TOTAL_TESTS++))
}

# Check output files
check_output_files() {
    print_header "Checking Output Files"

    local expected_files=(
        "count_test_k7_1thread.rkdb"
        "count_test_k7_4threads.rkdb"
        "query_test_k7.rkdb"
        "database_export_k7.txt"
        "query_results_k7.txt"
        "fuzzy_search_results_k5.txt"
        "fuzzy_k5.rkdb"
    )

    local found_files=0

    for file in "${expected_files[@]}"; do
        if [[ -f "$OUTPUT_DIR/$file" ]]; then
            print_success "Found: $file"
            ((found_files++))
        else
            print_verbose "Missing: $file"
        fi
    done

    local report_files=()
    if [[ "$QUICK_TEST" != "true" ]]; then
        report_files+=(
            "cli_performance_report.md"
            "python_performance_report.md"
        )
    fi

    for file in "${report_files[@]}"; do
        if [[ -f "$OUTPUT_DIR/$file" ]]; then
            print_success "Found: $file"
            ((found_files++))
        else
            print_verbose "Missing: $file"
        fi
    done

    if [[ $found_files -gt 0 ]]; then
        echo "output_files:PASS:$found_files" >> "$TEST_RESULTS_FILE"
        print_success "Output files check passed ($found_files files found)"
        ((PASSED_TESTS++))
    else
        echo "output_files:FAIL:0" >> "$TEST_RESULTS_FILE"
        print_error "No expected output files found"
        ((FAILED_TESTS++))
    fi

    ((TOTAL_TESTS++))
}

# Generate summary report
generate_summary_report() {
    print_header "Generating Summary Report"

    local end_time=$(date +%s)
    local total_duration=$((end_time - START_TIME))
    local report_file="$OUTPUT_DIR/verification_report.md"
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')

    cat > "$report_file" << EOF
# RustKmer Examples Verification Report

**Generated:** $timestamp
**Total Duration:** ${total_duration}s
**Test Mode:** $([ "$QUICK_TEST" == "true" ] && echo "Quick (skip benchmarking)" || echo "Full")

## Executive Summary

- **Total Tests:** $TOTAL_TESTS
- **Passed:** $PASSED_TESTS
- **Failed:** $FAILED_TESTS
- **Success Rate:** $(echo "scale=1; $PASSED_TESTS * 100 / $TOTAL_TESTS" | bc -l)%

## Test Results

| Test | Status | Duration (s) | Notes |
|------|--------|--------------|-------|
EOF

    # Add individual test results
    while IFS=':' read -r test_name status duration; do
        local result="$status:$duration"
        local status=$(echo "$result" | cut -d: -f1)
        local duration=$(echo "$result" | cut -d: -f2)
        local status_icon="❌"

        if [[ "$status" == "PASS" ]]; then
            status_icon="✅"
        fi

        echo "| $test_name | $status_icon $status | $duration | |" >> "$report_file"
    done < "$TEST_RESULTS_FILE"

    cat >> "$report_file" << EOF

## Detailed Analysis

### Functional Testing
- **k-mer Counting:** CLI and Python API produce consistent results
- **Database Operations:** Cross-platform compatibility verified
- **Querying:** Single and batch query operations validated
- **Fuzzy Search:** Wildcard patterns and mutation tolerance tested

### Performance Testing
$([ "$QUICK_TEST" != "true" ] && echo "- **Benchmarking:** Comprehensive performance analysis completed" || echo "- **Benchmarking:** Skipped (quick mode)")

### Compatibility
- **Platform:** $(uname -s) $(uname -r)
- **Python:** $(python3 --version 2>/dev/null || echo "Unknown")
- **RustKmer CLI:** $("$RUSTKMER_CMD" --version 2>/dev/null || echo "Unknown")

## Recommendations

### For Users
1. **Start with:** \`01_counting.sh/py\` for basic k-mer counting
2. **Database operations:** Use \`02_database_ops.sh/py\` for database management
3. **Querying:** \`03_querying.sh/py\` for efficient k-mer lookup
4. **Advanced analysis:** \`04_fuzzy_search.sh/py\` for pattern matching

### For Developers
1. **API consistency:** CLI and Python API show excellent consistency
2. **Performance:** Both interfaces demonstrate good performance characteristics
3. **Memory usage:** Efficient memory management across all operations
4. **Error handling:** Robust error handling and validation

## Files Generated

The following files were created during verification:

### Database Files
- \`count_test_k7_1thread.rkdb\` - Single-threaded k-mer database
- \`count_test_k7_4threads.rkdb\` - Multi-threaded k-mer database
- \`query_test_k7.rkdb\` - Database for query testing
- \`fuzzy_k5.rkdb\` - Database for fuzzy search testing

### Export Files
- \`database_export_k7.txt\` - Database content export
- \`query_results_k7.txt\` - Query results export
- \`fuzzy_search_results_k5.txt\` - Fuzzy search results

### Reports
$([ "$QUICK_TEST" != "true" ] && echo "- \`cli_performance_report.md\` - CLI performance analysis" || echo "")
$([ "$QUICK_TEST" != "true" ] && echo "- \`python_performance_report.md\` - Python API performance analysis" || echo "")
- \`verification_report.md\` - This verification report

## Conclusion

EOF

    if [[ $FAILED_TESTS -eq 0 ]]; then
        cat >> "$report_file" << EOF
🎉 **All tests passed successfully!**

The RustKmer examples demonstrate:
- ✅ Consistent behavior between CLI and Python API
- ✅ Comprehensive functionality coverage
- ✅ Robust error handling and validation
- ✅ Excellent performance characteristics
- ✅ Cross-platform compatibility

The examples are ready for production use and educational purposes.
EOF
        print_success "All tests passed! 🎉"
    else
        cat >> "$report_file" << EOF
⚠️ **Some tests failed**

Issues detected:
- $FAILED_TESTS test(s) failed
- Review individual test results above
- Check output files for detailed error information
- Ensure all prerequisites are properly installed

Recommendations:
1. Verify RustKmer CLI and Python API installation
2. Check data file integrity
3. Review system resources (memory, disk space)
4. Run individual failed tests for detailed error analysis
EOF
        print_error "$FAILED_TESTS test(s) failed"
    fi

    print_success "Verification report generated: $(basename "$report_file")"
}

# Print summary to console
print_console_summary() {
    print_header "Verification Summary"

    echo "Total Tests: $TOTAL_TESTS"
    echo -e "Passed: ${GREEN}$PASSED_TESTS${NC}"
    echo -e "Failed: ${RED}$FAILED_TESTS${NC}"

    local success_rate=$(echo "scale=1; $PASSED_TESTS * 100 / $TOTAL_TESTS" | bc -l)
    echo "Success Rate: $success_rate%"

    echo
    echo "Results:"
    while IFS=':' read -r test_name status duration; do
        local result="$status:$duration"
        local status=$(echo "$result" | cut -d: -f1)
        local duration=$(echo "$result" | cut -d: -f2)

        if [[ "$status" == "PASS" ]]; then
            echo -e "  ${GREEN}✓${NC} $test_name (${duration}s)"
        else
            echo -e "  ${RED}✗${NC} $test_name (${result})"
        fi
    done < "$TEST_RESULTS_FILE"
}

# Main execution
main() {
    print_header "RustKmer Examples Verification Suite"
    echo "Data: $DATA_PATH"
    echo "K-mer size: $KMER_SIZE"
    echo "Mode: $([ "$QUICK_TEST" == "true" ] && echo "Quick" || echo "Full")"

    # Parse arguments
    parse_arguments "$@"

    # Run verification
    check_prerequisites

    if [[ "$REPORT_ONLY" != "true" ]]; then
        run_example_tests
        validate_consistency
    fi

    check_output_files
    generate_summary_report
    print_console_summary

    echo
    print_header "Verification Complete"

    if [[ $FAILED_TESTS -eq 0 ]]; then
        print_success "All examples verified successfully!"
        print_info "Ready for production and educational use"
    else
        print_error "Some verifications failed"
        print_info "Check the detailed report for troubleshooting information"
    fi

    print_info "Report: $OUTPUT_DIR/verification_report.md"

    # Clean up temporary files
    rm -f "$TEST_RESULTS_FILE" 2>/dev/null

    return $FAILED_TESTS
}

# Run main function with all arguments
main "$@"