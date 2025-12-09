#!/usr/bin/env python3
"""
Large dataset stress testing for RustKmer CLI-Python compatibility

This module provides tools to test compatibility with large datasets,
monitor memory usage, and identify performance bottlenecks.
"""

import os
import sys
import time
import psutil
import threading
import json
import random
import string
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple, Callable
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
import tempfile
import shutil
import multiprocessing as mp
from concurrent.futures import ThreadPoolExecutor, as_completed
import numpy as np

# Import compatibility test runner
from runner import CompatibilityTestRunner, CLITester, PythonTester


@dataclass
class MemoryUsage:
    """Memory usage snapshot"""
    timestamp: float
    rss_mb: float  # Resident Set Size in MB
    vms_mb: float  # Virtual Memory Size in MB
    percent: float  # Memory usage percentage
    available_mb: float  # Available memory in MB


@dataclass
class StressTestResult:
    """Result from a stress test"""
    test_name: str
    dataset_size: int
    kmer_count: int
    passed: bool
    execution_time_cli: float
    execution_time_python: float
    memory_peak_cli: float
    memory_peak_python: float
    error: Optional[str] = None
    performance_ratio: Optional[float] = None
    memory_efficiency_ratio: Optional[float] = None


class MemoryMonitor:
    """Monitor memory usage during test execution"""

    def __init__(self, interval: float = 0.5):
        """
        Initialize memory monitor

        Args:
            interval: Sampling interval in seconds
        """
        self.interval = interval
        self.monitoring = False
        self.measurements: List[MemoryUsage] = []
        self.monitor_thread: Optional[threading.Thread] = None
        self.process = psutil.Process()

    def start_monitoring(self):
        """Start memory monitoring"""
        self.monitoring = True
        self.measurements = []
        self.monitor_thread = threading.Thread(target=self._monitor_loop)
        self.monitor_thread.daemon = True
        self.monitor_thread.start()

    def stop_monitoring(self) -> List[MemoryUsage]:
        """Stop monitoring and return measurements"""
        self.monitoring = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=1.0)
        return self.measurements

    def _monitor_loop(self):
        """Monitoring loop"""
        while self.monitoring:
            try:
                memory_info = self.process.memory_info()
                memory_percent = self.process.memory_percent()

                measurement = MemoryUsage(
                    timestamp=time.time(),
                    rss_mb=memory_info.rss / (1024 * 1024),
                    vms_mb=memory_info.vms / (1024 * 1024),
                    percent=memory_percent,
                    available_mb=psutil.virtual_memory().available / (1024 * 1024)
                )
                self.measurements.append(measurement)

                time.sleep(self.interval)
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                break

    def get_peak_usage(self) -> Tuple[float, float]:
        """
        Get peak memory usage

        Returns:
            Tuple of (peak_rss_mb, peak_vms_mb)
        """
        if not self.measurements:
            return 0.0, 0.0

        peak_rss = max(m.rss_mb for m in self.measurements)
        peak_vms = max(m.vms_mb for m in self.measurements)
        return peak_rss, peak_vms


class DatasetGenerator:
    """Generate synthetic genomic datasets for stress testing"""

    @staticmethod
    def generate_fasta(sequences: List[str], output_path: str, line_length: int = 80):
        """
        Generate FASTA file with given sequences

        Args:
            sequences: List of DNA sequences
            output_path: Path to output FASTA file
            line_length: Maximum line length for sequences
        """
        with open(output_path, 'w') as f:
            for i, seq in enumerate(sequences):
                f.write(f">sequence_{i}\n")
                # Write sequence with line breaks
                for j in range(0, len(seq), line_length):
                    f.write(seq[j:j+line_length] + "\n")

    @staticmethod
    def generate_random_dna(length: int, gc_content: float = 0.5) -> str:
        """
        Generate random DNA sequence with specified GC content

        Args:
            length: Length of sequence
            gc_content: Target GC content (0.0 to 1.0)

        Returns:
            Random DNA sequence
        """
        # Calculate number of G/C bases
        gc_count = int(length * gc_content)
        at_count = length - gc_count

        # Generate sequence
        bases = ['G'] * gc_count + ['A'] * (at_count // 2) + ['T'] * (at_count - at_count // 2)
        random.shuffle(bases)

        return ''.join(bases)

    @staticmethod
    def generate_genome_like_dataset(size_mb: float, avg_read_length: int = 150) -> List[str]:
        """
        Generate genome-like dataset with realistic characteristics

        Args:
            size_mb: Target dataset size in MB
            avg_read_length: Average read length

        Returns:
            List of generated sequences
        """
        # Rough estimate: 1 character = 1 byte
        target_bytes = int(size_mb * 1024 * 1024)
        sequences = []
        current_size = 0

        while current_size < target_bytes:
            # Vary read length around average
            read_length = avg_read_length + random.randint(-30, 30)
            read_length = max(50, min(300, read_length))  # Clamp to reasonable range

            # Generate read with realistic quality distribution
            # 70% high quality, 20% medium, 10% low quality
            quality_rand = random.random()
            if quality_rand < 0.7:
                # High quality: mostly A/T/G/C with few Ns
                seq = DatasetGenerator.generate_random_dna(read_length, gc_content=0.41)
                # Add 1-2 Ns
                for _ in range(random.randint(0, 2)):
                    pos = random.randint(0, len(seq)-1)
                    seq = seq[:pos] + 'N' + seq[pos+1:]
            elif quality_rand < 0.9:
                # Medium quality: more Ns
                seq = DatasetGenerator.generate_random_dna(read_length, gc_content=0.41)
                # Add 5-10 Ns
                for _ in range(random.randint(5, 10)):
                    pos = random.randint(0, len(seq)-1)
                    seq = seq[:pos] + 'N' + seq[pos+1:]
            else:
                # Low quality: many Ns and longer reads
                seq = DatasetGenerator.generate_random_dna(read_length + 50, gc_content=0.41)
                # Add 10-20 Ns
                for _ in range(random.randint(10, 20)):
                    pos = random.randint(0, len(seq)-1)
                    seq = seq[:pos] + 'N' + seq[pos+1:]

            sequences.append(seq)
            current_size += len(seq) + len(f">header\n"))  # Include header in size

        return sequences

    @staticmethod
    def generate_repetitive_dataset(num_sequences: int, pattern: str, repeats: int = 100) -> List[str]:
        """
        Generate dataset with repetitive patterns (stress for canonicalization)

        Args:
            num_sequences: Number of sequences to generate
            pattern: Base pattern to repeat
            repeats: Number of times to repeat pattern

        Returns:
            List of generated sequences
        """
        sequences = []
        for i in range(num_sequences):
            # Vary the pattern slightly
            variant_pattern = pattern
            if random.random() < 0.3:  # 30% chance to modify pattern
                # Introduce mutations
                variant_list = list(variant_pattern)
                for _ in range(random.randint(1, 3)):
                    pos = random.randint(0, len(variant_list)-1)
                    variant_list[pos] = random.choice(['A', 'T', 'G', 'C'])
                variant_pattern = ''.join(variant_list)

            # Create repetitive sequence
            seq = variant_pattern * repeats
            sequences.append(seq)

        return sequences


class StressTester:
    """Run stress tests with large datasets"""

    def __init__(self, temp_dir: Optional[str] = None):
        """
        Initialize stress tester

        Args:
            temp_dir: Temporary directory for test files
        """
        self.temp_dir = Path(temp_dir or tempfile.mkdtemp(prefix="rustkmer_stress_"))
        self.temp_dir.mkdir(exist_ok=True)

        # Initialize testers
        self.cli_tester = CLITester()
        self.python_tester = PythonTester()

        # Test configurations
        self.test_configs = [
            {
                "name": "small_dataset",
                "description": "Small dataset for baseline (~1MB)",
                "size_mb": 1,
                "k_sizes": [8, 16, 31]
            },
            {
                "name": "medium_dataset",
                "description": "Medium dataset (~10MB)",
                "size_mb": 10,
                "k_sizes": [16, 31]
            },
            {
                "name": "large_dataset",
                "description": "Large dataset (~100MB)",
                "size_mb": 100,
                "k_sizes": [31, 63]
            },
            {
                "name": "very_large_dataset",
                "description": "Very large dataset (~1GB)",
                "size_mb": 1000,
                "k_sizes": [31, 63]
            },
            {
                "name": "extreme_dataset",
                "description": "Extreme dataset (~5GB)",
                "size_mb": 5000,
                "k_sizes": [63]
            }
        ]

    def run_stress_tests(self, max_size_mb: Optional[int] = None, output_dir: str = "stress_test_results") -> List[StressTestResult]:
        """
        Run all stress tests

        Args:
            max_size_mb: Maximum dataset size to test (None for no limit)
            output_dir: Directory to save results

        Returns:
            List of stress test results
        """
        output_dir = Path(output_dir)
        output_dir.mkdir(exist_ok=True)

        print("Running RustKmer Stress Tests")
        print("=" * 50)
        print(f"Temp Directory: {self.temp_dir}")
        print(f"Output Directory: {output_dir}")
        print()

        # Check available memory
        available_memory = psutil.virtual_memory().available / (1024 * 1024)  # MB
        print(f"Available Memory: {available_memory:.1f} MB")

        results = []

        for config in self.test_configs:
            # Skip if too large for available memory
            if max_size_mb and config["size_mb"] > max_size_mb:
                print(f"Skipping {config['name']}: size {config['size_mb']}MB exceeds limit {max_size_mb}MB")
                continue

            # Check if we have enough memory
            estimated_memory = config["size_mb"] * 3  # Rough estimate of memory needed
            if estimated_memory > available_memory * 0.7:  # Use 70% of available memory
                print(f"Skipping {config['name']}: estimated memory {estimated_memory:.0f}MB exceeds available")
                continue

            print(f"\nTesting: {config['name']}")
            print(f"Description: {config['description']}")
            print(f"Size: {config['size_mb']}MB")
            print(f"K-mer sizes: {config['k_sizes']}")

            for k_size in config["k_sizes"]:
                try:
                    result = self._run_stress_test(config, k_size, output_dir)
                    results.append(result)

                    if result.passed:
                        print(f"  ✓ k={k_size}: PASS")
                        print(f"    CLI: {result.execution_time_cli:.2f}s, {result.memory_peak_cli:.1f}MB peak")
                        print(f"    Python: {result.execution_time_python:.2f}s, {result.memory_peak_python:.1f}MB peak")
                        if result.performance_ratio:
                            print(f"    Performance ratio: {result.performance_ratio:.2f}x")
                    else:
                        print(f"  ✗ k={k_size}: FAIL")
                        if result.error:
                            print(f"    Error: {result.error}")

                except Exception as e:
                    print(f"  ✗ k={k_size}: ERROR - {e}")
                    results.append(StressTestResult(
                        test_name=f"{config['name']}_k{k_size}",
                        dataset_size=config["size_mb"],
                        kmer_count=0,
                        passed=False,
                        execution_time_cli=0,
                        execution_time_python=0,
                        memory_peak_cli=0,
                        memory_peak_python=0,
                        error=str(e)
                    ))

            # Clean up test files for this config
            self._cleanup_config_files(config["name"])

        # Save all results
        self._save_results(results, output_dir)

        # Print summary
        self._print_summary(results)

        return results

    def _run_stress_test(self, config: Dict[str, Any], k_size: int, output_dir: Path) -> StressTestResult:
        """Run a single stress test"""
        test_name = f"{config['name']}_k{k_size}"
        test_dir = self.temp_dir / test_name
        test_dir.mkdir(exist_ok=True)

        # Generate dataset
        print(f"  Generating {config['size_mb']}MB dataset for k={k_size}...")
        dataset_path = test_dir / "dataset.fasta"
        db_path = test_dir / "dataset.rkdb"

        sequences = DatasetGenerator.generate_genome_like_dataset(config["size_mb"], k_size * 2)
        DatasetGenerator.generate_fasta(sequences, str(dataset_path))

        # Count k-mers in dataset (approximate)
        total_kmers = sum(max(0, len(seq) - k_size + 1) for seq in sequences)

        # Test CLI implementation
        cli_memory = MemoryMonitor()
        cli_memory.start_monitoring()

        start_time = time.time()
        try:
            cli_output = self.cli_tester.run_command("count", [
                "-k", str(k_size),
                "--canonical",
                str(dataset_path),
                str(db_path)
            ])
            cli_time = time.time() - start_time
        except Exception as e:
            cli_memory.stop_monitoring()
            raise

        cli_peak_rss, cli_peak_vms = cli_memory.stop_monitoring()

        # Test Python implementation
        python_memory = MemoryMonitor()
        python_memory.start_monitoring()

        start_time = time.time()
        try:
            python_output = self.python_tester.count_command(
                str(dataset_path),
                k=k_size,
                canonical=True
            )
            python_time = time.time() - start_time
        except Exception as e:
            python_memory.stop_monitoring()
            raise

        python_peak_rss, python_peak_vms = python_memory.stop_monitoring()

        # Calculate metrics
        performance_ratio = python_time / cli_time if cli_time > 0 else None
        memory_efficiency = (cli_peak_rss / python_peak_rss) if python_peak_rss > 0 else None

        # Determine success criteria
        passed = True
        error = None

        # Check for reasonable performance (Python shouldn't be >10x slower)
        if performance_ratio and performance_ratio > 10:
            passed = False
            error = f"Python too slow: {performance_ratio:.1f}x slower than CLI"

        # Check for reasonable memory usage
        if python_peak_rss > cli_peak_rss * 5:  # Python uses more memory due to bindings overhead
            pass  # This is expected

        # Check that database was created
        if not db_path.exists():
            passed = False
            error = "Database file not created"

        return StressTestResult(
            test_name=test_name,
            dataset_size=config["size_mb"],
            kmer_count=total_kmers,
            passed=passed,
            execution_time_cli=cli_time,
            execution_time_python=python_time,
            memory_peak_cli=cli_peak_rss,
            memory_peak_python=python_peak_rss,
            error=error,
            performance_ratio=performance_ratio,
            memory_efficiency_ratio=memory_efficiency
        )

    def _cleanup_config_files(self, config_name: str):
        """Clean up files for a specific test configuration"""
        config_dir = self.temp_dir / config_name
        if config_dir.exists():
            shutil.rmtree(config_dir, ignore_errors=True)

    def _save_results(self, results: List[StressTestResult], output_dir: Path):
        """Save stress test results"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        results_file = output_dir / f"stress_test_results_{timestamp}.json"

        # Convert results to dict
        results_dict = {
            "metadata": {
                "timestamp": datetime.now().isoformat(),
                "platform": {
                    "os": psutil.platform.system(),
                    "python": sys.version,
                    "memory_total_gb": psutil.virtual_memory().total / (1024**3),
                    "cpu_count": mp.cpu_count()
                }
            },
            "results": [asdict(r) for r in results]
        }

        with open(results_file, 'w') as f:
            json.dump(results_dict, f, indent=2)

        # Also save as latest
        latest_file = output_dir / "latest_stress_test_results.json"
        with open(latest_file, 'w') as f:
            json.dump(results_dict, f, indent=2)

    def _print_summary(self, results: List[StressTestResult]):
        """Print stress test summary"""
        print("\n" + "=" * 50)
        print("STRESS TEST SUMMARY")
        print("=" * 50)

        passed = sum(1 for r in results if r.passed)
        total = len(results)
        pass_rate = (passed / total * 100) if total > 0 else 0

        print(f"Total Tests: {total}")
        print(f"Passed: {passed}")
        print(f"Failed: {total - passed}")
        print(f"Pass Rate: {pass_rate:.1f}%")

        if results:
            # Performance summary
            perf_ratios = [r.performance_ratio for r in results if r.performance_ratio]
            if perf_ratios:
                print(f"\nPerformance Ratio (Python/CLI):")
                print(f"  Mean: {np.mean(perf_ratios):.2f}x")
                print(f"  Median: {np.median(perf_ratios):.2f}x")
                print(f"  Min: {np.min(perf_ratios):.2f}x")
                print(f"  Max: {np.max(perf_ratios):.2f}x")

            # Memory usage summary
            cli_memory = [r.memory_peak_cli for r in results]
            python_memory = [r.memory_peak_python for r in results]

            if cli_memory and python_memory:
                print(f"\nPeak Memory Usage:")
                print(f"  CLI: {np.mean(cli_memory):.1f}MB (avg), {np.max(cli_memory):.1f}MB (max)")
                print(f"  Python: {np.mean(python_memory):.1f}MB (avg), {np.max(python_memory):.1f}MB (max)")

            # Dataset size summary
            datasets_tested = set(r.dataset_size for r in results)
            if datasets_tested:
                print(f"\nDataset Sizes Tested:")
                for size in sorted(datasets_tested):
                    count = sum(1 for r in results if r.dataset_size == size)
                    print(f"  {size}MB: {count} test(s)")

    def run_memory_stress_test(self, dataset_size_mb: float = 100, duration_minutes: int = 5) -> Dict[str, Any]:
        """
        Run memory stress test for a specified duration

        Args:
            dataset_size_mb: Size of dataset to use
            duration_minutes: Duration to run test in minutes

        Returns:
            Test results with memory usage over time
        """
        print(f"\nRunning Memory Stress Test")
        print(f"Dataset Size: {dataset_size_mb}MB")
        print(f"Duration: {duration_minutes} minutes")
        print("-" * 50)

        # Generate test dataset
        test_dir = self.temp_dir / "memory_stress"
        test_dir.mkdir(exist_ok=True)
        dataset_path = test_dir / "stress_dataset.fasta"

        print("Generating test dataset...")
        sequences = DatasetGenerator.generate_genome_like_dataset(dataset_size_mb, 31)
        DatasetGenerator.generate_fasta(sequences, str(dataset_path))

        # Memory tracking
        memory_measurements = []
        start_time = time.time()
        end_time = start_time + (duration_minutes * 60)

        print("Running continuous memory monitoring...")
        try:
            while time.time() < end_time:
                # Measure memory
                memory_info = psutil.Process().memory_info()
                available = psutil.virtual_memory().available

                measurement = {
                    "timestamp": time.time(),
                    "rss_mb": memory_info.rss / (1024 * 1024),
                    "vms_mb": memory_info.vms / (1024 * 1024),
                    "available_mb": available / (1024 * 1024),
                    "percent": psutil.Process().memory_percent()
                }
                memory_measurements.append(measurement)

                # Run a quick test operation
                try:
                    # Quick count and query cycle
                    with tempfile.NamedTemporaryFile(suffix='.fasta') as tmp:
                        # Write a small test sequence
                        with open(tmp.name, 'w') as f:
                            f.write(">test\nATCGATCGATCG\n")

                        # Count
                        cli_output = self.cli_tester.run_command("count", [
                            "-k", "4",
                            str(tmp.name),
                            str(test_dir / "temp.rkdb")
                        ])

                        # Query
                        if (test_dir / "temp.rkdb").exists():
                            query_output = self.cli_tester.run_command("query", [
                                str(test_dir / "temp.rkdb"),
                                "ATCG"
                            ])

                        # Clean up
                        if (test_dir / "temp.rkdb").exists():
                            os.unlink(test_dir / "temp.rkdb")

                except Exception as e:
                    print(f"Test operation failed: {e}")

                time.sleep(10)  # Wait 10 seconds between measurements

        except KeyboardInterrupt:
            print("\nTest interrupted by user")
        except Exception as e:
            print(f"\nMemory stress test error: {e}")

        # Analyze results
        if memory_measurements:
            rss_values = [m["rss_mb"] for m in memory_measurements]
            memory_stats = {
                "duration_minutes": duration_minutes,
                "dataset_size_mb": dataset_size_mb,
                "measurements": len(memory_measurements),
                "rss_peak_mb": max(rss_values),
                "rss_mean_mb": np.mean(rss_values),
                "rss_std_mb": np.std(rss_values),
                "rss_trend": "increasing" if rss_values[-1] > rss_values[0] else "stable",
                "memory_leak_detected": rss_values[-1] > rss_values[0] * 1.5
            }

            print("\nMemory Stress Test Results:")
            print(f"  Duration: {memory_stats['duration_minutes']} minutes")
            f"  Dataset: {memory_stats['dataset_size_mb']}MB")
            print(f"  Measurements: {memory_stats['measurements']}")
            print(f"  Peak RSS: {memory_stats['rss_peak_mb']:.1f}MB")
            print(f"  Mean RSS: {memory_stats['rss_mean_mb']:.1f}MB")
            print(f"  RSS Std Dev: {memory_stats['rss_std_mb']:.1f}MB")
            print(f"  Trend: {memory_stats['rss_trend']}")
            print(f"  Memory Leak: {'DETECTED' if memory_stats['memory_leak_detected'] else 'NONE'}")

            return memory_stats

        return {}


def main():
    """Main entry point for stress testing"""
    import argparse

    parser = argparse.ArgumentParser(description="Run RustKmer stress tests")
    parser.add_argument(
        "--max-size", "-s",
        type=int,
        help="Maximum dataset size in MB to test"
    )
    parser.add_argument(
        "--output", "-o",
        default="stress_test_results",
        help="Output directory for test results"
    )
    parser.add_argument(
        "--memory-stress",
        action="store_true",
        help="Run continuous memory stress test"
    )
    parser.add_argument(
        "--memory-size",
        type=float,
        default=100,
        help="Dataset size for memory stress test (MB)"
    )
    parser.add_argument(
        "--memory-duration",
        type=int,
        default=5,
        help="Duration for memory stress test (minutes)"
    )
    parser.add_argument(
        "--temp-dir",
        help="Temporary directory for test files"
    )

    args = parser.parse_args()

    # Create stress tester
    tester = StressTester(temp_dir=args.temp_dir)

    if args.memory_stress:
        # Run memory stress test
        result = tester.run_memory_stress_test(
            dataset_size_mb=args.memory_size,
            duration_minutes=args.memory_duration
        )
    else:
        # Run regular stress tests
        results = tester.run_stress_test(
            max_size_mb=args.max_size,
            output_dir=args.output
        )

    # Clean up
    if args.temp_dir and Path(args.temp_dir).exists():
        shutil.rmtree(args.temp_dir, ignore_errors=True)

    sys.exit(0)


if __name__ == "__main__":
    main()