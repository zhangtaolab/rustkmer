#!/usr/bin/env python3
"""
FuzzyQuery API enhancement tests for Python API improvements feature.

These tests should FAIL before implementation to demonstrate TDD approach.
Test Goal: Verify max_variants property is accessible as Python property (not just method).
"""

import pytest
import sys
import os

# Add the src directory to Python path for importing rustkmer
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../src'))

try:
    import rustkmer
    from rustkmer import FuzzyQuery
except ImportError as e:
    pytest.skip(f"RustKmer Python bindings not available: {e}", allow_module_level=True)


class TestMaxVariantsPropertyAccessibility:
    """Test max_variants property accessibility (should FAIL before implementation)."""

    def test_max_variants_property_readable(self):
        """Test that max_variants property is readable as Python property."""
        # Create a FuzzyQuery with known max_variants
        fq = FuzzyQuery("ATGCG", 5, 0, 5000)

        # This should work: access max_variants as a property
        # Currently this FAILS because max_variants is only accessible as get_max_variants() method
        assert hasattr(fq, 'max_variants'), "FuzzyQuery should have max_variants property"
        assert fq.max_variants == 5000, f"Expected max_variants=5000, got {fq.max_variants}"

    def test_max_variants_property_writable(self):
        """Test that max_variants property is writable as Python property."""
        # Create a FuzzyQuery with default max_variants
        fq = FuzzyQuery("ATGCG", 5, 0, 10000)

        # This should work: modify max_variants as a property
        # Currently this FAILS because there's no setter for max_variants property
        fq.max_variants = 15000
        assert fq.max_variants == 15000, f"Expected max_variants=15000 after modification, got {fq.max_variants}"

    def test_max_variants_property_with_validation(self):
        """Test that max_variants property includes validation."""
        fq = FuzzyQuery("ATGCG", 5, 0, 10000)

        # Should fail validation: max_variants = 0 is invalid
        with pytest.raises(ValueError, match="max_variants must be between 1 and"):
            fq.max_variants = 0

        # Should fail validation: max_variants > 1,000,000 is invalid
        with pytest.raises(ValueError, match="max_variants must be between 1 and"):
            fq.max_variants = 2_000_000

        # Valid value should work
        fq.max_variants = 100000
        assert fq.max_variants == 100000


class TestVariantLimitEnforcement:
    """Test variant limit enforcement with configurable max_variants property."""

    def test_variant_limit_prevents_computational_explosion(self):
        """Test that variant limit prevents computational explosion."""
        # Create query with many wildcards (would generate 4^6 = 4096 variants)
        fq = FuzzyQuery("ATGCGNNNNNN", 12, 0, 1000)  # max_variants=1000

        # This should fail because 4096 > 1000
        with pytest.raises(Exception, match="exceeding max_variants"):
            fq.expand_wildcards()

    def test_variant_limit_enforcement_dynamic(self):
        """Test that variant limit can be modified dynamically."""
        fq = FuzzyQuery("ATGCGNNNNNN", 12, 0, 1000)  # max_variants=1000

        # Initially should fail
        with pytest.raises(Exception, match="exceeding max_variants"):
            fq.expand_wildcards()

        # Increase limit and it should work
        fq.max_variants = 5000
        variants = fq.expand_wildcards()
        assert len(variants) == 4096, f"Expected 4096 variants, got {len(variants)}"


class TestErrorMessagesForLimits:
    """Test clear error messages when variant limits are exceeded."""

    def test_clear_error_message_for_limit_exceeded(self):
        """Test clear error message when max_variants limit is exceeded."""
        fq = FuzzyQuery("ATGCGNNNNNN", 12, 0, 1000)

        try:
            fq.expand_wildcards()
            assert False, "Should have raised an exception"
        except Exception as e:
            error_msg = str(e)
            assert "exceeding max_variants" in error_msg, f"Error message should mention max_variants: {error_msg}"
            assert "4096" in error_msg, f"Error message should include variant count: {error_msg}"
            assert "1000" in error_msg, f"Error message should include limit: {error_msg}"

    def test_actionable_error_guidance(self):
        """Test that error messages provide actionable guidance."""
        fq = FuzzyQuery("ATGCGNNNNNNNNNNNNN", 20, 0, 10000)

        try:
            fq.expand_wildcards()
            assert False, "Should have raised an exception"
        except Exception as e:
            error_msg = str(e)
            # Error should suggest increasing max_variants
            assert any(keyword in error_msg.lower() for keyword in ["increase", "max_variants", "limit"]), \
                f"Error should provide actionable guidance: {error_msg}"


class TestBackwardCompatibility:
    """Test that changes maintain backward compatibility."""

    def test_existing_get_max_variants_method_still_works(self):
        """Test that existing get_max_variants() method still works for backward compatibility."""
        fq = FuzzyQuery("ATGCG", 5, 0, 7500)

        # Old method should still work
        assert fq.get_max_variants() == 7500

        # New property should also work
        assert fq.max_variants == 7500

        # Both should return same value
        assert fq.get_max_variants() == fq.max_variants


if __name__ == "__main__":
    pytest.main([__file__, "-v"])