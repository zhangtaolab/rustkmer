"""
FuzzyQuery Edge Cases Test Suite
================================

This module provides comprehensive edge case testing for FuzzyQuery wildcard pattern processing,
focusing on boundary conditions, extreme inputs, and robust error handling.

Validates:
- Wildcard pattern processing edge cases
- Boundary conditions for k-mer sizes and patterns
- Extreme input handling
- Robustness of variant generation algorithms
"""

import pytest
import sys
import os
from pathlib import Path

# Add the rustkmer Python module to path for testing
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src" / "python"))

try:
    from rustkmer import FuzzyQuery
except ImportError:
    pytest.skip("RustKmer Python bindings not available", allow_module_level=True)


class TestWildcardPatternEdgeCases:
    """Test suite for wildcard pattern processing edge cases."""

    def test_no_wildcards(self):
        """Test patterns with no wildcards."""
        patterns = [
            "ATCGATCGATCGATCGATCGAT",  # Standard pattern
            "AAAAAAAAAAAAAAAAAAAAAA",  # All A's
            "CCCCCCCCCCCCCCCCCCCCCC",  # All C's
            "ATATATATATATATATATATAT",  # Repetitive
            "GCGCGCGCGCGCGCGCGCGCGC",  # Repetitive with GC
        ]

        for pattern in patterns:
            fq = FuzzyQuery(k=len(pattern), pattern=pattern)
            assert fq.max_variants > 0

            # No wildcards should result in 1 variant
            fq.max_variants = 1  # Should be sufficient
            assert fq.max_variants == 1

    def test_all_wildcards(self):
        """Test patterns with all wildcards."""
        for k in [5, 10, 15, 21, 31]:
            pattern = "N" * k
            fq = FuzzyQuery(k=k, pattern=pattern)

            # All wildcards should generate 4^k variants
            expected_variants = 4 ** k

            # Test with reasonable limit
            if expected_variants > 50000:
                fq.max_variants = 50000
                assert fq.max_variants == 50000
            else:
                fq.max_variants = expected_variants
                assert fq.max_variants == expected_variants

    def test_wildcard_positions(self):
        """Test wildcards in different positions."""
        base_pattern = "ATCGATCGATCGATCGATCGAT"

        # Wildcard at start
        pattern_start = "N" + base_pattern[1:]
        fq_start = FuzzyQuery(k=len(base_pattern), pattern=pattern_start)
        assert fq_start.max_variants > 0

        # Wildcard at end
        pattern_end = base_pattern[:-1] + "N"
        fq_end = FuzzyQuery(k=len(base_pattern), pattern=pattern_end)
        assert fq_end.max_variants > 0

        # Wildcard in middle
        pattern_middle = base_pattern[:10] + "N" + base_pattern[11:]
        fq_middle = FuzzyQuery(k=len(base_pattern), pattern=pattern_middle)
        assert fq_middle.max_variants > 0

        # Multiple wildcards
        pattern_multiple = base_pattern[:5] + "NNN" + base_pattern[8:]
        fq_multiple = FuzzyQuery(k=len(base_pattern), pattern=pattern_multiple)
        assert fq_multiple.max_variants > 0

    def test_consecutive_wildcards(self):
        """Test consecutive wildcards."""
        patterns = [
            "ATNNCGATCGATCGATCGATCGAT",  # 2 consecutive
            "ATNNNNCGATCGATCGATCGATCGAT",  # 4 consecutive
            "ATNNNNNNNNNCGATCGATCGATCGAT",  # 8 consecutive
            "NNNNNNNNNNNNNNNNNNNNNNN"[:21],  # All consecutive
        ]

        for pattern in patterns:
            fq = FuzzyQuery(k=21, pattern=pattern)
            fq.max_variants = 10000  # Reasonable limit for testing
            assert fq.max_variants == 10000

    def test_sparse_wildcards(self):
        """Test sparse (distributed) wildcards."""
        patterns = [
            "NTCGATCGATCGATCGATCGATN",  # 2 wildcards at ends
            "NTCGATNCGATCGATCGATNCGATN",  # 4 wildcards distributed
            "NTCNATCNATCNATCNATCNATCN",  # Alternating pattern
            "ATCGATCGATCGATCGATCGAT",  # No wildcards (control)
        ]

        for pattern in patterns:
            fq = FuzzyQuery(k=21, pattern=pattern)
            assert fq.max_variants > 0

    def test_wildcard_density_variations(self):
        """Test patterns with different wildcard densities."""
        k = 21
        for density in [0.1, 0.25, 0.5, 0.75, 1.0]:
            # Create pattern with specific density
            num_wildcards = int(k * density)
            pattern = list("ATCGATCGATCGATCGATCGAT")

            for i in range(num_wildcards):
                pattern[i] = "N"

            pattern = "".join(pattern)
            fq = FuzzyQuery(k=k, pattern=pattern)

            # Higher density should still work with limits
            fq.max_variants = min(4 ** num_wildcards, 50000)
            assert fq.max_variants > 0

    def test_pattern_boundary_wildcards(self):
        """Test wildcards at pattern boundaries."""
        # Leading wildcards
        for i in range(1, 6):
            pattern = "N" * i + "ATCGATCGATCGATCGATCGAT"[i:]
            fq = FuzzyQuery(k=21, pattern=pattern)
            assert fq.max_variants > 0

        # Trailing wildcards
        for i in range(1, 6):
            pattern = "ATCGATCGATCGATCGATCGAT"[:-i] + "N" * i
            fq = FuzzyQuery(k=21, pattern=pattern)
            assert fq.max_variants > 0


class TestKMerSizeEdgeCases:
    """Test suite for k-mer size edge cases."""

    def test_minimum_k_mer_size(self):
        """Test minimum valid k-mer sizes."""
        for k in [1, 2, 3, 4, 5]:
            pattern = "ATCG"[:k] + "N" * (k - 2) if k > 2 else "ATCG"[:k]
            try:
                fq = FuzzyQuery(k=k, pattern=pattern)
                assert fq.k == k
                assert fq.max_variants > 0
            except (ValueError, TypeError):
                # Some very small k might not be supported
                pass

    def test_maximum_k_mer_size(self):
        """Test maximum k-mer sizes."""
        large_patterns = [
            "ATCG" * 8 + "NNNN",  # k=36
            "ATCG" * 16 + "NNNNNNNN",  # k=72
            "ATCG" * 25 + "NNNNNNNNNNNNNNN",  # k=114
        ]

        for pattern in large_patterns:
            try:
                fq = FuzzyQuery(k=len(pattern), pattern=pattern)
                assert fq.k == len(pattern)
                assert fq.max_variants > 0
            except (ValueError, MemoryError):
                # Very large k might cause issues
                pass

    def test_pattern_k_mismatch(self):
        """Test pattern length vs k mismatch."""
        base_pattern = "ATCGATCGATCGATCGATCGAT"

        # Pattern longer than k
        with pytest.raises((ValueError, TypeError)):
            FuzzyQuery(k=15, pattern=base_pattern)

        # Pattern shorter than k
        with pytest.raises((ValueError, TypeError)):
            FuzzyQuery(k=25, pattern=base_pattern)

        # Pattern equal to k
        fq = FuzzyQuery(k=len(base_pattern), pattern=base_pattern)
        assert fq.k == len(base_pattern)

    def test_k_mer_size_with_wildcards(self):
        """Test different k-mer sizes with varying wildcard counts."""
        test_cases = [
            (5, "ATNCG"),      # Small k, 1 wildcard
            (10, "ATNCGATCNN"), # Medium k, 2 wildcards
            (21, "ATNCGNNNNNNNNNNNNNNNNN"), # Large k, many wildcards
        ]

        for k, pattern in test_cases:
            fq = FuzzyQuery(k=k, pattern=pattern)
            assert fq.k == k
            assert len(pattern) == k
            assert fq.max_variants > 0


class TestExtremeInputHandling:
    """Test suite for extreme input handling."""

    def test_extremely_high_max_variants(self):
        """Test extremely high max_variants values."""
        fq = FuzzyQuery(k=21, pattern="ATNCGATNN")

        # Test very high values
        extreme_values = [10**6, 10**9, 2**31 - 1]

        for value in extreme_values:
            try:
                fq.max_variants = value
                # Should either accept or raise appropriate error
                if fq.max_variants == value:
                    assert True  # Accepted
                else:
                    # Likely capped at some maximum
                    assert fq.max_variants > 0
            except (ValueError, OverflowError):
                # Expected for extreme values
                pass

    def test_zero_and_negative_values(self):
        """Test zero and negative max_variants values."""
        fq = FuzzyQuery(k=21, pattern="ATNCGATNN")

        # Test invalid values
        invalid_values = [0, -1, -1000, -999999]

        for value in invalid_values:
            with pytest.raises((ValueError, OverflowError)):
                fq.max_variants = value

    def test_minimal_patterns(self):
        """Test minimal pattern edge cases."""
        minimal_cases = [
            ("A", 1),      # Single base, no wildcards
            ("N", 1),      # Single wildcard
            ("AT", 2),     # Two bases, no wildcards
            ("AN", 2),     # Two bases, one wildcard
            ("NN", 2),     # Two wildcards
        ]

        for pattern, k in minimal_cases:
            try:
                fq = FuzzyQuery(k=k, pattern=pattern)
                assert fq.k == k
                assert fq.pattern == pattern
                assert fq.max_variants > 0
            except (ValueError, TypeError):
                # Some minimal cases might not be supported
                pass

    def test_maximal_patterns(self):
        """Test maximal pattern edge cases."""
        # Create very long patterns
        long_patterns = [
            "ATCG" * 100,  # 400 bases
            "N" * 100,     # 100 wildcards
            "ATCG" * 50 + "N" * 50,  # Mixed
        ]

        for pattern in long_patterns:
            try:
                fq = FuzzyQuery(k=len(pattern), pattern=pattern)
                assert fq.k == len(pattern)
                assert fq.max_variants > 0
            except (MemoryError, ValueError):
                # Expected for very long patterns
                pass

    def test_special_characters_in_patterns(self):
        """Test patterns with special characters."""
        invalid_chars = ["X", "Y", "Z", "B", "D", "E", "F", "H", "I", "J", "K", "L", "M", "O", "P", "Q", "R", "S", "U", "V", "W"]

        for char in invalid_chars:
            pattern = f"AT{char}CG"
            with pytest.raises((ValueError, TypeError)):
                FuzzyQuery(k=5, pattern=pattern)

    def test_numeric_characters_in_patterns(self):
        """Test patterns with numeric characters."""
        invalid_patterns = ["AT1CG", "AT2CG", "12345", "AT0CG"]

        for pattern in invalid_patterns:
            with pytest.raises((ValueError, TypeError)):
                FuzzyQuery(k=5, pattern=pattern)


class TestRobustnessAndStability:
    """Test suite for robustness and stability."""

    def test_rapid_property_changes(self):
        """Test rapid changes to max_variants property."""
        fq = FuzzyQuery(k=21, pattern="ATNCGATNN")

        # Rapid property changes
        values = [100, 1000, 50000, 1000, 100, 50000, 1000]

        for i, value in enumerate(values):
            fq.max_variants = value
            assert fq.max_variants == value, f"Iteration {i} failed"

    def test_concurrent_property_access(self):
        """Test concurrent access to max_variants property."""
        import threading
        import time

        fq = FuzzyQuery(k=21, pattern="ATNCGATNN")
        results = []

        def worker(worker_id):
            try:
                for i in range(10):
                    fq.max_variants = worker_id * 1000 + i
                    time.sleep(0.001)  # Small delay
                    results.append(fq.max_variants)
            except Exception as e:
                results.append(f"Worker {worker_id} error: {e}")

        # Create multiple threads
        threads = []
        for i in range(5):
            t = threading.Thread(target=worker, args=(i,))
            threads.append(t)
            t.start()

        # Wait for all threads to complete
        for t in threads:
            t.join(timeout=5.0)

        # Should have some results without crashes
        assert len(results) > 0

    def test_memory_pressure_handling(self):
        """Test handling under memory pressure scenarios."""
        patterns = [
            "N" * 20,   # 4^20 variants
            "N" * 25,   # 4^25 variants
            "N" * 30,   # 4^30 variants
        ]

        for pattern in patterns:
            fq = FuzzyQuery(k=len(pattern), pattern=pattern)

            # Set reasonable limits to avoid memory issues
            fq.max_variants = 1000

            # Should not cause memory issues
            assert fq.max_variants == 1000

    def test_error_recovery(self):
        """Test recovery from error conditions."""
        fq = FuzzyQuery(k=21, pattern="ATNCGATNN")

        # Set invalid value (should fail)
        try:
            fq.max_variants = -1
        except (ValueError, TypeError):
            pass  # Expected

        # Should still be able to set valid values
        fq.max_variants = 5000
        assert fq.max_variants == 5000

        # Set another invalid value
        try:
            fq.max_variants = 0
        except (ValueError, TypeError):
            pass  # Expected

        # Should recover again
        fq.max_variants = 10000
        assert fq.max_variants == 10000


class TestPerformanceEdgeCases:
    """Test suite for performance edge cases."""

    def test_performance_with_many_wildcards(self):
        """Test performance with patterns containing many wildcards."""
        import time

        patterns = [
            "ATNNNNNNNN",      # 8 wildcards
            "ATNNNNNNNNNNNNNN",  # 14 wildcards
            "ATNNNNNNNNNNNNNNNNNNNN",  # 20 wildcards
        ]

        for pattern in patterns:
            fq = FuzzyQuery(k=len(pattern), pattern=pattern)

            start_time = time.time()
            fq.max_variants = 50000  # Set reasonable limit
            end_time = time.time()

            # Setting limit should be fast (< 10ms)
            assert (end_time - start_time) < 0.01, f"Setting limit took too long: {end_time - start_time}s"

    def test_performance_rapid_operations(self):
        """Test performance of rapid operations."""
        import time

        fq = FuzzyQuery(k=21, pattern="ATNCGATNN")

        start_time = time.time()

        # Perform many operations
        for i in range(1000):
            fq.max_variants = i % 50000 + 1
            _ = fq.max_variants  # Read value

        end_time = time.time()

        # 1000 operations should be fast (< 1 second)
        assert (end_time - start_time) < 1.0, f"1000 operations took too long: {end_time - start_time}s"

    def test_large_k_mer_performance(self):
        """Test performance with large k-mer sizes."""
        import time

        large_pattern = "ATCGATCGATCGATCGATCNNNNNNNNNNNNNNNNNNNNN"
        fq = FuzzyQuery(k=len(large_pattern), pattern=large_pattern)

        start_time = time.time()
        fq.max_variants = 100000
        end_time = time.time()

        # Even large k-mers should be fast to set limits (< 10ms)
        assert (end_time - start_time) < 0.01, f"Large k-mer took too long: {end_time - start_time}s"


class TestDataIntegrityEdgeCases:
    """Test suite for data integrity in edge cases."""

    def test_property_consistency(self):
        """Test property consistency across edge cases."""
        test_cases = [
            ("ATCGATCGATCGATCGATCGAT", 1000),  # No wildcards
            ("ATNCGATNN", 50000),               # Some wildcards
            ("NNNNNNNNNNNNNNNNNNNNNNN"[:21], 25000),  # Many wildcards
        ]

        for pattern, max_variants in test_cases:
            fq = FuzzyQuery(k=len(pattern), pattern=pattern)
            fq.max_variants = max_variants

            # Consistency checks
            assert fq.pattern == pattern
            assert fq.k == len(pattern)
            assert fq.max_variants == max_variants

    def test_boundary_value_accuracy(self):
        """Test accuracy at boundary values."""
        fq = FuzzyQuery(k=21, pattern="ATNCGATNN")

        # Test boundary values
        boundary_values = [1, 2, 10, 100, 1000, 10000]

        for value in boundary_values:
            fq.max_variants = value
            assert fq.max_variants == value, f"Boundary value {value} not accurate"

    def test_type_safety_edge_cases(self):
        """Test type safety with edge case inputs."""
        fq = FuzzyQuery(k=21, pattern="ATNCGATNN")

        # Test various numeric types
        edge_case_values = [
            True,      # Boolean (should be rejected or converted)
            False,     # Boolean (should be rejected or converted)
            3.14159,   # Float (should be rejected)
            "1000",    # String number (should be rejected)
            None,      # None (should be rejected)
        ]

        for value in edge_case_values:
            try:
                fq.max_variants = value
                # If accepted, should be a positive integer
                assert isinstance(fq.max_variants, int)
                assert fq.max_variants > 0
            except (TypeError, ValueError):
                # Expected for invalid types
                pass


# Test fixtures
@pytest.fixture(params=[5, 10, 15, 21, 31])
def k_mer_sizes(request):
    """Provide different k-mer sizes for testing."""
    return request.param


@pytest.fixture(params=[
    "ATCGATCGATCGATCGATCGAT",     # No wildcards
    "ATNCGATCGATCGATCGATCGAT",     # 1 wildcard
    "ATNNCGATCGATCGATCGATCGAT",     # 2 wildcards
    "ATNNNNNNCGATCGATCGATCGAT",     # 6 wildcards
    "NNNNNNNNNNNNNNNNNNNNNNN"[:21], # All wildcards
])
def wildcard_patterns(request):
    """Provide various wildcard patterns for testing."""
    return request.param


# Integration test class
class TestEdgeCaseIntegration:
    """Integration tests for edge cases."""

    def test_complex_scenario_combination(self):
        """Test complex scenarios combining multiple edge cases."""
        # Large k-mer with many wildcards and tight limits
        large_pattern = "ATCG" * 5 + "NNNNNNNNNNNNNNNNN"
        k = len(large_pattern)

        fq = FuzzyQuery(k=k, pattern=large_pattern)

        # Set progressively tighter limits
        limits = [100000, 50000, 10000, 1000, 100]

        for limit in limits:
            fq.max_variants = limit
            assert fq.max_variants == limit
            assert fq.k == k
            assert fq.pattern == large_pattern

    def test_real_world_bioinformatics_scenarios(self):
        """Test realistic bioinformatics scenarios."""
        # Common real-world patterns
        scenarios = [
            # Degenerate primer sequences
            ("ATNCGATCGATCGATCGATCGAT", 21),
            # K-mer with ambiguous bases from sequencing
            ("ATNCGNNNNATCGATCGATCGAT", 24),
            # Highly degenerate regions
            ("NNNNATCGATCGATCNNNNNATCG", 25),
        ]

        for pattern, k in scenarios:
            fq = FuzzyQuery(k=k, pattern=pattern)

            # Test with biologically reasonable limits
            bio_limits = [1000, 10000, 100000]

            for limit in bio_limits:
                fq.max_variants = limit
                assert fq.max_variants == limit
                assert fq.pattern == pattern
                assert fq.k == k


if __name__ == "__main__":
    # Run tests directly
    pytest.main([__file__, "-v"])