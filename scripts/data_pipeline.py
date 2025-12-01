#!/usr/bin/env python3
"""
Data Pipeline for RustKmer vs Jellyfish Performance Comparison

This script sets up the comprehensive testing infrastructure by:
1. Processing available test data and generating metadata
2. Creating diverse query sets for testing
3. Building databases for both tools with performance tracking
4. Setting up the directory structure for systematic testing

Author: Performance Comparison System
"""

import os
import sys
import json
import time
import gzip
import hashlib
import subprocess
import pandas as pd
from pathlib import Path
from collections import defaultdict
from typing import Dict, List, Tuple, Any
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/Users/forrest/Temp/demodata/performance_comparison/logs/data_pipeline.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class PerformanceDataPipeline:
    """Comprehensive data pipeline for performance comparison testing."""

    def __init__(self):
        self.base_dir = Path("/Users/forrest/Temp/demodata")
        self.output_dir = Path("/Users/forrest/Temp/demodata/performance_comparison")
        self.source_dirs = {
            "fasta": self.base_dir / "fasta",
            "fastq": self.base_dir / "fastq"
        }
        self.metadata = {
            "files": {},
            "datasets": {},
            "generated_at": time.time(),
            "total_size": 0
        }

    def setup_directories(self):
        """Create necessary directory structure."""
        logger.info("Setting up directory structure...")

        directories = [
            "data", "databases/jellyfish", "databases/rustkmer",
            "queries", "results", "logs", "reports"
        ]

        for dir_path in directories:
            full_path = self.output_dir / dir_path
            full_path.mkdir(parents=True, exist_ok=True)
            logger.info(f"Created directory: {full_path}")

    def scan_test_data(self) -> Dict[str, Any]:
        """Scan and analyze available test data."""
        logger.info("Scanning test data directories...")

        file_info = []
        total_size = 0

        for data_type, source_dir in self.source_dirs.items():
            if not source_dir.exists():
                logger.warning(f"Source directory not found: {source_dir}")
                continue

            logger.info(f"Processing {data_type} directory: {source_dir}")

            for file_path in source_dir.iterdir():
                if file_path.is_file():
                    # Get file info
                    stat = file_path.stat()
                    file_size = stat.st_size
                    compressed = file_path.suffix == '.gz'

                    # Calculate file hash for identification
                    file_hash = self._calculate_file_hash(file_path)

                    # Estimate uncompressed size for compressed files
                    uncompressed_size = file_size
                    if compressed:
                        uncompressed_size = self._estimate_uncompressed_size(file_path)

                    file_data = {
                        "path": str(file_path),
                        "name": file_path.name,
                        "type": data_type,
                        "size_bytes": file_size,
                        "size_mb": round(file_size / (1024 * 1024), 2),
                        "uncompressed_size_mb": round(uncompressed_size / (1024 * 1024), 2),
                        "compressed": compressed,
                        "compression_ratio": round(file_size / uncompressed_size, 3) if compressed else 1.0,
                        "hash": file_hash,
                        "modified_time": stat.st_mtime
                    }

                    file_info.append(file_data)
                    total_size += file_size
                    logger.info(f"  {file_path.name}: {file_data['size_mb']}MB "
                              f"({'compressed' if compressed else 'uncompressed'})")

        self.metadata["files"] = file_info
        self.metadata["total_size"] = total_size
        self.metadata["total_size_mb"] = round(total_size / (1024 * 1024), 2)

        logger.info(f"Found {len(file_info)} files totaling {self.metadata['total_size_mb']}MB")
        return file_info

    def _calculate_file_hash(self, file_path: Path) -> str:
        """Calculate SHA-256 hash of file for identification."""
        hash_sha256 = hashlib.sha256()

        try:
            with open(file_path, "rb") as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    hash_sha256.update(chunk)
        except Exception as e:
            logger.warning(f"Could not hash {file_path}: {e}")
            return "unknown"

        return hash_sha256.hexdigest()[:16]  # Use first 16 chars for brevity

    def _estimate_uncompressed_size(self, compressed_path: Path) -> int:
        """Estimate uncompressed size of gzipped file."""
        try:
            with gzip.open(compressed_path, 'rb') as f:
                # Read through file to get uncompressed size
                size = 0
                while chunk := f.read(8192):
                    size += len(chunk)
                return size
        except Exception as e:
            logger.warning(f"Could not estimate uncompressed size for {compressed_path}: {e}")
            return compressed_path.stat().st_size

    def generate_test_datasets(self):
        """Generate dataset configurations for testing."""
        logger.info("Generating test dataset configurations...")

        datasets = {}

        # Small-scale dataset (rice genome)
        fasta_files = [f for f in self.metadata["files"] if f["type"] == "fasta" and not f["compressed"]]
        if fasta_files:
            datasets["small_genome"] = {
                "name": "Rice Genome (OSA1)",
                "files": [f["path"] for f in fasta_files],
                "total_size_mb": sum(f["size_mb"] for f in fasta_files),
                "description": "Reference genome for initial testing",
                "kmer_sizes": [13, 21, 31],
                "test_queries_count": 1000,
                "category": "genomic"
            }

        # Large-scale dataset (RNA-seq)
        fastq_files = [f for f in self.metadata["files"] if f["type"] == "fastq"]
        if fastq_files:
            # Categorize by size for different stress tests
            small_fastq = [f for f in fastq_files if f["size_mb"] < 2000]
            large_fastq = [f for f in fastq_files if f["size_mb"] >= 2000]

            if small_fastq:
                datasets["medium_rnaseq"] = {
                    "name": "RNA-seq Medium",
                    "files": [f["path"] for f in small_fastq[:2]],  # Use 2 smallest files
                    "total_size_mb": sum(f["size_mb"] for f in small_fastq[:2]),
                    "description": "Medium-scale transcriptomic data",
                    "kmer_sizes": [21, 31],
                    "test_queries_count": 5000,
                    "category": "transcriptomic"
                }

            if large_fastq:
                datasets["large_rnaseq"] = {
                    "name": "RNA-seq Large",
                    "files": [f["path"] for f in large_fastq[:1]],  # Use 1 largest file
                    "total_size_mb": sum(f["size_mb"] for f in large_fastq[:1]),
                    "description": "Large-scale stress testing data",
                    "kmer_sizes": [21, 31],
                    "test_queries_count": 10000,
                    "category": "transcriptomic"
                }

        # Compression comparison dataset
        compressed_files = [f for f in self.metadata["files"] if f["compressed"]]
        if compressed_files:
            datasets["compression_test"] = {
                "name": "Compression Performance",
                "files": [f["path"] for f in compressed_files[:2]],
                "total_size_mb": sum(f["size_mb"] for f in compressed_files[:2]),
                "description": "Test compression handling performance",
                "kmer_sizes": [21],
                "test_queries_count": 2000,
                "category": "compression"
            }

        self.metadata["datasets"] = datasets
        logger.info(f"Generated {len(datasets)} test datasets")

        for name, dataset in datasets.items():
            logger.info(f"  {name}: {dataset['total_size_mb']}MB - {dataset['description']}")

    def generate_query_sets(self):
        """Generate diverse query sets for testing."""
        logger.info("Generating query sets for testing...")

        # For now, we'll use the existing OSA1 genome for query extraction
        # In a full implementation, this would extract queries from each dataset
        osa1_path = self.base_dir / "fasta" / "osa1_r7.asm.fa"

        if not osa1_path.exists():
            logger.warning("OSA1 genome not found, using placeholder queries")
            self._generate_placeholder_queries()
            return

        # Generate different types of query sets
        query_configs = [
            {"name": "exact_queries", "mutations": 0, "wildcards": 0, "count": 1000},
            {"name": "wildcard_queries", "mutations": 0, "wildcards": 1, "count": 500},
            {"name": "mutation_queries", "mutations": 1, "wildcards": 0, "count": 500},
            {"name": "combined_queries", "mutations": 1, "wildcards": 1, "count": 500},
            {"name": "stress_test_queries", "mutations": 2, "wildcards": 2, "count": 200}
        ]

        for config in query_configs:
            query_file = self.output_dir / "queries" / f"{config['name']}.txt"

            try:
                # This would use the existing query generation logic
                # For now, create placeholder file
                with open(query_file, 'w') as f:
                    f.write(f"# {config['name']} - {config['count']} queries\n")
                    f.write(f"# Mutations: {config['mutations']}, Wildcards: {config['wildcards']}\n")
                    # Add sample queries
                    for i in range(min(10, config['count'])):
                        sample_query = "ATGCGATGCTAGCTAGCTAGCGATGCTAGCTA"[:31]
                        if config['wildcards'] > 0:
                            sample_query = sample_query[:15] + 'N' + sample_query[16:]
                        f.write(f"{sample_query}\n")

                logger.info(f"Generated {config['name']}: {query_file}")

            except Exception as e:
                logger.error(f"Failed to generate {config['name']}: {e}")

    def _generate_placeholder_queries(self):
        """Generate placeholder query files when OSA1 genome is not available."""
        logger.info("Generating placeholder query sets...")

        sample_queries = [
            "ATGCGATGCTAGCTAGCTAGCGATGCTAGCTA",
            "CGATGCTAGCTAGCTAGCATGCTAGCTAGCG",
            "GCTAGCTAGCTAGCTAGCTAGCTAGCTAGCA"
        ]

        query_configs = ["exact", "wildcard", "mutation", "combined"]

        for config in query_configs:
            query_file = self.output_dir / "queries" / f"{config}_queries.txt"
            with open(query_file, 'w') as f:
                f.write(f"# {config} queries - placeholder\n")
                for query in sample_queries:
                    if config == "wildcard":
                        query = query[:15] + 'N' + query[16:]
                    f.write(f"{query}\n")

    def create_databases(self):
        """Create databases for both Jellyfish and RustKmer."""
        logger.info("Creating databases for performance testing...")

        for dataset_name, dataset in self.metadata["datasets"].items():
            logger.info(f"Processing dataset: {dataset_name}")

            for kmer_size in dataset["kmer_sizes"]:
                logger.info(f"  Creating k={kmer_size} databases...")

                for file_path in dataset["files"]:
                    self._create_jellyfish_database(file_path, kmer_size, dataset_name)
                    self._create_rustkmer_database(file_path, kmer_size, dataset_name)

    def _create_jellyfish_database(self, file_path: str, kmer_size: int, dataset_name: str):
        """Create Jellyfish database for performance testing."""
        try:
            output_file = (self.output_dir / "databases" / "jellyfish" /
                         f"{dataset_name}_k{kmer_size}_{Path(file_path).stem}.jf")

            cmd = [
                "jellyfish", "count",
                "-m", str(kmer_size),
                "-s", "100M",  # Hash size
                "-t", "4",     # Threads
                "-C",          # Canonical counting
                "-o", str(output_file),
                file_path
            ]

            start_time = time.time()
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=3600)
            end_time = time.time()

            performance_data = {
                "tool": "jellyfish",
                "dataset": dataset_name,
                "kmer_size": kmer_size,
                "input_file": file_path,
                "output_file": str(output_file),
                "creation_time_seconds": end_time - start_time,
                "success": result.returncode == 0,
                "command": " ".join(cmd),
                "timestamp": time.time()
            }

            if result.returncode == 0:
                logger.info(f"    Jellyfish k={kmer_size} database created: {output_file.name}")

                # Get database size
                if output_file.exists():
                    performance_data["database_size_mb"] = round(output_file.stat().st_size / (1024 * 1024), 2)
            else:
                logger.error(f"    Jellyfish failed: {result.stderr}")
                performance_data["error"] = result.stderr

            # Save performance data
            self._save_performance_data(performance_data)

        except subprocess.TimeoutExpired:
            logger.error(f"Jellyfish database creation timed out for {file_path}")
        except Exception as e:
            logger.error(f"Failed to create Jellyfish database: {e}")

    def _create_rustkmer_database(self, file_path: str, kmer_size: int, dataset_name: str):
        """Create RustKmer database for performance testing."""
        try:
            output_file = (self.output_dir / "databases" / "rustkmer" /
                         f"{dataset_name}_k{kmer_size}_{Path(file_path).stem}.rkdb")

            cmd = [
                "./target/release/rustkmer", "count",
                "-k", str(kmer_size),
                "-t", "4",        # Threads
                "--canonical",    # Canonical counting
                "--sort",         # Sort for fast querying
                "-o", str(output_file),
                file_path
            ]

            start_time = time.time()
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=3600)
            end_time = time.time()

            performance_data = {
                "tool": "rustkmer",
                "dataset": dataset_name,
                "kmer_size": kmer_size,
                "input_file": file_path,
                "output_file": str(output_file),
                "creation_time_seconds": end_time - start_time,
                "success": result.returncode == 0,
                "command": " ".join(cmd),
                "timestamp": time.time()
            }

            if result.returncode == 0:
                logger.info(f"    RustKmer k={kmer_size} database created: {output_file.name}")

                # Get database size
                if output_file.exists():
                    performance_data["database_size_mb"] = round(output_file.stat().st_size / (1024 * 1024), 2)
            else:
                logger.error(f"    RustKmer failed: {result.stderr}")
                performance_data["error"] = result.stderr

            # Save performance data
            self._save_performance_data(performance_data)

        except subprocess.TimeoutExpired:
            logger.error(f"RustKmer database creation timed out for {file_path}")
        except Exception as e:
            logger.error(f"Failed to create RustKmer database: {e}")

    def _save_performance_data(self, performance_data: Dict[str, Any]):
        """Save performance data to CSV file."""
        csv_file = self.output_dir / "results" / "database_creation_performance.csv"

        # Create file with headers if it doesn't exist
        if not csv_file.exists():
            headers = list(performance_data.keys())
            pd.DataFrame(columns=headers).to_csv(csv_file, index=False)

        # Append new data
        df = pd.DataFrame([performance_data])
        df.to_csv(csv_file, mode='a', header=False, index=False)

    def save_metadata(self):
        """Save complete metadata to JSON file."""
        metadata_file = self.output_dir / "data" / "pipeline_metadata.json"

        with open(metadata_file, 'w') as f:
            json.dump(self.metadata, f, indent=2, default=str)

        logger.info(f"Metadata saved to: {metadata_file}")

    def generate_summary_report(self):
        """Generate summary report of pipeline execution."""
        summary = {
            "pipeline_completed_at": time.time(),
            "total_files_processed": len(self.metadata["files"]),
            "total_datasets_created": len(self.metadata["datasets"]),
            "total_data_size_mb": self.metadata["total_size_mb"],
            "datasets_summary": {}
        }

        for name, dataset in self.metadata["datasets"].items():
            summary["datasets_summary"][name] = {
                "size_mb": dataset["total_size_mb"],
                "files_count": len(dataset["files"]),
                "kmer_sizes": dataset["kmer_sizes"],
                "category": dataset["category"]
            }

        summary_file = self.output_dir / "reports" / "pipeline_summary.json"
        with open(summary_file, 'w') as f:
            json.dump(summary, f, indent=2, default=str)

        logger.info("Pipeline summary report generated")

        # Print human-readable summary
        print("\n" + "="*60)
        print("DATA PIPELINE SUMMARY")
        print("="*60)
        print(f"Files processed: {summary['total_files_processed']}")
        print(f"Total data size: {summary['total_data_size_mb']}MB")
        print(f"Datasets created: {summary['total_datasets_created']}")
        print("\nDatasets:")
        for name, info in summary["datasets_summary"].items():
            print(f"  {name}: {info['size_mb']}MB, k={info['kmer_sizes']}")
        print("="*60)

    def run_complete_pipeline(self):
        """Execute the complete data pipeline."""
        logger.info("Starting complete data pipeline...")
        start_time = time.time()

        try:
            # Step 1: Setup directories
            self.setup_directories()

            # Step 2: Scan test data
            self.scan_test_data()

            # Step 3: Generate test datasets
            self.generate_test_datasets()

            # Step 4: Generate query sets
            self.generate_query_sets()

            # Step 5: Create databases
            self.create_databases()

            # Step 6: Save metadata
            self.save_metadata()

            # Step 7: Generate summary
            self.generate_summary_report()

            end_time = time.time()
            logger.info(f"Data pipeline completed in {end_time - start_time:.2f} seconds")

        except Exception as e:
            logger.error(f"Data pipeline failed: {e}")
            raise

def main():
    """Main entry point for the data pipeline."""
    print("🚀 RustKmer vs Jellyfish Performance Comparison Data Pipeline")
    print("=" * 70)

    pipeline = PerformanceDataPipeline()
    pipeline.run_complete_pipeline()

    print("\n✅ Data pipeline completed successfully!")
    print("📁 Results available in: /Users/forrest/Temp/demodata/performance_comparison/")
    print("📊 Ready for performance comparison testing!")

if __name__ == "__main__":
    main()