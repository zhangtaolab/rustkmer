#!/usr/bin/env python3

"""
RustKmer Python API K-mer Counting Example

This script demonstrates k-mer counting using the RustKmer Python API with
k=7 for optimal performance with the demo rice genome data.

Data: ../data/demo_rice_genome.fa.gz
K-mer size: 7 (optimal for demo data)
Output: Multiple database files with different configurations
"""

import os
import sys
import time
import subprocess
from pathlib import Path
from typing import Dict, List, Optional

# Import rustkmer classes correctly
from rustkmer import KmerCounter, Database


class Colors:
    """ANSI color codes for terminal output"""
    RED = '\033[0;31m'
    GREEN = '\033[0;32m'
    YELLOW = '\033[1;33m'
    BLUE = '\033[0;34m'
    NC = '\033[0m'  # No Color


def print_header(title: str):
    """Print a formatted header"""
    print(f"{Colors.BLUE}=== {title} ==={Colors.NC}")


def print_success(message: str):
    """Print a success message"""
    print(f"{Colors.GREEN}✓ {message}{Colors.NC}")


def print_info(message: str):
    """Print an info message"""
    print(f"{Colors.YELLOW}→ {message}{Colors.NC}")


def print_error(message: str):
    """Print an error message"""
    print(f"{Colors.RED}✗ {message}{Colors.NC}")


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


def format_file_size(size_bytes: int) -> str:
    """Format file size in human readable format"""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size_bytes < 1024.0:
            return f"{size_bytes:.1f}{unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.1f}TB"


def basic_counting(data_path: Path, output_dir: Path, kmer_size: int = 7):
    """Demonstrate basic k-mer counting"""
    print_header("Basic K-mer Counting")

    output_file = output_dir / f"demo_k{kmer_size}_basic.rkdb"

    print_info(f"Counting k-mers with k={kmer_size}...")

    start_time = time.time()

    try:
        # Create KmerCounter and process the file
        counter = KmerCounter(k=kmer_size, canonical=False, threads=1)
        counter.count_file(str(data_path))

        # Save to database (compression=False for current version)
        counter.save_to_database(str(output_file), False)

        end_time = time.time()

        if output_file.exists():
            file_size = output_file.stat().st_size
            print_success(f"Created database: {output_file.name} ({format_file_size(file_size)})")
            print_info(f"Processing time: {end_time - start_time:.2f} seconds")

            # Get statistics from counter
            unique_kmers = counter.get_unique_count()
            total_kmers = counter.get_total_count()

            print_info(f"Total k-mers counted: {total_kmers:,}")
            print_info(f"Unique k-mers: {unique_kmers:,}")

            return str(output_file)
        else:
            print_error("Failed to create database")
            return None

    except Exception as e:
        print_error(f"Error during k-mer counting: {e}")
        return None


def threaded_counting(data_path: Path, output_dir: Path, kmer_size: int = 7):
    """Demonstrate multi-threaded k-mer counting"""
    print_header("Multi-threaded K-mer Counting")

    thread_counts = [1, 2, 4]
    results = []

    for thread_count in thread_counts:
        output_file = output_dir / f"demo_k{kmer_size}_threads_{thread_count}.rkdb"

        print_info(f"Counting with {thread_count} thread(s)...")

        start_time = time.time()

        try:
            counter = KmerCounter(k=kmer_size, canonical=False, threads=thread_count)
            counter.count_file(str(data_path))
            counter.save_to_database(str(output_file), False)

            end_time = time.time()

            if output_file.exists():
                file_size = output_file.stat().st_size
                unique_kmers = counter.get_unique_count()
                total_kmers = counter.get_total_count()

                result = {
                    'threads': thread_count,
                    'file_size': file_size,
                    'processing_time': end_time - start_time,
                    'total_kmers': total_kmers,
                    'unique_kmers': unique_kmers,
                    'file_path': str(output_file)
                }
                results.append(result)

                print_success(f"Created database with {thread_count} threads: {format_file_size(file_size)}")
                print_info(f"Processing time: {end_time - start_time:.2f} seconds")
                if end_time - start_time > 0:
                    print_info(f"K-mers/second: {int(total_kmers / (end_time - start_time)):,}")
                print_info(f"Unique k-mers: {unique_kmers:,}")
            else:
                print_error(f"Failed to create database with {thread_count} threads")

        except Exception as e:
            print_error(f"Error with {thread_count} threads: {e}")

    # Performance comparison
    if len(results) > 1:
        print_info("Threading Performance Comparison:")
        for result in results:
            print(f"  {result['threads']} threads: {result['processing_time']:.2f}s ({result['total_kmers']:,} k-mers)")

        # Find best performance
        best_result = min(results, key=lambda x: x['processing_time'])
        print_success(f"Best performance: {best_result['threads']} threads ({best_result['processing_time']:.2f}s)")


def canonical_comparison(data_path: Path, output_dir: Path, kmer_size: int = 7):
    """Demonstrate canonical vs non-canonical k-mer counting"""
    print_header("Canonical vs Non-canonical K-mer Counting")

    # Non-canonical counting
    print_info("Counting non-canonical k-mers...")
    start_time = time.time()

    try:
        non_canonical_counter = KmerCounter(k=kmer_size, canonical=False, threads=4)
        non_canonical_counter.count_file(str(data_path))
        non_canonical_file = output_dir / f"demo_k{kmer_size}_noncanonical.rkdb"
        non_canonical_counter.save_to_database(str(non_canonical_file), False)

        non_canonical_time = time.time() - start_time
        non_canonical_unique = non_canonical_counter.get_unique_count()
        non_canonical_total = non_canonical_counter.get_total_count()

        # Canonical counting
        print_info("Counting canonical k-mers...")
        start_time = time.time()

        canonical_counter = KmerCounter(k=kmer_size, canonical=True, threads=4)
        canonical_counter.count_file(str(data_path))
        canonical_file = output_dir / f"demo_k{kmer_size}_canonical.rkdb"
        canonical_counter.save_to_database(str(canonical_file), False)

        canonical_time = time.time() - start_time
        canonical_unique = canonical_counter.get_unique_count()
        canonical_total = canonical_counter.get_total_count()

        # Compare results
        print_info("Non-canonical database stats:")
        print(f"  Unique k-mers: {non_canonical_unique:,}")
        print(f"  Total k-mers: {non_canonical_total:,}")
        print(f"  Processing time: {non_canonical_time:.2f}s")

        print_info("Canonical database stats:")
        print(f"  Unique k-mers: {canonical_unique:,}")
        print(f"  Total k-mers: {canonical_total:,}")
        print(f"  Processing time: {canonical_time:.2f}s")

        # File size comparison
        if non_canonical_file.exists() and canonical_file.exists():
            non_canonical_size = non_canonical_file.stat().st_size
            canonical_size = canonical_file.stat().st_size

            print_info("Database size comparison:")
            print(f"  Non-canonical: {format_file_size(non_canonical_size)}")
            print(f"  Canonical:    {format_file_size(canonical_size)}")

            if non_canonical_size > canonical_size:
                reduction = (non_canonical_size - canonical_size) * 100.0 / float(non_canonical_size)
                print_success(f"Canonical mode reduces database size by {reduction:.1f}%")

            return {
                'non_canonical': {
                    'file': str(non_canonical_file),
                    'size': non_canonical_size,
                    'unique_kmers': non_canonical_unique,
                    'total_kmers': non_canonical_total,
                    'time': non_canonical_time
                },
                'canonical': {
                    'file': str(canonical_file),
                    'size': canonical_size,
                    'unique_kmers': canonical_unique,
                    'total_kmers': canonical_total,
                    'time': canonical_time
                }
            }

    except Exception as e:
        print_error(f"Error in canonical comparison: {e}")
        return None


def export_functionality(db_file: str, output_dir: Path, kmer_size: int = 7):
    """Demonstrate database export functionality"""
    print_header("Database Export Functionality")

    if not os.path.exists(db_file):
        print_error(f"Database file not found: {db_file}")
        return None

    try:
        # Load database using correct pattern
        print_info("Loading database for export...")
        db = Database()
        db.load(db_file)

        # Get database stats for export
        export_file = output_dir / f"demo_k{kmer_size}_export.txt"

        start_time = time.time()

        # Get database stats
        stats = db.get_stats()

        # Sample some k-mers for export
        sample_kmers = [
            "ACGTACG", "GCTAGCT", "TATATAT", "CGCGCGC", "AAAAAAA",
            "CCCCCCC", "GGGGGGG", "TTTTTTT", "ATGCATG", "CGATCGA"
        ]

        # Query sample k-mers
        sample_results = []
        for kmer in sample_kmers:
            result = db.query(kmer)
            if result.found:
                sample_results.append((kmer, result.count))

        end_time = time.time()

        # Write to file in kmer:count format
        with open(export_file, 'w') as f:
            f.write(f"# RustKmer Database Export\n")
            f.write(f"# Database: {db_file}\n")
            f.write(f"# K-mer size: {stats.kmer_size}\n")
            f.write(f"# Total k-mers: {stats.total_kmers:,}\n")
            f.write(f"# Uses memory mapping: {stats.uses_memory_mapping}\n")
            f.write(f"# Canonical: {stats.canonical}\n")
            f.write(f"# Exported sample k-mers with counts > 0\n")
            f.write(f"# Format: KMER\tCOUNT\n")
            f.write("=" * 50 + "\n")

            # Sort by count descending
            sample_results.sort(key=lambda x: x[1], reverse=True)

            for kmer, count in sample_results:
                f.write(f"{kmer}\t{count}\n")

        if export_file.exists():
            export_size = export_file.stat().st_size
            line_count = len(sample_results)

            print_success(f"Exported database to: {export_file.name}")
            print_info(f"Export size: {format_file_size(export_size)}")
            print_info(f"Total k-mers exported: {line_count:,}")
            print_info(f"Export time: {end_time - start_time:.2f}s")

            # Show first few lines
            with open(export_file, 'r') as f:
                lines = f.readlines()[:10]
            print_info("Sample of exported k-mers:")
            for line in lines:
                if line.strip() and not line.startswith('#'):
                    print(f"  {line.strip()}")

            return str(export_file)
        else:
            print_error("Failed to export database")
            return None

    except Exception as e:
        print_error(f"Error during export: {e}")
        return None


def performance_summary(output_dir: Path, kmer_size: int = 7):
    """Display performance summary"""
    print_header("Performance Summary")

    # List created files
    db_files = list(output_dir.glob(f"demo_k{kmer_size}_*.rkdb"))

    if not db_files:
        print_info("No database files found for summary")
        return

    print_info(f"Files created in {output_dir}:")
    for db_file in db_files:
        file_size = db_file.stat().st_size
        print(f"  {db_file.name:30} {format_file_size(file_size):>10}")

    print_info("Quick stats comparison:")
    for db_file in db_files:
        try:
            db = Database()
            db.load(str(db_file))
            stats = db.get_stats()
            print(f"  {db_file.name:25}: {stats.total_kmers:,} total k-mers")
        except Exception as e:
            print(f"  {db_file.name:25}: Error reading database ({e})")


def main():
    """Main execution function"""
    print_header("RustKmer Python API K-mer Counting Examples")

    # Configuration
    kmer_size = 7
    data_path = get_data_path()
    output_dir = get_output_dir()

    print(f"Data: {data_path}")
    if data_path.exists():
        print(f"Data size: {format_file_size(data_path.stat().st_size)}")
    print(f"K-mer size: {kmer_size}")
    print(f"Output: {output_dir}")
    print()

    # Run all demonstrations
    basic_counting(data_path, output_dir, kmer_size)
    print()

    threaded_counting(data_path, output_dir, kmer_size)
    print()

    canonical_results = canonical_comparison(data_path, output_dir, kmer_size)
    print()

    # Use a basic database file for export
    basic_db_file = str(output_dir / f"demo_k{kmer_size}_basic.rkdb")
    if os.path.exists(basic_db_file):
        export_functionality(basic_db_file, output_dir, kmer_size)
        print()

    performance_summary(output_dir, kmer_size)
    print()

    print_header("Examples Completed Successfully!")
    print_success(f"All databases created with k={kmer_size}")
    print_info("You can now query these databases using:")
    print(f"  python -c \"from rustkmer import Database; db=Database(); db.load('{basic_db_file}'); print(db.query('ACGTACG').count)\"")
    print_info("Or use the CLI query examples")

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