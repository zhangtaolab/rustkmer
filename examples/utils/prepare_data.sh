#!/usr/bin/env bash

# RustKmer Data Preparation Utility
#
# This script prepares data files for RustKmer examples by:
# - Detecting compressed files (.gz)
# - Decompressing them to temporary files
# - Providing paths suitable for both CLI and Python API

set -e

# Configuration
EXAMPLES_DIR="$(dirname "$(dirname "$0")")"
DATA_DIR="$EXAMPLES_DIR/data"
TEMP_DIR="$EXAMPLES_DIR/temp"

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

print_info() {
    echo -e "${YELLOW}→ $1${NC}"
}

print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

# Create temp directory
mkdir -p "$TEMP_DIR"

# Check for compressed files and decompress them
prepare_demo_data() {
    local gz_file="$DATA_DIR/demo_rice_genome.fa.gz"
    local temp_file="$TEMP_DIR/demo_rice_genome.fa"

    if [[ -f "$gz_file" ]]; then
        print_info "Found compressed demo data, decompressing..."

        # Only decompress if temp file doesn't exist or is older
        if [[ ! -f "$temp_file" ]] || [[ "$gz_file" -nt "$temp_file" ]]; then
            gunzip -c "$gz_file" > "$temp_file"
            print_success "Decompressed to: $temp_file"
        else
            print_success "Using existing decompressed file: $temp_file"
        fi

        echo "$temp_file"
    else
        print_info "No compressed demo data found"
        echo ""
    fi
}

# Main execution
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    result=$(prepare_demo_data)
    if [[ -n "$result" ]]; then
        echo "Prepared data file: $result"
        echo "Use this path for RustKmer CLI commands"
    fi
fi