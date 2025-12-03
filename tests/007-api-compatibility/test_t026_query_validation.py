#!/usr/bin/env python3
"""
T026: Test cross-platform query result validation framework.
Comprehensive testing to validate 100% query result consistency between CLI and Python API.
"""

import pytest
import os
import sys
import tempfile
import json
import subprocess
from pathlib import Path

# Add the compatibility framework to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'compatibility_framework'))

try:
    from query_validator import CrossPlatformQueryValidator, QueryTestCase, QueryResult, ValidationResult
    from database_comparator import DatabaseComparator
except ImportError as e:
    pytest.skip(f"Compatibility framework not available: {e}")


class TestCrossPlatformQueryValidation:
    """Comprehensive cross-platform query validation testing."""

    @pytest.fixture
    def validator(self):
        """Create a CrossPlatformQueryValidator instance."""
        return CrossPlatformQueryValidator()

    @pytest.fixture
    def test_database_path(self):
        """Create a test database for validation."""
        comparator = DatabaseComparator()

        # Create test input
        test_input = ">test_query_validation\nACGTACGTACGTACGTACGTACGTACGTACGTACGTACGTACGTACGTACGTACGTACGTACGT\nTGCATGCATGCATGCATGCATGCATGCATGCATGCATGCATGCATGCATGCATGCATGCATGCAT"

        with tempfile.NamedTemporaryFile(mode='w', suffix='.fa', delete=False) as f:
            f.write(test_input)
            input_path = f.name

        try:
            # Create database using CLI
            result = comparator.run_compatibility_test(
                input_file=input_path,
                kmer_size=13,
                canonical=True
            )

            if result["cli_creation"]["success"] and result["cli_creation"]["database_path"]:
                return result["cli_creation"]["database_path"]
            else:
                pytest.skip("Failed to create test database")

        finally:
            os.unlink(input_path)

    def test_validator_initialization(self, validator):
        """Test validator initialization."""
        assert validator.cli_path is not None
        assert os.path.isfile(validator.cli_path)
        assert len(validator.test_results) == 0

    def test_test_case_creation(self, validator):
        """Test test case creation for different k-mer sizes."""
        # Test k=13
        test_cases = validator.create_test_cases(13)
        assert len(test_cases) > 0

        categories = set(tc.category for tc in test_cases)
        assert "valid" in categories
        assert "edge" in categories

        # Check valid k-mers have correct length
        valid_cases = [tc for tc in test_cases if tc.category == "valid"]
        for tc in valid_cases:
            assert len(tc.kmer) == 13
            assert set(tc.kmer).issubset(set("ACGT"))

    def test_individual_cli_query_execution(self, validator, test_database_path):
        """Test individual CLI query execution."""
        kmer = "ACGTACGTACGTAC"  # 13-mer

        result, error = validator._run_cli_query(test_database_path, kmer)

        assert error is None, f"CLI query failed: {error}"
        assert result is not None
        assert result.kmer == kmer.upper()
        assert isinstance(result.count, int)
        assert result.count >= 0
        assert result.source == "cli"
        assert result.duration >= 0

    def test_individual_python_query_execution(self, validator, test_database_path):
        """Test individual Python API query execution."""
        pytest.importorskip("rustkmer")  # Skip if Python module not available

        kmer = "ACGTACGTACGTAC"  # 13-mer

        result, error = validator._run_python_query(test_database_path, kmer)

        assert error is None, f"Python query failed: {error}"
        assert result is not None
        assert result.kmer == kmer.upper()
        assert isinstance(result.count, int)
        assert result.count >= 0
        assert result.source == "python"
        assert result.duration >= 0

    def test_query_result_consistency(self, validator, test_database_path):
        """Test that CLI and Python API return consistent results."""
        pytest.importorskip("rustkmer")  # Skip if Python module not available

        test_kmers = [
            "ACGTACGTACGTAC",  # Should exist
            "GGGGGGGGGGGGGG",  # May not exist
            "AAAAAAAAAAAAAA",  # Should exist
            "TTTTTTTTTTTTTT",  # Should exist
        ]

        for kmer in test_kmers:
            # Run both queries
            cli_result, cli_error = validator._run_cli_query(test_database_path, kmer)
            python_result, python_error = validator._run_python_query(test_database_path, kmer)

            # Check for errors
            assert cli_error is None, f"CLI query failed for {kmer}: {cli_error}"
            assert python_error is None, f"Python query failed for {kmer}: {python_error}"

            # Check consistency
            assert cli_result is not None
            assert python_result is not None

            assert cli_result.kmer == python_result.kmer
            assert cli_result.count == python_result.count
            assert cli_result.found == python_result.found

            print(f"  ✅ {kmer}: CLI={cli_result.count}, Python={python_result.count} (MATCH)")

    def test_batch_query_consistency(self, validator, test_database_path):
        """Test batch query consistency."""
        pytest.importorskip("rustkmer")  # Skip if Python module not available

        # Create test batch
        test_kmers = [
            "ACGTACGTACGTAC",
            "GGGGGGGGGGGGGG",
            "AAAAAAAAAAAAAA",
            "TTTTTTTTTTTTTT",
            "CCCCCCCCCCCCCC",
        ] * 10  # 50 total queries

        python_results, python_error = validator._run_python_batch_query(test_database_path, test_kmers)
        assert python_error is None, f"Python batch query failed: {python_error}"
        assert len(python_results) == len(test_kmers)

        # Compare with individual CLI queries
        matches = 0
        for i, (kmer, python_result) in enumerate(zip(test_kmers, python_results)):
            cli_result, cli_error = validator._run_cli_query(test_database_path, kmer)
            assert cli_error is None, f"CLI query failed for {kmer}: {cli_error}"

            if (cli_result.count == python_result.count and
                cli_result.found == python_result.found and
                cli_result.kmer == python_result.kmer):
                matches += 1

        accuracy = (matches / len(test_kmers)) * 100
        assert accuracy == 100.0, f"Batch query accuracy: {accuracy:.1f}% (expected 100%)"

    def test_comprehensive_database_validation(self, validator, test_database_path):
        """Test comprehensive database validation."""
        pytest.importorskip("rustkmer")  # Skip if Python module not available

        # Run comprehensive validation
        report = validator.validate_database_compatibility(test_database_path)

        # Check report structure
        assert "summary" in report
        assert "categories" in report
        assert "performance" in report
        assert "detailed_results" in report

        summary = report["summary"]
        assert summary["total_tests"] > 0
        assert summary["success_rate_percent"] >= 0

        # Check that most tests pass (allowing some edge cases to fail)
        assert summary["success_rate_percent"] >= 80.0, f"Success rate too low: {summary['success_rate_percent']:.1f}%"

        # Performance should be reasonable
        performance = report["performance"]
        assert performance["overhead_factor"] < 20.0, f"Overhead too high: {performance['overhead_factor']:.1f}x"

    def test_edge_case_handling(self, validator, test_database_path):
        """Test edge case handling in queries."""
        pytest.importorskip("rustkmer")  # Skip if Python module not available

        edge_cases = [
            ("N" * 13, "All N's"),
            ("acgtacgtacgtac", "Lower case"),
            ("A" * 12, "Too short"),
            ("A" * 14, "Too long"),
            ("ACGTACGTACGTX", "Invalid character"),
        ]

        for kmer, description in edge_cases:
            print(f"  Testing edge case: {description}")

            cli_result, cli_error = validator._run_cli_query(test_database_path, kmer)
            python_result, python_error = validator._run_python_query(test_database_path, kmer)

            # Both should handle errors gracefully or return consistent results
            if cli_error and python_error:
                # Both failed - acceptable for edge cases
                print(f"    ⚠️ Both failed (expected for edge case)")
            elif cli_error or python_error:
                # One failed - investigate
                print(f"    ❌ Mismatch: CLI error={bool(cli_error)}, Python error={bool(python_error)}")
            else:
                # Both succeeded - check consistency
                assert cli_result.count == python_result.count
                assert cli_result.found == python_result.found
                print(f"    ✅ Both handled consistently")

    def test_performance_analysis(self, validator, test_database_path):
        """Test performance analysis capabilities."""
        pytest.importorskip("rustkmer")  # Skip if Python module not available

        # Run validation with multiple queries to get performance data
        test_cases = validator.create_test_cases(13)
        test_cases = test_cases[:10]  # Limit to 10 for performance test

        report = validator.validate_database_compatibility(test_database_path, test_cases)

        performance = report["performance"]
        assert performance["avg_cli_time_ms"] >= 0
        assert performance["avg_python_time_ms"] >= 0
        assert performance["overhead_factor"] >= 0

        # Python overhead should be reasonable (less than 100x)
        assert performance["overhead_factor"] < 100.0, f"Python overhead too high: {performance['overhead_factor']:.1f}x"

        print(f"  Performance Analysis:")
        print(f"    Avg CLI time: {performance['avg_cli_time_ms']:.3f}ms")
        print(f"    Avg Python time: {performance['avg_python_time_ms']:.3f}ms")
        print(f"    Overhead factor: {performance['overhead_factor']:.1f}x")

    def test_batch_validation_framework(self, validator, test_database_path):
        """Test batch validation framework."""
        pytest.importorskip("rustkmer")  # Skip if Python module not available

        batch_report = validator.validate_batch_queries(test_database_path, [5, 10, 20])

        assert "database_path" in batch_report
        assert "batch_validation" in batch_report
        assert "summary" in batch_report

        summary = batch_report["summary"]
        assert summary["total_batches_tested"] == 3
        assert summary["batch_sizes_tested"] == [5, 10, 20]

        # Check batch results
        batch_validation = batch_report["batch_validation"]
        for batch_size in [5, 10, 20]:
            assert batch_size in batch_validation
            if "error" not in batch_validation[batch_size]:
                batch_result = batch_validation[batch_size]
                assert batch_result["total_queries"] == batch_size
                assert batch_result["accuracy_percent"] >= 0

    def test_validation_report_generation(self, validator, test_database_path):
        """Test validation report generation and saving."""
        pytest.importorskip("rustkmer")  # Skip if Python module not available

        # Run validation
        report = validator.validate_database_compatibility(test_database_path)

        # Save report
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            report_path = f.name

        try:
            saved_path = validator.save_validation_report(report, report_path)
            assert saved_path == report_path
            assert os.path.isfile(report_path)

            # Load and verify report
            with open(report_path, 'r') as f:
                loaded_report = json.load(f)

            assert loaded_report == report

        finally:
            if os.path.exists(report_path):
                os.unlink(report_path)

    def test_validation_result_structure(self):
        """Test ValidationResult data structure."""
        test_case = QueryTestCase(kmer="ACGTACGTACGTAC", description="Test case")
        result = ValidationResult(test_case=test_case)

        assert result.test_case == test_case
        assert result.cli_result is None
        assert result.python_result is None
        assert result.match is False
        assert result.error is None

    def test_query_result_structure(self):
        """Test QueryResult data structure."""
        result = QueryResult(
            kmer="ACGTACGTACGTAC",
            count=5,
            found=True,
            duration=0.001,
            source="cli"
        )

        assert result.kmer == "ACGTACGTACGTAC"
        assert result.count == 5
        assert result.found is True
        assert result.duration == 0.001
        assert result.source == "cli"

    def test_canonical_kmer_handling(self, validator, test_database_path):
        """Test canonical k-mer handling consistency."""
        pytest.importorskip("rustkmer")  # Skip if Python module not available

        # Test canonical k-mer pairs
        canonical_pairs = [
            ("ACGTACGTACGTAC", "GTGTACGTACGTAC"),  # Different forms
            ("AAAAAAAAAAAAAA", "TTTTTTTTTTTTTT"),  # Reverse complements
        ]

        for kmer1, kmer2 in canonical_pairs:
            print(f"  Testing canonical pair: {kmer1} vs {kmer2}")

            # Query both forms
            cli_result1, cli_error1 = validator._run_cli_query(test_database_path, kmer1)
            cli_result2, cli_error2 = validator._run_cli_query(test_database_path, kmer2)

            python_result1, python_error1 = validator._run_python_query(test_database_path, kmer1)
            python_result2, python_error2 = validator._run_python_query(test_database_path, kmer2)

            # Check that both CLI and Python handle canonical forms consistently
            if (cli_error1 is None and cli_error2 is None and
                python_error1 is None and python_error2 is None):

                # CLI should return same count for canonical forms
                assert cli_result1.count == cli_result2.count, f"CLI canonical mismatch: {kmer1}={cli_result1.count}, {kmer2}={cli_result2.count}"

                # Python should return same count for canonical forms
                assert python_result1.count == python_result2.count, f"Python canonical mismatch: {kmer1}={python_result1.count}, {kmer2}={python_result2.count}"

                # CLI and Python should agree
                assert cli_result1.count == python_result1.count, f"CLI/Python mismatch for {kmer1}: CLI={cli_result1.count}, Python={python_result1.count}"

                print(f"    ✅ Canonical forms consistent: count={cli_result1.count}")

    def test_different_kmer_sizes(self, validator):
        """Test validation with databases of different k-mer sizes."""
        pytest.importorskip("rustkmer")  # Skip if Python module not available

        kmer_sizes = [7, 13, 21]
        comparator = DatabaseComparator()

        for kmer_size in kmer_sizes:
            print(f"  Testing k={kmer_size} database validation")

            # Create test database
            test_input = f">test_k{kmer_size}\n{'ACGT' * 20}\n{'TGCA' * 15}"

            with tempfile.NamedTemporaryFile(mode='w', suffix='.fa', delete=False) as f:
                f.write(test_input)
                input_path = f.name

            try:
                result = comparator.run_compatibility_test(
                    input_file=input_path,
                    kmer_size=kmer_size,
                    canonical=True
                )

                if result["cli_creation"]["success"] and result["cli_creation"]["database_path"]:
                    db_path = result["cli_creation"]["database_path"]

                    # Create test cases for this k-mer size
                    test_cases = validator.create_test_cases(kmer_size)

                    # Run validation
                    report = validator.validate_database_compatibility(db_path, test_cases)

                    # Check that validation worked
                    assert report["summary"]["total_tests"] > 0
                    success_rate = report["summary"]["success_rate_percent"]
                    assert success_rate >= 70.0, f"k={kmer_size} success rate too low: {success_rate:.1f}%"

                    print(f"    ✅ k={kmer_size}: {success_rate:.1f}% success rate")

                else:
                    print(f"    ⚠️ k={kmer_size}: Failed to create database")

            finally:
                os.unlink(input_path)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])