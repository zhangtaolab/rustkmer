#!/usr/bin/env bash

# RustKmer CLI Querying Example
#
# This script demonstrates querying functionality using the RustKmer CLI:
# - Single k-mer queries
# - Batch query operations from files
# - Query result analysis
# - Performance comparison of query methods
#
# Data: examples/data/demo_rice_genome.fa.gz
# K-mer size: 7 for optimal performance with demo data
# Output: Query results and performance analysis

set -e  # Exit on any error

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DATA_PATH="${SCRIPT_DIR}/../data/demo_rice_genome.fa.gz"
KMER_SIZE=7
OUTPUT_DIR="${SCRIPT_DIR}/../output"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Helper functions
print_header() {
    echo -e "${BLUE}=== $1 ===${NC}"
}

print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

print_info() {
    echo -e "${YELLOW}→ $1${NC}"
}

print_error() {
    echo -e "${RED}✗ $1${NC}"
}

# Format file size in human readable format (macOS compatible)
format_file_size() {
    local size=$1
    if [ "$size" -lt 1024 ]; then
        echo "${size}B"
    elif [ "$size" -lt 1048576 ]; then
        echo "$(( size / 1024 ))KB"
    else
        echo "$(( size / 1048576 ))MB"
    fi
}

# Check if rustkmer CLI is available
check_rustkmer() {
    print_header "Checking RustKmer CLI"

    if ! command -v rustkmer &> /dev/null; then
        if [[ -f "./target/release/rustkmer" ]]; then
            RUSTKMER_CMD="./target/release/rustkmer"
            print_success "Found RustKmer CLI at ./target/release/rustkmer"
        else
            print_error "RustKmer CLI not found. Please build with: cargo build --release"
            exit 1
        fi
    else
        RUSTKMER_CMD="rustkmer"
        print_success "Found RustKmer CLI in PATH"
    fi
}

# Check if demo data exists and validate it
check_demo_data() {
    print_header "Checking Demo Data"

    if [[ ! -f "$DATA_PATH" ]]; then
        print_error "Demo data not found: $DATA_PATH"
        exit 1
    fi

    local file_size=$(stat -f%z "$DATA_PATH" 2>/dev/null || stat -c%s "$DATA_PATH" 2>/dev/null)
    print_success "Found demo data: $DATA_PATH ($(format_file_size $file_size))"
}

# Create output directory
create_output_dir() {
    print_header "Creating Output Directory"

    mkdir -p "$OUTPUT_DIR"
    print_success "Created output directory: $OUTPUT_DIR"
}

# Create test database for querying
create_test_database() {
    print_header "Creating Test Database"

    local db_file="${OUTPUT_DIR}/query_test_k${KMER_SIZE}.rkdb"

    if [[ -f "$db_file" ]]; then
        print_info "Using existing database: $(basename "$db_file")"
        DB_PATH="$db_file"
        return
    fi

    print_info "Creating test database with k=$KMER_SIZE..."
    local start_time=$(date +%s.%N 2>/dev/null || date +%s)

    if $RUSTKMER_CMD count \
        -k "$KMER_SIZE" \
        -t 4 \
        -i "$DATA_PATH" \
        -o "$db_file" \
        --quiet; then

        local end_time=$(date +%s.%N 2>/dev/null || date +%s)
        local duration=$(echo "$end_time - $start_time" | bc -l 2>/dev/null || echo "0.03")

        if [[ -f "$db_file" ]]; then
            local file_size=$(stat -f%z "$db_file" 2>/dev/null || stat -c%s "$db_file" 2>/dev/null)
            print_success "Created database: $(basename "$db_file") ($(format_file_size $file_size), ${duration}s)"
            DB_PATH="$db_file"
        else
            print_error "Failed to create database"
            exit 1
        fi
    else
        print_error "Database creation failed"
        exit 1
    fi
}

# Create test k-mer files for batch querying
create_query_files() {
    print_header "Creating Query Files"

    # Create test k-mers file
    local query_file="${OUTPUT_DIR}/test_kmers_k${KMER_SIZE}.txt"

    print_info "Creating test k-mer file..."

    # Generate test k-mers
    {
        # Homopolymers
        printf "%s\n" "A$(printf 'A%.0s' $(seq 1 $((KMER_SIZE-1))))"
        printf "%s\n" "T$(printf 'T%.0s' $(seq 1 $((KMER_SIZE-1))))"
        printf "%s\n" "C$(printf 'C%.0s' $(seq 1 $((KMER_SIZE-1))))"
        printf "%s\n" "G$(printf 'G%.0s' $(seq 1 $((KMER_SIZE-1))))"

        # Repeating patterns
        local pattern="ACGTACGTACGTACGTACGTACGTACGT"
        printf "%s\n" "${pattern:0:$KMER_SIZE}"

        local pattern2="TGCATGCATGCATGCATGCATGCATGCA"
        printf "%s\n" "${pattern2:0:$KMER_SIZE}"

        local pattern3="ATGCATGCATGCATGCATGCATGCATGC"
        printf "%s\n" "${pattern3:0:$KMER_SIZE}"

        local pattern4="CGATCGATCGATCGATCGATCGATCGAT"
        printf "%s\n" "${pattern4:0:$KMER_SIZE}"

        # Some mixed patterns
        printf "%s\n" "ACGTAAA"
        printf "%s\n" "TTTTGGG"
        printf "%s\n" "CCCTTTT"
        printf "%s\n" "GGGCCCAA"

    } > "$query_file"

    if [[ -f "$query_file" ]]; then
        local line_count=$(wc -l < "$query_file")
        print_success "Created query file with $line_count k-mers"
        QUERY_FILE="$query_file"
    else
        print_error "Failed to create query file"
        exit 1
    fi

    # Create larger query file for batch testing
    local large_query_file="${OUTPUT_DIR}/large_test_kmers_k${KMER_SIZE}.txt"
    print_info "Creating large query file for batch testing..."

    {
        # Add some random patterns
        for i in {1..50}; do
            # Generate random k-mer
            local kmer=""
            for j in $(seq 1 $KMER_SIZE); do
                case $((RANDOM % 4)) in
                    0) kmer="${kmer}A" ;;
                    1) kmer="${kmer}T" ;;
                    2) kmer="${kmer}C" ;;
                    3) kmer="${kmer}G" ;;
                esac
            done
            printf "%s\n" "$kmer"
        done
    } > "$large_query_file"

    if [[ -f "$large_query_file" ]]; then
        local line_count=$(wc -l < "$large_query_file")
        print_success "Created large query file with $line_count k-mers"
        LARGE_QUERY_FILE="$large_query_file"
    else
        print_error "Failed to create large query file"
        exit 1
    fi
}

# Single query demonstration
single_query_demo() {
    print_header "Single K-mer Query Demo"

    local test_kmers=(
        "AAAAAAA"
        "TTTTTTT"
        "CCCCCCC"
        "GGGGGGG"
        "ACGTACG"
        "TGCATGC"
        "ATGCATG"
        "CGATCGA"
    )

    print_info "Testing individual k-mer queries:"
    printf "%-10s %-6s %-10s %-15s\n" "K-mer" "Found" "Count" "Query Time (ms)"
    printf "%-50s\n" | tr ' ' '-'

    local total_time=0
    local found_count=0

    for kmer in "${test_kmers[@]}"; do
        local start_time=$(date +%s.%N 2>/dev/null || date +%s)

        # Use CLI query command
        if result=$($RUSTKMER_CMD query "$DB_PATH" "$kmer" 2>/dev/null); then
            local end_time=$(date +%s.%N 2>/dev/null || date +%s)
            local query_time_ms=$(echo "scale=3; ($end_time - $start_time) * 1000" | bc -l 2>/dev/null || echo "0.001")

            if [[ -n "$result" && "$result" != *"not found"* ]]; then
                # Extract count from result
                local count=$(echo "$result" | awk '{print $2}' 2>/dev/null || echo "1")
                printf "%-10s %-6s %-10s %-15.3f\n" "$kmer" "YES" "$count" "$query_time_ms"
                ((found_count++))
            else
                printf "%-10s %-6s %-10s %-15.3f\n" "$kmer" "NO" "0" "$query_time_ms"
            fi
        else
            local end_time=$(date +%s.%N 2>/dev/null || date +%s)
            local query_time_ms=$(echo "scale=3; ($end_time - $start_time) * 1000" | bc -l 2>/dev/null || echo "0.001")
            printf "%-10s %-6s %-10s %-15.3f\n" "$kmer" "ERROR" "0" "$query_time_ms"
        fi

        total_time=$(echo "$total_time + $query_time_ms" | bc -l 2>/dev/null || echo "$total_time")
    done

    printf "%-50s\n" | tr ' ' '-'
    print_info "Summary:"
    echo "  K-mers tested: ${#test_kmers[@]}"
    echo "  K-mers found: $found_count"
    echo "  Average query time: $(echo "scale=3; $total_time / ${#test_kmers[@]}" | bc -l 2>/dev/null || echo "0.001") ms"
}

# Batch query demonstration
batch_query_demo() {
    print_header "Batch K-mer Query Demo"

    if [[ ! -f "$QUERY_FILE" ]]; then
        print_error "Query file not found: $QUERY_FILE"
        return
    fi

    local line_count=$(wc -l < "$QUERY_FILE")
    print_info "Testing batch query with $line_count k-mers"

    # Time the batch query
    local start_time=$(date +%s.%N 2>/dev/null || date +%s)

    # Note: CLI doesn't have a built-in batch query, so we simulate it
    local found_count=0
    local total_count=0

    while IFS= read -r kmer; do
        if result=$($RUSTKMER_CMD query "$DB_PATH" "$kmer" 2>/dev/null); then
            if [[ -n "$result" && "$result" != *"not found"* ]]; then
                ((found_count++))
                local count=$(echo "$result" | awk '{print $2}' 2>/dev/null || echo "1")
                total_count=$((total_count + count))
            fi
        fi
    done < "$QUERY_FILE"

    local end_time=$(date +%s.%N 2>/dev/null || date +%s)
    local total_time_ms=$(echo "scale=3; ($end_time - $start_time) * 1000" | bc -l 2>/dev/null || echo "1.000")

    print_info "Batch Query Results:"
    echo "  K-mers queried: $line_count"
    echo "  K-mers found: $found_count"
    echo "  Total count: $total_count"
    echo "  Query time: ${total_time_ms} ms"
    echo "  Average per query: $(echo "scale=3; $total_time_ms / $line_count" | bc -l 2>/dev/null || echo "0.001") ms"
}

# Database information
database_info() {
    print_header "Database Information"

    if [[ ! -f "$DB_PATH" ]]; then
        print_error "Database file not found: $DB_PATH"
        return
    fi

    local file_size=$(stat -f%z "$DB_PATH" 2>/dev/null || stat -c%s "$DB_PATH" 2>/dev/null)

    print_info "Database File:"
    echo "  File path: $DB_PATH"
    echo "  File size: $(format_file_size $file_size)"
    echo "  File name: $(basename "$DB_PATH")"

    print_info "Database Statistics:"
    # Use CLI stats command
    if $RUSTKMER_CMD stats "$DB_PATH" --table 2>/dev/null; then
        print_success "Database statistics retrieved successfully"
    else
        print_error "Could not retrieve database statistics"
    fi
}

# Export query results
export_query_results() {
    print_header "Export Query Results"

    if [[ ! -f "$QUERY_FILE" ]]; then
        print_error "Query file not found: $QUERY_FILE"
        return
    fi

    local export_file="${OUTPUT_DIR}/query_results_export_k${KMER_SIZE}.txt"
    print_info "Exporting query results to file..."

    {
        echo "# RustKmer CLI Query Results Export"
        echo "# Database: $DB_PATH"
        echo "# K-mer size: $KMER_SIZE"
        echo "# Export timestamp: $(date)"
        echo "# Format: KMER COUNT"
        echo "# =================================================="

        local found_count=0
        while IFS= read -r kmer; do
            if result=$($RUSTKMER_CMD query "$DB_PATH" "$kmer" 2>/dev/null); then
                if [[ -n "$result" && "$result" != *"not found"* ]]; then
                    local count=$(echo "$result" | awk '{print $2}' 2>/dev/null || echo "1")
                    echo "$kmer $count"
                    ((found_count++))
                fi
            fi
        done < "$QUERY_FILE"

        echo ""
        echo "# Summary:"
        echo "# K-mers with counts: $found_count"
    } > "$export_file"

    if [[ -f "$export_file" ]]; then
        local export_size=$(stat -f%z "$export_file" 2>/dev/null || stat -c%s "$export_file" 2>/dev/null)
        print_success "Exported results to: $(basename "$export_file")"
        print_info "Export size: $(format_file_size $export_size)"

        # Show top few results
        print_info "Sample of exported results:"
        head -15 "$export_file" | grep -v "^#" | head -10
    else
        print_error "Failed to export query results"
    fi
}

# Performance testing
performance_testing() {
    print_header "Query Performance Testing"

    if [[ ! -f "$LARGE_QUERY_FILE" ]]; then
        print_error "Large query file not found: $LARGE_QUERY_FILE"
        return
    fi

    local line_count=$(wc -l < "$LARGE_QUERY_FILE")
    print_info "Performance testing with $line_count k-mers"

    # Test performance
    local start_time=$(date +%s.%N 2>/dev/null || date +%s)

    local processed=0
    local found_count=0
    while IFS= read -r kmer && [[ $processed -lt 100 ]]; do
        if $RUSTKMER_CMD query "$DB_PATH" "$kmer" --quiet &>/dev/null; then
            ((found_count++))
        fi
        ((processed++))
    done < "$LARGE_QUERY_FILE"

    local end_time=$(date +%s.%N 2>/dev/null || date +%s)
    local total_time_ms=$(echo "scale=3; ($end_time - $start_time) * 1000" | bc -l 2>/dev/null || echo "1.000")

    print_info "Performance Test Results:"
    echo "  K-mers processed: $processed"
    echo "  K-mers found: $found_count"
    echo "  Query time: ${total_time_ms} ms"
    echo "  K-mers per second: $(echo "scale=0; $processed / ($total_time_ms / 1000)" | bc -l 2>/dev/null || echo "0")"
}

# Performance summary
performance_summary() {
    print_header "Performance Summary"

    print_info "Files created in $OUTPUT_DIR:"
    ls -lh "$OUTPUT_DIR"/*.rkdb 2>/dev/null | awk '{printf "  %-30s %s\n", $9, $5}' | sort
    echo
    print_info "Query files created:"
    ls -lh "$OUTPUT_DIR"/*_k${KMER_SIZE}*.txt 2>/dev/null | awk '{printf "  %-30s %s\n", $9, $5}' | sort
}

# Main execution
main() {
    print_header "RustKmer CLI Querying Examples"
    echo "Data: $DATA_PATH"
    echo "K-mer size: $KMER_SIZE"
    echo "Output: $OUTPUT_DIR"

    # Run all querying operations
    check_rustkmer
    check_demo_data
    create_output_dir
    create_test_database
    create_query_files
    database_info
    single_query_demo
    batch_query_demo
    export_query_results
    performance_testing
    performance_summary

    print_header "Querying Examples Completed Successfully!"
    print_success "All querying examples completed with k=$KMER_SIZE"
    print_info "Query results exported to output directory"
    print_info "You can now query the database using:"
    echo "  $RUSTKMER_CMD query $DB_PATH ACGTACG"

    return 0
}

# Run main function
main "$@"