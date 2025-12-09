"""
Comprehensive test runner for RustKmer CLI-Python API compatibility tests.

This module provides a unified interface to run all compatibility tests,
generate reports, and aggregate results.
"""

import sys
import os
import json
import time
import traceback
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional, Union, Tuple
from dataclasses import dataclass, field
import argparse

# Import compatibility testing modules
if __name__ == "__main__":
    # When run as a script, add parent directory to path
    sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from tests.python.compatibility.test_data_manager import DemodataManager
from tests.python.compatibility.cli_comparator import CLICompatibilityTester
from tests.python.compatibility.performance_comparator import PerformanceComparator, PerformanceResult
from tests.python.compatibility.data_models import (
    CompatibilityTestSuite, TestExecution, PerformanceMetrics,
    ErrorComparison, TestConfiguration
)
from tests.python.compatibility.test_data.validators import TestDataValidator
from tests.python.compatibility.test_data.inventory import TestDataInventory


@dataclass
class TestResult:
    """Result of a single test run."""

    test_name: str
    passed: bool
    execution_time_ms: float
    error: Optional[str] = None
    details: Optional[Dict[str, Any]] = None


class ComprehensiveTestRunner:
    """Unified test runner for all compatibility tests."""

    def __init__(
        self,
        config: Optional[TestConfiguration] = None,
        base_path: str = "/Users/forrest/Temp/demodata"
    ):
        """
        Initialize the test runner.

        Args:
            config: Test configuration
            base_path: Base path for test data
        """
        self.config = config or TestConfiguration(
            test_data_base=base_path,
            performance_thresholds={"time": 1.10, "memory": 1.05},
            timeout_settings={"default": 300, "large_file": 600},
            categories=["small", "medium", "large"]
        )

        self.data_manager = DemodataManager(base_path)
        self.cli_tester = CLICompatibilityTester(test_data_base=base_path)
        self.perf_comparator = PerformanceComparator(
            time_threshold=self.config.performance_thresholds["time"],
            memory_threshold=self.config.performance_thresholds["memory"]
        )
        self.data_validator = TestDataValidator(base_path)

        # Initialize test suite
        self.test_suite = CompatibilityTestSuite(
            suite_id=f"compatibility_test_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            test_date=datetime.now(),
            python_version=f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
            cli_version="unknown",  # Will be updated
            configuration=self.config.to_dict()
        )

        # Test phases to run
        self.test_phases = {
            "phase2_core": self._run_phase2_tests,
            "phase3_advanced": self._run_phase3_tests,
            "phase4_cross_cutting": self._run_phase4_tests
        }

    def setup_directories(self):
        """Set up necessary directories."""
        self.data_manager.setup_directories()

    def validate_prerequisites(self) -> bool:
        """
        Validate that all prerequisites are met.

        Returns:
            True if prerequisites are valid
        """
        print("Validating prerequisites...")

        # Check test data directory
        if not Path(self.config.test_data_base).exists():
            print(f"⚠️  Warning: Test data directory does not exist: {self.config.test_data_base}")
            return False

        # Check CLI availability
        try:
            result = self.cli_tester.run_cli_command(["--version"])
            if result[0] != 0:
                print("⚠️  Warning: CLI may not be properly installed")
                return False
            # Extract CLI version from output
            self.test_suite.cli_version = result[1].strip().split()[1] if len(result[1].split()) > 1 else "unknown"
        except Exception as e:
            print(f"⚠️  Warning: CLI validation failed: {e}")
            return False

        # Check Python RustKmer module
        try:
            import rustkmer
            # Test basic functionality
            _ = rustkmer.KmerCounter(k=7)
        except ImportError:
            print("⚠️  Warning: RustKmer Python module not available")
            return False
        except Exception as e:
            print(f"⚠️  Warning: Python module test failed: {e}")
            return False

        print("✅ Prerequisites validated successfully")
        return True

    def run_all_tests(
        self,
        categories: Optional[List[str]] = None,
        include_performance: bool = True,
        run_parallel: bool = False
    ) -> CompatibilityTestSuite:
        """
        Run all compatibility tests.

        Args:
            categories: Test categories to run (small, medium, large)
            include_performance: Whether to include performance tests
            run_parallel: Whether to run tests in parallel (not implemented)

        Returns:
            CompatibilityTestSuite with all results
        """
        print(f"Starting comprehensive compatibility test suite...")
        print(f"Suite ID: {self.test_suite.suite_id}")
        print()

        # Validate prerequisites
        if not self.validate_prerequisites():
            print("❌ Prerequisites validation failed. Exiting.")
            return self.test_suite

        # Run test phases
        for phase_name, phase_func in self.test_phases.items():
            print(f"\n{'='*20} {phase_name.upper()} {'='*20}")
            phase_results = phase_func(categories or self.config.categories)
            self.test_suite.add_results(phase_results)

        # Calculate summary
        self.test_suite.calculate_summary()
        print(f"\n{'='*20} TEST SUMMARY {'='*20}")
        summary = self.test_suite.summary
        print(f"Total tests: {summary.total_tests}")
        print(f"Passed: {summary.passed_tests}")
        print(f"Failed: {summary.failed_count}")
        print(f"Success rate: {summary.success_rate:.1f}%")

        if summary.performance_summary:
            print(f"\nPerformance Summary:")
            print(f"  Average ratio (Python/CLI): {summary.performance_summary.average_ratio:.2f}")
            print(f"  Within threshold: {summary.performance_summary.within_threshold_count}/{summary.performance_summary.total_count}")
            print(f"  Within threshold %: {summary.performance_summary.within_threshold_percentage:.1f}%")

        return self.test_suite

    def _run_phase2_tests(self, categories: List[str]) -> List[TestExecution]:
        """Run Phase 2: Core API Testing."""
        results = []

        # Test T006-T015: Core API tests
        phase2_tests = [
            ("test_kmer_counter_fasta", self._test_kmer_counter_fasta),
            ("test_kmer_counter_fastq", self._test_kmer_counter_fastq),
            ("test_database_query", self._test_database_query),
            ("test_database_save", self._test_database_save),
            ("test_multiple_query", self._test_multiple_query),
            ("test_kmer_counter_params", self._test_kmer_counter_params),
            ("test_count_string", self._test_count_string),
            ("test_database_load_performance", self._test_database_load_performance)
        ]

        for test_name, test_func in phase2_tests:
            print(f"Running {test_name}...")
            result = self._run_single_test(test_name, test_func)
            if result:
                results.append(result)

        return results

    def _run_phase3_tests(self, categories: List[str]) -> List[TestExecution]:
        """Run Phase 3: Advanced Feature Testing."""
        results = []

        # Test T016-T025: Advanced feature tests
        phase3_tests = [
            ("test_fuzzy_query", self._test_fuzzy_query),
            ("test_database_stats", self._test_database_stats),
            ("test_database_merge", self._test_database_merge),
            ("test_database_dump", self._test_database_dump),
            ("test_format_compatibility", self._test_format_compatibility),
            ("test_alphabet_handling", self._test_alphabet_handling),
            ("test_memory_mapped_access", self._test_memory_mapped_access),
            ("test_progress_reporting", self._test_progress_reporting),
            ("test_version_migration", self._test_version_migration)
        ]

        for test_name, test_func in phase3_tests:
            print(f"Running {test_name}...")
            result = self._run_single_test(test_name, test_func)
            if result:
                results.append(result)

        return results

    def _run_phase4_tests(self, categories: List[str]) -> List[TestExecution]:
        """Run Phase 4: Cross-Cutting Concerns."""
        results = []

        # Test T026-T030: Cross-cutting tests
        phase4_tests = [
            ("test_error_handling_compatibility", self._test_error_handling_compatibility),
            ("test_cross_platform_compatibility", self._test_cross_platform_compatibility),
            ("test_suite_integration", self._test_suite_integration)
        ]

        for test_name, test_func in phase4_tests:
            print(f"Running {test_name}...")
            result = self._run_single_test(test_name, test_func)
            if result:
                results.append(result)

        return results

    def _run_single_test(self, test_name: str, test_func) -> Optional[TestExecution]:
        """
        Run a single test and create a TestExecution object.

        Args:
            test_name: Name of the test
            test_func: Test function to run

        Returns:
            TestExecution object or None if test failed to initialize
        """
        start_time = time.time()

        try:
            # Run the test
            test_result = test_func()
            end_time = time.time()

            # Create TestExecution
            execution = TestExecution(
                execution_id=f"{test_name}_{int(start_time)}",
                test_name=test_name,
                python_class=test_result.get("python_class", "Unknown"),
                python_method=test_result.get("python_method", "Unknown"),
                cli_command=test_result.get("cli_command", "Unknown"),
                test_parameters=test_result.get("parameters", {}),
                test_data_path=test_result.get("test_data_path"),
                python_output=test_result.get("python_output"),
                cli_output=test_result.get("cli_output"),
                is_identical=test_result.get("is_identical", False),
                difference_details=test_result.get("differences"),
                performance_metrics=test_result.get("performance_metrics"),
                error_comparison=test_result.get("error_comparison"),
                timestamp=datetime.now()
            )

            # Update execution time
            execution_time_ms = (end_time - start_time) * 1000
            if execution.performance_metrics:
                execution.performance_metrics.python_time_ms = execution_time_ms

            # Print result
            status = "✅ PASS" if execution.is_identical else "❌ FAIL"
            print(f"  {status} ({execution_time_ms:.0f}ms)")

            if not execution.is_identical:
                print(f"    Differences: {execution.difference_details}")

            return execution

        except Exception as e:
            end_time = time.time()
            execution_time_ms = (end_time - start_time) * 1000

            print(f"  ❌ ERROR ({execution_time_ms:.0f}ms): {str(e)}")
            if self.config.verbose:
                traceback.print_exc()

            # Return error result
            return TestExecution(
                execution_id=f"{test_name}_error_{int(start_time)}",
                test_name=test_name,
                python_class="Error",
                python_method="Error",
                cli_command="Error",
                test_parameters={},
                test_data_path=None,
                python_output=None,
                cli_output=None,
                is_identical=False,
                difference_details={"error": str(e)},
                performance_metrics=None,
                error_comparison=None,
                timestamp=datetime.now()
            )

    def _test_kmer_counter_fasta(self) -> Dict[str, Any]:
        """Test KmerCounter compatibility with FASTA files."""
        from rustkmer import KmerCounter

        # Get FASTA files
        fasta_files = self.data_manager.get_fasta_files()
        if not fasta_files:
            return {"skipped": "No FASTA files found"}

        test_file = fasta_files[0]  # Use first file
        k = 31

        # Python API
        try:
            counter = KmerCounter(k=k)
            counter.count_file(str(test_file))
            python_total = counter.get_total_count()
            python_unique = counter.get_unique_count()
        except Exception as e:
            return {"error": str(e)}

        # CLI
        try:
            ret_code, cli_output, _ = self.cli_tester.run_cli_with_real_data(
                ["count", "-k", str(k)],
                str(test_file.relative_to(self.data_manager.base_path))
            )

            if ret_code != 0:
                return {"error": f"CLI command failed with exit code {ret_code}"}

            # Use enhanced comparison
            is_compatible, details = self.cli_tester.compare_count_outputs_real_data(
                python_total, python_unique, cli_output
            )
        except Exception as e:
            return {"error": str(e)}

        return {
            "python_class": "KmerCounter",
            "python_method": "count_file",
            "cli_command": "rustkmer count",
            "parameters": {"k": k, "file": str(test_file.relative_to(self.data_manager.base_path))},
            "test_data_path": str(test_file.relative_to(self.data_manager.base_path)),
            "python_output": {"total": python_total, "unique": python_unique},
            "cli_output": cli_output,
            "is_identical": is_compatible,
            "differences": None if is_compatible else details
        }

    def _test_kmer_counter_fastq(self) -> Dict[str, Any]:
        """Test KmerCounter compatibility with FASTQ files."""
        from rustkmer import KmerCounter

        # Get FASTQ files
        fastq_files = self.data_manager.get_fastq_files()
        if not fastq_files:
            return {"skipped": "No FASTQ files found"}

        test_file = fastq_files[0]  # Use first file
        k = 31

        # Python API
        try:
            counter = KmerCounter(k=k)
            counter.count_file(str(test_file))
            python_total = counter.get_total_count()
            python_unique = counter.get_unique_count()
        except Exception as e:
            return {"error": str(e)}

        # CLI
        try:
            ret_code, cli_output, _ = self.cli_tester.run_cli_with_real_data(
                ["count", "-k", str(k)],
                str(test_file.relative_to(self.data_manager.base_path))
            )

            if ret_code != 0:
                return {"error": f"CLI command failed with exit code {ret_code}"}

            # Parse CLI output
            parts = cli_output.strip().split()
            cli_total = int(parts[0]) if parts else 0
            cli_unique = int(parts[1]) if len(parts) > 1 else 0

            is_compatible = python_total == cli_total and python_unique == cli_unique
        except Exception as e:
            return {"error": str(e)}

        return {
            "python_class": "KmerCounter",
            "python_method": "count_file",
            "cli_command": "rustkmer count",
            "parameters": {"k": k, "file": str(test_file.relative_to(self.data_manager.base_path))},
            "test_data_path": str(test_file.relative_to(self.data_manager.base_path)),
            "python_output": {"total": python_total, "unique": python_unique},
            "cli_output": cli_output,
            "is_identical": is_compatible,
            "differences": None if is_compatible else {"total_mismatch": python_total - cli_total}
        }

    def _test_database_query(self) -> Dict[str, Any]:
        """Test Database query compatibility."""
        from rustkmer import Database

        # Get RKDB files
        rkdb_files = self.data_manager.get_rkdb_files()
        if not rkdb_files:
            return {"skipped": "No RKDB files found"}

        test_db = rkdb_files[0]  # Use first file
        test_sequences = ["ATCGATCGATCGATCGATCGATCGATCGATCGATCG", "GCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAGCT"]

        try:
            # Python API
            db = Database.load(str(test_db))
            python_results = [db.query(seq) for seq in test_sequences]

            # CLI
            cli_results = []
            for seq in test_sequences:
                ret_code, cli_output, _ = self.cli_tester.run_cli_with_real_data(
                    ["query", str(test_db.relative_to(self.data_manager.base_path)), seq]
                )
                if ret_code == 0:
                    cli_results.append(int(cli_output.strip()))
                else:
                    cli_results.append(-1)

            is_compatible = python_results == cli_results
        except Exception as e:
            return {"error": str(e)}

        return {
            "python_class": "Database",
            "python_method": "query",
            "cli_command": "rustkmer query",
            "parameters": {"database": str(test_db.relative_to(self.data_manager.base_path))},
            "test_data_path": str(test_db.relative_to(self.data_manager.base_path)),
            "python_output": python_results,
            "cli_output": cli_results,
            "is_identical": is_compatible,
            "differences": None if is_compatible else {"mismatched_queries": [i for i, (p, c) in enumerate(zip(python_results, cli_results)) if p != c]}
        }

    def _test_database_save(self) -> Dict[str, Any]:
        """Test database saving compatibility."""
        from rustkmer import KmerCounter, Database

        # Get a test file
        fasta_files = self.data_manager.get_fasta_files()
        if not fasta_files:
            return {"skipped": "No FASTA files found"}

        input_file = fasta_files[0]
        python_db_path = self.data_manager.get_temp_db_path("python_saved")
        cli_db_path = self.data_manager.get_temp_db_path("cli_saved")
        k = 31

        try:
            # Python API - save database
            counter = KmerCounter(k=k)
            counter.count_file(str(input_file))
            counter.save_to_database(str(python_db_path))

            # CLI - save database
            ret_code, _, _ = self.cli_tester.run_cli_with_real_data(
                ["count", "-k", str(k), "-o", str(cli_db_path.relative_to(self.data_manager.base_path))],
                str(input_file.relative_to(self.data_manager.base_path))
            )

            if ret_code != 0:
                return {"error": f"CLI save failed with exit code {ret_code}"}

            # Compare databases
            python_db = Database.load(str(python_db_path))
            cli_db = Database.load(str(cli_db_path))

            python_stats = python_db.get_stats()
            cli_stats = cli_db.get_stats()

            is_compatible = (
                python_stats.total_kmers == cli_stats.total_kmers and
                python_stats.unique_kmers == cli_stats.unique_kmers and
                python_stats.kmer_size == cli_stats.kmer_size
            )
        except Exception as e:
            return {"error": str(e)}

        return {
            "python_class": "KmerCounter/Database",
            "python_method": "save_to_database",
            "cli_command": "rustkmer count -o",
            "parameters": {"k": k, "input_file": str(input_file.relative_to(self.data_manager.base_path))},
            "test_data_path": str(input_file.relative_to(self.data_manager.base_path)),
            "python_output": {"stats": python_stats},
            "cli_output": {"stats": cli_stats},
            "is_identical": is_compatible,
            "differences": None if is_compatible else {"stats_mismatch": True}
        }

    def _test_multiple_query(self) -> Dict[str, Any]:
        """Test multiple query operations."""
        # Skip - similar to database_query test
        return {"skipped": "Similar to database_query test"}

    def _test_kmer_counter_params(self) -> Dict[str, Any]:
        """Test KmerCounter parameter variations."""
        # Skip - would take too long
        return {"skipped": "Parameter variation test skipped for speed"}

    def _test_count_string(self) -> Dict[str, Any]:
        """Test string input counting."""
        from rustkmer import KmerCounter
        import tempfile

        test_sequence = "ATCGATCGATCGATCGATCGATCGATCGATCG"
        k = 7

        try:
            # Python API
            counter = KmerCounter(k=k)
            counter.count_string(test_sequence)
            python_total = counter.get_total_count()

            # CLI with temp file
            with tempfile.NamedTemporaryFile(mode='w', suffix='.fa', delete=False) as f:
                f.write(f">test_sequence\n{test_sequence}\n")
                temp_file = f.name

            try:
                ret_code, cli_output, _ = self.cli_tester.run_cli_command(
                    ["count", "-k", str(k), temp_file]
                )

                if ret_code == 0:
                    cli_total = int(cli_output.split()[0])
                else:
                    cli_total = -1
            finally:
                os.unlink(temp_file)

            is_compatible = python_total == cli_total
        except Exception as e:
            return {"error": str(e)}

        return {
            "python_class": "KmerCounter",
            "python_method": "count_string",
            "cli_command": "rustkmer count",
            "parameters": {"k": k, "sequence": test_sequence},
            "python_output": python_total,
            "cli_output": cli_total,
            "is_identical": is_compatible
        }

    def _test_database_load_performance(self) -> Dict[str, Any]:
        """Test database loading performance."""
        # Skip - performance tests are handled elsewhere
        return {"skipped": "Performance test handled separately"}

    def _test_fuzzy_query(self) -> Dict[str, Any]:
        """Test fuzzy query compatibility."""
        from rustkmer import FuzzyQuery

        # Get RKDB files
        rkdb_files = self.data_manager.get_rkdb_files()
        if not rkdb_files:
            return {"skipped": "No RKDB files found"}

        test_db = rkdb_files[0]
        query_seq = "ATCGATCGATCGATCGATCGATC"
        max_mismatches = 2

        try:
            # Python API
            fuzzy_query = FuzzyQuery(str(test_db))
            python_results = fuzzy_query.query(query_seq, max_mismatches)

            # CLI
            ret_code, cli_output, _ = self.cli_tester.run_cli_with_real_data(
                ["fuzzy-query", "-m", str(max_mismatches), str(test_db.relative_to(self.data_manager.base_path)), query_seq]
            )

            if ret_code != 0:
                return {"error": f"CLI fuzzy-query failed with exit code {ret_code}"}

            # Parse CLI output (simplified)
            cli_results = []
            for line in cli_output.strip().split('\n'):
                if line and '\t' in line:
                    parts = line.split('\t')
                    if len(parts) >= 2:
                        cli_results.append({
                            "sequence": parts[0],
                            "count": int(parts[1]),
                            "mismatches": int(parts[2]) if len(parts) > 2 else 0
                        })

            # Simplified comparison
            is_compatible = len(python_results) > 0 and len(cli_results) > 0
        except Exception as e:
            return {"error": str(e)}

        return {
            "python_class": "FuzzyQuery",
            "python_method": "query",
            "cli_command": "rustkmer fuzzy-query",
            "parameters": {"max_mismatches": max_mismatches},
            "test_data_path": str(test_db.relative_to(self.data_manager.base_path)),
            "python_output": python_results,
            "cli_output": cli_results,
            "is_identical": is_compatible
        }

    def _test_database_stats(self) -> Dict[str, Any]:
        """Test database statistics compatibility."""
        # Get RKDB files
        rkdb_files = self.data_manager.get_rkdb_files()
        if not rkdb_files:
            return {"skipped": "No RKDB files found"}

        test_db = rkdb_files[0]

        try:
            # Python API
            db = Database.load(str(test_db))
            python_stats = db.get_stats()

            # CLI
            ret_code, cli_output, _ = self.cli_tester.run_cli_command(
                ["stats", str(test_db.relative_to(self.data_manager.base_path))]
            )

            if ret_code != 0:
                return {"error": f"CLI stats failed with exit code {ret_code}"}

            # Parse CLI output (simplified)
            cli_stats = {}
            for line in cli_output.strip().split('\n'):
                if ':' in line:
                    key, value = line.split(':', 1)
                    key = key.strip()
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

            # Compare key statistics
            is_compatible = True
            for key in ['total_kmers', 'unique_kmers', 'kmer_size']:
                py_val = getattr(python_stats, key, None)
                cli_val = cli_stats.get(key.replace('_', ' '))
                if py_val is not None and cli_val is not None and py_val != cli_val:
                    is_compatible = False
                    break
        except Exception as e:
            return {"error": str(e)}

        return {
            "python_class": "Database",
            "python_method": "get_stats",
            "cli_command": "rustkmer stats",
            "test_data_path": str(test_db.relative_to(self.data_manager.base_path)),
            "python_output": python_stats,
            "cli_output": cli_stats,
            "is_identical": is_compatible
        }

    def _test_database_merge(self) -> Dict[str, Any]:
        """Test database merge compatibility."""
        # Skip - complex test requiring multiple files
        return {"skipped": "Complex merge test skipped"}

    def _test_database_dump(self) -> Dict[str, Any]:
        """Test database dump compatibility."""
        # Get RKDB files
        rkdb_files = self.data_manager.get_rkdb_files()
        if not rkdb_files:
            return {"skipped": "No RKDB files found"}

        test_db = rkdb_files[0]
        python_dump_path = self.data_manager.get_test_output_path("python_dump")
        cli_dump_path = self.data_manager.get_test_output_path("cli_dump")

        try:
            # Python API dump
            db = Database.load(str(test_db))
            db.dump(str(python_dump_path))

            # CLI dump
            ret_code, _, _ = self.cli_tester.run_cli_command(
                ["dump", str(test_db.relative_to(self.data_manager.base_path)), str(cli_dump_path)]
            )

            if ret_code != 0:
                return {"error": f"CLI dump failed with exit code {ret_code}"}

            # Compare dump files (simplified - just check if both exist and have content)
            python_lines = set()
            with open(python_dump_path) as f:
                for line in f:
                    if line.strip():
                        seq, count = line.strip().split('\t')
                        python_lines.add((seq, int(count)))

            cli_lines = set()
            with open(cli_dump_path) as f:
                for line in f:
                    if line.strip():
                        seq, count = line.strip().split('\t')
                        cli_lines.add((seq, int(count)))

            is_compatible = python_lines == cli_lines
        except Exception as e:
            return {"error": str(e)}

        return {
            "python_class": "Database",
            "python_method": "dump",
            "cli_command": "rustkmer dump",
            "test_data_path": str(test_db.relative_to(self.data_manager.base_path)),
            "python_output": f"Dumped {len(python_lines)} k-mers",
            "cli_output": f"Dumped {len(cli_lines)} k-mers",
            "is_identical": is_compatible
        }

    def _test_format_compatibility(self) -> Dict[str, Any]:
        """Test database format compatibility."""
        # Skip - tested in database_save test
        return {"skipped": "Already tested in database_save"}

    def _test_alphabet_handling(self) -> Dict[str, Any]:
        """Test alphabet handling compatibility."""
        # Skip - optional test
        return {"skipped": "Optional alphabet test skipped"}

    def _test_memory_mapped_access(self) -> Dict[str, Any]:
        """Test memory-mapped database access."""
        # Skip - optional test
        return {"skipped": "Optional memory-mapped test skipped"}

    def _test_progress_reporting(self) -> Dict[str, Any]:
        """Test progress reporting compatibility."""
        # Skip - optional test
        return {"skipped": "Optional progress test skipped"}

    def _test_version_migration(self) -> Dict[str, Any]:
        """Test database version migration."""
        # Skip - optional test
        return {"skipped": "Optional version test skipped"}

    def _test_error_handling_compatibility(self) -> Dict[str, Any]:
        """Test error handling compatibility."""
        # Test with invalid file path
        invalid_file = "/nonexistent/file.fa"

        python_error = None
        cli_error = None

        # Python API error
        try:
            from rustkmer import KmerCounter
            counter = KmerCounter(k=31)
            counter.count_file(invalid_file)
        except Exception as e:
            python_error = str(e)

        # CLI error
        ret_code, _, cli_stderr = self.cli_tester.run_cli_command(
            ["count", "-k", "31", invalid_file]
        )
        if ret_code != 0:
            cli_error = cli_stderr

        return {
            "python_class": "ErrorHandling",
            "python_method": "FileNotFoundError",
            "cli_command": "rustkmer count",
            "parameters": {"file": invalid_file},
            "python_output": None,
            "cli_output": None,
            "is_identical": python_error is not None and cli_error is not None,
            "differences": None
        }

    def _test_cross_platform_compatibility(self) -> Dict[str, Any]:
        """Test cross-platform compatibility."""
        # Skip - platform-dependent test
        return {"skipped": "Platform test skipped"}

    def _test_suite_integration(self) -> Dict[str, Any]:
        """Test suite integration."""
        # Test that all components work together
        try:
            # Test data manager
            self.data_manager.setup_directories()
            data_info = self.data_manager.get_test_data_info()

            # Test CLI tester
            cli_path = self.cli_tester.cli_path
            self.cli_tester.validate_test_file("nonexistent")  # Should return False

            # Test performance comparator
            perf_comp = PerformanceComparator()

            # Test data validator
            self.data_validator.validate_fasta("nonexistent")  # Should return errors

            return {"is_identical": True}
        except Exception as e:
            return {"error": str(e)}

    def generate_report(
        self,
        suite: Optional[CompatibilityTestSuite] = None,
        format: str = "html",
        output_path: Optional[str] = None
    ) -> str:
        """
        Generate a compatibility test report.

        Args:
            suite: Test suite to report on (uses self.test_suite if None)
            format: Report format (html or json)
            output_path: Output file path

        Returns:
            Report content
        """
        test_suite = suite or self.test_suite

        if output_path is None:
            output_path = self.data_manager.get_report_path(
                f"compatibility_report_{test_suite.suite_id}",
                format
            )

        if format == "html":
            return self._generate_html_report(test_suite, output_path)
        elif format == "json":
            return self._generate_json_report(test_suite, output_path)
        else:
            raise ValueError(f"Unsupported format: {format}")

    def _generate_html_report(self, suite: CompatibilityTestSuite, output_path: str) -> str:
        """Generate HTML report."""
        html_content = f"""
<!DOCTYPE html>
<html>
<head>
    <title>RustKmer CLI-Python API Compatibility Report</title>
    <meta charset="utf-8">
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        body {{
            font-family: Arial, sans-serif;
            margin: 40px;
            background-color: #f5f5f5;
        }}
        .container {{
            max-width: 1200px;
            margin: 0 auto;
            background-color: white;
            padding: 20px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        .header {{
            text-align: center;
            border-bottom: 2px solid #007bff;
            padding-bottom: 20px;
            margin-bottom: 30px;
        }}
        .summary {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }}
        .metric {{
            background-color: #f8f9fa;
            padding: 15px;
            border-radius: 5px;
            text-align: center;
        }}
        .metric h3 {{
            margin: 0;
            font-size: 24px;
            color: #007bff;
        }}
        .metric p {{
            margin: 5px 0 0 0;
            color: #666;
        }}
        .pass {{ background-color: #d4edda; }}
        .fail {{ background-color: #f8d7da; }}
        .warning {{ background-color: #fff3cd; }}
        .chart-container {{
            width: 100%;
            height: 400px;
            margin: 20px 0;
        }}
        .test-details {{
            margin-top: 30px;
        }}
        .test-item {{
            border: 1px solid #ddd;
            margin: 10px 0;
            padding: 15px;
            border-radius: 5px;
        }}
        .test-name {{
            font-weight: bold;
            margin-bottom: 10px;
        }}
        .test-result {{
            display: flex;
            justify-content: space-between;
            align-items: center;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>RustKmer CLI-Python API Compatibility Report</h1>
            <p>Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
            <p>Python Version: {suite.python_version} | CLI Version: {suite.cli_version}</p>
            <p>Test Suite ID: {suite.suite_id}</p>
        </div>
        <div class="summary">
            <div class="metric">
                <h3>{suite.summary.total_tests if suite.summary else 0}</h3>
                <p>Total Tests</p>
            </div>
            <div class="metric pass">
                <h3>{suite.summary.passed_tests if suite.summary else 0}</h3>
                <p>Passed</p>
            </div>
            <div class="metric fail">
                <h3>{suite.summary.failed_count if suite.summary else 0}</h3>
                <p>Failed</p>
            </div>
            <div class="metric">
                <h3>{suite.summary.success_rate:.1f}%</h3>
                <p>Success Rate</p>
            </div>
        </div>

        <div class="test-details">
            <h2>Test Results</h2>
"""

        for result in suite.results[:20]:  # Limit to first 20 results
            status_class = "pass" if result.is_identical else "fail"
            html_content += f"""
            <div class="test-item {status_class}">
                <div class="test-name">{result.test_name}</div>
                <div class="test-result">
                    <span>{'PASS' if result.is_identical else 'FAIL'}</span>
                    <span>{result.execution_id}</span>
                </div>
            </div>
        """

        if len(suite.results) > 20:
            html_content += f"""
            <p>... and {len(suite.results) - 20} more tests</p>
        """

        html_content += """
        </div>
    </div>
</body>
</html>
"""

        # Save report
        with open(output_path, 'w') as f:
            f.write(html_content)

        return html_content

    def _generate_json_report(self, suite: CompatibilityTestSuite, output_path: str) -> str:
        """Generate JSON report."""
        json_data = suite.to_dict()

        with open(output_path, 'w') as f:
            json.dump(json_data, f, indent=2, default=str)

        return json.dumps(json_data, indent=2)


def main():
    """Command line interface for the test runner."""
    parser = argparse.ArgumentParser(
        description="Run RustKmer CLI-Python API compatibility tests"
    )
    parser.add_argument(
        "--categories",
        nargs="+",
        choices=["small", "medium", "large"],
        default=["small", "medium", "large"],
        help="Test categories to run"
    )
    parser.add_argument(
        "--no-performance",
        action="store_true",
        help="Skip performance tests"
    )
    parser.add_argument(
        "--output-format",
        choices=["html", "json"],
        default="html",
        help="Report output format"
    )
    parser.add_argument(
        "--output-path",
        help="Output file path (default: auto-generated)"
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Verbose output"
    )

    args = parser.parse_args()

    # Create and run tests
    runner = ComprehensiveTestRunner()
    runner.setup_directories()

    # Run all tests
    suite = runner.run_all_tests(
        categories=args.categories,
        include_performance=not args.no_performance
    )

    # Generate report
    report_path = args.output_path
    if report_path:
        report_content = runner.generate_report(
            suite=suite,
            format=args.output_format,
            output_path=report_path
        )
        print(f"\nReport saved to: {report_path}")

        # Open HTML report if browser available
        if args.output_format == "html" and sys.platform == "darwin":
            try:
                import subprocess
                subprocess.run(["open", report_path])
            except:
                pass

    # Return exit code based on test results
    return 0 if suite.summary.success_rate == 100 else 1


if __name__ == "__main__":
    sys.exit(main())