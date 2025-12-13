#!/usr/bin/env python3
"""
Example: Basic rustkmer Usage

This example demonstrates the fundamental operations of the rustkmer Python API:
- Loading databases with context managers
- Performing single k-mer queries
- Retrieving database statistics
- Basic error handling

It uses all available test databases to showcase different database sizes and properties.
"""

import sys
from pathlib import Path

# Add rustkmer to path for development
sys.path.insert(0, str(Path(__file__).parent.parent))

from rustkmer import Database, DatabaseError
from rustkmer.exceptions import DatabaseNotFoundError


def print_header(title):
    """Print a formatted header."""
    print(f"\n{'='*60}")
    print(f" {title}")
    print(f"{'='*60}")


def print_section(title):
    """Print a formatted section header."""
    print(f"\n--- {title} ---")


def demo_database_loading():
    """Demonstrate database loading with different approaches."""
    print_header("Database Loading Demo")

    # Path to test data directory
    test_data_dir = Path(__file__).parent.parent / "tests" / "test_data"

    # Available test databases
    databases = [
        ("tiny_test.rkdb", "Tiny database (8KB, quick for testing)"),
        ("small_test.rkdb", "Small database (86KB, good for examples)"),
        ("small_test_k33_C.rkdb", "Special k=33 database (96KB)"),
        ("medium_test.rkdb", "Medium database (160KB)"),
        ("large_test.rkdb", "Large database (164KB)")
    ]

    for db_name, description in databases:
        db_path = test_data_dir / db_name
        print_section(f"Loading {db_name}")
        print(f"Description: {description}")
        print(f"Path: {db_path}")

        if not db_path.exists():
            print(f"❌ Database file not found!")
            continue

        try:
            # Method 1: Direct loading (need to manually close)
            print("\n1. Direct loading:")
            db = Database(str(db_path))
            print(f"   ✓ Database loaded successfully")
            print(f"   ✓ k-mer size: {db.kmer_size}")
            print(f"   ✓ Database is loaded: {db.is_loaded}")
            db.close()
            print(f"   ✓ Database closed")

            # Method 2: Context manager (recommended)
            print("\n2. Context manager (recommended):")
            with Database(str(db_path)) as db:
                print(f"   ✓ Database opened in context manager")
                print(f"   ✓ k-mer size: {db.kmer_size}")
                print(f"   ✓ Database is loaded: {db.is_loaded}")
            print(f"   ✓ Database automatically closed when exiting context")

        except DatabaseNotFoundError as e:
            print(f"❌ Database not found: {e}")
        except DatabaseError as e:
            print(f"❌ Database error: {e}")
        except Exception as e:
            print(f"❌ Unexpected error: {e}")


def demo_single_queries():
    """Demonstrate single k-mer queries."""
    print_header("Single K-mer Query Demo")

    test_data_dir = Path(__file__).parent.parent / "tests" / "test_data"
    db_path = test_data_dir / "tiny_test.rkdb"

    if not db_path.exists():
        print(f"❌ Test database not found: {db_path}")
        return

    print(f"Using database: {db_path.name}")

    # Test k-mers to demonstrate different scenarios
    test_kmers = [
        ("AAAAAAA", "All A's (edge case)"),
        ("TTTTTTT", "All T's (canonical of AAAAAAA)"),
        ("ATCGATC", "Mixed sequence (7-mer)"),
        ("GCCGCGG", "Another mixed sequence"),
        ("NNNNNNN", "Invalid characters (should return 0)"),
        ("ATCGX", "Invalid character + wrong length"),
        ("ATCGATCG", "Wrong length (8-mer for k=7 database)"),
    ]

    with Database(str(db_path)) as db:
        print(f"Database k-mer size: {db.kmer_size}")
        print_section("Query Results")

        for kmer, description in test_kmers:
            print(f"\nQuery: {kmer} ({description})")

            try:
                # Query with strict validation (default)
                result = db.query(kmer)
                print(f"  Result (strict): count={result.count}, canonical={result.canonical}")
            except Exception as e:
                print(f"  Result (strict): ❌ Error = {e}")

            # Query with lenient validation
            try:
                result = db.query(kmer, validate_strict=False)
                print(f"  Result (lenient): count={result.count}, canonical={result.canonical}")
            except Exception as e:
                print(f"  Result (lenient): ❌ Error = {e}")


def demo_database_stats():
    """Demonstrate retrieving database statistics."""
    print_header("Database Statistics Demo")

    test_data_dir = Path(__file__).parent.parent / "tests" / "test_data"

    # Compare statistics across different databases
    databases = ["tiny_test.rkdb", "small_test.rkdb", "medium_test.rkdb", "large_test.rkdb"]

    print_section("Database Comparison")
    print(f"{'Database':<20} {'k-mer':<8} {'Unique':<10} {'Total':<10} {'Min':<5} {'Max':<5} {'Avg':<8}")
    print("-" * 80)

    for db_name in databases:
        db_path = test_data_dir / db_name

        if not db_path.exists():
            continue

        try:
            with Database(str(db_path)) as db:
                stats = db.stats()
                avg_count = f"{stats.average_count:.2f}" if stats.average_count > 0 else "0.00"

                print(f"{db_name:<20} {stats.kmer_size:<8} {stats.unique_kmers:<10} "
                      f"{stats.total_counts:<10} {stats.min_count:<5} {stats.max_count:<5} "
                      f"{avg_count:<8}")
        except Exception as e:
            print(f"{db_name:<20} {'Error':<8} {str(e):<40}")

    # Detailed statistics for one database
    print_section("Detailed Statistics (small_test.rkdb)")
    db_path = test_data_dir / "small_test.rkdb"

    if db_path.exists():
        with Database(str(db_path)) as db:
            stats = db.stats()
            print(f"Database: {db_path.name}")
            print(f"  k-mer size: {stats.kmer_size}")
            print(f"  Unique k-mers: {stats.unique_kmers:,}")
            print(f"  Total counts: {stats.total_counts:,}")
            print(f"  Minimum count: {stats.min_count}")
            print(f"  Maximum count: {stats.max_count}")
            print(f"  Average count: {stats.average_count:.2f}")
            print(f"  File size: {stats.file_size:,} bytes")
            print(f"  Format version: {stats.format_version}")


def demo_error_handling():
    """Demonstrate error handling patterns."""
    print_header("Error Handling Demo")

    print_section("1. Database Not Found Error")
    try:
        db = Database("/nonexistent/path/database.rkdb")
    except DatabaseNotFoundError as e:
        print(f"✓ Caught DatabaseNotFoundError: {e}")
    except Exception as e:
        print(f"❌ Unexpected error type: {type(e).__name__}: {e}")

    print_section("2. Invalid K-mer Handling")
    test_data_dir = Path(__file__).parent.parent / "tests" / "test_data"
    db_path = test_data_dir / "tiny_test.rkdb"

    if db_path.exists():
        with Database(str(db_path)) as db:
            invalid_kmers = [
                ("ATCGX", "Invalid character X"),
                ("", "Empty string"),
                (123, "Integer instead of string"),
                (None, "None value"),
                ("ATCGATCG", "Wrong length (8 for k=7)")
            ]

            for kmer, description in invalid_kmers:
                print(f"\nTesting: {description}")

                # Try with strict validation
                try:
                    result = db.query(kmer, validate_strict=True)
                    print(f"  Strict: Unexpected success - count={result.count}")
                except Exception as e:
                    print(f"  Strict: ✓ Caught {type(e).__name__}: {e}")

                # Try with lenient validation
                try:
                    result = db.query(kmer, validate_strict=False)
                    print(f"  Lenient: ✓ Handled gracefully - count={result.count}")
                except Exception as e:
                    print(f"  Lenient: ❌ Still failed: {type(e).__name__}: {e}")

    print_section("3. Operations on Closed Database")
    if db_path.exists():
        db = Database(str(db_path))
        db.close()

        try:
            db.query("AAAAAAA")
            print("❌ Query on closed database should have failed!")
        except DatabaseError as e:
            print(f"✓ Query blocked: {e}")

        try:
            db.stats()
            print("❌ Stats on closed database should have failed!")
        except DatabaseError as e:
            print(f"✓ Stats blocked: {e}")


def main():
    """Run all basic usage demonstrations."""
    print("RustKmer Python API - Basic Usage Examples")
    print("This example demonstrates fundamental operations of the rustkmer Python API.")

    # Run all demonstrations
    demo_database_loading()
    demo_single_queries()
    demo_database_stats()
    demo_error_handling()

    print_header("Summary")
    print("✓ Database loading with context managers (recommended approach)")
    print("✓ Single k-mer queries with strict and lenient validation")
    print("✓ Database statistics retrieval and comparison")
    print("✓ Proper error handling for common scenarios")
    print("\nNext steps:")
    print("- Try the batch_processing.py example for efficient bulk querying")
    print("- Explore advanced features in advanced_features.py")
    print("- See real-world usage patterns in real_world_analysis.py")


if __name__ == "__main__":
    main()