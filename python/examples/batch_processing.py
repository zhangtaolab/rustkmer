#!/usr/bin/env python3
"""
Example: Batch Processing with rustkmer

This example demonstrates efficient bulk querying capabilities of the rustkmer Python API:
- Parallel batch queries with configurable workers
- Progress tracking for large batches
- Mixed valid/invalid k-mer handling
- Performance comparison between single and batch queries
- Memory-efficient chunked processing

It showcases how to process large numbers of k-mers efficiently using parallel processing.
"""

import sys
import time
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from typing import List, Dict, Tuple

# Add rustkmer to path for development
sys.path.insert(0, str(Path(__file__).parent.parent))

from rustkmer import Database
from rustkmer.query import QueryResult


def print_header(title):
    """Print a formatted header."""
    print(f"\n{'='*70}")
    print(f" {title}")
    print(f"{'='*70}")


def print_section(title):
    """Print a formatted section header."""
    print(f"\n--- {title} ---")


def generate_test_kmers(kmer_size: int, count: int) -> List[str]:
    """Generate test k-mers for batch processing."""
    import random

    # Define nucleotides
    nucleotides = ['A', 'T', 'C', 'G']

    # Generate random k-mers
    kmers = []
    for _ in range(count):
        kmer = ''.join(random.choice(nucleotides) for _ in range(kmer_size))
        kmers.append(kmer)

    # Add some specific test cases
    test_cases = [
        'A' * kmer_size,  # All A's
        'T' * kmer_size,  # All T's
        'C' * kmer_size,  # All C's
        'G' * kmer_size,  # All G's
    ]
    kmers.extend(test_cases)

    # Add some invalid k-mers for testing
    invalid_cases = [
        'X' * kmer_size,  # Invalid character
        'ATCG',          # Wrong length
        '',              # Empty string
    ]
    kmers.extend(invalid_cases)

    return kmers


def demo_basic_batch_query():
    """Demonstrate basic batch querying."""
    print_header("Basic Batch Query Demo")

    test_data_dir = Path(__file__).parent.parent / "tests" / "test_data"
    db_path = test_data_dir / "small_test.rkdb"

    if not db_path.exists():
        print(f"❌ Test database not found: {db_path}")
        return

    print(f"Using database: {db_path.name}")

    # Generate test k-mers
    kmer_size = 7  # Known size for test database
    test_kmers = generate_test_kmers(kmer_size, 20)

    print_section("Batch Query Results")
    print(f"Generated {len(test_kmers)} test k-mers")

    with Database(str(db_path)) as db:
        # Perform batch query
        results = db.query_batch(test_kmers, max_workers=4)

        print(f"\nBatch query completed with {len(results)} results")

        # Display results
        print(f"{'K-mer':<10} {'Count':<8} {'Canonical':<10} {'Status'}")
        print("-" * 50)

        for kmer in test_kmers[:10]:  # Show first 10
            if kmer in results:
                result = results[kmer]
                status = "✓ Found" if result.count > 0 else "Not found"
                print(f"{kmer:<10} {result.count:<8} {result.canonical:<10} {status}")
            else:
                print(f"{kmer:<10} {'N/A':<8} {'N/A':<10} ❌ Missing from results")

        if len(test_kmers) > 10:
            print(f"... and {len(test_kmers) - 10} more k-mers")


def demo_parallel_performance():
    """Compare performance of different worker counts."""
    print_header("Parallel Performance Comparison")

    test_data_dir = Path(__file__).parent.parent / "tests" / "test_data"
    db_path = test_data_dir / "medium_test.rkdb"

    if not db_path.exists():
        print(f"❌ Test database not found: {db_path}")
        return

    # Generate larger batch for meaningful comparison
    kmer_size = 7
    test_kmers = generate_test_kmers(kmer_size, 100)

    with Database(str(db_path)) as db:
        worker_counts = [1, 2, 4, 8]
        results = {}

        print_section("Performance Comparison")
        print(f"Processing {len(test_kmers)} k-mers with different worker counts")
        print(f"{'Workers':<8} {'Time (s)':<10} {'K-mers/s':<12} {'Results':<8}")
        print("-" * 45)

        for workers in worker_counts:
            start_time = time.time()
            batch_results = db.query_batch(test_kmers, max_workers=workers)
            elapsed = time.time() - start_time

            kmer_per_sec = len(test_kmers) / elapsed if elapsed > 0 else float('inf')

            results[workers] = {
                'time': elapsed,
                'kmer_per_sec': kmer_per_sec,
                'result_count': len(batch_results)
            }

            print(f"{workers:<8} {elapsed:<10.3f} {kmer_per_sec:<12.1f} {len(batch_results):<8}")

        # Find optimal worker count
        best_workers = min(results.keys(), key=lambda w: results[w]['time'])
        print(f"\n✓ Optimal worker count: {best_workers} ({results[best_workers]['time']:.3f}s)")


def demo_progress_tracking():
    """Demonstrate progress tracking for large batches."""
    print_header("Progress Tracking for Large Batches")

    test_data_dir = Path(__file__).parent.parent / "tests" / "test_data"
    db_path = test_data_dir / "large_test.rkdb"

    if not db_path.exists():
        print(f"❌ Test database not found: {db_path}")
        return

    # Generate a large batch
    kmer_size = 7
    batch_size = 500
    test_kmers = generate_test_kmers(kmer_size, batch_size)

    print(f"Processing batch of {len(test_kmers)} k-mers...")

    with Database(str(db_path)) as db:
        # Method 1: Simple progress indication
        print_section("Method 1: Simple Progress")

        start_time = time.time()
        chunk_size = 50
        processed = 0

        for i in range(0, len(test_kmers), chunk_size):
            chunk = test_kmers[i:i+chunk_size]
            chunk_results = db.query_batch(chunk, max_workers=4)
            processed += len(chunk)

            elapsed = time.time() - start_time
            remaining = (len(test_kmers) - processed) * elapsed / processed if processed > 0 else 0

            # Simple progress bar
            progress = processed / len(test_kmers)
            bar_length = 40
            filled = int(bar_length * progress)
            bar = '█' * filled + '░' * (bar_length - filled)

            print(f"\rProgress: |{bar}| {processed}/{len(test_kmers)} "
                  f"({progress*100:.1f}%) ETA: {remaining:.1f}s", end='', flush=True)

        print("\n✓ Batch processing completed!")


def demo_chunked_processing():
    """Demonstrate memory-efficient chunked processing for very large datasets."""
    print_header("Memory-Efficient Chunked Processing")

    test_data_dir = Path(__file__).parent.parent / "tests" / "test_data"
    db_path = test_data_dir / "large_test.rkdb"

    if not db_path.exists():
        print(f"❌ Test database not found: {db_path}")
        return

    # Simulate a very large dataset
    kmer_size = 7
    total_kmers = 2000
    chunk_size = 200

    print(f"Simulating processing of {total_kmers} k-mers in chunks of {chunk_size}")
    print_section("Chunked Processing Results")

    with Database(str(db_path)) as db:
        all_results = {}
        chunks_processed = 0

        for offset in range(0, total_kmers, chunk_size):
            # Generate chunk
            chunk_end = min(offset + chunk_size, total_kmers)
            chunk = generate_test_kmers(kmer_size, chunk_end - offset)

            # Process chunk
            chunk_start_time = time.time()
            chunk_results = db.query_batch(chunk, max_workers=4)
            chunk_time = time.time() - chunk_start_time

            # Merge results
            all_results.update(chunk_results)
            chunks_processed += 1

            print(f"Chunk {chunks_processed}: {len(chunk)} k-mers in {chunk_time:.3f}s, "
                  f"{len(chunk_results)} results")

        print_section("Summary")
        print(f"Total chunks processed: {chunks_processed}")
        print(f"Total k-mers processed: {total_kmers}")
        print(f"Total results: {len(all_results)}")

        # Analyze results
        found_count = sum(1 for r in all_results.values() if r.count > 0)
        print(f"K-mers found in database: {found_count}")
        print(f"Hit rate: {found_count/len(all_results)*100:.1f}%")


def demo_mixed_validation():
    """Demonstrate handling mixed valid/invalid k-mers in batches."""
    print_header("Mixed Validation in Batch Processing")

    test_data_dir = Path(__file__).parent.parent / "tests" / "test_data"
    db_path = test_data_dir / "small_test.rkdb"

    if not db_path.exists():
        print(f"❌ Test database not found: {db_path}")
        return

    # Create mixed batch with valid and invalid k-mers
    mixed_kmers = [
        # Valid 7-mers
        "AAAAAAA", "TTTTTTT", "ATCGATC", "GCCGCGG", "GCTAGCT",
        # Invalid k-mers (various issues)
        "ATCGX",      # Invalid character
        "ATCGATCG",   # Wrong length (8)
        "ATCG",       # Wrong length (4)
        "NNNNNNN",    # Invalid characters
        "toolongkkkkkkkkkkkkkkk",  # Too long
        "",           # Empty string
        "AtCgAtC",    # Mixed case (will work but good to test)
        "1234567",    # Numbers
        "AT CGA",     # Space in middle
    ]

    print_section("Mixed Batch Processing")
    print(f"Processing {len(mixed_kmers)} k-mers (mix of valid and invalid)")

    with Database(str(db_path)) as db:
        # Process with lenient validation (batch processing always uses lenient validation)
        print("\n1. Batch processing (always uses lenient validation):")
        lenient_results = db.query_batch(mixed_kmers, max_workers=2)

        print(f"   Results: {len(lenient_results)} out of {len(mixed_kmers)} k-mers processed")
        print(f"   {'K-mer':<15} {'Valid':<6} {'Count':<8} {'Canonical'}")
        print("   " + "-" * 50)

        for kmer in mixed_kmers:
            if kmer in lenient_results:
                result = lenient_results[kmer]
                is_valid = len(kmer) == 7 and all(c in 'ATCG' for c in kmer.upper())
                print(f"   {kmer:<15} {'Yes' if is_valid else 'No':<6} "
                      f"{result.count:<8} {result.canonical}")

    # Note: We can't easily test strict validation in batch mode because it would raise
    # an exception and stop processing. In a real application, you would validate
    # beforehand or use try/except blocks around each query.
    print("\n2. Strict validation:")
    print("   Note: Strict validation in batch mode requires pre-validation")
    print("   or handling exceptions for individual k-mers")

    # Demonstrate pre-validation approach
    print("\n3. Pre-validation approach for strict validation:")
    from rustkmer.utils import validate_kmer

    valid_kmers = []
    invalid_kmers = []

    for kmer in mixed_kmers:
        try:
            validated = validate_kmer(kmer, kmer_size=7, strict=True)
            if validated:
                valid_kmers.append(kmer)
            else:
                invalid_kmers.append(kmer)
        except:
            invalid_kmers.append(kmer)

    print(f"   Valid k-mers: {len(valid_kmers)}")
    print(f"   Invalid k-mers: {len(invalid_kmers)}")

    if valid_kmers:
        with Database(str(db_path)) as db:
            valid_results = db.query_batch(valid_kmers, max_workers=2)
            print(f"   ✓ Processed {len(valid_results)} valid k-mers successfully")


def main():
    """Run all batch processing demonstrations."""
    print("RustKmer Python API - Batch Processing Examples")
    print("This example demonstrates efficient bulk querying capabilities.")

    # Run all demonstrations
    demo_basic_batch_query()
    demo_parallel_performance()
    demo_progress_tracking()
    demo_chunked_processing()
    demo_mixed_validation()

    print_header("Best Practices Summary")
    print("✓ Use batch queries for processing multiple k-mers efficiently")
    print("✓ Experiment with worker counts to find optimal performance")
    print("✓ Implement progress tracking for large batches")
    print("✓ Use chunked processing for very large datasets")
    print("✓ Handle mixed valid/invalid k-mers gracefully")
    print("\nPerformance Tips:")
    print("- More workers = faster but higher memory usage")
    print("- Typical optimal worker count: 2-8 depending on your CPU")
    print("- Chunk size of 100-1000 works well for most datasets")
    print("- Always validate input k-mers for robust applications")


if __name__ == "__main__":
    main()