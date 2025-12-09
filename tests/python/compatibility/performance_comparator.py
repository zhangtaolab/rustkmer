"""
Performance measurement utilities for RustKmer CLI-Python API compatibility testing.

This module provides tools to measure and compare performance between the Python API
and CLI commands, including timing, memory usage, and statistical analysis.
"""

import time
import psutil
import statistics
import json
import threading
from typing import Dict, List, Any, Optional, Callable, Union
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class PerformanceData:
    """Performance measurement data."""

    times: List[float] = field(default_factory=list)
    memory_usage: List[float] = field(default_factory=list)
    cpu_usage: List[float] = field(default_factory=list)

    def __post_init__(self):
        """Calculate derived statistics."""
        self.mean_time = statistics.mean(self.times) if self.times else 0
        self.min_time = min(self.times) if self.times else 0
        self.max_time = max(self.times) if self.times else 0
        self.std_dev_time = statistics.stdev(self.times) if len(self.times) > 1 else 0

        self.mean_memory = statistics.mean(self.memory_usage) if self.memory_usage else 0
        self.min_memory = min(self.memory_usage) if self.memory_usage else 0
        self.max_memory = max(self.memory_usage) if self.memory_usage else 0
        self.std_dev_memory = statistics.stdev(self.memory_usage) if len(self.memory_usage) > 1 else 0

        self.mean_cpu = statistics.mean(self.cpu_usage) if self.cpu_usage else 0
        self.std_dev_cpu = statistics.stdev(self.cpu_usage) if len(self.cpu_usage) > 1 else 0

    def get_confidence_interval(self, confidence: float = 0.95) -> Dict[str, float]:
        """
        Calculate confidence interval for mean.

        Args:
            confidence: Confidence level (0.0 to 1.0)

        Returns:
            Dictionary with lower and upper bounds
        """
        if len(self.times) < 2:
            return {"lower": 0, "upper": 0}

        # Use t-distribution for small samples
        # For simplicity, using normal approximation
        from math import sqrt
        z_score = 1.96 if confidence == 0.95 else 2.576  # 99% CI
        margin = z_score * (self.std_dev_time / sqrt(len(self.times)))

        return {
            "lower": self.mean_time - margin,
            "upper": self.mean_time + margin
        }


@dataclass
class PerformanceResult:
    """Result of performance comparison between Python API and CLI."""

    python_time_ms: float
    cli_time_ms: float
    python_memory_mb: float
    cli_memory_mb: float
    python_cpu_percent: float
    cli_cpu_percent: float
    ratio: float  # python_time / cli_time
    memory_ratio: float  # python_memory / cli_memory
    within_threshold: bool
    within_memory_threshold: bool

    @property
    def performance_ratio(self) -> float:
        """Get performance ratio (Python/CLI)."""
        return self.ratio

    @property
    def is_acceptable(self) -> bool:
        """Check if performance is within acceptable thresholds."""
        return self.within_threshold and self.within_memory_threshold


class PerformanceComparator:
    """Compare performance between Python API and CLI."""

    def __init__(self, runs: int = 5, time_threshold: float = 1.10, memory_threshold: float = 1.05):
        """
        Initialize the performance comparator.

        Args:
            runs: Number of measurement runs for statistical accuracy
            time_threshold: Acceptable time ratio (Python/CLI)
            memory_threshold: Acceptable memory ratio (Python/CLI)
        """
        self.runs = runs
        self.time_threshold = time_threshold
        self.memory_threshold = memory_threshold
        self.results: List[Dict[str, Any]] = []

    def measure_python_api(
        self,
        func: Callable,
        *args,
        **kwargs
    ) -> PerformanceData:
        """
        Measure Python API performance.

        Args:
            func: Function to measure
            *args: Function arguments
            **kwargs: Function keyword arguments

        Returns:
            PerformanceData with measurements
        """
        times = []
        memory_usage = []
        cpu_usage = []

        # Get process for monitoring
        process = psutil.Process()

        for _ in range(self.runs):
            # Measure initial state
            start_time = time.time()
            start_mem = process.memory_info().rss

            # Start CPU monitoring in background
            cpu_samples = []
            stop_cpu_monitor = threading.Event()

            def monitor_cpu():
                while not stop_cpu_monitor.is_set():
                    try:
                        cpu_samples.append(process.cpu_percent())
                        time.sleep(0.01)  # Sample every 10ms
                    except:
                        break

            cpu_thread = threading.Thread(target=monitor_cpu)
            cpu_thread.start()

            try:
                # Run the function
                result = func(*args, **kwargs)

                # Stop CPU monitoring
                stop_cpu_monitor.set()
                cpu_thread.join(timeout=0.1)

                # Calculate elapsed time and memory
                end_time = time.time()
                end_mem = process.memory_info().rss

                elapsed_ms = (end_time - start_time) * 1000
                memory_mb = (end_mem - start_mem) / 1024 / 1024

                times.append(elapsed_ms)
                memory_usage.append(memory_mb)
                cpu_usage.append(statistics.mean(cpu_samples) if cpu_samples else 0)

            except Exception as e:
                stop_cpu_monitor.set()
                cpu_thread.join(timeout=0.1)
                raise e

        return PerformanceData(
            times=times,
            memory_usage=memory_usage,
            cpu_usage=cpu_usage
        )

    def measure_cli_command(
        self,
        command: List[str],
        cli_path: str = "rustkmer",
        timeout: int = 300
    ) -> PerformanceData:
        """
        Measure CLI command performance.

        Args:
            command: CLI command arguments (excluding binary)
            cli_path: Path to CLI binary
            timeout: Command timeout in seconds

        Returns:
            PerformanceData with measurements
        """
        import subprocess

        times = []
        memory_usage = []
        cpu_usage = []

        for _ in range(self.runs):
            # Monitor current process (parent)
            process = psutil.Process()

            # Start CPU monitoring
            cpu_samples = []
            stop_cpu_monitor = threading.Event()

            def monitor_cpu():
                while not stop_cpu_monitor.is_set():
                    try:
                        cpu_samples.append(process.cpu_percent())
                        time.sleep(0.01)
                    except:
                        break

            cpu_thread = threading.Thread(target=monitor_cpu)
            cpu_thread.start()

            try:
                # Measure initial state
                start_time = time.time()
                start_mem = process.memory_info().rss

                # Run CLI command
                result = subprocess.run(
                    [cli_path] + command,
                    capture_output=True,
                    text=True,
                    timeout=timeout
                )

                # Stop CPU monitoring
                stop_cpu_monitor.set()
                cpu_thread.join(timeout=0.1)

                # Calculate metrics
                end_time = time.time()
                end_mem = process.memory_info().rss

                elapsed_ms = (end_time - start_time) * 1000
                memory_mb = (end_mem - start_mem) / 1024 / 1024

                times.append(elapsed_ms)
                memory_usage.append(memory_mb)
                cpu_usage.append(statistics.mean(cpu_samples) if cpu_samples else 0)

            except subprocess.TimeoutExpired:
                stop_cpu_monitor.set()
                cpu_thread.join(timeout=0.1)
                raise TimeoutError(f"Command timed out after {timeout} seconds")
            except Exception as e:
                stop_cpu_monitor.set()
                cpu_thread.join(timeout=0.1)
                raise e

        return PerformanceData(
            times=times,
            memory_usage=memory_usage,
            cpu_usage=cpu_usage
        )

    def compare_performance(
        self,
        python_data: PerformanceData,
        cli_data: PerformanceData,
        test_name: str = "Unknown"
    ) -> PerformanceResult:
        """
        Compare performance between Python and CLI.

        Args:
            python_data: Performance measurements from Python API
            cli_data: Performance measurements from CLI
            test_name: Name of the test being measured

        Returns:
            PerformanceResult with comparison
        """
        ratio = python_data.mean_time / cli_data.mean_time if cli_data.mean_time > 0 else 1.0
        memory_ratio = python_data.mean_memory / cli_data.mean_memory if cli_data.mean_memory > 0 else 1.0

        result = PerformanceResult(
            python_time_ms=python_data.mean_time,
            cli_time_ms=cli_data.mean_time,
            python_memory_mb=python_data.mean_memory,
            cli_memory_mb=cli_data.mean_memory,
            python_cpu_percent=python_data.mean_cpu,
            cli_cpu_percent=cli_data.mean_cpu,
            ratio=ratio,
            memory_ratio=memory_ratio,
            within_threshold=ratio <= self.time_threshold,
            within_memory_threshold=memory_ratio <= self.memory_threshold
        )

        # Store result for later reporting
        self.results.append({
            "test_name": test_name,
            "python": {
                "time_ms": python_data.mean_time,
                "memory_mb": python_data.mean_memory,
                "cpu_percent": python_data.mean_cpu,
                "times": python_data.times,
                "memory": python_data.memory_usage
            },
            "cli": {
                "time_ms": cli_data.mean_time,
                "memory_mb": cli_data.mean_memory,
                "cpu_percent": cli_data.mean_cpu,
                "times": cli_data.times,
                "memory": cli_data.memory_usage
            },
            "comparison": {
                "ratio": ratio,
                "memory_ratio": memory_ratio,
                "within_threshold": result.within_threshold,
                "within_memory_threshold": result.within_memory_threshold
            }
        })

        return result

    def generate_comparison_report(self, python_data: PerformanceData, cli_data: PerformanceData) -> Dict[str, Any]:
        """
        Generate a detailed performance comparison report.

        Args:
            python_data: Performance measurements from Python API
            cli_data: Performance measurements from CLI

        Returns:
            Dictionary with comparison report
        """
        ratio = python_data.mean_time / cli_data.mean_time if cli_data.mean_time > 0 else 1.0
        memory_ratio = python_data.mean_memory / cli_data.mean_memory if cli_data.mean_memory > 0 else 1.0

        return {
            "performance": {
                "python": {
                    "mean_time_ms": python_data.mean_time,
                    "min_time_ms": python_data.min_time,
                    "max_time_ms": python_data.max_time,
                    "std_dev_ms": python_data.std_dev_time,
                    "confidence_interval_95": python_data.get_confidence_interval()
                },
                "cli": {
                    "mean_time_ms": cli_data.mean_time,
                    "min_time_ms": cli_data.min_time,
                    "max_time_ms": cli_data.max_time,
                    "std_dev_ms": cli_data.std_dev_time,
                    "confidence_interval_95": cli_data.get_confidence_interval()
                },
                "comparison": {
                    "ratio": ratio,
                    "within_threshold": ratio <= self.time_threshold,
                    "threshold": self.time_threshold
                }
            },
            "memory": {
                "python": {
                    "mean_mb": python_data.mean_memory,
                    "min_mb": python_data.min_memory,
                    "max_mb": python_data.max_memory,
                    "std_dev_mb": python_data.std_dev_memory
                },
                "cli": {
                    "mean_mb": cli_data.mean_memory,
                    "min_mb": cli_data.min_memory,
                    "max_mb": cli_data.max_memory,
                    "std_dev_mb": cli_data.std_dev_memory
                },
                "comparison": {
                    "ratio": memory_ratio,
                    "within_threshold": memory_ratio <= self.memory_threshold,
                    "threshold": self.memory_threshold
                }
            },
            "cpu": {
                "python": {
                    "mean_percent": python_data.mean_cpu,
                    "std_dev_percent": python_data.std_dev_cpu
                },
                "cli": {
                    "mean_percent": cli_data.mean_cpu,
                    "std_dev_percent": cli_data.std_dev_cpu
                }
            },
            "runs": self.runs
        }

    def save_report(self, output_path: str):
        """
        Save all performance results to a JSON file.

        Args:
            output_path: Path to save the report
        """
        report = {
            "configuration": {
                "runs": self.runs,
                "time_threshold": self.time_threshold,
                "memory_threshold": self.memory_threshold
            },
            "results": self.results,
            "summary": self._generate_summary()
        }

        with open(output_path, 'w') as f:
            json.dump(report, f, indent=2, default=str)

    def _generate_summary(self) -> Dict[str, Any]:
        """Generate summary statistics from all results."""
        if not self.results:
            return {}

        total_tests = len(self.results)
        passed_time_threshold = sum(1 for r in self.results
                                  if r["comparison"]["within_threshold"])
        passed_memory_threshold = sum(1 for r in self.results
                                     if r["comparison"]["within_memory_threshold"])
        passed_all = sum(1 for r in self.results
                        if r["comparison"]["within_threshold"] and
                           r["comparison"]["within_memory_threshold"])

        # Calculate average ratios
        avg_time_ratio = statistics.mean([r["comparison"]["ratio"] for r in self.results])
        avg_memory_ratio = statistics.mean([r["comparison"]["memory_ratio"] for r in self.results])

        return {
            "total_tests": total_tests,
            "passed_time_threshold": passed_time_threshold,
            "passed_memory_threshold": passed_memory_threshold,
            "passed_all": passed_all,
            "success_rate": passed_all / total_tests if total_tests > 0 else 0,
            "average_time_ratio": avg_time_ratio,
            "average_memory_ratio": avg_memory_ratio
        }


class PerformanceBenchmark:
    """High-level benchmarking utilities for RustKmer."""

    def __init__(self, comparator: Optional[PerformanceComparator] = None):
        """
        Initialize the benchmark.

        Args:
            comparator: Custom PerformanceComparator instance
        """
        self.comparator = comparator or PerformanceComparator()

    def benchmark_kmer_counting(
        self,
        file_path: str,
        k: int = 31,
        canonical: bool = False
    ) -> Dict[str, Any]:
        """
        Benchmark k-mer counting performance.

        Args:
            file_path: Path to input file
            k: K-mer size
            canonical: Whether to use canonical counting

        Returns:
            Benchmark results
        """
        # Python API benchmark
        def python_count():
            from rustkmer import KmerCounter
            counter = KmerCounter(k=k, canonical=canonical)
            counter.count_file(file_path)
            return counter.get_total_count()

        python_data = self.comparator.measure_python_api(python_count)

        # CLI benchmark
        cli_args = ['count', '-k', str(k)]
        if canonical:
            cli_args.append('--canonical')

        cli_data = self.comparator.measure_cli_command(cli_args + [file_path])

        # Generate report
        return self.comparator.generate_comparison_report(python_data, cli_data)

    def benchmark_database_query(
        self,
        db_path: str,
        queries: List[str]
    ) -> Dict[str, Any]:
        """
        Benchmark database query performance.

        Args:
            db_path: Path to RKDB database
            queries: List of query sequences

        Returns:
            Benchmark results
        """
        # Python API benchmark
        def python_query():
            from rustkmer import Database
            db = Database.load(db_path)
            results = []
            for seq in queries:
                results.append(db.query(seq))
            return results

        python_data = self.comparator.measure_python_api(python_query)

        # CLI benchmark (average over all queries)
        cli_times = []
        cli_memory = []

        for seq in queries:
            cli_data = self.comparator.measure_cli_command(
                ['query', db_path, seq]
            )
            cli_times.append(cli_data.mean_time)
            cli_memory.append(cli_data.mean_memory)

        # Create averaged CLI data
        avg_cli_data = PerformanceData(
            times=cli_times,
            memory_usage=cli_memory,
            cpu_usage=[0] * len(cli_times)
        )

        # Generate report
        return self.comparator.generate_comparison_report(python_data, avg_cli_data)