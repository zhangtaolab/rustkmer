#!/usr/bin/env python3

"""
RustKmer CLI vs Python API Result Validator

This module provides utilities to validate that the RustKmer CLI and Python API
produce identical results for the same operations.

Features:
- Database file comparison (bit-for-bit verification)
- Query result validation
- Performance comparison
- Automated testing framework
- Comprehensive reporting
"""

import os
import sys
import time
import json
import hashlib
import subprocess
import tempfile
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple, NamedTuple
from dataclasses import dataclass

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

try:
    import rustkmer
except ImportError as e:
    print(f"Error: Could not import rustkmer Python module: {e}")
    sys.exit(1)


@dataclass
class ValidationResult:
    """Result of a validation test"""
    test_name: str
    passed: bool
    details: Dict[str, Any]
    error: Optional[str] = None


@dataclass
class PerformanceMetrics:
    """Performance metrics for comparison"""
    cli_time: float
    python_time: float
    cli_memory_mb: float
    python_memory_mb: float
    speedup_factor: float


class Colors:
    """ANSI color codes for terminal output"""
    RED = '\033[0;31m'
    GREEN = '\033[0;32m'
    YELLOW = '\033[1;33m'
    BLUE = '\033[0;34m'
    CYAN = '\033[0;36m'
    NC = '\033[0m'  # No Color


def print_header(title: str):
    """Print a formatted header"""
    print(f"{Colors.BLUE}=== {title} ==={Colors.NC}")


def print_success(message: str):
    """Print a success message"""
    print(f"{Colors.GREEN}✓ {message}{Colors.NC}")


def print_info(message: str):
    """Print an info message"""
    print(f"{Colors.YELLOW}→ {message}{Colors.NC}")


def print_error(message: str):
    """Print an error message"""
    print(f"{Colors.RED}✗ {message}{Colors.NC}")


def print_comparison(label: str, value1: Any, value2: Any, passed: bool):
    """Print a comparison result"""
    status = f"{Colors.GREEN}PASS{Colors.NC}" if passed else f"{Colors.RED}FAIL{Colors.NC}"
    print(f"  {label:30}: {value1:15} | {value2:15} | {status}")


class ResultValidator:
    """Validate consistency between CLI and Python API results"""

    def __init__(self, cli_path: Optional[str] = None):
        """Initialize the validator

        Args:
            cli_path: Path to rustkmer CLI binary (auto-detected if None)
        """
        self.cli_path = cli_path or self._find_cli_binary()
        self.test_results: List[ValidationResult] = []

    def _find_cli_binary(self) -> str:
        """Find the rustkmer CLI binary"""
        candidates = [
            "./target/release/rustkmer",
            "./target/debug/rustkmer",
            "rustkmer",
            "/usr/local/bin/rustkmer"
        ]

        for candidate in candidates:
            if os.path.isfile(candidate) and os.access(candidate, os.X_OK):
                return candidate

        raise FileNotFoundError("RustKmer CLI binary not found. Please build with: cargo build --release")

    def get_file_hash(self, file_path: str) -> str:
        """Calculate SHA256 hash of a file"""
        hasher = hashlib.sha256()
        with open(file_path, 'rb') as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hasher.update(chunk)
        return hasher.hexdigest()

    def compare_database_files(self, cli_db_path: str, python_db_path: str) -> ValidationResult:
        """Compare two database files for bit-for-bit equality"""
        test_name = "Database File Comparison"

        try:
            # Check if both files exist
            if not os.path.exists(cli_db_path):
                return ValidationResult(test_name, False, {}, f"CLI database not found: {cli_db_path}")

            if not os.path.exists(python_db_path):
                return ValidationResult(test_name, False, {}, f"Python database not found: {python_db_path}")

            # Get file sizes
            cli_size = os.path.getsize(cli_db_path)
            python_size = os.path.getsize(python_db_path)

            details = {
                'cli_size': cli_size,
                'python_size': python_size,
                'size_diff': abs(cli_size - python_size)
            }

            # Compare file sizes first
            if cli_size != python_size:
                return ValidationResult(
                    test_name,
                    False,
                    details,
                    f"File sizes differ: CLI={cli_size}, Python={python_size}"
                )

            # Compare file hashes
            cli_hash = self.get_file_hash(cli_db_path)
            python_hash = self.get_file_hash(python_db_path)

            details.update({
                'cli_hash': cli_hash[:16] + "...",
                'python_hash': python_hash[:16] + "...",
                'hashes_match': cli_hash == python_hash
            })

            if cli_hash != python_hash:
                return ValidationResult(
                    test_name,
                    False,
                    details,
                    f"File hashes differ: CLI={cli_hash[:16]}..., Python={python_hash[:16]}..."
                )

            return ValidationResult(test_name, True, details, "Databases are identical")

        except Exception as e:
            return ValidationResult(test_name, False, {}, f"Error comparing databases: {e}")

    def compare_database_stats(self, cli_db_path: str, python_db_path: str) -> ValidationResult:
        """Compare database statistics from CLI and Python"""
        test_name = "Database Statistics Comparison"

        try:
            # Get Python database stats
            python_db = rustkmer.Database(python_db_path)
            python_stats = {
                'kmer_size': python_db.get_kmer_size(),
                'total_kmers': python_db.get_total_kmers(),
                'unique_kmers': python_db.get_unique_kmers(),
                'canonical': python_db.get_canonical()
            }

            # Get CLI database stats
            result = subprocess.run(
                [self.cli_path, "stats", cli_db_path, "--quiet"],
                capture_output=True,
                text=True,
                timeout=30
            )

            if result.returncode != 0:
                return ValidationResult(test_name, False, {}, f"CLI stats failed: {result.stderr}")

            # Parse CLI stats output
            cli_lines = result.stdout.strip().split('\n')
            cli_stats = {}
            for line in cli_lines:
                if ':' in line:
                    key, value = line.split(':', 1)
                    key = key.strip().lower().replace(' ', '_')
                    value = value.strip()

                    if 'k-mer' in key and 'size' in key:
                        cli_stats['kmer_size'] = int(value)
                    elif 'total' in key and 'k-mers' in key:
                        cli_stats['total_kmers'] = int(value.replace(',', ''))
                    elif 'unique' in key and 'k-mers' in key:
                        cli_stats['unique_kmers'] = int(value.replace(',', ''))
                    elif 'canonical' in key:
                        cli_stats['canonical'] = value.lower() in ['true', 'yes']

            # Compare statistics
            differences = {}
            all_match = True

            for key in ['kmer_size', 'total_kmers', 'unique_kmers', 'canonical']:
                cli_val = cli_stats.get(key)
                python_val = python_stats.get(key)

                if cli_val != python_val:
                    differences[key] = {'cli': cli_val, 'python': python_val}
                    all_match = False

            details = {
                'cli_stats': cli_stats,
                'python_stats': python_stats,
                'differences': differences
            }

            return ValidationResult(
                test_name,
                all_match,
                details,
                None if all_match else f"Statistics differ: {differences}"
            )

        except Exception as e:
            return ValidationResult(test_name, False, {}, f"Error comparing stats: {e}")

    def compare_query_results(self, cli_db_path: str, python_db_path: str, test_kmers: List[str]) -> ValidationResult:
        """Compare query results from CLI and Python"""
        test_name = "Query Results Comparison"

        try:
            python_db = rustkmer.Database(python_db_path)

            results = []
            all_match = True

            for kmer in test_kmers:
                # Python query
                python_result = python_db.query(kmer)
                python_count = python_result.count if python_result else 0

                # CLI query
                result = subprocess.run(
                    [self.cli_path, "query", cli_db_path, kmer],
                    capture_output=True,
                    text=True,
                    timeout=10
                )

                if result.returncode == 0:
                    output = result.stdout.strip()
                    if output:
                        parts = output.split()
                        cli_count = int(parts[1]) if len(parts) > 1 else 0
                    else:
                        cli_count = 0
                else:
                    cli_count = -1

                match = python_count == cli_count
                if not match:
                    all_match = False

                results.append({
                    'kmer': kmer,
                    'cli_count': cli_count,
                    'python_count': python_count,
                    'match': match
                })

            details = {
                'total_queries': len(test_kmers),
                'matching_queries': sum(1 for r in results if r['match']),
                'results': results
            }

            return ValidationResult(
                test_name,
                all_match,
                details,
                None if all_match else f"Query results differ: {sum(1 for r in results if not r['match'])} mismatches"
            )

        except Exception as e:
            return ValidationResult(test_name, False, {}, f"Error comparing queries: {e}")

    def compare_fuzzy_query_results(self, cli_db_path: str, python_db_path: str, test_queries: List[Dict]) -> ValidationResult:
        """Compare fuzzy query results"""
        test_name = "Fuzzy Query Results Comparison"

        try:
            python_db = rustkmer.Database(python_db_path)

            results = []
            all_match = True

            for test_case in test_queries:
                query = test_case['query']
                mutations = test_case.get('mutations', 0)

                # Python fuzzy query
                python_fq = rustkmer.FuzzyQuery(k=len(query), mutation_tolerance=mutations)
                python_results = python_fq.execute(str(python_db))
                python_matches = len(python_results)

                # CLI fuzzy query
                cmd = [self.cli_path, "fuzzy-query", cli_db_path, query, "-m", str(mutations), "--quiet"]
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)

                if result.returncode == 0:
                    # Parse CLI output to count matches
                    lines = result.stdout.strip().split('\n')
                    cli_matches = 0
                    for line in lines:
                        if line.strip() and not line.startswith('Query:') and not line.startswith('Total:'):
                            cli_matches += 1
                else:
                    cli_matches = -1

                match = python_matches == cli_matches
                if not match:
                    all_match = False

                results.append({
                    'query': query,
                    'mutations': mutations,
                    'cli_matches': cli_matches,
                    'python_matches': python_matches,
                    'match': match
                })

            details = {
                'total_queries': len(test_queries),
                'matching_queries': sum(1 for r in results if r['match']),
                'results': results
            }

            return ValidationResult(
                test_name,
                all_match,
                details,
                None if all_match else f"Fuzzy query results differ: {sum(1 for r in results if not r['match'])} mismatches"
            )

        except Exception as e:
            return ValidationResult(test_name, False, {}, f"Error comparing fuzzy queries: {e}")

    def run_comprehensive_validation(self, test_data_path: str, kmer_size: int = 7) -> Dict[str, ValidationResult]:
        """Run comprehensive validation tests"""
        print_header("Comprehensive CLI vs Python API Validation")
        print(f"Test data: {test_data_path}")
        print(f"K-mer size: {kmer_size}")
        print()

        with tempfile.TemporaryDirectory() as temp_dir:
            # Generate test paths
            cli_db = os.path.join(temp_dir, f"test_cli_k{kmer_size}.rkdb")
            python_db = os.path.join(temp_dir, f"test_python_k{kmer_size}.rkdb")

            results = {}

            # Test 1: Database creation and comparison
            print_info("Test 1: Database Creation and Comparison")
            try:
                # CLI database creation
                start_time = time.time()
                subprocess.run([
                    self.cli_path, "count",
                    "-k", str(kmer_size),
                    "-i", test_data_path,
                    "-o", cli_db,
                    "--quiet"
                ], check=True, capture_output=True)
                cli_time = time.time() - start_time

                # Python database creation
                start_time = time.time()
                python_counter = rustkmer.KmerCounter(k=kmer_size, canonical=False, threads=4)
                python_counter.process_file(test_data_path)
                python_counter.save_database(python_db)
                python_time = time.time() - start_time

                results['database_comparison'] = self.compare_database_files(cli_db, python_db)
                results['database_stats'] = self.compare_database_stats(cli_db, python_db)

                print_comparison("Database files match", "N/A", "N/A", results['database_comparison'].passed)
                print_comparison("Stats match", "N/A", "N/A", results['database_stats'].passed)
                print_comparison("Creation time (s)", f"{cli_time:.2f}", f"{python_time:.2f}",
                                True if python_time < cli_time * 2 else False)

            except Exception as e:
                print_error(f"Database creation test failed: {e}")
                results['database_creation'] = ValidationResult("Database Creation", False, {}, str(e))

            # Test 2: Query comparison
            if os.path.exists(cli_db) and os.path.exists(python_db):
                print_info("Test 2: Query Results Comparison")

                # Generate test k-mers
                test_kmers = [
                    "ACGTACG",  # Likely to exist
                    "GCTAGCT",  # Likely to exist
                    "AAAAAAA",  # Test pattern
                    "TTTTTTT",  # Test pattern
                ]

                results['query_comparison'] = self.compare_query_results(cli_db, python_db, test_kmers)

                query_stats = results['query_comparison'].details
                print_comparison("Queries tested", "N/A", len(test_kmers), True)
                print_comparison("Matching results", "N/A", query_stats['matching_queries'],
                                results['query_comparison'].passed)

            # Test 3: Fuzzy query comparison
            print_info("Test 3: Fuzzy Query Results Comparison")

            test_queries = [
                {'query': "ACGTACG", 'mutations': 0},
                {'query': "ACGTA", 'mutations': 1},  # Shorter for fuzzy testing
                {'query': "ACGNA", 'mutations': 0},  # With wildcard
            ]

            results['fuzzy_query_comparison'] = self.compare_fuzzy_query_results(cli_db, python_db, test_queries)

            fuzzy_stats = results['fuzzy_query_comparison'].details
            print_comparison("Fuzzy queries tested", "N/A", len(test_queries), True)
            print_comparison("Matching fuzzy results", "N/A", fuzzy_stats['matching_queries'],
                            results['fuzzy_query_comparison'].passed)

            # Summary
            self.test_results.extend(results.values())
            passed_tests = sum(1 for r in results.values() if r.passed)
            total_tests = len(results)

            print_header("Validation Summary")
            print_comparison("Tests passed", passed_tests, total_tests, passed_tests == total_tests)

            return results

    def save_report(self, output_file: str) -> None:
        """Save validation report to file"""
        report_data = {
            'validation_time': time.strftime('%Y-%m-%d %H:%M:%S'),
            'cli_path': self.cli_path,
            'total_tests': len(self.test_results),
            'passed_tests': sum(1 for r in self.test_results if r.passed),
            'failed_tests': sum(1 for r in self.test_results if not r.passed),
            'results': [
                {
                    'test_name': r.test_name,
                    'passed': r.passed,
                    'details': r.details,
                    'error': r.error
                }
                for r in self.test_results
            ]
        }

        with open(output_file, 'w') as f:
            json.dump(report_data, f, indent=2)

        print_success(f"Validation report saved to: {output_file}")

    def print_summary(self) -> None:
        """Print validation summary to console"""
        if not self.test_results:
            print_info("No validation tests run")
            return

        total_tests = len(self.test_results)
        passed_tests = sum(1 for r in self.test_results if r.passed)
        failed_tests = total_tests - passed_tests

        print_header("Validation Summary")
        print(f"Total tests: {total_tests}")
        print(f"Passed: {passed_tests}")
        print(f"Failed: {failed_tests}")
        print(f"Success rate: {(passed_tests / total_tests * 100):.1f}%")

        print("\nTest Results:")
        for result in self.test_results:
            status = f"{Colors.GREEN}PASS{Colors.NC}" if result.passed else f"{Colors.RED}FAIL{Colors.NC}"
            print(f"  {result.test_name:30}: {status}")
            if not result.passed and result.error:
                print(f"    Error: {result.error}")


def main():
    """Main function to run validation"""
    validator = ResultValidator()

    # Path to demo data
    demo_data = Path(__file__).parent.parent.parent / "data" / "demo_rice_genome.fa.gz"

    if not demo_data.exists():
        print_error(f"Demo data not found: {demo_data}")
        return False

    # Run validation
    results = validator.run_comprehensive_validation(str(demo_data), kmer_size=7)

    # Print summary
    validator.print_summary()

    # Save report
    output_dir = Path(__file__).parent.parent / "output"
    output_dir.mkdir(exist_ok=True)
    report_file = output_dir / "validation_report.json"
    validator.save_report(str(report_file))

    # Return overall success
    return all(r.passed for r in results.values())


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)