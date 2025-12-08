#!/usr/bin/env python3
"""
Examples of using rustkmer Python API with k-mers > 32

This script demonstrates how to use rustkmer with large k-mers (k > 32)
that require u128 encoding.
"""

import sys
import os

# Add rustkmer to path if not installed
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', 'src', 'python'))

try:
    import rustkmer
except ImportError:
    print("Error: rustkmer Python module not found!")
    print("Please build the Python bindings first with: cargo build --release")
    sys.exit(1)


def example_basic_usage():
    """Basic usage with k > 32"""
    print("=" * 60)
    print("Example 1: Basic Usage with k > 32")
    print("=" * 60)

    # Create a counter for 33-mers
    k = 33
    counter = rustkmer.SimpleKmerCounter(k=k, canonical=False)

    # Add some sequences
    sequences = [
        "ACGTACGTACGTACGTACGTACGTACGTACGTG",  # 33 bases
        "CCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCC",  # 33 C's
        "GGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGG",  # 33 G's
    ]

    print(f"Creating k={k} database from {len(sequences)} sequences...")

    for i, seq in enumerate(sequences):
        print(f"  Sequence {i+1}: {seq[:10]}... (length: {len(seq)})")
        counter.add_sequence(seq)

    # Get counts
    print("\nK-mer counts:")
    for i, seq in enumerate(sequences):
        if len(seq) >= k:
            kmer = seq[:k]
            count = counter.get_kmer_count(kmer)
            print(f"  {kmer[:10]}...: {count}")

    # Save database
    db_path = "example_k33.rkdb"
    counter.save(db_path)
    print(f"\nDatabase saved to: {db_path}")
    print(f"Database size: {os.path.getsize(db_path)} bytes")


def example_k64_maximum():
    """Example with maximum k=64"""
    print("\n" + "=" * 60)
    print("Example 2: Maximum k=64")
    print("=" * 60)

    k = 64
    counter = rustkmer.SimpleKmerCounter(k=k, canonical=True)

    # Create a 64-mer
    seq_64 = "ACGT" * 16  # 64 bases
    print(f"Creating k={k} database...")
    print(f"  64-mer: {seq_64[:20]}...{seq_64[-20:]}")

    counter.add_sequence(seq_64)

    # Query the database
    count = counter.get_kmer_count(seq_64)
    print(f"  Count: {count}")

    # Save
    db_path = "example_k64.rkdb"
    counter.save(db_path)
    print(f"  Database saved to: {db_path}")
    print(f"  Database size: {os.path.getsize(db_path)} bytes")


def example_canonical_mode():
    """Example with canonical mode"""
    print("\n" + "=" * 60)
    print("Example 3: Canonical Mode")
    print("=" * 60)

    k = 33
    counter = rustkmer.SimpleKmerCounter(k=k, canonical=True)

    # Add sequences where reverse complement matters
    sequences = [
        "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAC",
        "GTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTT",  # Approximate reverse complement
    ]

    print(f"Creating canonical k={k} database...")

    for seq in sequences:
        print(f"  Adding: {seq[:20]}...")
        counter.add_sequence(seq)

    db_path = "example_canonical.rkdb"
    counter.save(db_path)
    print(f"  Saved to: {db_path}")

    # Query from the database
    db = rustkmer.SimpleDatabase(db_path)

    print("\nQuerying canonical database:")
    for seq in sequences:
        if len(seq) >= k:
            kmer = seq[:k]
            count = db.query(kmer)
            print(f"  {kmer[:20]}...: {count}")


def example_batch_operations():
    """Example of batch operations"""
    print("\n" + "=" * 60)
    print("Example 4: Batch Operations")
    print("=" * 60)

    # Create a database with many k-mers
    k = 33
    counter = rustkmer.SimpleKmerCounter(k=k, canonical=False)

    print(f"Creating database with many k={k} sequences...")

    # Add many sequences
    base = "ACGTACGTACGTACGTACGTACGTACGTAC"
    for i in range(100):
        # Create variation
        suffix = "A" * (33 - len(base)) + "C"[0]
        seq = base + suffix[:33 - len(base)]
        counter.add_sequence(seq)
        if i < 5:  # Show first few
            print(f"  {seq[:20]}...")

    # Save database
    db_path = "example_batch.rkdb"
    counter.save(db_path)

    # Load for querying
    db = rustkmer.SimpleDatabase(db_path)

    # Prepare batch queries
    queries = [
        base + "A" * (33 - len(base)),
        base + "C" * (33 - len(base)),
        "T" * 33,  # Likely not in database
    ]

    print(f"\nBatch querying {len(queries)} k-mers...")
    results = db.query_batch(queries)

    print("Results:")
    for kmer, count in results:
        print(f"  {kmer[:20]}...: {count}")


def example_performance_test():
    """Simple performance test"""
    print("\n" + "=" * 60)
    print("Example 5: Performance Test")
    print("=" * 60)

    import time

    k = 48
    counter = rustkmer.SimpleKmerCounter(k=k, canonical=False)

    print(f"Performance test with k={k}")

    # Add many k-mers
    start = time.time()
    for i in range(1000):
        seq = "ACGT" * 12 + "A" * (48 - 48)  # Simplified
        counter.add_sequence(seq)
    add_time = time.time() - start

    db_path = "example_perf.rkdb"
    start = time.time()
    counter.save(db_path)
    save_time = time.time() - start

    # Load and query
    db = rustkmer.SimpleDatabase(db_path)
    test_seq = "ACGT" * 12

    start = time.time()
    for _ in range(1000):
        count = db.query(test_seq)
    query_time = time.time() - start

    print(f"  Added 1000 sequences in {add_time:.3f}s")
    print(f"  Saved database in {save_time:.3f}s")
    print(f"  Performed 1000 queries in {query_time:.3f}s")
    print(f"  Database size: {os.path.getsize(db_path)} bytes")
    print(f"  Query rate: {1000/query_time:.1f} queries/second")

    # Clean up
    os.unlink(db_path)


def example_error_handling():
    """Example of error handling"""
    print("\n" + "=" * 60)
    print("Example 6: Error Handling")
    print("=" * 60)

    # Test invalid k size
    print("Testing error handling...")

    try:
        counter = rustkmer.SimpleKmerCounter(k=65, canonical=False)
        print("  ERROR: Should have failed for k=65!")
    except Exception as e:
        print(f"  ✓ Correctly rejected k=65: {e}")

    try:
        counter = rustkmer.SimpleKmerCounter(k=0, canonical=False)
        print("  ERROR: Should have failed for k=0!")
    except Exception as e:
        print(f"  ✓ Correctly rejected k=0: {e}")

    # Test invalid database path
    try:
        db = rustkmer.SimpleDatabase("/nonexistent/path.rkdb")
        print("  ERROR: Should have failed for invalid path!")
    except Exception as e:
        print(f"  ✓ Correctly handled invalid path: {e}")

    print("  Error handling works correctly")


def cleanup():
    """Clean up example files"""
    print("\n" + "=" * 60)
    print("Cleaning up example files...")

    files_to_remove = [
        "example_k33.rkdb",
        "example_k64.rkdb",
        "example_canonical.rkdb",
        "example_batch.rkdb",
        "example_perf.rkdb",
    ]

    for file in files_to_remove:
        if os.path.exists(file):
            os.unlink(file)
            print(f"  Removed: {file}")

    print("Cleanup complete!")


def main():
    """Run all examples"""
    print("rustkmer Python API Examples - u128 Support")
    print("=" * 60)
    print("This demonstrates using rustkmer with k-mers > 32 that require u128 encoding.")
    print()

    try:
        example_basic_usage()
        example_k64_maximum()
        example_canonical_mode()
        example_batch_operations()
        example_performance_test()
        example_error_handling()

        print("\n" + "=" * 60)
        print("All examples completed successfully!")
        print("\nKey takeaways:")
        print("- rustkmer supports k-mers up to 64 bases using u128 encoding")
        print("- Database files are ~33% larger for k>32 (16 bytes vs 12 bytes per entry)")
        print("- All standard features work with large k-mers: counting, querying, canonical mode")
        print("- Python API provides the same interface for all k sizes")

        # Ask about cleanup
        try:
            response = input("\nRemove example database files? (y/N): ").strip().lower()
            if response in ['y', 'yes']:
                cleanup()
            else:
                print("Example files preserved for inspection")
        except KeyboardInterrupt:
            print("\nExample files preserved")

    except Exception as e:
        print(f"\nError running examples: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()