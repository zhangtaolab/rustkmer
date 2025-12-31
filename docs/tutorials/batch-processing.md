# Batch Processing with Python API

This tutorial demonstrates efficient batch processing techniques for handling multiple k-mer queries, large datasets, and automated workflows using the RustKmer Python API.

## Tutorial Overview

You'll learn to:
- Process multiple FASTA files efficiently
- Perform batch k-mer queries with optimization
- Merge multiple k-mer databases
- Implement parallel processing strategies
- Build automated k-mer analysis pipelines

### Prerequisites
- Python 3.8+ with RustKmer installed
- Understanding of basic k-mer operations
- Multiple FASTA files for batch processing
- 20-30 minutes to complete

---

## Scenario: Processing Multiple Samples

You have multiple genomic samples that need k-mer analysis:
- Sample batch with 10-100 FASTA files
- Need to compare k-mer content across samples
- Want to identify sample-specific vs shared k-mers
- Require automated pipeline for reproducible analysis

### Example Dataset Structure
```
project/
├── samples/
│   ├── sample_01.fasta
│   ├── sample_02.fasta
│   ├── sample_03.fasta
│   └── ...
├── queries.txt
└── results/
```

---

## Strategy 1: Batch File Processing

### Process Multiple FASTA Files

```python
#!/usr/bin/env python3
"""
Batch processing of multiple FASTA files for k-mer analysis.
"""

import os
import glob
import time
import pandas as pd
from pathlib import Path
from rustkmer import KmerCounter, Database
from concurrent.futures import ThreadPoolExecutor, as_completed
import multiprocessing

class BatchKmerProcessor:
    """Efficient batch processor for multiple FASTA files."""

    def __init__(self, input_dir, output_dir, k=31, workers=None):
        self.input_dir = Path(input_dir)
        self.output_dir = Path(output_dir)
        self.k = k
        self.workers = workers or min(multiprocessing.cpu_count(), 4)

        # Create output directory
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # Find all FASTA files
        self.fasta_files = list(self.input_dir.glob("*.fasta")) + \
                          list(self.input_dir.glob("*.fa")) + \
                          list(self.input_dir.glob("*.fa.gz")) + \
                          list(self.input_dir.glob("*.fasta.gz"))

        print(f"Found {len(self.fasta_files)} FASTA files")
        print(f"Using {self.workers} workers")

    def process_all_files(self):
        """Process all FASTA files in parallel."""

        print(f"\n🔄 Processing {len(self.fasta_files)} files...")
        start_time = time.time()

        # Process files in parallel
        with ThreadPoolExecutor(max_workers=self.workers) as executor:
            # Submit all tasks
            future_to_file = {
                executor.submit(self._process_single_file, fasta_file): fasta_file
                for fasta_file in self.fasta_files
            }

            # Collect results
            results = {}
            for future in as_completed(future_to_file):
                fasta_file = future_to_file[future]
                try:
                    result = future.result()
                    results[fasta_file] = result
                    print(f"✅ Processed: {fasta_file.name}")
                except Exception as e:
                    print(f"❌ Failed to process {fasta_file.name}: {e}")
                    results[fasta_file] = None

        processing_time = time.time() - start_time
        successful = sum(1 for r in results.values() if r is not None)

        print(f"\n📊 Processing Summary:")
        print(f"   Total files: {len(self.fasta_files)}")
        print(f"   Successful: {successful}")
        print(f"   Failed: {len(self.fasta_files) - successful}")
        print(f"   Processing time: {processing_time:.1f} seconds")
        print(f"   Average time per file: {processing_time/len(self.fasta_files):.1f} seconds")

        return results

    def _process_single_file(self, fasta_file):
        """Process a single FASTA file and create k-mer database."""

        # Generate output filename
        db_file = self.output_dir / f"{fasta_file.stem}_k{self.k}.rkdb"

        # Skip if already processed
        if db_file.exists():
            print(f"⏭️  Skipping {fasta_file.name} (already processed)")
            return {
                'input_file': fasta_file,
                'output_file': db_file,
                'status': 'skipped',
                'total_kmers': 0,
                'unique_kmers': 0
            }

        try:
            print(f"🧬 Processing {fasta_file.name}...")

            # Create k-mer counter
            counter = KmerCounter(k=self.k, canonical=True)

            # Count k-mers from file
            counter.count_file(str(fasta_file))

            # Get statistics
            total_kmers = counter.get_total_count()
            unique_kmers = counter.get_unique_count()

            # Save database
            counter.save_to_database(str(db_file))

            return {
                'input_file': fasta_file,
                'output_file': db_file,
                'status': 'success',
                'total_kmers': total_kmers,
                'unique_kmers': unique_kmers
            }

        except Exception as e:
            print(f"❌ Error processing {fasta_file.name}: {e}")
            return {
                'input_file': fasta_file,
                'output_file': db_file,
                'status': 'error',
                'error': str(e),
                'total_kmers': 0,
                'unique_kmers': 0
            }

    def generate_summary_report(self, results):
        """Generate summary report of batch processing."""

        # Create DataFrame from results
        data = []
        for result in results.values():
            if result and result['status'] in ['success', 'skipped']:
                data.append({
                    'Sample': result['input_file'].name,
                    'Status': result['status'],
                    'Total_kmers': result['total_kmers'],
                    'Unique_kmers': result['unique_kmers'],
                    'Uniqueness_ratio': result['unique_kmers'] / result['total_kmers'] if result['total_kmers'] > 0 else 0,
                    'Database_size_mb': result['output_file'].stat().st_size / (1024*1024) if result['output_file'].exists() else 0
                })

        df = pd.DataFrame(data)

        # Save summary
        summary_file = self.output_dir / "batch_processing_summary.csv"
        df.to_csv(summary_file, index=False)
        print(f"\n📋 Summary report saved to: {summary_file}")

        # Print statistics
        if len(df) > 0:
            print(f"\n📊 Batch Processing Statistics:")
            print(f"   Total samples processed: {len(df)}")
            print(f"   Total k-mers across all samples: {df['Total_kmers'].sum():,}")
            print(f"   Average unique k-mers per sample: {df['Unique_kmers'].mean():,.0f}")
            print(f"   Average uniqueness ratio: {df['Uniqueness_ratio'].mean():.4f}")
            print(f"   Total database size: {df['Database_size_mb'].sum():.1f} MB")

        return df

# Usage
if __name__ == "__main__":
    # Example usage
    processor = BatchKmerProcessor(
        input_dir="samples/",
        output_dir="results/databases/",
        k=31,
        workers=4
    )

    results = processor.process_all_files()
    summary_df = processor.generate_summary_report(results)
```

### Parallel Batch Querying

```python
from rustkmer import Database
from concurrent.futures import ThreadPoolExecutor
import pandas as pd

class BatchKmerQuery:
    """Efficient batch k-mer querying across multiple samples."""

    def __init__(self, database_files, queries):
        self.database_files = database_files
        self.queries = queries
        self.results = {}

    def query_all_databases(self, max_workers=4):
        """Query all databases for all k-mers."""

        print(f"Querying {len(self.queries)} k-mers across {len(self.database_files)} databases")

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Submit queries for each database
            future_to_db = {
                executor.submit(self._query_single_database, db_file): db_file
                for db_file in self.database_files
            }

            # Collect results
            for future in as_completed(future_to_db):
                db_file = future_to_db[future]
                try:
                    db_results = future.result()
                    self.results[db_file] = db_results
                    print(f"✅ Queried: {db_file.name}")
                except Exception as e:
                    print(f"❌ Failed to query {db_file.name}: {e}")
                    self.results[db_file] = None

        return self.results

    def _query_single_database(self, db_file):
        """Query a single database for all k-mers."""

        results = {}

        try:
            with Database(str(db_file)) as db:
                for query in self.queries:
                    try:
                        result = db.query(query)
                        results[query] = {
                            'count': result.count,
                            'present': result.is_present,
                            'canonical': result.canonical
                        }
                    except Exception as e:
                        print(f"Query failed for {query[:10]}...: {e}")
                        results[query] = {'count': 0, 'present': False, 'canonical': None}

        except Exception as e:
            print(f"Database access failed for {db_file}: {e}")
            return None

        return results

    def create_presence_matrix(self):
        """Create a binary presence matrix across all samples."""

        if not self.results:
            print("No results available. Run query_all_databases() first.")
            return None

        # Create presence matrix
        matrix_data = []

        for db_file, db_results in self.results.items():
            if db_results:
                row = {'Sample': db_file.stem}
                for query in self.queries:
                    row[query] = 1 if db_results[query]['present'] else 0
                matrix_data.append(row)

        df = pd.DataFrame(matrix_data)
        return df

    def create_count_matrix(self):
        """Create a count matrix across all samples."""

        if not self.results:
            print("No results available. Run query_all_databases() first.")
            return None

        # Create count matrix
        matrix_data = []

        for db_file, db_results in self.results.items():
            if db_results:
                row = {'Sample': db_file.stem}
                for query in self.queries:
                    row[query] = db_results[query]['count']
                matrix_data.append(row)

        df = pd.DataFrame(matrix_data)
        return df

    def analyze_kmer_distribution(self):
        """Analyze k-mer distribution across samples."""

        if not self.results:
            print("No results available. Run query_all_databases() first.")
            return None

        # Analyze each k-mer across samples
        analysis = []

        for query in self.queries:
            presence_count = 0
            total_count = 0
            samples_with_kmer = []

            for db_file, db_results in self.results.items():
                if db_results and db_results[query]['present']:
                    presence_count += 1
                    total_count += db_results[query]['count']
                    samples_with_kmer.append(db_file.stem)

            analysis.append({
                'kmer': query,
                'samples_present': presence_count,
                'samples_total': len([r for r in self.results.values() if r]),
                'presence_frequency': presence_count / len([r for r in self.results.values() if r]),
                'total_counts': total_count,
                'mean_count': total_count / presence_count if presence_count > 0 else 0,
                'samples_with_kmer': samples_with_kmer
            })

        df = pd.DataFrame(analysis)
        return df

# Usage
if __name__ == "__main__":
    # Example usage
    db_files = list(Path("results/databases/").glob("*.rkdb"))
    queries = ["ATCGATCGATCGATCGATCGATCGATCGATCGATCG",
               "GCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAG",
               "TTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTT"]

    batch_query = BatchKmerQuery(db_files, queries)
    results = batch_query.query_all_databases()

    # Create matrices
    presence_df = batch_query.create_presence_matrix()
    count_df = batch_query.create_count_matrix()
    analysis_df = batch_query.analyze_kmer_distribution()

    # Save results
    presence_df.to_csv("results/presence_matrix.csv", index=False)
    count_df.to_csv("results/count_matrix.csv", index=False)
    analysis_df.to_csv("results/kmer_analysis.csv", index=False)
```

---

## Strategy 2: Database Merging

### Merge Multiple K-mer Databases

```python
#!/usr/bin/env python3
"""
Merge multiple k-mer databases into a single comprehensive database.
"""

import os
import glob
import time
from pathlib import Path
from rustkmer import Database, KmerCounter
import pandas as pd

class DatabaseMerger:
    """Merge multiple k-mer databases efficiently."""

    def __init__(self, input_dir, output_file):
        self.input_dir = Path(input_dir)
        self.output_file = Path(output_file)

        # Find all database files
        self.db_files = list(self.input_dir.glob("*.rkdb"))
        print(f"Found {len(self.db_files)} database files to merge")

    def merge_databases_strategy1(self, strategy='union'):
        """Merge databases using re-counting strategy (most reliable)."""

        print(f"\n🔄 Merging databases using re-counting strategy...")
        start_time = time.time()

        # Extract original FASTA files if available
        fasta_files = []
        for db_file in self.db_files:
            # Look for corresponding FASTA file
            base_name = db_file.stem.replace('_k31', '').replace('_k21', '')
            possible_fasta = self.input_dir / f"{base_name}.fasta"
            if possible_fasta.exists():
                fasta_files.append(possible_fasta)

        if fasta_files:
            print(f"Found {len(fasta_files)} original FASTA files")
            return self._merge_from_fasta(fasta_files)
        else:
            print("No original FASTA files found, using database dump strategy")
            return self._merge_from_databases()

    def _merge_from_fasta(self, fasta_files):
        """Merge by re-counting from original FASTA files."""

        # Get k-mer size from first database
        with Database(str(self.db_files[0])) as db:
            stats = db.stats()
            k = stats.kmer_size

        print(f"Using k-mer size: {k}")

        # Create merged counter
        merged_counter = KmerCounter(k=k, canonical=True)

        # Count k-mers from all FASTA files
        for fasta_file in fasta_files:
            print(f"Processing: {fasta_file.name}")
            merged_counter.count_file(str(fasta_file))

        # Save merged database
        merged_counter.save_to_database(str(self.output_file))

        # Get statistics
        total_kmers = merged_counter.get_total_count()
        unique_kmers = merged_counter.get_unique_count()

        print(f"\n✅ Merge completed:")
        print(f"   Total k-mers: {total_kmers:,}")
        print(f"   Unique k-mers: {unique_kmers:,}")
        print(f"   Output file: {self.output_file}")

        return {
            'total_kmers': total_kmers,
            'unique_kmers': unique_kmers,
            'output_file': self.output_file,
            'input_files': len(fasta_files)
        }

    def _merge_from_databases(self):
        """Merge by extracting and re-counting from databases."""

        print("Extracting k-mers from databases...")

        # Get k-mer size from first database
        with Database(str(self.db_files[0])) as db:
            stats = db.stats()
            k = stats.kmer_size

        # Create temporary FASTA for all k-mers
        temp_fasta = self.input_dir / "temp_all_kmers.fasta"

        with open(temp_fasta, 'w') as out_f:
            kmer_count = 0

            for db_file in self.db_files:
                print(f"Extracting from: {db_file.name}")

                with Database(str(db_file)) as db:
                    # Dump all k-mers (consider using a limit for very large databases)
                    for result in db.dump(limit=1000000):  # Limit to 1M per database for demo
                        # Write k-mer with count as sequence name
                        out_f.write(f">kmer_{kmer_count}_count_{result.count}\n")
                        out_f.write(f"{result.canonical}\n")
                        kmer_count += 1

        print(f"Extracted {kmer_count:,} k-mers")

        # Re-count from extracted k-mers
        merged_counter = KmerCounter(k=k, canonical=True)
        merged_counter.count_file(str(temp_fasta))
        merged_counter.save_to_database(str(self.output_file))

        # Clean up temporary file
        temp_fasta.unlink()

        # Get statistics
        total_kmers = merged_counter.get_total_count()
        unique_kmers = merged_counter.get_unique_count()

        print(f"\n✅ Merge completed:")
        print(f"   Total k-mers: {total_kmers:,}")
        print(f"   Unique k-mers: {unique_kmers:,}")
        print(f"   Output file: {self.output_file}")

        return {
            'total_kmers': total_kmers,
            'unique_kmers': unique_kmers,
            'output_file': self.output_file,
            'input_files': len(self.db_files)
        }

    def create_merge_report(self, merge_result):
        """Create a detailed merge report."""

        # Get statistics for input databases
        input_stats = []

        for db_file in self.db_files:
            try:
                with Database(str(db_file)) as db:
                    stats = db.stats()
                    input_stats.append({
                        'Database': db_file.name,
                        'Unique_kmers': stats.unique_kmers,
                        'Total_counts': stats.total_counts,
                        'File_size_mb': db_file.stat().st_size / (1024*1024)
                    })
            except Exception as e:
                print(f"Could not read {db_file.name}: {e}")

        # Create summary
        total_input_kmers = sum(s['Unique_kmers'] for s in input_stats)
        merged_kmers = merge_result['unique_kmers']
        overlap_ratio = (total_input_kmers - merged_kmers) / total_input_kmers if total_input_kmers > 0 else 0

        report = f"""# Database Merge Report

## Summary
- **Input databases**: {len(self.db_files)}
- **Output database**: {self.output_file}
- **Merge strategy**: Re-counting from sources
- **Total input unique k-mers**: {total_input_kmers:,}
- **Merged unique k-mers**: {merged_kmers:,}
- **Overlap ratio**: {overlap_ratio:.2%}

## Input Databases
"""

        # Add input statistics table
        for stat in input_stats:
            report += f"""
- **{stat['Database']}**
  - Unique k-mers: {stat['Unique_kmers']:,}
  - Total counts: {stat['Total_counts']:,}
  - File size: {stat['File_size_mb']:.1f} MB
"""

        # Save report
        report_file = self.input_dir / "merge_report.md"
        with open(report_file, 'w') as f:
            f.write(report)

        print(f"\n📋 Merge report saved to: {report_file}")
        return report_file

# Usage
if __name__ == "__main__":
    # Example usage
    merger = DatabaseMerger(
        input_dir="results/databases/",
        output_file="results/merged_database.rkdb"
    )

    merge_result = merger.merge_databases_strategy1()
    merger.create_merge_report(merge_result)
```

---

## Strategy 3: Automated Pipeline

### Complete Batch Processing Pipeline

```python
#!/usr/bin/env python3
"""
Complete automated pipeline for batch k-mer analysis of multiple samples.
"""

import os
import sys
import time
import argparse
from pathlib import Path
import pandas as pd
import matplotlib.pyplot as plt
from concurrent.futures import ThreadPoolExecutor
import multiprocessing

# Import our custom classes
from batch_processor import BatchKmerProcessor
from batch_query import BatchKmerQuery
from database_merger import DatabaseMerger

class KmerAnalysisPipeline:
    """Complete automated pipeline for k-mer analysis."""

    def __init__(self, config):
        self.config = config
        self.results_dir = Path(config['results_dir'])
        self.results_dir.mkdir(parents=True, exist_ok=True)

    def run_complete_pipeline(self):
        """Run the complete analysis pipeline."""

        print("🧬 K-mer Analysis Pipeline")
        print("=" * 50)

        pipeline_start = time.time()

        # Step 1: Batch processing
        if self.config['run_batch_processing']:
            print(f"\n{'='*20} STEP 1: Batch Processing {'='*20}")
            self._run_batch_processing()

        # Step 2: Query analysis
        if self.config['run_query_analysis']:
            print(f"\n{'='*20} STEP 2: Query Analysis {'='*20}")
            self._run_query_analysis()

        # Step 3: Database merging
        if self.config['run_database_merging']:
            print(f"\n{'='*20} STEP 3: Database Merging {'='*20}")
            self._run_database_merging()

        # Step 4: Final analysis
        if self.config['run_final_analysis']:
            print(f"\n{'='*20} STEP 4: Final Analysis {'='*20}")
            self._run_final_analysis()

        # Step 5: Generate report
        print(f"\n{'='*20} STEP 5: Generate Report {'='*20}")
        self._generate_final_report(pipeline_start)

        print(f"\n🎉 Pipeline completed successfully!")
        print(f"Results saved to: {self.results_dir}")

    def _run_batch_processing(self):
        """Run batch processing of all samples."""

        processor = BatchKmerProcessor(
            input_dir=self.config['input_dir'],
            output_dir=self.results_dir / "databases",
            k=self.config['kmer_size'],
            workers=self.config.get('workers', multiprocessing.cpu_count())
        )

        self.batch_results = processor.process_all_files()
        self.batch_summary = processor.generate_summary_report(self.batch_results)

    def _run_query_analysis(self):
        """Run batch query analysis."""

        # Load queries
        queries = self._load_queries()

        # Find databases
        db_files = list((self.results_dir / "databases").glob("*.rkdb"))

        if not db_files:
            print("No databases found for query analysis")
            return

        batch_query = BatchKmerQuery(db_files, queries)
        self.query_results = batch_query.query_all_databases()

        # Create matrices
        self.presence_matrix = batch_query.create_presence_matrix()
        self.count_matrix = batch_query.create_count_matrix()
        self.kmer_analysis = batch_query.analyze_kmer_distribution()

        # Save results
        if self.presence_matrix is not None:
            self.presence_matrix.to_csv(self.results_dir / "presence_matrix.csv", index=False)
        if self.count_matrix is not None:
            self.count_matrix.to_csv(self.results_dir / "count_matrix.csv", index=False)
        if self.kmer_analysis is not None:
            self.kmer_analysis.to_csv(self.results_dir / "kmer_analysis.csv", index=False)

    def _run_database_merging(self):
        """Merge all databases."""

        merger = DatabaseMerger(
            input_dir=self.results_dir / "databases",
            output_file=self.results_dir / "merged_database.rkdb"
        )

        self.merge_result = merger.merge_databases_strategy1()
        self.merge_report = merger.create_merge_report(self.merge_result)

    def _run_final_analysis(self):
        """Run final comprehensive analysis."""

        print("Running comprehensive analysis...")

        # Create comparative plots
        self._create_comparative_plots()

        # Analyze sample relationships
        self._analyze_sample_relationships()

        # Generate statistics
        self._generate_statistics()

    def _load_queries(self):
        """Load queries from file or use defaults."""

        query_file = self.config.get('query_file')
        if query_file and Path(query_file).exists():
            with open(query_file) as f:
                queries = [line.strip() for line in f if line.strip()]
            print(f"Loaded {len(queries)} queries from {query_file}")
            return queries
        else:
            # Default queries for demonstration
            queries = [
                "ATCGATCGATCGATCGATCGATCGATCGATCGATCG",
                "GCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAG",
                "TTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTT"
            ]
            print(f"Using {len(queries)} default queries")
            return queries

    def _create_comparative_plots(self):
        """Create comparative visualization plots."""

        try:
            fig, axes = plt.subplots(2, 2, figsize=(15, 12))

            # Plot 1: Sample k-mer diversity
            if hasattr(self, 'batch_summary'):
                axes[0, 0].scatter(self.batch_summary['Total_kmers'],
                                 self.batch_summary['Unique_kmers'],
                                 alpha=0.6)
                axes[0, 0].set_xlabel('Total k-mers')
                axes[0, 0].set_ylabel('Unique k-mers')
                axes[0, 0].set_title('Sample K-mer Diversity')
                axes[0, 0].grid(True, alpha=0.3)

            # Plot 2: K-mer presence heatmap (subset)
            if hasattr(self, 'presence_matrix'):
                sample_presence = self.presence_matrix.iloc[:, 1:6]  # First 5 k-mers
                im = axes[0, 1].imshow(sample_presence.values, cmap='YlOrRd', aspect='auto')
                axes[0, 1].set_xticks(range(len(sample_presence.columns)))
                axes[0, 1].set_xticklabels([c[:8] + "..." for c in sample_presence.columns], rotation=45)
                axes[0, 1].set_yticks(range(len(sample_presence)))
                axes[0, 1].set_yticklabels(sample_presence['Sample'])
                axes[0, 1].set_title('K-mer Presence Heatmap')

            # Plot 3: K-mer frequency distribution
            if hasattr(self, 'kmer_analysis'):
                axes[1, 0].bar(range(len(self.kmer_analysis)),
                              self.kmer_analysis['samples_present'])
                axes[1, 0].set_xlabel('K-mer')
                axes[1, 0].set_ylabel('Samples with k-mer')
                axes[1, 0].set_title('K-mer Prevalence')
                axes[1, 0].set_xticks(range(len(self.kmer_analysis)))
                axes[1, 0].set_xticklabels([k[:8] + "..." for k in self.kmer_analysis['kmer']], rotation=45)

            # Plot 4: Database sizes
            if hasattr(self, 'batch_summary'):
                axes[1, 1].hist(self.batch_summary['Database_size_mb'], bins=10, alpha=0.7)
                axes[1, 1].set_xlabel('Database Size (MB)')
                axes[1, 1].set_ylabel('Number of Samples')
                axes[1, 1].set_title('Database Size Distribution')

            plt.tight_layout()
            plt.savefig(self.results_dir / "comparative_analysis.png", dpi=300, bbox_inches='tight')
            plt.close()

            print("Comparative plots saved to: comparative_analysis.png")

        except Exception as e:
            print(f"Warning: Could not create plots: {e}")

    def _analyze_sample_relationships(self):
        """Analyze relationships between samples."""

        if not hasattr(self, 'presence_matrix'):
            return

        # Calculate sample similarity based on k-mer presence
        sample_data = self.presence_matrix.iloc[:, 1:].values  # Exclude Sample column

        # Simple Jaccard similarity
        n_samples = len(sample_data)
        similarity_matrix = [[0] * n_samples for _ in range(n_samples)]

        for i in range(n_samples):
            for j in range(n_samples):
                intersection = sum(a and b for a, b in zip(sample_data[i], sample_data[j]))
                union = sum(a or b for a, b in zip(sample_data[i], sample_data[j]))
                similarity = intersection / union if union > 0 else 0
                similarity_matrix[i][j] = similarity

        # Create similarity DataFrame
        sample_names = self.presence_matrix['Sample'].tolist()
        self.similarity_df = pd.DataFrame(
            similarity_matrix,
            index=sample_names,
            columns=sample_names
        )

        # Save similarity matrix
        self.similarity_df.to_csv(self.results_dir / "sample_similarity.csv")

    def _generate_statistics(self):
        """Generate comprehensive statistics."""

        stats = {
            'total_samples': len(self.batch_summary) if hasattr(self, 'batch_summary') else 0,
            'total_kmers': self.batch_summary['Total_kmers'].sum() if hasattr(self, 'batch_summary') else 0,
            'unique_kmers_per_sample': self.batch_summary['Unique_kmers'].mean() if hasattr(self, 'batch_summary') else 0,
            'queries_tested': len(self.kmer_analysis) if hasattr(self, 'kmer_analysis') else 0,
            'merged_database_size_mb': self.merge_result['output_file'].stat().st_size / (1024*1024) if hasattr(self, 'merge_result') else 0
        }

        self.statistics = stats

        # Save statistics
        with open(self.results_dir / "pipeline_statistics.txt", 'w') as f:
            f.write("Pipeline Statistics\n")
            f.write("=" * 20 + "\n")
            for key, value in stats.items():
                if isinstance(value, float):
                    f.write(f"{key}: {value:.2f}\n")
                else:
                    f.write(f"{key}: {value:,}\n")

    def _generate_final_report(self, pipeline_start):
        """Generate final comprehensive report."""

        pipeline_time = time.time() - pipeline_start

        report = f"""# K-mer Analysis Pipeline Report

## Summary
- **Input directory**: {self.config['input_dir']}
- **K-mer size**: {self.config['kmer_size']}
- **Pipeline runtime**: {pipeline_time:.1f} seconds
- **Results directory**: {self.results_dir}

## Pipeline Steps Completed
"""

        if self.config['run_batch_processing']:
            report += f"✅ Batch Processing - {self.statistics.get('total_samples', 0)} samples\n"
        if self.config['run_query_analysis']:
            report += f"✅ Query Analysis - {self.statistics.get('queries_tested', 0)} k-mers\n"
        if self.config['run_database_merging']:
            report += f"✅ Database Merging - Single merged database created\n"
        if self.config['run_final_analysis']:
            report += f"✅ Final Analysis - Comprehensive analysis completed\n"

        report += f"""

## Key Results
- **Total samples processed**: {self.statistics.get('total_samples', 0):,}
- **Total k-mers across all samples**: {self.statistics.get('total_kmers', 0):,}
- **Average unique k-mers per sample**: {self.statistics.get('unique_kmers_per_sample', 0):.0f}
- **Merged database size**: {self.statistics.get('merged_database_size_mb', 0):.1f} MB

## Output Files
- **batch_processing_summary.csv**: Summary of sample processing
- **presence_matrix.csv**: Binary presence of query k-mers
- **count_matrix.csv**: K-mer counts across samples
- **kmer_analysis.csv**: Analysis of k-mer distribution
- **sample_similarity.csv**: Sample similarity matrix
- **merged_database.rkdb**: Merged k-mer database
- **comparative_analysis.png**: Visual analysis plots
- **pipeline_statistics.txt**: Pipeline performance statistics

## Generated Files
"""

        # List all generated files
        for file_path in sorted(self.results_dir.rglob("*")):
            if file_path.is_file():
                size_mb = file_path.stat().st_size / (1024*1024)
                report += f"- **{file_path.name}**: {size_mb:.1f} MB\n"

        # Save report
        report_file = self.results_dir / "pipeline_report.md"
        with open(report_file, 'w') as f:
            f.write(report)

        print(f"Final report saved to: {report_file}")

def main():
    """Main function to run the pipeline."""

    parser = argparse.ArgumentParser(description='K-mer Analysis Pipeline')
    parser.add_argument('--input-dir', required=True, help='Input directory with FASTA files')
    parser.add_argument('--results-dir', required=True, help='Output directory for results')
    parser.add_argument('--kmer-size', type=int, default=31, help='K-mer size (default: 31)')
    parser.add_argument('--query-file', help='File with query k-mers')
    parser.add_argument('--workers', type=int, help='Number of worker threads')
    parser.add_argument('--skip-batch', action='store_true', help='Skip batch processing')
    parser.add_argument('--skip-query', action='store_true', help='Skip query analysis')
    parser.add_argument('--skip-merge', action='store_true', help='Skip database merging')
    parser.add_argument('--skip-analysis', action='store_true', help='Skip final analysis')

    args = parser.parse_args()

    # Create configuration
    config = {
        'input_dir': args.input_dir,
        'results_dir': args.results_dir,
        'kmer_size': args.kmer_size,
        'query_file': args.query_file,
        'workers': args.workers,
        'run_batch_processing': not args.skip_batch,
        'run_query_analysis': not args.skip_query,
        'run_database_merging': not args.skip_merge,
        'run_final_analysis': not args.skip_analysis
    }

    # Run pipeline
    pipeline = KmerAnalysisPipeline(config)
    pipeline.run_complete_pipeline()

if __name__ == "__main__":
    main()
```

---

## Performance Tips for Batch Processing

### 1. Memory Management
```python
# Process files in smaller batches
batch_size = 50  # Adjust based on available memory

# Use context managers
with Database(db_file) as db:
    # Automatic cleanup
    pass

# Clear intermediate results
del large_data_structure
import gc
gc.collect()
```

### 2. Parallel Processing
```python
# Optimal worker count
import multiprocessing
optimal_workers = min(multiprocessing.cpu_count(), 8)  # Don't exceed 8 for I/O bound tasks

# Use process pools for CPU-intensive tasks
from concurrent.futures import ProcessPoolExecutor
```

### 3. Storage Optimization
```python
# Compress intermediate files
import gzip

# Use SSD storage for better I/O performance
fast_storage_dir = "/fast_nvme_storage/temp"

# Clean up temporary files
import shutil
shutil.rmtree(temp_dir)
```

---

## Troubleshooting Batch Processing

### Common Issues

1. **Memory Overflow**:
   ```python
   # Reduce chunk size
   chunk_size = 50000  # Instead of 500000

   # Process fewer files in parallel
   workers = 2  # Instead of 8
   ```

2. **Database Corruption**:
   ```python
   # Validate databases before merging
   for db_file in database_files:
       try:
           with Database(db_file) as db:
               stats = db.stats()
               print(f"✅ {db_file.name}: {stats.unique_kmers:,} k-mers")
       except Exception as e:
           print(f"❌ {db_file.name}: {e}")
   ```

3. **Slow Performance**:
   ```python
   # Profile your pipeline
   import cProfile
   cProfile.run('your_function()')

   # Monitor resource usage
   import psutil
   print(f"CPU: {psutil.cpu_percent()}%")
   print(f"Memory: {psutil.virtual_memory().percent}%")
   ```

---

## Next Steps

- **Scale to clusters**: Distribute processing across multiple machines
- **Advanced queries**: Fuzzy queries with position mutations
- **Machine learning**: Use k-mer features for classification
- **Visualization**: Interactive dashboards for k-mer analysis

## Related Documentation

- [Python API Reference](../api-reference/python/)
- [Large Genomes Tutorial](large-genomes.md)
- [Integration Tutorial](integration.md)
- [Performance Tips](../user-guide/performance-tips.md)