#!/usr/bin/env python3
"""
RustKmer Advanced Features Example

This example demonstrates advanced RustKmer features:
- Fuzzy queries with wildcards and mismatches
- Database merging operations
- Progress reporting for long operations
- Memory-mapped database access
- Batch query optimization
- Error handling patterns

Author: RustKmer Team
"""

import os
import sys
import time
import tempfile
from concurrent.futures import ThreadPoolExecutor
from rustkmer import KmerCounter, Database, FuzzyQuery
from rustkmer import SequenceError, DatabaseError, FuzzyQueryError

def create_test_databases():
    """Create test databases for demonstration"""
    print("Creating test databases...")

    # Test sequences with variations
    sequences = [
        "ATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATC",  # Original
        "ATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATT",  # 1 mismatch
        "ATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATG",  # 1 mismatch
        "ATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGACC",  # 1 mismatch
        "GCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAGCT",  # Completely different
        "CCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCC",  # All C
    ]

    db_paths = []

    # Create multiple databases
    for i, seq_set in enumerate([sequences[:3], sequences[3:]], 1):
        counter = KmerCounter(k=21, canonical=True)

        print(f"  Database {i}: Counting {len(seq_set)} sequences...")
        for seq in seq_set:
            counter.count_string(seq)

        db_path = f"test_db_{i}.rkdb"
        counter.save_to_database(db_path, canonical=True)
        db_paths.append(db_path)

    return db_paths

def demonstrate_fuzzy_queries():
    """Demonstrate fuzzy query capabilities"""
    print("\n" + "=" * 60)
    print("1. Fuzzy Query with Wildcards and Mismatches")
    print("=" * 60)

    # Create test database
    counter = KmerCounter(k=21, canonical=True)
    test_sequence = "ATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATC"
    counter.count_string(test_sequence)

    db_path = "fuzzy_test.rkdb"
    counter.save_to_database(db_path)

    # Initialize fuzzy query
    fq = FuzzyQuery()
    fq.load(db_path)

    query_sequence = "ATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATC"

    # Test 1: Exact match
    print("\n--- Exact Match ---")
    results = fq.query(query_sequence, max_mismatches=0)
    print(f"Query: {query_sequence[:10]}...")
    print(f"Matches found: {len(results)}")
    for match, count in results[:5]:  # Show first 5
        print(f"  {match[:10]}...: {count}")

    # Test 2: Wildcard search (N = any base)
    print("\n--- Wildcard Search ---")
    patterns = [
        "ATCGATNNNNATCGATCG",  # N in middle
        "NNNNATCGATCGATCGAT",  # N at start
        "ATCGATCGATCGATNNNN",  # N at end
        "ATNATNATNATNATNATNATN",  # Alternating
    ]

    for pattern in patterns:
        results = fq.query(pattern)
        print(f"Pattern '{pattern}': {len(results)} matches")

    # Test 3: Mismatch tolerance
    print("\n--- Mismatch Tolerance ---")
    max_mismatches_list = [1, 2, 3]

    for max_mismatches in max_mismatches_list:
        results = fq.query(query_sequence, max_mismatches=max_mismatches)
        print(f"Max mismatches {max_mismatches}: {len(results)} matches")

        # Group by actual mismatches
        mismatch_groups = {}
        for match, count in results:
            mismatches = sum(1 for a, b in zip(query_sequence, match) if a != b)
            mismatch_groups.setdefault(mismatches, []).append((match, count))

        for mismatches, matches in sorted(mismatch_groups.items()):
            print(f"  {mismatches} mismatches: {len(matches)} sequences")

    # Clean up
    os.remove(db_path)

def demonstrate_database_merging():
    """Demonstrate database merging operations"""
    print("\n" + "=" * 60)
    print("2. Database Merging")
    print("=" * 60)

    # Create test databases
    db_paths = create_test_databases()

    # Load first database and merge others
    print("\n--- Merging Databases ---")
    merged_db = Database()
    merged_db.load(db_paths[0])

    # Get initial statistics
    initial_stats = merged_db.get_stats()
    print(f"Initial database:")
    print(f"  Total k-mers: {initial_stats['total_kmers']:,}")
    print(f"  Unique k-mers: {initial_stats['unique_kmers']:,}")

    # Merge with second database
    print(f"\nMerging with {db_paths[1]}...")
    merged_db.merge_with(db_paths[1])

    # Get final statistics
    final_stats = merged_db.get_stats()
    print(f"\nMerged database:")
    print(f"  Total k-mers: {final_stats['total_kmers']:,}")
    print(f"  Unique k-mers: {final_stats['unique_kmers']:,}")
    print(f"  Increase in unique k-mers: {final_stats['unique_kmers'] - initial_stats['unique_kmers']:,}")

    # Save merged database
    merged_path = "merged_databases.rkdb"
    merged_db.save(merged_path)
    print(f"\nMerged database saved to: {merged_path}")

    # Clean up
    for path in db_paths + [merged_path]:
        if os.path.exists(path):
            os.remove(path)

def demonstrate_progress_reporting():
    """Demonstrate progress reporting for long operations"""
    print("\n" + "=" * 60)
    print("3. Progress Reporting")
    print("=" * 60)

    # Create a large synthetic sequence
    print("Creating large synthetic sequence...")
    base_seq = "ATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATC"
    large_sequence = base_seq * 10000  # ~330k bp

    # Progress callback function
    def progress_callback(progress):
        """Progress callback for counting operations"""
        bar_length = 50
        filled = int(bar_length * progress)
        bar = '█' * filled + '-' * (bar_length - filled)
        print(f'\rProgress: |{bar}| {progress*100:.1f}%', end='', flush=True)

    print("\nCounting k-mers with progress reporting...")
    counter = KmerCounter(k=31, canonical=True)

    # Count with progress callback
    start_time = time.time()
    counter.count_string(large_sequence, progress_callback=progress_callback)
    elapsed = time.time() - start_time

    print(f"\n\nCounting completed in {elapsed:.2f} seconds")
    print(f"Total k-mers: {counter.get_total_count():,}")
    print(f"Unique k-mers: {counter.get_unique_count():,}")

def demonstrate_memory_mapped_access():
    """Demonstrate memory-mapped database access"""
    print("\n" + "=" * 60)
    print("4. Memory-Mapped Database Access")
    print("=" * 60)

    # Create a large database
    print("Creating large test database...")
    counter = KmerCounter(k=21, canonical=True)

    # Add many sequences
    for i in range(1000):
        seq = f"{'ATCG' * 5}{'{i:04d}{'GCTA' * 5}"
        counter.count_string(seq)

    db_path = "large_test_db.rkdb"
    counter.save_to_database(db_path)

    size_mb = os.path.getsize(db_path) / 1024 / 1024
    print(f"Database created: {size_mb:.2f} MB")

    # Test without memory mapping
    print("\n--- Loading without memory mapping ---")
    start_time = time.time()
    db1 = Database()
    db1.load(db_path, memory_mapped=False)
    load_time1 = time.time() - start_time
    print(f"Load time: {load_time1:.3f} seconds")

    # Test query performance
    test_queries = ["ATCGATCGATCGATCGATCGATC", "GCTAGCTAGCTAGCTAGCTAGCT"] * 100

    start_time = time.time()
    for query in test_queries:
        db1.query(query)
    query_time1 = time.time() - start_time
    print(f"Query time ({len(test_queries)} queries): {query_time1:.3f} seconds")

    # Test with memory mapping
    print("\n--- Loading with memory mapping ---")
    start_time = time.time()
    db2 = Database()
    db2.load(db_path, memory_mapped=True)
    load_time2 = time.time() - start_time
    print(f"Load time: {load_time2:.3f} seconds")

    start_time = time.time()
    for query in test_queries:
        db2.query(query)
    query_time2 = time.time() - start_time
    print(f"Query time ({len(test_queries)} queries): {query_time2:.3f} seconds")

    # Compare performance
    print(f"\nPerformance comparison:")
    print(f"  Load time reduction: {load_time1/load_time2:.2f}x faster with memory mapping")
    print(f"  Query performance: {query_time2/query_time1:.2f}x {'slower' if query_time2 > query_time1 else 'faster'} with memory mapping")

    # Clean up
    os.remove(db_path)

def demonstrate_batch_queries():
    """Demonstrate batch query optimization"""
    print("\n" + "=" * 60)
    print("5. Batch Query Optimization")
    print("=" * 60)

    # Create database
    counter = KmerCounter(k=21, canonical=True)
    test_sequences = [
        "ATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATC",
        "GCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAGC",
        "CCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCC",
    ]

    for seq in test_sequences:
        counter.count_string(seq)

    db_path = "batch_test.rkdb"
    counter.save_to_database(db_path)
    db = Database()
    db.load(db_path)

    # Generate many query sequences
    num_queries = 1000
    queries = []
    for i in range(num_queries):
        # Mix of real and random sequences
        if i % 10 == 0 and i // 10 < len(test_sequences):
            queries.append(test_sequences[i // 10][:21])
        else:
            queries.append(f"{'ATCG' * 5}{i:04d}{'GCTA' * 5}"[:21])

    # Test individual queries
    print(f"\nTesting {num_queries} individual queries...")
    start_time = time.time()
    individual_results = []
    for query in queries:
        individual_results.append(db.query(query))
    individual_time = time.time() - start_time

    print(f"Individual queries: {individual_time:.3f} seconds")
    print(f"Average per query: {individual_time/num_queries*1000:.2f} ms")

    # Test batch queries
    print(f"\nTesting {num_queries} batch queries...")
    start_time = time.time()
    batch_results = db.query_multiple(queries)
    batch_time = time.time() - start_time

    print(f"Batch queries: {batch_time:.3f} seconds")
    print(f"Average per query: {batch_time/num_queries*1000:.2f} ms")
    print(f"Speedup: {individual_time/batch_time:.2f}x faster")

    # Verify results match
    assert individual_results == batch_results, "Results don't match!"
    print("✓ Results verified to be identical")

    # Clean up
    os.remove(db_path)

def demonstrate_parallel_processing():
    """Demonstrate parallel processing capabilities"""
    print("\n" + "=" * 60)
    print("6. Parallel Processing")
    print("=" * 60)

    # Create test files
    num_files = 10
    sequences_per_file = 100

    print(f"Creating {num_files} test files...")
    file_paths = []

    for i in range(num_files):
        file_path = f"parallel_test_{i}.fa"
        with open(file_path, "w") as f:
            for j in range(sequences_per_file):
                seq_id = f">seq_{i}_{j}\n"
                seq = f"{'ATCG' * 5}{i:03d}{j:03d}{'GCTA' * 5}\n"
                f.write(seq_id + seq)
        file_paths.append(file_path)

    def process_file(filepath, k=21):
        """Process a single file"""
        counter = KmerCounter(k=k, canonical=True, threads=2)
        counter.count_file(filepath)
        return counter.get_total_count()

    # Sequential processing
    print(f"\nSequential processing...")
    start_time = time.time()
    sequential_results = []
    for file_path in file_paths:
        result = process_file(file_path)
        sequential_results.append(result)
    sequential_time = time.time() - start_time

    print(f"Sequential time: {sequential_time:.2f} seconds")
    print(f"Total k-mers: {sum(sequential_results):,}")

    # Parallel processing
    print(f"\nParallel processing (4 threads)...")
    start_time = time.time()
    with ThreadPoolExecutor(max_workers=4) as executor:
        parallel_results = list(executor.map(process_file, file_paths))
    parallel_time = time.time() - start_time

    print(f"Parallel time: {parallel_time:.2f} seconds")
    print(f"Total k-mers: {sum(parallel_results):,}")
    print(f"Speedup: {sequential_time/parallel_time:.2f}x")

    # Verify results
    assert sequential_results == parallel_results, "Results don't match!"
    print("✓ Results verified to be identical")

    # Clean up
    for file_path in file_paths:
        if os.path.exists(file_path):
            os.remove(file_path)

def demonstrate_error_handling():
    """Demonstrate comprehensive error handling"""
    print("\n" + "=" * 60)
    print("7. Error Handling Patterns")
    print("=" * 60)

    # Test various error conditions

    # 1. Invalid k-mer size
    print("\n--- Testing Invalid k-mer Size ---")
    try:
        counter = KmerCounter(k=200)  # Too large
        print("ERROR: Should have failed!")
    except Exception as e:
        print(f"✓ Caught expected error: {type(e).__name__}: {e}")

    # 2. Invalid file path
    print("\n--- Testing Invalid File Path ---")
    try:
        counter = KmerCounter(k=21)
        counter.count_file("nonexistent_file.fa")
        print("ERROR: Should have failed!")
    except SequenceError as e:
        print(f"✓ Caught SequenceError: {e}")
    except Exception as e:
        print(f"✓ Caught error: {type(e).__name__}: {e}")

    # 3. Database operations
    print("\n--- Testing Database Operations ---")

    # Create a test database
    counter = KmerCounter(k=21)
    counter.count_string("ATCGATCGATCGATCGATCGATC")
    db_path = "error_test.rkdb"
    counter.save_to_database(db_path)

    # Try to load with wrong path
    try:
        db = Database()
        db.load("wrong_path.rkdb")
        print("ERROR: Should have failed!")
    except DatabaseError as e:
        print(f"✓ Caught DatabaseError: {e}")

    # Clean up
    if os.path.exists(db_path):
        os.remove(db_path)

    # 4. Fuzzy query errors
    print("\n--- Testing Fuzzy Query Errors ---")
    try:
        fq = FuzzyQuery()
        fq.load("nonexistent.rkdb")
        results = fq.query("ATCG")
        print(f"Unexpected success: {len(results)} results")
    except FuzzyQueryError as e:
        print(f"✓ Caught FuzzyQueryError: {e}")
    except Exception as e:
        print(f"✓ Caught error: {type(e).__name__}: {e}")

def main():
    """Main function to run all advanced examples"""
    print("\nRustKmer Advanced Features Example")
    print("==================================\n")

    try:
        # Run all demonstrations
        demonstrate_fuzzy_queries()
        demonstrate_database_merging()
        demonstrate_progress_reporting()
        demonstrate_memory_mapped_access()
        demonstrate_batch_queries()
        demonstrate_parallel_processing()
        demonstrate_error_handling()

        print("\n" + "=" * 60)
        print("All advanced examples completed successfully!")
        print("=" * 60)

    except Exception as e:
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()