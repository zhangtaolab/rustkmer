#!/usr/bin/env python3
"""
Performance benchmarking suite for CLI vs Python API compatibility validation.
Ensures Python API maintains <10% overhead compared to native CLI operations.
"""

import os
import subprocess
import time
import json
import statistics
from typing import Dict, List, Any, Tuple
import tempfile
import matplotlib.pyplot as plt
import numpy as np

class PerformanceBenchmark:
    """Benchmark performance between CLI and Python API."""

    def __init__(self, cli_path: str = "rustkmer"):
        self.cli_path = cli_path
        self.benchmark_results = []

    def benchmark_cli_creation(
        self,
        input_file: str,
        output_path: str,
        kmer_size: int = 21,
        canonical: bool = True,
        iterations: int = 3
    ) -> Dict[str, Any]:
        """Benchmark CLI database creation."""
        times = []
        success_count = 0

        for i in range(iterations):
            # Remove existing database
            if os.path.exists(output_path):
                os.remove(output_path)

            start_time = time.time()
            cmd = [
                self.cli_path, "count",
                "-k", str(kmer_size),
                "--canonical" if canonical else "--no-canonical",
                "-o", output_path,
                input_file
            ]

            try:
                subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    check=True,
                    timeout=300
                )
                end_time = time.time()
                times.append(end_time - start_time)
                success_count += 1
            except (subprocess.CalledProcessError, subprocess.TimeoutExpired):
                continue

        if not times:
            return {
                "success": False,
                "error": "All iterations failed"
            }

        return {
            "success": True,
            "success_rate": (success_count / iterations) * 100,
            "times": times,
            "mean_time": statistics.mean(times),
            "median_time": statistics.median(times),
            "std_dev": statistics.stdev(times) if len(times) > 1 else 0,
            "min_time": min(times),
            "max_time": max(times)
        }

    def benchmark_python_creation(
        self,
        input_file: str,
        output_path: str,
        kmer_size: int = 21,
        canonical: bool = True,
        iterations: int = 3
    ) -> Dict[str, Any]:
        """Benchmark Python API database creation."""
        times = []
        success_count = 0

        try:
            import rustkmer
            from rustkmer import KmerCounter
        except ImportError:
            return {
                "success": False,
                "error": "Python API module not available"
            }

        for i in range(iterations):
            # Remove existing database
            if os.path.exists(output_path):
                os.remove(output_path)

            start_time = time.time()

            try:
                # Create k-mer counter
                counter = KmerCounter(k=kmer_size, canonical=canonical)

                # Process input file
                if input_file.endswith(('.fasta', '.fa')):
                    counter.process_fasta(input_file)
                elif input_file.endswith(('.fastq', '.fq')):
                    counter.process_fastq(input_file)
                else:
                    continue

                # Save to database
                counter.save_to_database(output_path)
                end_time = time.time()
                times.append(end_time - start_time)
                success_count += 1

            except Exception:
                continue

        if not times:
            return {
                "success": False,
                "error": "All iterations failed"
            }

        return {
            "success": True,
            "success_rate": (success_count / iterations) * 100,
            "times": times,
            "mean_time": statistics.mean(times),
            "median_time": statistics.median(times),
            "std_dev": statistics.stdev(times) if len(times) > 1 else 0,
            "min_time": min(times),
            "max_time": max(times)
        }

    def benchmark_cli_query(
        self,
        database_path: str,
        kmers: List[str],
        iterations: int = 3
    ) -> Dict[str, Any]:
        """Benchmark CLI query operations."""
        all_times = []
        success_count = 0

        for i in range(iterations):
            times = []
            iteration_success = True

            for kmer in kmers:
                cmd = [
                    self.cli_path, "query",
                    "-d", database_path,
                    kmer
                ]

                start_time = time.time()
                try:
                    subprocess.run(
                        cmd,
                        capture_output=True,
                        text=True,
                        check=True,
                        timeout=60
                    )
                    end_time = time.time()
                    times.append(end_time - start_time)
                except (subprocess.CalledProcessError, subprocess.TimeoutExpired):
                    iteration_success = False
                    break

            if iteration_success and times:
                all_times.extend(times)
                success_count += 1

        if not all_times:
            return {
                "success": False,
                "error": "All iterations failed"
            }

        return {
            "success": True,
            "success_rate": (success_count / iterations) * 100,
            "times": all_times,
            "mean_time": statistics.mean(all_times),
            "median_time": statistics.median(all_times),
            "std_dev": statistics.stdev(all_times) if len(all_times) > 1 else 0,
            "min_time": min(all_times),
            "max_time": max(all_times),
            "queries_per_second": len(kmers) / statistics.mean(all_times)
        }

    def benchmark_python_query(
        self,
        database_path: str,
        kmers: List[str],
        iterations: int = 3
    ) -> Dict[str, Any]:
        """Benchmark Python API query operations."""
        all_times = []
        success_count = 0

        try:
            import rustkmer
            from rustkmer import Database
        except ImportError:
            return {
                "success": False,
                "error": "Python API module not available"
            }

        # Pre-load database
        db = Database(database_path)

        for i in range(iterations):
            times = []
            iteration_success = True

            for kmer in kmers:
                start_time = time.time()
                try:
                    db.query(kmer)
                    end_time = time.time()
                    times.append(end_time - start_time)
                except Exception:
                    iteration_success = False
                    break

            if iteration_success and times:
                all_times.extend(times)
                success_count += 1

        if not all_times:
            return {
                "success": False,
                "error": "All iterations failed"
            }

        return {
            "success": True,
            "success_rate": (success_count / iterations) * 100,
            "times": all_times,
            "mean_time": statistics.mean(all_times),
            "median_time": statistics.median(all_times),
            "std_dev": statistics.stdev(all_times) if len(all_times) > 1 else 0,
            "min_time": min(all_times),
            "max_time": max(all_times),
            "queries_per_second": len(kmers) / statistics.mean(all_times)
        }

    def run_performance_benchmark(
        self,
        input_file: str,
        output_pattern: str = "benchmark_test",
        kmer_size: int = 21,
        iterations: int = 3
    ) -> Dict[str, Any]:
        """Run complete performance benchmark."""
        benchmark_start = time.time()

        with tempfile.TemporaryDirectory() as temp_dir:
            cli_db = os.path.join(temp_dir, f"{output_pattern}_cli.rkdb")
            python_db = os.path.join(temp_dir, f"{output_pattern}_python.rkdb")

            results = {
                "input_file": input_file,
                "kmer_size": kmer_size,
                "iterations": iterations,
                "benchmark_start": benchmark_start,
                "creation_benchmark": None,
                "query_benchmark": None,
                "overhead_analysis": None,
                "benchmark_duration": None
            }

            # Benchmark database creation
            print("Benchmarking database creation...")
            creation_start = time.time()

            cli_creation = self.benchmark_cli_creation(
                input_file, cli_db, kmer_size, True, iterations
            )
            python_creation = self.benchmark_python_creation(
                input_file, python_db, kmer_size, True, iterations
            )

            creation_end = time.time()
            results["creation_benchmark"] = {
                "cli": cli_creation,
                "python": python_creation,
                "creation_duration": creation_end - creation_start
            }

            # Benchmark queries (if databases created successfully)
            if (cli_creation["success"] and python_creation["success"] and
                os.path.exists(cli_db) and os.path.exists(python_db)):

                print("Benchmarking query operations...")
                query_start = time.time()

                # Generate test k-mers
                test_kmers = ["ACGTACGTACGTACGTACGT", "TGCATGCATGCATGCATGCA", "ATCGATCGATCGATCGATCG"]

                cli_query = self.benchmark_cli_query(cli_db, test_kmers, iterations)
                python_query = self.benchmark_python_query(python_db, test_kmers, iterations)

                query_end = time.time()
                results["query_benchmark"] = {
                    "cli": cli_query,
                    "python": python_query,
                    "query_duration": query_end - query_start
                }

                # Calculate overhead analysis
                results["overhead_analysis"] = self._analyze_overhead(
                    cli_creation, python_creation, cli_query, python_query
                )

        results["benchmark_duration"] = time.time() - benchmark_start
        results["benchmark_end"] = time.time()

        self.benchmark_results.append(results)
        return results

    def _analyze_overhead(
        self,
        cli_creation: Dict[str, Any],
        python_creation: Dict[str, Any],
        cli_query: Dict[str, Any],
        python_query: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Analyze performance overhead between CLI and Python API."""

        analysis = {
            "creation_overhead_percent": 0,
            "query_overhead_percent": 0,
            "within_10_percent_target": False,
            "creation_recommendation": "OK",
            "query_recommendation": "OK"
        }

        # Calculate creation overhead
        if (cli_creation["success"] and python_creation["success"] and
            cli_creation["mean_time"] > 0):
            creation_overhead = ((python_creation["mean_time"] - cli_creation["mean_time"])
                                / cli_creation["mean_time"]) * 100
            analysis["creation_overhead_percent"] = creation_overhead

            if creation_overhead > 20:
                analysis["creation_recommendation"] = "HIGH OVERHEAD"
            elif creation_overhead > 10:
                analysis["creation_recommendation"] = "ABOVE TARGET"
            else:
                analysis["creation_recommendation"] = "WITHIN TARGET"

        # Calculate query overhead
        if (cli_query["success"] and python_query["success"] and
            cli_query["mean_time"] > 0):
            query_overhead = ((python_query["mean_time"] - cli_query["mean_time"])
                              / cli_query["mean_time"]) * 100
            analysis["query_overhead_percent"] = query_overhead

            if query_overhead > 20:
                analysis["query_recommendation"] = "HIGH OVERHEAD"
            elif query_overhead > 10:
                analysis["query_recommendation"] = "ABOVE TARGET"
            else:
                analysis["query_recommendation"] = "WITHIN TARGET"

        # Overall assessment
        analysis["within_10_percent_target"] = (
            abs(analysis["creation_overhead_percent"]) <= 10 and
            abs(analysis["query_overhead_percent"]) <= 10
        )

        return analysis

    def generate_report(self, output_file: str = None) -> str:
        """Generate performance benchmark report."""
        if not self.benchmark_results:
            return "No benchmark results available"

        report = []
        report.append("# Performance Benchmark Report")
        report.append(f"Generated: {time.strftime('%Y-%m-%d %H:%M:%S')}")
        report.append("")

        for i, result in enumerate(self.benchmark_results, 1):
            report.append(f"## Benchmark {i}: {os.path.basename(result['input_file'])}")
            report.append(f"- K-mer Size: {result['kmer_size']}")
            report.append(f"- Iterations: {result['iterations']}")
            report.append(f"- Duration: {result['benchmark_duration']:.2f}s")
            report.append("")

            if result.get("creation_benchmark"):
                report.append("### Database Creation Performance")
                creation = result["creation_benchmark"]
                report.append(f"- CLI Mean Time: {creation['cli']['mean_time']:.4f}s")
                report.append(f"- Python Mean Time: {creation['python']['mean_time']:.4f}s")
                report.append("")

            if result.get("query_benchmark"):
                report.append("### Query Performance")
                query = result["query_benchmark"]
                report.append(f"- CLI QPS: {query['cli']['queries_per_second']:.2f}")
                report.append(f"- Python QPS: {query['python']['queries_per_second']:.2f}")
                report.append("")

            if result.get("overhead_analysis"):
                overhead = result["overhead_analysis"]
                report.append("### Overhead Analysis")
                report.append(f"- Creation Overhead: {overhead['creation_overhead_percent']:.2f}%")
                report.append(f"- Query Overhead: {overhead['query_overhead_percent']:.2f}%")
                report.append(f"- Within 10% Target: {'✓' if overhead['within_10_percent_target'] else '✗'}")
                report.append("")

            report.append("---")

        report_text = "\n".join(report)

        if output_file:
            with open(output_file, 'w') as f:
                f.write(report_text)

        return report_text

    def get_benchmark_summary(self) -> Dict[str, Any]:
        """Get summary of all benchmark results."""
        if not self.benchmark_results:
            return {"total_benchmarks": 0}

        total_benchmarks = len(self.benchmark_results)
        within_target = sum(1 for result in self.benchmark_results
                           if result.get("overhead_analysis", {}).get("within_10_percent_target", False))

        avg_creation_overhead = statistics.mean([
            result.get("overhead_analysis", {}).get("creation_overhead_percent", 0)
            for result in self.benchmark_results
            if result.get("overhead_analysis")
        ])

        avg_query_overhead = statistics.mean([
            result.get("overhead_analysis", {}).get("query_overhead_percent", 0)
            for result in self.benchmark_results
            if result.get("overhead_analysis")
        ])

        return {
            "total_benchmarks": total_benchmarks,
            "within_target_count": within_target,
            "within_target_rate": (within_target / total_benchmarks) * 100 if total_benchmarks > 0 else 0,
            "average_creation_overhead": avg_creation_overhead,
            "average_query_overhead": avg_query_overhead
        }


# Example usage
if __name__ == "__main__":
    benchmark = PerformanceBenchmark()

    # Find sample input file
    sample_files = [
        "test_data/small/sample.fasta",
        "test_data/small/sample.fastq"
    ]

    for sample_file in sample_files:
        if os.path.exists(sample_file):
            print(f"Benchmarking with {sample_file}")
            result = benchmark.run_performance_benchmark(sample_file, iterations=2)
            print(f"Overhead Analysis: {result.get('overhead_analysis', {})}")
            print("-" * 50)

    # Generate report
    report = benchmark.generate_report("benchmark_report.md")
    print("Report generated: benchmark_report.md")

    summary = benchmark.get_benchmark_summary()
    print(f"Benchmark Summary: {summary}")