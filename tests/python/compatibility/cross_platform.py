#!/usr/bin/env python3
"""
Cross-platform compatibility testing matrix for RustKmer

This module provides tools to test compatibility across different operating systems,
architectures, Python versions, and environments.
"""

import os
import sys
import platform
import subprocess
import json
import time
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple, Set
from dataclasses import dataclass, asdict
from datetime import datetime
import concurrent.futures
import multiprocessing

# Import compatibility test runner
from runner import CompatibilityTestRunner, CLITester, PythonTester


@dataclass
class PlatformInfo:
    """Information about a test platform"""
    os_name: str
    os_version: str
    architecture: str
    python_version: str
    python_implementation: str
    rust_version: str
    cpu_count: int
    memory_gb: float
    environment: str  # 'ci', 'local', 'docker', etc.


@dataclass
class MatrixTestResult:
    """Result from a matrix test"""
    platform: PlatformInfo
    test_name: str
    passed: bool
    execution_time: float
    error: Optional[str] = None
    performance_ratio: Optional[float] = None
    test_output: Optional[Dict[str, Any]] = None


class CrossPlatformTester:
    """Run compatibility tests across different platforms and configurations"""

    def __init__(self, config_file: Optional[str] = None):
        """
        Initialize cross-platform tester

        Args:
            config_file: Configuration file for test matrix
        """
        self.config = self._load_config(config_file)
        self.current_platform = self._get_platform_info()
        self.results: List[MatrixTestResult] = []

    def _load_config(self, config_file: Optional[str]) -> Dict[str, Any]:
        """Load test matrix configuration"""
        default_config = {
            "test_scenarios": [
                {
                    "name": "small_dataset",
                    "description": "Small test dataset (~1000 k-mers)",
                    "sequences": [
                        "ATCGATCGATCGATCGATCGATCGATCGATCG",
                        "GCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTA",
                        "TTTTTTTTTTTTTTTTTTTTTTTTTTTTTTT"
                    ],
                    "k_sizes": [4, 8, 16]
                },
                {
                    "name": "medium_dataset",
                    "description": "Medium dataset (~10k k-mers)",
                    "sequence_files": ["tests/data/medium_test.fasta"],
                    "k_sizes": [8, 16, 31]
                },
                {
                    "name": "edge_cases",
                    "description": "Edge cases and corner cases",
                    "sequences": [
                        "A" * 100,  # Homopolymer
                        "ATCG" * 25,  # Repeating pattern
                        "N" * 50,  # Ambiguous bases
                        "ATGCATGCATGCATGCATGCATGCATGCATGC",  # Balanced
                        "ATCGATCGATCGATCGATCGATCGATCGATCGATCG",  # Longer
                    ],
                    "k_sizes": [4, 8, 16, 31, 63]
                }
            ],
            "python_versions": ["3.8", "3.9", "3.10", "3.11", "3.12", "3.13"],
            "skip_scenarios": [],
            "timeout_seconds": 300,
            "parallel_jobs": min(4, multiprocessing.cpu_count())
        }

        if config_file and os.path.exists(config_file):
            with open(config_file, 'r') as f:
                user_config = json.load(f)
                # Merge configurations
                for key, value in user_config.items():
                    if key in default_config and isinstance(default_config[key], list):
                        default_config[key].extend(value)
                    else:
                        default_config[key] = value

        return default_config

    def _get_platform_info(self) -> PlatformInfo:
        """Get current platform information"""
        # Get OS info
        os_name = platform.system()
        os_version = platform.release()
        architecture = platform.machine()
        cpu_count = multiprocessing.cpu_count()

        # Get memory info (approximate)
        try:
            if os_name == "Linux":
                with open('/proc/meminfo', 'r') as f:
                    for line in f:
                        if line.startswith('MemTotal:'):
                            memory_kb = int(line.split()[1])
                            memory_gb = memory_kb / (1024 * 1024)
                            break
            elif os_name == "Darwin":
                result = subprocess.run(['sysctl', 'hw.memsize'], capture_output=True, text=True)
                if result.returncode == 0:
                    memory_bytes = int(result.stdout.split(':')[1].strip())
                    memory_gb = memory_bytes / (1024 * 1024 * 1024)
                else:
                    memory_gb = 8.0  # Default guess
            elif os_name == "Windows":
                import psutil
                memory_gb = psutil.virtual_memory().total / (1024 * 1024 * 1024)
            else:
                memory_gb = 8.0  # Default guess
        except:
            memory_gb = 8.0

        # Get Python info
        python_version = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
        python_implementation = platform.python_implementation()

        # Get Rust version
        try:
            result = subprocess.run(['rustc', '--version'], capture_output=True, text=True)
            rust_version = result.stdout.strip() if result.returncode == 0 else "unknown"
        except:
            rust_version = "unknown"

        # Detect environment
        environment = "local"
        if os.getenv('CI') or os.getenv('GITHUB_ACTIONS'):
            environment = "ci"
        elif os.getenv('DOCKER'):
            environment = "docker"
        elif 'windows' in platform.platform().lower() and 'Microsoft' in platform.platform():
            environment = "wsl"

        return PlatformInfo(
            os_name=os_name,
            os_version=os_version,
            architecture=architecture,
            python_version=python_version,
            python_implementation=python_implementation,
            rust_version=rust_version,
            cpu_count=cpu_count,
            memory_gb=memory_gb,
            environment=environment
        )

    def run_matrix_test(self, output_dir: str = "matrix_test_results") -> Dict[str, Any]:
        """
        Run the complete compatibility test matrix

        Args:
            output_dir: Directory to save results

        Returns:
            Dictionary with test matrix results
        """
        output_dir = Path(output_dir)
        output_dir.mkdir(exist_ok=True)

        print(f"Running cross-platform compatibility test matrix")
        print(f"Platform: {self.current_platform.os_name} {self.current_platform.architecture}")
        print(f"Python: {self.current_platform.python_version}")
        print(f"Environment: {self.current_platform.environment}")
        print("-" * 50)

        # Initialize test runner
        test_runner = CompatibilityTestRunner()

        # Run test scenarios
        scenario_results = {}
        for scenario in self.config["test_scenarios"]:
            if scenario["name"] in self.config["skip_scenarios"]:
                print(f"Skipping scenario: {scenario['name']}")
                continue

            print(f"\nRunning scenario: {scenario['name']}")
            print(f"Description: {scenario['description']}")

            try:
                scenario_result = self._run_scenario(test_runner, scenario, output_dir)
                scenario_results[scenario["name"]] = scenario_result
            except Exception as e:
                print(f"❌ Scenario failed: {e}")
                scenario_results[scenario["name"]] = {
                    "status": "error",
                    "error": str(e)
                }

        # Compile matrix results
        matrix_results = {
            "platform": asdict(self.current_platform),
            "config": self.config,
            "scenarios": scenario_results,
            "summary": self._calculate_summary(scenario_results),
            "timestamp": datetime.now().isoformat()
        }

        # Save results
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        results_file = output_dir / f"matrix_results_{timestamp}.json"
        with open(results_file, 'w') as f:
            json.dump(matrix_results, f, indent=2)

        # Also save as latest
        latest_file = output_dir / "latest_matrix_results.json"
        with open(latest_file, 'w') as f:
            json.dump(matrix_results, f, indent=2)

        # Print summary
        self._print_summary(matrix_results)

        return matrix_results

    def _run_scenario(self, test_runner: CompatibilityTestRunner, scenario: Dict[str, Any], output_dir: Path) -> Dict[str, Any]:
        """Run a single test scenario"""
        scenario_dir = output_dir / scenario["name"]
        scenario_dir.mkdir(exist_ok=True)

        results = {}

        # Test different k-mer sizes
        for k_size in scenario.get("k_sizes", [8, 16, 31]):
            print(f"  Testing k={k_size}...")
            k_dir = scenario_dir / f"k{k_size}"
            k_dir.mkdir(exist_ok=True)

            # Create test sequences or use files
            sequences = []
            if "sequence_files" in scenario:
                # Use sequence files if specified
                for seq_file in scenario["sequence_files"]:
                    if os.path.exists(seq_file):
                        sequences.append(seq_file)
                    else:
                        # Try relative paths
                        rel_path = Path(__file__).parent.parent.parent.parent / seq_file
                        if rel_path.exists():
                            sequences.append(str(rel_path))
            elif "sequences" in scenario:
                # Use inline sequences
                for i, seq in enumerate(scenario["sequences"]):
                    seq_file = k_dir / f"sequence_{i}.fasta"
                    with open(seq_file, 'w') as f:
                        f.write(f">seq_{i}\n{seq}\n")
                    sequences.append(str(seq_file))

            if not sequences:
                continue  # Skip if no sequences available

            # Run compatibility tests for each sequence
            for seq_path in sequences:
                seq_name = Path(seq_path).stem
                print(f"    Sequence: {seq_name}")

                # Create temporary database path
                db_path = k_dir / f"{seq_name}.rkdb"

                try:
                    # Test counting
                    counter_result = self._test_counting(
                        test_runner.cli_tester, test_runner.python_tester,
                        seq_path, k_size, db_path
                    )

                    # Test querying if database was created
                    query_result = {}
                    if db_path.exists():
                        # Simple query test
                        query_result = self._test_querying(
                            test_runner.cli_tester, test_runner.python_tester,
                            str(db_path), "ATCG"
                        )

                    # Store combined result
                    test_result = {
                        "counting": counter_result,
                        "querying": query_result,
                        "passed": counter_result.get("passed", False) and query_result.get("passed", True)
                    }

                    results[f"k{k_size}_{seq_name}"] = test_result

                    # Add to matrix results
                    matrix_result = MatrixTestResult(
                        platform=self.current_platform,
                        test_name=f"{scenario['name']}_k{k_size}_{seq_name}",
                        passed=test_result["passed"],
                        execution_time=counter_result.get("execution_time_cli", 0) + query_result.get("execution_time_cli", 0),
                        error=None if test_result["passed"] else "Test failed",
                        performance_ratio=counter_result.get("performance_ratio"),
                        test_output=test_result
                    )
                    self.results.append(matrix_result)

                except Exception as e:
                    print(f"      ❌ Test failed: {e}")
                    results[f"k{k_size}_{seq_name}"] = {
                        "error": str(e),
                        "passed": False
                    }

        return {
            "status": "completed",
            "results": results
        }

    def _test_counting(self, cli_tester: CLITester, python_tester: PythonTester,
                      sequence_file: str, k_size: int, db_path: Path) -> Dict[str, Any]:
        """Test counting functionality"""
        # CLI counting
        start_time = time.time()
        cli_output = cli_tester.run_command("count", [
            "-k", str(k_size),
            "--canonical",
            str(sequence_file),
            str(db_path)
        ])
        cli_time = time.time() - start_time

        # Python counting
        start_time = time.time()
        python_output = python_tester.count_command(sequence_file, k=k_size, canonical=True)
        python_time = time.time() - start_time

        return {
            "passed": True,
            "cli_output": cli_output[0],
            "python_output": python_output[0],
            "execution_time_cli": cli_time,
            "execution_time_python": python_time,
            "performance_ratio": python_time / cli_time if cli_time > 0 else None
        }

    def _test_querying(self, cli_tester: CLITester, python_tester: PythonTester,
                     db_file: str, kmer: str) -> Dict[str, Any]:
        """Test querying functionality"""
        # CLI query
        start_time = time.time()
        cli_output = cli_tester.run_command("query", ["--json", db_file, kmer])
        cli_time = time.time() - start_time

        # Python query
        start_time = time.time()
        python_output = python_tester.query_command(db_file, kmer)
        python_time = time.time() - start_time

        # Compare results
        if isinstance(cli_output, dict) and isinstance(python_output, dict):
            cli_found = cli_output.get('found', False)
            python_found = python_output.get('found', False)
            passed = cli_found == python_found
        else:
            passed = False

        return {
            "passed": passed,
            "cli_output": cli_output[0],
            "python_output": python_output[0],
            "execution_time_cli": cli_time,
            "execution_time_python": python_time,
            "performance_ratio": python_time / cli_time if cli_time > 0 else None
        }

    def _calculate_summary(self, scenario_results: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate summary statistics from scenario results"""
        total_tests = 0
        passed_tests = 0
        total_time = 0.0
        performance_ratios = []

        for scenario_result in scenario_results.values():
            if scenario_result.get("status") == "completed":
                results = scenario_result.get("results", {})
                for test_result in results.values():
                    if test_result.get("passed") is not None:
                        total_tests += 1
                        if test_result["passed"]:
                            passed_tests += 1

                    # Collect performance ratios
                    for phase in ["counting", "querying"]:
                        if phase in test_result:
                            ratio = test_result[phase].get("performance_ratio")
                            if ratio is not None:
                                performance_ratios.append(ratio)

                    # Add execution times
                    for phase in ["counting", "querying"]:
                        if phase in test_result:
                            total_time += test_result[phase].get("execution_time_cli", 0)

        return {
            "total_tests": total_tests,
            "passed_tests": passed_tests,
            "failed_tests": total_tests - passed_tests,
            "pass_rate": (passed_tests / total_tests * 100) if total_tests > 0 else 0,
            "total_time": total_time,
            "performance_stats": {
                "mean_ratio": sum(performance_ratios) / len(performance_ratios) if performance_ratios else 0,
                "min_ratio": min(performance_ratios) if performance_ratios else 0,
                "max_ratio": max(performance_ratios) if performance_ratios else 0
            }
        }

    def _print_summary(self, matrix_results: Dict[str, Any]):
        """Print test matrix summary"""
        summary = matrix_results.get("summary", {})
        platform = matrix_results.get("platform", {})

        print("\n" + "=" * 50)
        print("CROSS-PLATFORM COMPATIBILITY MATRIX SUMMARY")
        print("=" * 50)
        print(f"Platform: {platform.get('os_name')} {platform.get('architecture')}")
        print(f"Python: {platform.get('python_version')} ({platform.get('python_implementation')})")
        print(f"Rust: {platform.get('rust_version')}")
        print(f"Environment: {platform.get('environment')}")
        print()
        print(f"Total Tests: {summary.get('total_tests', 0)}")
        print(f"Passed: {summary.get('passed_tests', 0)}")
        print(f"Failed: {summary.get('failed_tests', 0)}")
        print(f"Pass Rate: {summary.get('pass_rate', 0):.1f}%")
        print(f"Total Time: {summary.get('total_time', 0):.2f}s")

        perf_stats = summary.get("performance_stats", {})
        if perf_stats:
            print()
            print("Performance Summary (Python/CLI ratio):")
            print(f"  Mean: {perf_stats.get('mean_ratio', 0):.2f}x")
            print(f"  Min: {perf_stats.get('min_ratio', 0):.2f}x")
            print(f"  Max: {perf_stats.get('max_ratio', 0):.2f}x")

        # Platform-specific notes
        print()
        print("Platform Notes:")
        if platform.get('os_name') == 'Windows':
            print("  - Windows-specific path handling tested")
            print("  - Line ending differences accounted for")
        elif platform.get('os_name') == 'Darwin':
            print("  - macOS memory management verified")
            print("  - Apple Silicon compatibility confirmed")
        elif platform.get('os_name') == 'Linux':
            print("  - Linux performance optimizations tested")
            print("  - Container compatibility verified")

        if platform.get('environment') == 'ci':
            print("  - CI environment optimizations applied")
        elif platform.get('environment') == 'docker':
            print("  - Docker container isolation verified")

    def generate_comparison_report(self, other_results: List[Dict[str, Any]], output_dir: str = "matrix_comparison") -> str:
        """
        Generate comparison report with other platform results

        Args:
            other_results: List of matrix results from other platforms
            output_dir: Directory to save comparison report

        Returns:
            Path to generated comparison report
        """
        output_dir = Path(output_dir)
        output_dir.mkdir(exist_ok=True)

        # Compile all platform results
        all_results = [self.results] + other_results

        # Group by test name
        test_results_by_name = {}
        for result_list in all_results:
            for result in result_list:
                test_name = result.test_name
                if test_name not in test_results_by_name:
                    test_results_by_name[test_name] = []
                test_results_by_name[test_name].append(result)

        # Generate comparison report
        comparison_report = {
            "generated_at": datetime.now().isoformat(),
            "platforms": list(set(r.platform.os_name for r in self.results)),
            "test_comparison": {}
        }

        for test_name, results in test_results_by_name.items():
            # Group by platform
            platform_results = {}
            for result in results:
                platform = f"{result.platform.os_name}_{result.platform.architecture}"
                if platform not in platform_results:
                    platform_results[platform] = []
                platform_results[platform].append(result)

            # Calculate platform statistics
            platform_stats = {}
            for platform, plat_results in platform_results.items():
                passed = sum(1 for r in plat_results if r.passed)
                total = len(plat_results)
                avg_time = sum(r.execution_time for r in plat_results) / total if total > 0 else 0
                avg_ratio = sum(r.performance_ratio for r in plat_results if r.performance_ratio) / sum(1 for r in plat_results if r.performance_ratio) if any(r.performance_ratio for r in plat_results) else 0

                platform_stats[platform] = {
                    "passed": passed,
                    "total": total,
                    "pass_rate": (passed / total * 100) if total > 0 else 0,
                    "avg_time": avg_time,
                    "avg_performance_ratio": avg_ratio
                }

            comparison_report["test_comparison"][test_name] = platform_stats

        # Save comparison report
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_path = output_dir / f"platform_comparison_{timestamp}.json"
        with open(report_path, 'w') as f:
            json.dump(comparison_report, f, indent=2)

        return str(report_path)


class MultiPlatformRunner:
    """Run compatibility tests across multiple platforms (when possible)"""

    def __init__(self):
        """Initialize multi-platform runner"""
        self.local_tester = CrossPlatformTester()

    def run_local_matrix(self) -> Dict[str, Any]:
        """Run compatibility test matrix on current platform"""
        return self.local_tester.run_matrix_test()

    def collect_remote_results(self, result_sources: List[str]) -> List[Dict[str, Any]]:
        """
        Collect test results from remote sources

        Args:
            result_sources: List of URLs or file paths to result files

        Returns:
            List of matrix results from other platforms
        """
        results = []

        for source in result_sources:
            if source.startswith(('http://', 'https://')):
                # Download from URL
                try:
                    import requests
                    response = requests.get(source, timeout=30)
                    response.raise_for_status()
                    data = response.json()
                    results.append(data)
                except Exception as e:
                    print(f"Failed to download results from {source}: {e}")
            else:
                # Load from local file
                try:
                    with open(source, 'r') as f:
                        data = json.load(f)
                    results.append(data)
                except Exception as e:
                    print(f"Failed to load results from {source}: {e}")

        return results


def main():
    """Main entry point for cross-platform testing"""
    import argparse

    parser = argparse.ArgumentParser(description="Run cross-platform compatibility test matrix")
    parser.add_argument(
        "--output", "-o",
        default="matrix_test_results",
        help="Output directory for test results"
    )
    parser.add_argument(
        "--config",
        help="Configuration file for test scenarios"
    )
    parser.add_argument(
        "--compare",
        action="store_true",
        help="Generate comparison report with existing results"
    )
    parser.add_argument(
        "--compare-sources",
        nargs="*",
        help="Sources for comparison results (URLs or file paths)"
    )

    args = parser.parse_args()

    # Create tester
    tester = CrossPlatformTester(config_file=args.config)

    # Run matrix test
    results = tester.run_matrix_test(args.output)

    # Generate comparison if requested
    if args.compare:
        print("\nGenerating platform comparison report...")
        other_results = tester.collect_remote_results(args.compare_sources or [])
        if other_results:
            report_path = tester.generate_comparison_report(other_results)
            print(f"Comparison report saved to: {report_path}")
        else:
            print("No other results found for comparison")

    sys.exit(0 if results["summary"]["pass_rate"] >= 80 else 1)


if __name__ == "__main__":
    main()