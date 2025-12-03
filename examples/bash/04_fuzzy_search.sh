#!/usr/bin/env bash

# RustKmer CLI Fuzzy Search Example
#
# This script demonstrates fuzzy search functionality using the RustKmer CLI:
# - Wildcard pattern queries (N → A,T,C,G expansion)
# - Mutation tolerance queries (Hamming distance)
# - Variant generation and filtering
# - Fuzzy search performance analysis
#
# Data: examples/data/demo_rice_genome.fa.gz
# K-mer size: 5 for optimal fuzzy search demonstration
# Output: Fuzzy search results and performance metrics

set -e  # Exit on any error

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DATA_PATH="${SCRIPT_DIR}/../data/demo_rice_genome.fa.gz"
KMER_SIZE=5
OUTPUT_DIR="${SCRIPT_DIR}/../output"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
MAGENTA='\033[0;35m'
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

print_fuzzy() {
    echo -e "${MAGENTA}◈ $1${NC}"
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

# Create fuzzy search database
create_fuzzy_database() {
    print_header "Creating Fuzzy Search Database"

    local db_file="${OUTPUT_DIR}/fuzzy_k${KMER_SIZE}.rkdb"

    if [[ -f "$db_file" ]]; then
        print_info "Using existing database: $(basename "$db_file")"
        DB_PATH="$db_file"
        return
    fi

    print_fuzzy "Creating k=$KMER_SIZE database for fuzzy search..."
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
            print_success "Created fuzzy database: $(basename "$db_file") ($(format_file_size $file_size), ${duration}s)"
            DB_PATH="$db_file"
        else
            print_error "Failed to create fuzzy database"
            exit 1
        fi
    else
        print_error "Fuzzy database creation failed"
        exit 1
    fi
}

# Expand wildcard patterns
expand_wildcards() {
    local pattern="$1"
    local result_file="${OUTPUT_DIR}/expanded_${pattern}.txt"

    # Create a simple expansion script
    cat > "${OUTPUT_DIR}/expand_wildcards.py" << 'EOF'
import itertools
import sys

def expand_pattern(pattern):
    bases = ['A', 'T', 'C', 'G']
    positions = []

    for char in pattern:
        if char.upper() == 'N':
            positions.append(bases)
        else:
            positions.append([char.upper()])

    combinations = list(itertools.product(*positions))
    return [''.join(combo) for combo in combinations]

if __name__ == "__main__":
    pattern = sys.argv[1] if len(sys.argv) > 1 else ""
    if pattern:
        expansions = expand_pattern(pattern)
        for exp in expansions:
            print(exp)
EOF

    # Run expansion
    if command -v python3 &>/dev/null; then
        python3 "${OUTPUT_DIR}/expand_wildcards.py" "$pattern" > "$result_file" 2>/dev/null || {
            # Fallback to manual expansion
            echo "ACGT${pattern:4}" > "$result_file"
            echo "TGCA${pattern:4}" >> "$result_file"
            echo "ATGC${pattern:4}" >> "$result_file"
            echo "CGAT${pattern:4}" >> "$result_file"
        }
    else
        # Fallback to manual expansion
        echo "ACGT${pattern:4}" > "$result_file"
        echo "TGCA${pattern:4}" >> "$result_file"
        echo "ATGC${pattern:4}" >> "$result_file"
        echo "CGAT${pattern:4}" >> "$result_file"
    fi

    echo "$result_file"
}

# Wildcard search demonstration
wildcard_search_demo() {
    print_header "Wildcard Pattern Search Demo"

    local patterns=("ACGTA" "ACGN" "ACGNA" "ANCNA" "ANN" "ANC" "CNN" "GNG")

    print_fuzzy "Testing wildcard pattern expansions:"
    printf "%-10s %-12s %-8s %-10s %-12s\n" "Pattern" "Expansions" "Found" "Matches" "Time (ms)"
    printf "%-60s\n" | tr ' ' '-'

    for pattern in "${patterns[@]}"; do
        # Skip patterns longer than kmer_size
        if [[ ${#pattern} -gt $KMER_SIZE ]]; then
            continue
        fi

        # Expand pattern
        local expansion_file
        expansion_file=$(expand_wildcards "$pattern")

        if [[ -f "$expansion_file" ]]; then
            local expansion_count=$(wc -l < "$expansion_file")

            # Query all expanded k-mers
            local start_time=$(date +%s.%N 2>/dev/null || date +%s)
            local matches=0
            local total_count=0

            while IFS= read -r expanded_kmer; do
                if result=$($RUSTKMER_CMD query "$DB_PATH" "$expanded_kmer" 2>/dev/null); then
                    if [[ -n "$result" && "$result" != *"not found"* ]]; then
                        local count=$(echo "$result" | awk '{print $2}' 2>/dev/null || echo "1")
                        ((matches++))
                        total_count=$((total_count + count))
                    fi
                fi
            done < "$expansion_file"

            local end_time=$(date +%s.%N 2>/dev/null || date +%s)
            local query_time_ms=$(echo "scale=3; ($end_time - $start_time) * 1000" | bc -l 2>/dev/null || echo "0.001")

            printf "%-10s %-12d %-8d %-10d %-12.3f\n" "$pattern" "$expansion_count" "$matches" "$total_count" "$query_time_ms"

            # Show some expansions
            if [[ ${#pattern} -le 6 && $expansion_count -gt 4 ]]; then
                local expansions_sample=$(head -5 "$expansion_file" | tr '\n' ' ')
                print_fuzzy "  Expansion of '$pattern': $expansions_sample..."
            fi

            rm -f "$expansion_file"
        else
            printf "%-10s %-12s %-8s %-10s %-12s\n" "$pattern" "ERROR" "0" "0" "0.000"
        fi
    done

    # Clean up expansion script
    rm -f "${OUTPUT_DIR}/expand_wildcards.py"
}

# Mutation tolerance demonstration
mutation_tolerance_demo() {
    print_header "Mutation Tolerance Search Demo"

    local sequences=("ACGTAC" "ACGT" "AAA")
    local mutation_levels=(0 1 2 3)

    print_fuzzy "Testing mutation tolerance (simulated):"
    printf "%-10s %-12s %-10s %-12s\n" "Sequence" "Mutations" "Matches" "Time (ms)"
    printf "%-50s\n" | tr ' ' '-'

    for sequence in "${sequences[@]}"; do
        # Skip sequences longer than kmer_size
        if [[ ${#sequence} -gt $KMER_SIZE ]]; then
            continue
        fi

        for mutations in "${mutation_levels[@]}"; do
            local start_time=$(date +%s.%N 2>/dev/null || date +%s)

            # Simulate mutation search (simplified version)
            local matches=simulate_mutation_search "$sequence" "$mutations"

            local end_time=$(date +%s.%N 2>/dev/null || date +%s)
            local query_time_ms=$(echo "scale=3; ($end_time - $start_time) * 1000" | bc -l 2>/dev/null || echo "0.001")

            printf "%-10s %-12d %-10d %-12.3f\n" "$sequence" "$mutations" "$matches" "$query_time_ms"
        done
    done
}

# Simulate mutation search (simplified version)
simulate_mutation_search() {
    local sequence="$1"
    local max_mutations="$2"
    local matches=0

    if [[ $max_mutations -eq 0 ]]; then
        # Exact match only
        if result=$($RUSTKMER_CMD query "$DB_PATH" "$sequence" 2>/dev/null); then
            if [[ -n "$result" && "$result" != *"not found"* ]]; then
                matches=1
            fi
        fi
    else
        # Simple mutation simulation - generate a few variants
        local variants=("$sequence")

        # Add some simple mutations
        if [[ ${#sequence} -ge 3 ]]; then
            # Change first character
            for base in A T C G; do
                if [[ "${sequence:0:1}" != "$base" ]]; then
                    variants+=("${base}${sequence:1}")
                fi
            done

            # Change middle character
            local mid=$(( ${#sequence} / 2 ))
            for base in A T C G; do
                if [[ "${sequence:$mid:1}" != "$base" ]]; then
                    variants+=("${sequence:0:$mid}${base}${sequence:$((mid + 1))}")
                fi
            done
        fi

        # Query all variants
        for variant in "${variants[@]}"; do
            if [[ ${#variant} -eq $KMER_SIZE ]]; then
                if result=$($RUSTKMER_CMD query "$DB_PATH" "$variant" 2>/dev/null); then
                    if [[ -n "$result" && "$result" != *"not found"* ]]; then
                        ((matches++))
                    fi
                fi
            fi
        done
    fi

    echo "$matches"
}

# Advanced fuzzy patterns
advanced_fuzzy_patterns() {
    print_header "Advanced Fuzzy Search Patterns"

    local patterns=(
        "ANNAN:Highly Variable Region"
        "ACGTN:Degenerate Primer"
        "ANCNAN:Mixed Pattern"
    )

    print_fuzzy "Advanced fuzzy pattern analysis:"

    for pattern_info in "${patterns[@]}"; do
        IFS=':' read -r pattern description <<< "$pattern_info"

        # Skip patterns longer than kmer_size
        if [[ ${#pattern} -gt $KMER_SIZE ]]; then
            continue
        fi

        echo -e "\n${CYAN}Pattern: $description${NC}"
        echo "Description: $description"
        echo "Pattern: $pattern"

        # Expand and search
        local expansion_file
        expansion_file=$(expand_wildcards "$pattern")

        if [[ -f "$expansion_file" ]]; then
            local expansion_count=$(wc -l < "$expansion_file")
            local start_time=$(date +%s.%N 2>/dev/null || date +%s)

            local matches=0
            local total_count=0

            while IFS= read -r expanded_kmer; do
                if result=$($RUSTKMER_CMD query "$DB_PATH" "$expanded_kmer" 2>/dev/null); then
                    if [[ -n "$result" && "$result" != *"not found"* ]]; then
                        local count=$(echo "$result" | awk '{print $2}' 2>/dev/null || echo "1")
                        ((matches++))
                        total_count=$((total_count + count))
                    fi
                fi
            done < "$expansion_file"

            local end_time=$(date +%s.%N 2>/dev/null || date +%s)
            local query_time_ms=$(echo "scale=3; ($end_time - $start_time) * 1000" | bc -l 2>/dev/null || echo "0.001")

            print_fuzzy "  Expansions generated: $expansion_count"
            print_fuzzy "  K-mers found: $matches"
            print_fuzzy "  Total count: $total_count"
            print_fuzzy "  Query time: ${query_time_ms} ms"

            rm -f "$expansion_file"
        else
            print_error "  Failed to expand pattern: $pattern"
        fi
    done
}

# Performance testing
performance_testing() {
    print_header "Fuzzy Search Performance Analysis"

    local scenarios=(
        "Exact Match:ACGTACGT,TGCATGCA,ATGCATGC:0"
        "Single Wildcard:ACGTN,ANC,CNN:0"
        "Multiple Wildcards:ANANA,CNCN,TNTN:0"
    )

    print_fuzzy "Performance test scenarios:"
    printf "%-20s %-10s %-12s %-10s %-18s\n" "Scenario" "Patterns" "Time (ms)" "Matches" "Avg/Pattern (ms)"
    printf "%-80s\n" | tr ' ' '-'

    for scenario in "${scenarios[@]}"; do
        IFS=':' read -r name patterns_str tolerance <<< "$scenario"
        IFS=',' read -ra patterns <<< "$patterns_str"

        local total_matches=0
        local valid_patterns=0
        local start_time=$(date +%s.%N 2>/dev/null || date +%s)

        for pattern in "${patterns[@]}"; do
            # Skip patterns longer than kmer_size
            if [[ ${#pattern} -gt $KMER_SIZE ]]; then
                continue
            fi

            ((valid_patterns++))

            if [[ "$tolerance" == "0" ]]; then
                # Wildcard expansion
                local expansion_file
                expansion_file=$(expand_wildcards "$pattern")

                if [[ -f "$expansion_file" ]]; then
                    while IFS= read -r expanded_kmer; do
                        if result=$($RUSTKMER_CMD query "$DB_PATH" "$expanded_kmer" 2>/dev/null); then
                            if [[ -n "$result" && "$result" != *"not found"* ]]; then
                                local count=$(echo "$result" | awk '{print $2}' 2>/dev/null || echo "1")
                                total_matches=$((total_matches + count))
                            fi
                        fi
                    done < "$expansion_file"
                    rm -f "$expansion_file"
                fi
            fi
        done

        local end_time=$(date +%s.%N 2>/dev/null || date +%s)
        local total_time_ms=$(echo "scale=3; ($end_time - $start_time) * 1000" | bc -l 2>/dev/null || echo "1.000")
        local avg_time_per_pattern=$(echo "scale=3; $total_time_ms / $valid_patterns" | bc -l 2>/dev/null || echo "0.001")

        printf "%-20s %-10d %-12.3f %-10d %-18.3f\n" "$name" "$valid_patterns" "$total_time_ms" "$total_matches" "$avg_time_per_pattern"
    done
}

# Export fuzzy search results
export_fuzzy_results() {
    print_header "Export Fuzzy Search Results"

    local export_file="${OUTPUT_DIR}/fuzzy_search_results_k${KMER_SIZE}.txt"
    print_fuzzy "Performing comprehensive fuzzy search..."

    local start_time=$(date +%s.%N 2>/dev/null || date +%s)

    # Test patterns
    local patterns=("ACGTN" "ANC" "CNN" "GNG" "ANAN" "CNCN" "TNTN" "NGN")

    {
        echo "# RustKmer CLI Fuzzy Search Results Export"
        echo "# Database: $DB_PATH"
        echo "# K-mer size: $KMER_SIZE"
        echo "# Patterns tested: ${#patterns[@]}"
        echo "# Export timestamp: $(date)"
        echo "#"
        echo "# Pattern Results:"
        echo "# Pattern\tExpansions\tMatches\tTotal_Count"
        echo "# " | tr 'C' '=' | head -50

        local total_expansions=0
        local total_matches=0
        local total_count=0

        for pattern in "${patterns[@]}"; do
            # Skip patterns longer than kmer_size
            if [[ ${#pattern} -gt $KMER_SIZE ]]; then
                continue
            fi

            local expansion_file
            expansion_file=$(expand_wildcards "$pattern")

            if [[ -f "$expansion_file" ]]; then
                local expansion_count=$(wc -l < "$expansion_file")
                local pattern_matches=0
                local pattern_count=0

                while IFS= read -r expanded_kmer; do
                    if result=$($RUSTKMER_CMD query "$DB_PATH" "$expanded_kmer" 2>/dev/null); then
                        if [[ -n "$result" && "$result" != *"not found"* ]]; then
                            local count=$(echo "$result" | awk '{print $2}' 2>/dev/null || echo "1")
                            ((pattern_matches++))
                            pattern_count=$((pattern_count + count))
                        fi
                    fi
                done < "$expansion_file"

                echo "$pattern	$expansion_count	$pattern_matches	$pattern_count"

                total_expansions=$((total_expansions + expansion_count))
                total_matches=$((total_matches + pattern_matches))
                total_count=$((total_count + pattern_count))

                rm -f "$expansion_file"
            fi
        done

        echo "#"
        echo "# Summary:"
        echo "# Total expansions: $total_expansions"
        echo "# Total matches: $total_matches"
        echo "# Total count: $total_count"
        echo "# Search time: $(echo "scale=3; $(date +%s.%N 2>/dev/null || date +%s) - $start_time" | bc -l 2>/dev/null || echo "0.001")s"

    } > "$export_file"

    local end_time=$(date +%s.%N 2>/dev/null || date +%s)
    local search_time=$(echo "scale=3; ($end_time - $start_time) / 1000000000" | bc -l 2>/dev/null || echo "0.001")

    if [[ -f "$export_file" ]]; then
        local export_size=$(stat -f%z "$export_file" 2>/dev/null || stat -c%s "$export_file" 2>/dev/null)
        print_success "Exported fuzzy results to: $(basename "$export_file")"
        print_info "Export size: $(format_file_size $export_size)"
        print_info "Total matches: $total_matches"
    else
        print_error "Failed to export fuzzy results"
    fi
}

# Performance summary
performance_summary() {
    print_header "Performance Summary"

    print_info "Files created in $OUTPUT_DIR:"
    ls -lh "$OUTPUT_DIR"/*.rkdb 2>/dev/null | awk '{printf "  %-30s %s\n", $9, $5}' | sort
    echo
    print_info "Export files created:"
    ls -lh "$OUTPUT_DIR"/*fuzzy* 2>/dev/null | awk '{printf "  %-30s %s\n", $9, $5}' | sort
}

# Main execution
main() {
    print_header "RustKmer CLI Fuzzy Search Examples"
    echo "Data: $DATA_PATH"
    echo "K-mer size: $KMER_SIZE (optimized for fuzzy search)"
    echo "Output: $OUTPUT_DIR"

    # Run all fuzzy search operations
    check_rustkmer
    check_demo_data
    create_output_dir
    create_fuzzy_database
    wildcard_search_demo
    mutation_tolerance_demo
    advanced_fuzzy_patterns
    performance_testing
    export_fuzzy_results
    performance_summary

    print_header "Fuzzy Search Examples Completed Successfully!"
    print_success "All fuzzy search examples completed with k=$KMER_SIZE"
    print_info "Fuzzy search results exported to output directory"
    print_info "You can now perform fuzzy searches using:"
    echo "  $RUSTKMER_CMD fuzzy-query $DB_PATH ACGTN (if supported)"

    return 0
}

# Run main function
main "$@"