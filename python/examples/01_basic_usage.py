#!/usr/bin/env python3
"""
RustKmer Basic Usage Example

This example demonstrates the fundamental operations of RustKmer:
- Creating k-mer counters
- Counting k-mers from strings and files
- Saving and loading databases
- Performing queries

Author: RustKmer Team
"""

import os
import sys
from rustkmer import KmerCounter, Database

def demonstrate_string_counting():
    """Demonstrate k-mer counting from strings"""
    print("=" * 60)
    print("1. K-mer Counting from String")
    print("=" * 60)

    # Test sequence
    sequence = "ATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATC"
    print(f"Sequence: {sequence}")
    print(f"Length: {len(sequence)} bp")

    # Create counter with different k-mer sizes
    k_sizes = [7, 15, 21, 31]

    for k in k_sizes:
        if k <= len(sequence):
            print(f"\n--- k = {k} ---")
            counter = KmerCounter(k=k, canonical=True)
            counter.count_string(sequence)

            total = counter.get_total_count()
            unique = counter.get_unique_count()

            print(f"Total k-mers: {total}")
            print(f"Unique k-mers: {unique}")
            print(f"Reduction ratio: {unique/total:.2f}" if total > 0 else "N/A")

def demonstrate_canonical_vs_non_canonical():
    """Compare canonical and non-canonical k-mer counting"""
    print("\n" + "=" * 60)
    print("2. Canonical vs Non-Canonical K-mers")
    print("=" * 60)

    # Sequence with its reverse complement
    sequence = "ATCGATCG"
    reverse_comp = "CGATCGAT"

    print(f"Sequence: {sequence}")
    print(f"Reverse complement: {reverse_comp}")

    k = 7
    print(f"\nk-mer size: {k}")

    # Non-canonical counting
    print("\n--- Non-Canonical Mode ---")
    counter_nc = KmerCounter(k=k, canonical=False)
    counter_nc.count_string(sequence)
    counter_nc.count_string(reverse_comp)
    print(f"Total k-mers: {counter_nc.get_total_count()}")
    print(f"Unique k-mers: {counter_nc.get_unique_count()}")

    # Canonical counting
    print("\n--- Canonical Mode ---")
    counter_c = KmerCounter(k=k, canonical=True)
    counter_c.count_string(sequence)
    counter_c.count_string(reverse_comp)
    print(f"Total k-mers: {counter_c.get_total_count()}")
    print(f"Unique k-mers: {counter_c.get_unique_count()}")
    print(f"Memory reduction: {counter_nc.get_unique_count() / counter_c.get_unique_count():.2f}x")

def demonstrate_database_operations():
    """Demonstrate database save and load operations"""
    print("\n" + "=" * 60)
    print("3. Database Operations")
    print("=" * 60)

    # Create and populate counter
    k = 21
    sequences = [
        "ATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATC",
        "GCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAGC",
        "CCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCC",
        "GGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGG"
    ]

    counter = KmerCounter(k=k, canonical=True)
    print(f"Counting k-mers from {len(sequences)} sequences (k={k})...")

    for i, seq in enumerate(sequences, 1):
        counter.count_string(seq)
        print(f"  Sequence {i}: {counter.get_total_count()} total, "
              f"{counter.get_unique_count()} unique")

    # Save to database
    db_path = "example_basic.rkdb"
    print(f"\nSaving to database: {db_path}")
    counter.save_to_database(db_path, canonical=True)

    # Verify file was created
    if os.path.exists(db_path):
        size_mb = os.path.getsize(db_path) / 1024 / 1024
        print(f"Database created: {size_mb:.2f} MB")
    else:
        print("Error: Database file not created!")
        return

    # Load and query database
    print(f"\nLoading database: {db_path}")
    db = Database()
    db.load(db_path)

    # Query some k-mers
    test_kmers = [
        sequences[0][:k],  # First k-mer from first sequence
        sequences[1][:k],  # First k-mer from second sequence
        "AAAAAAAAAAAAAAAAAAAAAAAAAAA",  # Not in sequences
    ]

    print("\nQuerying k-mers:")
    for kmer in test_kmers:
        count = db.query(kmer)
        print(f"  {kmer}: {count}")

    # Get database statistics
    stats = db.get_stats()
    print("\nDatabase Statistics:")
    print(f"  Total k-mers: {stats['total_kmers']:,}")
    print(f"  Unique k-mers: {stats['unique_kmers']:,}")
    print(f"  K-mer size: {stats['k_size']}")
    print(f"  Canonical mode: {stats['canonical_mode']}")

    # Clean up
    if os.path.exists(db_path):
        os.remove(db_path)
        print(f"\nCleaned up: {db_path}")

def create_sample_fasta():
    """Create a sample FASTA file for testing"""
    content = """>sample_seq_1
ATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCG
GCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAGCT
CCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCC
>sample_seq_2
GGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGG
AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA
TTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTT"""

    with open("sample.fa", "w") as f:
        f.write(content)
    print("Created sample.fa")

def demonstrate_file_counting():
    """Demonstrate counting k-mers from FASTA files"""
    print("\n" + "=" * 60)
    print("4. File-based K-mer Counting")
    print("=" * 60)

    # Create sample file
    create_sample_fasta()

    # Count k-mers from file
    k = 31
    print(f"\nCounting k-mers from sample.fa (k={k})...")

    counter = KmerCounter(k=k, canonical=True)
    counter.count_file("sample.fa")

    print(f"Total k-mers: {counter.get_total_count():,}")
    print(f"Unique k-mers: {counter.get_unique_count():,}")

    # Save results
    db_path = "sample_counts.rkdb"
    counter.save_to_database(db_path)
    print(f"Results saved to: {db_path}")

    # Clean up
    for file in ["sample.fa", db_path]:
        if os.path.exists(file):
            os.remove(file)
            print(f"Cleaned up: {file}")

def main():
    """Main function to run all demonstrations"""
    print("\nRustKmer Basic Usage Example")
    print("============================\n")

    try:
        # Run demonstrations
        demonstrate_string_counting()
        demonstrate_canonical_vs_non_canonical()
        demonstrate_database_operations()
        demonstrate_file_counting()

        print("\n" + "=" * 60)
        print("All examples completed successfully!")
        print("=" * 60)

    except Exception as e:
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()