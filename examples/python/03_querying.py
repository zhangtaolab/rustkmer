#!/usr/bin/env python3

"""
RustKmer Querying Example

This script demonstrates querying functionality using the RustKmer Python API:
- Single k-mer queries
- Batch query operations (simulated)
- Query result analysis
- Performance comparison of query methods

Data: ../data/demo_rice_genome.fa.gz
K-mer size: 7 for optimal performance with demo data
Output: Query results and performance analysis
"""

import os
import sys
import time
import random
import tempfile
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any

# Import rustkmer classes correctly
from rustkmer import KmerCounter, Database


class Colors:
    """ANSI color codes for terminal output"""
    RED = '\033[0;31m'
    GREEN = '\033[0;32m'
    YELLOW = '\033[1;33m'
    BLUE = '\033[0;34m'
    CYAN = '\033[0;36m'
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


def format_file_size(size_bytes: int) -> str:
    """Format file size in human readable format"""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size_bytes < 1024.0:
            return f"{size_bytes:.1f}{unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.1f}TB"


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


def create_test_database(data_path: Path, output_dir: Path, kmer_size: int = 7):
    """Create a test database for querying demonstrations"""
    print_header("Creating Test Database")

    db_file = output_dir / f"query_test_k{kmer_size}.rkdb"

    if db_file.exists():
        print_info(f"Using existing database: {db_file.name}")
        return str(db_file)

    print_info(f"Creating test database with k={kmer_size}...")
    start_time = time.time()

    try:
        counter = KmerCounter(k=kmer_size, canonical=False, threads=4)
        counter.count_file(str(data_path))
        counter.save_to_database(str(db_file), False)

        end_time = time.time()

        if db_file.exists():
            file_size = db_file.stat().st_size
            print_success(f"Created database: {db_file.name} ({format_file_size(file_size)})")
            print_info(f"Creation time: {end_time - start_time:.2f} seconds")

            # Get statistics from counter
            unique_kmers = counter.get_unique_count()
            total_kmers = counter.get_total_count()
            print_info(f"Total k-mers: {total_kmers:,}")
            print_info(f"Unique k-mers: {unique_kmers:,}")

            return str(db_file)
        else:
            print_error("Failed to create database")
            return None

    except Exception as e:
        print_error(f"Error creating database: {e}")
        return None


def generate_test_kmers(kmer_size: int = 7, count: int = 100) -> List[str]:
    """Generate test k-mers for querying"""
    bases = ['A', 'T', 'C', 'G']
    kmers = []

    # Add some common patterns
    common_patterns = [
        "A" * kmer_size,
        "T" * kmer_size,
        "C" * kmer_size,
        "G" * kmer_size,
        "ACGT" * ((kmer_size // 4) + 1),
        "TGCA" * ((kmer_size // 4) + 1),
    ]

    # Truncate to kmer_size
    common_patterns = [pattern[:kmer_size] for pattern in common_patterns]
    kmers.extend(common_patterns)

    # Add random k-mers
    while len(kmers) < count:
        kmer = ''.join(random.choice(bases) for _ in range(kmer_size))
        if kmer not in kmers:  # Avoid duplicates
            kmers.append(kmer)

    return kmers[:count]


def single_query_demo(db_path: str, kmer_size: int = 7):
    """Demonstrate single k-mer queries"""
    print_header("Single K-mer Query Demo")

    try:
        db = Database()
        db.load(db_path)

        # Test k-mers with different patterns
        test_kmers = [
            "AAAAAAA",  # Homopolymer A
            "TTTTTTT",  # Homopolymer T
            "CCCCCCC",  # Homopolymer C
            "GGGGGGG",  # Homopolymer G
            "ACGTACG",  # Alternating pattern
            "TGCATGC",  # Reverse complement pattern
            "ATGCATG",  # Another pattern
            "CGATCGA",  # Another pattern
        ]

        print_info("Testing individual k-mer queries:")
        print(f"{'K-mer':<10} {'Found':<6} {'Count':<10} {'Query Time (ms)'}")
        print("-" * 40)

        total_time = 0
        found_count = 0

        for kmer in test_kmers:
            start_time = time.time()
            result = db.query(kmer)
            end_time = time.time()

            query_time_ms = (end_time - start_time) * 1000
            total_time += query_time_ms

            if result and result.found:
                print(f"{kmer:<10} {'YES':<6} {result.count:<10} {query_time_ms:.3f}")
                found_count += 1
            else:
                print(f"{kmer:<10} {'NO':<6} {'0':<10} {query_time_ms:.3f}")

        print("-" * 40)
        print_info(f"Summary:")
        print(f"  K-mers tested: {len(test_kmers)}")
        print(f"  K-mers found: {found_count}")
        print(f"  Average query time: {total_time / len(test_kmers):.3f} ms")

    except Exception as e:
        print_error(f"Error in single query demo: {e}")


def simulated_batch_query_demo(db_path: str, kmer_size: int = 7):
    """Demonstrate simulated batch k-mer queries using individual queries"""
    print_header("Simulated Batch K-mer Query Demo")

    try:
        db = Database()
        db.load(db_path)

        # Generate test k-mers
        batch_sizes = [10, 50, 100]
        results = {}

        for batch_size in batch_sizes:
            print_info(f"Testing simulated batch size: {batch_size} k-mers")

            # Generate test k-mers
            test_kmers = generate_test_kmers(kmer_size, batch_size)

            # Simulated batch query using individual queries
            start_time = time.time()
            batch_results = []
            found_kmers = []

            for kmer in test_kmers:
                result = db.query(kmer)
                batch_results.append(result)
                if result.found:
                    found_kmers.append((kmer, result.count))

            end_time = time.time()

            # Analyze results
            found_count = len(found_kmers)
            total_count = sum(count for _, count in found_kmers)
            query_time_ms = (end_time - start_time) * 1000

            results[batch_size] = {
                'found_count': found_count,
                'total_count': total_count,
                'time_ms': query_time_ms,
                'avg_time_per_query': query_time_ms / batch_size
            }

            print(f"  K-mers queried: {batch_size}")
            print(f"  K-mers found: {found_count}")
            print(f"  Total count: {total_count:,}")
            print(f"  Query time: {query_time_ms:.3f} ms")
            print(f"  Avg per query: {results[batch_size]['avg_time_per_query']:.3f} ms")
            print()

        # Performance comparison
        print_info("Simulated Batch Query Performance Comparison:")
        print(f"{'Batch Size':<12} {'Found':<8} {'Total Count':<12} {'Time (ms)':<12} {'Avg/Query (ms)':<16}")
        print("-" * 70)

        for batch_size in sorted(batch_sizes):
            result = results[batch_size]
            print(f"{batch_size:<12} {result['found_count']:<8} {result['total_count']:<12} "
                  f"{result['time_ms']:<12.3f} {result['avg_time_per_query']:<16.3f}")

        # Find optimal batch size
        best_batch_size = min(results.keys(), key=lambda x: results[x]['avg_time_per_query'])
        print(f"\nBest performance: batch size {best_batch_size} "
              f"({results[best_batch_size]['avg_time_per_query']:.3f} ms per query)")

    except Exception as e:
        print_error(f"Error in simulated batch query demo: {e}")


def query_performance_comparison(db_path: str, kmer_size: int = 7):
    """Compare performance of different query patterns"""
    print_header("Query Performance Comparison")

    try:
        db = Database()
        db.load(db_path)

        # Test k-mers
        test_kmers = generate_test_kmers(kmer_size, 100)

        # Sequential single query performance
        print_info("Testing sequential single queries...")
        start_time = time.time()
        single_results = []
        for kmer in test_kmers:
            result = db.query(kmer)
            if result.found:
                single_results.append((kmer, result.count))
        end_time = time.time()
        single_time_ms = (end_time - start_time) * 1000

        # Random order queries (different access pattern)
        print_info("Testing random order queries...")
        random.shuffle(test_kmers)
        start_time = time.time()
        random_results = []
        for kmer in test_kmers:
            result = db.query(kmer)
            if result.found:
                random_results.append((kmer, result.count))
        end_time = time.time()
        random_time_ms = (end_time - start_time) * 1000

        # Analyze results
        single_count = len(single_results)
        random_count = len(random_results)

        print_info("Performance Comparison:")
        print(f"{'Method':<20} {'Time (ms)':<12} {'K-mers/s':<15} {'Found':<8}")
        print("-" * 65)

        single_kmers_per_sec = len(test_kmers) / (single_time_ms / 1000)
        random_kmers_per_sec = len(test_kmers) / (random_time_ms / 1000)

        print(f"{'Sequential':<20} {single_time_ms:<12.3f} {single_kmers_per_sec:<15.0f} {single_count:<8}")
        print(f"{'Random Order':<20} {random_time_ms:<12.3f} {random_kmers_per_sec:<15.0f} {random_count:<8}")

        # Verify consistency
        if single_count == random_count:
            print_success("✓ Results consistent between sequential and random queries")
        else:
            print_error(f"✗ Results inconsistent: sequential={single_count}, random={random_count}")

    except Exception as e:
        print_error(f"Error in performance comparison: {e}")


def export_query_results(db_path: str, output_dir: Path, kmer_size: int = 7):
    """Export query results to file"""
    print_header("Export Query Results")

    try:
        db = Database()
        db.load(db_path)

        # Generate comprehensive test k-mers
        test_patterns = [
            # Homopolymers
            ["A" * kmer_size, "T" * kmer_size, "C" * kmer_size, "G" * kmer_size],
            # Repeating patterns
            ["ACGT" * ((kmer_size // 4) + 1), "TGCA" * ((kmer_size // 4) + 1)],
            ["ATGC" * ((kmer_size // 4) + 1), "CGAT" * ((kmer_size // 4) + 1)],
            # Mixed patterns
            generate_test_kmers(kmer_size, 50)
        ]

        all_kmers = []
        for pattern_group in test_patterns:
            all_kmers.extend(pattern_group)

        # Remove duplicates and limit length
        unique_kmers = list(set(all_kmers))[:100]

        # Query all k-mers (simulate batch with individual queries)
        start_time = time.time()
        found_kmers = []

        for kmer in unique_kmers:
            result = db.query(kmer)
            if result.found:
                found_kmers.append((kmer, result.count))

        end_time = time.time()

        # Export to file
        export_file = output_dir / f"query_results_k{kmer_size}.txt"

        with open(export_file, 'w') as f:
            f.write(f"# RustKmer Query Results Export\n")
            f.write(f"# Database: {db_path}\n")
            f.write(f"# K-mer size: {kmer_size}\n")
            f.write(f"# K-mers tested: {len(unique_kmers)}\n")
            f.write(f"# K-mers found: {len(found_kmers)}\n")
            f.write(f"# Query time: {end_time - start_time:.3f}s\n")
            f.write(f"# Export timestamp: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write("# Format: KMER\tCOUNT\n")
            f.write("=" * 60 + "\n")

            # Sort by count descending
            found_kmers.sort(key=lambda x: x[1], reverse=True)

            for kmer, count in found_kmers:
                f.write(f"{kmer}\t{count}\n")

        if export_file.exists():
            export_size = export_file.stat().st_size
            print_success(f"Exported results to: {export_file.name}")
            print_info(f"Export size: {format_file_size(export_size)}")
            print_info(f"K-mers with counts: {len(found_kmers)}")

            # Show top results
            print_info("Top 10 most frequent k-mers:")
            for kmer, count in found_kmers[:10]:
                print(f"  {kmer}: {count:,}")

    except Exception as e:
        print_error(f"Error exporting query results: {e}")


def query_database_info(db_path: str):
    """Display comprehensive database information"""
    print_header("Database Information")

    try:
        db = Database()
        db.load(db_path)

        # Get statistics
        stats = db.get_stats()
        print_info("Database Statistics:")
        print(f"  K-mer size: {stats.kmer_size}")
        print(f"  Total k-mers: {stats.total_kmers:,}")
        print(f"  Canonical: {stats.canonical}")
        print(f"  Uses memory mapping: {stats.uses_memory_mapping}")

        # File information
        db_file = Path(db_path)
        if db_file.exists():
            file_size = db_file.stat().st_size
            print_info("File Information:")
            print(f"  File size: {format_file_size(file_size)}")
            print(f"  File path: {db_file}")

    except Exception as e:
        print_error(f"Error getting database info: {e}")


def main():
    """Main execution function"""
    print_header("RustKmer Querying Examples")

    # Configuration
    kmer_size = 7
    data_path = get_data_path()
    output_dir = get_output_dir()

    print(f"Data: {data_path}")
    if data_path.exists():
        print(f"Data size: {format_file_size(data_path.stat().st_size)}")
    print(f"K-mer size: {kmer_size}")
    print(f"Output: {output_dir}")

    # Create test database
    print()
    db_path = create_test_database(data_path, output_dir, kmer_size)

    if not db_path:
        print_error("Failed to create test database")
        return False

    # Execute querying demonstrations
    print()
    query_database_info(db_path)

    print()
    single_query_demo(db_path, kmer_size)

    print()
    simulated_batch_query_demo(db_path, kmer_size)

    print()
    query_performance_comparison(db_path, kmer_size)

    print()
    export_query_results(db_path, output_dir, kmer_size)

    print_header("Querying Examples Completed Successfully!")
    print_success(f"All querying examples completed with k={kmer_size}")
    print_info("Query results exported to output directory")
    print_info("You can now query the database using:")
    print(f"  python -c \"from rustkmer import Database; db=Database(); db.load('{db_path}'); print(db.query('ACGTACG').count)\"")

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