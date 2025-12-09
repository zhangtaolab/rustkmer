"""
CLI Compatibility Testing Framework

This module provides utilities to compare Python API outputs with CLI command outputs
to ensure 100% functional parity.
"""

import subprocess
import json
import csv
import io
import os
import tempfile
import gzip
import time
import psutil
from typing import Dict, List, Any, Optional, Tuple, Union
from pathlib import Path
import difflib


class CLICompatibilityTester:
    """Test Python API against CLI commands for compatibility."""

    def __init__(self, cli_path: Optional[str] = None, test_data_base: str = "/Users/forrest/Temp/demodata"):
        """
        Initialize the tester.

        Args:
            cli_path: Path to the rustkmer CLI binary (auto-detect if None)
            test_data_base: Base path for test data
        """
        self.cli_path = cli_path or self._find_cli_path()
        self.test_data_base = Path(test_data_base)
        self.temp_dir = tempfile.mkdtemp(prefix="rustkmer_compat_test_")
        self.default_timeout = 300  # 5 minutes

    def __del__(self):
        """Clean up temporary files."""
        import shutil
        if hasattr(self, 'temp_dir') and os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)

    def run_cli_command(self, args: List[str], input_data: Optional[str] = None) -> Tuple[int, str, str]:
        """
        Run a CLI command and return output.

        Args:
            args: Command arguments
            input_data: Optional input data for stdin

        Returns:
            Tuple of (return_code, stdout, stderr)
        """
        cmd = [self.cli_path] + args

        try:
            result = subprocess.run(
                cmd,
                input=input_data,
                text=True,
                capture_output=True,
                timeout=300  # 5 minute timeout
            )
            return result.returncode, result.stdout, result.stderr
        except subprocess.TimeoutExpired:
            return -1, "", "Command timed out"
        except Exception as e:
            return -1, "", str(e)

    def compare_count_outputs(
        self,
        python_counts: Dict[str, int],
        cli_output: str,
        tolerance: float = 0.0
    ) -> Tuple[bool, Dict[str, Any]]:
        """
        Compare k-mer count outputs between Python and CLI.

        Args:
            python_counts: Python API output dictionary
            cli_output: CLI command output
            tolerance: Allowed difference percentage (0.0 = exact match)

        Returns:
            Tuple of (is_compatible, comparison_details)
        """
        # Parse CLI output
        cli_counts = {}

        # Try to parse as JSON first
        try:
            cli_counts = json.loads(cli_output)
        except json.JSONDecodeError:
            # Try to parse as TSV/CSV
            try:
                reader = csv.reader(io.StringIO(cli_output), delimiter='\t')
                for row in reader:
                    if len(row) >= 2:
                        kmer = row[0].strip()
                        count = int(row[1].strip())
                        cli_counts[kmer] = count
            except:
                # Try to parse as "kmer count" lines
                for line in cli_output.strip().split('\n'):
                    if line:
                        parts = line.strip().split()
                        if len(parts) >= 2:
                            try:
                                kmer = parts[0]
                                count = int(parts[1])
                                cli_counts[kmer] = count
                            except ValueError:
                                continue

        # Compare counts
        details = {
            'python_total': sum(python_counts.values()),
            'cli_total': sum(cli_counts.values()),
            'python_unique': len(python_counts),
            'cli_unique': len(cli_counts),
            'matches': 0,
            'mismatches': [],
            'missing_in_cli': [],
            'extra_in_cli': []
        }

        # Check each k-mer from Python
        for kmer, count in python_counts.items():
            if kmer in cli_counts:
                cli_count = cli_counts[kmer]
                if tolerance == 0.0:
                    # Exact match required
                    if count == cli_count:
                        details['matches'] += 1
                    else:
                        details['mismatches'].append({
                            'kmer': kmer,
                            'python': count,
                            'cli': cli_count,
                            'diff': abs(count - cli_count)
                        })
                else:
                    # Allow tolerance
                    diff_percent = abs(count - cli_count) / max(count, cli_count, 1)
                    if diff_percent <= tolerance:
                        details['matches'] += 1
                    else:
                        details['mismatches'].append({
                            'kmer': kmer,
                            'python': count,
                            'cli': cli_count,
                            'diff_percent': diff_percent * 100
                        })
            else:
                details['missing_in_cli'].append({'kmer': kmer, 'count': count})

        # Check for extra k-mers in CLI
        for kmer, count in cli_counts.items():
            if kmer not in python_counts:
                details['extra_in_cli'].append({'kmer': kmer, 'count': count})

        # Determine compatibility
        is_compatible = (
            len(details['mismatches']) == 0 and
            len(details['missing_in_cli']) == 0 and
            len(details['extra_in_cli']) == 0
        )

        return is_compatible, details

    def compare_query_outputs(
        self,
        python_results: List[Dict[str, Any]],
        cli_output: str
    ) -> Tuple[bool, Dict[str, Any]]:
        """
        Compare query outputs between Python and CLI.

        Args:
            python_results: List of query results from Python
            cli_output: CLI query output

        Returns:
            Tuple of (is_compatible, comparison_details)
        """
        # Parse CLI output
        cli_results = []

        for line in cli_output.strip().split('\n'):
            if line:
                parts = line.strip().split()
                if len(parts) >= 2:
                    try:
                        kmer = parts[0]
                        count = int(parts[1])
                        found = count > 0
                        cli_results.append({
                            'kmer': kmer,
                            'count': count,
                            'found': found
                        })
                    except ValueError:
                        continue

        details = {
            'python_count': len(python_results),
            'cli_count': len(cli_results),
            'matches': 0,
            'mismatches': []
        }

        # Create lookup dictionaries
        python_lookup = {r['kmer']: r for r in python_results}
        cli_lookup = {r['kmer']: r for r in cli_results}

        # Check each k-mer
        all_kmers = set(python_lookup.keys()) | set(cli_lookup.keys())
        for kmer in all_kmers:
            py_result = python_lookup.get(kmer, {'kmer': kmer, 'count': 0, 'found': False})
            cli_result = cli_lookup.get(kmer, {'kmer': kmer, 'count': 0, 'found': False})

            if (py_result['count'] == cli_result['count'] and
                py_result['found'] == cli_result['found']):
                details['matches'] += 1
            else:
                details['mismatches'].append({
                    'kmer': kmer,
                    'python': py_result,
                    'cli': cli_result
                })

        is_compatible = len(details['mismatches']) == 0
        return is_compatible, details

    def compare_stats_outputs(
        self,
        python_stats: Dict[str, Any],
        cli_output: str
    ) -> Tuple[bool, Dict[str, Any]]:
        """
        Compare statistics outputs between Python and CLI.

        Args:
            python_stats: Statistics from Python API
            cli_output: CLI stats output

        Returns:
            Tuple of (is_compatible, comparison_details)
        """
        # Parse CLI stats output
        cli_stats = {}

        try:
            # Try to parse as JSON
            cli_stats = json.loads(cli_output)
        except json.JSONDecodeError:
            # Parse key: value lines
            for line in cli_output.strip().split('\n'):
                if ':' in line:
                    key, value = line.split(':', 1)
                    key = key.strip().lower().replace(' ', '_')
                    value = value.strip()

                    # Try to convert to number
                    try:
                        if '.' in value:
                            value = float(value)
                        else:
                            value = int(value)
                    except ValueError:
                        pass

                    cli_stats[key] = value

        details = {
            'matches': 0,
            'mismatches': [],
            'missing_in_cli': [],
            'extra_in_cli': []
        }

        # Check each stat from Python
        for key, py_value in python_stats.items():
            if key in cli_stats:
                cli_value = cli_stats[key]
                if py_value == cli_value:
                    details['matches'] += 1
                else:
                    details['mismatches'].append({
                        'key': key,
                        'python': py_value,
                        'cli': cli_value
                    })
            else:
                details['missing_in_cli'].append({'key': key, 'value': py_value})

        # Check for extra stats in CLI
        for key, cli_value in cli_stats.items():
            if key not in python_stats:
                details['extra_in_cli'].append({'key': key, 'value': cli_value})

        is_compatible = len(details['mismatches']) == 0
        return is_compatible, details

    def generate_report(self, test_results: List[Dict[str, Any]]) -> str:
        """
        Generate a compatibility test report.

        Args:
            test_results: List of test results

        Returns:
            Formatted report string
        """
        report_lines = [
            "RustKmer Python API - CLI Compatibility Report",
            "=" * 50,
            ""
        ]

        total_tests = len(test_results)
        passed_tests = sum(1 for r in test_results if r['compatible'])

        report_lines.append(f"Total Tests: {total_tests}")
        report_lines.append(f"Passed: {passed_tests}")
        report_lines.append(f"Failed: {total_tests - passed_tests}")
        report_lines.append(f"Success Rate: {passed_tests/total_tests*100:.1f}%")
        report_lines.append("")

        for i, result in enumerate(test_results, 1):
            report_lines.append(f"Test {i}: {result['test_name']}")
            report_lines.append(f"  Status: {'PASS' if result['compatible'] else 'FAIL'}")

            if not result['compatible']:
                report_lines.append(f"  Reason: {result.get('reason', 'Unknown')}")

                # Add mismatch details
                if 'details' in result:
                    details = result['details']
                    if 'mismatches' in details and details['mismatches']:
                        report_lines.append(f"  Mismatches: {len(details['mismatches'])}")
                        for mismatch in details['mismatches'][:5]:  # Show first 5
                            report_lines.append(f"    - {mismatch}")
                        if len(details['mismatches']) > 5:
                            report_lines.append(f"    ... and {len(details['mismatches']) - 5} more")

            report_lines.append("")

        return "\n".join(report_lines)

    def save_report(self, report: str, output_path: str):
        """
        Save the compatibility report to a file.

        Args:
            report: Report string
            output_path: Output file path
        """
        with open(output_path, 'w') as f:
            f.write(report)

    def _find_cli_path(self) -> str:
        """
        Find the rustkmer CLI binary in common locations.

        Returns:
            Path to the CLI binary
        """
        possible_paths = [
            "./target/release/rustkmer",
            "./target/debug/rustkmer",
            "/usr/local/bin/rustkmer",
            "rustkmer"
        ]

        for path in possible_paths:
            try:
                result = subprocess.run(
                    [path, "--version"],
                    capture_output=True,
                    timeout=5
                )
                if result.returncode == 0:
                    return path
            except (subprocess.TimeoutExpired, FileNotFoundError):
                continue

        # Default to "rustkmer" and let the system PATH handle it
        return "rustkmer"

    def validate_test_file(self, file_path: str) -> bool:
        """
        Validate test file exists and is readable.

        Args:
            file_path: Path to test file (relative or absolute)

        Returns:
            True if file exists and is readable
        """
        path = Path(file_path)
        if not path.is_absolute():
            path = self.test_data_base / file_path

        return path.exists() and path.is_file()

    def run_cli_with_real_data(
        self,
        command: List[str],
        input_file: str,
        timeout: Optional[int] = None,
        env: Optional[Dict[str, str]] = None
    ) -> Tuple[int, str, str]:
        """
        Run CLI command with real test data.

        Args:
            command: CLI command arguments (excluding binary)
            input_file: Input file path (relative to test_data_base or absolute)
            timeout: Command timeout in seconds
            env: Environment variables

        Returns:
            Tuple of (return_code, stdout, stderr)

        Raises:
            FileNotFoundError: If test data file not found
        """
        if not self.validate_test_file(input_file):
            raise FileNotFoundError(f"Test data not found: {input_file}")

        # Get full path to input file
        input_path = Path(input_file)
        if not input_path.is_absolute():
            input_path = self.test_data_base / input_file

        cmd = [self.cli_path] + command + [str(input_path)]

        # Set up environment
        process_env = os.environ.copy()
        if env:
            process_env.update(env)

        # Run the command
        try:
            start_time = time.time()
            start_mem = psutil.Process().memory_info().rss

            result = subprocess.run(
                cmd,
                text=True,
                capture_output=True,
                timeout=timeout or self.default_timeout,
                env=process_env
            )

            end_time = time.time()
            end_mem = psutil.Process().memory_info().rss

            # Add timing and memory info to output
            timing_info = {
                "execution_time_seconds": end_time - start_time,
                "memory_usage_mb": (end_mem - start_mem) / 1024 / 1024
            }

            # Add timing info as a JSON comment at the end of output
            if result.stdout:
                result.stdout += f"\n#TIMING: {json.dumps(timing_info)}"

            return result.returncode, result.stdout, result.stderr

        except subprocess.TimeoutExpired:
            return -1, "", f"Command timed out after {timeout or self.default_timeout} seconds"
        except Exception as e:
            return -1, "", str(e)

    def run_cli_benchmark(
        self,
        command: List[str],
        input_file: str,
        runs: int = 5,
        timeout: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Run CLI command multiple times for benchmarking.

        Args:
            command: CLI command arguments
            input_file: Input file path
            runs: Number of runs
            timeout: Timeout per run

        Returns:
            Benchmark results with statistics
        """
        times = []
        memory_usage = []
        return_codes = []

        for i in range(runs):
            ret_code, stdout, stderr = self.run_cli_with_real_data(
                command, input_file, timeout
            )
            return_codes.append(ret_code)

            # Extract timing info from output
            try:
                if "#TIMING:" in stdout:
                    timing_line = stdout.split("#TIMING:")[-1].strip()
                    timing_info = json.loads(timing_line)
                    times.append(timing_info["execution_time_seconds"])
                    memory_usage.append(timing_info["memory_usage_mb"])
            except (json.JSONDecodeError, KeyError):
                # Fallback if timing info not available
                times.append(0)
                memory_usage.append(0)

        # Calculate statistics
        avg_time = sum(times) / len(times) if times else 0
        min_time = min(times) if times else 0
        max_time = max(times) if times else 0
        avg_memory = sum(memory_usage) / len(memory_usage) if memory_usage else 0

        return {
            "runs": runs,
            "return_codes": return_codes,
            "timing": {
                "avg_seconds": avg_time,
                "min_seconds": min_time,
                "max_seconds": max_time,
                "std_dev_seconds": self._calculate_std_dev(times),
                "all_times": times
            },
            "memory": {
                "avg_mb": avg_memory,
                "min_mb": min(memory_usage) if memory_usage else 0,
                "max_mb": max(memory_usage) if memory_usage else 0,
                "std_dev_mb": self._calculate_std_dev(memory_usage),
                "all_memory": memory_usage
            }
        }

    def _calculate_std_dev(self, values: List[float]) -> float:
        """Calculate standard deviation of values."""
        if len(values) < 2:
            return 0
        avg = sum(values) / len(values)
        variance = sum((x - avg) ** 2 for x in values) / len(values)
        return variance ** 0.5

    def compare_count_outputs_real_data(
        self,
        python_total: int,
        python_unique: int,
        cli_output: str
    ) -> Tuple[bool, Dict[str, Any]]:
        """
        Compare count outputs with real data.

        Args:
            python_total: Total k-mers from Python API
            python_unique: Unique k-mers from Python API
            cli_output: CLI command output

        Returns:
            Tuple of (is_compatible, comparison_details)
        """
        # Parse CLI output (expect: "total unique")
        cli_parts = cli_output.strip().split()
        cli_total = int(cli_parts[0]) if cli_parts else 0
        cli_unique = int(cli_parts[1]) if len(cli_parts) > 1 else 0

        details = {
            "python_total": python_total,
            "python_unique": python_unique,
            "cli_total": cli_total,
            "cli_unique": cli_unique,
            "total_match": python_total == cli_total,
            "unique_match": python_unique == cli_unique,
            "compatible": python_total == cli_total and python_unique == cli_unique
        }

        return details["compatible"], details

    def is_gzipped_file(self, file_path: str) -> bool:
        """Check if a file is gzipped."""
        path = Path(file_path)
        return path.suffix == '.gz'

    def read_gzipped_file_first_line(self, file_path: str) -> str:
        """Read first line of a gzipped file."""
        path = Path(file_path)
        if not path.is_absolute():
            path = self.test_data_base / path

        with gzip.open(path, 'rt') as f:
            return f.readline().strip()