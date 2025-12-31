#!/usr/bin/env python3
"""
Example: Advanced rustkmer Features

This example showcases advanced capabilities of the rustkmer Python API:
- Database dumping (streaming vs string output)
- Memory-efficient iteration with limits
- JSON serialization of results
- K-mer validation modes (strict vs lenient)
- Canonical k-mer representation
- Database metadata exploration
- Custom error handling strategies

It demonstrates how to use rustkmer for complex bioinformatics workflows.
"""

import sys
import json
import time
from pathlib import Path
from typing import Iterator, Dict, List, Any

# Add rustkmer to path for development
sys.path.insert(0, str(Path(__file__).parent.parent))

from rustkmer import Database
from rustkmer.query import QueryResult
from rustkmer.stats import DatabaseStats
from rustkmer.utils import validate_kmer, canonical_kmer, run_rustkmer_command


def print_header(title):
    """Print a formatted header."""
    print(f"\n{'='*80}")
    print(f" {title}")
    print(f"{'='*80}")


def print_section(title):
    """Print a formatted section header."""
    print(f"\n--- {title} ---")


def demo_database_dumping():
    """Demonstrate different database dumping approaches."""
    print_header("Database Dumping Demo")

    test_data_dir = Path(__file__).parent.parent / "tests" / "test_data"
    db_path = test_data_dir / "tiny_test.rkdb"

    if not db_path.exists():
        print(f"❌ Test database not found: {db_path}")
        return

    print(f"Using database: {db_path.name}")

    with Database(str(db_path)) as db:
        print_section("Method 1: Dump as String")
        print("Retrieving all k-mers as a single string...")

        start_time = time.time()
        dump_string = db.dump(as_string=True)
        string_time = time.time() - start_time

        lines = dump_string.strip().split('\n')
        print(f"✓ Retrieved {len(lines)} k-mers in {string_time:.3f} seconds")
        print("Sample lines:")
        for i, line in enumerate(lines[:5]):
            kmer, count = line.strip().split('\t')
            print(f"  {i+1}. {kmer}: {count}")
        if len(lines) > 5:
            print(f"  ... and {len(lines) - 5} more")

        print_section("Method 2: Dump as Iterator (Memory Efficient)")
        print("Iterating over k-mers with memory-efficient streaming...")

        start_time = time.time()
        count = 0
        sample_results = []

        for result in db.dump(as_string=False, limit=20):
            count += 1
            if count <= 5:
                sample_results.append(f"{result.kmer}: {result.count}")

        iterator_time = time.time() - start_time

        print(f"✓ Processed {count} k-mers in {iterator_time:.3f} seconds")
        print("Sample results:")
        for i, result in enumerate(sample_results):
            print(f"  {i+1}. {result}")

        print_section("Method 3: Limited Dump")
        print("Retrieving first 10 k-mers...")

        limited_results = list(db.dump(as_string=False, limit=10))
        print(f"✓ Retrieved {len(limited_results)} k-mers")

        # Show data in different formats
        print_section("Result Data Formats")
        first_result = limited_results[0] if limited_results else None

        if first_result:
            print(f"QueryResult object: {first_result}")
            print(f"Dictionary format: {first_result.to_dict()}")
            print(f"JSON format: {first_result.to_json()}")


def demo_kmer_validation():
    """Demonstrate k-mer validation modes and canonical representation."""
    print_header("K-mer Validation & Canonical Representation")

    print_section("K-mer Validation Modes")

    # Test cases for validation
    test_cases = [
        ("ATCGATC", "Valid 7-mer"),
        ("atcgatc", "Valid 7-mer (lowercase)"),
        ("AAAAAAA", "Valid 7-mer (all A's)"),
        ("ATCGX", "Invalid character X"),
        ("ATCGATCG", "Wrong length (8-mer)"),
        ("ATCG", "Wrong length (4-mer)"),
        ("", "Empty string"),
        ("AT CGA", "Contains space"),
        ("1234567", "Contains numbers"),
    ]

    kmer_size = 7

    print(f"Testing k-mers (expected k-mer size: {kmer_size})")
    print(f"{'K-mer':<12} {'Strict':<8} {'Lenient':<10} {'Canonical':<12} {'Notes'}")
    print("-" * 70)

    for kmer, description in test_cases:
        # Test strict validation
        try:
            strict_result = validate_kmer(kmer, kmer_size=kmer_size, strict=True)
            strict_status = "✓"
        except Exception as e:
            strict_status = f"❌ {type(e).__name__}"

        # Test lenient validation
        try:
            lenient_result = validate_kmer(kmer, kmer_size=kmer_size, strict=False)
            if lenient_result is None:
                lenient_status = "None"
            else:
                lenient_status = f"✓ {lenient_result}"
        except Exception as e:
            lenient_status = f"❌ {type(e).__name__}"

        # Calculate canonical if valid
        try:
            canonical = canonical_kmer(kmer.upper() if isinstance(kmer, str) else kmer)
            canonical_str = f"{canonical}"
        except:
            canonical_str = "N/A"

        print(f"{kmer:<12} {strict_status:<8} {lenient_status:<10} {canonical_str:<12} {description}")

    print_section("Canonical K-mer Pairs")
    print("Demonstrating that k-mers and their reverse complements have the same canonical:")

    kmer_pairs = [
        ("ATCGATC", "GATCGAT"),  # Reverse complement pair
        ("AAAAAAA", "TTTTTTT"),  # All A/T pair
        ("GCCGCGG", "CCGCGCC"),  # G/C rich pair
    ]

    for kmer1, kmer2 in kmer_pairs:
        try:
            canon1 = canonical_kmer(kmer1)
            canon2 = canonical_kmer(kmer2)
            match = "✓" if canon1 == canon2 else "❌"
            print(f"  {kmer1} <-> {kmer2}: {canon1} {match}")
        except Exception as e:
            print(f"  {kmer1} <-> {kmer2}: Error - {e}")


def demo_json_serialization():
    """Demonstrate JSON serialization capabilities."""
    print_header("JSON Serialization Demo")

    test_data_dir = Path(__file__).parent.parent / "tests" / "test_data"
    db_path = test_data_dir / "small_test.rkdb"

    if not db_path.exists():
        print(f"❌ Test database not found: {db_path}")
        return

    with Database(str(db_path)) as db:
        print_section("Query Result Serialization")

        # Query some k-mers
        test_kmers = ["AAAAAAA", "TTTTTTT", "ATCGATC", "GCCGCGG"]
        results = db.query_batch(test_kmers)

        print(f"Serializing {len(results)} query results...")

        # Method 1: Individual result serialization
        print("\n1. Individual JSON serialization:")
        for kmer, result in results.items():
            json_str = result.to_json()
            print(f"   {kmer}: {json_str}")

        # Method 2: Batch serialization
        print("\n2. Batch serialization:")
        batch_data = {
            'database': str(db_path.name),
            'kmer_size': db.kmer_size,
            'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
            'results': {kmer: result.to_dict() for kmer, result in results.items()}
        }

        batch_json = json.dumps(batch_data, indent=2)
        print(f"   Batch JSON ({len(batch_json)} characters):")
        print("   " + "\n   ".join(batch_json.split('\n')[:10]))
        if len(batch_json.split('\n')) > 10:
            print("   ... (truncated)")

        print_section("Database Statistics Serialization")

        stats = db.stats()
        stats_dict = stats.to_dict()
        stats_json = json.dumps(stats_dict, indent=2)

        print(f"Database statistics as JSON:")
        print(stats_json)

        # Demonstrate deserialization
        print_section("Deserialization")
        loaded_stats = DatabaseStats.from_dict(json.loads(stats_json))
        print(f"✓ Loaded stats: k={loaded_stats.kmer_size}, unique={loaded_stats.unique_kmers}")
        print(f"   Average count: {loaded_stats.average_count:.2f}")


def demo_database_metadata():
    """Demonstrate comprehensive database metadata exploration."""
    print_header("Database Metadata Exploration")

    test_data_dir = Path(__file__).parent.parent / "tests" / "test_data"

    # Compare metadata across all databases
    databases = [
        "tiny_test.rkdb",
        "small_test.rkdb",
        "small_test_k33_C.rkdb",
        "medium_test.rkdb",
        "large_test.rkdb"
    ]

    all_metadata = []

    print_section("Database Metadata Comparison")
    print(f"{'Database':<20} {'k':<4} {'Unique':<8} {'Total':<10} {'Min':<4} {'Max':<6} {'Avg':<6} {'Size':<8} {'Version'}")
    print("-" * 85)

    for db_name in databases:
        db_path = test_data_dir / db_name

        if not db_path.exists():
            print(f"{db_name:<20} {'N/A':<4} {'File not found':<46}")
            continue

        try:
            with Database(str(db_path)) as db:
                stats = db.stats()
                size_kb = stats.file_size / 1024 if stats.file_size > 0 else 0
                avg_count = f"{stats.average_count:.1f}" if stats.average_count > 0 else "0.0"

                print(f"{db_name:<20} {stats.kmer_size:<4} {stats.unique_kmers:<8} "
                      f"{stats.total_counts:<10} {stats.min_count:<4} {stats.max_count:<6} "
                      f"{avg_count:<6} {size_kb:<8.1f} {stats.format_version}")

                # Collect metadata for detailed analysis
                metadata = {
                    'name': db_name,
                    'stats': stats.to_dict(),
                    'path': str(db_path)
                }
                all_metadata.append(metadata)

        except Exception as e:
            print(f"{db_name:<20} {'Error':<4} {str(e):<46}")

    # Detailed analysis
    if all_metadata:
        print_section("Metadata Analysis")

        # Database with most k-mers
        max_unique = max(all_metadata, key=lambda m: m['stats']['unique_kmers'])
        print(f"Database with most unique k-mers: {max_unique['name']} "
              f"({max_unique['stats']['unique_kmers']:,})")

        # Database with highest counts
        max_total = max(all_metadata, key=lambda m: m['stats']['total_counts'])
        print(f"Database with highest total count: {max_total['name']} "
              f"({max_total['stats']['total_counts']:,})")

        # Special k=33 database
        k33_db = next((m for m in all_metadata if m['stats']['kmer_size'] == 33), None)
        if k33_db:
            print(f"Special k=33 database: {k33_db['name']} "
                  f"({k33_db['stats']['unique_kmers']:,} k-mers)")

        # Size distribution
        total_size = sum(m['stats']['file_size'] for m in all_metadata)
        print(f"\nTotal storage across all databases: {total_size / 1024:.1f} KB")


def demo_advanced_error_handling():
    """Demonstrate sophisticated error handling strategies."""
    print_header("Advanced Error Handling Strategies")

    print_section("Strategy 1: Graceful Degradation")

    test_data_dir = Path(__file__).parent.parent / "tests" / "test_data"
    db_path = test_data_dir / "tiny_test.rkdb"

    # Mix of valid and problematic k-mers
    test_kmers = [
        "AAAAAAA",      # Valid
        "ATCGATC",      # Valid
        "ATCGX",        # Invalid character
        "ATCGATCG",     # Wrong length
        "",             # Empty
        "GCCGCGG",      # Valid
        "toolongkkkkk", # Too long
    ]

    print(f"Processing {len(test_kmers)} k-mers with graceful degradation:")

    if db_path.exists():
        results = {}
        errors = {}

        with Database(str(db_path)) as db:
            for kmer in test_kmers:
                try:
                    result = db.query(kmer, validate_strict=True)
                    results[kmer] = result
                except Exception as e:
                    errors[kmer] = {
                        'error_type': type(e).__name__,
                        'error_message': str(e)
                    }

        print(f"✓ Successfully processed {len(results)} k-mers")
        print(f"⚠ Encountered errors with {len(errors)} k-mers")

        if results:
            print("\nSuccessful queries:")
            for kmer, result in results.items():
                print(f"  {kmer}: count={result.count}")

        if errors:
            print("\nError details:")
            for kmer, error in errors.items():
                print(f"  {kmer!r}: {error['error_type']} - {error['error_message']}")

    print_section("Strategy 2: Retry with Different Validation")

    print("Demonstrating retry logic with different validation modes:")

    retry_results = {}

    if db_path.exists():
        with Database(str(db_path)) as db:
            for kmer in test_kmers:
                success = False
                attempts = []

                # Attempt 1: Strict validation
                try:
                    result = db.query(kmer, validate_strict=True)
                    attempts.append("Strict: ✓")
                    retry_results[kmer] = result
                    success = True
                except Exception as e:
                    attempts.append(f"Strict: ❌ {type(e).__name__}")

                if not success:
                    # Attempt 2: Lenient validation
                    try:
                        result = db.query(kmer, validate_strict=False)
                        attempts.append("Lenient: ✓")
                        retry_results[kmer] = result
                        success = True
                    except Exception as e:
                        attempts.append(f"Lenient: ❌ {type(e).__name__}")

                print(f"  {kmer!r}: {' | '.join(attempts)}")

    print_section("Strategy 3: Custom Error Context")

    class KmerQueryContext:
        """Custom error context for k-mer queries."""
        def __init__(self, database_path: str, kmer_size: int):
            self.database_path = database_path
            self.kmer_size = kmer_size
            self.queries_attempted = 0
            self.queries_successful = 0
            self.error_summary = {}

        def query_with_context(self, db: Database, kmer: str) -> QueryResult:
            """Query with full context tracking."""
            self.queries_attempted += 1

            try:
                result = db.query(kmer, validate_strict=True)
                self.queries_successful += 1
                return result
            except Exception as e:
                error_type = type(e).__name__
                if error_type not in self.error_summary:
                    self.error_summary[error_type] = []
                self.error_summary[error_type].append(kmer)
                raise

    # Use custom context
    if db_path.exists():
        context = KmerQueryContext(str(db_path), kmer_size=7)

        with Database(str(db_path)) as db:
            successful_results = {}

            for kmer in test_kmers:
                try:
                    result = context.query_with_context(db, kmer)
                    successful_results[kmer] = result
                except:
                    pass  # Errors tracked in context

        print(f"Query context summary:")
        print(f"  Queries attempted: {context.queries_attempted}")
        print(f"  Queries successful: {context.queries_successful}")
        print(f"  Success rate: {context.queries_successful/context.queries_attempted*100:.1f}%")

        if context.error_summary:
            print(f"  Error breakdown:")
            for error_type, kmers in context.error_summary.items():
                print(f"    {error_type}: {len(kmers)} occurrences")


def demo_cli_integration():
    """Demonstrate integration with rustkmer CLI."""
    print_header("CLI Integration Demo")

    test_data_dir = Path(__file__).parent.parent / "tests" / "test_data"
    db_path = test_data_dir / "tiny_test.rkdb"

    if not db_path.exists():
        print(f"❌ Test database not found: {db_path}")
        return

    print_section("Direct CLI Command Execution")

    try:
        # Use the utility function to run CLI commands
        result = run_rustkmer_command(['stats', str(db_path)])
        print("✓ CLI stats command output:")
        for line in result.split('\n')[:10]:  # Show first 10 lines
            print(f"  {line}")

        # Query specific k-mers via CLI
        test_kmers = ["AAAAAAA", "ATCGATC"]
        print(f"\n✓ CLI query results:")
        for kmer in test_kmers:
            try:
                result = run_rustkmer_command(['query', str(db_path), kmer])
                if result:
                    parts = result.strip().split('\t')
                    if len(parts) >= 2:
                        print(f"  {kmer}: count={parts[1]}")
            except Exception as e:
                print(f"  {kmer}: CLI error - {e}")

    except Exception as e:
        print(f"❌ CLI integration error: {e}")


def main():
    """Run all advanced feature demonstrations."""
    print("RustKmer Python API - Advanced Features Examples")
    print("This example demonstrates advanced capabilities for complex workflows.")

    # Run all demonstrations
    demo_database_dumping()
    demo_kmer_validation()
    demo_json_serialization()
    demo_database_metadata()
    demo_advanced_error_handling()
    demo_cli_integration()

    print_header("Advanced Features Summary")
    print("✓ Database dumping with memory-efficient streaming")
    print("✓ Flexible k-mer validation (strict vs lenient)")
    print("✓ Automatic canonical k-mer representation")
    print("✓ JSON serialization for API integration")
    print("✓ Comprehensive database metadata exploration")
    print("✓ Sophisticated error handling strategies")
    print("✓ Direct CLI integration for advanced use cases")
    print("\nAdvanced Usage Tips:")
    print("- Use streaming dumps for large databases to save memory")
    print("- Implement graceful degradation for robust applications")
    print("- Leverage JSON serialization for web API integration")
    print("- Use validation modes appropriate for your use case")
    print("- Explore database metadata to understand your data")


if __name__ == "__main__":
    main()