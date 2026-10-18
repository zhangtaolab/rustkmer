<!-- generated-by: gsd-doc-writer -->
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
- Python 3.11+ with RustKmer installed (`pip install pyrustkmer`)
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

Note that `PyCounter` parallelizes counting internally via Rayon (see its `threads` argument), so a simple loop over files already uses all cores per file. A separate Python thread pool on top usually adds little and can oversubscribe the machine.

```python
#!/usr/bin/env python3
"""
Batch processing of multiple FASTA files for k-mer analysis.
"""

import time
import pandas as pd
from pathlib import Path
from pyrustkmer import PyCounter

class BatchKmerProcessor:
    """Efficient batch processor for multiple FASTA files."""

    def __init__(self, input_dir, output_dir, k=31, workers=None):
        self.input_dir = Path(input_dir)
        self.output_dir = Path(output_dir)
        self.k = k
        # `workers` is accepted for interface compatibility; counting itself
        # is already parallelized inside PyCounter via Rayon.
        self.workers = workers

        # Create output directory
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # Find all FASTA files
        self.fasta_files = list(self.input_dir.glob("*.fasta")) + \
                          list(self.input_dir.glob("*.fa")) + \
                          list(self.input_dir.glob("*.fa.gz")) + \
                          list(self.input_dir.glob("*.fasta.gz"))

        print(f"Found {len(self.fasta_files)} FASTA files")

    def process_all_files(self):
        """Process all FASTA files."""

        print(f"\nProcessing {len(self.fasta_files)} files...")
        start_time = time.time()

        results = {}
        for fasta_file in self.fasta_files:
            try:
                result = self._process_single_file(fasta_file)
                results[fasta_file] = result
                print(f"Processed: {fasta_file.name}")
            except Exception as e:
                print(f"Failed to process {fasta_file.name}: {e}")
                results[fasta_file] = None

        processing_time = time.time() - start_time
        successful = sum(1 for r in results.values() if r is not None)

        print(f"\nProcessing Summary:")
        print(f"   Total files: {len(self.fasta_files)}")
        print(f"   Successful: {successful}")
        print(f"   Failed: {len(self.fasta_files) - successful}")
        print(f"   Processing time: {processing_time:.1f} seconds")
        if self.fasta_files:
            print(f"   Average time per file: {processing_time/len(self.fasta_files):.1f} seconds")

        return results

    def _process_single_file(self, fasta_file):
        """Process a single FASTA file and create k-mer database."""

        # Generate output filename
        db_file = self.output_dir / f"{fasta_file.stem}_k{self.k}.rkdb"

        # Skip if already processed
        if db_file.exists():
            print(f"Skipping {fasta_file.name} (already processed)")
            return {
                'input_file': fasta_file,
                'output_file': db_file,
                'status': 'skipped',
                'total_kmers': 0,
                'unique_kmers': 0
            }

        print(f"Processing {fasta_file.name}...")

        # Create k-mer counter (counting is parallelized internally by Rayon)
        counter = PyCounter(self.k, canonical=True)

        # Count k-mers from file (.gz/.bz2/.xz compression is handled
        # transparently by add_from_fasta)
        counter.add_from_fasta(str(fasta_file))

        # Get statistics
        stats = counter.get_stats()

        # Save database
        counter.save_database(str(db_file))

        return {
            'input_file': fasta_file,
            'output_file': db_file,
            'status': 'success',
            'total_kmers': stats.total_kmers,
            'unique_kmers': stats.unique_kmers
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
        print(f"\nSummary report saved to: {summary_file}")

        # Print statistics
        if len(df) > 0:
            print(f"\nBatch Processing Statistics:")
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
        k=31
    )

    results = processor.process_all_files()
    summary_df = processor.generate_summary_report(results)
```

### Batch Querying Across Samples

```python
from pathlib import Path
import pandas as pd
from pyrustkmer import PyDatabase, LoadMode

class BatchKmerQuery:
    """Efficient batch k-mer querying across multiple samples."""

    def __init__(self, database_files, queries):
        self.database_files = database_files
        self.queries = queries
        self.results = {}

    def query_all_databases(self):
        """Query all databases for all k-mers."""

        print(f"Querying {len(self.queries)} k-mers across {len(self.database_files)} databases")

        for db_file in self.database_files:
            try:
                db_results = self._query_single_database(db_file)
                self.results[db_file] = db_results
                print(f"Queried: {db_file.name}")
            except Exception as e:
                print(f"Failed to query {db_file.name}: {e}")
                self.results[db_file] = None

        return self.results

    def _query_single_database(self, db_file):
        """Query a single database for all k-mers."""

        results = {}

        # LoadMode is a required second constructor argument
        db = PyDatabase(str(db_file), LoadMode.Preload)

        for query in self.queries:
            try:
                result = db.query_exact(query)
                results[query] = {
                    'count': result.count,
                    'present': result.found
                }
            except Exception as e:
                print(f"Query failed for {query[:10]}...: {e}")
                results[query] = {'count': 0, 'present': False}

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
        valid_results = [r for r in self.results.values() if r]

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
                'samples_total': len(valid_results),
                'presence_frequency': presence_count / len(valid_results) if valid_results else 0,
                'total_kmer_counts': total_count,
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

For pure exact-match workloads, `PyDatabase.query_exact_batch(queries)` performs the batch lookup in one call and returns a dict of `{kmer: PyQueryResult}`.

---

## Strategy 2: Database Merging

### Merge Multiple K-mer Databases

`PyDatabase.merge()` is a static method that merges multiple `.rkdb` files into one output file. It goes through the same bounded core as the CLI's `merge` command: the total k-mer count is read from the input headers, compared against the memory budget, and the merge is routed to an in-memory or streaming path accordingly. The output file is written directly by the merge — the merged database is never held in RAM.

```python
#!/usr/bin/env python3
"""
Merge multiple k-mer databases into a single comprehensive database.
"""

from pathlib import Path
from pyrustkmer import PyDatabase, LoadMode

class DatabaseMerger:
    """Merge multiple k-mer databases efficiently."""

    def __init__(self, input_dir, output_file):
        self.input_dir = Path(input_dir)
        self.output_file = Path(output_file)

        # Find all database files
        self.db_files = list(self.input_dir.glob("*.rkdb"))
        print(f"Found {len(self.db_files)} database files to merge")

    def merge_databases(self, max_memory=None, merge_mode="auto"):
        """Merge databases using PyDatabase.merge().

        Args:
            max_memory: Optional memory budget string (e.g. "4GB", "512MB").
                Defaults to 50% of system memory when omitted.
            merge_mode: "auto" (default), "memory", or "streaming" — same
                semantics as the CLI's --merge-mode flag.
        """

        print(f"\nMerging databases...")
        input_paths = [str(f) for f in self.db_files]

        # Static call: writes the merged output file directly
        PyDatabase.merge(
            input_paths,
            str(self.output_file),
            max_memory=max_memory,
            merge_mode=merge_mode,
        )

        # Read back statistics from the merged database
        merged = PyDatabase(str(self.output_file), LoadMode.Preload)
        stats = merged.get_stats()

        print(f"\nMerge completed:")
        print(f"   Unique k-mers: {stats.unique_kmers:,}")
        print(f"   Output file: {self.output_file}")

        return {
            'unique_kmers': stats.unique_kmers,
            'total_kmers': stats.total_kmers,
            'output_file': self.output_file,
            'input_files': len(self.db_files)
        }

    def create_merge_report(self, merge_result):
        """Create a detailed merge report."""

        # Get statistics for input databases
        input_stats = []

        for db_file in self.db_files:
            try:
                db = PyDatabase(str(db_file), LoadMode.Lazy)
                stats = db.get_stats()
                input_stats.append({
                    'Database': db_file.name,
                    'Unique_kmers': stats.unique_kmers,
                    'Total_kmers': stats.total_kmers,
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
- **Merge strategy**: PyDatabase.merge (memory-bounded, streaming when over budget)
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
  - Total k-mers: {stat['Total_kmers']:,}
  - File size: {stat['File_size_mb']:.1f} MB
"""

        # Save report
        report_file = self.input_dir / "merge_report.md"
        with open(report_file, 'w') as f:
            f.write(report)

        print(f"\nMerge report saved to: {report_file}")
        return report_file

# Usage
if __name__ == "__main__":
    # Example usage
    merger = DatabaseMerger(
        input_dir="results/databases/",
        output_file="results/merged_database.rkdb"
    )

    merge_result = merger.merge_databases(max_memory="4GB")
    merger.create_merge_report(merge_result)
```

`merge_mode="memory"` refuses to run over budget instead of risking an OOM (raising a `RuntimeError`), while `"streaming"` always streams. Invalid `merge_mode` or `max_memory` values raise `ValueError` at the Python boundary.

---

## Strategy 3: Automated Pipeline

### Complete Batch Processing Pipeline

```python
#!/usr/bin/env python3
"""
Complete automated pipeline for batch k-mer analysis of multiple samples.
"""

import time
import argparse
from pathlib import Path
import pandas as pd
import matplotlib.pyplot as plt
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

        print("K-mer Analysis Pipeline")
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

        print(f"\nPipeline completed successfully!")
        print(f"Results saved to: {self.results_dir}")

    def _run_batch_processing(self):
        """Run batch processing of all samples."""

        processor = BatchKmerProcessor(
            input_dir=self.config['input_dir'],
            output_dir=self.results_dir / "databases",
            k=self.config['kmer_size'],
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

        self.merge_result = merger.merge_databases(max_memory=self.config.get('max_memory'))
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
            report += f"Completed Batch Processing - {self.statistics.get('total_samples', 0)} samples\n"
        if self.config['run_query_analysis']:
            report += f"Completed Query Analysis - {self.statistics.get('queries_tested', 0)} k-mers\n"
        if self.config['run_database_merging']:
            report += f"Completed Database Merging - Single merged database created\n"
        if self.config['run_final_analysis']:
            report += f"Completed Final Analysis - Comprehensive analysis completed\n"

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
    parser.add_argument('--max-memory', help='Memory budget for the merge (e.g. 4GB)')
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
        'max_memory': args.max_memory,
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

# Free databases you no longer need (PyDatabase is NOT a context manager —
# drop the reference and let garbage collection reclaim it)
del db
import gc
gc.collect()

# For large databases, load with LoadMode.Lazy instead of Preload:
# Preload caches every k-mer in memory, Lazy keeps a sorted index for
# binary-search lookups
db = PyDatabase("big.rkdb", LoadMode.Lazy)

# Clear intermediate results
del large_data_structure
gc.collect()
```

### 2. Parallel Processing
```python
# Counting is already parallel inside PyCounter via its `threads` argument:
counter = PyCounter(31, canonical=True, threads=8)

# Use process pools for CPU-intensive Python-side post-processing
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
   # Process fewer files at once and free databases between stages
   del db
   gc.collect()

   # Bound the merge with an explicit budget so it streams instead of
   # loading everything into RAM
   PyDatabase.merge(inputs, "merged.rkdb", max_memory="4GB", merge_mode="streaming")
   ```

2. **Database Corruption**:
   ```python
   # Validate databases before merging
   from pyrustkmer import PyDatabase, LoadMode

   for db_file in database_files:
       try:
           db = PyDatabase(str(db_file), LoadMode.Lazy)
           stats = db.get_stats()
           print(f"OK {db_file.name}: {stats.unique_kmers:,} k-mers")
       except Exception as e:
           print(f"FAILED {db_file.name}: {e}")
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
