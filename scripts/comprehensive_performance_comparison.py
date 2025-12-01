#!/usr/bin/env python3
"""
Comprehensive Performance Comparison: RustKmer vs Jellyfish

This script executes systematic performance comparison between RustKmer and Jellyfish
including:
- Database creation performance
- Query performance (exact, fuzzy, batch)
- Memory usage profiling
- I/O and compression performance
- Real-world workflow testing

Author: Performance Comparison System
"""

import os
import sys
import json
import time
import psutil
import subprocess
import pandas as pd
import numpy as np
from pathlib import Path
from typing import Dict, List, Tuple, Any, Optional
import logging
import matplotlib.pyplot as plt
import seaborn as sns
from concurrent.futures import ThreadPoolExecutor, as_completed
import multiprocessing

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/Users/forrest/Temp/demodata/performance_comparison/logs/performance_comparison.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class ComprehensivePerformanceTest:
    """Comprehensive performance testing for RustKmer vs Jellyfish comparison."""

    def __init__(self):
        self.base_dir = Path("/Users/forrest/Temp/demodata/performance_comparison")
        self.results_dir = self.base_dir / "results"
        self.reports_dir = self.base_dir / "reports"
        self.databases_dir = self.base_dir / "databases"
        self.queries_dir = self.base_dir / "queries"

        self.results = {
            "database_creation": [],
            "query_performance": [],
            "memory_usage": [],
            "io_performance": [],
            "workflow_performance": []
        }

        # Ensure results directories exist
        self.results_dir.mkdir(parents=True, exist_ok=True)
        self.reports_dir.mkdir(parents=True, exist_ok=True)

        # Performance test configuration
        self.test_config = self._load_test_config()

    def _load_test_config(self) -> Dict[str, Any]:
        """Load test configuration or use defaults."""
        config_file = self.base_dir / "data" / "pipeline_metadata.json"

        default_config = {
            "datasets": {
                "small_genome": {
                    "kmer_sizes": [13, 21, 31],
                    "query_sets": ["exact_queries", "wildcard_queries", "mutation_queries"]
                }
            },
            "performance_tests": {
                "query_counts": [100, 500, 1000],
                "thread_counts": [1, 2, 4, 8],
                "iterations": 3
            }
        }

        if config_file.exists():
            try:
                with open(config_file, 'r') as f:
                    data = json.load(f)
                    return {
                        "datasets": data.get("datasets", default_config["datasets"]),
                        "performance_tests": default_config["performance_tests"]
                    }
            except Exception as e:
                logger.warning(f"Could not load config: {e}, using defaults")

        return default_config

    def measure_memory_usage(self, pid: int, duration: float = 1.0) -> Dict[str, float]:
        """Measure memory usage of a process over time."""
        try:
            process = psutil.Process(pid)
            memory_samples = []
            cpu_samples = []

            start_time = time.time()
            while time.time() - start_time < duration:
                try:
                    memory_info = process.memory_info()
                    memory_samples.append(memory_info.rss / 1024 / 1024)  # MB
                    cpu_samples.append(process.cpu_percent())
                    time.sleep(0.1)
                except psutil.NoSuchProcess:
                    break

            if memory_samples:
                return {
                    "peak_memory_mb": max(memory_samples),
                    "avg_memory_mb": np.mean(memory_samples),
                    "min_memory_mb": min(memory_samples),
                    "memory_std_mb": np.std(memory_samples),
                    "avg_cpu_percent": np.mean(cpu_samples) if cpu_samples else 0
                }
        except Exception as e:
            logger.warning(f"Memory measurement failed: {e}")

        return {
            "peak_memory_mb": 0,
            "avg_memory_mb": 0,
            "min_memory_mb": 0,
            "memory_std_mb": 0,
            "avg_cpu_percent": 0
        }

    def run_command_with_profiling(self, cmd: List[str], timeout: int = 3600) -> Dict[str, Any]:
        """Run a command with comprehensive profiling."""
        logger.info(f"Running: {' '.join(cmd)}")

        start_time = time.time()
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )

        # Start memory profiling
        memory_data = self.measure_memory_usage(process.pid, duration=5.0)

        try:
            stdout, stderr = process.communicate(timeout=timeout - 5)
            end_time = time.time()

            return {
                "command": " ".join(cmd),
                "success": process.returncode == 0,
                "execution_time_seconds": end_time - start_time,
                "stdout": stdout,
                "stderr": stderr,
                "return_code": process.returncode,
                "memory_profiling": memory_data,
                "timestamp": start_time
            }

        except subprocess.TimeoutExpired:
            process.kill()
            return {
                "command": " ".join(cmd),
                "success": False,
                "execution_time_seconds": timeout,
                "stdout": "",
                "stderr": "Command timed out",
                "return_code": -1,
                "memory_profiling": memory_data,
                "timestamp": start_time
            }

    def test_database_creation_performance(self):
        """Test database creation performance for both tools."""
        logger.info("Testing database creation performance...")

        datasets = self.test_config["datasets"]

        for dataset_name, dataset in datasets.items():
            logger.info(f"Testing dataset: {dataset_name}")

            for kmer_size in dataset["kmer_sizes"]:
                logger.info(f"  K-mer size: {kmer_size}")

                # Find input files
                jellyfish_dir = self.databases_dir / "jellyfish"
                rustkmer_dir = self.databases_dir / "rustkmer"

                # Use existing databases if available, or find input files
                input_files = self._find_input_files(dataset_name)

                if not input_files:
                    logger.warning(f"No input files found for {dataset_name}")
                    continue

                for input_file in input_files[:1]:  # Test with first file
                    file_name = Path(input_file).stem

                    # Test Jellyfish
                    jellyfish_output = jellyfish_dir / f"{dataset_name}_k{kmer_size}_{file_name}.jf"
                    jellyfish_cmd = [
                        "jellyfish", "count",
                        "-m", str(kmer_size),
                        "-s", "100M",
                        "-t", "4",
                        "-C",
                        "-o", str(jellyfish_output),
                        input_file
                    ]

                    result = self.run_command_with_profiling(jellyfish_cmd)
                    result.update({
                        "tool": "jellyfish",
                        "operation": "database_creation",
                        "dataset": dataset_name,
                        "kmer_size": kmer_size,
                        "input_file": input_file,
                        "output_file": str(jellyfish_output)
                    })
                    self.results["database_creation"].append(result)

                    # Test RustKmer
                    rustkmer_output = rustkmer_dir / f"{dataset_name}_k{kmer_size}_{file_name}.rkdb"
                    rustkmer_cmd = [
                        "./target/release/rustkmer", "count",
                        "-k", str(kmer_size),
                        "-t", "4",
                        "--canonical",
                        "--sort",
                        "-o", str(rustkmer_output),
                        input_file
                    ]

                    result = self.run_command_with_profiling(rustkmer_cmd)
                    result.update({
                        "tool": "rustkmer",
                        "operation": "database_creation",
                        "dataset": dataset_name,
                        "kmer_size": kmer_size,
                        "input_file": input_file,
                        "output_file": str(rustkmer_output)
                    })
                    self.results["database_creation"].append(result)

    def test_query_performance(self):
        """Test query performance for both tools."""
        logger.info("Testing query performance...")

        # Find available databases
        jellyfish_dbs = list((self.databases_dir / "jellyfish").glob("*.jf"))
        rustkmer_dbs = list((self.databases_dir / "rustkmer").glob("*.rkdb"))

        if not jellyfish_dbs or not rustkmer_dbs:
            logger.warning("No databases found for query testing")
            return

        # Use first available databases
        jellyfish_db = jellyfish_dbs[0]
        rustkmer_db = rustkmer_dbs[0]

        logger.info(f"Using databases: {jellyfish_db.name}, {rustkmer_db.name}")

        # Test with different query sets
        query_counts = self.test_config["performance_tests"]["query_counts"]
        iterations = self.test_config["performance_tests"]["iterations"]

        for query_count in query_counts:
            logger.info(f"  Query count: {query_count}")

            # Generate test queries
            test_queries = self._generate_test_queries(query_count)

            for iteration in range(iterations):
                logger.info(f"    Iteration: {iteration + 1}")

                # Test Jellyfish
                jellyfish_times = []
                for query in test_queries:
                    jellyfish_cmd = ["jellyfish", "query", str(jellyfish_db), query]
                    result = self.run_command_with_profiling(jellyfish_cmd, timeout=30)

                    jellyfish_times.append({
                        "query": query,
                        "time": result["execution_time_seconds"],
                        "success": result["success"],
                        "memory": result["memory_profiling"]["peak_memory_mb"]
                    })

                # Calculate Jellyfish statistics
                jellyfish_stats = self._calculate_query_stats(jellyfish_times, "jellyfish")
                jellyfish_stats.update({
                    "operation": "query_performance",
                    "query_count": query_count,
                    "iteration": iteration,
                    "database": str(jellyfish_db)
                })
                self.results["query_performance"].append(jellyfish_stats)

                # Test RustKmer exact queries
                rustkmer_times = []
                for query in test_queries:
                    rustkmer_cmd = [
                        "./target/release/rustkmer", "query",
                        str(rustkmer_db), query,
                        "--format", "json",
                        "--quiet"
                    ]
                    result = self.run_command_with_profiling(rustkmer_cmd, timeout=30)

                    rustkmer_times.append({
                        "query": query,
                        "time": result["execution_time_seconds"],
                        "success": result["success"],
                        "memory": result["memory_profiling"]["peak_memory_mb"]
                    })

                # Calculate RustKmer statistics
                rustkmer_stats = self._calculate_query_stats(rustkmer_times, "rustkmer")
                rustkmer_stats.update({
                    "operation": "query_performance",
                    "query_count": query_count,
                    "iteration": iteration,
                    "database": str(rustkmer_db)
                })
                self.results["query_performance"].append(rustkmer_stats)

                # Test RustKmer fuzzy queries
                fuzzy_queries = self._generate_fuzzy_queries(min(100, query_count))
                rustkmer_fuzzy_times = []

                for query in fuzzy_queries:
                    rustkmer_fuzzy_cmd = [
                        "./target/release/rustkmer", "fuzzy-query",
                        str(rustkmer_db), query,
                        "--mutations", "1",
                        "--format", "json",
                        "--quiet"
                    ]
                    result = self.run_command_with_profiling(rustkmer_fuzzy_cmd, timeout=60)

                    rustkmer_fuzzy_times.append({
                        "query": query,
                        "time": result["execution_time_seconds"],
                        "success": result["success"],
                        "memory": result["memory_profiling"]["peak_memory_mb"]
                    })

                # Calculate RustKmer fuzzy statistics
                rustkmer_fuzzy_stats = self._calculate_query_stats(rustkmer_fuzzy_times, "rustkmer_fuzzy")
                rustkmer_fuzzy_stats.update({
                    "operation": "fuzzy_query_performance",
                    "query_count": len(fuzzy_queries),
                    "iteration": iteration,
                    "database": str(rustkmer_db)
                })
                self.results["query_performance"].append(rustkmer_fuzzy_stats)

    def test_io_performance(self):
        """Test I/O and compression performance."""
        logger.info("Testing I/O and compression performance...")

        # Find test files with different compression
        test_files = []
        base_dir = Path("/Users/forrest/Temp/demodata")

        # Add compressed and uncompressed files
        fasta_files = list((base_dir / "fasta").glob("*.fa*"))
        fastq_files = list((base_dir / "fastq").glob("*.fq*"))

        test_files.extend(fasta_files[:2])  # Limit to prevent too many tests
        test_files.extend(fastq_files[:2])

        for file_path in test_files:
            if not file_path.exists():
                continue

            file_size_mb = file_path.stat().st_size / (1024 * 1024)
            is_compressed = file_path.suffix == '.gz'

            logger.info(f"  Testing I/O on {file_path.name} ({file_size_mb:.1f}MB, "
                       f"{'compressed' if is_compressed else 'uncompressed'})")

            # Test file reading performance
            read_times = []
            for i in range(3):
                start_time = time.time()

                try:
                    if is_compressed:
                        with open(file_path, 'rb') as f:
                            while f.read(8192):
                                pass
                    else:
                        with open(file_path, 'r') as f:
                            while f.read(8192):
                                pass

                    read_time = time.time() - start_time
                    read_times.append(read_time)

                except Exception as e:
                    logger.error(f"Failed to read {file_path}: {e}")
                    read_times.append(float('inf'))

            # Calculate I/O statistics
            valid_times = [t for t in read_times if t != float('inf')]
            if valid_times:
                io_stats = {
                    "file_path": str(file_path),
                    "file_size_mb": file_size_mb,
                    "compressed": is_compressed,
                    "operation": "file_reading",
                    "avg_read_time_seconds": np.mean(valid_times),
                    "min_read_time_seconds": min(valid_times),
                    "max_read_time_seconds": max(valid_times),
                    "read_throughput_mb_per_sec": file_size_mb / np.mean(valid_times),
                    "timestamp": time.time()
                }

                self.results["io_performance"].append(io_stats)

    def test_workflow_performance(self):
        """Test complete end-to-end workflows."""
        logger.info("Testing complete workflow performance...")

        # Find a test file
        test_files = list(Path("/Users/forrest/Temp/demodata/fasta").glob("*.fa"))
        if not test_files:
            logger.warning("No test files found for workflow testing")
            return

        test_file = test_files[0]
        kmer_size = 21

        logger.info(f"Using test file: {test_file.name}")

        # Test complete Jellyfish workflow
        jellyfish_workflow_start = time.time()
        jellyfish_db = self.base_dir / "databases" / "jellyfish" / f"workflow_test_{test_file.stem}.jf"

        # Create database
        jellyfish_count_cmd = [
            "jellyfish", "count",
            "-m", str(kmer_size),
            "-s", "100M",
            "-t", "4",
            "-C",
            "-o", str(jellyfish_db),
            str(test_file)
        ]

        count_result = self.run_command_with_profiling(jellyfish_count_cmd)

        # Query database
        test_queries = self._generate_test_queries(100)
        jellyfish_query_times = []

        if count_result["success"]:
            for query in test_queries:
                query_start = time.time()
                query_cmd = ["jellyfish", "query", str(jellyfish_db), query]
                query_result = subprocess.run(query_cmd, capture_output=True, text=True, timeout=10)
                query_time = time.time() - query_start

                jellyfish_query_times.append({
                    "query": query,
                    "time": query_time,
                    "success": query_result.returncode == 0
                })

        jellyfish_workflow_time = time.time() - jellyfish_workflow_start

        jellyfish_workflow_stats = {
            "tool": "jellyfish",
            "operation": "complete_workflow",
            "input_file": str(test_file),
            "kmer_size": kmer_size,
            "total_workflow_time_seconds": jellyfish_workflow_time,
            "database_creation_time": count_result["execution_time_seconds"],
            "database_creation_success": count_result["success"],
            "avg_query_time_seconds": np.mean([q["time"] for q in jellyfish_query_times if q["success"]]) if jellyfish_query_times else 0,
            "queries_tested": len(jellyfish_query_times),
            "successful_queries": sum(1 for q in jellyfish_query_times if q["success"]),
            "timestamp": time.time()
        }

        self.results["workflow_performance"].append(jellyfish_workflow_stats)

        # Test complete RustKmer workflow
        rustkmer_workflow_start = time.time()
        rustkmer_db = self.base_dir / "databases" / "rustkmer" / f"workflow_test_{test_file.stem}.rkdb"

        # Create database
        rustkmer_count_cmd = [
            "./target/release/rustkmer", "count",
            "-k", str(kmer_size),
            "-t", "4",
            "--canonical",
            "--sort",
            "-o", str(rustkmer_db),
            str(test_file)
        ]

        count_result = self.run_command_with_profiling(rustkmer_count_cmd)

        # Query database
        rustkmer_query_times = []

        if count_result["success"]:
            for query in test_queries:
                query_start = time.time()
                query_cmd = [
                    "./target/release/rustkmer", "query",
                    str(rustkmer_db), query,
                    "--format", "json",
                    "--quiet"
                ]
                query_result = subprocess.run(query_cmd, capture_output=True, text=True, timeout=10)
                query_time = time.time() - query_start

                rustkmer_query_times.append({
                    "query": query,
                    "time": query_time,
                    "success": query_result.returncode == 0
                })

        rustkmer_workflow_time = time.time() - rustkmer_workflow_start

        rustkmer_workflow_stats = {
            "tool": "rustkmer",
            "operation": "complete_workflow",
            "input_file": str(test_file),
            "kmer_size": kmer_size,
            "total_workflow_time_seconds": rustkmer_workflow_time,
            "database_creation_time": count_result["execution_time_seconds"],
            "database_creation_success": count_result["success"],
            "avg_query_time_seconds": np.mean([q["time"] for q in rustkmer_query_times if q["success"]]) if rustkmer_query_times else 0,
            "queries_tested": len(rustkmer_query_times),
            "successful_queries": sum(1 for q in rustkmer_query_times if q["success"]),
            "timestamp": time.time()
        }

        self.results["workflow_performance"].append(rustkmer_workflow_stats)

    def _find_input_files(self, dataset_name: str) -> List[str]:
        """Find input files for a given dataset."""
        base_dir = Path("/Users/forrest/Temp/demodata")

        if "genome" in dataset_name.lower():
            return [str(f) for f in (base_dir / "fasta").glob("*.fa*")]
        elif "rnaseq" in dataset_name.lower():
            return [str(f) for f in (base_dir / "fastq").glob("*.fq*")]
        else:
            return []

    def _generate_test_queries(self, count: int) -> List[str]:
        """Generate test queries for performance testing."""
        # Use sample 31-mers that are likely to be found
        sample_queries = [
            "ATGCGATGCTAGCTAGCTAGCGATGCTAGCTA",
            "CGATGCTAGCTAGCTAGCATGCTAGCTAGCG",
            "GCTAGCTAGCTAGCTAGCTAGCTAGCTAGCA",
            "CTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAG",
            "TAGCTAGCTAGCTAGCTAGCTAGCTAGCTAGC"
        ]

        queries = []
        for i in range(count):
            base_query = sample_queries[i % len(sample_queries)]
            # Add some variation
            if i % 10 == 0:
                base_query = base_query[:15] + 'N' + base_query[16:]
            queries.append(base_query)

        return queries

    def _generate_fuzzy_queries(self, count: int) -> List[str]:
        """Generate fuzzy queries with wildcards."""
        sample_queries = [
            "ATGCGATGCTAGCTAGCTAGCGATGCTAGCTA",
            "CGATGCTAGCTAGCTAGCATGCTAGCTAGCG"
        ]

        queries = []
        for i in range(count):
            base_query = sample_queries[i % len(sample_queries)]
            # Add wildcards for fuzzy testing
            if len(base_query) > 20:
                fuzzy_query = base_query[:10] + 'N' + base_query[11:]
            else:
                fuzzy_query = base_query[:5] + 'N' + base_query[6:]
            queries.append(fuzzy_query)

        return queries

    def _calculate_query_stats(self, query_times: List[Dict], tool_name: str) -> Dict[str, Any]:
        """Calculate statistics for query performance."""
        successful_times = [q["time"] for q in query_times if q["success"]]
        memory_usage = [q["memory"] for q in query_times if q["success"] and q["memory"] > 0]

        stats = {
            "tool": tool_name,
            "total_queries": len(query_times),
            "successful_queries": len(successful_times),
            "success_rate": len(successful_times) / len(query_times) if query_times else 0,
            "timestamp": time.time()
        }

        if successful_times:
            stats.update({
                "avg_query_time_seconds": np.mean(successful_times),
                "min_query_time_seconds": min(successful_times),
                "max_query_time_seconds": max(successful_times),
                "std_query_time_seconds": np.std(successful_times),
                "median_query_time_seconds": np.median(successful_times),
                "queries_per_second": 1 / np.mean(successful_times) if np.mean(successful_times) > 0 else 0
            })

        if memory_usage:
            stats.update({
                "avg_memory_mb": np.mean(memory_usage),
                "max_memory_mb": max(memory_usage),
                "min_memory_mb": min(memory_usage)
            })

        return stats

    def save_results(self):
        """Save all results to CSV files."""
        logger.info("Saving performance results...")

        for category, results in self.results.items():
            if not results:
                continue

            df = pd.DataFrame(results)
            csv_file = self.results_dir / f"{category}.csv"
            df.to_csv(csv_file, index=False)
            logger.info(f"Saved {len(results)} results to {csv_file}")

    def generate_performance_report(self):
        """Generate comprehensive performance report."""
        logger.info("Generating performance report...")

        report = {
            "summary": {},
            "database_creation": {},
            "query_performance": {},
            "io_performance": {},
            "workflow_performance": {},
            "recommendations": []
        }

        # Database creation analysis
        if self.results["database_creation"]:
            db_df = pd.DataFrame(self.results["database_creation"])
            successful = db_df[db_df["success"] == True]

            if not successful.empty:
                jellyfish_times = successful[successful["tool"] == "jellyfish"]["execution_time_seconds"]
                rustkmer_times = successful[successful["tool"] == "rustkmer"]["execution_time_seconds"]

                if not jellyfish_times.empty and not rustkmer_times.empty:
                    report["database_creation"] = {
                        "jellyfish_avg_time": jellyfish_times.mean(),
                        "rustkmer_avg_time": rustkmer_times.mean(),
                        "rustkmer_speedup": jellyfish_times.mean() / rustkmer_times.mean(),
                        "jellyfish_avg_memory": jellyfish_times.mean(),
                        "rustkmer_avg_memory": rustkmer_times.mean()
                    }

        # Query performance analysis
        if self.results["query_performance"]:
            query_df = pd.DataFrame(self.results["query_performance"])
            exact_queries = query_df[query_df["operation"] == "query_performance"]

            if not exact_queries.empty:
                jellyfish_queries = exact_queries[exact_queries["tool"] == "jellyfish"]
                rustkmer_queries = exact_queries[exact_queries["tool"] == "rustkmer"]

                if not jellyfish_queries.empty and not rustkmer_queries.empty:
                    report["query_performance"] = {
                        "jellyfish_avg_queries_per_sec": jellyfish_queries["queries_per_second"].mean(),
                        "rustkmer_avg_queries_per_sec": rustkmer_queries["queries_per_second"].mean(),
                        "rustkmer_query_speedup": rustkmer_queries["queries_per_second"].mean() / jellyfish_queries["queries_per_second"].mean(),
                        "jellyfish_success_rate": jellyfish_queries["success_rate"].mean(),
                        "rustkmer_success_rate": rustkmer_queries["success_rate"].mean()
                    }

        # Workflow performance analysis
        if self.results["workflow_performance"]:
            workflow_df = pd.DataFrame(self.results["workflow_performance"])
            jellyfish_workflow = workflow_df[workflow_df["tool"] == "jellyfish"]
            rustkmer_workflow = workflow_df[workflow_df["tool"] == "rustkmer"]

            if not jellyfish_workflow.empty and not rustkmer_workflow.empty:
                report["workflow_performance"] = {
                    "jellyfish_total_time": jellyfish_workflow["total_workflow_time_seconds"].iloc[0],
                    "rustkmer_total_time": rustkmer_workflow["total_workflow_time_seconds"].iloc[0],
                    "rustkmer_workflow_speedup": jellyfish_workflow["total_workflow_time_seconds"].iloc[0] / rustkmer_workflow["total_workflow_time_seconds"].iloc[0]
                }

        # Generate recommendations
        report["recommendations"] = self._generate_recommendations(report)

        # Save report
        report_file = self.reports_dir / "performance_comparison_report.json"
        with open(report_file, 'w') as f:
            json.dump(report, f, indent=2, default=str)

        logger.info(f"Performance report saved to {report_file}")

        return report

    def _generate_recommendations(self, report: Dict[str, Any]) -> List[str]:
        """Generate performance recommendations based on results."""
        recommendations = []

        if "database_creation" in report:
            rustkmer_speedup = report["database_creation"].get("rustkmer_speedup", 1.0)
            if rustkmer_speedup > 1.2:
                recommendations.append(f"RustKmer is {rustkmer_speedup:.1f}x faster for database creation - recommended for large-scale counting")
            elif rustkmer_speedup < 0.8:
                recommendations.append("Jellyfish is faster for database creation - consider using for time-critical operations")

        if "query_performance" in report:
            rustkmer_query_speedup = report["query_performance"].get("rustkmer_query_speedup", 1.0)
            if rustkmer_query_speedup > 1.2:
                recommendations.append(f"RustKmer provides {rustkmer_query_speedup:.1f}x better query throughput - ideal for high-volume querying")
            elif rustkmer_query_speedup < 0.8:
                recommendations.append("Jellyfish has better query performance - use for query-intensive applications")

        if not recommendations:
            recommendations.append("Performance is comparable between tools - choose based on feature requirements")

        return recommendations

    def create_visualizations(self):
        """Create performance visualization charts."""
        logger.info("Creating performance visualizations...")

        # Set up plotting style
        plt.style.use('default')
        sns.set_palette("husl")

        # Database creation performance
        if self.results["database_creation"]:
            self._plot_database_creation_performance()

        # Query performance
        if self.results["query_performance"]:
            self._plot_query_performance()

        # Memory usage
        if self.results["database_creation"]:
            self._plot_memory_usage()

        logger.info("Visualizations saved to reports directory")

    def _plot_database_creation_performance(self):
        """Plot database creation performance comparison."""
        df = pd.DataFrame(self.results["database_creation"])
        successful = df[df["success"] == True]

        if successful.empty:
            return

        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(15, 6))

        # Execution time comparison
        tools = successful["tool"].unique()
        times_by_tool = [successful[successful["tool"] == tool]["execution_time_seconds"] for tool in tools]

        ax1.boxplot(times_by_tool, labels=tools)
        ax1.set_title('Database Creation Time Comparison')
        ax1.set_ylabel('Time (seconds)')
        ax1.set_xlabel('Tool')

        # Memory usage comparison
        memory_by_tool = []
        for tool in tools:
            memory_data = successful[successful["tool"] == tool]["memory_profiling"]
            memory_values = [m["peak_memory_mb"] for m in memory_data if m["peak_memory_mb"] > 0]
            memory_by_tool.append(memory_values if memory_values else [0])

        ax2.boxplot(memory_by_tool, labels=tools)
        ax2.set_title('Peak Memory Usage Comparison')
        ax2.set_ylabel('Memory (MB)')
        ax2.set_xlabel('Tool')

        plt.tight_layout()
        plt.savefig(self.reports_dir / "database_creation_performance.png", dpi=300, bbox_inches='tight')
        plt.close()

    def _plot_query_performance(self):
        """Plot query performance comparison."""
        df = pd.DataFrame(self.results["query_performance"])
        exact_queries = df[df["operation"] == "query_performance"]

        if exact_queries.empty:
            return

        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(15, 6))

        # Queries per second
        tools = exact_queries["tool"].unique()
        qps_by_tool = [exact_queries[exact_queries["tool"] == tool]["queries_per_second"] for tool in tools]

        ax1.boxplot(qps_by_tool, labels=tools)
        ax1.set_title('Query Throughput Comparison')
        ax1.set_ylabel('Queries per Second')
        ax1.set_xlabel('Tool')

        # Success rate
        success_rates = [exact_queries[exact_queries["tool"] == tool]["success_rate"].mean() for tool in tools]

        ax2.bar(tools, success_rates)
        ax2.set_title('Query Success Rate')
        ax2.set_ylabel('Success Rate')
        ax2.set_xlabel('Tool')
        ax2.set_ylim(0, 1)

        plt.tight_layout()
        plt.savefig(self.reports_dir / "query_performance.png", dpi=300, bbox_inches='tight')
        plt.close()

    def _plot_memory_usage(self):
        """Plot memory usage comparison."""
        df = pd.DataFrame(self.results["database_creation"])
        successful = df[df["success"] == True]

        if successful.empty:
            return

        fig, ax = plt.subplots(figsize=(10, 6))

        # Memory usage over time
        for tool in successful["tool"].unique():
            tool_data = successful[successful["tool"] == tool]
            memory_data = tool_data["memory_profiling"]

            avg_memories = [m["avg_memory_mb"] for m in memory_data if m["avg_memory_mb"] > 0]
            if avg_memories:
                ax.hist(avg_memories, alpha=0.7, label=tool, bins=20)

        ax.set_title('Memory Usage Distribution')
        ax.set_xlabel('Average Memory Usage (MB)')
        ax.set_ylabel('Frequency')
        ax.legend()

        plt.tight_layout()
        plt.savefig(self.reports_dir / "memory_usage.png", dpi=300, bbox_inches='tight')
        plt.close()

    def print_summary(self, report: Dict[str, Any]):
        """Print performance summary to console."""
        print("\n" + "="*80)
        print("RUSTKMER vs JELLYFISH PERFORMANCE COMPARISON SUMMARY")
        print("="*80)

        if "database_creation" in report:
            db = report["database_creation"]
            print(f"\n📊 DATABASE CREATION PERFORMANCE:")
            print(f"   Jellyfish Average Time: {db.get('jellyfish_avg_time', 'N/A'):.2f}s")
            print(f"   RustKmer Average Time:  {db.get('rustkmer_avg_time', 'N/A'):.2f}s")
            if db.get('rustkmer_speedup'):
                speedup = db['rustkmer_speedup']
                print(f"   RustKmer Speedup: {speedup:.2f}x {'✅' if speedup > 1 else '⚠️'}")

        if "query_performance" in report:
            qp = report["query_performance"]
            print(f"\n⚡ QUERY PERFORMANCE:")
            print(f"   Jellyfish QPS: {qp.get('jellyfish_avg_queries_per_sec', 'N/A'):.1f}")
            print(f"   RustKmer QPS:   {qp.get('rustkmer_avg_queries_per_sec', 'N/A'):.1f}")
            if qp.get('rustkmer_query_speedup'):
                speedup = qp['rustkmer_query_speedup']
                print(f"   RustKmer Speedup: {speedup:.2f}x {'✅' if speedup > 1 else '⚠️'}")

        if "workflow_performance" in report:
            wf = report["workflow_performance"]
            print(f"\n🔄 WORKFLOW PERFORMANCE:")
            print(f"   Jellyfish Total Time: {wf.get('jellyfish_total_time', 'N/A'):.2f}s")
            print(f"   RustKmer Total Time:  {wf.get('rustkmer_total_time', 'N/A'):.2f}s")
            if wf.get('rustkmer_workflow_speedup'):
                speedup = wf['rustkmer_workflow_speedup']
                print(f"   RustKmer Speedup: {speedup:.2f}x {'✅' if speedup > 1 else '⚠️'}")

        if report.get("recommendations"):
            print(f"\n💡 RECOMMENDATIONS:")
            for i, rec in enumerate(report["recommendations"], 1):
                print(f"   {i}. {rec}")

        print(f"\n📁 Detailed results saved to: {self.reports_dir}")
        print("="*80)

    def run_complete_comparison(self):
        """Execute complete performance comparison."""
        logger.info("Starting comprehensive performance comparison...")
        start_time = time.time()

        try:
            # Check if RustKmer binary exists
            if not Path("./target/release/rustkmer").exists():
                logger.error("RustKmer binary not found. Please run 'cargo build --release' first.")
                return

            # Execute performance tests
            self.test_database_creation_performance()
            self.test_query_performance()
            self.test_io_performance()
            self.test_workflow_performance()

            # Save results
            self.save_results()

            # Generate report
            report = self.generate_performance_report()

            # Create visualizations
            self.create_visualizations()

            # Print summary
            self.print_summary(report)

            end_time = time.time()
            logger.info(f"Performance comparison completed in {end_time - start_time:.2f} seconds")

        except Exception as e:
            logger.error(f"Performance comparison failed: {e}")
            raise

def main():
    """Main entry point for performance comparison."""
    print("🚀 RustKmer vs Jellyfish Comprehensive Performance Comparison")
    print("=" * 80)

    comparison = ComprehensivePerformanceTest()
    comparison.run_complete_comparison()

    print("\n✅ Performance comparison completed successfully!")
    print("📊 Reports and visualizations available in: /Users/forrest/Temp/demodata/performance_comparison/reports/")

if __name__ == "__main__":
    main()