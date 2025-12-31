#!/usr/bin/env python3
"""
Basic RustKmer Python API Usage Examples

This script demonstrates fundamental operations with RustKmer:
- Database creation and loading
- Basic k-mer queries
- Database statistics
- Context manager usage
"""

from rustkmer import Database, KmerCounter
import tempfile
import os
import sys

def example_1_basic_query():
    """Example 1: Basic database querying."""
    print("=" * 50)
    print("Example 1: Basic Database Querying")
    print("=" * 50)

    # Load existing database (replace with your database path)
    db_path = "example.rkdb"

    if not os.path.exists(db_path):
        print(f"Database file {db_path} not found. Creating a sample database first...")
        create_sample_database(db_path)

    try:
        # Create database object
        db = Database(db_path)

        # Query a k-mer
        kmer = "ATCGATCGATCGATCGATCGATCGATCGATCGATCG"
        result = db.query(kmer)

        print(f"Query k-mer: {kmer}")
        print(f"Found in database: {result.is_present}")
        print(f"Count: {result.count:,}")
        print(f"Canonical form: {result.canonical}")

        # Get database statistics
        stats = db.stats()
        print(f"\nDatabase Statistics:")
        print(f"  K-mer size: {stats.kmer_size}")
        print(f"  Unique k-mers: {stats.unique_kmers:,}")
        print(f"  Total counts: {stats.total_counts:,}")

        # Close database
        db.close()
        print("\nDatabase closed successfully.")

    except Exception as e:
        print(f"Error: {e}")
        return False

    return True


def example_2_context_manager():
    """Example 2: Using context manager (recommended approach)."""
    print("\n" + "=" * 50)
    print("Example 2: Context Manager Usage")
    print("=" * 50)

    db_path = "example.rkdb"

    if not os.path.exists(db_path):
        print(f"Database file {db_path} not found.")
        return False

    # Context manager automatically handles opening/closing
    try:
        with Database(db_path) as db:
            # Multiple queries
            queries = [
                "ATCGATCGATCGATCGATCGATCGATCGATCGATCG",
                "GCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAG",
                "TTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTT",
                "CCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCC",
                "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"  # Likely not found
            ]

            print("Querying multiple k-mers:")
            for i, query in enumerate(queries, 1):
                result = db.query(query)
                status = "✓ Found" if result.is_present else "✗ Not found"
                print(f"  {i:2d}. {query[:20]:20} {status} (count: {result.count:,})")

            # Database statistics
            stats = db.stats()
            print(f"\nDatabase contains {stats.unique_kmers:,} unique k-mers")

        # Database is automatically closed here
        print("Context manager completed successfully.")

    except Exception as e:
        print(f"Error: {e}")
        return False

    return True


def example_3_create_database():
    """Example 3: Creating a database from sequences."""
    print("\n" + "=" * 50)
    print("Example 3: Creating a K-mer Database")
    print("=" * 50)

    # Create sample sequences
    sequences = [
        "ATCGATCGATCGATCGATCGATCGATCGATCGATCG",  # 33 bp
        "GCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAG",  # 33 bp
        "ATCGATCGATCGATCGATCGATCGATCGATCGATCG",  # Duplicate
        "TTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTT",  # Homopolymer T
        "CCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCC"   # Homopolymer C
    ]

    # Create temporary FASTA file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.fasta', delete=False) as f:
        fasta_content = ""
        for i, seq in enumerate(sequences):
            fasta_content += f">sequence_{i+1}\n{seq}\n"
        f.write(fasta_content)
        fasta_file = f.name

    try:
        print(f"Created sample FASTA file: {fasta_file}")
        print("Sample sequences:")
        for i, seq in enumerate(sequences):
            print(f"  Seq {i+1}: {seq}")

        # Count k-mers
        print("\nCounting k-mers...")
        kmer_size = 21  # Use k=21 for demonstration
        counter = KmerCounter(k=kmer_size, canonical=True)
        counter.count_file(fasta_file)

        # Get counting statistics
        total_kmers = counter.get_total_count()
        unique_kmers = counter.get_unique_count()

        print(f"K-mer counting results:")
        print(f"  K-mer size: {kmer_size}")
        print(f"  Total k-mers: {total_kmers:,}")
        print(f"  Unique k-mers: {unique_kmers:,}")
        print(f"  Reduction ratio: {unique_kmers/total_kmers:.4f}")

        # Save database
        db_file = "sample_database.rkdb"
        counter.save_to_database(db_file)

        print(f"\nDatabase saved to: {db_file}")
        print(f"Database file size: {os.path.getsize(db_file) / 1024:.1f} KB")

        # Verify database
        print("\nVerifying created database...")
        with Database(db_file) as db:
            stats = db.stats()
            print(f"Verification successful:")
            print(f"  K-mer size: {stats.kmer_size}")
            print(f"  Unique k-mers: {stats.unique_kmers:,}")

    except Exception as e:
        print(f"Error: {e}")
        return False

    finally:
        # Clean up temporary file
        os.unlink(fasta_file)

    return True


def example_4_error_handling():
    """Example 4: Error handling best practices."""
    print("\n" + "=" * 50)
    print("Example 4: Error Handling")
    print("=" * 50)

    from rustkmer import DatabaseNotFoundError, InvalidKmerError, QueryError

    # Test different error scenarios
    error_scenarios = [
        ("nonexistent.rkdb", DatabaseNotFoundError, "Non-existent database"),
        ("", QueryError, "Empty database path"),
    ]

    for db_path, expected_error, description in error_scenarios:
        print(f"\nTesting: {description}")
        print(f"Database path: '{db_path}'")

        try:
            with Database(db_path) as db:
                result = db.query("ATCGATCGATCGATCGATCGATCGATCGATCGATCG")
                print(f"Unexpected success: {result.count}")

        except DatabaseNotFoundError as e:
            print(f"✓ Expected DatabaseNotFoundError: {e}")
        except InvalidKmerError as e:
            print(f"✓ Expected InvalidKmerError: {e}")
        except QueryError as e:
            print(f"✓ Expected QueryError: {e}")
        except Exception as e:
            print(f"? Unexpected error: {type(e).__name__}: {e}")

    # Test invalid k-mer handling
    print(f"\nTesting: Invalid k-mer handling")
    try:
        with Database("example.rkdb") as db:
            # Try invalid k-mer (wrong characters)
            invalid_kmer = "ATCGXKATCG"  # Contains X and K
            result = db.query(invalid_kmer, validate_strict=True)
            print(f"Unexpected success with invalid k-mer")

    except InvalidKmerError as e:
        print(f"✓ Correctly caught InvalidKmerError: {e.kmer} - {e.reason}")

    # Test non-strict validation
    print(f"\nTesting: Non-strict validation")
    try:
        with Database("example.rkdb") as db:
            invalid_kmer = "ATCGXKATCG"
            result = db.query(invalid_kmer, validate_strict=False)
            print(f"Non-strict validation: count={result.count}, is_present={result.is_present}")

    except Exception as e:
        print(f"Unexpected error in non-strict validation: {e}")

    return True


def create_sample_database(db_path):
    """Create a sample database for demonstration."""
    sequences = [
        "ATCGATCGATCGATCGATCGATCGATCGATCGATCG",
        "GCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAG",
        "ATCGATCGATCGATCGATCGATCGATCGATCGATCG",
    ]

    with tempfile.NamedTemporaryFile(mode='w', suffix='.fasta', delete=False) as f:
        for i, seq in enumerate(sequences):
            f.write(f">sample_{i+1}\n{seq}\n")
        fasta_file = f.name

    try:
        counter = KmerCounter(k=31, canonical=True)
        counter.count_file(fasta_file)
        counter.save_to_database(db_path)

    finally:
        os.unlink(fasta_file)


def main():
    """Run all examples."""
    print("RustKmer Python API - Basic Usage Examples")
    print("===============================================")

    examples = [
        ("Basic Querying", example_1_basic_query),
        ("Context Manager", example_2_context_manager),
        ("Database Creation", example_3_create_database),
        ("Error Handling", example_4_error_handling)
    ]

    results = []
    for name, example_func in examples:
        print(f"\nRunning: {name}")
        try:
            success = example_func()
            results.append((name, success))
        except Exception as e:
            print(f"Example '{name}' failed with error: {e}")
            results.append((name, False))

    # Summary
    print("\n" + "=" * 50)
    print("EXAMPLES SUMMARY")
    print("=" * 50)

    for name, success in results:
        status = "✓ PASSED" if success else "✗ FAILED"
        print(f"{name:20} {status}")

    passed = sum(1 for _, success in results if success)
    total = len(results)

    print(f"\nTotal: {passed}/{total} examples completed successfully")

    if passed == total:
        print("🎉 All examples completed successfully!")
        return 0
    else:
        print("⚠️  Some examples failed. Check the output above for details.")
        return 1


if __name__ == "__main__":
    sys.exit(main())