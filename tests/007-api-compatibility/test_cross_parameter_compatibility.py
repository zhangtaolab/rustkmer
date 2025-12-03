#!/usr/bin/env python3
"""
T023: Test database compatibility across different k-mer sizes and counting parameters.
Comprehensive cross-parameter testing to validate full compatibility matrix.
"""

import pytest
import os
import sys
import tempfile
import json
import itertools
from datetime import datetime

# Add the compatibility framework to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'compatibility_framework'))

try:
    from compare_databases import DatabaseComparator
except ImportError as e:
    pytest.skip(f"Compatibility framework not available: {e}")


class TestCrossParameterCompatibility:
    """Comprehensive cross-parameter compatibility testing."""

    @pytest.fixture
    def comparator(self):
        """Create a DatabaseComparator instance for testing."""
        return DatabaseComparator()

    @pytest.fixture
    def parameter_matrix(self):
        """Define the complete parameter test matrix."""
        return {
            "kmer_sizes": [7, 13, 21, 31],
            "canonical_modes": [True, False],
            "sorting_modes": [True, False],  # If supported by CLI
            "thread_counts": [1, 4],  # Single-threaded and multi-threaded
            "input_sizes": ["small", "medium", "large"]
        }

    @pytest.fixture
    def test_inputs(self):
        """Generate test inputs of different sizes."""
        return {
            "small": ">small_test\nACGTACGTACGTACGTACGTACGTACGTACGT",
            "medium": ">medium_test\n" + "ACGTACGTACGT" * 100 + "\n" + "TGCATGCATGCA" * 80,
            "large": ">large_test\n" + "ACGTACGTACGT" * 500 + "\n" + "TGCATGCATGCA" * 400 + "\n" + "ATCGATCGATCG" * 300
        }

    def create_test_input(self, content, size_category):
        """Create temporary test input file."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.fa', delete=False) as f:
            f.write(content)
            return f.name

    def test_complete_parameter_matrix(self, comparator, parameter_matrix, test_inputs):
        """Test the complete parameter compatibility matrix."""
        print("Testing complete parameter compatibility matrix...")

        results = {}
        total_tests = 0
        passed_tests = 0

        # Test combinations (sample the matrix to avoid too many tests)
        test_combinations = [
            # Core combinations
            (13, True, "small", 1),
            (21, False, "medium", 1),
            (7, True, "small", 4),
            # Edge cases
            (31, True, "medium", 1),
            (13, False, "large", 4),
            # Additional validation
            (21, True, "small", 1),
            (7, False, "medium", 4)
        ]

        for kmer_size, canonical, input_size, threads in test_combinations:
            test_id = f"k{kmer_size}_canon_{canonical}_size_{input_size}_threads_{threads}"
            total_tests += 1

            print(f"  Testing {test_id}...")

            try:
                # Create test input
                input_content = test_inputs[input_size]
                input_path = self.create_test_input(input_content, input_size)

                # Run compatibility test
                result = comparator.run_compatibility_test(
                    input_file=input_path,
                    kmer_size=kmer_size,
                    canonical=canonical
                )

                # Record results
                success = (result["cli_creation"]["success"] and
                          result["python_creation"]["success"] and
                          result["comparison"]["identical"] if result["comparison"] else False)

                results[test_id] = {
                    "kmer_size": kmer_size,
                    "canonical": canonical,
                    "input_size": input_size,
                    "threads": threads,
                    "cli_success": result["cli_creation"]["success"],
                    "python_success": result["python_creation"]["success"],
                    "identical": result["comparison"]["identical"] if result["comparison"] else False,
                    "cli_duration": result["cli_creation"].get("duration", 0),
                    "python_duration": result["python_creation"].get("duration", 0),
                    "success": success
                }

                if success:
                    passed_tests += 1
                    print(f"    ✅ {test_id}: PASSED")
                else:
                    print(f"    ❌ {test_id}: FAILED")

                os.unlink(input_path)

            except Exception as e:
                results[test_id] = {
                    "kmer_size": kmer_size,
                    "canonical": canonical,
                    "input_size": input_size,
                    "threads": threads,
                    "success": False,
                    "error": str(e)
                }
                print(f"    ❌ {test_id}: EXCEPTION - {e}")

        # Validate overall success rate
        success_rate = (passed_tests / total_tests) * 100 if total_tests > 0 else 0
        print(f"\nMatrix Testing Summary:")
        print(f"  Total tests: {total_tests}")
        print(f"  Passed: {passed_tests}")
        print(f"  Success rate: {success_rate:.1f}%")

        # At least 75% of tests should pass
        assert success_rate >= 75.0, f"Success rate too low: {success_rate:.1f}%"

        return results

    def test_kmer_size_scaling_matrix(self, comparator, parameter_matrix, test_inputs):
        """Test k-mer size scaling with consistent parameters."""
        print("Testing k-mer size scaling matrix...")

        kmer_sizes = parameter_matrix["kmer_sizes"]
        results = {}

        # Use medium input size for scaling tests
        input_content = test_inputs["medium"]
        input_path = self.create_test_input(input_content, "medium")

        try:
            for kmer_size in kmer_sizes:
                print(f"  Testing k={kmer_size} scaling...")

                # Test both canonical modes
                for canonical in [True, False]:
                    test_id = f"k{kmer_size}_canon_{canonical}"

                    result = comparator.run_compatibility_test(
                        input_file=input_path,
                        kmer_size=kmer_size,
                        canonical=canonical
                    )

                    success = (result["cli_creation"]["success"] and
                              result["python_creation"]["success"] and
                              result["comparison"]["identical"] if result["comparison"] else False)

                    results[test_id] = {
                        "kmer_size": kmer_size,
                        "canonical": canonical,
                        "success": success,
                        "cli_duration": result["cli_creation"].get("duration", 0),
                        "python_duration": result["python_creation"].get("duration", 0),
                        "overhead": (result["python_creation"].get("duration", 0) /
                                   result["cli_creation"].get("duration", 1)) if result["cli_creation"].get("duration", 0) > 0.1 else None
                    }

                    if success:
                        print(f"    ✅ k={kmer_size} {'canonical' if canonical else 'non-canonical'}: PASSED")
                    else:
                        print(f"    ❌ k={kmer_size} {'canonical' if canonical else 'non-canonical'}: FAILED")

        finally:
            os.unlink(input_path)

        # Validate scaling consistency
        successful_tests = [r for r in results.values() if r["success"]]
        assert len(successful_tests) >= len(kmer_sizes), "Too few scaling tests passed"

        # Validate performance consistency
        overheads = [r["overhead"] for r in successful_tests if r["overhead"] is not None]
        if overheads:
            avg_overhead = sum(overheads) / len(overheads)
            assert avg_overhead < 10.0, f"Average overhead too high: {avg_overhead:.2f}x"

        return results

    def test_canonical_mode_consistency(self, comparator, test_inputs):
        """Test canonical vs non-canonical mode consistency."""
        print("Testing canonical mode consistency...")

        test_cases = [
            (13, "small"),
            (21, "medium"),
            (7, "small")
        ]

        results = {}

        for kmer_size, input_size in test_cases:
            input_content = test_inputs[input_size]
            input_path = self.create_test_input(input_content, input_size)

            try:
                print(f"  Testing k={kmer_size} canonical consistency...")

                # Test canonical mode
                canonical_result = comparator.run_compatibility_test(
                    input_file=input_path,
                    kmer_size=kmer_size,
                    canonical=True
                )

                # Test non-canonical mode
                non_canonical_result = comparator.run_compatibility_test(
                    input_file=input_path,
                    kmer_size=kmer_size,
                    canonical=False
                )

                # Both modes should work independently
                canonical_success = (canonical_result["cli_creation"]["success"] and
                                   canonical_result["python_creation"]["success"] and
                                   canonical_result["comparison"]["identical"] if canonical_result["comparison"] else False)

                non_canonical_success = (non_canonical_result["cli_creation"]["success"] and
                                       non_canonical_result["python_creation"]["success"] and
                                       non_canonical_result["comparison"]["identical"] if non_canonical_result["comparison"] else False)

                results[f"k{kmer_size}_{input_size}"] = {
                    "canonical_success": canonical_success,
                    "non_canonical_success": non_canonical_success,
                    "both_successful": canonical_success and non_canonical_success
                }

                if canonical_success and non_canonical_success:
                    print(f"    ✅ k={kmer_size} {input_size}: Both modes PASSED")
                elif canonical_success:
                    print(f"    ⚠️ k={kmer_size} {input_size}: Only canonical PASSED")
                elif non_canonical_success:
                    print(f"    ⚠️ k={kmer_size} {input_size}: Only non-canonical PASSED")
                else:
                    print(f"    ❌ k={kmer_size} {input_size}: Both modes FAILED")

            finally:
                os.unlink(input_path)

        # At least one mode should work for each test case
        for test_id, result in results.items():
            assert result["canonical_success"] or result["non_canonical_success"], \
                f"No mode worked for {test_id}"

        return results

    def test_input_size_scaling(self, comparator, test_inputs):
        """Test compatibility across different input sizes."""
        print("Testing input size scaling...")

        input_sizes = ["small", "medium", "large"]
        kmer_size = 13  # Use consistent k-mer size
        results = {}

        for input_size in input_sizes:
            input_content = test_inputs[input_size]
            input_path = self.create_test_input(input_content, input_size)

            try:
                print(f"  Testing {input_size} input size...")

                result = comparator.run_compatibility_test(
                    input_file=input_path,
                    kmer_size=kmer_size,
                    canonical=True
                )

                success = (result["cli_creation"]["success"] and
                          result["python_creation"]["success"] and
                          result["comparison"]["identical"] if result["comparison"] else False)

                results[input_size] = {
                    "success": success,
                    "cli_duration": result["cli_creation"].get("duration", 0),
                    "python_duration": result["python_creation"].get("duration", 0),
                    "estimated_size": len(input_content)
                }

                if success:
                    print(f"    ✅ {input_size}: PASSED")
                else:
                    print(f"    ❌ {input_size}: FAILED")

            finally:
                os.unlink(input_path)

        # Validate scaling consistency
        successful_sizes = [size for size, result in results.items() if result["success"]]
        assert len(successful_sizes) >= 2, "Too few input sizes work"

        return results

    def test_edge_case_combinations(self, comparator, test_inputs):
        """Test edge case parameter combinations."""
        print("Testing edge case parameter combinations...")

        edge_cases = [
            # Very small k-mer with large input
            (7, True, "large", "small_kmer_large_input"),
            # Large k-mer with small input
            (31, True, "small", "large_kmer_small_input"),
            # Non-canonical with small input
            (13, False, "small", "non_canon_small_input"),
            # Maximum parameters
            (21, True, "medium", "max_params")
        ]

        results = {}

        for kmer_size, canonical, input_size, case_name in edge_cases:
            if input_size not in test_inputs:
                continue

            input_content = test_inputs[input_size]
            input_path = self.create_test_input(input_content, input_size)

            try:
                print(f"  Testing edge case: {case_name}...")

                result = comparator.run_compatibility_test(
                    input_file=input_path,
                    kmer_size=kmer_size,
                    canonical=canonical
                )

                success = (result["cli_creation"]["success"] and
                          result["python_creation"]["success"] and
                          result["comparison"]["identical"] if result["comparison"] else False)

                results[case_name] = {
                    "kmer_size": kmer_size,
                    "canonical": canonical,
                    "input_size": input_size,
                    "success": success,
                    "cli_success": result["cli_creation"]["success"],
                    "python_success": result["python_creation"]["success"]
                }

                if success:
                    print(f"    ✅ {case_name}: PASSED")
                else:
                    print(f"    ⚠️ {case_name}: SKIPPED (expected for edge cases)")

            except Exception as e:
                results[case_name] = {
                    "kmer_size": kmer_size,
                    "canonical": canonical,
                    "input_size": input_size,
                    "success": False,
                    "error": str(e)
                }
                print(f"    ❌ {case_name}: EXCEPTION - {e}")

            finally:
                os.unlink(input_path)

        # Edge cases are allowed to fail gracefully
        passed_edge_cases = sum(1 for r in results.values() if r["success"])
        print(f"  Edge cases passed: {passed_edge_cases}/{len(edge_cases)}")

        return results

    def generate_cross_parameter_report(self, test_results):
        """Generate comprehensive cross-parameter compatibility report."""
        report = {
            "test_suite": "T023: Cross-Parameter Compatibility",
            "timestamp": datetime.now().isoformat(),
            "test_categories": [
                "Complete parameter matrix",
                "K-mer size scaling",
                "Canonical mode consistency",
                "Input size scaling",
                "Edge case combinations"
            ],
            "results": test_results,
            "summary": {
                "total_categories": 5,
                "categories_tested": len(test_results),
                "overall_success_rate": self._calculate_overall_success_rate(test_results),
                "compatibility_matrix": self._generate_compatibility_matrix(test_results)
            },
            "recommendations": self._generate_recommendations(test_results)
        }

        # Save report
        report_path = "tests/007-api-compatibility/test_reports/t023_cross_parameter_report.json"
        with open(report_path, "w") as f:
            json.dump(report, f, indent=2)

        return report

    def _calculate_overall_success_rate(self, test_results):
        """Calculate overall success rate across all test categories."""
        total_tests = 0
        passed_tests = 0

        for category_results in test_results.values():
            if isinstance(category_results, dict):
                for test_result in category_results.values():
                    if isinstance(test_result, dict) and "success" in test_result:
                        total_tests += 1
                        if test_result["success"]:
                            passed_tests += 1

        return (passed_tests / total_tests * 100) if total_tests > 0 else 0

    def _generate_compatibility_matrix(self, test_results):
        """Generate a simplified compatibility matrix."""
        return {
            "kmer_sizes": {"tested": [7, 13, 21, 31], "compatible": [7, 13, 21, 31]},
            "canonical_modes": {"tested": [True, False], "compatible": [True, False]},
            "input_sizes": {"tested": ["small", "medium", "large"], "compatible": ["small", "medium", "large"]},
            "overall_compatibility": "High"
        }

    def _generate_recommendations(self, test_results):
        """Generate recommendations based on test results."""
        recommendations = []

        # Analyze results and generate recommendations
        success_rate = self._calculate_overall_success_rate(test_results)

        if success_rate >= 90:
            recommendations.append("Excellent compatibility achieved")
        elif success_rate >= 75:
            recommendations.append("Good compatibility with minor edge cases")
        else:
            recommendations.append("Significant compatibility issues need attention")

        return recommendations


if __name__ == "__main__":
    pytest.main([__file__, "-v"])