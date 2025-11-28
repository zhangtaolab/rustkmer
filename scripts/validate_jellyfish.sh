#!/bin/bash

# Jellyfish validation script for rustkmer
# Compares rustkmer output with jellyfish golden standard

set -e

# Configuration
TEST_DATA_DIR="${TEST_DATA_DIR:-/Users/forrest/Temp/demodata}"
RUSTKMER_BIN="${RUSTKMER_BIN:-target/release/rustkmer}"
JELLYFISH_BIN="${JELLYFISH_BIN:-jellyfish}"
OUTPUT_DIR="${OUTPUT_DIR:-${TEST_DATA_DIR}/test_output}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Create output directory
mkdir -p "$OUTPUT_DIR"

# Function to log messages
log() {
    echo -e "${NC}[$(date '+%Y-%m-%d %H:%M:%S')] $1${NC}"
}

# Function to log success
success() {
    echo -e "${GREEN}✓ $1${NC}"
}

# Function to log error
error() {
    echo -e "${RED}✗ $1${NC}"
}

# Function to log warning
warning() {
    echo -e "${YELLOW}⚠ $1${NC}"
}

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Function to run jellyfish comparison
compare_with_jellyfish() {
    local kmer_size=$1
    local canonical=$2
    local input_file=$3

    local base_name=$(basename "$input_file" .fa)
    local jellyfish_out="${OUTPUT_DIR}/${base_name}_jellyfish_${kmer_size}_${canonical}.jf"
    local rustkmer_out="${OUTPUT_DIR}/${base_name}_rustkmer_${kmer_size}_${canonical}.rk"
    local comparison_result="${OUTPUT_DIR}/${base_name}_comparison_${kmer_size}_${canonical}.txt"

    log "Testing k=$kmer_size canonical=$canonical on $input_file"

    # Run jellyfish
    log "Running jellyfish..."
    local jellyfish_cmd="$JELLYFISH_BIN count"
    if [ "$canonical" = "canonical" ]; then
        jellyfish_cmd="$jellyfish_cmd -C"
    fi

    $jellyfish_cmd -m "$kmer_size" -s 100M -o "$jellyfish_out" "$input_file"
    success "Jellyfish completed"

    # Run rustkmer
    log "Running rustkmer..."
    if [ "$canonical" = "canonical" ]; then
        $RUSTKMER_BIN count -k "$kmer_size" -C -o "$rustkmer_out" "$input_file"
    else
        $RUSTKMER_BIN count -k "$kmer_size" -o "$rustkmer_out" "$input_file"
    fi
    success "RustKmer completed"

    # Compare results (placeholder - actual comparison will be implemented later)
    log "Comparing results..."
    echo "Comparison for k=$kmer_size canonical=$canonical" > "$comparison_result"
    echo "Jellyfish output: $jellyfish_out" >> "$comparison_result"
    echo "RustKmer output: $rustkmer_out" >> "$comparison_result"
    echo "Status: Comparison not yet implemented" >> "$comparison_result"

    success "Comparison saved to $comparison_result"
}

# Main validation function
run_validation() {
    log "Starting jellyfish validation"

    # Check dependencies
    if ! command_exists "$JELLYFISH_BIN"; then
        error "jellyfish not found. Please install jellyfish."
        exit 1
    fi

    if [ ! -f "$RUSTKMER_BIN" ]; then
        error "rustkmer binary not found at $RUSTKMER_BIN"
        error "Please build rustkmer first: cargo build --release"
        exit 1
    fi

    # Test data files
    local test_files=(
        "$TEST_DATA_DIR/fasta/osa1_r7.asm.fa"
    )

    for test_file in "${test_files[@]}"; do
        if [ ! -f "$test_file" ]; then
            warning "Test file not found: $test_file"
            continue
        fi

        # Test with k=13 (small)
        compare_with_jellyfish 13 "non_canonical" "$test_file"
        compare_with_jellyfish 13 "canonical" "$test_file"

        # TODO: Add k=21 tests after k=13 validation passes
        # compare_with_jellyfish 21 "non_canonical" "$test_file"
        # compare_with_jellyfish 21 "canonical" "$test_file"
    done

    success "Validation completed"
}

# Run validation if script is executed directly
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    run_validation "$@"
fi