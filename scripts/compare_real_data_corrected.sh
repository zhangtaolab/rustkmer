#!/bin/bash

echo "=== Real Data Comparison: RustKmer vs Jellyfish Query Results ==="
echo "Testing k-mers from actual dataset (k=21):"
echo

# Extract first 25 k-mers from jellyfish dump for comparison
echo "Extracting k-mers from jellyfish dump..."
jellyfish dump -c /Users/forrest/Temp/demodata/jellyfish_k21.jf | head -25 > /tmp/jellyfish_top25.txt

# Extract first 25 k-mers from rustkmer dump for comparison
echo "Extracting k-mers from rustkmer dump..."
./target/release/rustkmer dump /Users/forrest/Temp/demodata/test_real_rustkmer_k21.rkdb | head -25 > /tmp/rustkmer_top25.txt

echo "Comparison of top 25 k-mers:"
echo "K-mer | RustKmer | Jellyfish | Match?"
echo "------|----------|-----------|-------"

# Read k-mers from jellyfish output and test both tools
while IFS=$'\t' read -r kmer count; do
    # Skip if line is empty or malformed
    if [[ -z "$kmer" || -z "$count" ]]; then
        continue
    fi

    # Query rustkmer for this k-mer
    rustkmer_result=$(./target/release/rustkmer query /Users/forrest/Temp/demodata/test_real_rustkmer_k21.rkdb "$kmer" 2>/dev/null | grep -E "^[ACGT]+:" | tail -1 | cut -d: -f2 | tr -d ' ' || echo "NOT_FOUND")

    # Clean up rustkmer result - it might have extra formatting
    if [[ "$rustkmer_result" == *"count:"* ]]; then
        rustkmer_result=$(echo "$rustkmer_result" | grep -o 'count: [0-9]*' | cut -d' ' -f2)
    fi

    if [[ "$rustkmer_result" == "NOT_FOUND" || "$rustkmer_result" == "ERROR" || -z "$rustkmer_result" ]]; then
        rustkmer_result="0"
    fi

    # Get jellyfish count (already have it from the dump)
    jellyfish_result="$count"

    # Check if they match (allow some tolerance for large numbers)
    match="✓"
    if [[ "$rustkmer_result" != "$jellyfish_result" ]]; then
        # Check if it's a scaling issue (one is much larger)
        if [[ "$rustkmer_result" -gt 0 && "$jellyfish_result" -gt 0 ]]; then
            ratio=$((rustkmer_result / jellyfish_result))
            if [[ $ratio -gt 1000 || $ratio -lt 1 ]]; then
                match="✗ (scaled)"
            else
                match="✗"
            fi
        else
            match="✗"
        fi
    fi

    printf "%-21s | %-9s | %-9s | %s\n" "$kmer" "$rustkmer_result" "$jellyfish_result" "$match"

    # Only process first 25 k-mers
    count=$((count + 1))
    if [[ $count -ge 25 ]]; then
        break
    fi
done < /tmp/jellyfish_top25.txt

echo
echo "=== Database Statistics ==="
echo "RustKmer database info:"
./target/release/rustkmer info /Users/forrest/Temp/demodata/test_real_rustkmer_k21.rkdb 2>/dev/null || echo "Info command not available"

echo
echo "Jellyfish database info:"
jellyfish info -c /Users/forrest/Temp/demodata/jellyfish_k21.jf 2>/dev/null || echo "Info command not available"

echo
echo "=== Sample Verification ==="
echo "Testing a few specific k-mers with both tools:"

# Test a specific k-mer that appears frequently
test_kmer="AAAAAAAAAAAAAAAAAAAG"  # 21 A's with G at the end
echo "Testing k-mer: $test_kmer"

rustkmer_result=$(./target/release/rustkmer query /Users/forrest/Temp/demodata/test_real_rustkmer_k21.rkdb "$test_kmer" 2>/dev/null | grep -o '[0-9]\+' | tail -1 || echo "0")
jellyfish_result=$(jellyfish query /Users/forrest/Temp/demodata/jellyfish_k21.jf "$test_kmer" 2>/dev/null | awk '{print $2}' || echo "0")

echo "RustKmer: $rustkmer_result"
echo "Jellyfish: $jellyfish_result"

if [[ "$rustkmer_result" == "$jellyfish_result" ]]; then
    echo "✓ Results match!"
else
    echo "✗ Results differ"
fi