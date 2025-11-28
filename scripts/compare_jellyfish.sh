#!/bin/bash

# Jellyfish vs RustKmer comparison script
# Usage: ./scripts/compare_jellyfish.sh <kmer_size> <input_file> [canonical_flag]

set -euo pipefail

# Check arguments
if [ $# -lt 2 ]; then
    echo "Usage: $0 <kmer_size> <input_file> [canonical_flag]"
    echo "Example: $0 13 /Users/forrest/Temp/demodata/fasta/osa1_r7.asm.fa"
    echo "Example: $0 13 /Users/forrest/Temp/demodata/fasta/osa1_r7.asm.fa -C"
    exit 1
fi

KMER_SIZE="$1"
INPUT_FILE="$2"
CANONICAL_FLAG="${3:-}"

# Validate kmer size
if ! [[ "$KMER_SIZE" =~ ^[0-9]+$ ]] || [ "$KMER_SIZE" -lt 1 ] || [ "$KMER_SIZE" -gt 127 ]; then
    echo "Error: k-mer size must be between 1 and 127"
    exit 1
fi

# Validate input file exists
if [ ! -f "$INPUT_FILE" ]; then
    echo "Error: Input file '$INPUT_FILE' does not exist"
    exit 1
fi

# Create output directories
OUTPUT_DIR="/Users/forrest/Temp/demodata/validation_output"
JELLYFISH_DIR="$OUTPUT_DIR/jellyfish"
RUSTKMER_DIR="$OUTPUT_DIR/rustkmer"
mkdir -p "$JELLYFISH_DIR" "$RUSTKMER_DIR"

# Generate base filename for outputs
BASENAME=$(basename "$INPUT_FILE" .fa)
BASENAME=$(basename "$BASENAME" .fasta)
BASENAME=$(basename "$BASENAME" .fna)

JELLYFISH_OUTPUT="$JELLYFISH_DIR/${BASENAME}_k${KMER_SIZE}${CANONICAL_FLAG}.jf"
RUSTKMER_OUTPUT="$RUSTKMER_DIR/${BASENAME}_k${KMER_SIZE}${CANONICAL_FLAG}.txt"
RUSTKMER_BINARY="$RUSTKMER_DIR/${BASENAME}_k${KMER_SIZE}${CANONICAL_FLAG}.rk"

echo "=== RustKmer vs Jellyfish Comparison ==="
echo "K-mer size: $KMER_SIZE"
echo "Input file: $INPUT_FILE"
echo "Canonical mode: ${CANONICAL_FLAG:-No}"
echo "Output directory: $OUTPUT_DIR"
echo

# Get absolute paths
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
RUSTKMER_BIN="$SCRIPT_DIR/../target/release/rustkmer"

# Check if rustkmer binary exists
if [ ! -f "$RUSTKMER_BIN" ]; then
    echo "Building rustkmer in release mode..."
    cargo build --release
fi

# Step 1: Run Jellyfish
echo "Step 1: Running Jellyfish..."
# Use 8 threads by default (adjustable for macOS compatibility)
THREAD_COUNT=8
JELLYFISH_CMD="jellyfish count -m $KMER_SIZE -s 1000000 -t $THREAD_COUNT -o $JELLYFISH_OUTPUT $INPUT_FILE"
if [ -n "$CANONICAL_FLAG" ]; then
    JELLYFISH_CMD="jellyfish count -m $KMER_SIZE -s 1000000 -t $THREAD_COUNT -C -o $JELLYFISH_OUTPUT $INPUT_FILE"
fi

echo "Command: $JELLYFISH_CMD"
eval $JELLYFISH_CMD

if [ ! -f "$JELLYFISH_OUTPUT" ]; then
    echo "Error: Jellyfish failed to create output file"
    exit 1
fi

# Step 2: Run RustKmer
echo "Step 2: Running RustKmer..."
RUSTKMER_CMD="$RUSTKMER_BIN count -k $KMER_SIZE -i $INPUT_FILE -o $RUSTKMER_OUTPUT --format text"
if [ -n "$CANONICAL_FLAG" ]; then
    RUSTKMER_CMD="$RUSTKMER_BIN count -k $KMER_SIZE -i $INPUT_FILE -o $RUSTKMER_OUTPUT --format text -C"
fi

echo "Command: $RUSTKMER_CMD"
eval $RUSTKMER_CMD

if [ ! -f "$RUSTKMER_OUTPUT" ]; then
    echo "Error: RustKmer failed to create output file"
    exit 1
fi

# Step 3: Convert Jellyfish output to text format for comparison
echo "Step 3: Converting Jellyfish output to text format..."
JELLYFISH_TEXT="$JELLYFISH_DIR/${BASENAME}_k${KMER_SIZE}${CANONICAL_FLAG}.txt"
jellyfish dump -c "$JELLYFISH_OUTPUT" > "$JELLYFISH_TEXT"

# Step 4: Generate comparison statistics
echo "Step 4: Generating comparison statistics..."

# Count unique k-mers
JELLYFISH_COUNT=$(wc -l < "$JELLYFISH_TEXT")
RUSTKMER_COUNT=$(wc -l < "$RUSTKMER_OUTPUT")

# Count total k-mers
JELLYFISH_TOTAL=$(awk '{sum += $2} END {print sum}' "$JELLYFISH_TEXT")
RUSTKMER_TOTAL=$(awk '{sum += $2} END {print sum}' "$RUSTKMER_OUTPUT")

# Find top 10 k-mers
JELLYFISH_TOP=$(sort -k2,2nr "$JELLYFISH_TEXT" | head -10)
RUSTKMER_TOP=$(sort -k2,2nr "$RUSTKMER_OUTPUT" | head -10)

echo "=== Comparison Results ==="
echo "Jellyfish unique k-mers: $JELLYFISH_COUNT"
echo "RustKmer unique k-mers: $RUSTKMER_COUNT"
echo "Unique k-mer difference: $((JELLYFISH_COUNT - RUSTKMER_COUNT))"
echo
echo "Jellyfish total k-mers: $JELLYFISH_TOTAL"
echo "RustKmer total k-mers: $RUSTKMER_TOTAL"
echo "Total k-mer difference: $((JELLYFISH_TOTAL - RUSTKMER_TOTAL))"
echo

# Step 5: Detailed comparison
echo "Step 5: Detailed comparison..."

# Compare sorted outputs
JELLYFISH_SORTED="$JELLYFISH_DIR/${BASENAME}_k${KMER_SIZE}${CANONICAL_FLAG}_sorted.txt"
RUSTKMER_SORTED="$RUSTKMER_DIR/${BASENAME}_k${KMER_SIZE}${CANONICAL_FLAG}_sorted.txt"

sort "$JELLYFISH_TEXT" > "$JELLYFISH_SORTED"
sort "$RUSTKMER_OUTPUT" > "$RUSTKMER_SORTED"

# Find differences
DIFF_FILE="$OUTPUT_DIR/${BASENAME}_k${KMER_SIZE}${CANONICAL_FLAG}_diff.txt"
if diff "$JELLYFISH_SORTED" "$RUSTKMER_SORTED" > "$DIFF_FILE"; then
    echo "✅ PERFECT MATCH: Outputs are identical!"
    MATCH_STATUS="PERFECT"
else
    echo "❌ DIFFERENCES FOUND: Outputs differ"
    MATCH_STATUS="DIFFERENCES"

    # Count differences
    DIFF_COUNT=$(wc -l < "$DIFF_FILE")
    echo "Number of differing lines: $DIFF_COUNT"

    # Show first 10 differences
    echo "First 10 differences:"
    head -20 "$DIFF_FILE"
fi

# Step 6: Generate summary report
REPORT_FILE="$OUTPUT_DIR/${BASENAME}_k${KMER_SIZE}${CANONICAL_FLAG}_report.txt"
cat > "$REPORT_FILE" << EOF
RustKmer vs Jellyfish Comparison Report
========================================

Configuration:
- K-mer size: $KMER_SIZE
- Input file: $INPUT_FILE
- Canonical mode: ${CANONICAL_FLAG:-No}
- Comparison date: $(date)

Results Summary:
- Match Status: $MATCH_STATUS
- Jellyfish unique k-mers: $JELLYFISH_COUNT
- RustKmer unique k-mers: $RUSTKMER_COUNT
- Unique k-mer difference: $((JELLYFISH_COUNT - RUSTKMER_COUNT))
- Jellyfish total k-mers: $JELLYFISH_TOTAL
- RustKmer total k-mers: $RUSTKMER_TOTAL
- Total k-mer difference: $((JELLYFISH_TOTAL - RUSTKMER_TOTAL))

Files Generated:
- Jellyfish binary: $JELLYFISH_OUTPUT
- Jellyfish text: $JELLYFISH_TEXT
- RustKmer text: $RUSTKMER_OUTPUT
- Differences: $DIFF_FILE
- Sorted jellyfish: $JELLYFISH_SORTED
- Sorted rustkmer: $RUSTKMER_SORTED

Top 10 k-mers (Jellyfish):
$JELLYFISH_TOP

Top 10 k-mers (RustKmer):
$RUSTKMER_TOP
EOF

echo "Step 6: Report generated: $REPORT_FILE"
echo
echo "=== Comparison Complete ==="

# Return appropriate exit code
if [ "$MATCH_STATUS" = "PERFECT" ]; then
    exit 0
else
    exit 1
fi