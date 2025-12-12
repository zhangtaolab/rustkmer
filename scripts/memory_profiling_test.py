#!/usr/bin/env python3
"""
Memory profiling tests for RustKmer Python API.

This script runs various operations and profiles their memory usage
to detect memory leaks and excessive memory consumption.
"""

import gc
import os
import psutil
import tempfile
import time
import tracemalloc
from memory_profiler import profile
import matplotlib.pyplot as plt


def get_memory_usage():
    """Get current memory usage in MB."""
    process = psutil.Process()
    return process.memory_info().rss / 1024 / 1024


def plot_memory_usage(memory_samples, operation_name):
    """Plot memory usage over time."""
    plt.figure(figsize=(10, 6))
    plt.plot(memory_samples, label='Memory Usage (MB)')
    plt.xlabel('Time (samples)')
    plt.ylabel('Memory Usage (MB)')
    plt.title(f'Memory Usage During {operation_name}')
    plt.grid(True)
    plt.legend()

    output_file = f"memory_profile_{operation_name.replace(' ', '_').lower()}.png"
    plt.savefig(output_file)
    plt.close()
    print(f"Memory plot saved to: {output_file}")


def test_kmer_counter_memory():
    """Test memory usage of KmerCounter operations."""
    print("\n=== Testing KmerCounter Memory Usage ===")

    memory_samples = []
    tracemalloc.start()

    # Initial memory
    initial_memory = get_memory_usage()
    memory_samples.append(initial_memory)

    try:
        import rustkmer
    except ImportError:
        print("RustKmer not available, skipping memory test")
        return

    # Create multiple counters
    counters = []
    for i in range(10):
        counter = rustkmer.KmerCounter(k=31)
        counters.append(counter)
        memory_samples.append(get_memory_usage())

    # Count sequences
    test_seq = "ATCGATCGATCGATCGATCGATCGATCGATCGATC" * 1000
    for counter in counters:
        counter.count_string(test_seq)
        memory_samples.append(get_memory_usage())

    # Delete counters
    del counters
    gc.collect()
    memory_samples.append(get_memory_usage())

    # Final memory
    final_memory = get_memory_usage()
    memory_samples.append(final_memory)

    # Memory statistics
    current, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()

    print(f"Initial memory: {initial_memory:.1f} MB")
    print(f"Final memory: {final_memory:.1f} MB")
    print(f"Memory increase: {final_memory - initial_memory:.1f} MB")
    print(f"Peak memory (tracemalloc): {peak / 1024 / 1024:.1f} MB")

    # Plot memory usage
    plot_memory_usage(memory_samples, "KmerCounter Operations")


def test_database_loading_memory():
    """Test memory usage of database operations."""
    print("\n=== Testing Database Loading Memory Usage ===")

    memory_samples = []
    tracemalloc.start()

    try:
        import rustkmer
    except ImportError:
        print("RustKmer not available, skipping memory test")
        return

    initial_memory = get_memory_usage()
    memory_samples.append(initial_memory)

    # Create test database
    counter = rustkmer.KmerCounter(k=21)
    test_seq = "ATCGATCGATCGATCGATCGATC" * 10000
    counter.count_string(test_seq)

    with tempfile.NamedTemporaryFile(suffix='.rkdb', delete=False) as f:
        db_path = f.name

    counter.save_to_database(db_path)
    memory_samples.append(get_memory_usage())

    # Load database multiple times
    databases = []
    for i in range(5):
        db = rustkmer.Database()
        db.load(db_path)
        databases.append(db)
        memory_samples.append(get_memory_usage())

    # Query databases
    for db in databases:
        result = db.query("ATCGATCGATCGATCGATCGATC")
        memory_samples.append(get_memory_usage())

    # Clean up
    del databases
    os.unlink(db_path)
    gc.collect()
    memory_samples.append(get_memory_usage())

    final_memory = get_memory_usage()
    memory_samples.append(final_memory)

    current, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()

    print(f"Initial memory: {initial_memory:.1f} MB")
    print(f"Final memory: {final_memory:.1f} MB")
    print(f"Memory increase: {final_memory - initial_memory:.1f} MB")
    print(f"Peak memory (tracemalloc): {peak / 1024 / 1024:.1f} MB")

    plot_memory_usage(memory_samples, "Database Loading")


@profile
def test_fuzzy_query_memory():
    """Profile memory usage of fuzzy queries."""
    print("\n=== Testing Fuzzy Query Memory Usage ===")

    try:
        import rustkmer
    except ImportError:
        print("RustKmer not available, skipping memory test")
        return

    # Create test database
    counter = rustkmer.KmerCounter(k=7)
    test_seq = "ATCGATCGATCGATCGATCGATC" * 1000
    counter.count_string(test_seq)

    with tempfile.NamedTemporaryFile(suffix='.rkdb', delete=False) as f:
        db_path = f.name

    counter.save_to_database(db_path)

    # Load database and create fuzzy query
    db = rustkmer.Database()
    db.load(db_path)
    fuzzy = rustkmer.FuzzyQuery(db)

    # Perform many fuzzy queries
    queries = [
        "ATCGATCG",
        "GCTAGCTA",
        "TTTTTTTT",
        "CCCCCCCC",
        "GGGGGGGG"
    ] * 100

    for query in queries:
        results = fuzzy.query(query, max_distance=2)
        # Force memory allocation
        _ = list(results)

    # Clean up
    os.unlink(db_path)
    gc.collect()


def test_large_sequence_memory():
    """Test memory usage with large sequences."""
    print("\n=== Testing Large Sequence Memory Usage ===")

    memory_samples = []
    tracemalloc.start()

    try:
        import rustkmer
    except ImportError:
        print("RustKmer not available, skipping memory test")
        return

    initial_memory = get_memory_usage()
    memory_samples.append(initial_memory)

    # Test with increasing sequence sizes
    sizes = [1000, 10000, 100000, 1000000, 10000000]

    for size in sizes:
        seq = "ATCG" * (size // 4)
        print(f"\nTesting sequence of length {len(seq)}...")

        before_memory = get_memory_usage()

        counter = rustkmer.KmerCounter(k=31)
        counter.count_string(seq)

        after_memory = get_memory_usage()

        memory_samples.append(after_memory)
        print(f"  Memory usage: {after_memory - before_memory:.1f} MB increase")

        del counter
        gc.collect()

    final_memory = get_memory_usage()
    memory_samples.append(final_memory)

    current, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()

    print(f"\nFinal memory: {final_memory:.1f} MB")
    print(f"Total increase: {final_memory - initial_memory:.1f} MB")
    print(f"Peak memory (tracemalloc): {peak / 1024 / 1024:.1f} MB")

    plot_memory_usage(memory_samples, "Large Sequence Processing")


def test_concurrent_memory():
    """Test memory usage under concurrent operations."""
    print("\n=== Testing Concurrent Operations Memory Usage ===")

    import threading
    import queue

    memory_samples = []
    tracemalloc.start()

    try:
        import rustkmer
    except ImportError:
        print("RustKmer not available, skipping memory test")
        return

    initial_memory = get_memory_usage()
    memory_samples.append(initial_memory)

    # Create shared test database
    counter = rustkmer.KmerCounter(k=7)
    test_seq = "ATCGATCGATCGATCGATCGATC" * 100
    counter.count_string(test_seq)

    with tempfile.NamedTemporaryFile(suffix='.rkdb', delete=False) as f:
        db_path = f.name

    counter.save_to_database(db_path)

    # Worker function
    def worker(q, thread_id):
        try:
            for _ in range(10):
                db = rustkmer.Database()
                db.load(db_path)
                result = db.query("ATCGATCG")
                q.put((thread_id, "success", result))
        except Exception as e:
            q.put((thread_id, "error", str(e)))

    # Run concurrent operations
    threads = []
    result_queue = queue.Queue()

    for i in range(10):
        t = threading.Thread(target=worker, args=(result_queue, i))
        threads.append(t)
        t.start()

    # Monitor memory while threads run
    for _ in range(20):
        memory_samples.append(get_memory_usage())
        time.sleep(0.1)

    # Wait for threads to complete
    for t in threads:
        t.join()

    # Collect results
    results = []
    while not result_queue.empty():
        results.append(result_queue.get())

    memory_samples.append(get_memory_usage())

    # Clean up
    os.unlink(db_path)
    gc.collect()

    final_memory = get_memory_usage()
    memory_samples.append(final_memory)

    current, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()

    print(f"Threads completed: {len(results)}")
    print(f"Initial memory: {initial_memory:.1f} MB")
    print(f"Final memory: {final_memory:.1f} MB")
    print(f"Peak memory (tracemalloc): {peak / 1024 / 1024:.1f} MB")

    plot_memory_usage(memory_samples, "Concurrent Operations")


def main():
    """Run all memory profiling tests."""
    print("Starting RustKmer Memory Profiling Tests")
    print("=" * 50)

    # Run all tests
    test_kmer_counter_memory()
    test_database_loading_memory()
    test_fuzzy_query_memory()
    test_large_sequence_memory()
    test_concurrent_memory()

    print("\n" + "=" * 50)
    print("Memory profiling tests completed!")
    print("\nMemory profile reports have been saved:")
    print("  - memory_profile_kmer_counter_operations.png")
    print("  - memory_profile_database_loading.png")
    print("  - memory_profile_large_sequence_processing.png")
    print("  - memory_profile_concurrent_operations.png")


if __name__ == "__main__":
    main()