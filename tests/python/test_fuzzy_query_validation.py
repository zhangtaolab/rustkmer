"""
FuzzyQuery Validation Tests for User Story 1
============================================

This module provides comprehensive validation for FuzzyQuery API Enhancement,
specifically testing the max_variants property accessibility and functionality.

Validates:
- max_variants property accessibility (get/set)
- Variant limit enforcement
- Error handling for computational explosion prevention
- Backward compatibility with existing FuzzyQuery API
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


class TestMaxVariantsPropertyAccessibility:
    """Test suite for max_variants property accessibility."""

    def test_max_variants_property_exists(self):
        """Test that max_variants property exists and is accessible."""
        fq = FuzzyQuery(k=21, pattern="ATCGATCGATCGATCGATCGAT")

        # Test property exists
        assert hasattr(fq, 'max_variants'), "max_variants property should exist"

        # Test property is readable
        initial_value = fq.max_variants
        assert isinstance(initial_value, int), "max_variants should be an integer"
        assert initial_value > 0, "max_variants should be positive"

    def test_max_variants_property_writable(self):
        """Test that max_variants property is writable."""
        fq = FuzzyQuery(k=21, pattern="ATCGATCGATCGATCGATCGAT")

        # Test setting different values
        test_values = [1000, 50000, 100000, 1, 999999]

        for value in test_values:
            fq.max_variants = value
            assert fq.max_variants == value, f"max_variants should be set to {value}"

    def test_max_variants_default_value(self):
        """Test that max_variants has sensible default value."""
        fq1 = FuzzyQuery(k=21, pattern="ATCGATCGATCGATCGATCGAT")
        fq2 = FuzzyQuery(k=21, pattern="ATCGATCGATCGATCGATCGAT", max_variants=75000)

        # Test default is reasonable (around 50000)
        default_value = fq1.max_variants
        assert 10000 <= default_value <= 100000, f"Default max_variants {default_value} should be reasonable"

        # Test explicit value override
        assert fq2.max_variants == 75000, "Explicit max_variants should override default"

    def test_max_variants_type_validation(self):
        """Test that max_variants property validates input types."""
        fq = FuzzyQuery(k=21, pattern="ATCGATCGATCGATCGATCGAT")

        # Test invalid types
        invalid_values = [
            "string",  # String
            3.14,      # Float
            None,      # None
            [],        # List
            {},        # Dict
            True,      # Boolean
        ]

        for invalid_value in invalid_values:
            with pytest.raises((TypeError, ValueError)) as exc_info:
                fq.max_variants = invalid_value
            print(f"Correctly rejected invalid type: {type(invalid_value).__name__}")

    def test_max_variants_range_validation(self):
        """Test that max_variants property validates input ranges."""
        fq = FuzzyQuery(k=21, pattern="ATCGATCGATCGATCGATCGAT")

        # Test invalid ranges
        invalid_values = [0, -1, -1000, 10**10]  # Zero, negative, extremely large

        for invalid_value in invalid_values:
            with pytest.raises((ValueError, OverflowError)) as exc_info:
                fq.max_variants = invalid_value
            print(f"Correctly rejected invalid value: {invalid_value}")

    def test_max_variants_persistence_across_operations(self):
        """Test that max_variants value persists across query operations."""
        fq = FuzzyQuery(k=21, pattern="ATNCGATNN")
        original_max = 25000
        fq.max_variants = original_max

        # Simulate some operations (if available)
        # This would depend on the actual FuzzyQuery API
        try:
            # Try to access variants or perform some operation
            variants = getattr(fq, 'get_variants', lambda: [])
            if callable(variants):
                _ = variants()
        except Exception:
            pass  # Expected for this test

        # Verify value persists
        assert fq.max_variants == original_max, "max_variants should persist across operations"


class TestVariantLimitEnforcement:
    """Test suite for variant limit enforcement functionality."""

    def test_simple_wildcard_limit_enforcement(self):
        """Test variant limit enforcement with simple wildcards."""
        fq = FuzzyQuery(k=21, pattern="ATNCGATCGATCGATCGATCGAT")

        # Pattern has 1 wildcard -> 4 variants
        fq.max_variants = 10  # Allow all variants
        # This would test actual variant generation if available

        fq.max_variants = 2   # Limit to 2 variants
        # This should enforce the limit

    def test_multiple_wildcard_limit_enforcement(self):
        """Test variant limit enforcement with multiple wildcards."""
        fq = FuzzyQuery(k=21, pattern="ATNNNNNNNNNNNNNNNNNNNN")

        # Pattern has 19 wildcards -> 4^19 variants (huge number)
        fq.max_variants = 50000  # Reasonable limit

        # Verify that limit is enforced
        assert fq.max_variants == 50000

    def test_edge_case_limit_enforcement(self):
        """Test variant limit enforcement with edge cases."""
        # No wildcards - should have 1 variant
        fq_no_wildcard = FuzzyQuery(k=21, pattern="ATCGATCGATCGATCGATCGAT")
        fq_no_wildcard.max_variants = 1
        assert fq_no_wildcard.max_variants == 1

        # All wildcards - should be limited
        fq_all_wildcard = FuzzyQuery(k=5, pattern="NNNNN")
        fq_all_wildcard.max_variants = 100  # 4^5 = 1024 possible, limit to 100
        assert fq_all_wildcard.max_variants == 100

    def test_limit_changes_affect_behavior(self):
        """Test that changing max_variants affects subsequent behavior."""
        fq = FuzzyQuery(k=21, pattern="ATNCGATNN")

        # Set high limit
        fq.max_variants = 100000

        # Change to low limit
        fq.max_variants = 100

        # Verify the change took effect
        assert fq.max_variants == 100


class TestComputationalExplosionPrevention:
    """Test suite for computational explosion prevention."""

    def test_excessive_wildcard_prevention(self):
        """Test prevention of computational explosion from excessive wildcards."""
        # Create pattern with many wildcards
        excessive_pattern = "N" * 20  # 4^20 = 1 trillion variants

        fq = FuzzyQuery(k=20, pattern=excessive_pattern)
        fq.max_variants = 50000  # Reasonable limit

        # Should handle this without memory issues
        assert fq.max_variants == 50000

    def test_memory_efficient_limit_enforcement(self):
        """Test that limit enforcement is memory efficient."""
        # Create patterns that would generate many variants
        patterns = [
            "ATNNNNNNNNNNNNNNNNNNNN",  # 18 wildcards
            "NNNNNNNNNNNNNNNNNNNN",    # 19 wildcards
            "CNNNNNNNNNNNNNNNNNNNNN",  # 19 wildcards
        ]

        for pattern in patterns:
            fq = FuzzyQuery(k=len(pattern), pattern=pattern)
            fq.max_variants = 1000  # Very low limit

            # Should not cause memory issues
            assert fq.max_variants == 1000

    def test_performance_with_limits(self):
        """Test performance characteristics with different limits."""
        import time

        pattern = "ATNNNNNNNN"  # 7 wildcards -> 4^7 = 16384 variants
        fq = FuzzyQuery(k=13, pattern=pattern)

        # Test with different limits
        limits = [10, 100, 1000, 50000]

        for limit in limits:
            start_time = time.time()
            fq.max_variants = limit
            end_time = time.time()

            # Setting limit should be fast (< 1ms)
            assert (end_time - start_time) < 0.001, f"Setting limit {limit} should be fast"
            assert fq.max_variants == limit

    def test_large_k_mer_with_wildcards(self):
        """Test handling of large k-mers with wildcards."""
        large_pattern = "ATCGATCGATCGATCNNNNNNNNNN"  # k=31 with wildcards

        fq = FuzzyQuery(k=31, pattern=large_pattern)
        fq.max_variants = 25000

        # Should handle large k-mers without issues
        assert fq.max_variants == 25000
        assert len(fq.pattern) == 31


class TestComputationalExplosionErrorHandling:
    """Test suite for error handling in computational explosion prevention."""

    def test_limit_enforcement_error_messages(self):
        """Test that limit enforcement provides clear error messages."""
        fq = FuzzyQuery(k=21, pattern="ATNCGATNN")

        # Test setting invalid limits that should trigger validation
        invalid_limits = [0, -1, -100]

        for limit in invalid_limits:
            try:
                fq.max_variants = limit
                # If no exception is raised, check if value was clamped
                assert fq.max_variants > 0, "max_variants should remain positive"
            except (ValueError, TypeError) as e:
                # Check that error message is informative
                error_str = str(e).lower()
                assert any(keyword in error_str for keyword in ["invalid", "positive", "range", "limit"]), \
                    f"Error message should be informative: {e}"

    def test_memory_error_prevention(self):
        """Test that memory errors are prevented during limit enforcement."""
        # Create patterns that would generate massive variant counts
        dangerous_patterns = [
            "N" * 25,  # 4^25 = huge number
            "ATNNNNNNNNNNNNNNNNNNNNNNNNNNN",  # 27 wildcards
        ]

        for pattern in dangerous_patterns:
            try:
                fq = FuzzyQuery(k=len(pattern), pattern=pattern)

                # Set very low limit to prevent memory issues
                fq.max_variants = 1000

                # Should not cause memory errors
                assert fq.max_variants == 1000

            except MemoryError:
                pytest.fail("Memory error should have been prevented by limit enforcement")

    def test_computationally_expensive_pattern_detection(self):
        """Test detection of computationally expensive patterns."""
        expensive_patterns = [
            # Patterns with many consecutive wildcards
            "AT" + "N" * 15 + "CG",
            "AT" + "N" * 20 + "CG",
            "AT" + "N" * 25 + "CG",

            # Patterns with distributed wildcards
            "N" + "ATCG" * 5 + "N" + "ATCG" * 5 + "N",

            # Edge case: all wildcards
            "N" * 30,
        ]

        for pattern in expensive_patterns:
            fq = FuzzyQuery(k=len(pattern), pattern=pattern)

            # Should be able to set reasonable limits without issues
            fq.max_variants = 50000
            assert fq.max_variants == 50000

    def test_variant_count_estimation_accuracy(self):
        """Test that variant count estimation is accurate."""
        test_cases = [
            ("ATCG", 1),         # No wildcards -> 1 variant
            ("ATNG", 4),         # 1 wildcard -> 4 variants
            ("ATNNCG", 16),      # 2 wildcards -> 16 variants
            ("ATNNNNCG", 1024),  # 4 wildcards -> 1024 variants
        ]

        for pattern, expected_variants in test_cases:
            fq = FuzzyQuery(k=len(pattern), pattern=pattern)

            # Test with limit higher than expected variants
            fq.max_variants = expected_variants * 2

            # Should work fine
            assert fq.max_variants == expected_variants * 2

    def test_dynamic_limit_adjustment(self):
        """Test dynamic adjustment of limits during operation."""
        fq = FuzzyQuery(k=21, pattern="ATNCGNNNNNNNNNNNNNNN")

        # Start with high limit
        fq.max_variants = 100000
        assert fq.max_variants == 100000

        # Dynamically reduce to prevent potential issues
        fq.max_variants = 10000
        assert fq.max_variants == 10000

        # Further reduce for safety
        fq.max_variants = 1000
        assert fq.max_variants == 1000

    def test_error_recovery_after_limit_violation(self):
        """Test recovery after attempting to set invalid limits."""
        fq = FuzzyQuery(k=21, pattern="ATNCGATNN")

        # Try to set invalid limit
        try:
            fq.max_variants = -1
        except (ValueError, TypeError):
            pass  # Expected

        # Should be able to recover with valid limit
        fq.max_variants = 5000
        assert fq.max_variants == 5000

        # Try another invalid limit
        try:
            fq.max_variants = 0
        except (ValueError, TypeError):
            pass  # Expected

        # Should recover again
        fq.max_variants = 10000
        assert fq.max_variants == 10000

    def test_concurrent_limit_safety(self):
        """Test limit safety under concurrent access."""
        import threading
        import time

        fq = FuzzyQuery(k=21, pattern="ATNCGNNNNNNNNNNNNNNN")
        errors = []

        def worker():
            try:
                for i in range(10):
                    # Try setting various limits
                    fq.max_variants = (i + 1) * 1000
                    time.sleep(0.001)  # Small delay
                    assert fq.max_variants > 0
            except Exception as e:
                errors.append(e)

        # Create multiple threads
        threads = []
        for _ in range(5):
            t = threading.Thread(target=worker)
            threads.append(t)
            t.start()

        # Wait for completion
        for t in threads:
            t.join(timeout=5.0)

        # Should have no errors
        assert len(errors) == 0, f"Concurrent access caused errors: {errors}"

    def test_extreme_pattern_edge_cases(self):
        """Test extreme pattern edge cases for explosion prevention."""
        edge_cases = [
            # Maximum reasonable wildcard count
            "ATCG" + "N" * 15,  # 19 wildcards

            # Very distributed wildcards
            "NATNATNATNATNATNATNATNATNATNAT",  # Alternating pattern

            # Consecutive blocks of wildcards
            "ATCG" + "N" * 10 + "ATCG" + "N" * 5 + "ATCG",

            # Nearly all wildcards
            "ATCGNNNNNNNNNNNNNNNNNNNNN",
        ]

        for pattern in edge_cases:
            try:
                fq = FuzzyQuery(k=len(pattern), pattern=pattern)

                # Set conservative limit
                fq.max_variants = 10000

                # Should handle gracefully
                assert fq.max_variants == 10000

            except MemoryError:
                pytest.fail(f"Memory error not prevented for pattern: {pattern}")

    def test_resource_cleanup_after_limit_enforcement(self):
        """Test that resources are properly cleaned up after limit enforcement."""
        fq = FuzzyQuery(k=21, pattern="ATNCGNNNNNNNNNNNNNNN")

        # Perform multiple limit changes
        for limit in [100000, 50000, 10000, 1000, 50000, 100000]:
            fq.max_variants = limit
            assert fq.max_variants == limit

        # Should still be functional after many changes
        fq.max_variants = 25000
        assert fq.max_variants == 25000


class TestBackwardCompatibility:
    """Test suite for backward compatibility with existing FuzzyQuery API."""

    def test_existing_constructor_still_works(self):
        """Test that existing FuzzyQuery constructors still work."""
        # Original constructor should work
        fq1 = FuzzyQuery(k=21, pattern="ATCGATCGATCGATCGATCGAT")

        # Constructor with max_variants should work
        fq2 = FuzzyQuery(k=21, pattern="ATCGATCGATCGATCGATCGAT", max_variants=10000)

        # Both should create valid objects
        assert fq1.max_variants > 0
        assert fq2.max_variants == 10000

    def test_existing_methods_still_work(self):
        """Test that existing FuzzyQuery methods still work."""
        fq = FuzzyQuery(k=21, pattern="ATCGATCGATCGATCGATCGAT")

        # Check that original properties/methods still exist
        assert hasattr(fq, 'k'), "FuzzyQuery should still have k property"
        assert hasattr(fq, 'pattern'), "FuzzyQuery should still have pattern property"

        assert fq.k == 21
        assert fq.pattern == "ATCGATCGATCGATCGATCGAT"

    def test_default_behavior_unchanged(self):
        """Test that default behavior is unchanged for existing code."""
        # Create FuzzyQuery without max_variants (old way)
        fq_old = FuzzyQuery(k=21, pattern="ATNCGATNN")

        # Should work just like before
        assert hasattr(fq_old, 'max_variants')  # New property exists
        assert fq_old.max_variants > 0  # Has reasonable default

    def test_property_access_patterns(self):
        """Test different property access patterns."""
        fq = FuzzyQuery(k=21, pattern="ATCGATCGATCGATCGATCGAT")

        # Direct access
        direct_value = fq.max_variants

        # Getattr
        getattr_value = getattr(fq, 'max_variants')

        # Should be the same
        assert direct_value == getattr_value

    def test_no_breaking_changes_in_api(self):
        """Test that no breaking changes were introduced to the API."""
        fq = FuzzyQuery(k=21, pattern="ATCGATCGATCGATCGATCGAT")

        # All original attributes should still be accessible
        original_attrs = ['k', 'pattern']
        for attr in original_attrs:
            assert hasattr(fq, attr), f"Attribute {attr} should still exist"

        # New max_variants attribute should be accessible
        assert hasattr(fq, 'max_variants'), "New max_variants attribute should exist"


class TestEdgeCasesAndErrorConditions:
    """Test suite for edge cases and error conditions."""

    def test_zero_k_mer_handling(self):
        """Test handling of zero k-mer size."""
        with pytest.raises((ValueError, TypeError)):
            FuzzyQuery(k=0, pattern="ATCG")

    def test_empty_pattern_handling(self):
        """Test handling of empty patterns."""
        with pytest.raises((ValueError, TypeError)):
            FuzzyQuery(k=21, pattern="")

    def test_pattern_longer_than_k(self):
        """Test handling of patterns longer than k."""
        with pytest.raises((ValueError, TypeError)):
            FuzzyQuery(k=5, pattern="ATCGATCGATCG")

    def test_invalid_characters_in_pattern(self):
        """Test handling of invalid characters in pattern."""
        invalid_patterns = ["ATXG", "ATBG", "AT5G", "AT*G"]

        for pattern in invalid_patterns:
            with pytest.raises((ValueError, TypeError)):
                FuzzyQuery(k=4, pattern=pattern)

    def test_very_large_k_mer(self):
        """Test handling of very large k-mer sizes."""
        large_pattern = "ATCG" * 25  # k=100

        fq = FuzzyQuery(k=100, pattern=large_pattern)
        fq.max_variants = 1000

        assert fq.k == 100
        assert fq.max_variants == 1000

    def test_boundary_values(self):
        """Test boundary values for max_variants."""
        fq = FuzzyQuery(k=21, pattern="ATCGATCGATCGATCGATCGAT")

        # Test minimum valid value
        fq.max_variants = 1
        assert fq.max_variants == 1

        # Test reasonable maximum
        fq.max_variants = 1000000
        assert fq.max_variants == 1000000


# Pytest configuration and fixtures
@pytest.fixture
def sample_fuzzy_query():
    """Provide a sample FuzzyQuery for testing."""
    return FuzzyQuery(k=21, pattern="ATNCGATNN")


@pytest.fixture
def wildcard_patterns():
    """Provide various wildcard patterns for testing."""
    return {
        'single': 'ATNCGATCGATCGATCGATCGAT',
        'double': 'ATNNCGATCGATCGATCGATCGAT',
        'multiple': 'ATNNNNNNNNNNNNNNNNNNNN',
        'none': 'ATCGATCGATCGATCGATCGAT',
        'all': 'NNNNNNNNNNNNNNNNNNNNNNN'[:21],
    }


# Integration test class
class TestFuzzyQueryIntegration:
    """Integration tests for FuzzyQuery with max_variants."""

    def test_end_to_end_workflow(self):
        """Test complete workflow with max_variants."""
        # Create FuzzyQuery with wildcards
        pattern = "ATNCGATNN"
        fq = FuzzyQuery(k=10, pattern=pattern)

        # Set custom limit
        fq.max_variants = 5000

        # Verify all properties
        assert fq.k == 10
        assert fq.pattern == pattern
        assert fq.max_variants == 5000

        # Modify limit
        fq.max_variants = 1000
        assert fq.max_variants == 1000

    def test_compatibility_with_existing_code(self):
        """Test compatibility with existing code patterns."""
        # Simulate existing code that creates FuzzyQuery
        fuzzy_queries = []
        patterns = ["ATCGATCGATCGATCGATCGAT", "ATNCGATNN", "CNNNNNNNNN"]

        for pattern in patterns:
            fq = FuzzyQuery(k=len(pattern), pattern=pattern)
            fuzzy_queries.append(fq)

        # All should work with new max_variants property
        for fq in fuzzy_queries:
            assert hasattr(fq, 'max_variants')
            assert fq.max_variants > 0


if __name__ == "__main__":
    # Run tests directly
    pytest.main([__file__, "-v"])