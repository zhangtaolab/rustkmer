#!/usr/bin/env python3
"""
Database Operations Examples

This script demonstrates comprehensive database operations:
- Database statistics and metadata
- Database dumping and exporting
- Database backup and migration
- Database comparison and analysis
- Large database handling
"""

from rustkmer import Database, KmerCounter
import os
import sys
import time
import hashlib
import shutil
import json
import pandas as pd
from pathlib import Path
from collections import defaultdict, Counter

def example_1_database_statistics():
    """Example 1: Comprehensive database statistics."""
    print("=" * 60)
    print("Example 1: Comprehensive Database Statistics")
    print("=" * 60)

    db_path = "example.rkdb"

    if not os.path.exists(db_path):
        print(f"Database {db_path} not found. Creating sample database...")
        create_sample_database(db_path)

    try:
        with Database(db_path) as db:
            # Basic statistics
            stats = db.stats()
            print("Basic Statistics:")
            print(f"  K-mer size: {stats.kmer_size}")
            print(f"  Unique k-mers: {stats.unique_kmers:,}")
            print(f"  Total counts: {stats.total_counts:,}")
            print(f"  File size: {stats.file_size:,} bytes")
            print(f"  Format version: {stats.format_version}")

            # Calculate derived statistics
            if stats.unique_kmers > 0:
                avg_count = stats.total_counts / stats.unique_kmers
                compression_ratio = stats.file_size / (stats.unique_kmers * 8)  # Rough estimate
                print(f"\nDerived Statistics:")
                print(f"  Average count per k-mer: {avg_count:.2f}")
                print(f"  Estimated compression ratio: {compression_ratio:.3f}")

            # Sample database content
            print(f"\nSample Database Content:")
            sample_count = 0
            for result in db.dump(limit=10):
                print(f"  {result.kmer}: {result.count:,}")
                sample_count += 1
                if sample_count >= 5:  # Limit output
                    break

            # K-mer length distribution
            print(f"\nK-mer Length Analysis:")
            length_counts = defaultdict(int)
            total_examined = 0

            for result in db.dump(limit=1000):
                length_counts[len(result.kmer)] += 1
                total_examined += 1

            if length_counts:
                print("  Length distribution (from sample):")
                for length in sorted(length_counts.keys()):
                    count = length_counts[length]
                    percentage = count / total_examined * 100
                    print(f"    Length {length}: {count:4d} k-mers ({percentage:5.1f}%)")

    except Exception as e:
        print(f"Error: {e}")
        return False

    return True


def example_2_database_dumping():
    """Example 2: Database dumping and exporting."""
    print("\n" + "=" * 60)
    print("Example 2: Database Dumping and Exporting")
    print("=" * 60)

    db_path = "example.rkdb"

    try:
        with Database(db_path) as db:
            print("Dumping database content...")

            # Count total entries first
            total_entries = 0
            for _ in db.dump():
                total_entries += 1

            print(f"Total database entries: {total_entries:,}")

            # Export to TSV
            tsv_file = "database_export.tsv"
            print(f"\nExporting to TSV file: {tsv_file}")

            start_time = time.time()
            entries_exported = 0

            with open(tsv_file, 'w') as f:
                # Write header
                f.write("kmer\tcount\tcanonical\n")

                # Dump entries (limited for demo)
                for result in db.dump(limit=10000):
                    f.write(f"{result.kmer}\t{result.count}\t{result.canonical}\n")
                    entries_exported += 1

                    # Progress indicator
                    if entries_exported % 1000 == 0:
                        print(f"  Exported {entries_exported:,} entries")

            export_time = time.time() - start_time
            file_size = os.path.getsize(tsv_file)

            print(f"Export completed:")
            print(f"  Entries exported: {entries_exported:,}")
            print(f"  Time: {export_time:.2f} seconds")
            print(f"  File size: {file_size:,} bytes")

            # Export canonical k-mers only (smaller file)
            canonical_file = "database_canonical.tsv"
            print(f"\nExporting canonical k-mers to: {canonical_file}")

            start_time = time.time()
            canonical_exported = 0

            with open(canonical_file, 'w') as f:
                f.write("kmer\tcount\n")

                for result in db.dump(limit=5000, canonical_only=True):
                    f.write(f"{result.kmer}\t{result.count}\n")
                    canonical_exported += 1

            canonical_time = time.time() - start_time
            canonical_size = os.path.getsize(canonical_file)

            print(f"Canonical export completed:")
            print(f"  Entries exported: {canonical_exported:,}")
            print(f"  Time: {canonical_time:.2f} seconds")
            print(f"  File size: {canonical_size:,} bytes")

            # Analysis of exported data
            print(f"\n--- Export Analysis ---")
            print(f"TSV file: {entries_exported:,} entries, {file_size/1024:.1f} KB")
            print(f"Canonical file: {canonical_exported:,} entries, {canonical_size/1024:.1f} KB")
            print(f"Reduction ratio: {canonical_exported/entries_exported:.2%} k-mers")
            print(f"Size reduction: {canonical_size/file_size:.2%} file size")

    except Exception as e:
        print(f"Error: {e}")
        return False

    return True


def example_3_database_backup():
    """Example 3: Database backup with validation."""
    print("\n" + "=" * 60)
    print("Example 3: Database Backup and Validation")
    print("=" * 60)

    original_db = "example.rkdb"
    backup_dir = "database_backups"

    if not os.path.exists(original_db):
        print(f"Original database {original_db} not found.")
        return False

    # Create backup directory
    Path(backup_dir).mkdir(parents=True, exist_ok=True)

    try:
        # Generate backup filename with timestamp
        import datetime
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_file = os.path.join(backup_dir, f"backup_{timestamp}.rkdb")

        print(f"Creating backup: {backup_file}")

        # Calculate original checksum
        def calculate_checksum(file_path):
            """Calculate SHA-256 checksum."""
            sha256_hash = hashlib.sha256()
            with open(file_path, "rb") as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    sha256_hash.update(chunk)
            return sha256_hash.hexdigest()

        # Copy database
        print("Copying database file...")
        shutil.copy2(original_db, backup_file)

        # Calculate checksums
        print("Calculating checksums...")
        original_checksum = calculate_checksum(original_db)
        backup_checksum = calculate_checksum(backup_file)

        print(f"Original checksum: {original_checksum}")
        print(f"Backup checksum: {backup_checksum}")

        # Validate backup integrity
        print("Validating backup integrity...")
        backup_valid = validate_database_integrity(backup_file)
        original_valid = validate_database_integrity(original_db)

        # Create backup metadata
        metadata = {
            'original_file': os.path.abspath(original_db),
            'backup_file': os.path.abspath(backup_file),
            'timestamp': timestamp,
            'original_checksum': original_checksum,
            'backup_checksum': backup_checksum,
            'checksum_match': original_checksum == backup_checksum,
            'original_valid': original_valid,
            'backup_valid': backup_valid,
            'original_size': os.path.getsize(original_db),
            'backup_size': os.path.getsize(backup_file),
            'copy_successful': original_checksum == backup_checksum
        }

        metadata_file = backup_file.replace('.rkdb', '_metadata.json')
        with open(metadata_file, 'w') as f:
            json.dump(metadata, f, indent=2)

        print(f"Backup metadata saved to: {metadata_file}")

        # Validation summary
        print(f"\n--- Backup Validation Summary ---")
        print(f"Checksums match: {'✓' if metadata['checksum_match'] else '✗'}")
        print(f"Original valid: {'✓' if metadata['original_valid'] else '✗'}")
        print(f"Backup valid: {'✓' if metadata['backup_valid'] else '✗'}")
        print(f"Copy successful: {'✓' if metadata['copy_successful'] else '✗'}")

        if metadata['copy_successful'] and metadata['backup_valid']:
            print(f"\n✓ Backup created successfully!")
            print(f"  Original: {metadata['original_size']:,} bytes")
            print(f"  Backup: {metadata['backup_size']:,} bytes")
        else:
            print(f"\n✗ Backup validation failed!")
            return False

    except Exception as e:
        print(f"Error: {e}")
        return False

    return True


def validate_database_integrity(db_path):
    """Validate database integrity and functionality."""
    try:
        with Database(db_path) as db:
            # Test basic functionality
            stats = db.stats()

            # Test query functionality
            test_kmer = "A" * stats.kmer_size if stats.kmer_size else "ATCGATCGATCGATCGATCGATCGATCGATCGATCG"
            result = db.query(test_kmer)

            # Test dump functionality
            dump_results = list(db.dump(limit=10))

        return True

    except Exception as e:
        print(f"Database validation failed: {e}")
        return False


def example_4_database_comparison():
    """Example 4: Compare multiple databases."""
    print("\n" + "=" * 60)
    print("Example 4: Database Comparison")
    print("=" * 60)

    # Create sample databases for comparison
    databases = {
        "sample1.rkdb": ["ATCG" * 10, "GCTA" * 10, "ATCG" * 8 + "GGGG"],
        "sample2.rkdb": ["ATCG" * 10, "GCTA" * 10, "TTTT" * 8 + "CCCC"],
        "sample3.rkdb": ["ATCG" * 10, "GCTA" * 10, "AAAA" * 8 + "TTTT"]
    }

    print("Creating sample databases for comparison...")
    create_sample_databases(databases)

    try:
        # Load all databases
        db_data = {}

        for name, sequences in databases.items():
            print(f"\nLoading {name}...")
            with Database(name) as db:
                stats = db.stats()
                db_data[name] = {
                    'stats': stats,
                    'db': db,
                    'top_kmers': []
                }

                # Get top k-mers
                for result in db.dump(limit=20, canonical_only=True):
                    db_data[name]['top_kmers'].append({
                        'kmer': result.kmer,
                        'count': result.count
                    })

        # Compare statistics
        print(f"\n--- Database Statistics Comparison ---")
        print(f"{'Database':<15} {'K-size':<8} {'Unique':<10} {'Total':<12} {'Size (KB)':<12}")
        print("-" * 65)

        for name, data in db_data.items():
            stats = data['stats']
            size_kb = stats.file_size / 1024
            print(f"{name:<15} {stats.kmer_size:<8} {stats.unique_kmers:<10,} "
                  f"{stats.total_counts:<12,} {size_kb:<12.1f}")

        # Find common and unique k-mers
        print(f"\n--- K-mer Overlap Analysis ---")

        # Extract k-mer sets
        kmer_sets = {}
        for name, data in db_data.items():
            kmer_sets[name] = set(k['kmer'] for k in data['top_kmers'])

        all_kmers = set()
        for kmer_set in kmer_sets.values():
            all_kmers.update(kmer_set)

        # Calculate overlaps
        print(f"Total unique k-mers across all databases: {len(all_kmers)}")

        pairwise_overlaps = {}
        db_names = list(kmer_sets.keys())

        for i, db1 in enumerate(db_names):
            for j, db2 in enumerate(db_names[i+1:], i+1):
                overlap = kmer_sets[db1] & kmer_sets[db2]
                pairwise_overlaps[f"{db1}_vs_{db2}"] = overlap
                print(f"{db1} vs {db2}: {len(overlap)} common k-mers")

        # Find database-specific k-mers
        print(f"\n--- Database-Specific K-mers ---")
        for name, kmer_set in kmer_sets.items():
            specific_kmers = kmer_set - all_kmers
            print(f"{name}: {len(specific_kmers)} database-specific k-mers")

        # Create comparison matrix
        print(f"\n--- K-mer Presence Matrix ---")
        print(f"{'K-mer':<25} " + " | ".join(f"{name:<8}" for name in db_names))
        print("-" * (25 + 9 * len(db_names)))

        # Select representative k-mers for matrix
        sample_kmers = list(all_kmers)[:10]

        for kmer in sample_kmers:
            presence = " | ".join(
                "✓" if kmer in kmer_sets[name] else "✗" for name in db_names
            )
            print(f"{kmer[:25]:25} {presence}")

    except Exception as e:
        print(f"Error: {e}")
        return False

    finally:
        # Clean up sample databases
        for name in databases.keys():
            if os.path.exists(name):
                os.unlink(name)

    return True


def example_5_large_database_handling():
    """Example 5: Efficient handling of large databases."""
    print("\n" + "=" * 60)
    print("Example 5: Large Database Handling")
    print("=" * 60)

    # Create a larger sample database
    large_db_path = "large_sample.rkdb"

    print("Creating larger sample database...")
    create_large_sample_database(large_db_path)

    try:
        with Database(large_db_path) as db:
            stats = db.stats()
            print(f"Large database statistics:")
            print(f"  Unique k-mers: {stats.unique_kmers:,}")
            print(f"  File size: {stats.file_size / (1024*1024):.1f} MB")

            # Memory-efficient processing
            print(f"\n--- Memory-Efficient Processing ---")

            # Process in chunks
            chunk_size = 1000
            total_processed = 0
            high_count_kmers = []
            start_time = time.time()

            for result in db.dump(canonical_only=True):
                total_processed += 1

                # Collect high-count k-mers (example threshold)
                if result.count > 10:
                    high_count_kmers.append({
                        'kmer': result.kmer,
                        'count': result.count
                    })

                # Periodic progress update
                if total_processed % chunk_size == 0:
                    elapsed = time.time() - start_time
                    rate = total_processed / elapsed
                    print(f"  Processed {total_processed:,} k-mers "
                          f"({rate:.1f} k-mers/sec), "
                          f"found {len(high_count_kmers)} high-count k-mers")

                # Limit for demo
                if total_processed >= 10000:
                    print(f"  Stopping at {total_processed:,} k-mers for demo")
                    break

            # Analyze high-count k-mers
            if high_count_kmers:
                high_count_kmers.sort(key=lambda x: x['count'], reverse=True)

                print(f"\n--- High-Count K-mers (count > 10) ---")
                print(f"Total found: {len(high_count_kmers)}")

                for i, kmer_data in enumerate(high_count_kmers[:10], 1):
                    print(f"  {i:2d}. {kmer_data['kmer']}: {kmer_data['count']:,}")

                # Analyze distribution
                counts = [k['count'] for k in high_count_kmers]
                print(f"\nHigh-count distribution:")
                print(f"  Mean: {sum(counts)/len(counts):.1f}")
                print(f"  Median: {sorted(counts)[len(counts)//2]:.1f}")
                print(f"  Max: {max(counts):,}")
                print(f"  Min: {min(counts):,}")

            # Database size estimation
            processing_time = time.time() - start_time
            estimated_total = stats.unique_kmers
            if total_processed > 0:
                estimate_time = (estimated_total / total_processed) * processing_time
                print(f"\n--- Processing Estimates ---")
                print(f"  Processed: {total_processed:,}/{estimated_total:,} k-mers")
                print(f"  Time elapsed: {processing_time:.2f} seconds")
                print(f"  Estimated total time: {estimate_time:.1f} seconds")

    except Exception as e:
        print(f"Error: {e}")
        return False

    finally:
        # Clean up
        if os.path.exists(large_db_path):
            os.unlink(large_db_path)

    return True


def create_sample_database(db_path):
    """Create a simple sample database."""
    sequences = [
        "ATCGATCGATCGATCGATCGATCGATCGATCGATCG",
        "GCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAG",
        "TTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTT",
        "CCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCC"
    ]

    counter = KmerCounter(k=31, canonical=True)
    counter.count_file_list([seq for seq in sequences])
    counter.save_to_database(db_path)


def create_sample_databases(database_configs):
    """Create sample databases for comparison."""
    for db_file, sequences in database_configs.items():
        counter = KmerCounter(k=31, canonical=True)
        counter.count_file_list([seq for seq in sequences])
        counter.save_to_database(db_file)


def create_large_sample_database(db_path):
    """Create a larger sample database for testing."""
    # Generate more sequences with variations
    base_sequence = "ATCGATCGATCGATCGATCGATCGATCGATCGATCG"
    sequences = [base_sequence]

    # Add variations
    for i in range(100):
        # Simple mutations
        seq = list(base_sequence)
        pos = i % len(seq)
        bases = ['A', 'T', 'C', 'G']
        seq[pos] = bases[(bases.index(seq[pos]) + 1) % 4]  # Change base
        sequences.append(''.join(seq))

        # Add some repeats
        if i % 20 == 0:
            sequences.append("ATCG" * 10)

    counter = KmerCounter(k=31, canonical=True)
    counter.count_file_list(sequences)
    counter.save_to_database(db_path)


def main():
    """Run all database operation examples."""
    print("RustKmer Python API - Database Operations Examples")
    print("==============================================")

    examples = [
        ("Database Statistics", example_1_database_statistics),
        ("Database Dumping", example_2_database_dumping),
        ("Database Backup", example_3_database_backup),
        ("Database Comparison", example_4_database_comparison),
        ("Large Database Handling", example_5_large_database_handling)
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
    print("\n" + "=" * 60)
    print("EXAMPLES SUMMARY")
    print("=" * 60)

    for name, success in results:
        status = "✓ PASSED" if success else "✗ FAILED"
        print(f"{name:25} {status}")

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