#!/usr/bin/env python3
"""
Large Dataset Validator for CLI vs Python API Compatibility Testing

This framework handles large genomic datasets (like the 364MB rice genome) efficiently
without memory issues, providing chunked processing, progress tracking, and resource monitoring.
"""

import os
import sys
import subprocess
import json
import time
import tempfile
import psutil
import threading
from typing import Dict, List, Tuple, Any, Optional, Callable
from dataclasses import dataclass
from pathlib import Path

# Import existing frameworks
sys.path.insert(0, os.path.dirname(__file__))
from compare_databases import DatabaseComparator

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', 'src', 'python'))

try:
    import rustkmer
except ImportError as e:
    print(f"Warning: rustkmer Python module not available: {e}")
    rustkmer = None


@dataclass
class ResourceUsage:
    """Represents system resource usage at a point in time."""
    timestamp: float
    cpu_percent: float
    memory_mb: float
    memory_percent: float
    disk_io_read_mb: float
    disk_io_write_mb: float


@dataclass
class ProcessingProgress:
    """Represents progress during large dataset processing."""
    start_time: float
    current_step: str
    total_steps: int
    completed_steps: int
    current_operation: str
    bytes_processed: int = 0
    total_bytes: int = 0


class LargeDatasetValidator:
    """Validator for large genomic datasets with memory management and progress tracking."""

    def __init__(self, cli_path: str = None, memory_limit_gb: float = 4.0, timeout_minutes: int = 30):
        """
        Initialize the large dataset validator.

        Args:
            cli_path: Path to the rustkmer CLI binary
            memory_limit_gb: Memory limit in GB for processing
            timeout_minutes: Timeout in minutes for operations
        """
        self.cli_path = cli_path or self._find_cli_binary()
        self.memory_limit_bytes = memory_limit_gb * 1024 * 1024 * 1024
        self.timeout_seconds = timeout_minutes * 60
        self.database_comparator = DatabaseComparator(cli_path)
        self.resource_history: List[ResourceUsage] = []
        self.monitoring_active = False
        self.monitoring_thread = None
        self.progress_callback: Optional[Callable[[ProcessingProgress], None]] = None

    def _find_cli_binary(self) -> str:
        """Find the rustkmer CLI binary."""
        candidates = [
            "./target/release/rustkmer",
            "./target/debug/rustkmer",
            "rustkmer",
            "/usr/local/bin/rustkmer"
        ]

        for candidate in candidates:
            if os.path.isfile(candidate):
                return candidate

        raise FileNotFoundError("RustKmer CLI binary not found")

    def _start_resource_monitoring(self):
        """Start monitoring system resources in background thread."""
        self.monitoring_active = True
        self.resource_history.clear()

        def monitor_resources():
            process = psutil.Process()
            io_counters = process.io_counters() if hasattr(process, 'io_counters') else None

            while self.monitoring_active:
                try:
                    memory_info = process.memory_info()
                    cpu_percent = process.cpu_percent()

                    disk_read = 0
                    disk_write = 0
                    if io_counters and hasattr(process, 'io_counters'):
                        current_io = process.io_counters()
                        disk_read = (current_io.read_bytes - io_counters.read_bytes) / (1024 * 1024)
                        disk_write = (current_io.write_bytes - io_counters.write_bytes) / (1024 * 1024)
                        io_counters = current_io

                    usage = ResourceUsage(
                        timestamp=time.time(),
                        cpu_percent=cpu_percent,
                        memory_mb=memory_info.rss / (1024 * 1024),
                        memory_percent=process.memory_percent(),
                        disk_io_read_mb=disk_read,
                        disk_io_write_mb=disk_write
                    )
                    self.resource_history.append(usage)

                    time.sleep(1)  # Monitor every second
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    break

        self.monitoring_thread = threading.Thread(target=monitor_resources, daemon=True)
        self.monitoring_thread.start()

    def _stop_resource_monitoring(self):
        """Stop monitoring system resources."""
        self.monitoring_active = False
        if self.monitoring_thread:
            self.monitoring_thread.join(timeout=2)

    def _check_memory_usage(self) -> bool:
        """Check if current memory usage exceeds limits."""
        current_memory = psutil.Process().memory_info().rss
        return current_memory <= self.memory_limit_bytes

    def _get_file_size(self, file_path: str) -> int:
        """Get file size in bytes."""
        try:
            return os.path.getsize(file_path)
        except OSError:
            return 0

    def _update_progress(self, current_step: str, total_steps: int, completed_steps: int,
                        current_operation: str, bytes_processed: int = 0, total_bytes: int = 0):
        """Update and report progress."""
        if self.progress_callback:
            progress = ProcessingProgress(
                start_time=time.time(),
                current_step=current_step,
                total_steps=total_steps,
                completed_steps=completed_steps,
                current_operation=current_operation,
                bytes_processed=bytes_processed,
                total_bytes=total_bytes
            )
            self.progress_callback(progress)

    def _create_sample_dataset(self, input_file: str, sample_size_mb: float = 10) -> str:
        """
        Create a smaller sample from large dataset for quick testing.

        Args:
            input_file: Path to the input FASTA file
            sample_size_mb: Target sample size in MB

        Returns:
            Path to the sampled file
        """
        target_size_bytes = sample_size_mb * 1024 * 1024
        temp_dir = tempfile.mkdtemp()
        sample_file = os.path.join(temp_dir, f"sample_{os.path.basename(input_file)}")

        try:
            with open(input_file, 'r') as infile, open(sample_file, 'w') as outfile:
                current_size = 0
                buffer = []

                for line in infile:
                    buffer.append(line)
                    current_size += len(line.encode('utf-8'))

                    # Write buffer when we have enough data or at sequence boundaries
                    if current_size >= target_size_bytes or (line.startswith('>') and buffer):
                        outfile.writelines(buffer)
                        if current_size >= target_size_bytes:
                            break
                        buffer = []

                # Write remaining buffer
                if buffer:
                    outfile.writelines(buffer)

            return sample_file

        except Exception as e:
            # Clean up on error
            try:
                os.remove(sample_file)
                os.rmdir(temp_dir)
            except:
                pass
            raise e

    def validate_large_dataset_compatibility(self, input_file: str, kmer_sizes: List[int] = [13, 21],
                                          canonical_modes: List[bool] = [True, False],
                                          use_sample: bool = False) -> Dict[str, Any]:
        """
        Validate compatibility for large dataset across multiple configurations.

        Args:
            input_file: Path to the input FASTA file
            kmer_sizes: List of k-mer sizes to test
            canonical_modes: List of canonical modes to test
            use_sample: If True, use a smaller sample for quick testing

        Returns:
            Comprehensive validation results
        """
        print(f"🧬 Starting large dataset compatibility validation")
        print(f"Input file: {input_file}")
        print(f"File size: {self._get_file_size(input_file) / (1024*1024):.1f} MB")

        # Use sample file if requested
        working_file = input_file
        if use_sample:
            print("Creating sample dataset for quick testing...")
            working_file = self._create_sample_dataset(input_file, sample_size_mb=10)
            print(f"Sample file: {working_file}")
            print(f"Sample size: {self._get_file_size(working_file) / (1024*1024):.1f} MB")

        try:
            # Start resource monitoring
            self._start_resource_monitoring()

            validation_results = {
                "input_file": input_file,
                "working_file": working_file,
                "use_sample": use_sample,
                "file_size_mb": self._get_file_size(working_file) / (1024 * 1024),
                "kmer_sizes": kmer_sizes,
                "canonical_modes": canonical_modes,
                "test_results": [],
                "resource_usage": {},
                "summary": {}
            }

            total_configurations = len(kmer_sizes) * len(canonical_modes)
            completed_configurations = 0

            for kmer_size in kmer_sizes:
                for canonical in canonical_modes:
                    config_name = f"k{kmer_size}_{'canon' if canonical else 'noncanon'}"
                    print(f"\n🔧 Testing configuration: {config_name}")

                    self._update_progress(
                        current_step=config_name,
                        total_steps=total_configurations,
                        completed_steps=completed_configurations,
                        current_operation="Database creation comparison"
                    )

                    # Run compatibility test for this configuration
                    config_result = self._test_single_configuration(
                        working_file, kmer_size, canonical
                    )

                    config_result["configuration"] = config_name
                    config_result["kmer_size"] = kmer_size
                    config_result["canonical"] = canonical
                    validation_results["test_results"].append(config_result)

                    completed_configurations += 1
                    print(f"✅ Configuration {config_name} completed")

                    # Check memory usage
                    if not self._check_memory_usage():
                        print("⚠️  Memory limit approached, stopping further tests")
                        break

                if not self._check_memory_usage():
                    break

            # Generate summary
            validation_results["summary"] = self._generate_summary(validation_results["test_results"])

            return validation_results

        finally:
            # Stop resource monitoring and clean up
            self._stop_resource_monitoring()
            validation_results["resource_usage"] = self._analyze_resource_usage()

            # Clean up sample file if created
            if use_sample and working_file != input_file:
                try:
                    os.remove(working_file)
                    os.rmdir(os.path.dirname(working_file))
                except:
                    pass

    def _test_single_configuration(self, input_file: str, kmer_size: int, canonical: bool) -> Dict[str, Any]:
        """Test a single configuration (kmer_size + canonical mode)."""
        config_start_time = time.time()

        # Create temporary directory for this configuration
        with tempfile.TemporaryDirectory() as temp_dir:
            cli_db = os.path.join(temp_dir, f"cli_k{kmer_size}_{'canon' if canonical else 'noncanon'}.rkdb")
            python_db = os.path.join(temp_dir, f"python_k{kmer_size}_{'canon' if canonical else 'noncanon'}.rkdb")

            result = {
                "kmer_size": kmer_size,
                "canonical": canonical,
                "cli_creation": None,
                "python_creation": None,
                "database_comparison": None,
                "query_validation": None,
                "cross_platform_test": None,
                "duration": 0,
                "status": "unknown"
            }

            try:
                # Step 1: Create databases with both platforms
                print("  📊 Creating databases...")

                # CLI database creation
                cli_start = time.time()
                cli_success, cli_msg = self.database_comparator.create_database_cli(
                    input_file, cli_db, kmer_size, canonical
                )
                cli_duration = time.time() - cli_start

                result["cli_creation"] = {
                    "success": cli_success,
                    "message": cli_msg,
                    "duration": cli_duration
                }

                if not cli_success:
                    result["status"] = "cli_creation_failed"
                    return result

                # Python database creation
                python_start = time.time()
                python_success, python_msg = self.database_comparator.create_database_python(
                    input_file, python_db, kmer_size, canonical
                )
                python_duration = time.time() - python_start

                result["python_creation"] = {
                    "success": python_success,
                    "message": python_msg,
                    "duration": python_duration
                }

                if not python_success:
                    result["status"] = "python_creation_failed"
                    return result

                # Step 2: Compare databases bit-for-bit
                print("  🔍 Comparing databases...")
                result["database_comparison"] = self.database_comparator.compare_files_bitwise(cli_db, python_db)

                # Step 3: Test query compatibility
                print("  🎯 Testing query compatibility...")
                result["query_validation"] = self._test_query_compatibility(cli_db, python_db, kmer_size)

                # Step 4: Test cross-platform database usage
                print("  🔄 Testing cross-platform compatibility...")
                result["cross_platform_test"] = self._test_cross_platform_compatibility(cli_db, python_db)

                # Determine overall status
                if (result["database_comparison"]["identical"] and
                    result["query_validation"]["compatible"] and
                    result["cross_platform_test"]["compatible"]):
                    result["status"] = "passed"
                else:
                    result["status"] = "failed"

            except Exception as e:
                result["status"] = "error"
                result["error"] = str(e)

            result["duration"] = time.time() - config_start_time
            return result

    def _test_query_compatibility(self, cli_db: str, python_db: str, kmer_size: int) -> Dict[str, Any]:
        """Test query compatibility between databases created by different platforms."""
        from query_validator import CrossPlatformQueryValidator

        try:
            validator = CrossPlatformQueryValidator(self.cli_path)

            # Create simple test cases for this k-mer size
            test_cases = validator.create_test_cases(kmer_size)[:10]  # Limit to 10 for speed

            # Test CLI database with both platforms
            cli_results = validator.validate_database_compatibility(cli_db, test_cases)

            # Test Python database with both platforms
            python_results = validator.validate_database_compatibility(python_db, test_cases)

            return {
                "compatible": (
                    cli_results["summary"]["overall_status"] == "PASSED" and
                    python_results["summary"]["overall_status"] == "PASSED"
                ),
                "cli_db_results": cli_results["summary"],
                "python_db_results": python_results["summary"],
                "tests_run": len(test_cases)
            }

        except Exception as e:
            return {
                "compatible": False,
                "error": str(e),
                "tests_run": 0
            }

    def _test_cross_platform_compatibility(self, cli_db: str, python_db: str) -> Dict[str, Any]:
        """Test that CLI can use Python-created databases and vice versa."""
        results = {
            "cli_reads_python_db": False,
            "python_reads_cli_db": False,
            "compatible": False,
            "errors": []
        }

        try:
            # Test CLI reading Python database
            try:
                cmd = [self.cli_path, "info", python_db]
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
                if result.returncode == 0:
                    results["cli_reads_python_db"] = True
                else:
                    results["errors"].append(f"CLI reading Python DB: {result.stderr}")
            except Exception as e:
                results["errors"].append(f"CLI reading Python DB exception: {e}")

            # Test Python reading CLI database
            try:
                if rustkmer is not None:
                    db = rustkmer.Database(cli_db)
                    info = {
                        "kmer_size": db.get_kmer_size(),
                        "canonical": db.get_canonical(),
                        "total_kmers": db.get_total_kmers()
                    }
                    results["python_reads_cli_db"] = True
                    results["python_db_info"] = info
                else:
                    results["errors"].append("Python rustkmer module not available")
            except Exception as e:
                results["errors"].append(f"Python reading CLI DB exception: {e}")

            results["compatible"] = results["cli_reads_python_db"] and results["python_reads_cli_db"]

        except Exception as e:
            results["errors"].append(f"Cross-platform test exception: {e}")

        return results

    def _generate_summary(self, test_results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Generate summary of all test results."""
        if not test_results:
            return {"total_configurations": 0, "passed": 0, "failed": 0, "pass_rate": 0}

        total = len(test_results)
        passed = sum(1 for result in test_results if result.get("status") == "passed")
        failed = total - passed

        # Database compatibility rates
        db_identical = sum(1 for result in test_results
                          if result.get("database_comparison", {}).get("identical", False))

        query_compatible = sum(1 for result in test_results
                             if result.get("query_validation", {}).get("compatible", False))

        cross_platform_compatible = sum(1 for result in test_results
                                      if result.get("cross_platform_test", {}).get("compatible", False))

        return {
            "total_configurations": total,
            "passed": passed,
            "failed": failed,
            "pass_rate_percent": (passed / total * 100) if total > 0 else 0,
            "database_compatibility_rate": (db_identical / total * 100) if total > 0 else 0,
            "query_compatibility_rate": (query_compatible / total * 100) if total > 0 else 0,
            "cross_platform_compatibility_rate": (cross_platform_compatible / total * 100) if total > 0 else 0,
            "overall_status": "PASSED" if failed == 0 else "FAILED"
        }

    def _analyze_resource_usage(self) -> Dict[str, Any]:
        """Analyze collected resource usage data."""
        if not self.resource_history:
            return {"error": "No resource usage data collected"}

        cpu_values = [r.cpu_percent for r in self.resource_history]
        memory_values = [r.memory_mb for r in self.resource_history]
        memory_percent_values = [r.memory_percent for r in self.resource_history]

        return {
            "monitoring_duration_seconds": self.resource_history[-1].timestamp - self.resource_history[0].timestamp if len(self.resource_history) > 1 else 0,
            "avg_cpu_percent": sum(cpu_values) / len(cpu_values) if cpu_values else 0,
            "max_cpu_percent": max(cpu_values) if cpu_values else 0,
            "avg_memory_mb": sum(memory_values) / len(memory_values) if memory_values else 0,
            "max_memory_mb": max(memory_values) if memory_values else 0,
            "avg_memory_percent": sum(memory_percent_values) / len(memory_percent_values) if memory_percent_values else 0,
            "max_memory_percent": max(memory_percent_values) if memory_percent_values else 0,
            "peak_disk_read_mb": sum(r.disk_io_read_mb for r in self.resource_history),
            "peak_disk_write_mb": sum(r.disk_io_write_mb for r in self.resource_history)
        }

    def save_validation_report(self, report: Dict[str, Any], output_path: str = None):
        """Save validation report to file."""
        if output_path is None:
            timestamp = int(time.time())
            output_path = f"tests/007-api-compatibility/test_reports/large_dataset_validation_report_{timestamp}.json"

        os.makedirs(os.path.dirname(output_path), exist_ok=True)

        with open(output_path, 'w') as f:
            json.dump(report, f, indent=2)

        print(f"Large dataset validation report saved to: {output_path}")
        return output_path

    def set_progress_callback(self, callback: Callable[[ProcessingProgress], None]):
        """Set callback function for progress updates."""
        self.progress_callback = callback


def main():
    """Main function for standalone testing."""
    import argparse

    parser = argparse.ArgumentParser(description="Large dataset compatibility validator")
    parser.add_argument("input_file", help="Input FASTA file to validate")
    parser.add_argument("--cli-path", help="Path to rustkmer CLI binary")
    parser.add_argument("--output", help="Output report path")
    parser.add_argument("--kmer-sizes", nargs="+", type=int, default=[13, 21], help="K-mer sizes to test")
    parser.add_argument("--canonical-modes", nargs="+", type=bool, default=[True, False], help="Canonical modes to test")
    parser.add_argument("--sample", action="store_true", help="Use sample dataset for quick testing")
    parser.add_argument("--memory-limit", type=float, default=4.0, help="Memory limit in GB")
    parser.add_argument("--timeout", type=int, default=30, help="Timeout in minutes")

    args = parser.parse_args()

    # Progress callback
    def progress_callback(progress: ProcessingProgress):
        percent = (progress.completed_steps / progress.total_steps) * 100
        print(f"Progress: {progress.completed_steps}/{progress.total_steps} ({percent:.1f}%) - {progress.current_operation}")

    validator = LargeDatasetValidator(
        cli_path=args.cli_path,
        memory_limit_gb=args.memory_limit,
        timeout_minutes=args.timeout
    )
    validator.set_progress_callback(progress_callback)

    # Run validation
    report = validator.validate_large_dataset_compatibility(
        args.input_file,
        kmer_sizes=args.kmer_sizes,
        canonical_modes=args.canonical_modes,
        use_sample=args.sample
    )

    # Save report
    output_path = validator.save_validation_report(report, args.output)

    # Print summary
    summary = report["summary"]
    print(f"\n📊 Large Dataset Validation Summary:")
    print(f"  Total configurations: {summary['total_configurations']}")
    print(f"  Passed: {summary['passed']}")
    print(f"  Failed: {summary['failed']}")
    print(f"  Pass rate: {summary['pass_rate_percent']:.1f}%")
    print(f"  Database compatibility: {summary['database_compatibility_rate']:.1f}%")
    print(f"  Query compatibility: {summary['query_compatibility_rate']:.1f}%")
    print(f"  Cross-platform compatibility: {summary['cross_platform_compatibility_rate']:.1f}%")
    print(f"  Overall status: {summary['overall_status']}")

    if "resource_usage" in report and "max_memory_mb" in report["resource_usage"]:
        resources = report["resource_usage"]
        print(f"\n💾 Resource Usage:")
        print(f"  Peak memory: {resources['max_memory_mb']:.1f} MB")
        print(f"  Average memory: {resources['avg_memory_mb']:.1f} MB")
        print(f"  Peak CPU: {resources['max_cpu_percent']:.1f}%")

    return summary["overall_status"] == "PASSED"


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)