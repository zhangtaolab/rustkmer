#!/usr/bin/env python3
"""
RustKmer Real-World Genomics Pipeline

This example demonstrates a realistic genomics analysis pipeline:
1. Quality control of sequencing data
2. K-mer counting with multiple parameters
3. Database creation and management
4. Comparative analysis between samples
5. Statistical analysis and reporting

Author: RustKmer Team
"""

import os
import sys
import json
import time
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path
from collections import defaultdict
from rustkmer import KmerCounter, Database, FuzzyQuery
from rustkmer import SequenceError, DatabaseError

class GenomicsPipeline:
    """A complete genomics analysis pipeline using RustKmer"""

    def __init__(self, config_file=None):
        """Initialize the pipeline with configuration"""
        self.config = self.load_config(config_file) if config_file else self.default_config()
        self.results = defaultdict(dict)
        self.start_time = time.time()

    def default_config(self):
        """Default pipeline configuration"""
        return {
            "k_sizes": [21, 31, 51],  # Multiple k-mer sizes for analysis
            "canonical": True,  # Use canonical k-mers
            "threads": 4,  # Number of threads for parallel processing
            "min_abundance": 2,  # Minimum k-mer abundance threshold
            "output_dir": "pipeline_output",
            "samples": {
                "control": ["control_rep1.fastq", "control_rep2.fastq"],
                "treatment": ["treatment_rep1.fastq", "treatment_rep2.fastq", "treatment_rep3.fastq"]
            }
        }

    def load_config(self, config_file):
        """Load configuration from JSON file"""
        with open(config_file, 'r') as f:
            return json.load(f)

    def create_output_directory(self):
        """Create output directory structure"""
        os.makedirs(self.config["output_dir"], exist_ok=True)
        for subdir in ["databases", "statistics", "plots", "reports"]:
            os.makedirs(os.path.join(self.config["output_dir"], subdir), exist_ok=True)
        print(f"Output directory: {self.config['output_dir']}")

    def simulate_sequencing_data(self):
        """Simulate FASTQ files for demonstration"""
        print("\n=== Simulating Sequencing Data ===")

        # Define sequences for each condition
        sequences = {
            "control": [
                "ATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATC",  # Common sequence
                "GCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAGCT",  # Another common
                "CCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCC",  # Control-specific
            ],
            "treatment": [
                "ATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATC",  # Common sequence
                "GCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAGCT",  # Another common
                "GGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGG",  # Treatment-specific
                "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA",  # Treatment-specific
            ]
        }

        # Create FASTQ files
        for condition, reps in self.config["samples"].items():
            for i, rep_file in enumerate(reps):
                file_path = os.path.join(self.config["output_dir"], rep_file)
                with open(file_path, 'w') as f:
                    seq_count = 0
                    for base_seq in sequences[condition]:
                        # Add variations and duplicates
                        for j in range(100):
                            # Add some noise
                            if j % 10 == 0:
                                seq = base_seq[:20] + "N" * 10 + base_seq[30:]
                            else:
                                seq = base_seq

                            # FASTQ format
                            f.write(f"@{condition}_rep{i+1}_read{seq_count+1}\n")
                            f.write(f"{seq}\n")
                            f.write("+\n")
                            f.write(f"{'I' * len(seq)}\n")
                            seq_count += 1

                print(f"Created {file_path} with {seq_count} reads")

    def process_sample(self, file_path, condition):
        """Process a single sample file"""
        sample_name = os.path.basename(file_path).split('.')[0]
        print(f"\nProcessing {sample_name}...")

        sample_results = {
            "file_path": file_path,
            "condition": condition,
            "k_mers": {},
            "databases": {}
        }

        # Process different k-mer sizes
        for k in self.config["k_sizes"]:
            print(f"  Counting k={k}...")
            start_time = time.time()

            counter = KmerCounter(
                k=k,
                canonical=self.config["canonical"],
                threads=self.config["threads"]
            )

            # Count k-mers
            counter.count_file(file_path)

            # Get statistics
            total_kmers = counter.get_total_count()
            unique_kmers = counter.get_unique_count()
            processing_time = time.time() - start_time

            # Save results
            db_path = os.path.join(
                self.config["output_dir"],
                "databases",
                f"{sample_name}_k{k}.rkdb"
            )
            counter.save_to_database(db_path, canonical=self.config["canonical"])

            sample_results["k_mers"][k] = {
                "total": total_kmers,
                "unique": unique_kmers,
                "abundance_ratio": total_kmers / unique_kmers if unique_kmers > 0 else 0,
                "processing_time": processing_time,
                "database_path": db_path
            }

            sample_results["databases"][k] = db_path

            print(f"    Total: {total_kmers:,}, Unique: {unique_kmers:,}")
            print(f"    Time: {processing_time:.2f}s, Database: {os.path.getsize(db_path)/1024:.1f}KB")

        return sample_name, sample_results

    def run_kmer_analysis(self):
        """Run k-mer counting analysis for all samples"""
        print("\n=== K-mer Counting Analysis ===")

        self.create_output_directory()

        # Simulate or use existing data
        if not any(os.path.exists(f) for files in self.config["samples"].values() for f in files):
            self.simulate_sequencing_data()

        # Process each sample
        all_filepaths = []
        for condition, files in self.config["samples"].items():
            for file in files:
                all_filepaths.append((os.path.join(self.config["output_dir"], file), condition))

        for file_path, condition in all_filepaths:
            if os.path.exists(file_path):
                sample_name, results = self.process_sample(file_path, condition)
                self.results["samples"][sample_name] = results
            else:
                print(f"Warning: File not found: {file_path}")

    def analyze_kmer_overlap(self):
        """Analyze k-mer overlap between conditions"""
        print("\n=== K-mer Overlap Analysis ===")

        # Choose a k-mer size for comparison (usually the middle one)
        k = self.config["k_sizes"][1]

        # Collect databases by condition
        condition_dbs = defaultdict(list)
        for sample_name, sample_data in self.results["samples"].items():
            if k in sample_data["databases"]:
                condition_dbs[sample_data["condition"]].append(sample_data["databases"][k])

        # Create merged databases for each condition
        for condition, db_paths in condition_dbs.items():
            print(f"\nMerging {condition} databases (k={k})...")

            if db_paths:
                # Load first database
                merged_db = Database()
                merged_db.load(db_paths[0])

                # Merge with remaining databases
                for db_path in db_paths[1:]:
                    merged_db.merge_with(db_path)

                # Save merged database
                merged_path = os.path.join(
                    self.config["output_dir"],
                    "databases",
                    f"{condition}_merged_k{k}.rkdb"
                )
                merged_db.save(merged_path)

                # Store statistics
                stats = merged_db.get_stats()
                self.results["conditions"][condition] = {
                    "merged_database": merged_path,
                    "statistics": stats,
                    "k": k
                }

                print(f"  Total k-mers: {stats['total_kmers']:,}")
                print(f"  Unique k-mers: {stats['unique_kmers']:,}")

    def perform_differential_analysis(self):
        """Perform differential k-mer analysis between conditions"""
        print("\n=== Differential Analysis ===")

        conditions = list(self.results["conditions"].keys())
        if len(conditions) != 2:
            print("Differential analysis requires exactly 2 conditions")
            return

        control, treatment = conditions
        print(f"Comparing {treatment} vs {control}")

        # Load merged databases
        control_db = Database()
        control_db.load(self.results["conditions"][control]["merged_database"])

        treatment_db = Database()
        treatment_db.load(self.results["conditions"][treatment]["merged_database"])

        # Get common k-mers for comparison
        # Note: This is a simplified approach. In practice, you'd need a method
        # to get all k-mers from the database

        # For demonstration, we'll use test k-mers
        test_kmers = [
            "ATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATC",
            "GCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAGCT",
            "CCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCC",
            "GGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGG",
            "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"
        ]

        differential_results = []
        for kmer in test_kmers:
            control_count = control_db.query(kmer)
            treatment_count = treatment_db.query(kmer)

            if control_count > 0 or treatment_count > 0:
                # Calculate fold change
                fold_change = treatment_count / control_count if control_count > 0 else float('inf')

                differential_results.append({
                    "kmer": kmer,
                    "control": control_count,
                    "treatment": treatment_count,
                    "fold_change": fold_change,
                    "log2_fold_change": 0 if fold_change == 1 else (1 if fold_change > 1 else -1) * abs(fold_change).bit_length()
                })

        # Convert to DataFrame for analysis
        df = pd.DataFrame(differential_results)

        # Add significance criteria
        df['significant'] = (
            (df['log2_fold_change'].abs() >= 1) &  # |log2FC| >= 1 (2-fold change)
            (df['control'] + df['treatment'] >= 10)  # Minimum total count
        )

        # Save results
        output_path = os.path.join(
            self.config["output_dir"],
            "statistics",
            "differential_kmers.csv"
        )
        df.to_csv(output_path, index=False)

        # Print summary
        significant = df[df['significant']]
        print(f"\nDifferential Analysis Results:")
        print(f"  Total k-mers tested: {len(df)}")
        print(f"  Significant changes: {len(significant)}")
        print(f"  Up-regulated in {treatment}: {len(significant[significant['fold_change'] > 1])}")
        print(f"  Down-regulated in {treatment}: {len(significant[significant['fold_change'] < 1])}")

        self.results["differential"] = {
            "dataframe": df,
            "significant_kmers": significant,
            "output_path": output_path
        }

    def generate_statistics_report(self):
        """Generate comprehensive statistics report"""
        print("\n=== Generating Statistics Report ===")

        # Collect all statistics
        report = {
            "pipeline_config": self.config,
            "processing_summary": {},
            "sample_statistics": {},
            "condition_statistics": {}
        }

        # Processing summary
        total_processing_time = time.time() - self.start_time
        total_files = len(self.results["samples"])

        report["processing_summary"] = {
            "total_samples": total_files,
            "total_processing_time": total_processing_time,
            "average_time_per_sample": total_processing_time / total_files if total_files > 0 else 0
        }

        # Sample statistics
        for sample_name, sample_data in self.results["samples"].items():
            report["sample_statistics"][sample_name] = {
                "condition": sample_data["condition"],
                "k_mers": sample_data["k_mers"]
            }

        # Condition statistics
        for condition, condition_data in self.results["conditions"].items():
            report["condition_statistics"][condition] = condition_data["statistics"]

        # Add differential results if available
        if "differential" in self.results:
            report["differential_analysis"] = {
                "total_kmers_tested": len(self.results["differential"]["dataframe"]),
                "significant_changes": len(self.results["differential"]["significant_kmers"]),
                "results_file": self.results["differential"]["output_path"]
            }

        # Save report
        report_path = os.path.join(
            self.config["output_dir"],
            "reports",
            "pipeline_report.json"
        )

        with open(report_path, 'w') as f:
            json.dump(report, f, indent=2, default=str)

        print(f"Report saved to: {report_path}")

        # Print summary
        print(f"\nPipeline Summary:")
        print(f"  Samples processed: {total_files}")
        print(f"  Processing time: {total_processing_time:.2f} seconds")
        print(f"  Average per sample: {total_processing_time/total_files:.2f} seconds")

        print(f"\nK-mer Statistics:")
        for k in self.config["k_sizes"]:
            totals = [s["k_mers"][k]["total"] for s in self.results["samples"].values() if k in s["k_mers"]]
            uniques = [s["k_mers"][k]["unique"] for s in self.results["samples"].values() if k in s["k_mers"]]

            if totals and uniques:
                print(f"  k={k}: Total avg={sum(totals)/len(totals):,.0f}, "
                      f"Unique avg={sum(uniques)/len(uniques):,.0f}")

    def create_visualizations(self):
        """Create visualization plots"""
        print("\n=== Creating Visualizations ===")

        plt.style.use('seaborn-v0_8')
        fig_dir = os.path.join(self.config["output_dir"], "plots")

        # 1. K-mer distribution by sample
        plt.figure(figsize=(12, 6))

        sample_names = []
        total_kmers = []
        unique_kmers = []
        conditions = []

        for sample_name, sample_data in self.results["samples"].items():
            k = self.config["k_sizes"][1]  # Use middle k-mer size
            if k in sample_data["k_mers"]:
                sample_names.append(sample_name)
                total_kmers.append(sample_data["k_mers"][k]["total"])
                unique_kmers.append(sample_data["k_mers"][k]["unique"])
                conditions.append(sample_data["condition"])

        df_plot = pd.DataFrame({
            'Sample': sample_names,
            'Total K-mers': total_kmers,
            'Unique K-mers': unique_kmers,
            'Condition': conditions
        })

        # Stacked bar plot
        df_plot.set_index('Sample')[['Total K-mers', 'Unique K-mers']].plot(
            kind='bar', stacked=False, figsize=(12, 6)
        )
        plt.title('K-mer Counts by Sample')
        plt.ylabel('Number of K-mers')
        plt.xticks(rotation=45)
        plt.tight_layout()
        plt.savefig(os.path.join(fig_dir, 'kmer_counts_by_sample.png'), dpi=300, bbox_inches='tight')
        plt.close()

        # 2. Processing time comparison
        plt.figure(figsize=(10, 6))

        processing_times = []
        for sample_name, sample_data in self.results["samples"].items():
            k = self.config["k_sizes"][1]
            if k in sample_data["k_mers"]:
                processing_times.append({
                    'Sample': sample_name,
                    'Time (s)': sample_data["k_mers"][k]["processing_time"],
                    'Condition': sample_data["condition"]
                })

        df_time = pd.DataFrame(processing_times)
        sns.barplot(data=df_time, x='Sample', y='Time (s)', hue='Condition')
        plt.title('Processing Time by Sample')
        plt.xticks(rotation=45)
        plt.tight_layout()
        plt.savefig(os.path.join(fig_dir, 'processing_times.png'), dpi=300, bbox_inches='tight')
        plt.close()

        # 3. Differential analysis volcano plot (if available)
        if "differential" in self.results:
            df = self.results["differential"]["dataframe"]

            plt.figure(figsize=(10, 8))
            plt.scatter(
                df['log2_fold_change'],
                -np.log10(df['control'] + df['treatment'] + 1),
                alpha=0.6,
                s=30
            )

            # Highlight significant points
            significant = df[df['significant']]
            plt.scatter(
                significant['log2_fold_change'],
                -np.log10(significant['control'] + significant['treatment'] + 1),
                color='red',
                alpha=0.8,
                s=30,
                label='Significant'
            )

            # Add reference lines
            plt.axhline(y=-np.log10(10), color='gray', linestyle='--', alpha=0.5)
            plt.axvline(x=-1, color='gray', linestyle='--', alpha=0.5)
            plt.axvline(x=1, color='gray', linestyle='--', alpha=0.5)

            plt.xlabel('Log2 Fold Change')
            plt.ylabel('-Log10 Combined Count')
            plt.title('Differential K-mer Expression Volcano Plot')
            plt.legend()
            plt.grid(True, alpha=0.3)
            plt.tight_layout()
            plt.savefig(os.path.join(fig_dir, 'volcano_plot.png'), dpi=300, bbox_inches='tight')
            plt.close()

        print(f"Plots saved to: {fig_dir}")

    def run_complete_pipeline(self):
        """Run the complete genomics analysis pipeline"""
        print("RustKmer Genomics Analysis Pipeline")
        print("==================================")
        print(f"Configuration: k={self.config['k_sizes']}, canonical={self.config['canonical']}")
        print(f"Threads: {self.config['threads']}\n")

        try:
            # Run pipeline steps
            self.run_kmer_analysis()
            self.analyze_kmer_overlap()
            self.perform_differential_analysis()
            self.generate_statistics_report()
            self.create_visualizations()

            print("\n" + "=" * 60)
            print("Pipeline completed successfully!")
            print("=" * 60)
            print(f"Output directory: {self.config['output_dir']}")
            print(f"Total time: {time.time() - self.start_time:.2f} seconds")

        except Exception as e:
            print(f"\nPipeline failed with error: {e}")
            import traceback
            traceback.print_exc()
            sys.exit(1)

def main():
    """Main function"""
    # Run pipeline with default configuration
    pipeline = GenomicsPipeline()
    pipeline.run_complete_pipeline()

    # To run with custom configuration:
    # pipeline = GenomicsPipeline("config.json")
    # pipeline.run_complete_pipeline()

if __name__ == "__main__":
    main()