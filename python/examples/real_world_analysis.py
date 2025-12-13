#!/usr/bin/env python3
"""
Example: Real-world Bioinformatics Analysis with rustkmer

This example demonstrates practical bioinformatics workflows using rustkmer:
- Loading k-mers from FASTA files
- Querying genomic sequences across multiple databases
- Analyzing k-mer frequency distributions
- Comparing different databases
- Exporting results to common formats (CSV, JSON)
- Integration with popular libraries (pandas, matplotlib)

It simulates real genomic analysis scenarios using the provided test data.
"""

import sys
import json
import csv
import time
from pathlib import Path
from typing import List, Dict, Tuple, Optional
from collections import Counter, defaultdict

# Add rustkmer to path for development
sys.path.insert(0, str(Path(__file__).parent.parent))

from rustkmer import Database
from rustkmer.query import QueryResult

# Try to import optional libraries
try:
    import pandas as pd
    HAS_PANDAS = True
except ImportError:
    HAS_PANDAS = False
    print("Note: pandas not available. Install with: pip install pandas")

try:
    import matplotlib.pyplot as plt
    import numpy as np
    HAS_MATPLOTLIB = True
except ImportError:
    HAS_MATPLOTLIB = False
    print("Note: matplotlib not available. Install with: pip install matplotlib")


def print_header(title):
    """Print a formatted header."""
    print(f"\n{'='*80}")
    print(f" {title}")
    print(f"{'='*80}")


def print_section(title):
    """Print a formatted section header."""
    print(f"\n--- {title} ---")


def read_fasta_kmers(fasta_path: Path, kmer_size: int = 7) -> List[str]:
    """
    Extract k-mers from a FASTA file.

    Args:
        fasta_path: Path to FASTA file
        kmer_size: Size of k-mers to extract

    Returns:
        List of unique k-mers found in the file
    """
    kmers = set()

    print(f"Extracting {kmer_size}-mers from {fasta_path.name}...")

    try:
        with open(fasta_path, 'r') as f:
            current_seq = []

            for line in f:
                line = line.strip()
                if line.startswith('>'):
                    # Process previous sequence
                    if current_seq:
                        seq = ''.join(current_seq)
                        for i in range(len(seq) - kmer_size + 1):
                            kmer = seq[i:i + kmer_size]
                            if 'N' not in kmer:  # Skip k-mers with N
                                kmers.add(kmer.upper())
                        current_seq = []
                else:
                    current_seq.append(line)

            # Process last sequence
            if current_seq:
                seq = ''.join(current_seq)
                for i in range(len(seq) - kmer_size + 1):
                    kmer = seq[i:i + kmer_size]
                    if 'N' not in kmer:
                        kmers.add(kmer.upper())

    except FileNotFoundError:
        print(f"❌ FASTA file not found: {fasta_path}")
        return []

    print(f"✓ Extracted {len(kmers)} unique {kmer_size}-mers")
    return list(kmers)


def demo_fasta_analysis():
    """Analyze k-mers from FASTA files."""
    print_header("FASTA File Analysis")

    test_data_dir = Path(__file__).parent.parent / "tests" / "test_data"

    # Available FASTA files
    fasta_files = [
        ("tiny_test.fasta", "Tiny test sequence"),
        ("small_test.fasta", "Small test sequence"),
        ("medium_test.fasta", "Medium test sequence"),
        ("large_test.fasta", "Large test sequence")
    ]

    fasta_results = {}

    for fasta_name, description in fasta_files:
        fasta_path = test_data_dir / fasta_name

        if not fasta_path.exists():
            print(f"❌ FASTA file not found: {fasta_name}")
            continue

        print_section(f"Analyzing {fasta_name}")
        print(f"Description: {description}")

        # Extract k-mers from FASTA
        kmers = read_fasta_kmers(fasta_path, kmer_size=7)

        if kmers:
            # Analyze k-mer composition
            nucleotide_counts = Counter()
            for kmer in kmers:
                nucleotide_counts.update(kmer)

            # Calculate composition percentages
            total = sum(nucleotide_counts.values())
            composition = {nuc: count/total*100 for nuc, count in nucleotide_counts.items()}

            fasta_results[fasta_name] = {
                'kmer_count': len(kmers),
                'kmers': kmers[:100],  # Store first 100 for analysis
                'composition': composition
            }

            print(f"  Total k-mers: {len(kmers):,}")
            print(f"  Nucleotide composition:")
            for nuc, pct in sorted(composition.items()):
                print(f"    {nuc}: {pct:.1f}%")


def demo_database_comparison():
    """Compare k-mer presence across multiple databases."""
    print_header("Cross-Database Comparison")

    test_data_dir = Path(__file__).parent.parent / "tests" / "test_data"

    # Test k-mers from FASTA (using tiny_test if available)
    fasta_path = test_data_dir / "tiny_test.fasta"
    test_kmers = []

    if fasta_path.exists():
        test_kmers = read_fasta_kmers(fasta_path, kmer_size=7)[:50]  # Use 50 for demo
    else:
        # Fallback test k-mers
        test_kmers = [
            "AAAAAAA", "TTTTTTT", "CCCCCC", "GGGGGG",
            "ATCGATC", "GCCGCGG", "GCTAGCT", "ATCGATC",
            "TATATAT", "CGCGCGC", "ATATCGC", "GCATGCA"
        ]

    # Databases to compare
    databases = [
        ("tiny_test.rkdb", "Tiny database"),
        ("small_test.rkdb", "Small database"),
        ("medium_test.rkdb", "Medium database"),
        ("large_test.rkdb", "Large database")
    ]

    print(f"Comparing {len(test_kmers)} k-mers across {len(databases)} databases")

    comparison_results = {}

    for db_name, description in databases:
        db_path = test_data_dir / db_name

        if not db_path.exists():
            print(f"❌ Database not found: {db_name}")
            continue

        print(f"\nQuerying {db_name} ({description})...")

        with Database(str(db_path)) as db:
            results = db.query_batch(test_kmers, max_workers=4)

            comparison_results[db_name] = {
                'description': description,
                'results': results,
                'found_count': sum(1 for r in results.values() if r.count > 0),
                'total_count': sum(r.count for r in results.values())
            }

            found = sum(1 for r in results.values() if r.count > 0)
            print(f"  Found {found}/{len(test_kmers)} k-mers")
            print(f"  Total occurrences: {sum(r.count for r in results.values())}")

    # Summary comparison table
    print_section("Comparison Summary")
    print(f"{'Database':<20} {'Found':<8} {'Coverage':<10} {'Total Counts':<12} {'Avg Count':<10}")
    print("-" * 70)

    for db_name, data in comparison_results.items():
        coverage = data['found_count'] / len(test_kmers) * 100
        avg_count = data['total_count'] / data['found_count'] if data['found_count'] > 0 else 0

        print(f"{db_name:<20} {data['found_count']:<8} {coverage:<10.1f}% "
              f"{data['total_count']:<12} {avg_count:<10.1f}")


def demo_kmer_frequency_analysis():
    """Analyze k-mer frequency distributions."""
    print_header("K-mer Frequency Analysis")

    test_data_dir = Path(__file__).parent.parent / "tests" / "test_data"
    db_path = test_data_dir / "medium_test.rkdb"

    if not db_path.exists():
        print(f"❌ Database not found: {db_path}")
        return

    print(f"Analyzing k-mer frequencies in {db_path.name}")

    with Database(str(db_path)) as db:
        # Sample k-mers for analysis
        print_section("Sampling K-mers")

        sample_results = list(db.dump(as_string=False, limit=1000))
        print(f"✓ Sampled {len(sample_results)} k-mers for analysis")

        # Analyze frequency distribution
        counts = [r.count for r in sample_results]

        print_section("Frequency Statistics")
        print(f"  Total k-mers sampled: {len(counts):,}")
        print(f"  Min count: {min(counts):,}")
        print(f"  Max count: {max(counts):,}")
        print(f"  Mean count: {sum(counts)/len(counts):.2f}")
        print(f"  Median count: {sorted(counts)[len(counts)//2]:.0f}")

        # Categorize k-mers by frequency
        rare = [c for c in counts if c == 1]
        low_freq = [c for c in counts if 2 <= c <= 5]
        medium_freq = [c for c in counts if 6 <= c <= 20]
        high_freq = [c for c in counts if c > 20]

        print_section("Frequency Categories")
        print(f"  Rare (count=1): {len(rare)} ({len(rare)/len(counts)*100:.1f}%)")
        print(f"  Low (2-5): {len(low_freq)} ({len(low_freq)/len(counts)*100:.1f}%)")
        print(f"  Medium (6-20): {len(medium_freq)} ({len(medium_freq)/len(counts)*100:.1f}%)")
        print(f"  High (>20): {len(high_freq)} ({len(high_freq)/len(counts)*100:.1f}%)")

        # Show examples from each category
        examples = {}
        for result in sample_results:
            if result.count == 1 and 'rare' not in examples:
                examples['rare'] = result.kmer
            elif 2 <= result.count <= 5 and 'low' not in examples:
                examples['low'] = result.kmer
            elif 6 <= result.count <= 20 and 'medium' not in examples:
                examples['medium'] = result.kmer
            elif result.count > 20 and 'high' not in examples:
                examples['high'] = result.kmer

            if len(examples) == 4:
                break

        print_section("Example K-mers")
        for category, kmer in examples.items():
            count = next(r.count for r in sample_results if r.kmer == kmer)
            print(f"  {category.capitalize()}: {kmer} (count={count})")

        # Create frequency visualization if matplotlib is available
        if HAS_MATPLOTLIB:
            print_section("Frequency Distribution Plot")
            try:
                # Create histogram
                plt.figure(figsize=(10, 6))

                # Log scale for better visualization
                plt.hist(counts, bins=50, log=True, alpha=0.7, color='skyblue', edgecolor='black')
                plt.xlabel('K-mer Count')
                plt.ylabel('Number of K-mers (log scale)')
                plt.title('K-mer Frequency Distribution')
                plt.grid(True, alpha=0.3)

                # Save plot
                output_path = Path(__file__).parent / "kmer_frequency_distribution.png"
                plt.savefig(output_path, dpi=150, bbox_inches='tight')
                plt.close()

                print(f"✓ Distribution plot saved to: {output_path}")

            except Exception as e:
                print(f"❌ Could not create plot: {e}")


def demo_export_formats():
    """Demonstrate exporting results to different formats."""
    print_header("Export Results to Various Formats")

    test_data_dir = Path(__file__).parent.parent / "tests" / "test_data"
    db_path = test_data_dir / "small_test.rkdb"

    if not db_path.exists():
        print(f"❌ Database not found: {db_path}")
        return

    print(f"Exporting results from {db_path.name}")

    # Collect sample data for export
    with Database(str(db_path)) as db:
        sample_results = list(db.dump(as_string=False, limit=100))
        stats = db.stats()

        print(f"✓ Collected {len(sample_results)} k-mers for export")

    print_section("Export to JSON")

    # Prepare data for export
    export_data = {
        'metadata': {
            'database': str(db_path.name),
            'export_timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
            'kmer_size': stats.kmer_size,
            'total_unique_kmers': stats.unique_kmers,
            'exported_kmers': len(sample_results)
        },
        'kmer_data': [result.to_dict() for result in sample_results],
        'statistics': stats.to_dict()
    }

    # Export to JSON
    json_path = Path(__file__).parent / "rustkmer_export.json"
    with open(json_path, 'w') as f:
        json.dump(export_data, f, indent=2)

    print(f"✓ Exported to JSON: {json_path}")

    # Export to CSV
    print_section("Export to CSV")

    csv_path = Path(__file__).parent / "rustkmer_export.csv"
    with open(csv_path, 'w', newline='') as f:
        writer = csv.writer(f)

        # Write header
        writer.writerow(['kmer', 'count', 'canonical'])

        # Write data
        for result in sample_results:
            writer.writerow([result.kmer, result.count, result.canonical])

    print(f"✓ Exported to CSV: {csv_path}")

    # Export to pandas DataFrame if available
    if HAS_PANDAS:
        print_section("Export to pandas DataFrame")

        df = pd.DataFrame([result.to_dict() for result in sample_results])
        print(f"✓ Created DataFrame with {len(df)} rows and columns: {list(df.columns)}")

        # Show basic statistics
        print("\nDataFrame Statistics:")
        print(df['count'].describe())

        # Export DataFrame to different formats
        excel_path = Path(__file__).parent / "rustkmer_export.xlsx"
        try:
            df.to_excel(excel_path, index=False)
            print(f"✓ Exported to Excel: {excel_path}")
        except ImportError:
            print("   Note: openpyxl not installed for Excel export")

    # Create summary report
    print_section("Create Summary Report")

    report_path = Path(__file__).parent / "rustkmer_report.txt"
    with open(report_path, 'w') as f:
        f.write("RustKmer Database Analysis Report\n")
        f.write("=" * 40 + "\n\n")
        f.write(f"Database: {db_path.name}\n")
        f.write(f"Analysis Date: {time.strftime('%Y-%m-%d %H:%M:%S')}\n\n")

        f.write("Database Statistics:\n")
        f.write(f"  K-mer size: {stats.kmer_size}\n")
        f.write(f"  Unique k-mers: {stats.unique_kmers:,}\n")
        f.write(f"  Total counts: {stats.total_counts:,}\n")
        f.write(f"  Min count: {stats.min_count}\n")
        f.write(f"  Max count: {stats.max_count}\n")
        f.write(f"  Average count: {stats.average_count:.2f}\n\n")

        f.write(f"Export Summary:\n")
        f.write(f"  K-mers exported: {len(sample_results)}\n")
        f.write(f"  Export formats: JSON, CSV")
        if HAS_PANDAS:
            f.write(f", Excel")
        f.write("\n")

    print(f"✓ Created summary report: {report_path}")


def demo_sequence_analysis():
    """Demonstrate practical sequence analysis."""
    print_header("Genomic Sequence Analysis")

    test_data_dir = Path(__file__).parent.parent / "tests" / "test_data"

    # Simulate a genomic analysis workflow
    print_section("Simulating Genomic Analysis Workflow")

    # Step 1: Load database
    db_path = test_data_dir / "large_test.rkdb"
    if not db_path.exists():
        print(f"❌ Database not found: {db_path}")
        return

    print("Step 1: Loading database...")
    with Database(str(db_path)) as db:
        stats = db.stats()
        print(f"  Loaded {db_path.name}")
        print(f"  Database contains {stats.unique_kmers:,} unique {stats.kmer_size}-mers")

        # Step 2: Simulate querying biological sequences
        print_section("Step 2: Querying Biological Sequences")

        # Simulate some biological sequences (promoters, motifs, etc.)
        biological_sequences = {
            "TATA_box_motif": "TATAAA",      # Will be padded/validated
            "GC-rich_region": "GCCGGCGG",
            "AT_rich_region": "ATATATA",
            "Potential_primer": "ATCGATCG",
            "Random_sequence": "GCTAGCT"
        }

        query_results = {}

        for name, seq in biological_sequences.items():
            print(f"\n  Querying {name}: {seq}")

            # Pad or truncate to correct k-mer size
            if len(seq) < stats.kmer_size:
                # Pad with A's
                padded_seq = seq + 'A' * (stats.kmer_size - len(seq))
                print(f"    Padded to: {padded_seq}")
                query_seq = padded_seq
            elif len(seq) > stats.kmer_size:
                # Truncate
                truncated_seq = seq[:stats.kmer_size]
                print(f"    Truncated to: {truncated_seq}")
                query_seq = truncated_seq
            else:
                query_seq = seq

            try:
                result = db.query(query_seq, validate_strict=False)
                query_results[name] = {
                    'original_seq': seq,
                    'query_seq': query_seq,
                    'result': result
                }

                if result.count > 0:
                    print(f"    ✓ Found: count={result.count}, canonical={result.canonical}")
                else:
                    print(f"    - Not found in database")

            except Exception as e:
                print(f"    ❌ Error: {e}")

        # Step 3: Analyze results
        print_section("Step 3: Analyzing Results")

        found_sequences = {name: data for name, data in query_results.items()
                          if data['result'].count > 0}

        print(f"  Sequences found: {len(found_sequences)}/{len(biological_sequences)}")

        if found_sequences:
            print("\n  Found sequences:")
            for name, data in found_sequences.items():
                result = data['result']
                print(f"    {name}:")
                print(f"      Original: {data['original_seq']}")
                print(f"      Query: {data['query_seq']}")
                print(f"      Count: {result.count}")
                print(f"      Canonical: {result.canonical}")

        # Step 4: Calculate similarity scores
        print_section("Step 4: Sequence Similarity Analysis")

        # Group sequences by canonical representation
        canonical_groups = defaultdict(list)
        for name, data in query_results.items():
            canonical = data['result'].canonical
            canonical_groups[canonical].append(name)

        print(f"  Unique canonical groups: {len(canonical_groups)}")

        for canonical, sequences in canonical_groups.items():
            if len(sequences) > 1:
                print(f"    Same canonical ({canonical}): {', '.join(sequences)}")


def main():
    """Run all real-world analysis demonstrations."""
    print("RustKmer Python API - Real-world Analysis Examples")
    print("This example demonstrates practical bioinformatics workflows.")

    if not HAS_PANDAS:
        print("\nNote: Install pandas for enhanced export capabilities:")
        print("  pip install pandas")

    if not HAS_MATPLOTLIB:
        print("\nNote: Install matplotlib for visualization capabilities:")
        print("  pip install matplotlib")

    print("\n" + "="*80)

    # Run all demonstrations
    demo_fasta_analysis()
    demo_database_comparison()
    demo_kmer_frequency_analysis()
    demo_export_formats()
    demo_sequence_analysis()

    print_header("Real-world Analysis Summary")
    print("✓ K-mer extraction from FASTA files")
    print("✓ Cross-database comparison and analysis")
    print("✓ Frequency distribution analysis")
    print("✓ Multi-format export (JSON, CSV, Excel)")
    print("✓ Genomic sequence analysis workflow")
    print("✓ Integration with pandas/matplotlib for data science")
    print("\nProduction Recommendations:")
    print("- Use batch processing for large k-mer sets")
    print("- Implement proper error handling for production workflows")
    print("- Export to formats compatible with your analysis pipeline")
    print("- Leverage pandas for downstream statistical analysis")
    print("- Use matplotlib for publication-quality visualizations")


if __name__ == "__main__":
    main()