#!/usr/bin/env python3
"""
Complete RustKmer Pipeline Example

This script demonstrates a complete k-mer analysis pipeline including:
1. Counting k-mers from FASTA/FASTQ files
2. Database operations (query, statistics, export)
3. Fuzzy searching for variant detection
4. Merging multiple databases
5. Performance monitoring and reporting
"""

import sys
import os
import time
import json
import argparse
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional

# Import RustKmer modules
try:
    from rustkmer import (
        KmerCounter, Database, QueryResult,
        FuzzyQueryEngine, FuzzyQueryConfig,
        DatabaseExporter, ExportConfig, ExportFormat,
        DatabaseMerger, MergeConfig
    )
    from rustkmer.stats import StatisticsCalculator
    from rustkmer.utils import SequenceReader
    from rustkmer.exceptions import RustKmerError
except ImportError as e:
    print("Error: Could not import rustkmer module.")
    print("Please install with: cd python && maturin develop --release")
    sys.exit(1)


class KmerAnalysisPipeline:
    """Complete k-mer analysis pipeline."""

    def __init__(self, config: Dict[str, Any]):
        """Initialize pipeline with configuration."""
        self.config = config
        self.logger = self._setup_logging()
        self.results = {}

    def _setup_logging(self) -> logging.Logger:
        """Setup logging configuration."""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )
        return logging.getLogger(__name__)

    def count_kmers(self, input_file: str, k: int = 31) -> Database:
        """Count k-mers from input file."""
        self.logger.info(f"Counting {k}-mers from {input_file}")

        start_time = time.time()

        # Create counter with configuration
        counter = KmerCounter(
            k=k,
            threads=self.config.get('threads', 4),
            canonical=self.config.get('canonical', True)
        )

        # Count k-mers with progress tracking
        progress_calls = []

        def progress_callback(processed: int, total: int):
            progress_calls.append((processed, total))
            if total > 0 and processed % 1000 == 0:
                percent = (processed / total) * 100
                self.logger.info(f"  Progress: {percent:.1f}% ({processed}/{total} sequences)")

        # Process file
        database = counter.count_from_file(
            input_file,
            low_memory=self.config.get('low_memory', False),
            progress_callback=progress_callback
        )

        elapsed = time.time() - start_time

        # Store results
        self.results['counting'] = {
            'input_file': input_file,
            'k': k,
            'total_kmers': database.total_kmers,
            'unique_kmers': database.get_stats().cardinality,
            'processing_time': elapsed,
            'progress_updates': len(progress_calls)
        }

        self.logger.info(f"  Completed in {elapsed:.2f} seconds")
        self.logger.info(f"  Total k-mers: {database.total_kmers:,}")
        self.logger.info(f"  Unique k-mers: {database.get_stats().cardinality:,}")

        return database

    def analyze_database(self, database: Database) -> Dict[str, Any]:
        """Perform comprehensive database analysis."""
        self.logger.info("Analyzing database...")

        start_time = time.time()

        # Get basic statistics
        basic_stats = database.get_stats()

        # Calculate detailed statistics
        calc = StatisticsCalculator()
        detailed_stats = calc.calculate_all_stats(database)

        elapsed = time.time() - start_time

        # Prepare analysis results
        analysis = {
            'basic_stats': {
                'kmer_size': basic_stats.kmer_size,
                'total_kmers': basic_stats.total_kmers,
                'cardinality': basic_stats.cardinality,
                'max_count': basic_stats.max_count,
                'avg_count': basic_stats.avg_count
            },
            'frequency_stats': {
                'mean': detailed_stats['frequency'].mean,
                'median': detailed_stats['frequency'].median,
                'std_dev': detailed_stats['frequency'].std_dev,
                'min': detailed_stats['frequency'].min_val,
                'max': detailed_stats['frequency'].max_val
            },
            'composition_stats': {
                'gc_content': detailed_stats['composition'].gc_content,
                'at_content': detailed_stats['composition'].at_content,
                'a_content': detailed_stats['composition'].a_content,
                't_content': detailed_stats['composition'].t_content,
                'g_content': detailed_stats['composition'].g_content,
                'c_content': detailed_stats['composition'].c_content
            },
            'analysis_time': elapsed
        }

        self.results['analysis'] = analysis

        # Log key findings
        self.logger.info(f"  K-mer size: {basic_stats.kmer_size}")
        self.logger.info(f"  GC content: {detailed_stats['composition'].gc_content:.2%}")
        self.logger.info(f"  Mean abundance: {detailed_stats['frequency'].mean:.2f}")
        self.logger.info(f"  Analysis completed in {elapsed:.2f} seconds")

        return analysis

    def query_kmers(self, database: Database, kmer_list: List[str]) -> List[QueryResult]:
        """Query specific k-mers in database."""
        self.logger.info(f"Querying {len(kmer_list)} k-mers")

        start_time = time.time()

        # Query k-mers
        results = database.query_multiple(kmer_list)

        elapsed = time.time() - start_time

        # Count found k-mers
        found_count = sum(1 for r in results if r.found)
        total_count = sum(r.count for r in results if r.found)

        # Store results
        self.results['query'] = {
            'total_queries': len(kmer_list),
            'found_kmers': found_count,
            'total_count': total_count,
            'query_time': elapsed,
            'avg_time_per_query': elapsed / len(kmer_list)
        }

        self.logger.info(f"  Found {found_count}/{len(kmer_list)} k-mers")
        self.logger.info(f"  Total occurrences: {total_count:,}")
        self.logger.info(f"  Query completed in {elapsed:.3f} seconds")

        return results

    def fuzzy_search(self, database: Database, queries: List[str],
                    max_distance: int = 2) -> Dict[str, List]:
        """Perform fuzzy k-mer search."""
        self.logger.info(f"Performing fuzzy search on {len(queries)} queries")

        start_time = time.time()

        # Configure fuzzy search
        config = FuzzyQueryConfig(
            max_distance=max_distance,
            max_results=self.config.get('max_fuzzy_results', 10),
            include_counts=True,
            sort_by_distance=True
        )

        # Create and configure engine
        engine = FuzzyQueryEngine(config)
        engine.attach_database(database)

        # Perform searches
        results = {}
        for query in queries:
            fuzzy_results = engine.query(query)
            results[query] = fuzzy_results

        elapsed = time.time() - start_time

        # Calculate statistics
        total_matches = sum(len(matches) for matches in results.values())

        # Store results
        self.results['fuzzy_search'] = {
            'queries': len(queries),
            'total_matches': total_matches,
            'max_distance': max_distance,
            'search_time': elapsed
        }

        self.logger.info(f"  Found {total_matches} total matches")
        self.logger.info(f"  Fuzzy search completed in {elapsed:.2f} seconds")

        return results

    def export_database(self, database: Database, output_dir: str,
                        formats: List[str] = None) -> Dict[str, str]:
        """Export database in multiple formats."""
        if formats is None:
            formats = ['text', 'json', 'csv']

        self.logger.info(f"Exporting database in {formats} formats")

        start_time = time.time()
        output_files = {}

        for fmt in formats:
            output_path = Path(output_dir) / f"database_export.{fmt}"

            # Configure export
            export_config = ExportConfig(
                format=ExportFormat[fmt.upper()],
                include_header=True,
                include_stats=True,
                sort_by_count=True
            )

            # Export database
            exporter = DatabaseExporter(export_config)
            exporter.export(database, str(output_path))

            output_files[fmt] = str(output_path)

        elapsed = time.time() - start_time

        # Store results
        self.results['export'] = {
            'formats': formats,
            'output_files': output_files,
            'export_time': elapsed
        }

        self.logger.info(f"  Export completed in {elapsed:.2f} seconds")
        for fmt, path in output_files.items():
            size_mb = Path(path).stat().st_size / 1024 / 1024
            self.logger.info(f"  {fmt.upper()}: {path} ({size_mb:.2f} MB)")

        return output_files

    def merge_databases(self, databases: List[Database], output_file: str) -> Dict[str, Any]:
        """Merge multiple databases."""
        self.logger.info(f"Merging {len(databases)} databases")

        start_time = time.time()

        # Configure merge
        config = MergeConfig(
            threads=self.config.get('threads', 4),
            max_memory_mb=self.config.get('max_memory_mb', 1024),
            validate_checksums=True,
            preserve_metadata=True
        )

        # Perform merge
        merger = DatabaseMerger(config)
        merge_result = merger.merge_databases(databases, output_file)

        elapsed = time.time() - start_time

        # Store results
        merge_info = {
            'total_databases': merge_result.total_databases,
            'successful_merges': merge_result.successful_merges,
            'total_kmers': merge_result.total_kmers,
            'unique_kmers': merge_result.total_unique_kmers,
            'duplicate_rate': merge_result.duplicate_rate,
            'output_size': merge_result.output_size_bytes,
            'merge_time': elapsed
        }

        self.results['merge'] = merge_info

        self.logger.info(f"  Merged {merge_result.successful_merges} databases")
        self.logger.info(f"  Total k-mers: {merge_result.total_kmers:,}")
        self.logger.info(f"  Unique k-mers: {merge_result.total_unique_kmers:,}")
        self.logger.info(f"  Duplicate rate: {merge_result.duplicate_rate:.2%}")
        self.logger.info(f"  Merge completed in {elapsed:.2f} seconds")

        return merge_info

    def run_complete_pipeline(self, input_files: List[str], output_dir: str,
                             kmer_list: List[str] = None,
                             fuzzy_queries: List[str] = None) -> Dict[str, Any]:
        """Run complete analysis pipeline."""
        self.logger.info("Starting complete k-mer analysis pipeline")
        self.logger.info(f"Input files: {input_files}")
        self.logger.info(f"Output directory: {output_dir}")

        # Create output directory
        os.makedirs(output_dir, exist_ok=True)

        all_databases = []
        pipeline_start = time.time()

        try:
            # Step 1: Count k-mers for each file
            for input_file in input_files:
                db = self.count_kmers(input_file, k=self.config.get('k', 31))
                all_databases.append(db)

                # Analyze individual database
                self.analyze_database(db)

            # Step 2: Merge databases if multiple
            if len(all_databases) > 1:
                merged_file = os.path.join(output_dir, "merged_database.rkdb")
                self.merge_databases(all_databases, merged_file)

                # Load merged database for further analysis
                merged_db = Database()
                merged_db.load(merged_file)
                analysis_db = merged_db
            else:
                analysis_db = all_databases[0]

            # Step 3: Analyze final database
            final_analysis = self.analyze_database(analysis_db)

            # Step 4: Query specific k-mers
            if kmer_list:
                self.query_kmers(analysis_db, kmer_list)

            # Step 5: Perform fuzzy search
            if fuzzy_queries:
                self.fuzzy_search(analysis_db, fuzzy_queries)

            # Step 6: Export database
            self.export_database(analysis_db, output_dir)

            # Step 7: Generate report
            total_time = time.time() - pipeline_start
            self._generate_report(output_dir, total_time)

            self.logger.info(f"Pipeline completed successfully in {total_time:.2f} seconds")
            return self.results

        except RustKmerError as e:
            self.logger.error(f"Pipeline failed with RustKmer error: {e}")
            raise
        except Exception as e:
            self.logger.error(f"Pipeline failed with unexpected error: {e}")
            raise

    def _generate_report(self, output_dir: str, total_time: float):
        """Generate comprehensive analysis report."""
        report = {
            'pipeline_config': self.config,
            'results': self.results,
            'total_time': total_time,
            'timestamp': time.strftime('%Y-%m-%d %H:%M:%S')
        }

        # Save JSON report
        report_file = os.path.join(output_dir, "analysis_report.json")
        with open(report_file, 'w') as f:
            json.dump(report, f, indent=2)

        # Generate text summary
        summary_file = os.path.join(output_dir, "analysis_summary.txt")
        with open(summary_file, 'w') as f:
            f.write("RustKmer Analysis Pipeline Report\n")
            f.write("=" * 40 + "\n\n")
            f.write(f"Total processing time: {total_time:.2f} seconds\n\n")

            # Counting summary
            if 'counting' in self.results:
                counting = self.results['counting']
                f.write("K-mer Counting:\n")
                f.write(f"  Input file: {counting['input_file']}\n")
                f.write(f"  K-mer size: {counting['k']}\n")
                f.write(f"  Total k-mers: {counting['total_kmers']:,}\n")
                f.write(f"  Unique k-mers: {counting['unique_kmers']:,}\n")
                f.write(f"  Processing time: {counting['processing_time']:.2f}s\n\n")

            # Analysis summary
            if 'analysis' in self.results:
                analysis = self.results['analysis']
                f.write("Database Analysis:\n")
                f.write(f"  GC content: {analysis['composition_stats']['gc_content']:.2%}\n")
                f.write(f"  Mean abundance: {analysis['frequency_stats']['mean']:.2f}\n")
                f.write(f"  Max abundance: {analysis['frequency_stats']['max']}\n\n")

            # Query summary
            if 'query' in self.results:
                query = self.results['query']
                f.write("K-mer Queries:\n")
                f.write(f"  Queries performed: {query['total_queries']}\n")
                f.write(f"  K-mers found: {query['found_kmers']}\n")
                f.write(f"  Query time: {query['query_time']:.3f}s\n\n")

            # Export summary
            if 'export' in self.results:
                export = self.results['export']
                f.write("Database Export:\n")
                for fmt, path in export['output_files'].items():
                    size_mb = Path(path).stat().st_size / 1024 / 1024
                    f.write(f"  {fmt.upper()}: {size_mb:.2f} MB\n")

        self.logger.info(f"Report generated: {report_file}")
        self.logger.info(f"Summary generated: {summary_file}")


def main():
    """Main function with command-line interface."""
    parser = argparse.ArgumentParser(
        description="Complete RustKmer k-mer analysis pipeline",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Analyze single file
  python complete_pipeline.py input.fasta output_dir

  # Analyze multiple files with custom k-mer size
  python complete_pipeline.py file1.fasta file2.fastq output_dir -k 21

  # Include queries and fuzzy search
  python complete_pipeline.py input.fasta output_dir \\
    --query ATCGATCG GCTAGCTA \\
    --fuzzy ATCGATCG GCTAGCTA TTTTTTTT

  # Performance configuration
  python complete_pipeline.py input.fasta output_dir \\
    --threads 8 --max-memory 4096
        """
    )

    parser.add_argument('input_files', nargs='+',
                       help='Input FASTA/FASTQ files to analyze')
    parser.add_argument('output_dir',
                       help='Output directory for results')
    parser.add_argument('-k', '--kmer-size', type=int, default=31,
                       help='K-mer size (default: 31)')
    parser.add_argument('-t', '--threads', type=int, default=4,
                       help='Number of threads to use (default: 4)')
    parser.add_argument('--max-memory', type=int, default=1024,
                       help='Maximum memory in MB for merging (default: 1024)')
    parser.add_argument('--low-memory', action='store_true',
                       help='Use low memory mode for counting')
    parser.add_argument('--query', nargs='*',
                       help='K-mers to query in database')
    parser.add_argument('--fuzzy', nargs='*',
                       help='K-mers for fuzzy search')
    parser.add_argument('--max-fuzzy-results', type=int, default=10,
                       help='Maximum results per fuzzy query (default: 10)')
    parser.add_argument('--export-formats', nargs='+',
                       choices=['text', 'json', 'csv'],
                       default=['text', 'json'],
                       help='Export formats (default: text json)')

    args = parser.parse_args()

    # Configuration
    config = {
        'k': args.kmer_size,
        'threads': args.threads,
        'max_memory_mb': args.max_memory,
        'low_memory': args.low_memory,
        'max_fuzzy_results': args.max_fuzzy_results,
        'canonical': True
    }

    # Create and run pipeline
    pipeline = KmerAnalysisPipeline(config)

    try:
        results = pipeline.run_complete_pipeline(
            input_files=args.input_files,
            output_dir=args.output_dir,
            kmer_list=args.query,
            fuzzy_queries=args.fuzzy
        )

        print("\n✓ Pipeline completed successfully!")
        print(f"Results saved to: {args.output_dir}")

    except Exception as e:
        print(f"\n✗ Pipeline failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()