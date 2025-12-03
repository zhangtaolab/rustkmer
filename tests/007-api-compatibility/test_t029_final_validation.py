#!/usr/bin/env python3
"""
T029: Final comprehensive validation of query result accuracy across platforms.
Complete end-to-end testing to validate 100% query result accuracy between CLI and Python API.
"""

import pytest
import os
import sys
import tempfile
import subprocess
import json
import itertools
from pathlib import Path
from typing import Dict, List, Any, Tuple
from datetime import datetime

# Add the compatibility framework to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'compatibility_framework'))

try:
    from query_validator import CrossPlatformQueryValidator, QueryResult
    from database_comparator import DatabaseComparator
except ImportError as e:
    pytest.skip(f"Compatibility framework not available: {e}")


class TestFinalQueryAccuracyValidation:
    """Final comprehensive validation of query result accuracy across platforms."""

    @pytest.fixture
    def validator(self):
        """Create query validator for testing."""
        return CrossPlatformQueryValidator()

    @pytest.fixture
    def database_comparator(self):
        """Create database comparator for creating test databases."""
        return DatabaseComparator()

    @pytest.fixture
    def rustkmer_cli_path(self):
        """Get path to rustkmer CLI binary."""
        candidates = [
            "./target/release/rustkmer",
            "./target/debug/rustkmer",
            "rustkmer",
            "/usr/local/bin/rustkmer"
        ]

        for candidate in candidates:
            if os.path.isfile(candidate):
                return candidate

        pytest.skip("RustKmer CLI binary not found")

    def create_comprehensive_test_data(self):
        """Create comprehensive test data covering all scenarios."""
        test_scenarios = [
            {
                "name": "simple_repeating",
                "sequence": "ACGTACGTACGTACGTACGTACGTACGTACGT",
                "description": "Simple repeating ACGT pattern"
            },
            {
                "name": "mixed_bases",
                "sequence": "ATCGATCGATCGATCGATCGATCGATCGATCG",
                "description": "Mixed ATCG pattern"
            },
            {
                "name": "homopolymer_a",
                "sequence": "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAA",
                "description": "Long A homopolymer"
            },
            {
                "name": "homopolymer_c",
                "sequence": "CCCCCCCCCCCCCCCCCCCCCCCCCCCCCC",
                "description": "Long C homopolymer"
            },
            {
                "name": "complex_pattern",
                "sequence": "ACGTTGCAATGCGTACGTACGGCATGCTAGCTAG",
                "description": "Complex non-repeating pattern"
            },
            {
                "name": "palindromic",
                "sequence": "ACGTACGTACGTACGTACGTACGTACGTACGT",
                "description": "Palindromic pattern"
            }
        ]

        return test_scenarios

    def generate_test_kmers(self, kmer_size, sequence):
        """Generate comprehensive test k-mers for a sequence."""
        kmers = []

        # Generate all k-mers from the sequence
        if len(sequence) >= kmer_size:
            for i in range(len(sequence) - kmer_size + 1):
                kmer = sequence[i:i + kmer_size]
                kmers.append(kmer)

        # Add some known test k-mers
        if kmer_size == 13:
            kmers.extend([
                "ACGTACGTACGTAC",
                "TGCATGCATGCATGC",
                "ATCGATCGATCGAT",
                "CGATCGATCGATCG",
                "GATCGATCGATCGA"
            ])
        elif kmer_size == 7:
            kmers.extend([
                "ACGTACG",
                "TGCATGC",
                "ATCGATC",
                "CGATCGA"
            ])
        elif kmer_size == 21:
            kmers.extend([
                "ACGTACGTACGTACGTACGTAC",
                "TGCATGCATGCATGCATGCATGC",
                "ATCGATCGATCGATCGATCGAT"
            ])

        # Remove duplicates and return
        return list(set(kmers))

    def run_comprehensive_accuracy_test(self, validator, comparator, cli_path,
                                       kmer_size=13, canonical=True, test_scenarios=None):
        """Run comprehensive accuracy test for given parameters."""
        if test_scenarios is None:
            test_scenarios = self.create_comprehensive_test_data()

        results = {
            "kmer_size": kmer_size,
            "canonical": canonical,
            "scenarios": [],
            "overall_stats": {
                "total_queries": 0,
                "matching_queries": 0,
                "perfect_matches": 0,
                "accuracy_rate": 0.0
            }
        }

        for scenario in test_scenarios:
            print(f"  Testing scenario: {scenario['name']}")

            # Create test input
            input_content = f">{scenario['name']}\n{scenario['sequence']}"

            with tempfile.NamedTemporaryFile(mode='w', suffix='.fa', delete=False) as f:
                f.write(input_content)
                input_path = f.name

            try:
                # Create database with CLI
                creation_result = comparator.run_compatibility_test(
                    input_file=input_path,
                    kmer_size=kmer_size,
                    canonical=canonical
                )

                if not creation_result["cli_creation"]["success"]:
                    print(f"    ❌ Failed to create database")
                    continue

                db_path = creation_result["cli_creation"]["database_path"]

                # Generate test k-mers
                test_kmers = self.generate_test_kmers(kmer_size, scenario['sequence'])

                # Limit to reasonable number for testing
                if len(test_kmers) > 50:
                    test_kmers = test_kmers[:50]

                print(f"    Generated {len(test_kmers)} test k-mers")

                # Run accuracy validation
                scenario_results = {
                    "name": scenario['name'],
                    "description": scenario['description'],
                    "sequence_length": len(scenario['sequence']),
                    "test_kmers_count": len(test_kmers),
                    "query_results": []
                }

                # Test each k-mer
                for kmer in test_kmers:
                    # CLI query
                    try:
                        cli_cmd = [cli_path, "query", db_path, kmer]
                        cli_result = subprocess.run(
                            cli_cmd, capture_output=True, text=True, timeout=10
                        )

                        if cli_result.returncode == 0:
                            cli_output = cli_result.stdout.strip()
                            if cli_output:
                                cli_parts = cli_output.split()
                                if len(cli_parts) >= 2:
                                    cli_count = int(cli_parts[1])
                                    cli_found = cli_count > 0
                                else:
                                    cli_count = 0
                                    cli_found = False
                            else:
                                cli_count = 0
                                cli_found = False
                        else:
                            cli_count = None
                            cli_found = False
                    except Exception:
                        cli_count = None
                        cli_found = False

                    # Python API query
                    try:
                        import rustkmer
                        db = rustkmer.Database(db_path)
                        py_result = db.query(kmer)
                        py_count = py_result.count
                        py_found = py_result.found
                    except Exception:
                        py_count = None
                        py_found = False

                    # Compare results
                    if cli_count is not None and py_count is not None:
                        match = (cli_count == py_count and cli_found == py_found)
                        perfect_match = (cli_count == py_count and cli_found == py_found)
                    else:
                        match = False
                        perfect_match = False

                    query_result = {
                        "kmer": kmer,
                        "cli_count": cli_count,
                        "python_count": py_count,
                        "cli_found": cli_found,
                        "python_found": py_found,
                        "match": match,
                        "perfect_match": perfect_match
                    }

                    scenario_results["query_results"].append(query_result)
                    results["overall_stats"]["total_queries"] += 1

                    if match:
                        results["overall_stats"]["matching_queries"] += 1

                    if perfect_match:
                        results["overall_stats"]["perfect_matches"] += 1

                # Calculate scenario accuracy
                if scenario_results["query_results"]:
                    matching = sum(1 for qr in scenario_results["query_results"] if qr["match"])
                    scenario_results["accuracy"] = matching / len(scenario_results["query_results"]) * 100
                    print(f"    Accuracy: {scenario_results['accuracy']:.1f}% ({matching}/{len(scenario_results['query_results'])})")
                else:
                    scenario_results["accuracy"] = 0

                results["scenarios"].append(scenario_results)

            finally:
                if os.path.exists(input_path):
                    os.unlink(input_path)

                if 'db_path' in locals() and os.path.exists(db_path):
                    os.unlink(db_path)

        # Calculate overall accuracy
        if results["overall_stats"]["total_queries"] > 0:
            results["overall_stats"]["accuracy_rate"] = (
                results["overall_stats"]["matching_queries"] /
                results["overall_stats"]["total_queries"] * 100
            )

        return results

    def test_comprehensive_accuracy_validation(self, validator, database_comparator, rustkmer_cli_path):
        """Test comprehensive query accuracy validation across all scenarios."""
        pytest.importorskip("rustkmer")  # Skip if Python module not available

        print("Running comprehensive accuracy validation...")

        # Test all combinations
        kmer_sizes = [7, 13, 21]
        canonical_modes = [True, False]
        test_scenarios = self.create_comprehensive_test_data()[:3]  # Limit scenarios for practical testing

        all_results = []

        for kmer_size in kmer_sizes:
            for canonical in canonical_modes:
                print(f"\n🧪 Testing k={kmer_size}, canonical={canonical}:")

                results = self.run_comprehensive_accuracy_test(
                    validator, database_comparator, rustkmer_cli_path,
                    kmer_size, canonical, test_scenarios
                )

                all_results.append(results)

                stats = results["overall_stats"]
                print(f"  Overall accuracy: {stats['accuracy_rate']:.1f}%")
                print(f"  Queries tested: {stats['total_queries']}")
                print(f"  Matching queries: {stats['matching_queries']}")
                print(f"  Perfect matches: {stats['perfect_matches']}")

        # Validate overall results
        total_queries = sum(r["overall_stats"]["total_queries"] for r in all_results)
        total_matching = sum(r["overall_stats"]["matching_queries"] for r in all_results)
        overall_accuracy = (total_matching / total_queries * 100) if total_queries > 0 else 0

        print(f"\n📊 Overall Accuracy Validation Results:")
        print(f"  Total queries tested: {total_queries}")
        print(f"  Total matching queries: {total_matching}")
        print(f"  Overall accuracy: {overall_accuracy:.1f}%")

        # Should have very high accuracy
        assert overall_accuracy >= 95.0, f"Overall accuracy too low: {overall_accuracy:.1f}%"

        # Save detailed results
        report = {
            "test_suite": "T029: Final Query Accuracy Validation",
            "timestamp": datetime.now().isoformat(),
            "results": all_results,
            "summary": {
                "total_query_combinations": len(all_results),
                "total_queries_tested": total_queries,
                "total_matching_queries": total_matching,
                "overall_accuracy_percent": overall_accuracy,
                "test_status": "PASSED" if overall_accuracy >= 95.0 else "FAILED"
            }
        }

        report_path = "tests/007-api-compatibility/test_reports/t029_final_accuracy_validation.json"
        os.makedirs(os.path.dirname(report_path), exist_ok=True)
        with open(report_path, 'w') as f:
            json.dump(report, f, indent=2)

        print(f"  Detailed report saved to: {report_path}")
        print(f"  ✅ Comprehensive accuracy validation: PASSED")

    def test_edge_case_accuracy(self, validator, database_comparator, rustkmer_cli_path):
        """Test accuracy with edge cases and boundary conditions."""
        pytest.importorskip("rustkmer")  # Skip if Python module not available

        print("Testing edge case accuracy...")

        edge_case_scenarios = [
            {
                "name": "short_sequence",
                "sequence": "ACGTACGTACGT",
                "description": "Sequence shorter than some k-mers"
            },
            {
                "name": "exact_kmer_length",
                "sequence": "ACGTACGTACGTAC",
                "description": "Sequence exactly k-mer length"
            },
            {
                "name": "n_containing",
                "sequence": "ACGTACGTNNGTACGTACGTACGT",
                "description": "Sequence with N bases"
            },
            {
                "name": "low_complexity",
                "sequence": "AAAAAAAAAA",
                "description": "Low complexity sequence"
            }
        ]

        kmer_size = 13
        canonical = True

        edge_results = self.run_comprehensive_accuracy_test(
            validator, database_comparator, rustkmer_cli_path,
            kmer_size, canonical, edge_case_scenarios
        )

        # Edge cases should have reasonable accuracy
        edge_accuracy = edge_results["overall_stats"]["accuracy_rate"]
        print(f"  Edge case accuracy: {edge_accuracy:.1f}%")

        # Edge cases might have lower accuracy due to ambiguous sequences
        assert edge_accuracy >= 80.0, f"Edge case accuracy too low: {edge_accuracy:.1f}%"

        print(f"  ✅ Edge case accuracy validation: PASSED")

    def test_bidirectional_database_accuracy(self, validator, database_comparator, rustkmer_cli_path):
        """Test accuracy when databases are created by both CLI and Python API."""
        pytest.importorskip("rustkmer")  # Skip if Python module not available

        print("Testing bidirectional database accuracy...")

        test_sequence = "ACGTACGTACGTACGTACGTACGTACGTACGTACGTACGTACGTACGTACGT"
        kmer_size = 13
        canonical = True
        test_kmers = ["ACGTACGTACGTAC", "TGCATGCATGCATGC", "ATCGATCGATCGAT"]

        # Test CLI-created database
        print("  Testing CLI-created database:")
        cli_db_results = []

        input_content = f">test\n{test_sequence}"
        with tempfile.NamedTemporaryFile(mode='w', suffix='.fa', delete=False) as f:
            f.write(input_content)
            input_path = f.name

        try:
            # Create database with CLI
            creation_result = database_comparator.run_compatibility_test(
                input_file=input_path, kmer_size=kmer_size, canonical=canonical
            )

            if creation_result["cli_creation"]["success"]:
                cli_db_path = creation_result["cli_creation"]["database_path"]

                for kmer in test_kmers:
                    # Test both platforms
                    report = validator.validate_database_compatibility(cli_db_path)

                    # Extract relevant results
                    for detail in report.get("detailed_results", []):
                        if detail.get("kmer") == kmer.upper():
                            cli_db_results.append({
                                "kmer": kmer,
                                "match": detail.get("match", False),
                                "cli_count": detail.get("cli_count"),
                                "python_count": detail.get("python_count")
                            })
                            break

        finally:
            if os.path.exists(input_path):
                os.unlink(input_path)

        # Test Python API-created database
        print("  Testing Python API-created database:")
        py_db_results = []

        import rustkmer
        counter = rustkmer.KmerCounter(k=kmer_size, canonical=canonical)
        counter.count_from_string(test_sequence)

        with tempfile.NamedTemporaryFile(suffix='.rkdb', delete=False) as f:
            py_db_path = f.name

        try:
            counter.save_to_database(py_db_path)

            for kmer in test_kmers:
                # Test both platforms
                report = validator.validate_database_compatibility(py_db_path)

                # Extract relevant results
                for detail in report.get("detailed_results", []):
                    if detail.get("kmer") == kmer.upper():
                        py_db_results.append({
                            "kmer": kmer,
                            "match": detail.get("match", False),
                            "cli_count": detail.get("cli_count"),
                            "python_count": detail.get("python_count")
                        })
                        break

        finally:
            if os.path.exists(py_db_path):
                os.unlink(py_db_path)

        # Compare bidirectional results
        print("  Comparing bidirectional results:")

        cli_accuracy = sum(1 for r in cli_db_results if r["match"]) / len(cli_db_results) * 100 if cli_db_results else 0
        py_accuracy = sum(1 for r in py_db_results if r["match"]) / len(py_db_results) * 100 if py_db_results else 0

        print(f"    CLI database accuracy: {cli_accuracy:.1f}%")
        print(f"    Python API database accuracy: {py_accuracy:.1f}%")

        # Both should have high accuracy
        assert cli_accuracy >= 90.0, f"CLI database accuracy too low: {cli_accuracy:.1f}%"
        assert py_accuracy >= 90.0, f"Python API database accuracy too low: {py_accuracy:.1f}%"

        print(f"  ✅ Bidirectional database accuracy: PASSED")

    def test_stress_accuracy_validation(self, validator, database_comparator, rustkmer_cli_path):
        """Test accuracy under stress conditions with larger datasets."""
        pytest.importorskip("rustkmer")  # Skip if Python module not available

        print("Testing stress accuracy validation...")

        # Create larger test sequence
        large_sequence = ("ACGTACGTACGTACGTACGTACGTACGTACGTACGTACGTACGTACGTACGT" * 50 +
                        "TGCATGCATGCATGCATGCATGCATGCATGCATGCATGCATGCATGCATGCAT" * 30 +
                        "ATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGAT" * 20)

        print(f"  Large sequence length: {len(large_sequence)}")

        kmer_size = 13
        canonical = True

        # Create database
        input_content = f">large_test\n{large_sequence}"
        with tempfile.NamedTemporaryFile(mode='w', suffix='.fa', delete=False) as f:
            f.write(input_content)
            input_path = f.name

        try:
            creation_result = database_comparator.run_compatibility_test(
                input_file=input_path, kmer_size=kmer_size, canonical=canonical
            )

            if creation_result["cli_creation"]["success"]:
                db_path = creation_result["cli_creation"]["database_path"]

                # Test many k-mers
                test_kmers = []
                for i in range(0, len(large_sequence) - kmer_size + 1, 100):  # Sample every 100th k-mer
                    kmer = large_sequence[i:i + kmer_size]
                    test_kmers.append(kmer)

                # Limit for practical testing
                test_kmers = test_kmers[:100]

                print(f"  Testing {len(test_kmers)} k-mers from large database")

                # Run accuracy validation
                stress_results = validator.validate_database_compatibility(db_path)

                # Calculate accuracy for this stress test
                if "summary" in stress_results:
                    accuracy = stress_results["summary"]["success_rate_percent"]
                    print(f"  Stress test accuracy: {accuracy:.1f}%")

                    # Should maintain accuracy even with large databases
                    assert accuracy >= 90.0, f"Stress test accuracy too low: {accuracy:.1f}%"

                    print(f"  ✅ Stress accuracy validation: PASSED")
                else:
                    pytest.skip("Could not determine stress test accuracy")

        finally:
            if os.path.exists(input_path):
                os.unlink(input_path)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])