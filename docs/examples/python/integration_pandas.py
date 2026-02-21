#!/usr/bin/env python3
"""
RustKmer Integration with Pandas Examples

This script demonstrates how to integrate RustKmer with pandas
for data analysis and visualization:
- Creating k-mer count matrices
- Analyzing multiple samples
- Statistical analysis with pandas
- Data visualization
- Exporting results
"""

from pyrustkmer import PyDatabase, LoadMode
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path
import tempfile
import os
import sys

def example_1_kmer_count_matrix():
    """Example 1: Create k-mer count matrix from multiple samples."""
    print("=" * 60)
    print("Example 1: K-mer Count Matrix")
    print("=" * 60)

    # Create sample databases for demonstration
    sample_files = {
        "sample_A.rkdb": ["ATCGATCGATCGATCGATCGATCGATCGATCGATCG"] * 5,
        "sample_B.rkdb": ["GCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAG"] * 5,
        "sample_C.rkdb": ["ATCGATCGATCGATCGATCGATCGATCGATCGATCG"] * 3 +
                         ["GCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAG"] * 2
    }

    print("Creating sample databases...")
    create_sample_databases(sample_files)

    try:
        # Define query k-mers
        query_kmers = [
            "ATCGATCGATCGATCGATCGATCGATCGATCGATCG",
            "GCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAG",
            "TTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTT",
            "CCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCC",
            "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"
        ]

        print(f"Querying {len(query_kmers)} k-mers across {len(sample_files)} samples")

        # Create DataFrame for results
        matrix_data = []

        for sample_name, db_file in sample_files.items():
            sample_row = {'Sample': sample_name}

            db = PyDatabase(db_file, LoadMode.Preload)
                for kmer in query_kmers:
                    try:
                        result = db.query_exact(kmer)
                        sample_row[kmer] = result.count
                    except Exception as e:
                        print(f"Error querying {kmer} in {sample_name}: {e}")
                        sample_row[kmer] = 0

            matrix_data.append(sample_row)

        # Create DataFrame
        df = pd.DataFrame(matrix_data)
        print(f"\nCreated matrix with shape: {df.shape}")
        print("First few rows:")
        print(df.head())

        # Matrix statistics
        print(f"\nMatrix Statistics:")
        print(f"  Total cells: {df.shape[0] * df.shape[1]:,}")
        print(f"  Non-zero cells: {(df.iloc[:, 1:] > 0).sum().sum():,}")
        print(f"  Sparsity: {1 - (df.iloc[:, 1:] > 0).sum().sum() / (df.shape[0] * (df.shape[1] - 1)):.2%}")

        # Column statistics
        print(f"\nK-mer Statistics:")
        for kmer in query_kmers:
            counts = df[kmer]
            print(f"  {kmer[:20]:20}: min={counts.min()}, "
                  f"max={counts.max():,}, mean={counts.mean():.1f}, "
                  f"sum={counts.sum():,}")

        # Row (sample) statistics
        print(f"\nSample Statistics:")
        for _, row in df.iterrows():
            sample_name = row['Sample']
            counts = row.drop('Sample')
            print(f"  {sample_name}: min={counts.min():}, "
                  f"max={counts.max():,}, mean={counts.mean():.1f}, "
                  f"sum={counts.sum():,}")

        return df

    except Exception as e:
        print(f"Error: {e}")
        return None

    finally:
        # Clean up
        for db_file in sample_files.keys():
            if os.path.exists(db_file):
                os.unlink(db_file)


def example_2_presence_absence_matrix():
    """Example 2: Create presence/absence matrix."""
    print("\n" + "=" * 60)
    print("Example 2: Presence/Absence Matrix")
    print("=" * 60)

    # Sample databases
    sample_files = {
        "genome1.rkdb": ["ATCG" * 10] * 5,
        "genome2.rkdb": ["GCTA" * 10] * 5,
        "genome3.rkdb": ["ATCG" * 10] * 3 + ["GCTA" * 10] * 2
    }

    print("Creating sample databases...")
    create_sample_databases(sample_files)

    try:
        # Define k-mers for presence/absence analysis
        kmer_set = [
            "ATCGATCGATCGATCGATCGATCGATCGATCGATCG",
            "GCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAG",
            "TTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTT"
        ]

        # Create presence/absence matrix
        presence_data = []

        for sample_name, db_file in sample_files.items():
            row_data = {'Sample': sample_name}

            db = PyDatabase(db_file, LoadMode.Preload)
                for kmer in kmer_set:
                    result = db.query_exact(kmer)
                    row_data[kmer] = 1 if result.is_present else 0

            presence_data.append(row_data)

        df = pd.DataFrame(presence_data)
        print(f"Created presence/absence matrix: {df.shape}")
        print("\nMatrix (presence = 1, absence = 0):")
        print(df.to_string(index=False))

        # Analysis
        print(f"\nPresence Analysis:")
        kmer_presence = df.iloc[:, 1:].sum()
        for kmer, presence_count in kmer_presence.items():
            print(f"  {kmer[:20]:20}: present in {presence_count}/{len(df)} samples "
                  f"({presence_count/len(df):.1%})")

        # Jaccard similarity between samples
        print(f"\nSample Similarity (Jaccard Index):")
        sample_names = df['Sample'].tolist()
        presence_matrix = df.iloc[:, 1:].values

        similarity_matrix = pd.DataFrame(
            index=sample_names,
            columns=sample_names
        )

        for i, sample1 in enumerate(sample_names):
            for j, sample2 in enumerate(sample_names):
                if i <= j:
                    # Calculate Jaccard similarity
                    set1 = set(np.where(presence_matrix[i] == 1)[0])
                    set2 = set(np.where(presence_matrix[j] == 1)[0])

                    if len(set1) == 0 and len(set2) == 0:
                        similarity = 1.0
                    else:
                        intersection = len(set1 & set2)
                        union = len(set1 | set2)
                        similarity = intersection / union if union > 0 else 0

                    similarity_matrix.loc[sample1, sample2] = similarity
                    similarity_matrix.loc[sample2, sample1] = similarity

        print(similarity_matrix.round(3))

        return df, similarity_matrix

    except Exception as e:
        print(f"Error: {e}")
        return None, None

    finally:
        for db_file in sample_files.keys():
            if os.path.exists(db_file):
                os.unlink(db_file)


def example_3_abundance_analysis():
    """Example 3: K-mer abundance analysis with pandas."""
    print("\n" + "=" * 60)
    print("Example 3: K-mer Abundance Analysis")
    print("=" * 60)

    db_path = "abundance_analysis.rkdb"

    if not os.path.exists(db_path):
        print(f"Database {db_path} not found. Creating sample database...")
        create_abundance_database(db_path)

    try:
        # Collect abundance data
        abundance_data = []
        top_kmers = []

        print("Collecting k-mer abundance data...")
        db = PyDatabase(db_path, LoadMode.Preload)
            for result in db.dump(limit=1000, canonical_only=True):
                abundance_data.append({
                    'kmer': result.kmer,
                    'count': result.count,
                    'gc_content': (result.kmer.count('G') + result.kmer.count('C')) / len(result.kmer),
                    'log_count': np.log10(result.count + 1)
                })

        df = pd.DataFrame(abundance_data)
        print(f"Collected abundance data for {len(df)} k-mers")

        # Basic statistics
        print(f"\nAbundance Statistics:")
        print(f"  Count range: {df['count'].min():,} - {df['count'].max():,}")
        print(f"  Mean count: {df['count'].mean():.1f}")
        print(f"  Median count: {df['count'].median():.1f}")
        print(f"  Standard deviation: {df['count'].std():.1f}")

        print(f"\nGC Content Statistics:")
        print(f"  Range: {df['gc_content'].min():.3f} - {df['gc_content'].max():.3f}")
        print(f"  Mean: {df['gc_content'].mean():.3f} ± {df['gc_content'].std():.3f}")

        # Top k-mers
        top_kmers = df.nlargest(20, 'count')
        print(f"\nTop 20 Most Abundant K-mers:")
        for i, (_, row) in enumerate(top_kmers.iterrows(), 1):
            print(f"  {i:2d}. {row['kmer']:35} | "
                  f"Count: {row['count']:8,} | "
                  f"GC: {row['gc_content']:.2f}")

        # Distribution analysis
        print(f"\nCount Distribution:")
        count_bins = [0, 1, 5, 10, 50, 100, 500, 1000, float('inf')]
        count_labels = ['0', '1', '2-4', '5-9', '10-49', '50-99', '100-499', '500-999', '1000+']

        df['count_bin'] = pd.cut(df['count'], bins=count_bins, labels=count_labels, right=False)
        count_distribution = df['count_bin'].value_counts().sort_index()
        total_kmers = len(df)

        for bin_range, count in count_distribution.items():
            percentage = count / total_kmers * 100
            print(f"  {bin_range:>10}: {count:6d} k-mers ({percentage:5.1f}%)")

        # GC content vs abundance correlation
        correlation = df['count'].corr(df['gc_content'])
        print(f"\nCount vs GC Content Correlation: {correlation:.3f}")

        # Create abundance categories
        df['abundance_category'] = pd.cut(
            df['count'],
            bins=[0, 1, 10, 100, float('inf')],
            labels=['rare', 'low', 'medium', 'high', 'very_high']
        )

        print(f"\nAbundance Categories:")
        for category, group in df.groupby('abundance_category'):
            print(f"  {category:12}: {len(group):6d} k-mers "
                  f"({len(group)/len(df)*100:5.1f}%)")

        return df

    except Exception as e:
        print(f"Error: {e}")
        return None

    finally:
        if os.path.exists(db_path):
            os.unlink(db_path)


def example_4_visualization():
    """Example 4: Data visualization with matplotlib and seaborn."""
    print("\n" + "=" * 60)
    print("Example 4: Data Visualization")
    print("=" * 60)

    # Get abundance data
    df = example_3_abundance_analysis()
    if df is None:
        print("Could not get abundance data for visualization.")
        return False

    try:
        # Set up plotting style
        plt.style.use('seaborn-v0_8')
        sns.set_palette("husl")

        # Create figure with multiple subplots
        fig, axes = plt.subplots(2, 3, figsize=(18, 12))
        fig.suptitle('RustKmer K-mer Analysis with Pandas', fontsize=16)

        # Plot 1: Count distribution histogram
        axes[0, 0].hist(df['count'], bins=50, alpha=0.7, edgecolor='black')
        axes[0, 0].set_xlabel('K-mer Count')
        axes[0, 0].set_ylabel('Frequency')
        axes[0, 0].set_title('K-mer Count Distribution')
        axes[0, 0].set_xscale('log')
        axes[0, 0].grid(True, alpha=0.3)

        # Plot 2: GC content distribution
        axes[0, 1].hist(df['gc_content'], bins=20, alpha=0.7, edgecolor='black')
        axes[0, 1].set_xlabel('GC Content')
        axes[0, 1].set_ylabel('Frequency')
        axes[0, 1].set_title('GC Content Distribution')
        axes[0, 1].grid(True, alpha=0.3)

        # Plot 3: Count vs GC content scatter
        scatter = axes[0, 2].scatter(
            df['gc_content'], df['count'],
            alpha=0.6, s=10
        )
        axes[0, 2].set_xlabel('GC Content')
        axes[0, 2].set_ylabel('Count')
        axes[0, 2].set_title('Count vs GC Content')
        axes[0, 2].set_xscale('linear')
        axes[0, 2].set_yscale('log')

        # Add regression line
        z = np.polyfit(df['gc_content'], df['log_count'], 1)
        p = np.poly1d(z)
        axes[0, 2].plot(df['gc_content'], p(df['gc_content']), "r--", alpha=0.8)
        axes[0, 2].grid(True, alpha=0.3)

        # Plot 4: Abundance categories bar chart
        category_counts = df['abundance_category'].value_counts()
        bars = axes[1, 0].bar(category_counts.index, category_counts.values, alpha=0.7)
        axes[1, 0].set_xlabel('Abundance Category')
        axes[1, 0].set_ylabel('Number of K-mers')
        axes[1, 0].set_title('K-mer Abundance Categories')
        axes[1, 0].tick_params(axis='x', rotation=45)

        # Add value labels on bars
        for bar, count in zip(bars, category_counts.values):
            axes[1, 0].text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.5,
                           str(count), ha='center', va='bottom')

        # Plot 5: Box plot of counts by GC content quintiles
        df['gc_quintile'] = pd.qcut(df['gc_content'], 5, labels=['Q1', 'Q2', 'Q3', 'Q4', 'Q5'])
        df.boxplot(column='count', by='gc_quintile', ax=axes[1, 1])
        axes[1, 1].set_xlabel('GC Content Quintile')
        axes[1, 1].set_ylabel('Count')
        axes[1, 1].set_title('Count Distribution by GC Content Quintile')
        axes[1, 1].set_yscale('log')

        # Plot 6: Heatmap of top k-mers (if we have enough)
        top_20 = df.nlargest(20, 'count')
        if len(top_20) >= 4:
            # Create heatmap data matrix
            heatmap_data = []
            for _, row in top_20.iterrows():
                heatmap_data.append([
                    row['count'],
                    row['gc_content'] * 100,  # Scale to percentage
                    len(row['kmer']),
                    sum(1 for c in row['kmer'] if c == 'A'),
                    sum(1 for c in row['kmer'] if c == 'T'),
                    sum(1 for c in row['kmer'] if c == 'C'),
                    sum(1 for c in row['kmer'] if c == 'G')
                ])

            heatmap_df = pd.DataFrame(heatmap_data, index=[r['kmer'][:15] + "..." for r in top_20],
                                      columns=['Count', 'GC%', 'Length', 'A', 'T', 'C', 'G'])

            # Create heatmap for first 4 columns
            heatmap_subset = heatmap_df.iloc[:10, :4]
            sns.heatmap(heatmap_subset, annot=True, fmt='.0f', cmap='YlOrRd', ax=axes[1, 2])
            axes[1, 2].set_title('Top 10 K-mers Characteristics Heatmap')

        plt.tight_layout()

        # Save figure
        output_file = "kmer_analysis_visualization.png"
        plt.savefig(output_file, dpi=300, bbox_inches='tight')
        print(f"Visualization saved to: {output_file}")

        plt.show()

    except Exception as e:
        print(f"Error creating visualizations: {e}")
        return False

    return True


def example_5_export_and_analysis():
    """Example 5: Export results and perform analysis."""
    print("\n" + "=" * 60)
    "Example 5: Export and Advanced Analysis"
    print("=" * 60)

    # Get data from previous example
    df = example_3_abundance_analysis()
    if df is None:
        print("Could not get abundance data for analysis.")
        return False

    try:
        # Export to multiple formats
        print("Exporting data...")

        # Export to CSV
        csv_file = "kmer_abundance_analysis.csv"
        df.to_csv(csv_file, index=False)
        print(f"  Exported to CSV: {csv_file}")

        # Export to Excel-style TSV with additional columns
        tsv_file = "kmer_abundance_analysis.tsv"
        export_df = df.copy()
        export_df['count_per_kb'] = export_df['count'] / (len(export_df['kmer']) / 1024)
        export_df['gc_percentage'] = (export_df['gc_content'] * 100).round(1)
        export_df.to_csv(tsv_file, sep='\t', index=False)
        print(f"  Exported to TSV: {tsv_file}")

        # Create summary report
        print(f"\nGenerating summary report...")
        report = {
            'total_kmers': len(df),
            'abundance_stats': {
                'mean_count': df['count'].mean(),
                'median_count': df['count'].median(),
                'std_count': df['count'].std(),
                'min_count': df['count'].min(),
                'max_count': df['count'].max()
            },
            'gc_content_stats': {
                'mean_gc': df['gc_content'].mean(),
                'std_gc': df['gc_content'].std(),
                'min_gc': df['gc_content'].min(),
                'max_gc': df['gc_content'].max()
            },
            'top_10_kmers': [
                {
                    'kmer': row['kmer'],
                    'count': row['count'],
                    'gc_content': row['gc_content']
                }
                for _, row in df.nlargest(10, 'count').iterrows()
            ],
            'distribution_analysis': {
                category: count for category, count in df['abundance_category'].value_counts().items()
            }
        }

        # Save report as JSON
        report_file = "kmer_analysis_report.json"
        with open(report_file, 'w') as f:
            json.dump(report, f, indent=2)
        print(f"  Saved report to JSON: {report_file}")

        # Create human-readable text report
        text_report_file = "kmer_analysis_report.txt"
        with open(text_report_file, 'w') as f:
            f.write("RustKmer K-mer Abundance Analysis Report\n")
            f.write("=" * 50 + "\n\n")

            f.write("Summary Statistics:\n")
            f.write("-" * 20 + "\n")
            f.write(f"Total k-mers analyzed: {report['total_kmers']:,}\n")
            f.write(f"Mean k-mer count: {report['abundance_stats']['mean_count']:.2f}\n")
            f.write(f"Median k-mer count: {report['abundance_stats']['median_count']:.2f}\n")
            f.write(f"Standard deviation: {report['abundance_stats']['std_count']:.2f}\n")
            f.write(f"Count range: {report['abundance_stats']['min_count']:,} - {report['abundance_stats']['max_count']:,}\n\n")

            f.write("GC Content Statistics:\n")
            f.write("-" * 20 + "\n")
            f.write(f"Mean GC content: {report['gc_content_stats']['mean_gc']:.2%}\n")
            f.write(f"Standard deviation: {report['gc_content_stats']['std_gc']:.2%}\n")
            f.write(f"GC range: {report['gc_content_stats']['min_gc']:.2%} - {report['gc_content_stats']['max_gc']:.2%}\n\n")

            f.write("Top 10 Most Abundant K-mers:\n")
            f.write("-" * 30 + "\n")
            for i, kmer_data in enumerate(report['top_10_kmers'], 1):
                f.write(f"{i:2d}. {kmer_data['kmer']:<35} | "
                      f"Count: {kmer_data['count']:8,} | "
                      f"GC: {kmer_data['gc_content']:.2%}\n")

            f.write("\nDistribution Analysis:\n")
            f.write("-" * 20 + "\n")
            for category, count in report['distribution_analysis'].items():
                f.write(f"{category:15}: {count:6d} k-mers ({count/report['total_kmers']*100:.1f}%)\n")

        print(f"  Saved text report to: {text_report_file}")

        # Perform correlation analysis
        print(f"\n--- Correlation Analysis ---")
        numeric_cols = ['count', 'gc_content', 'log_count', 'kmer_length']
        numeric_data = export_df[numeric_cols].copy()
        numeric_data['kmer_length'] = export_df['kmer'].str.len()

        correlation_matrix = numeric_data.corr()
        print("Correlation Matrix:")
        print(correlation_matrix.round(3))

        # Find strongest correlations
        print("\nStrongest correlations (|r| > 0.3):")
        for i in range(len(correlation_matrix.columns)):
            for j in range(i+1, len(correlation_matrix.columns)):
                corr = correlation_matrix.iloc[i, j]
                if abs(corr) > 0.3:
                    col1 = correlation_matrix.columns[i]
                    col2 = correlation_matrix.columns[j]
                    print(f"  {col1:15} vs {col2:15}: {corr:.3f}")

        return True

    except Exception as e:
        print(f"Error in export/analysis: {e}")
        return False


def create_sample_databases(database_configs):
    """Create sample databases for demonstration."""
    for db_file, sequences in database_configs.items():
        counter = PyCounter(k=31, canonical=True)
        counter.count_file_list(sequences)
        counter.save_to_database(db_file)


def create_abundance_database(db_path):
    """Create a database with varied k-mer abundances."""
    # Create sequences with different frequencies
    sequences = []

    # High abundance sequences (repeated)
    high_abundance_seq = "ATCGATCGATCGATCGATCGATCGATCGATCGATCG"
    for _ in range(50):
        sequences.append(high_abundance_seq)

    # Medium abundance sequences
    medium_abundance_seq = "GCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAG"
    for _ in range(20):
        sequences.append(medium_abundance_seq)

    # Low abundance sequences
    low_abundance_seq = "TTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTT"
    for _ in range(10):
        sequences.append(low_abundance_seq)

    # Unique sequences
    unique_sequences = [
        "CCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCC",
        "ATCGGCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAGC",
        "GCTAATCGATCGATCGATCGATCGATCGATCGATCGA"
    ]
    sequences.extend(unique_sequences)

    counter = PyCounter(k=31, canonical=True)
    counter.count_file_list(sequences)
    counter.save_to_database(db_path)


def main():
    """Run all pandas integration examples."""
    print("RustKmer Python API - Pandas Integration Examples")
    print("=============================================")

    examples = [
        ("K-mer Count Matrix", example_1_kmer_count_matrix),
        ("Presence/Absence Matrix", example_2_presence_absence_matrix),
        ("Abundance Analysis", example_3_abundance_analysis),
        ("Data Visualization", example_4_visualization),
        ("Export and Analysis", example_5_export_and_analysis)
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