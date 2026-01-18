#!/usr/bin/env python3
"""Test script to verify PyCounter's __repr__ method"""

import sys
import os

# Add the pyo3 directory to Python path
sys.path.insert(0, "/Users/forrest/GitHub/rustkmer/pyo3/target/debug")

try:
    from rustkmer import PyCounter

    # Create a counter
    counter = PyCounter(kmer_length=21, canonical=True)

    # Get the repr output
    repr_str = repr(counter)

    print(f"repr(counter) = {repr_str}")
    print(
        f"Expected format: PyCounter(kmer_length=21, canonical=True, total_kmers=0, unique_kmers=0)"
    )

    # Check if it contains "PyCounter"
    if "PyCounter" in repr_str:
        print("✓ PASS: repr contains 'PyCounter'")
    else:
        print("✗ FAIL: repr does NOT contain 'PyCounter'")

    # Check if it contains "KmerCounter"
    if "KmerCounter" in repr_str:
        print("✗ FAIL: repr contains 'KmerCounter' (should be 'PyCounter')")
    else:
        print("✓ PASS: repr does NOT contain 'KmerCounter'")

except ImportError as e:
    print(f"Failed to import rustkmer: {e}")
    print(
        "Please build the pyo3 crate first with: cargo build --manifest-path=/Users/forrest/GitHub/rustkmer/pyo3/Cargo.toml"
    )
    sys.exit(1)
except Exception as e:
    print(f"Error: {e}")
    import traceback

    traceback.print_exc()
    sys.exit(1)
