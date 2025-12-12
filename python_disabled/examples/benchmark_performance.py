#!/usr/bin/env python3
"""
RustKmer Performance Benchmark Script

This script benchmarks various aspects of the RustKmer Python API
and generates detailed performance reports.
"""

import sys
import os
import time
import json
import argparse
import tempfile
import statistics
from pathlib import Path
from typing import List, Dict, Any, Tuple
import multiprocessing as mp

# Import RustKmer
try:
    from rustkmer import (
        KmerCounter, Database, DatabaseExporter, DatabaseMerger,
        FuzzyQueryEngine, FuzzyQueryConfig
    )
    from rustkmer.performance import (
        DatabaseCache, BatchProcessor, ParallelProcessor,
        performance_monitor, timer, memory_monitor
    )
    from rustkmer.stats import StatisticsCalculator
except ImportError as e:
    print("Error: Could not import rustkmer module.")
    print("Please install with: cd python && maturin develop --release")
    sys.exit(1)

# Import system monitoring
try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False
    print("Warning: psutil not available. Memory monitoring disabled.")


class BenchmarkSuite:
    """Comprehensive benchmark suite for RustKmer."""

    def __init__(self, output_dir: str):
        """Initialize benchmark suite."""
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
        self.results: Dict[str, Any] = {}

    def run_all_benchmarks(self) -> None:
        """Run all benchmark tests."""
        print("=" * 60)
        print("RustKmer Performance Benchmark Suite")
        print("=" * 60)

        # System information
        self._collect_system_info()

        # Benchmarks
        self._benchmark_counting()
        self._benchmark_querying()
        self._benchmark_fuzzy_search()
        self._benchmark_merging()
        self._benchmark_exporting()
        self._benchmark_batch_processing()
        self._benchmark_parallel_processing()
        self._benchmark_memory_usage()
        self._benchmark_caching()

        # Generate report
        self._generate_report()

    def _collect_system_info(self) -> None:
        """Collect system information."""
        info = {
            'cpu_count': mp.cpu_count(),
            'python_version': sys.version,
            'platform': sys.platform
        }

        if PSUTIL_AVAILABLE:
            memory = psutil.virtual_memory()
            info['total_memory_gb'] = memory.total / 1024 / 1024 / 1024
            info['available_memory_gb'] = memory.available / 1024 / 1024 / 1024

        self.results['system_info'] = info

        print(f"\nSystem Information:")
        print(f"  CPU cores: {info['cpu_count']}")
        if 'total_memory_gb' in info:
            print(f"  Total RAM: {info['total_memory_gb']:.1f} GB")

    def _benchmark_counting(self) -> None:
        """Benchmark k-mer counting performance."""
        print("\nBenchmarking k-mer counting...")

        # Generate test data
        test_sizes = [1000, 5000, 10000, 50000]  # sequences
        k_sizes = [21, 31, 51]

        results = {}

        for size in test_sizes:
            print(f"  Dataset size: {size:,} sequences")
            size_results = {}

            # Create temporary FASTA file
            with tempfile.NamedTemporaryFile(mode='w', suffix='.fasta', delete=False) as f:
                for i in range(size):
                    seq = "ATCGATCGATCGATCG" * (10 + (i % 20))  # Variable length sequences
                    f.write(f">seq{i}\n{seq}\n")
                temp_file = f.name

            try:
                for k in k_sizes:
                    # Benchmark with different thread counts
                    thread_results = {}
                    for threads in [1, 2, 4, 8]:
                        if threads > mp.cpu_count():
                            continue

                        # Warm up
                        counter = KmerCounter(k=k, threads=threads)
                        counter.count_from_file(temp_file)

                        # Benchmark
                        times = []
                        for _ in range(3):  # Run multiple times
                            start = time.time()
                            counter = KmerCounter(k=k, threads=threads)
                            db = counter.count_from_file(temp_file)
                            times.append(time.time() - start)

                        thread_results[threads] = {
                            'mean_time': statistics.mean(times),
                            'std_dev': statistics.stdev(times) if len(times) > 1 else 0,
                            'kmer_count': db.total_kmers
                        }

                    size_results[f'k{k}'] = thread_results

                results[f'size_{size}'] = size_results

            finally:
                os.unlink(temp_file)

        self.results['counting'] = results

    def _benchmark_querying(self) -> None:
        """Benchmark database querying performance."""
        print("\nBenchmarking database querying...")

        # Create test database
        with tempfile.NamedTemporaryFile(mode='w', suffix='.fasta', delete=False) as f:
            for i in range(10000):
                seq = "ATCGATCGATCGATCG" * 25
                f.write(f">seq{i}\n{seq}\n")
            temp_file = f.name

        try:
            # Create database
            counter = KmerCounter(k=31, threads=8)
            db = counter.count_from_file(temp_file)

            # Benchmark different query sizes
            query_sizes = [1, 10, 100, 1000, 10000]
            results = {}

            for size in query_sizes:
                print(f"  Query size: {size:,} k-mers")

                # Generate test k-mers
                kmers = [f"ATCGATCG{i:08d}"[:31] for i in range(size)]

                # Benchmark individual queries vs batch
                individual_times = []
                batch_times = []

                # Individual queries
                for _ in range(3):
                    start = time.time()
                    for kmer in kmers[:min(100, size)]:  # Limit for time
                        db.query(kmer)
                    individual_times.append(time.time() - start)

                # Batch query
                for _ in range(3):
                    start = time.time()
                    db.query_multiple(kmers)
                    batch_times.append(time.time() - start)

                results[f'size_{size}'] = {
                    'individual_mean': statistics.mean(individual_times),
                    'batch_mean': statistics.mean(batch_times),
                    'speedup': statistics.mean(individual_times) / statistics.mean(batch_times)
                }

            self.results['querying'] = results

        finally:
            os.unlink(temp_file)

    def _benchmark_fuzzy_search(self) -> None:
        """Benchmark fuzzy search performance."""
        print("\nBenchmarking fuzzy search...")

        # Create test database
        with tempfile.NamedTemporaryFile(mode='w', suffix='.fasta', delete=False) as f:
            for i in range(5000):
                # Create sequences with patterns
                base = "ATCGATCGATCGATCG" * 20
                if i % 5 == 0:
                    seq = base[:400] + "A" + base[401:]  # Mutation
                else:
                    seq = base
                f.write(f">seq{i}\n{seq}\n")
            temp_file = f.name

        try:
            # Create database
            counter = KmerCounter(k=31, threads=8)
            db = counter.count_from_file(temp_file)

            # Configure fuzzy search
            distances = [1, 2, 3]
            max_results_options = [10, 50, 100]

            results = {}

            for distance in distances:
                distance_results = {}
                for max_results in max_results_options:
                    config = FuzzyQueryConfig(
                        max_distance=distance,
                        max_results=max_results
                    )
                    engine = FuzzyQueryEngine(config)
                    engine.attach_database(db)

                    # Test queries
                    queries = [
                        "ATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCG",
                        "ATCAATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCG",  # 1 mutation
                        "ATCCATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCG",  # 1 mutation
                    ]

                    times = []
                    total_matches = 0

                    for _ in range(5):
                        start = time.time()
                        for query in queries:
                            results_list = engine.query(query)
                            total_matches += len(results_list)
                        times.append(time.time() - start)

                    distance_results[f'max_{max_results}'] = {
                        'mean_time': statistics.mean(times),
                        'avg_matches_per_query': total_matches / (len(times) * len(queries))
                    }

                results[f'distance_{distance}'] = distance_results

            self.results['fuzzy_search'] = results

        finally:
            os.unlink(temp_file)

    def _benchmark_merging(self) -> None:
        """Benchmark database merging performance."""
        print("\nBenchmarking database merging...")

        # Create multiple databases
        db_files = []
        db_count = 5

        try:
            for i in range(db_count):
                with tempfile.NamedTemporaryFile(mode='w', suffix='.fasta', delete=False) as f:
                    for j in range(2000):
                        seq = "ATCGATCGATCGATCG" * (10 + i % 10)
                        f.write(f">seq{i}_{j}\n{seq}\n")
                    temp_file = f.name
                    db_file = temp_file.replace('.fasta', '.rkdb')

                # Create database
                counter = KmerCounter(k=31, threads=4)
                db = counter.count_from_file(temp_file)
                db.save(db_file)

                db_files.append(db_file)
                os.unlink(temp_file)

            # Load databases for merging
            databases = []
            for db_file in db_files:
                db = Database()
                db.load(db_file)
                databases.append(db)

            # Benchmark merging with different thread counts
            thread_counts = [1, 2, 4, 8]
            results = {}

            for threads in thread_counts:
                if threads > mp.cpu_count():
                    continue

                print(f"  Merging with {threads} threads")

                times = []
                for _ in range(3):
                    with tempfile.NamedTemporaryFile(suffix='.rkdb', delete=False) as f:
                        output_file = f.name

                    start = time.time()
                    merger = DatabaseMerger(threads=threads)
                    result = merger.merge_databases(databases, output_file)
                    times.append(time.time() - start)

                    os.unlink(output_file)

                results[f'threads_{threads}'] = {
                    'mean_time': statistics.mean(times),
                    'std_dev': statistics.stdev(times) if len(times) > 1 else 0
                }

            self.results['merging'] = results

        finally:
            # Cleanup
            for db_file in db_files:
                if os.path.exists(db_file):
                    os.unlink(db_file)

    def _benchmark_exporting(self) -> None:
        """Benchmark database exporting performance."""
        print("\nBenchmarking database exporting...")

        # Create test database
        with tempfile.NamedTemporaryFile(mode='w', suffix='.fasta', delete=False) as f:
            for i in range(5000):
                seq = "ATCGATCGATCGATCG" * 15
                f.write(f">seq{i}\n{seq}\n")
            temp_file = f.name

        try:
            # Create database
            counter = KmerCounter(k=31, threads=8)
            db = counter.count_from_file(temp_file)

            # Benchmark different export formats
            from rustkmer import ExportConfig, ExportFormat
            formats = [ExportFormat.TEXT, ExportFormat.JSON, ExportFormat.CSV]

            results = {}

            for fmt in formats:
                print(f"  Exporting to {fmt.value}")

                times = []
                for _ in range(3):
                    with tempfile.NamedTemporaryFile(suffix=f'.{fmt.value}', delete=False) as f:
                        output_file = f.name

                    config = ExportConfig(format=fmt)
                    exporter = DatabaseExporter(config)

                    start = time.time()
                    exporter.export(db, output_file)
                    times.append(time.time() - start)

                    # Get file size
                    file_size = os.path.getsize(output_file)
                    os.unlink(output_file)

                results[fmt.value] = {
                    'mean_time': statistics.mean(times),
                    'std_dev': statistics.stdev(times) if len(times) > 1 else 0,
                    'avg_file_size_mb': file_size / 1024 / 1024
                }

            self.results['exporting'] = results

        finally:
            os.unlink(temp_file)

    def _benchmark_batch_processing(self) -> None:
        """Benchmark batch processing utilities."""
        print("\nBenchmarking batch processing...")

        from rustkmer.performance import BatchProcessor

        # Create test files
        file_count = 10
        files = []

        try:
            for i in range(file_count):
                with tempfile.NamedTemporaryFile(mode='w', suffix='.fasta', delete=False) as f:
                    for j in range(1000):
                        seq = "ATCGATCGATCGATCG" * (5 + i % 5)
                        f.write(f">seq{i}_{j}\n{seq}\n")
                    files.append(f.name)

            # Benchmark batch processor
            processor = BatchProcessor(k=31, threads=8)

            start = time.time()
            databases = processor.count_files_batch(files)
            batch_time = time.time() - start

            # Benchmark individual processing
            start = time.time()
            individual_dbs = []
            for file in files:
                counter = KmerCounter(k=31)
                db = counter.count_from_file(file)
                individual_dbs.append(db)
            individual_time = time.time() - start

            self.results['batch_processing'] = {
                'batch_time': batch_time,
                'individual_time': individual_time,
                'speedup': individual_time / batch_time,
                'files_processed': file_count
            }

        finally:
            for file in files:
                os.unlink(file)

    def _benchmark_parallel_processing(self) -> None:
        """Benchmark parallel processing utilities."""
        print("\nBenchmarking parallel processing...")

        from rustkmer.performance import ParallelProcessor

        # Create test files
        file_count = 20
        files = []

        try:
            for i in range(file_count):
                with tempfile.NamedTemporaryFile(mode='w', suffix='.fasta', delete=False) as f:
                    for j in range(500):
                        seq = "ATCGATCGATCGATCG" * 5
                        f.write(f">seq{i}_{j}\n{seq}\n")
                    files.append(f.name)

            # Thread vs Process comparison
            processor = ParallelProcessor(max_workers=4)

            # Threads
            start = time.time()
            thread_dbs = processor.process_files_parallel(files[:10], 'count', k=31, use_processes=False)
            thread_time = time.time() - start

            # Processes
            start = time.time()
            process_dbs = processor.process_files_parallel(files[10:], 'count', k=31, use_processes=True)
            process_time = time.time() - start

            self.results['parallel_processing'] = {
                'thread_time': thread_time,
                'process_time': process_time,
                'files_per_method': len(files) // 2
            }

        finally:
            for file in files:
                os.unlink(file)

    def _benchmark_memory_usage(self) -> None:
        """Benchmark memory usage patterns."""
        print("\nBenchmarking memory usage...")

        if not PSUTIL_AVAILABLE:
            print("  Skipping (psutil not available)")
            return

        process = psutil.Process()

        # Test memory growth with database operations
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB
        memory_measurements = [initial_memory]

        # Create multiple databases
        databases = []
        for i in range(10):
            with tempfile.NamedTemporaryFile(mode='w', suffix='.fasta', delete=False) as f:
                for j in range(1000):
                    seq = "ATCGATCGATCGATCG" * 10
                    f.write(f">seq{i}_{j}\n{seq}\n")
                temp_file = f.name

            counter = KmerCounter(k=31)
            db = counter.count_from_file(temp_file)
            databases.append(db)

            current_memory = process.memory_info().rss / 1024 / 1024
            memory_measurements.append(current_memory)

            os.unlink(temp_file)

        # Calculate memory statistics
        memory_increase = max(memory_measurements) - initial_memory
        memory_per_db = memory_increase / len(databases)

        self.results['memory_usage'] = {
            'initial_memory_mb': initial_memory,
            'peak_memory_mb': max(memory_measurements),
            'memory_increase_mb': memory_increase,
            'memory_per_database_mb': memory_per_db,
            'memory_measurements': memory_measurements
        }

    def _benchmark_caching(self) -> None:
        """Benchmark database caching performance."""
        print("\nBenchmarking database caching...")

        from rustkmer.performance import DatabaseCache

        # Create test database
        with tempfile.NamedTemporaryFile(mode='w', suffix='.fasta', delete=False) as f:
            for i in range(2000):
                seq = "ATCGATCGATCGATCG" * 20
                f.write(f">seq{i}\n{seq}\n")
            temp_file = f.name
            db_file = temp_file.replace('.fasta', '.rkdb')

        try:
            # Create database
            counter = KmerCounter(k=31)
            db = counter.count_from_file(temp_file)
            db.save(db_file)

            # Benchmark with cache
            cache = DatabaseCache(max_size=5)

            # First load (cache miss)
            start = time.time()
            db1 = Database()
            db1.load(db_file)
            miss_time = time.time() - start

            # Cache the database
            cache.put(db_file, db1)

            # Subsequent loads (cache hits)
            hit_times = []
            for _ in range(10):
                start = time.time()
                cached_db = cache.get(db_file)
                if cached_db is None:
                    # Cache miss, reload
                    cached_db = Database()
                    cached_db.load(db_file)
                    cache.put(db_file, cached_db)
                hit_times.append(time.time() - start)

            self.results['caching'] = {
                'cache_miss_time': miss_time,
                'avg_cache_hit_time': statistics.mean(hit_times),
                'speedup': miss_time / statistics.mean(hit_times),
                'cache_stats': cache.stats()
            }

        finally:
            os.unlink(temp_file)
            if os.path.exists(db_file):
                os.unlink(db_file)

    def _generate_report(self) -> None:
        """Generate comprehensive benchmark report."""
        # Save JSON results
        results_file = self.output_dir / "benchmark_results.json"
        with open(results_file, 'w') as f:
            json.dump(self.results, f, indent=2)

        # Generate text report
        report_file = self.output_dir / "benchmark_report.txt"
        with open(report_file, 'w') as f:
            f.write("RustKmer Performance Benchmark Report\n")
            f.write("=" * 50 + "\n\n")

            # System info
            f.write("System Information:\n")
            f.write("-" * 20 + "\n")
            sys_info = self.results['system_info']
            f.write(f"CPU cores: {sys_info['cpu_count']}\n")
            if 'total_memory_gb' in sys_info:
                f.write(f"Total RAM: {sys_info['total_memory_gb']:.1f} GB\n")
            f.write(f"Platform: {sys_info['platform']}\n\n")

            # Counting benchmarks
            if 'counting' in self.results:
                f.write("K-mer Counting Benchmarks:\n")
                f.write("-" * 30 + "\n")
                for size_key, size_data in self.results['counting'].items():
                    f.write(f"\n{size_key}:\n")
                    for k_key, k_data in size_data.items():
                        f.write(f"  {k_key}:\n")
                        for threads, thread_data in k_data.items():
                            f.write(f"    {threads} threads: {thread_data['mean_time']:.3f}s ± {thread_data['std_dev']:.3f}s\n")

            # Query benchmarks
            if 'querying' in self.results:
                f.write("\nDatabase Querying Benchmarks:\n")
                f.write("-" * 30 + "\n")
                for size_key, size_data in self.results['querying'].items():
                    f.write(f"{size_key}:\n")
                    f.write(f"  Individual queries: {size_data['individual_mean']:.3f}s\n")
                    f.write(f"  Batch query: {size_data['batch_mean']:.3f}s\n")
                    f.write(f"  Speedup: {size_data['speedup']:.1f}x\n")

            # Memory usage
            if 'memory_usage' in self.results:
                mem_data = self.results['memory_usage']
                f.write("\nMemory Usage:\n")
                f.write("-" * 15 + "\n")
                f.write(f"Initial: {mem_data['initial_memory_mb']:.1f} MB\n")
                f.write(f"Peak: {mem_data['peak_memory_mb']:.1f} MB\n")
                f.write(f"Increase: {mem_data['memory_increase_mb']:.1f} MB\n")
                f.write(f"Per database: {mem_data['memory_per_database_mb']:.1f} MB\n")

            # Caching performance
            if 'caching' in self.results:
                cache_data = self.results['caching']
                f.write("\nCaching Performance:\n")
                f.write("-" * 20 + "\n")
                f.write(f"Cache miss: {cache_data['cache_miss_time']:.3f}s\n")
                f.write(f"Cache hit: {cache_data['avg_cache_hit_time']:.6f}s\n")
                f.write(f"Speedup: {cache_data['speedup']:.1f}x\n")

        print(f"\nReports saved to:")
        print(f"  JSON: {results_file}")
        print(f"  Text: {report_file}")


def main():
    """Main benchmark runner."""
    parser = argparse.ArgumentParser(description="RustKmer performance benchmark suite")
    parser.add_argument('output_dir', help="Output directory for benchmark results")
    parser.add_argument('--quick', action='store_true', help="Run quick benchmarks (less comprehensive)")
    args = parser.parse_args()

    # Create and run benchmark suite
    suite = BenchmarkSuite(args.output_dir)
    suite.run_all_benchmarks()


if __name__ == "__main__":
    main()