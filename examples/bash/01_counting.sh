#!/usr/bin/env bash

# RustKmer CLI K-mer Counting Example
#
# This script demonstrates k-mer counting using the RustKmer CLI with
# k=7 for optimal performance with the demo rice genome data.
#
# Data: examples/data/demo_rice_genome.fa.gz
# K-mer size: 7 (optimal for demo data)
# Output: Multiple database files with different configurations

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

    # Test if CLI can read the data
    print_info "Validating data compatibility with CLI..."
    if ! $RUSTKMER_CMD count -k 3 -i "$DATA_PATH" -o /tmp/test_validation.rkdb --quiet 2>/dev/null; then
        print_error "CLI cannot read the demo data file (possible UTF-8 validation issue with N characters)"
        print_info "This is a known issue with the current CLI version."
        print_info "The Python API example works perfectly with this data."
        print_info "To test the CLI example, use a file without N characters or contact developers."
        exit 1
    fi
    rm -f /tmp/test_validation.rkdb
    print_success "Data is compatible with CLI"
}

# Create output directory
create_output_dir() {
    print_header "Creating Output Directory"

    mkdir -p "$OUTPUT_DIR"
    print_success "Created output directory: $OUTPUT_DIR"
}

# Basic k-mer counting demonstration
basic_counting() {
    print_header "Basic K-mer Counting"

    local output_file="${OUTPUT_DIR}/demo_k7_basic.rkdb"

    print_info "Counting k-mers with k=$KMER_SIZE..."
    time $RUSTKMER_CMD count \
        -k "$KMER_SIZE" \
        -i "$DATA_PATH" \
        -o "$output_file" \
        --quiet

    if [[ -f "$output_file" ]]; then
        local db_size=$(stat -f%z "$output_file" 2>/dev/null || stat -c%s "$output_file" 2>/dev/null)
        print_success "Created database: $output_file ($(format_file_size $db_size))"

        # Show database info
        print_info "Database information:"
        $RUSTKMER_CMD stats "$output_file" --table
    else
        print_error "Failed to create database"
        return 1
    fi
}

# Multi-threaded k-mer counting demonstration
threaded_counting() {
    print_header "Multi-threaded K-mer Counting"

    local threads=(1 2 4 8)

    for threads in "${threads[@]}"; do
        local output_file="${OUTPUT_DIR}/demo_k7_threads_${threads}.rkdb"

        print_info "Counting with $threads thread(s)..."
        time $RUSTKMER_CMD count \
            -k "$KMER_SIZE" \
            -t "$threads" \
            -i "$DATA_PATH" \
            -o "$output_file" \
            --quiet

        if [[ -f "$output_file" ]]; then
            local db_size=$(stat -f%z "$output_file" 2>/dev/null || stat -c%s "$output_file" 2>/dev/null)
            print_success "Created database with $threads threads: $(format_file_size $db_size)"
        else
            print_error "Failed to create database with $threads threads"
            return 1
        fi
    done
}

# Canonical vs non-canonical k-mer counting
canonical_comparison() {
    print_header "Canonical vs Non-canonical K-mer Counting"

    # Non-canonical database
    local non_canonical_file="${OUTPUT_DIR}/demo_k7_noncanonical.rkdb"
    print_info "Counting non-canonical k-mers..."
    time $RUSTKMER_CMD count \
        -k "$KMER_SIZE" \
        -i "$DATA_PATH" \
        -o "$non_canonical_file" \
        --quiet

    # Canonical database
    local canonical_file="${OUTPUT_DIR}/demo_k7_canonical.rkdb"
    print_info "Counting canonical k-mers..."
    time $RUSTKMER_CMD count \
        -k "$KMER_SIZE" \
        -i "$DATA_PATH" \
        -o "$canonical_file" \
        --canonical \
        --quiet

    # Compare results
    if [[ -f "$non_canonical_file" && -f "$canonical_file" ]]; then
        print_info "Non-canonical database stats:"
        $RUSTKMER_CMD stats "$non_canonical_file" --table

        print_info "Canonical database stats:"
        $RUSTKMER_CMD stats "$canonical_file" --table

        local non_canonical_size=$(stat -f%z "$non_canonical_file" 2>/dev/null || stat -c%s "$non_canonical_file" 2>/dev/null)
        local canonical_size=$(stat -f%z "$canonical_file" 2>/dev/null || stat -c%s "$canonical_file" 2>/dev/null)

        print_info "Database size comparison:"
        echo "  Non-canonical: $(format_file_size $non_canonical_size)"
        echo "  Canonical:    $(format_file_size $canonical_size)"

        if [[ "$non_canonical_size" -gt "$canonical_size" ]]; then
            local reduction=$(( (non_canonical_size - canonical_size) * 100 / non_canonical_size ))
            print_success "Canonical mode reduces database size by ${reduction}%"
        fi
    else
        print_error "Failed to create canonical/non-canonical databases"
        return 1
    fi
}

# Export functionality demonstration
export_functionality() {
    print_header "Database Export Functionality"

    local db_file="${OUTPUT_DIR}/demo_k7_basic.rkdb"
    local export_file="${OUTPUT_DIR}/demo_k7_export.txt"

    if [[ -f "$db_file" ]]; then
        print_info "Exporting database to text format..."
        time $RUSTKMER_CMD dump \
            "$db_file" \
            -o "$export_file"

        if [[ -f "$export_file" ]]; then
            local export_size=$(stat -f%z "$export_file" 2>/dev/null || stat -c%s "$export_file" 2>/dev/null)
            local line_count=$(wc -l < "$export_file")

            print_success "Exported database to: $export_file"
            print_info "Export size: $(format_file_size $export_size)"
            print_info "Total k-mers: $line_count"

            # Show first few lines
            print_info "Sample of exported k-mers:"
            head -10 "$export_file"
        else
            print_error "Failed to export database"
            return 1
        fi
    else
        print_error "Database file not found for export: $db_file"
        return 1
    fi
}

# Performance summary
performance_summary() {
    print_header "Performance Summary"

    print_info "Files created in $OUTPUT_DIR:"
    ls -lh "$OUTPUT_DIR"/*.rkdb 2>/dev/null | awk '{printf "  %-30s %s\n", $9, $5}'

    print_info "Quick stats comparison:"
    for file in "$OUTPUT_DIR"/*.rkdb; do
        if [[ -f "$file" ]]; then
            local filename=$(basename "$file")
            local kmer_count=$($RUSTKMER_CMD stats "$file" --quiet | head -1 | awk '{print $NF}')
            echo "  $filename: $kmer_count unique k-mers"
        fi
    done
}

# Cleanup function
cleanup() {
    print_header "Cleanup"

    read -p "Do you want to remove all generated database files? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        rm -rf "$OUTPUT_DIR"
        print_success "Removed output directory: $OUTPUT_DIR"
    else
        print_info "Output files kept in: $OUTPUT_DIR"
    fi
}

# Main execution
main() {
    print_header "RustKmer CLI K-mer Counting Examples"
    echo "Data: $DATA_PATH"
    echo "K-mer size: $KMER_SIZE"
    echo "Output: $OUTPUT_DIR"
    echo

    # Run all demonstrations
    check_rustkmer
    check_demo_data
    create_output_dir
    basic_counting
    threaded_counting
    canonical_comparison
    export_functionality
    performance_summary

    print_header "Examples Completed Successfully!"
    print_info "All databases created with k=$KMER_SIZE"
    print_info "You can now query these databases using:"
    echo "  $RUSTKMER_CMD query ${OUTPUT_DIR}/demo_k7_basic.rkdb ACGTACG"
    echo "  $RUSTKMER_CMD fuzzy-query ${OUTPUT_DIR}/demo_k7_basic.rkdb ACGNACG"

    # Ask for cleanup
    cleanup
}

# Trap cleanup on script exit
trap cleanup EXIT

# Run main function
main "$@"