#!/bin/bash

# Automated Performance Comparison Script for prefix-query vs fuzzy-query
# This script runs comprehensive performance tests and generates comparison reports

set -e  # Exit on any error

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
BENCHMARKS_DIR="$PROJECT_ROOT/benchmarks"
RESULTS_DIR="$PROJECT_ROOT/benchmarks/results"
LOGS_DIR="$PROJECT_ROOT/benchmarks/logs"

# Create directories
mkdir -p "$RESULTS_DIR" "$LOGS_DIR"

# Default parameters
DATABASE=""
TEST_PREFIXES=""
TEST_PATTERNS=""
QUICK_MODE=false
HELP=false

# Usage function
usage() {
    cat << EOF
Usage: $0 [OPTIONS]

Automated Performance Comparison Script for prefix-query vs fuzzy-query

OPTIONS:
    -d, --database PATH       Path to RKDB database file (required)
    -p, --prefixes LIST       Space-separated list of prefixes to test
    -t, --patterns LIST       Space-separated list of fuzzy patterns to test
    -q, --quick              Run quick test with limited patterns
    -h, --help               Show this help message

EXAMPLES:
    $0 -d test_database.rkdb
    $0 -d test_database.rkdb -p "A AT ATC ATG" -t "A ATCG AAANNN"
    $0 -d test_database.rkdb --quick

For detailed performance testing, use:
    python3 $BENCHMARKS_DIR/prefix_query_performance.py

EOF
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -d|--database)
            DATABASE="$2"
            shift 2
            ;;
        -p|--prefixes)
            TEST_PREFIXES="$2"
            shift 2
            ;;
        -t|--patterns)
            TEST_PATTERNS="$2"
            shift 2
            ;;
        -q|--quick)
            QUICK_MODE=true
            shift
            ;;
        -h|--help)
            HELP=true
            shift
            ;;
        *)
            echo "Unknown option: $1"
            usage
            exit 1
            ;;
    esac
done

# Show help and exit
if [[ "$HELP" == "true" ]]; then
    usage
    exit 0
fi

# Validate required parameters
if [[ -z "$DATABASE" ]]; then
    echo "Error: Database path is required"
    echo
    usage
    exit 1
fi

if [[ ! -f "$DATABASE" ]]; then
    echo "Error: Database file not found: $DATABASE"
    exit 1
fi

# Check if compiled binary exists
if [[ ! -f "$PROJECT_ROOT/target/debug/rustkmer" ]]; then
    echo "Error: rustkmer binary not found. Please compile first:"
    echo "  cd $PROJECT_ROOT && cargo build"
    exit 1
fi

# Check if Python script exists
if [[ ! -f "$BENCHMARKS_DIR/prefix_query_performance.py" ]]; then
    echo "Error: Performance test script not found: $BENCHMARKS_DIR/prefix_query_performance.py"
    exit 1
fi

# Check Python dependencies
echo "Checking Python dependencies..."
python3 -c "import psutil" 2>/dev/null || {
    echo "Error: psutil package not installed. Please install with:"
    echo "  pip install psutil"
    exit 1
}

# Get database information
DB_SIZE=$(du -h "$DATABASE" | cut -f1)
DB_NAME=$(basename "$DATABASE")
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
LOG_FILE="$LOGS_DIR/benchmark_${DB_NAME}_${TIMESTAMP}.log"

echo "=========================================="
echo "Performance Comparison: prefix-query vs fuzzy-query"
echo "=========================================="
echo "Database: $DATABASE"
echo "Size: $DB_SIZE"
echo "Timestamp: $TIMESTAMP"
echo "Log file: $LOG_FILE"
echo "=========================================="

# Redirect all output to log file
exec > >(tee -a "$LOG_FILE")
exec 2>&1

# Define test patterns based on mode
if [[ "$QUICK_MODE" == "true" ]]; then
    echo "Running in QUICK mode..."
    PREFIXES="A AT ATC ATG ATGC"
    PATTERNS="A ATG ATCG"
else
    echo "Running in FULL mode..."
    if [[ -z "$TEST_PREFIXES" ]]; then
        PREFIXES="A AT ATC ATG ATGC AAAAA AAAAAA"
    else
        PREFIXES="$TEST_PREFIXES"
    fi
    
    if [[ -z "$TEST_PATTERNS" ]]; then
        PATTERNS="A ATG ATCG AAAAA AANNNN AAANNN"
    else
        PATTERNS="$TEST_PATTERNS"
    fi
fi

echo "Test prefixes: $PREFIXES"
echo "Test patterns: $PATTERNS"

# Step 1: Test individual commands
echo ""
echo "Step 1: Testing individual prefix-query commands..."
echo "=================================================="

for prefix in $PREFIXES; do
    echo "Testing prefix: $prefix"
    start_time=$(date +%s.%N)
    
    ./target/debug/rustkmer prefix-query "$DATABASE" "$prefix" --quiet --format table > /dev/null 2>&1
    
    end_time=$(date +%s.%N)
    duration=$(echo "$end_time - $start_time" | bc -l)
    
    echo "  Completed in ${duration}s"
done

echo ""
echo "Step 2: Testing individual fuzzy-query commands..."
echo "================================================="

for pattern in $PATTERNS; do
    echo "Testing pattern: $pattern"
    start_time=$(date +%s.%N)
    
    ./target/debug/rustkmer fuzzy-query "$DATABASE" "$pattern" --quiet > /dev/null 2>&1
    
    end_time=$(date +%s.%N)
    duration=$(echo "$end_time - $start_time" | bc -l)
    
    echo "  Completed in ${duration}s"
done

# Step 3: Run comprehensive performance tests
echo ""
echo "Step 3: Running comprehensive performance analysis..."
echo "===================================================="

python3 "$BENCHMARKS_DIR/prefix_query_performance.py" \
    "$DATABASE" \
    --output-dir "$RESULTS_DIR" \
    --prefixes $PREFIXES \
    --patterns $PATTERNS

# Step 4: Generate comparison report
echo ""
echo "Step 4: Generating comparison report..."
echo "====================================="

# Extract key metrics from results
if [[ -f "$RESULTS_DIR/performance_summary.json" ]]; then
    echo "Performance Summary:"
    echo "==================="
    
    # Use jq if available, otherwise use basic parsing
    if command -v jq >/dev/null 2>&1; then
        echo "Prefix Query Performance:"
        jq -r '.summary.prefix_query_stats // "No data"' "$RESULTS_DIR/performance_summary.json"
        
        echo ""
        echo "Fuzzy Query Performance:"
        jq -r '.summary.fuzzy_query_stats // "No data"' "$RESULTS_DIR/performance_summary.json"
        
        echo ""
        echo "Performance Comparison:"
        jq -r '.summary.performance_comparison // "No comparison available"' "$RESULTS_DIR/performance_summary.json"
    else
        echo "Install 'jq' for detailed JSON parsing"
        echo "Basic summary available in: $RESULTS_DIR/performance_summary.json"
    fi
else
    echo "Warning: Performance summary not found"
fi

# Step 5: Create detailed comparison
echo ""
echo "Step 5: Creating detailed comparison..."
echo "====================================="

# Generate HTML report if Python is available
if command -v python3 >/dev/null 2>&1; then
    python3 << 'EOF'
import json
import os
import sys

try:
    results_dir = sys.argv[1]
    summary_file = os.path.join(results_dir, 'performance_summary.json')
    
    if os.path.exists(summary_file):
        with open(summary_file, 'r') as f:
            data = json.load(f)
        
        # Generate HTML report
        html_file = os.path.join(results_dir, 'performance_report.html')
        with open(html_file, 'w') as f:
            f.write("""
<!DOCTYPE html>
<html>
<head>
    <title>Prefix Query vs Fuzzy Query Performance Report</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; }
        .header { background-color: #f0f0f0; padding: 10px; }
        .section { margin: 20px 0; }
        table { border-collapse: collapse; width: 100%; }
        th, td { border: 1px solid #ddd; padding: 8px; text-align: left; }
        th { background-color: #f2f2f2; }
        .success { color: green; }
        .error { color: red; }
    </style>
</head>
<body>
    <div class="header">
        <h1>Prefix Query vs Fuzzy Query Performance Report</h1>
        <p>Generated automatically from performance testing</p>
    </div>
""")
        
        # Add summary data
        if 'summary' in data:
            summary = data['summary']
            
            f.write(f"""
    <div class="section">
        <h2>Test Summary</h2>
        <p>Total tests: {summary.get('total_tests', 'N/A')}</p>
        <p>Successful: {summary.get('successful_tests', 'N/A')}</p>
        <p>Failed: {summary.get('failed_tests', 'N/A')}</p>
    </div>
""")
            
            # Performance stats
            if 'prefix_query_stats' in summary and summary['prefix_query_stats']:
                stats = summary['prefix_query_stats']
                f.write(f"""
    <div class="section">
        <h2>Prefix Query Performance</h2>
        <p>Average execution time: {stats.get('avg_execution_time', 0):.3f}s</p>
        <p>Average memory usage: {stats.get('avg_memory_mb', 0):.2f} MB</p>
        <p>Average throughput: {stats.get('avg_throughput', 0):.0f} matches/sec</p>
        <p>Total matches found: {stats.get('total_matches', 0)}</p>
    </div>
""")
            
            if 'fuzzy_query_stats' in summary and summary['fuzzy_query_stats']:
                stats = summary['fuzzy_query_stats']
                f.write(f"""
    <div class="section">
        <h2>Fuzzy Query Performance</h2>
        <p>Average execution time: {stats.get('avg_execution_time', 0):.3f}s</p>
        <p>Average memory usage: {stats.get('avg_memory_mb', 0):.2f} MB</p>
        <p>Average throughput: {stats.get('avg_throughput', 0):.0f} matches/sec</p>
        <p>Total matches found: {stats.get('total_matches', 0)}</p>
    </div>
""")
            
            if 'performance_comparison' in summary and summary['performance_comparison']:
                comp = summary['performance_comparison']
                f.write(f"""
    <div class="section">
        <h2>Performance Comparison</h2>
        <p>Faster command: {comp.get('faster_command', 'N/A')}</p>
        <p>Speedup factor: {comp.get('speedup_factor', 0):.1f}x</p>
        <p>Memory usage ratio: {comp.get('memory_comparison', 0):.1f}x</p>
    </div>
""")
        
        f.write("""
</body>
</html>
""")
        
        print(f"HTML report generated: {html_file}")
    else:
        print("Summary file not found")
except Exception as e:
    print(f"Error generating HTML report: {e}")
EOF
    
    python3 "$RESULTS_DIR/performance_summary.json"
else
    echo "HTML report generation skipped (Python not available)"
fi

# Final summary
echo ""
echo "=========================================="
echo "Performance Comparison Complete"
echo "=========================================="
echo "Results saved to: $RESULTS_DIR"
echo "Log file: $LOG_FILE"
echo
echo "Key files:"
echo "  - Raw results: $RESULTS_DIR/performance_results.json"
echo "  - CSV results: $RESULTS_DIR/performance_results.csv"
echo "  - Summary: $RESULTS_DIR/performance_summary.json"
echo "  - HTML report: $RESULTS_DIR/performance_report.html"
echo
echo "To view results:"
echo "  cat $RESULTS_DIR/performance_summary.json"
echo "  python3 -m json.tool $RESULTS_DIR/performance_summary.json"
echo
echo "Log file available at: $LOG_FILE"

echo ""
echo "Performance comparison completed successfully!"
