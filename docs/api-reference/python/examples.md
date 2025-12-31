# Python API Examples

This page provides comprehensive examples of using the RustKmer Python API for various bioinformatics applications. The examples range from basic usage to advanced workflows, demonstrating real-world use cases and best practices.

## Table of Contents

- [Basic Usage Examples](#basic-usage-examples)
- [Database Operations](#database-operations)
- [Query and Analysis Examples](#query-and-analysis-examples)
- [Performance Optimization](#performance-optimization)
- [Integration with Bioinformatics Tools](#integration-with-bioinformatics-tools)
- [Machine Learning Applications](#machine-learning-applications)
- [Visualization and Reporting](#visualization-and-reporting)

---

## Basic Usage Examples

### Getting Started with RustKmer

```python
#!/usr/bin/env python3
"""
Basic RustKmer Python API usage example.
"""

from rustkmer import Database, KmerCounter
from pathlib import Path

def basic_example():
    """Demonstrate basic RustKmer functionality."""

    # Example 1: Query an existing database
    print("=== Example 1: Query Database ===")
    db = Database("example.rkdb")

    # Query a single k-mer
    kmer = "ATCGATCGATCGATCGATCGATCGATCGATCGATCG"
    result = db.query(kmer)

    print(f"Query: {kmer}")
    print(f"Found: {result.is_present}")
    print(f"Count: {result.count}")
    print(f"Canonical: {result.canonical}")

    # Example 2: Get database statistics
    print("\n=== Example 2: Database Statistics ===")
    stats = db.stats()
    print(f"K-mer size: {stats.kmer_size}")
    print(f"Unique k-mers: {stats.unique_kmers:,}")
    print(f"Total counts: {stats.total_counts:,}")

    # Example 3: Context manager usage (recommended)
    print("\n=== Example 3: Context Manager ===")
    with Database("example.rkdb") as db:
        result = db.query("GCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAG")
        print(f"Query result: {result.count}")
        # Database automatically closed

    print("Basic example completed!")

if __name__ == "__main__":
    basic_example()
```

### Creating and Querying Databases

```python
#!/usr/bin/env python3
"""
Create k-mer databases and perform queries.
"""

from rustkmer import KmerCounter, Database
import tempfile
import os

def create_and_query_database():
    """Create a database from sequences and query it."""

    # Create sample FASTA file
    sequences = [
        "ATCGATCGATCGATCGATCGATCGATCGATCGATCG",
        "GCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAG",
        "ATCGATCGATCGATCGATCGATCGATCGATCGATCG"  # Duplicate
    ]

    fasta_content = ""
    for i, seq in enumerate(sequences):
        fasta_content += f">seq_{i+1}\n{seq}\n"

    # Write to temporary file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.fasta', delete=False) as f:
        f.write(fasta_content)
        fasta_file = f.name

    try:
        print("=== Creating k-mer database ===")

        # Count k-mers
        counter = KmerCounter(k=31, canonical=True)
        counter.count_file(fasta_file)

        # Get statistics
        total_kmers = counter.get_total_count()
        unique_kmers = counter.get_unique_count()

        print(f"Total k-mers: {total_kmers:,}")
        print(f"Unique k-mers: {unique_kmers:,}")

        # Save database
        db_file = "example_database.rkdb"
        counter.save_to_database(db_file)
        print(f"Database saved to: {db_file}")

        # Query the database
        print("\n=== Querying database ===")
        with Database(db_file) as db:
            # Query exact match
            result1 = db.query("ATCGATCGATCGATCGATCGATCGATCGATCGATCG")
            print(f"Exact query: {result1.count} occurrences")

            # Query non-existent k-mer
            result2 = db.query("AAAAAAAAAAAAAAAAAAAAAAAAAAAAAA")
            print(f"Non-existent query: {result2.is_present}")

        print("Database creation and query completed!")

    finally:
        # Clean up temporary file
        os.unlink(fasta_file)

if __name__ == "__main__":
    create_and_query_database()
```

---

## Database Operations

### Database Merging and Comparison

```python
#!/usr/bin/env python3
"""
Merge multiple databases and compare their contents.
"""

from rustkmer import Database, KmerCounter
import pandas as pd
from pathlib import Path
import tempfile

def merge_and_compare_databases():
    """Demonstrate database merging and comparison."""

    # Create sample databases
    print("=== Creating sample databases ===")

    # Database 1: AT-rich sequences
    seq1 = ["ATATATATATATATATATATATATATATATATAT", "ATCGATCGATCGATCGATCGATCGATCGATCGATCG"]

    # Database 2: GC-rich sequences
    seq2 = ["GCGCGCGCGCGCGCGCGCGCGCGCGCGCGCGCGCGC", "GCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAG"]

    # Create temporary FASTA files
    temp_files = []
    sequences = [seq1, seq2]
    db_files = []

    for i, seqs in enumerate(sequences):
        with tempfile.NamedTemporaryFile(mode='w', suffix=f'_sample{i+1}.fasta', delete=False) as f:
            fasta_content = ""
            for j, seq in enumerate(seqs):
                fasta_content += f">sample{i+1}_seq{j+1}\n{seq}\n"
            f.write(fasta_content)
            temp_files.append(f.name)

        # Count k-mers and create database
        counter = KmerCounter(k=21, canonical=True)
        counter.count_file(f.name)

        db_file = f"sample{i+1}_k21.rkdb"
        counter.save_to_database(db_file)
        db_files.append(db_file)

        print(f"Created {db_file} with {counter.get_unique_count():,} unique k-mers")

    try:
        # Compare databases
        print("\n=== Comparing databases ===")

        # Get common k-mers
        common_kmers = set()
        all_kmers = set()

        for i, db_file in enumerate(db_files):
            db_kmers = set()
            with Database(db_file) as db:
                for result in db.dump(limit=1000):  # Limit for demo
                    db_kmers.add(result.canonical)

            if i == 0:
                common_kmers = db_kmers
            else:
                common_kmers &= db_kmers
            all_kmers |= db_kmers

        print(f"Total unique k-mers across all databases: {len(all_kmers):,}")
        print(f"Common k-mers in all databases: {len(common_kmers):,}")

        # Create presence matrix
        print("\n=== Creating presence matrix ===")
        presence_data = []

        for i, db_file in enumerate(db_files):
            sample_name = f"sample_{i+1}"
            sample_data = {'Sample': sample_name}

            # Query a subset of common k-mers
            query_kmers = list(common_kmers)[:20]  # First 20 for demo

            with Database(db_file) as db:
                for kmer in query_kmers:
                    result = db.query(kmer)
                    sample_data[kmer] = 1 if result.is_present else 0

            presence_data.append(sample_data)

        df = pd.DataFrame(presence_data)
        print("Presence matrix (first 10 k-mers):")
        print(df.iloc[:, :11])  # Sample + first 10 k-mers

        # Calculate similarity
        print("\n=== Database similarity ===")
        presence_matrix = df.iloc[:, 1:].values  # Exclude Sample column

        # Simple Jaccard similarity
        from sklearn.metrics import jaccard_score
        import numpy as np

        n_samples = len(db_files)
        similarity_matrix = np.zeros((n_samples, n_samples))

        for i in range(n_samples):
            for j in range(i, n_samples):
                if i == j:
                    similarity_matrix[i, j] = 1.0
                else:
                    intersection = np.sum(np.logical_and(presence_matrix[i], presence_matrix[j]))
                    union = np.sum(np.logical_or(presence_matrix[i], presence_matrix[j]))
                    similarity = intersection / union if union > 0 else 0
                    similarity_matrix[i, j] = similarity_matrix[j, i] = similarity

        print("Sample similarity matrix:")
        for i in range(n_samples):
            row = " ".join(f"{similarity_matrix[i, j]:.2f}" for j in range(n_samples))
            print(f"Sample {i+1}: {row}")

    finally:
        # Clean up
        for f in temp_files + db_files:
            if Path(f).exists():
                Path(f).unlink()

if __name__ == "__main__":
    merge_and_compare_databases()
```

### Database Backup and Migration

```python
#!/usr/bin/env python3
"""
Database backup, migration, and validation utilities.
"""

from rustkmer import Database
import shutil
import hashlib
import json
from pathlib import Path

def backup_database(db_path, backup_dir):
    """Create a backup of a database with validation."""

    db_path = Path(db_path)
    backup_dir = Path(backup_dir)
    backup_dir.mkdir(parents=True, exist_ok=True)

    # Generate backup filename with timestamp
    import datetime
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_file = backup_dir / f"{db_path.stem}_{timestamp}.rkdb"

    print(f"Backing up {db_path} to {backup_file}")

    # Copy database file
    shutil.copy2(db_path, backup_file)

    # Validate both databases
    print("Validating original database...")
    original_valid = validate_database(db_path)

    print("Validating backup database...")
    backup_valid = validate_database(backup_file)

    # Calculate checksums
    original_checksum = calculate_file_checksum(db_path)
    backup_checksum = calculate_file_checksum(backup_file)

    # Create backup metadata
    metadata = {
        'original_file': str(db_path),
        'backup_file': str(backup_file),
        'timestamp': timestamp,
        'original_checksum': original_checksum,
        'backup_checksum': backup_checksum,
        'original_valid': original_valid,
        'backup_valid': backup_valid,
        'file_size': backup_file.stat().st_size
    }

    metadata_file = backup_dir / f"{db_path.stem}_{timestamp}_metadata.json"
    with open(metadata_file, 'w') as f:
        json.dump(metadata, f, indent=2)

    print(f"Backup completed successfully!")
    print(f"Original checksum: {original_checksum}")
    print(f"Backup checksum: {backup_checksum}")
    print(f"Metadata saved to: {metadata_file}")

    return backup_file, metadata_file

def validate_database(db_path):
    """Validate database integrity and functionality."""

    try:
        with Database(db_path) as db:
            # Test basic functionality
            stats = db.stats()

            # Test query with a simple k-mer
            test_kmer = "A" * stats.kmer_size if stats.kmer_size else "ATCGATCGATCGATCGATCGATCGATCGATCGATCG"
            result = db.query(test_kmer)

            # Test dump functionality
            dump_results = list(db.dump(limit=10))

        return True

    except Exception as e:
        print(f"Database validation failed: {e}")
        return False

def calculate_file_checksum(file_path):
    """Calculate SHA-256 checksum of a file."""

    sha256_hash = hashlib.sha256()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            sha256_hash.update(chunk)
    return sha256_hash.hexdigest()

def migrate_database_format(old_db_path, new_db_path):
    """Migrate database to new format (conceptual example)."""

    print(f"Migrating database from {old_db_path} to {new_db_path}")

    with Database(old_db_path) as old_db:
        stats = old_db.stats()
        print(f"Original database: {stats.unique_kmers:,} unique k-mers")

        # Create new database (in practice, this would use RustKmer's migration tools)
        # For this example, we'll just copy and validate
        shutil.copy2(old_db_path, new_db_path)

        # Validate new database
        with Database(new_db_path) as new_db:
            new_stats = new_db.stats()
            print(f"Migrated database: {new_stats.unique_kmers:,} unique k-mers")

            if stats.unique_kmers == new_stats.unique_kmers:
                print("Migration successful: k-mer counts match")
            else:
                print("Warning: k-mer counts differ between databases")

    return new_db_path

# Example usage
if __name__ == "__main__":
    # Example backup
    backup_file, metadata_file = backup_database(
        "example.rkdb",
        "database_backups"
    )

    # Example migration
    migrate_database_format(
        "example.rkdb",
        "example_migrated.rkdb"
    )
```

---

## Query and Analysis Examples

### Fuzzy Query Analysis

```python
#!/usr/bin/env python3
"""
Advanced fuzzy query analysis and interpretation.
"""

from rustkmer import Database
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from collections import defaultdict
import numpy as np

def analyze_fuzzy_queries():
    """Comprehensive fuzzy query analysis."""

    db = Database("example.rkdb")

    # Test k-mers with different characteristics
    test_kmers = [
        "ATCGATCGATCGATCGATCGATCGATCGATCGATCG",  # Balanced
        "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA",  # Low complexity
        "GCGCGCGCGCGCGCGCGCGCGCGCGCGCGCGCGCGC",  # High GC
        "TTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTT"   # Homopolymer
    ]

    print("=== Fuzzy Query Analysis ===")

    # Analyze each k-mer with different mutation tolerances
    all_results = []

    for kmer in test_kmers:
        print(f"\nAnalyzing: {kmer[:20]}...")

        for mutations in range(4):  # 0, 1, 2, 3 mutations
            result = db.fuzzy_query(kmer, mutations=mutations)

            analysis = {
                'kmer': kmer,
                'mutations_allowed': mutations,
                'total_matches': result.total_matches,
                'exact_matches': result.exact_matches,
                'fuzzy_matches': result.fuzzy_matches,
                'unique_variants': len(result.get_fuzzy_matches()),
                'max_count': max([m.count for m in result.matches]) if result.matches else 0,
                'mean_count': np.mean([m.count for m in result.matches]) if result.matches else 0
            }

            all_results.append(analysis)

            print(f"  Mutations {mutations}: {result.total_matches} matches "
                  f"({result.exact_matches} exact, {result.fuzzy_matches} fuzzy)")

    # Create analysis DataFrame
    df = pd.DataFrame(all_results)

    print("\n=== Summary Statistics ===")
    print(df.groupby('mutations_allowed').agg({
        'total_matches': ['mean', 'std'],
        'unique_variants': ['mean', 'std'],
        'fuzzy_matches': ['mean', 'std']
    }).round(2))

    # Analyze mutation patterns
    print("\n=== Mutation Pattern Analysis ===")

    for kmer in test_kmers[:2]:  # Analyze first 2 k-mers in detail
        result = db.fuzzy_query(kmer, mutations=2)

        # Count mutations by position
        position_mutations = defaultdict(int)
        total_variants = 0

        for match in result.get_fuzzy_matches():
            total_variants += match.count
            for mutation in match.mutations:
                if '>' in mutation:
                    position = int(mutation.split('>')[0][1:]) - 1  # 0-based position
                    position_mutations[position] += match.count

        if position_mutations:
            print(f"\nK-mer: {kmer[:20]}...")
            print("Mutation distribution by position:")
            for pos in sorted(position_mutations.keys()):
                frequency = position_mutations[pos] / total_variants
                print(f"  Position {pos+1}: {frequency:.2%}")

    # Create visualization
    create_fuzzy_query_visualization(df)

    return df

def create_fuzzy_query_visualization(df):
    """Create visualizations for fuzzy query results."""

    fig, axes = plt.subplots(2, 2, figsize=(15, 12))
    fig.suptitle('Fuzzy Query Analysis Results', fontsize=16)

    # Plot 1: Total matches vs mutations allowed
    ax1 = axes[0, 0]
    for kmer in df['kmer'].unique():
        kmer_data = df[df['kmer'] == kmer]
        ax1.plot(kmer_data['mutations_allowed'], kmer_data['total_matches'],
                marker='o', label=kmer[:15] + "...", linewidth=2, markersize=6)

    ax1.set_xlabel('Mutations Allowed')
    ax1.set_ylabel('Total Matches')
    ax1.set_title('Total Matches vs Mutation Tolerance')
    ax1.legend(bbox_to_anchor=(1.05, 1), loc='upper left')
    ax1.grid(True, alpha=0.3)

    # Plot 2: Exact vs fuzzy matches
    ax2 = axes[0, 1]
    mutations_groups = df.groupby('mutations_allowed')

    exact_matches = mutations_groups['exact_matches'].mean()
    fuzzy_matches = mutations_groups['fuzzy_matches'].mean()

    x = np.arange(len(exact_matches.index))
    width = 0.35

    ax2.bar(x - width/2, exact_matches.values, width, label='Exact Matches', alpha=0.7)
    ax2.bar(x + width/2, fuzzy_matches.values, width, label='Fuzzy Matches', alpha=0.7)

    ax2.set_xlabel('Mutations Allowed')
    ax2.set_ylabel('Average Matches')
    ax2.set_title('Exact vs Fuzzy Matches')
    ax2.set_xticks(x)
    ax2.set_xticklabels(exact_matches.index)
    ax2.legend()
    ax2.grid(True, alpha=0.3)

    # Plot 3: Unique variants
    ax3 = axes[1, 0]
    for kmer in df['kmer'].unique():
        kmer_data = df[df['kmer'] == kmer]
        ax3.plot(kmer_data['mutations_allowed'], kmer_data['unique_variants'],
                marker='s', label=kmer[:15] + "...", linewidth=2, markersize=6)

    ax3.set_xlabel('Mutations Allowed')
    ax3.set_ylabel('Unique Variants')
    ax3.set_title('Unique Variants vs Mutation Tolerance')
    ax3.legend(bbox_to_anchor=(1.05, 1), loc='upper left')
    ax3.grid(True, alpha=0.3)

    # Plot 4: Match abundance distribution
    ax4 = axes[1, 1]

    # Collect all match counts for visualization
    all_counts = []
    for mutations in df['mutations_allowed'].unique():
        counts = df[df['mutations_allowed'] == mutations]['max_count']
        all_counts.extend([(count, mutations) for count in counts])

    if all_counts:
        counts_df = pd.DataFrame(all_counts, columns=['count', 'mutations'])

        # Create boxplot
        sns.boxplot(data=counts_df, x='mutations', y='count', ax=ax4)
        ax4.set_xlabel('Mutations Allowed')
        ax4.set_ylabel('Max Match Count')
        ax4.set_title('Match Abundance Distribution')
        ax4.set_yscale('log')

    plt.tight_layout()
    plt.show()

def find_optimal_mutation_tolerance(db, test_kmers, max_mutations=4):
    """Find optimal mutation tolerance for different use cases."""

    print("=== Finding Optimal Mutation Tolerance ===")

    results = []

    for kmer in test_kmers:
        kmer_results = []

        for mutations in range(max_mutations + 1):
            result = db.fuzzy_query(kmer, mutations=mutations)

            # Calculate metrics
            if result.total_matches > 0:
                diversity = len(result.matches) / result.total_matches
                abundance = np.mean([m.count for m in result.matches])
            else:
                diversity = 0
                abundance = 0

            kmer_results.append({
                'mutations': mutations,
                'total_matches': result.total_matches,
                'diversity': diversity,
                'abundance': abundance,
                'efficiency': result.total_matches / (4 ** mutations) if mutations > 0 else result.total_matches
            })

        # Find optimal based on different criteria
        results.append({
            'kmer': kmer,
            'by_total_matches': max(kmer_results, key=lambda x: x['total_matches'])['mutations'],
            'by_diversity': max(kmer_results, key=lambda x: x['diversity'])['mutations'],
            'by_efficiency': max(kmer_results, key=lambda x: x['efficiency'])['mutations']
        })

    # Print recommendations
    for result in results:
        print(f"\nK-mer: {result['kmer'][:20]}...")
        print(f"  Optimal for total matches: {result['by_total_matches']} mutations")
        print(f"  Optimal for diversity: {result['by_diversity']} mutations")
        print(f"  Optimal for efficiency: {result['by_efficiency']} mutations")

    return results

if __name__ == "__main__":
    # Run analysis
    results_df = analyze_fuzzy_queries()

    # Find optimal mutation tolerances
    test_kmers = [
        "ATCGATCGATCGATCGATCGATCGATCGATCGATCG",
        "GCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAG"
    ]

    db = Database("example.rkdb")
    optimal_results = find_optimal_mutation_tolerance(db, test_kmers)
```

### Batch Query Processing

```python
#!/usr/bin/env python3
"""
Efficient batch query processing with progress tracking and error handling.
"""

from rustkmer import Database
from concurrent.futures import ThreadPoolExecutor, as_completed
import pandas as pd
import time
import logging
from typing import List, Dict, Tuple

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class BatchQueryProcessor:
    """Efficient batch query processor with progress tracking."""

    def __init__(self, db_path: str, max_workers: int = 4):
        self.db_path = db_path
        self.max_workers = max_workers
        self.results = []

    def process_batch(self, queries: List[str], mutations: int = 1) -> Dict:
        """Process a batch of queries with progress tracking."""

        logger.info(f"Processing {len(queries)} queries with {mutations} mutations allowed")
        start_time = time.time()

        # Process queries in parallel
        with Database(self.db_path) as db:
            with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                # Submit all queries
                future_to_query = {
                    executor.submit(self._single_query, db, query, mutations): query
                    for query in queries
                }

                # Collect results with progress tracking
                completed = 0
                for future in as_completed(future_to_query):
                    query = future_to_query[future]
                    completed += 1

                    try:
                        result = future.result()
                        self.results.append(result)

                        if completed % 100 == 0 or completed == len(queries):
                            progress = completed / len(queries) * 100
                            logger.info(f"Progress: {progress:.1f}% ({completed}/{len(queries)})")

                    except Exception as e:
                        logger.error(f"Query failed for {query[:20]}...: {e}")
                        self.results.append({
                            'query': query,
                            'error': str(e),
                            'success': False
                        })

        processing_time = time.time() - start_time
        successful = sum(1 for r in self.results if r.get('success', True))

        logger.info(f"Batch processing completed in {processing_time:.2f} seconds")
        logger.info(f"Successful queries: {successful}/{len(queries)} ({successful/len(queries):.1%})")

        return {
            'total_queries': len(queries),
            'successful': successful,
            'failed': len(queries) - successful,
            'processing_time': processing_time,
            'queries_per_second': len(queries) / processing_time,
            'results': self.results
        }

    def _single_query(self, db: Database, query: str, mutations: int) -> Dict:
        """Process a single fuzzy query."""

        try:
            result = db.fuzzy_query(query, mutations=mutations)

            return {
                'query': query,
                'success': True,
                'total_matches': result.total_matches,
                'exact_matches': result.exact_matches,
                'fuzzy_matches': result.fuzzy_matches,
                'top_match': result.get_top_matches(1)[0].kmer if result.matches else None,
                'top_match_count': result.get_top_matches(1)[0].count if result.matches else 0
            }

        except Exception as e:
            return {
                'query': query,
                'success': False,
                'error': str(e)
            }

    def results_to_dataframe(self) -> pd.DataFrame:
        """Convert results to pandas DataFrame for analysis."""

        successful_results = [r for r in self.results if r.get('success', True)]

        if not successful_results:
            return pd.DataFrame()

        return pd.DataFrame(successful_results)

    def generate_summary_report(self) -> Dict:
        """Generate comprehensive summary of batch processing results."""

        df = self.results_to_dataframe()

        if df.empty:
            return {'error': 'No successful results to analyze'}

        summary = {
            'total_queries': len(self.results),
            'successful_queries': len(df),
            'success_rate': len(df) / len(self.results),

            # Match statistics
            'mean_total_matches': df['total_matches'].mean(),
            'median_total_matches': df['total_matches'].median(),
            'max_total_matches': df['total_matches'].max(),

            # Exact vs fuzzy matches
            'total_exact_matches': df['exact_matches'].sum(),
            'total_fuzzy_matches': df['fuzzy_matches'].sum(),
            'queries_with_exact_matches': (df['exact_matches'] > 0).sum(),
            'queries_with_fuzzy_matches': (df['fuzzy_matches'] > 0).sum(),

            # Top match statistics
            'mean_top_match_count': df['top_match_count'].mean(),
            'median_top_match_count': df['top_match_count'].median()
        }

        return summary

def generate_test_queries(num_queries: int = 1000, kmer_length: int = 31) -> List[str]:
    """Generate test k-mers for batch processing."""

    import random

    bases = ['A', 'T', 'C', 'G']
    queries = []

    # Generate random k-mers
    for _ in range(num_queries):
        kmer = ''.join(random.choices(bases, k=kmer_length))
        queries.append(kmer)

    # Add some known patterns
    patterns = [
        "A" * kmer_length,
        "T" * kmer_length,
        "C" * kmer_length,
        "G" * kmer_length,
        "ATCG" * (kmer_length // 4),
        "GCTA" * (kmer_length // 4)
    ]

    queries.extend(patterns)

    return queries

def analyze_batch_results(batch_results: Dict, output_file: str = None):
    """Analyze batch processing results and generate visualizations."""

    if 'results' not in batch_results:
        print("No results to analyze")
        return

    # Create DataFrame
    df = pd.DataFrame([r for r in batch_results['results'] if r.get('success', True)])

    if df.empty:
        print("No successful results to analyze")
        return

    print("=== Batch Query Analysis ===")
    print(f"Total queries: {batch_results['total_queries']}")
    print(f"Successful: {batch_results['successful']}")
    print(f"Failed: {batch_results['failed']}")
    print(f"Processing time: {batch_results['processing_time']:.2f} seconds")
    print(f"Queries/second: {batch_results['queries_per_second']:.1f}")

    print("\n=== Match Statistics ===")
    print(f"Mean total matches: {df['total_matches'].mean():.2f}")
    print(f"Median total matches: {df['total_matches'].median():.2f}")
    print(f"Max total matches: {df['total_matches'].max()}")
    print(f"Queries with exact matches: {(df['exact_matches'] > 0).sum()}")
    print(f"Queries with fuzzy matches: {(df['fuzzy_matches'] > 0).sum()}")

    # Create visualizations
    try:
        import matplotlib.pyplot as plt
        import seaborn as sns

        fig, axes = plt.subplots(2, 2, figsize=(15, 12))
        fig.suptitle('Batch Query Processing Results', fontsize=16)

        # Total matches distribution
        axes[0, 0].hist(df['total_matches'], bins=50, alpha=0.7, edgecolor='black')
        axes[0, 0].set_xlabel('Total Matches')
        axes[0, 0].set_ylabel('Frequency')
        axes[0, 0].set_title('Total Matches Distribution')
        axes[0, 0].set_yscale('log')

        # Exact vs fuzzy matches
        exact_mask = df['exact_matches'] > 0
        fuzzy_mask = df['fuzzy_matches'] > 0

        labels = ['Only Exact', 'Only Fuzzy', 'Both', 'Neither']
        sizes = [
            (exact_mask & ~fuzzy_mask).sum(),
            (~exact_mask & fuzzy_mask).sum(),
            (exact_mask & fuzzy_mask).sum(),
            (~exact_mask & ~fuzzy_mask).sum()
        ]

        axes[0, 1].pie(sizes, labels=labels, autopct='%1.1f%%', startangle=90)
        axes[0, 1].set_title('Match Type Distribution')

        # Top match counts
        axes[1, 0].hist(df['top_match_count'], bins=50, alpha=0.7, edgecolor='black')
        axes[1, 0].set_xlabel('Top Match Count')
        axes[1, 0].set_ylabel('Frequency')
        axes[1, 0].set_title('Top Match Count Distribution')
        axes[1, 0].set_yscale('log')

        # Performance over time (simulated)
        axes[1, 1].plot(range(len(df)), df['total_matches'], alpha=0.6)
        axes[1, 1].set_xlabel('Query Index')
        axes[1, 1].set_ylabel('Total Matches')
        axes[1, 1].set_title('Matches per Query')

        plt.tight_layout()

        if output_file:
            plt.savefig(output_file, dpi=300, bbox_inches='tight')
            print(f"\nVisualization saved to: {output_file}")
        else:
            plt.show()

    except ImportError:
        print("\nMatplotlib not available for visualization")

    # Save detailed results
    if output_file:
        detailed_file = output_file.replace('.png', '_details.csv')
        df.to_csv(detailed_file, index=False)
        print(f"Detailed results saved to: {detailed_file}")

# Example usage
if __name__ == "__main__":
    # Generate test queries
    queries = generate_test_queries(num_queries=500, kmer_length=31)

    # Create batch processor
    processor = BatchQueryProcessor("example.rkdb", max_workers=8)

    # Process batch
    batch_results = processor.process_batch(queries, mutations=2)

    # Analyze results
    analyze_batch_results(batch_results, "batch_query_analysis.png")
```

---

## Performance Optimization

### Memory-Efficient Database Processing

```python
#!/usr/bin/env python3
"""
Memory-efficient techniques for processing large databases.
"""

from rustkmer import Database
import psutil
import gc
from pathlib import Path

class MemoryEfficientProcessor:
    """Process databases with memory monitoring and optimization."""

    def __init__(self, memory_limit_gb: float = 4.0):
        self.memory_limit_gb = memory_limit_gb
        self.memory_check_interval = 10000

    def get_memory_usage(self) -> float:
        """Get current memory usage in GB."""
        return psutil.Process().memory_info().rss / (1024**3)

    def process_large_database_safely(self, db_path: str,
                                     process_function=None,
                                     max_variants: int = None):
        """Process large database with memory safety checks."""

        print(f"Processing large database: {db_path}")
        print(f"Memory limit: {self.memory_limit_gb} GB")

        initial_memory = self.get_memory_usage()
        print(f"Initial memory usage: {initial_memory:.2f} GB")

        processed_items = 0
        results = []

        try:
            with Database(db_path) as db:
                if max_variants:
                    # Use limited dump
                    iterator = db.dump(limit=max_variants)
                else:
                    iterator = db.dump(canonical_only=True)

                for result in iterator:
                    processed_items += 1

                    # Process result if function provided
                    if process_function:
                        result_data = process_function(result)
                        if result_data:
                            results.append(result_data)

                    # Periodic memory checks
                    if processed_items % self.memory_check_interval == 0:
                        current_memory = self.get_memory_usage()
                        memory_increase = current_memory - initial_memory

                        print(f"Processed {processed_items:,} items, "
                              f"Memory: {current_memory:.2f} GB (+{memory_increase:.2f} GB)")

                        # Safety check
                        if current_memory > self.memory_limit_gb:
                            print(f"WARNING: Memory limit exceeded ({current_memory:.2f} GB)")
                            print("Triggering garbage collection...")
                            gc.collect()

                            # Check again after garbage collection
                            current_memory = self.get_memory_usage()
                            if current_memory > self.memory_limit_gb:
                                print("CRITICAL: Memory still exceeds limit, stopping processing")
                                break

                        # Periodic garbage collection
                        elif processed_items % (self.memory_check_interval * 5) == 0:
                            gc.collect()

            final_memory = self.get_memory_usage()
            print(f"\nProcessing completed!")
            print(f"Total items processed: {processed_items:,}")
            print(f"Final memory usage: {final_memory:.2f} GB")
            print(f"Memory increase: {final_memory - initial_memory:.2f} GB")

            return results

        except Exception as e:
            print(f"Error during processing: {e}")
            raise

    def stream_database_to_file(self, db_path: str, output_file: str,
                               max_items: int = None,
                               format_type: str = 'tsv'):
        """Stream database contents to file with minimal memory usage."""

        print(f"Streaming database to {output_file}")

        processed_items = 0

        with Database(db_path) as db:
            with open(output_file, 'w') as out_file:

                # Write header based on format
                if format_type == 'tsv':
                    out_file.write("kmer\tcount\tcanonical\n")
                elif format_type == 'csv':
                    out_file.write("kmer,count,canonical\n")

                # Stream results
                iterator = db.dump(limit=max_items)

                for result in iterator:
                    processed_items += 1

                    if format_type == 'tsv':
                        out_file.write(f"{result.kmer}\t{result.count}\t{result.canonical}\n")
                    elif format_type == 'csv':
                        out_file.write(f"{result.kmer},{result.count},{result.canonical}\n")

                    # Progress update
                    if processed_items % 100000 == 0:
                        memory_gb = self.get_memory_usage()
                        print(f"Processed {processed_items:,} items, Memory: {memory_gb:.2f} GB")

        print(f"Streaming completed: {processed_items:,} items written to {output_file}")
        return processed_items

def memory_optimized_analysis():
    """Example of memory-optimized database analysis."""

    # Create processor with 2GB memory limit
    processor = MemoryEfficientProcessor(memory_limit_gb=2.0)

    # Example processing function
    def analyze_abundant_kmers(result, min_count=100):
        """Process result to find abundant k-mers."""
        if result.count >= min_count:
            return {
                'kmer': result.kmer,
                'count': result.count,
                'canonical': result.canonical
            }
        return None

    # Process database safely
    try:
        abundant_kmers = processor.process_large_database_safely(
            "large_genome.rkdb",
            process_function=analyze_abundant_kmers,
            max_variants=1000000  # Limit to 1M items
        )

        print(f"\nFound {len(abundant_kmers)} abundant k-mers")

        # Sort by count and show top 10
        abundant_kmers.sort(key=lambda x: x['count'], reverse=True)
        for i, kmer in enumerate(abundant_kmers[:10], 1):
            print(f"{i:2d}. {kmer['kmer']}: {kmer['count']:,}")

    except Exception as e:
        print(f"Analysis failed: {e}")

    # Example streaming to file
    try:
        items_streamed = processor.stream_database_to_file(
            "large_genome.rkdb",
            "database_contents.tsv",
            max_items=500000,
            format_type='tsv'
        )
        print(f"Streamed {items_streamed:,} items to file")

    except Exception as e:
        print(f"Streaming failed: {e}")

# Chunked processing for very large databases
def process_in_chunks(db_path: str, chunk_size: int = 100000,
                      max_total_items: int = None):
    """Process database in fixed-size chunks."""

    print(f"Processing database in chunks of {chunk_size:,} items")

    chunk_results = []
    total_processed = 0

    with Database(db_path) as db:
        chunk_data = []

        for result in db.dump(canonical_only=True):
            chunk_data.append({
                'kmer': result.kmer,
                'count': result.count
            })

            if len(chunk_data) >= chunk_size:
                # Process chunk
                chunk_result = process_chunk(chunk_data, len(chunk_results) + 1)
                chunk_results.append(chunk_result)

                total_processed += len(chunk_data)
                print(f"Processed chunk {len(chunk_results)}: {len(chunk_data):,} items "
                      f"(Total: {total_processed:,})")

                # Clear chunk data
                chunk_data.clear()
                gc.collect()

                # Check total limit
                if max_total_items and total_processed >= max_total_items:
                    break

        # Process remaining items
        if chunk_data:
            chunk_result = process_chunk(chunk_data, len(chunk_results) + 1)
            chunk_results.append(chunk_result)
            total_processed += len(chunk_data)
            print(f"Processed final chunk: {len(chunk_data):,} items")

    print(f"Chunked processing completed: {total_processed:,} total items in {len(chunk_results)} chunks")
    return chunk_results

def process_chunk(chunk_data: list, chunk_number: int):
    """Process a single chunk of data."""

    # Example processing: find top 10 most abundant in chunk
    sorted_chunk = sorted(chunk_data, key=lambda x: x['count'], reverse=True)
    top_10 = sorted_chunk[:10]

    return {
        'chunk_number': chunk_number,
        'items_processed': len(chunk_data),
        'top_abundant': top_10,
        'mean_count': sum(item['count'] for item in chunk_data) / len(chunk_data),
        'max_count': max(item['count'] for item in chunk_data)
    }

# Example usage
if __name__ == "__main__":
    memory_optimized_analysis()

    # Example chunked processing
    # chunk_results = process_in_chunks("very_large_genome.rkdb", chunk_size=50000)
```

---

## Integration with Bioinformatics Tools

### BioPython Integration

```python
#!/usr/bin/env python3
"""
Integration with BioPython for comprehensive sequence analysis.
"""

from rustkmer import Database, KmerCounter
from Bio import SeqIO, Seq, SeqRecord
from Bio.SeqUtils import gc_fraction
import pandas as pd
import matplotlib.pyplot as plt
from pathlib import Path
from collections import defaultdict
import numpy as np

class KmerBioAnalyzer:
    """Integrate RustKmer with BioPython for sequence analysis."""

    def __init__(self, db_path: str = None):
        self.db_path = db_path
        self.db = None

    def load_database(self, db_path: str):
        """Load k-mer database."""
        self.db_path = db_path
        self.db = Database(db_path)
        print(f"Loaded database: {db_path}")

    def analyze_fasta_file(self, fasta_file: str, k: int = 31,
                           create_database: bool = False):
        """Analyze FASTA file and optionally create database."""

        print(f"Analyzing FASTA file: {fasta_file}")

        # Parse sequences
        sequences = []
        total_length = 0

        for record in SeqIO.parse(fasta_file, "fasta"):
            sequences.append(record)
            total_length += len(record.seq)

        print(f"Found {len(sequences)} sequences, total length: {total_length:,} bp")

        # Extract basic statistics
        gc_contents = [gc_fraction(seq.seq) for seq in sequences]
        lengths = [len(seq.seq) for seq in sequences]

        print(f"GC content: {np.mean(gc_contents):.2%} ± {np.std(gc_contents):.2%}")
        print(f"Sequence lengths: {np.mean(lengths):.1f} ± {np.std(lengths):.1f}")

        # Create k-mer database if requested
        if create_database:
            print("Creating k-mer database...")

            db_file = fasta_file.replace('.fasta', '.fasta.rkdb').replace('.fa', '.fa.rkdb')
            counter = KmerCounter(k=k, canonical=True)
            counter.count_file(fasta_file)
            counter.save_to_database(db_file)

            stats = counter.get_total_count(), counter.get_unique_count()
            print(f"Database created: {db_file}")
            print(f"Total k-mers: {stats[0]:,}, Unique: {stats[1]:,}")

            return {
                'sequences': sequences,
                'database_file': db_file,
                'total_kmers': stats[0],
                'unique_kmers': stats[1]
            }

        return {'sequences': sequences}

    def query_sequence_kmers(self, sequence: Seq.Seq, k: int = 31,
                           mutations: int = 0):
        """Query all k-mers from a sequence."""

        if not self.db:
            raise ValueError("No database loaded")

        seq_str = str(sequence).upper()
        kmer_results = []

        # Extract k-mers
        for i in range(len(seq_str) - k + 1):
            kmer = seq_str[i:i+k]

            # Skip k-mers with ambiguous bases
            if 'N' in kmer:
                continue

            if mutations == 0:
                # Exact query
                result = self.db.query(kmer)
                kmer_results.append({
                    'position': i,
                    'kmer': kmer,
                    'count': result.count,
                    'found': result.is_present,
                    'canonical': result.canonical
                })
            else:
                # Fuzzy query
                result = self.db.fuzzy_query(kmer, mutations=mutations)
                kmer_results.append({
                    'position': i,
                    'kmer': kmer,
                    'total_matches': result.total_matches,
                    'exact_matches': result.exact_matches,
                    'fuzzy_matches': result.fuzzy_matches
                })

        return kmer_results

    def find_kmer_density_regions(self, sequence: Seq.Seq, k: int = 31,
                                  window_size: int = 1000, step: int = 100):
        """Find regions with high/low k-mer density."""

        if not self.db:
            raise ValueError("No database loaded")

        seq_str = str(sequence).upper()
        density_data = []

        for start in range(0, len(seq_str) - k + 1, step):
            end = min(start + window_size, len(seq_str))
            window_seq = seq_str[start:end]

            # Count k-mers in window
            kmer_count = 0
            found_kmers = 0

            for i in range(len(window_seq) - k + 1):
                kmer = window_seq[i:i+k]

                if 'N' in kmer:
                    continue

                kmer_count += 1
                result = self.db.query(kmer)

                if result.is_present:
                    found_kmers += 1

            if kmer_count > 0:
                density = found_kmers / kmer_count
            else:
                density = 0

            density_data.append({
                'start': start,
                'end': end,
                'window_size': window_size,
                'kmer_count': kmer_count,
                'found_kmers': found_kmers,
                'density': density
            })

        return density_data

    def compare_sequence_databases(self, sequences: list, labels: list = None):
        """Compare k-mer content across multiple sequences."""

        if not self.db:
            raise ValueError("No database loaded")

        if labels is None:
            labels = [f"Seq_{i+1}" for i in range(len(sequences))]

        comparison_data = []

        for i, (sequence, label) in enumerate(zip(sequences, labels)):
            print(f"Analyzing {label}...")

            # Query all k-mers in sequence
            kmer_results = self.query_sequence_kmers(sequence)

            # Calculate statistics
            total_kmers = len(kmer_results)
            found_kmers = sum(1 for r in kmer_results if r.get('found', False))
            total_counts = sum(r.get('count', 0) for r in kmer_results)

            comparison_data.append({
                'label': label,
                'total_kmers': total_kmers,
                'found_kmers': found_kmers,
                'not_found_kmers': total_kmers - found_kmers,
                'coverage': found_kmers / total_kmers if total_kmers > 0 else 0,
                'total_counts': total_counts,
                'mean_count': total_counts / found_kmers if found_kmers > 0 else 0
            })

        df = pd.DataFrame(comparison_data)
        return df

    def create_kmer_abundance_profile(self, k: int = 31, top_n: int = 1000):
        """Create k-mer abundance profile from database."""

        if not self.db:
            raise ValueError("No database loaded")

        print("Creating k-mer abundance profile...")

        # Get top k-mers from database
        top_kmers = []

        for result in self.db.dump(limit=top_n, canonical_only=True):
            top_kmers.append({
                'kmer': result.kmer,
                'count': result.count,
                'gc_content': (result.kmer.count('G') + result.kmer.count('C')) / len(result.kmer),
                'log_count': np.log10(result.count + 1)
            })

        df = pd.DataFrame(top_kmers)

        print(f"Profile created with {len(df)} k-mers")
        print(f"Count range: {df['count'].min():,} - {df['count'].max():,}")
        print(f"Mean GC content: {df['gc_content'].mean():.2%}")

        return df

    def visualize_kmer_profiles(self, abundance_df, sequence_dfs: list = None):
        """Create visualizations of k-mer profiles."""

        fig, axes = plt.subplots(2, 2, figsize=(15, 12))
        fig.suptitle('K-mer Analysis Visualization', fontsize=16)

        # Plot 1: K-mer abundance distribution
        axes[0, 0].hist(abundance_df['count'], bins=50, alpha=0.7, edgecolor='black')
        axes[0, 0].set_xlabel('K-mer Count')
        axes[0, 0].set_ylabel('Frequency')
        axes[0, 0].set_title('K-mer Abundance Distribution')
        axes[0, 0].set_yscale('log')
        axes[0, 0].grid(True, alpha=0.3)

        # Plot 2: GC content distribution
        axes[0, 1].hist(abundance_df['gc_content'], bins=20, alpha=0.7, edgecolor='black')
        axes[0, 1].set_xlabel('GC Content')
        axes[0, 1].set_ylabel('Frequency')
        axes[0, 1].set_title('K-mer GC Content Distribution')
        axes[0, 1].grid(True, alpha=0.3)

        # Plot 3: Count vs GC content scatter
        axes[1, 0].scatter(abundance_df['gc_content'], abundance_df['count'],
                        alpha=0.6, s=10)
        axes[1, 0].set_xlabel('GC Content')
        axes[1, 0].set_ylabel('Count')
        axes[1, 0].set_title('Count vs GC Content')
        axes[1, 0].set_xscale('linear')
        axes[1, 0].set_yscale('log')
        axes[1, 0].grid(True, alpha=0.3)

        # Plot 4: Sequence comparison (if provided)
        if sequence_dfs:
            combined_df = pd.concat(sequence_dfs, ignore_index=True)

            x_pos = np.arange(len(combined_df))
            width = 0.35

            axes[1, 1].bar(x_pos - width/2, combined_df['coverage'],
                           width, label='Coverage', alpha=0.7)
            axes[1, 1].bar(x_pos + width/2, combined_df['mean_count'],
                           width, label='Mean Count', alpha=0.7)

            axes[1, 1].set_xlabel('Sequence')
            axes[1, 1].set_ylabel('Value')
            axes[1, 1].set_title('Sequence Comparison')
            axes[1, 1].set_xticks(x_pos)
            axes[1, 1].set_xticklabels(combined_df['label'], rotation=45)
            axes[1, 1].legend()
            axes[1, 1].grid(True, alpha=0.3)
        else:
            axes[1, 1].text(0.5, 0.5, 'No sequence data provided',
                            transform=axes[1, 1].transAxes,
                            ha='center', va='center', fontsize=12)

        plt.tight_layout()
        plt.show()

def advanced_biological_analysis():
    """Advanced biological analysis example."""

    # Initialize analyzer
    analyzer = KmerBioAnalyzer()

    # Example 1: Analyze existing database with sequence files
    print("=== Advanced Biological Analysis ===")

    # Load existing database
    analyzer.load_database("genome.rkdb")

    # Load sequences from FASTA
    sequences = list(SeqIO.parse("genome_sequences.fasta", "fasta"))[:5]  # First 5 sequences

    # Compare sequences
    comparison_df = analyzer.compare_sequence_databases(sequences)
    print("\nSequence Comparison:")
    print(comparison_df[['label', 'coverage', 'mean_count']].round(3))

    # Create k-mer abundance profile
    abundance_df = analyzer.create_kmer_abundance_profile(k=31, top_n=500)

    # Analyze specific sequence regions
    if sequences:
        test_seq = sequences[0]
        print(f"\nAnalyzing {test_seq.id}...")

        # Find high-density regions
        density_data = analyzer.find_kmer_density_regions(test_seq.seq)

        # Find top regions
        sorted_density = sorted(density_data, key=lambda x: x['density'], reverse=True)
        print("Top 5 high-density regions:")
        for region in sorted_density[:5]:
            print(f"  {region['start']}-{region['end']}: density={region['density']:.3f}")

    # Create visualizations
    analyzer.visualize_kmer_profiles(abundance_df, [comparison_df])

def sequence_feature_extraction():
    """Extract features from sequences using k-mer analysis."""

    analyzer = KmerBioAnalyzer()
    analyzer.load_database("genome.rkdb")

    # Load sequences
    sequences = list(SeqIO.parse("genome_sequences.fasta", "fasta"))

    features = []

    for seq_record in sequences:
        sequence = seq_record.seq
        seq_id = seq_record.id

        # Extract various features
        seq_length = len(sequence)
        gc_content = gc_fraction(sequence)

        # K-mer-based features
        kmer_results = analyzer.query_sequence_kmers(sequence, k=31)

        total_kmers = len(kmer_results)
        found_kmers = sum(1 for r in kmer_results if r['found'])
        total_counts = sum(r['count'] for r in kmer_results)

        # Calculate additional metrics
        coverage = found_kmers / total_kmers if total_kmers > 0 else 0
        avg_count = total_counts / found_kmers if found_kmers > 0 else 0

        # Find longest stretch of found k-mers
        max_consecutive = 0
        current_consecutive = 0

        for result in kmer_results:
            if result['found']:
                current_consecutive += 1
                max_consecutive = max(max_consecutive, current_consecutive)
            else:
                current_consecutive = 0

        features.append({
            'sequence_id': seq_id,
            'length': seq_length,
            'gc_content': gc_content,
            'total_kmers': total_kmers,
            'found_kmers': found_kmers,
            'coverage': coverage,
            'avg_count': avg_count,
            'max_consecutive': max_consecutive,
            'total_counts': total_counts
        })

    df = pd.DataFrame(features)

    print("=== Sequence Feature Extraction ===")
    print(f"Processed {len(df)} sequences")
    print("\nFeature Summary:")
    print(df[['length', 'gc_content', 'coverage', 'avg_count']].describe())

    return df

# Example usage
if __name__ == "__main__":
    # Run advanced analysis
    advanced_biological_analysis()

    # Extract features
    feature_df = sequence_feature_extraction()
```

---

This examples reference provides comprehensive, real-world examples of using the RustKmer Python API for various bioinformatics applications. Each example includes detailed explanations, error handling, and best practices for production use.