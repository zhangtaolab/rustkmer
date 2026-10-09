#!/bin/bash
# Deterministic FASTQ slice: first N reads (4 lines each) of a gz stream.
# Usage: ./scripts/bench/make_slice.sh INPUT N_READS OUTPUT
#
# Portable decompression via gunzip -c — the macOS compress-family zcat
# variant is never invoked (plan 04-01 RESEARCH Pitfall 1). Identical output
# bytes for the same INPUT and N_READS on every machine.

set -e

if [ "$#" -ne 3 ]; then
    echo "Usage: $0 INPUT N_READS OUTPUT" >&2
    exit 1
fi

INPUT="$1"
N_READS="$2"
OUTPUT="$3"

case "$N_READS" in
    ''|*[!0-9]*)
        echo "error: N_READS must be a positive integer, got '$N_READS'" >&2
        exit 1
        ;;
esac
if [ "$N_READS" -lt 1 ]; then
    echo "error: N_READS must be >= 1, got '$N_READS'" >&2
    exit 1
fi
if [ ! -f "$INPUT" ]; then
    echo "error: INPUT not found: '$INPUT'" >&2
    exit 1
fi

gunzip -c "$INPUT" | head -n $((4 * N_READS)) > "$OUTPUT"
