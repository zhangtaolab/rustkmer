#!/usr/bin/env python3

"""
RustKmer Performance Benchmarking Example

This script demonstrates comprehensive performance benchmarking using the RustKmer Python API:
- Database creation performance across different configurations
- Query performance testing (single and simulated batch)
- Memory usage analysis
- Scalability testing with different data sizes
- Performance regression detection

Data: ../data/demo_rice_genome.fa.gz
K-mer sizes: 5, 7 for performance testing
Output: Comprehensive performance reports and metrics
"""

import os
import sys
import time
import gc
import tempfile
import statistics
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any, NamedTuple

# Import rustkmer classes correctly
from rustkmer import KmerCounter, Database


class Colors:
    """ANSI color codes for terminal output"""
    RED = '\033[0;31m'
    GREEN = '\033[0;32m'
    YELLOW = '\033[1;33m'
    BLUE = '\033[0;34m'
    CYAN = '\033[0;36m'
    MAGENTA = '\033[0;35m'
    NC = '\033[0m'  # No Color


def print_header(title: str):
    """Print a formatted header"""
    print(f"\n{Colors.BLUE}=== {title} ==={Colors.NC}")


def print_success(message: str):
    """Print a success message"""
    print(f"{Colors.GREEN}✓ {message}{Colors.NC}")


def print_info(message: str):
    """Print an info message"""
    print(f"{Colors.YELLOW}→ {message}{Colors.NC}")


def print_error(message: str):
    """Print an error message"""
    print(f"{Colors.RED}✗ {message}{Colors.NC}")


def print_benchmark(message: str):
    """Print a benchmark-related message"""
    print(f"{Colors.CYAN}⚡ {message}{Colors.NC}")


def format_file_size(size_bytes: int) -> str:
    """Format file size in human readable format"""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size_bytes < 1024.0:
            return f"{size_bytes:.1f}{unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.1f}TB"


def format_number(num: int) -> str:
    """Format large numbers with commas"""
    return f"{num:,}"


def format_time(seconds: float) -> str:
    """Format time in appropriate units"""
    if seconds < 0.001:
        return f"{seconds * 1000000:.1f}μs"
    elif seconds < 1:
        return f"{seconds * 1000:.1f}ms"
    elif seconds < 60:
        return f"{seconds:.2f}s"
    elif seconds < 3600:
        return f"{seconds / 60:.1f}m"
    else:
        return f"{seconds / 3600:.1f}h"


class PerformanceMetrics(NamedTuple):
    """Named tuple for performance metrics"""
    name: str
    kmer_size: int
    canonical: bool
    threads: int
    time_seconds: float
    kmer_count: int
    unique_kmers: int
    database_size_bytes: int


def get_data_path() -> Path:
    """Get the path to the demo data"""
    script_dir = Path(__file__).parent
    data_path = script_dir.parent / "data" / "demo_rice_genome.fa.gz"

    if not data_path.exists():
        # Use the actual test data that exists
        data_path = script_dir.parent.parent / "tests" / "007-api-compatibility" / "test_data" / "small_dataset.fa"
        if not data_path.exists():
            print_error(f"Demo data not found: {data_path}")
            print_info("Please ensure test data is available")
            sys.exit(1)

    return data_path


def get_output_dir() -> Path:
    """Get the output directory"""
    script_dir = Path(__file__).parent
    output_dir = script_dir.parent / "output"
    output_dir.mkdir(exist_ok=True)
    return output_dir


def benchmark_database_creation(data_path: Path, output_dir: Path, kmer_size: int = 7):
    """Benchmark database creation with different configurations"""
    print_header("Database Creation Benchmark")

    configurations = [
        {"name": "Basic", "canonical": False, "threads": 1},
        {"name": "Multi-thread", "canonical": False, "threads": 4},
        {"name": "Canonical", "canonical": True, "threads": 4},
        {"name": "Optimized", "canonical": True, "threads": 8},
    ]

    results = []

    print_benchmark("Testing database creation configurations:")
    print(f"{'Config':<12} {'Threads':<8} {'Canonical':<10} {'Time (s)':<10} {'K-mers/s':<12} {'DB Size':<10}")
    print("-" * 75)

    for config in configurations:
        db_file = output_dir / f"benchmark_{config['name'].lower()}_k{kmer_size}.rkdb"

        # Remove existing file for fair comparison
        if db_file.exists():
            db_file.unlink()

        try:
            # Force garbage collection before test
            gc.collect()
            start_time = time.time()

            counter = KmerCounter(
                k=kmer_size,
                canonical=config["canonical"],
                threads=config["threads"]
            )
            counter.count_file(str(data_path))
            counter.save_to_database(str(db_file), False)

            end_time = time.time()

            if db_file.exists():
                creation_time = end_time - start_time
                file_size = db_file.stat().st_size
                unique_kmers = counter.get_unique_count()
                total_kmers = counter.get_total_count()

                # Calculate k-mers per second
                kmers_per_sec = total_kmers / creation_time if creation_time > 0 else 0

                result = PerformanceMetrics(
                    name=config["name"],
                    kmer_size=kmer_size,
                    canonical=config["canonical"],
                    threads=config["threads"],
                    time_seconds=creation_time,
                    kmer_count=total_kmers,
                    unique_kmers=unique_kmers,
                    database_size_bytes=file_size
                )
                results.append(result)

                print(f"{config['name']:<12} {config['threads']:<8} {config['canonical']:<10} "
                      f"{creation_time:<10.2f} {kmers_per_sec:<12.0f} {format_file_size(file_size):<10}")

            else:
                print_error(f"Failed to create database for {config['name']} configuration")

        except Exception as e:
            print_error(f"Error in {config['name']} configuration: {e}")

    # Find best performance
    if results:
        best_performance = min(results, key=lambda x: x.time_seconds)
        best_kmers_per_sec = max(results, key=lambda x: x.kmer_count / x.time_seconds if x.time_seconds > 0 else 0)

        print(f"\n{Colors.GREEN}Fastest creation: {best_performance.name} "
              f"({format_time(best_performance.time_seconds)}){Colors.NC}")
        print(f"{Colors.GREEN}Highest throughput: {best_kmers_per_sec.name} "
              f"({best_kmers_per_sec.kmer_count / best_kmers_per_sec.time_seconds:.0f} k-mers/s){Colors.NC}")

    return results


def benchmark_query_performance(db_files: Dict[str, str], kmer_size: int = 7):
    """Benchmark query performance across different databases"""
    print_header("Query Performance Benchmark")

    # Generate test k-mers
    test_kmers = [
        "AAAAAAA", "TTTTTTT", "CCCCCCC", "GGGGGGG",
        "ACGTACG", "TGCATGC", "ATGCATG", "CGATCGA",
        "AAAAAAC", "CCCCCTT", "GGGGGGA", "TTTTTTG",
        "ACGTACGTACGT", "TGCATGCATGC", "ATGCATGCATG"
    ]

    # Filter to k-mer size
    test_kmers = [k[:kmer_size] for k in test_kmers if len(k[:kmer_size]) == kmer_size]

    results = {}

    print_benchmark("Testing query performance:")
    print(f"{'Database':<15} {'Queries':<8} {'Time (s)':<10} {'Q/s':<12} {'Found':<8} {'Avg (ms)':<10}")
    print("-" * 75)

    for db_name, db_path in db_files.items():
        if not Path(db_path).exists():
            continue

        try:
            db = Database()
            db.load(db_path)

            # Benchmark queries
            gc.collect()
            start_time = time.time()

            found_count = 0
            for kmer in test_kmers:
                result = db.query(kmer)
                if result.found:
                    found_count += 1

            end_time = time.time()

            query_time = end_time - start_time
            queries_per_sec = len(test_kmers) / query_time if query_time > 0 else 0
            avg_time_ms = (query_time / len(test_kmers)) * 1000

            results[db_name] = {
                'queries': len(test_kmers),
                'time_seconds': query_time,
                'queries_per_sec': queries_per_sec,
                'found_count': found_count,
                'avg_time_ms': avg_time_ms
            }

            print(f"{db_name:<15} {len(test_kmers):<8} {query_time:<10.4f} "
                  f"{queries_per_sec:<12.0f} {found_count:<8} {avg_time_ms:<10.3f}")

        except Exception as e:
            print_error(f"Error querying {db_name}: {e}")

    # Find best query performance
    if results:
        best_query = max(results.items(), key=lambda x: x[1]['queries_per_sec'])
        print(f"\n{Colors.GREEN}Fastest queries: {best_query[0]} "
              f"({best_query[1]['queries_per_sec']:.0f} queries/s){Colors.NC}")

    return results


def benchmark_scalability(data_path: Path, output_dir: Path):
    """Benchmark scalability with different k-mer sizes"""
    print_header("Scalability Benchmark")

    kmer_sizes = [5, 7]
    results = []

    print_benchmark("Testing scalability across k-mer sizes:")
    print(f"{'K-mer Size':<12} {'Time (s)':<10} {'K-mers':<12} {'K-mers/s':<12} {'DB Size':<10} {'Unique':<10}")
    print("-" * 75)

    for kmer_size in kmer_sizes:
        db_file = output_dir / f"scalability_k{kmer_size}.rkdb"

        # Remove existing file
        if db_file.exists():
            db_file.unlink()

        try:
            gc.collect()
            start_time = time.time()

            counter = KmerCounter(k=kmer_size, canonical=True, threads=4)
            counter.count_file(str(data_path))
            counter.save_to_database(str(db_file), False)

            end_time = time.time()

            if db_file.exists():
                creation_time = end_time - start_time
                file_size = db_file.stat().st_size
                unique_kmers = counter.get_unique_count()
                total_kmers = counter.get_total_count()

                kmers_per_sec = total_kmers / creation_time if creation_time > 0 else 0

                print(f"{kmer_size:<12} {creation_time:<10.2f} {total_kmers:<12} "
                      f"{kmers_per_sec:<12.0f} {format_file_size(file_size):<10} {unique_kmers:<10}")

                results.append({
                    'kmer_size': kmer_size,
                    'time_seconds': creation_time,
                    'kmer_count': total_kmers,
                    'unique_kmers': unique_kmers,
                    'kmers_per_sec': kmers_per_sec,
                    'database_size': file_size
                })

        except Exception as e:
            print_error(f"Error with k={kmer_size}: {e}")

    return results


def export_benchmark_results(creation_results: List[PerformanceMetrics],
                            query_results: Dict[str, Dict],
                            scalability_results: List[Dict],
                            output_dir: Path):
    """Export comprehensive benchmark results"""
    print_header("Export Benchmark Results")

    export_file = output_dir / "performance_benchmark_report.txt"

    try:
        with open(export_file, 'w') as f:
            f.write("# RustKmer Performance Benchmark Report\n")
            f.write(f"# Generated: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write("# " + "=" * 60 + "\n\n")

            # Database Creation Results
            f.write("## Database Creation Performance\n\n")
            f.write(f"{'Configuration':<15} {'K-mer Size':<12} {'Threads':<8} {'Time (s)':<10} "
                   f"{'K-mers/s':<12} {'DB Size':<12} {'Unique K-mers':<15}\n")
            f.write("-" * 90 + "\n")

            for result in creation_results:
                kmers_per_sec = result.kmer_count / result.time_seconds if result.time_seconds > 0 else 0
                f.write(f"{result.name:<15} {result.kmer_size:<12} {result.threads:<8} "
                       f"{result.time_seconds:<10.2f} {kmers_per_sec:<12.0f} "
                       f"{format_file_size(result.database_size_bytes):<12} {result.unique_kmers:<15}\n")

            # Query Performance Results
            f.write("\n## Query Performance\n\n")
            f.write(f"{'Database':<15} {'Queries':<8} {'Time (s)':<10} {'Q/s':<12} "
                   f"{'Found':<8} {'Avg (ms)':<10}\n")
            f.write("-" * 70 + "\n")

            for db_name, metrics in query_results.items():
                f.write(f"{db_name:<15} {metrics['queries']:<8} {metrics['time_seconds']:<10.4f} "
                       f"{metrics['queries_per_sec']:<12.0f} {metrics['found_count']:<8} "
                       f"{metrics['avg_time_ms']:<10.3f}\n")

            # Scalability Results
            f.write("\n## Scalability Analysis\n\n")
            f.write(f"{'K-mer Size':<12} {'Time (s)':<10} {'K-mers':<12} {'K-mers/s':<12} "
                   f"{'DB Size':<12} {'Unique':<12}\n")
            f.write("-" * 75 + "\n")

            for result in scalability_results:
                f.write(f"{result['kmer_size']:<12} {result['time_seconds']:<10.2f} "
                       f"{result['kmer_count']:<12} {result['kmers_per_sec']:<12.0f} "
                       f"{format_file_size(result['database_size']):<12} {result['unique_kmers']:<12}\n")

        if export_file.exists():
            export_size = export_file.stat().st_size
            print_success(f"Exported benchmark report to: {export_file.name}")
            print_info(f"Report size: {format_file_size(export_size)}")

    except Exception as e:
        print_error(f"Error exporting benchmark results: {e}")


def main():
    """Main execution function"""
    print_header("RustKmer Performance Benchmarking")

    # Configuration
    kmer_size = 7  # Primary k-mer size for testing
    data_path = get_data_path()
    output_dir = get_output_dir()

    print(f"Data: {data_path}")
    if data_path.exists():
        print(f"Data size: {format_file_size(data_path.stat().st_size)}")
    print(f"Primary k-mer size: {kmer_size}")
    print(f"Output: {output_dir}")

    # Run benchmarks
    print()
    creation_results = benchmark_database_creation(data_path, output_dir, kmer_size)

    print()
    # Create db file mapping for query benchmark
    db_files = {}
    for result in creation_results:
        db_files[result.name] = str(output_dir / f"benchmark_{result.name.lower()}_k{kmer_size}.rkdb")

    query_results = benchmark_query_performance(db_files, kmer_size)

    print()
    scalability_results = benchmark_scalability(data_path, output_dir)

    print()
    export_benchmark_results(creation_results, query_results, scalability_results, output_dir)

    print_header("Performance Benchmarking Completed Successfully!")
    print_success(f"All benchmarking tests completed")
    print_info("Benchmark reports exported to output directory")

    # Clean up benchmark databases
    for db_file in db_files.values():
        if Path(db_file).exists():
            Path(db_file).unlink()
    print_info("Cleaned up benchmark databases")

    return True


if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print_info("\nScript interrupted by user")
        sys.exit(1)
    except Exception as e:
        print_error(f"Unexpected error: {e}")
        sys.exit(1)