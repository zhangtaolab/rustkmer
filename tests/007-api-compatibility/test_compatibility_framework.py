#!/usr/bin/env python3
"""
Test suite for compatibility framework validation.
"""

import pytest
import sys
import os

# Add the compatibility framework to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'compatibility_framework'))

try:
    from compare_databases import DatabaseComparator
    from query_comparator import QueryComparator
except ImportError as e:
    pytest.skip(f"Compatibility framework not available: {e}")

class TestDatabaseComparator:
    """Test database comparison functionality."""

    def test_comparator_initialization(self):
        """Test that DatabaseComparator can be initialized."""
        comparator = DatabaseComparator()
        assert comparator.cli_path == "rustkmer"
        assert len(comparator.test_results) == 0

    def test_hash_calculation(self):
        """Test hash calculation functionality."""
        # Create temporary files with known content
        import tempfile
        import hashlib

        test_content = "test content for hashing"

        with tempfile.NamedTemporaryFile(mode='w', delete=False) as f:
            f.write(test_content)
            f.flush()
            file_path = f.name

        try:
            # Calculate hash using our method
            def file_hash(filepath):
                hasher = hashlib.sha256()
                with open(filepath, 'rb') as f:
                    for chunk in iter(lambda: f.read(4096), b""):
                        hasher.update(chunk)
                return hasher.hexdigest()

            hash1 = file_hash(file_path)
            hash2 = file_hash(file_path)  # Should be identical

            assert hash1 == hash2
            assert len(hash1) == 64  # SHA256 hash length

        finally:
            os.unlink(file_path)

    def test_file_size_comparison(self):
        """Test file size comparison logic."""
        import tempfile

        with tempfile.NamedTemporaryFile(mode='w', delete=False) as f1:
            f1.write("short")
            f1.flush()
            file1_path = f1.name

        with tempfile.NamedTemporaryFile(mode='w', delete=False) as f2:
            f2.write("short")
            f2.flush()
            file2_path = f2.name

        with tempfile.NamedTemporaryFile(mode='w', delete=False) as f3:
            f3.write("different length content")
            f3.flush()
            file3_path = f3.name

        try:
            # Test identical sizes
            size1 = os.path.getsize(file1_path)
            size2 = os.path.getsize(file2_path)
            assert size1 == size2

            # Test different sizes
            size3 = os.path.getsize(file3_path)
            assert size1 != size3

        finally:
            os.unlink(file1_path)
            os.unlink(file2_path)
            os.unlink(file3_path)


class TestQueryComparator:
    """Test query comparison functionality."""

    def test_query_comparator_initialization(self):
        """Test that QueryComparator can be initialized."""
        comparator = QueryComparator()
        assert comparator.cli_path == "rustkmer"
        assert len(comparator.query_results) == 0

    def test_kmer_format_validation(self):
        """Test k-mer format validation."""
        # Test valid k-mers
        valid_kmers = [
            "ACGTACGTACGTACGTACGT",
            "TGCATGCATGCATGCATGCA",
            "ATCGATCGATCGATCGATCG"
        ]

        for kmer in valid_kmers:
            assert len(kmer) == 21  # Assuming k=21
            assert all(base in 'ACGTacgt' for base in kmer)

        # Test invalid k-mers (contain N)
        invalid_kmers = [
            "ACGTACGTACGTACGTACGN",
            "TGCATGCATGCATGCATGCN"
        ]

        for kmer in invalid_kmers:
            assert 'N' in kmer or 'n' in kmer  # Invalid characters

    def test_result_comparison_logic(self):
        """Test query result comparison logic."""
        # Test identical results
        result1 = {"found": True, "count": 5, "kmer": "ACGT"}
        result2 = {"found": True, "count": 5, "kmer": "acgt"}  # Case insensitive
        result3 = {"found": False, "count": 0, "kmer": "ACGT"}

        comparator = QueryComparator()

        # Test comparison method exists and works
        comparison1 = comparator._compare_query_results(result1, result2, True, True)
        assert comparison1["identical"] is True

        comparison2 = comparator._compare_query_results(result1, result3, True, True)
        assert comparison2["identical"] is False
        assert comparison2["reason"].startswith("Count mismatch")

        # Test failure cases
        comparison3 = comparator._compare_query_results(
            {"error": "CLI failed"}, {"error": "Python failed"}, False, False
        )
        assert comparison3["identical"] is False
        assert "Query failed" in comparison3["reason"]


@pytest.mark.compatibility
class TestFrameworkIntegration:
    """Integration tests for the compatibility framework."""

    def test_module_imports(self):
        """Test that all required modules can be imported."""
        try:
            import compare_databases
            import query_comparator
            assert hasattr(compare_databases, 'DatabaseComparator')
            assert hasattr(query_comparator, 'QueryComparator')
        except ImportError as e:
            pytest.fail(f"Failed to import framework modules: {e}")

    def test_directory_structure(self):
        """Test that required directories exist."""
        required_dirs = [
            'compatibility_framework',
            'performance_benchmarks',
            'test_data/small',
            'test_data/medium',
            'test_data/large'
        ]

        for dir_name in required_dirs:
            dir_path = os.path.join(os.path.dirname(__file__), dir_name)
            assert os.path.exists(dir_path), f"Directory {dir_name} does not exist"

    def test_file_permissions(self):
        """Test that framework files have correct permissions."""
        framework_files = [
            'compatibility_framework/compare_databases.py',
            'compatibility_framework/query_comparator.py',
            'performance_benchmarks/benchmark_suite.py'
        ]

        for file_name in framework_files:
            file_path = os.path.join(os.path.dirname(__file__), file_name)
            assert os.path.exists(file_path), f"File {file_name} does not exist"
            assert os.access(file_path, os.R_OK), f"File {file_name} is not readable"
            assert os.access(file_path, os.X_OK), f"File {file_name} is not executable"


@pytest.mark.compatibility
class TestBitForBitDatabaseValidation:
    """Bit-for-bit database compatibility validation tests."""

    @pytest.fixture
    def comparator(self):
        """Create a DatabaseComparator instance for testing."""
        return DatabaseComparator()

    @pytest.fixture
    def test_data_dir(self):
        """Get path to test data directory."""
        return os.path.join(os.path.dirname(__file__), "test_data")

    def test_small_dataset_bit_for_bit_compatibility(self, comparator, test_data_dir):
        """Test bit-for-bit compatibility with small test dataset."""
        small_file = os.path.join(test_data_dir, "small", "test_sequences.fa")

        if not os.path.exists(small_file):
            pytest.skip("Small test data not available")

        # Run compatibility test
        result = comparator.run_compatibility_test(
            input_file=small_file,
            kmer_size=13,  # Small k-mer size for testing
            canonical=True
        )

        # Verify both databases were created successfully
        assert result["cli_creation"]["success"], f"CLI database creation failed: {result['cli_creation']['message']}"
        assert result["python_creation"]["success"], f"Python database creation failed: {result['python_creation']['message']}"

        # Verify bit-for-bit compatibility
        comparison = result["comparison"]
        assert comparison["identical"], f"Bit-for-bit comparison failed: {comparison['reason']}"

        # Verify file sizes are reasonable (should be > 0 bytes)
        assert comparison.get("size_diff", 0) == 0, "Database files should be identical size"

    def test_medium_dataset_bit_for_bit_compatibility(self, comparator, test_data_dir):
        """Test bit-for-bit compatibility with medium test dataset."""
        medium_file = os.path.join(test_data_dir, "medium", "test_sequences.fa")

        if not os.path.exists(medium_file):
            pytest.skip("Medium test data not available")

        # Run compatibility test
        result = comparator.run_compatibility_test(
            input_file=medium_file,
            kmer_size=21,  # Medium k-mer size
            canonical=True
        )

        # Verify both databases were created successfully
        assert result["cli_creation"]["success"], f"CLI database creation failed: {result['cli_creation']['message']}"
        assert result["python_creation"]["success"], f"Python database creation failed: {result['python_creation']['message']}"

        # Verify bit-for-bit compatibility
        comparison = result["comparison"]
        assert comparison["identical"], f"Bit-for-bit comparison failed: {comparison['reason']}"

        # Verify performance overhead is reasonable (<10x)
        cli_time = result["cli_creation"]["duration"]
        python_time = result["python_creation"]["duration"]

        if cli_time > 0.1:  # Only check if CLI time is significant
            overhead = python_time / cli_time
            assert overhead < 10.0, f"Python API overhead too high: {overhead:.2f}x (should be <10x)"

    def test_canonical_mode_compatibility(self, comparator, test_data_dir):
        """Test compatibility with canonical mode enabled."""
        small_file = os.path.join(test_data_dir, "small", "test_sequences.fa")

        if not os.path.exists(small_file):
            pytest.skip("Small test data not available")

        # Test canonical mode
        result = comparator.run_compatibility_test(
            input_file=small_file,
            kmer_size=13,
            canonical=True
        )

        # Verify bit-for-bit compatibility in canonical mode
        comparison = result["comparison"]
        assert comparison["identical"], f"Canonical mode compatibility failed: {comparison['reason']}"

    def test_non_canonical_mode_compatibility(self, comparator, test_data_dir):
        """Test compatibility with canonical mode disabled."""
        small_file = os.path.join(test_data_dir, "small", "test_sequences.fa")

        if not os.path.exists(small_file):
            pytest.skip("Small test data not available")

        # Test non-canonical mode
        result = comparator.run_compatibility_test(
            input_file=small_file,
            kmer_size=13,
            canonical=False
        )

        # Verify bit-for-bit compatibility in non-canonical mode
        comparison = result["comparison"]
        assert comparison["identical"], f"Non-canonical mode compatibility failed: {comparison['reason']}"

    def test_different_kmer_sizes_compatibility(self, comparator, test_data_dir):
        """Test compatibility across different k-mer sizes."""
        small_file = os.path.join(test_data_dir, "small", "test_sequences.fa")

        if not os.path.exists(small_file):
            pytest.skip("Small test data not available")

        # Test different k-mer sizes
        kmer_sizes = [7, 13, 21, 31]  # Range of k-mer sizes

        for kmer_size in kmer_sizes:
            result = comparator.run_compatibility_test(
                input_file=small_file,
                kmer_size=kmer_size,
                canonical=True
            )

            # Verify compatibility for each k-mer size
            comparison = result["comparison"]
            assert comparison["identical"], f"K-mer size {kmer_size} compatibility failed: {comparison['reason']}"

    def test_test_results_accumulation(self, comparator):
        """Test that test results are properly accumulated."""
        initial_count = len(comparator.test_results)

        # Create a simple test file
        import tempfile
        with tempfile.NamedTemporaryFile(mode='w', suffix='.fa', delete=False) as f:
            f.write(">test_sequence\nACGTACGTACGTACGTACGT\n")
            test_file = f.name

        try:
            # Run multiple tests
            for i in range(3):
                comparator.run_compatibility_test(
                    input_file=test_file,
                    kmer_size=13,
                    canonical=True
                )

            # Verify results were accumulated
            assert len(comparator.test_results) == initial_count + 3, f"Expected {initial_count + 3} test results, got {len(comparator.test_results)}"

            # Get summary
            summary = comparator.get_test_summary()
            assert "total_tests" in summary, "Test summary should contain total_tests"
            assert "successful_tests" in summary, "Test summary should contain successful_tests"

        finally:
            # Clean up
            os.unlink(test_file)

    def test_database_file_preservation(self, comparator, test_data_dir):
        """Test that database files are preserved for manual inspection."""
        small_file = os.path.join(test_data_dir, "small", "test_sequences.fa")

        if not os.path.exists(small_file):
            pytest.skip("Small test data not available")

        # Run compatibility test
        result = comparator.run_compatibility_test(
            input_file=small_file,
            kmer_size=13,
            canonical=True
        )

        if result["cli_creation"]["success"] and result["python_creation"]["success"]:
            # Check that test databases directory was created and contains files
            test_databases_dir = "test_databases"
            assert os.path.exists(test_databases_dir), "Test databases directory should be created"

            # Look for test database files
            test_files = [f for f in os.listdir(test_databases_dir) if f.endswith('.rkdb')]
            assert len(test_files) >= 2, f"Expected at least 2 test database files, found {len(test_files)}"

            # Verify files are not empty
            for test_file in test_files:
                file_path = os.path.join(test_databases_dir, test_file)
                assert os.path.getsize(file_path) > 0, f"Test database file {test_file} should not be empty"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])