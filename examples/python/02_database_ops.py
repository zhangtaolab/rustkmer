#!/usr/bin/env python3

"""
RustKmer Database Operations Example

This script demonstrates database operations using the RustKmer Python API:
- Database loading and creation
- Database statistics and metadata
- Database export functionality
- Database comparison and validation

Data: ../data/demo_rice_genome.fa.gz
K-mer size: 7 for optimal performance with demo data
Output: Multiple database formats and exports
"""

import os
import sys
import time
import tempfile
from pathlib import Path
from typing import Dict, List, Optional, Any

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


def create_databases(data_path: Path, output_dir: Path, kmer_size: int = 7):
    """Create databases with different configurations"""
    print_header("Database Creation")

    databases = {}

    # Configuration variations
    configs = [
        {"name": "canonical", "canonical": True, "threads": 4},
        {"name": "noncanonical", "canonical": False, "threads": 4},
        {"name": "single_thread", "canonical": False, "threads": 1},
    ]

    for config in configs:
        print_info(f"Creating {config['name']} database...")
        output_file = output_dir / f"ops_k{kmer_size}_{config['name']}.rkdb"

        start_time = time.time()

        try:
            counter = KmerCounter(
                k=kmer_size,
                canonical=config["canonical"],
                threads=config["threads"]
            )
            counter.count_file(str(data_path))
            counter.save_to_database(str(output_file), False)

            end_time = time.time()

            if output_file.exists():
                file_size = output_file.stat().st_size
                unique_kmers = counter.get_unique_count()
                total_kmers = counter.get_total_count()

                databases[config['name']] = {
                    'path': str(output_file),
                    'size': file_size,
                    'time': end_time - start_time,
                    'unique_kmers': unique_kmers,
                    'total_kmers': total_kmers,
                    'config': config
                }
                print_success(f"Created {config['name']}: {format_file_size(file_size)} ({end_time - start_time:.2f}s)")
                print_info(f"  Unique k-mers: {unique_kmers:,}, Total: {total_kmers:,}")
            else:
                print_error(f"Failed to create {config['name']} database")

        except Exception as e:
            print_error(f"Error creating {config['name']} database: {e}")

    return databases


def database_statistics(databases: Dict[str, Any]):
    """Display comprehensive database statistics"""
    print_header("Database Statistics and Metadata")

    for name, db_info in databases.items():
        print_info(f"Statistics for {name} database:")

        try:
            db = Database()
            db.load(db_info['path'])

            # Get database stats
            stats = db.get_stats()
            print(f"  K-mer size: {stats.kmer_size}")
            print(f"  Total k-mers: {stats.total_kmers:,}")
            print(f"  Canonical: {stats.canonical}")
            print(f"  Uses memory mapping: {stats.uses_memory_mapping}")

            # Get file info
            file_path = Path(db_info['path'])
            if file_path.exists():
                file_size = file_path.stat().st_size
                print(f"  File size: {format_file_size(file_size)}")
                print(f"  File path: {file_path}")

            print()

        except Exception as e:
            print_error(f"Error reading {name} database: {e}")


def export_databases(databases: Dict[str, Any], output_dir: Path, kmer_size: int = 7):
    """Demonstrate database export functionality"""
    print_header("Database Export Functionality")

    for name, db_info in databases.items():
        print_info(f"Exporting {name} database...")

        try:
            db = Database()
            db.load(db_info['path'])
            export_file = output_dir / f"ops_k{kmer_size}_{name}_export.txt"

            start_time = time.time()

            # Different export strategies
            if name == "canonical":
                # Export top k-mers by querying common patterns
                test_kmers = [
                    "AAAAAAA", "CCCCCC", "GGGGGG", "TTTTTT",  # Homopolymers
                    "ACGTACG", "CGTACGT", "GTACGTA", "TACGTAC",  # Repeats
                ]
            else:
                # Export diverse k-mers for non-canonical
                test_kmers = [
                    "AAAAAAA", "CCCCCCC", "GGGGGGG", "TTTTTTT",
                    "ACGTACG", "TGCATGC", "ATGCATG", "CATGCAT",
                    "AAAAAAC", "CCCCCTT", "GGGGGGA", "TTTTTTG",
                ]

            # Query k-mers and collect results
            results = []
            for kmer in test_kmers:
                result = db.query(kmer)
                if result.found:
                    results.append((kmer, result.count))

            end_time = time.time()

            # Write export file
            with open(export_file, 'w') as f:
                f.write(f"# RustKmer Database Export - {name.title()}\n")
                f.write(f"# Database: {db_info['path']}\n")
                f.write(f"# K-mer size: {kmer_size}\n")
                f.write(f"# Configuration: {db_info['config']}\n")
                f.write(f"# Export time: {end_time - start_time:.3f}s\n")
                f.write(f"# K-mers with counts > 0: {len(results)}\n")
                f.write("# Format: KMER\tCOUNT\n")
                f.write("=" * 60 + "\n")

                # Sort by count descending
                results.sort(key=lambda x: x[1], reverse=True)
                for kmer, count in results:
                    f.write(f"{kmer}\t{count}\n")

            if export_file.exists():
                export_size = export_file.stat().st_size
                print_success(f"Exported {name}: {format_file_size(export_size)} ({len(results)} k-mers)")

        except Exception as e:
            print_error(f"Error exporting {name} database: {e}")


def compare_databases(databases: Dict[str, Any]):
    """Compare different database configurations"""
    print_header("Database Configuration Comparison")

    if len(databases) < 2:
        print_info("Need at least 2 databases for comparison")
        return

    # Print comparison table
    print_info("Database Comparison:")
    print(f"{'Configuration':<15} {'Size':<10} {'Time (s)':<10} {'Unique K-mers':<12} {'Canonical'}")
    print("-" * 75)

    for name, db_info in databases.items():
        size_str = format_file_size(db_info['size'])
        time_str = f"{db_info['time']:.2f}"
        kmer_str = f"{db_info['unique_kmers']:,}"
        canonical_str = str(db_info['config']['canonical'])

        print(f"{name:<15} {size_str:<10} {time_str:<10} {kmer_str:<12} {canonical_str}")

    # Find best performance
    fastest_db = min(databases.items(), key=lambda x: x[1]['time'])
    smallest_db = min(databases.items(), key=lambda x: x[1]['size'])
    most_kmers_db = max(databases.items(), key=lambda x: x[1]['unique_kmers'])

    print("\nPerformance Summary:")
    print_success(f"Fastest creation: {fastest_db[0]} ({fastest_db[1]['time']:.2f}s)")
    print_success(f"Smallest database: {smallest_db[0]} ({format_file_size(smallest_db[1]['size'])})")
    print_success(f"Most k-mers: {most_kmers_db[0]} ({most_kmers_db[1]['unique_kmers']:,} unique)")


def database_validation(databases: Dict[str, Any]):
    """Validate database integrity"""
    print_header("Database Integrity Validation")

    for name, db_info in databases.items():
        print_info(f"Validating {name} database...")

        try:
            db = Database()
            db.load(db_info['path'])

            # Test database is accessible
            stats = db.get_stats()

            # Test query functionality
            test_result = db.query("ACGTACG")

            # Test file size is reasonable
            file_size = db_info['size']

            validation_results = []

            # Check if k-mer size is expected
            if stats.kmer_size == 7:
                validation_results.append("✓ Correct k-mer size")
            else:
                validation_results.append(f"✗ Unexpected k-mer size: {stats.kmer_size}")

            # Check if database has k-mers
            if stats.total_kmers > 0:
                validation_results.append(f"✓ Contains {stats.total_kmers:,} k-mers")
            else:
                validation_results.append("✗ No k-mers found")

            # Check if file size is reasonable (> 100 bytes for headers)
            if file_size > 100:
                validation_results.append(f"✓ Reasonable file size: {format_file_size(file_size)}")
            else:
                validation_results.append(f"✗ File too small: {format_file_size(file_size)}")

            # Check if query works
            if hasattr(test_result, 'count') and hasattr(test_result, 'found'):
                validation_results.append("✓ Query functionality works")
            else:
                validation_results.append("✗ Query functionality failed")

            # Check if canonical flag matches config
            if stats.canonical == db_info['config']['canonical']:
                validation_results.append("✓ Canonical flag matches configuration")
            else:
                validation_results.append("✗ Canonical flag mismatch")

            # Print validation results
            print(f"  {name} validation:")
            for result in validation_results:
                print(f"    {result}")

        except Exception as e:
            print_error(f"Validation failed for {name}: {e}")


def performance_analysis(databases: Dict[str, Any]):
    """Analyze performance characteristics"""
    print_header("Performance Analysis")

    if not databases:
        print_info("No databases available for analysis")
        return

    # Calculate performance metrics
    total_time = sum(db['time'] for db in databases.values())
    total_size = sum(db['size'] for db in databases.values())
    total_kmers = sum(db['unique_kmers'] for db in databases.values())
    avg_time = total_time / len(databases)

    print_info("Overall Performance:")
    print(f"  Total databases created: {len(databases)}")
    print(f"  Total creation time: {total_time:.2f}s")
    print(f"  Average creation time: {avg_time:.2f}s")
    print(f"  Total disk usage: {format_file_size(total_size)}")
    print(f"  Average database size: {format_file_size(total_size // len(databases))}")
    print(f"  Total unique k-mers across all databases: {total_kmers:,}")

    # Time per k-mer efficiency
    for name, db_info in databases.items():
        if db_info['unique_kmers'] > 0:
            time_per_kmer = (db_info['time'] / db_info['unique_kmers']) * 1000000  # microseconds per k-mer
            print(f"  {name}: {time_per_kmer:.1f} μs per k-mer")

    # Database efficiency (k-mers per byte)
    for name, db_info in databases.items():
        if db_info['size'] > 0:
            kmers_per_byte = db_info['unique_kmers'] / db_info['size']
            print(f"  {name}: {kmers_per_byte:.2f} k-mers per byte")


def main():
    """Main execution function"""
    print_header("RustKmer Database Operations Examples")

    # Configuration
    kmer_size = 7
    data_path = get_data_path()
    output_dir = get_output_dir()

    print(f"Data: {data_path}")
    if data_path.exists():
        print(f"Data size: {format_file_size(data_path.stat().st_size)}")
    print(f"K-mer size: {kmer_size}")
    print(f"Output: {output_dir}")

    # Execute database operations
    print()
    databases = create_databases(data_path, output_dir, kmer_size)

    if not databases:
        print_error("No databases were created successfully")
        return False

    print()
    database_statistics(databases)

    print()
    export_databases(databases, output_dir, kmer_size)

    print()
    compare_databases(databases)

    print()
    database_validation(databases)

    print()
    performance_analysis(databases)

    print_header("Database Operations Completed Successfully!")
    print_success(f"All database operations completed with k={kmer_size}")
    print_info("You can now query these databases using:")
    for name in databases.keys():
        db_path = databases[name]['path']
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