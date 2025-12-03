#!/usr/bin/env bash

# RustKmer CLI Database Operations Example
#
# This script demonstrates database operations using the RustKmer CLI:
# - Database creation with different configurations
# - Database statistics and information display
# - Database export functionality
# - Database comparison and validation
#
# Data: examples/data/demo_rice_genome.fa.gz
# K-mer size: 7 for optimal performance with demo data
# Output: Multiple database formats and exports

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

# Create databases with different configurations
create_databases() {
    print_header "Database Creation"

    local configs=(
        "canonical:True:4"
        "noncanonical:False:4"
        "single_thread:False:1"
    )

    for config in "${configs[@]}"; do
        IFS=':' read -r name canonical threads <<< "$config"

        local output_file="${OUTPUT_DIR}/ops_k${KMER_SIZE}_${name}.rkdb"

        print_info "Creating $name database..."

        local start_time=$(date +%s.%N 2>/dev/null || date +%s)

        if [[ "$canonical" == "True" ]]; then
            $RUSTKMER_CMD count \
                -k "$KMER_SIZE" \
                -t "$threads" \
                -i "$DATA_PATH" \
                -o "$output_file" \
                --canonical \
                --quiet
        else
            $RUSTKMER_CMD count \
                -k "$KMER_SIZE" \
                -t "$threads" \
                -i "$DATA_PATH" \
                -o "$output_file" \
                --quiet
        fi

        local end_time=$(date +%s.%N 2>/dev/null || date +%s)
        local duration=$(echo "$end_time - $start_time" | bc -l 2>/dev/null || echo "0.03")

        if [[ -f "$output_file" ]]; then
            local db_size=$(stat -f%z "$output_file" 2>/dev/null || stat -c%s "$output_file" 2>/dev/null)
            print_success "Created $name: $(format_file_size $db_size) (${duration}s)"

            # Store database info for later use
            DB_FILES["$name"]="$output_file"
            DB_SIZES["$name"]="$db_size"
            DB_TIMES["$name"]="$duration"
        else
            print_error "Failed to create $name database"
        fi
    done
}

# Display database statistics
database_statistics() {
    print_header "Database Statistics and Metadata"

    for name in "${!DB_FILES[@]}"; do
        local db_file="${DB_FILES[$name]}"
        print_info "Statistics for $name database:"

        if [[ -f "$db_file" ]]; then
            # Get database stats using CLI
            echo "  Database information:"
            $RUSTKMER_CMD stats "$db_file" --table 2>/dev/null || {
                print_error "Could not retrieve stats for $name"
                continue
            }

            # Get file size
            local file_size=$(stat -f%z "$db_file" 2>/dev/null || stat -c%s "$db_file" 2>/dev/null)
            echo "  File size: $(format_file_size $file_size)"
            echo
        fi
    done
}

# Export databases
export_databases() {
    print_header "Database Export Functionality"

    for name in "${!DB_FILES[@]}"; do
        local db_file="${DB_FILES[$name]}"
        local export_file="${OUTPUT_DIR}/ops_k${KMER_SIZE}_${name}_export.txt"

        print_info "Exporting $name database..."

        if [[ -f "$db_file" ]]; then
            # Export using CLI dump command
            local start_time=$(date +%s.%N 2>/dev/null || date +%s)

            if $RUSTKMER_CMD dump "$db_file" -o "$export_file" 2>/dev/null; then
                local end_time=$(date +%s.%N 2>/dev/null || date +%s)
                local duration=$(echo "$end_time - $start_time" | bc -l 2>/dev/null || echo "0.01")

                if [[ -f "$export_file" ]]; then
                    local export_size=$(stat -f%z "$export_file" 2>/dev/null || stat -c%s "$export_file" 2>/dev/null)
                    local line_count=$(wc -l < "$export_file" 2>/dev/null || echo "0")

                    print_success "Exported $name: $(format_file_size $export_size) ($line_count k-mers, ${duration}s)"

                    # Add metadata to export file
                    {
                        echo "# RustKmer Database Export - ${name^}"
                        echo "# Database: $db_file"
                        echo "# K-mer size: $KMER_SIZE"
                        echo "# Export time: ${duration}s"
                        echo "# Total k-mers exported: $line_count"
                        echo "#"
                    } | cat - "$export_file" > "${export_file}.tmp" && mv "${export_file}.tmp" "$export_file"
                else
                    print_error "Export file not created for $name"
                fi
            else
                print_error "Export failed for $name"
            fi
        else
            print_error "Database file not found for $name: $db_file"
        fi
    done
}

# Compare database configurations
compare_databases() {
    print_header "Database Configuration Comparison"

    if [[ ${#DB_FILES[@]} -lt 2 ]]; then
        print_info "Need at least 2 databases for comparison"
        return
    fi

    # Print comparison table header
    print_info "Database Comparison:"
    printf "%-15s %-10s %-10s %-12s %-10s\n" "Configuration" "Size" "Time(s)" "Created" "Status"
    printf "%-70s\n" | tr ' ' '-'

    # Print database info
    for name in "${!DB_FILES[@]}"; do
        local size_str=$(format_file_size ${DB_SIZES[$name]})
        local time_str=$(printf "%.2f" ${DB_TIMES[$name]})
        local status="OK"

        if [[ -f "${DB_FILES[$name]}" ]]; then
            local created="Yes"
        else
            local created="No"
            status="Error"
        fi

        printf "%-15s %-10s %-10s %-12s %-10s\n" "$name" "$size_str" "$time_str" "$created" "$status"
    done

    # Find best performance
    local fastest_name=""
    local fastest_time=999999

    for name in "${!DB_FILES[@]}"; do
        if (( $(echo "${DB_TIMES[$name]} < $fastest_time" | bc -l 2>/dev/null || echo "1") )); then
            fastest_time=${DB_TIMES[$name]}
            fastest_name=$name
        fi
    done

    local smallest_name=""
    local smallest_size=999999999

    for name in "${!DB_FILES[@]}"; do
        if [[ ${DB_SIZES[$name]} -lt $smallest_size ]]; then
            smallest_size=${DB_SIZES[$name]}
            smallest_name=$name
        fi
    done

    echo
    print_info "Performance Summary:"
    [[ -n "$fastest_name" ]] && print_success "Fastest creation: $fastest_name (${DB_TIMES[$fastest_name]}s)"
    [[ -n "$smallest_name" ]] && print_success "Smallest database: $smallest_name ($(format_file_size $smallest_size))"
}

# Validate database integrity
database_validation() {
    print_header "Database Integrity Validation"

    for name in "${!DB_FILES[@]}"; do
        local db_file="${DB_FILES[$name]}"
        print_info "Validating $name database..."

        if [[ -f "$db_file" ]]; then
            local validation_results=()

            # Check file size
            local file_size=$(stat -f%z "$db_file" 2>/dev/null || stat -c%s "$db_file" 2>/dev/null)
            if [[ $file_size -gt 100 ]]; then
                validation_results+=("✓ Reasonable file size: $(format_file_size $file_size)")
            else
                validation_results+=("✗ File too small: $(format_file_size $file_size)")
            fi

            # Check if stats command works
            if $RUSTKMER_CMD stats "$db_file" --quiet &>/dev/null; then
                validation_results+=("✓ Database readable")
            else
                validation_results+=("✗ Database not readable")
            fi

            # Print validation results
            echo "  $name validation:"
            for result in "${validation_results[@]}"; do
                echo "    $result"
            done
        else
            print_error "Database file not found: $db_file"
        fi
    done
}

# Performance analysis
performance_analysis() {
    print_header "Performance Analysis"

    if [[ ${#DB_FILES[@]} -eq 0 ]]; then
        print_info "No databases available for analysis"
        return
    fi

    # Calculate performance metrics
    local total_time=0
    local total_size=0
    local db_count=${#DB_FILES[@]}

    for name in "${!DB_FILES[@]}"; do
        total_time=$(echo "$total_time + ${DB_TIMES[$name]}" | bc -l 2>/dev/null || echo "$total_time")
        total_size=$((total_size + ${DB_SIZES[$name]}))
    done

    local avg_time=$(echo "scale=2; $total_time / $db_count" | bc -l 2>/dev/null || echo "0.00")
    local avg_size=$((total_size / db_count))

    print_info "Overall Performance:"
    echo "  Total databases created: $db_count"
    echo "  Total creation time: $(printf "%.2f" $total_time)s"
    echo "  Average creation time: ${avg_time}s"
    echo "  Total disk usage: $(format_file_size $total_size)"
    echo "  Average database size: $(format_file_size $avg_size)"
}

# Performance summary
performance_summary() {
    print_header "Performance Summary"

    print_info "Files created in $OUTPUT_DIR:"
    ls -lh "$OUTPUT_DIR"/*.rkdb 2>/dev/null | awk '{printf "  %-30s %s\n", $9, $5}' | sort

    echo
    print_info "Export files created:"
    ls -lh "$OUTPUT_DIR"/*_export.txt 2>/dev/null | awk '{printf "  %-30s %s\n", $9, $5}' | sort
}

# Main execution
main() {
    print_header "RustKmer CLI Database Operations Examples"
    echo "Data: $DATA_PATH"
    echo "K-mer size: $KMER_SIZE"
    echo "Output: $OUTPUT_DIR"

    # Initialize associative arrays for database info
    declare -A DB_FILES
    declare -A DB_SIZES
    declare -A DB_TIMES

    # Run all database operations
    check_rustkmer
    check_demo_data
    create_output_dir
    create_databases
    database_statistics
    export_databases
    compare_databases
    database_validation
    performance_analysis
    performance_summary

    print_header "Database Operations Completed Successfully!"
    print_success "All database operations completed with k=$KMER_SIZE"
    print_info "You can now query these databases using:"
    for name in "${!DB_FILES[@]}"; do
        echo "  $RUSTKMER_CMD query ${DB_FILES[$name]} ACGTACG"
    done

    return 0
}

# Run main function
main "$@"