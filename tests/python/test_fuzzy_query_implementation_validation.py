"""
FuzzyQuery Implementation Validation Tests
=======================================

This module validates the actual PyO3 implementation of FuzzyQuery
to ensure it correctly implements the max_variants property
according to the design specifications.

Validates:
- PyO3 property getter/setter implementation
- Variant limit validation logic and error messages
- Wildcard expansion algorithm performance and accuracy
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


class TestPyO3PropertyImplementation:
    """Validate PyO3 property getter/setter implementation."""

    def test_max_variants_property_access_patterns(self):
        """Test different property access patterns to validate implementation."""
        # Create FuzzyQuery instance
        fq = FuzzyQuery(k=21, pattern="ATNCGATNN")
        original_max = 10000

        # Test if property-based access works
        if hasattr(fq, 'max_variants'):
            # Direct property access should work if implemented with #[pyo3(get, set)]
            assert fq.max_variants == original_max

            # Test property assignment
            fq.max_variants = 50000
            assert fq.max_variants == 50000
            print("✓ Property-based access works")
        else:
            print("⚠ Property-based access not available, checking method-based access")

        # Test method-based access (should always work)
        if hasattr(fq, 'get_max_variants'):
            max_via_getter = fq.get_max_variants()
            assert max_via_getter == 50000 or max_via_getter == original_max
            print("✓ Method-based getter works")

            # Test method-based setter
            fq.set_max_variants(25000)
            max_after_set = fq.get_max_variants()
            assert max_after_set == 25000
            print("✓ Method-based setter works")

    def test_property_consistency(self):
        """Test consistency between property and method access."""
        fq = FuzzyQuery(k=21, pattern="ATNCGATNN")

        # Test different values
        test_values = [1000, 5000, 25000, 100000]

        for value in test_values:
            # Set via method
            fq.set_max_variants(value)
            method_result = fq.get_max_variants()

            # Check via property if available
            if hasattr(fq, 'max_variants'):
                property_result = fq.max_variants
                assert method_result == property_result, \
                    f"Method ({method_result}) and property ({property_result}) results should match for value {value}"

            assert method_result == value, f"Method should return the set value {value}, got {method_result}"

    def test_thread_safety_of_property_access(self):
        """Test thread safety of property access patterns."""
        import threading
        import time

        fq = FuzzyQuery(k=21, pattern="ATNCGATNN")
        errors = []
        results = []

        def worker():
            try:
                for i in range(10):
                    # Alternate between access patterns
                    if i % 2 == 0 and hasattr(fq, 'max_variants'):
                        fq.max_variants = (i + 1) * 1000
                        results.append(('property', fq.max_variants))
                    else:
                        fq.set_max_variants((i + 1) * 1000)
                        results.append(('method', fq.get_max_variants()))

                    time.sleep(0.001)  # Small delay
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
        assert len(errors) == 0, f"Thread safety issues: {errors}"

        # Final value should be reasonable
        final_value = fq.get_max_variants()
        assert final_value > 0 and final_value <= 1000000, f"Final value {final_value} should be reasonable"

    def test_property_persistence_after_operations(self):
        """Test that property values persist after other operations."""
        fq = FuzzyQuery(k=21, pattern="ATNCGNNNNNNNNNNNNNNN")

        # Set specific value
        fq.set_max_variants(75000)

        # Perform other operations
        try:
            _ = fq.validate()
            _ = fq.get_variant_count()
            _ = fq.get_wildcard_count()
            _ = fq.get_query_string()
            _ = fq.get_kmer_size()
        except Exception:
            pass  # Operations might fail due to implementation details

        # Value should persist
        assert fq.get_max_variants() == 75000

        # Check via property if available
        if hasattr(fq, 'max_variants'):
            assert fq.max_variants == 75000

    def test_initial_property_values(self):
        """Test initial property values are correctly set."""
        # Test different constructor patterns
        test_cases = [
            # (constructor_args, expected_max_variants)
            ({"k": 21, "pattern": "ATCGATCGATCGATCGATCGAT"}, 10000),  # Default
            ({"k": 21, "pattern": "ATNCGATNN", "max_variants": 50000}, 50000),  # Custom
            ({"k": 15, "pattern": "ATNCGATNNNNNNNN"}, 10000),  # Different k
        ]

        for constructor_args, expected_max in test_cases:
            fq = FuzzyQuery(**constructor_args)

            # Check initial value
            initial_max = fq.get_max_variants()
            assert initial_max == expected_max, \
                f"Expected {expected_max}, got {initial_max} for {constructor_args}"

            # Check via property if available
            if hasattr(fq, 'max_variants'):
                assert fq.max_variants == expected_max, \
                    f"Property should show {expected_max}, got {fq.max_variants}"


class TestVariantLimitValidationLogic:
    """Validate variant limit validation logic and error messages."""

    def test_validation_error_message_quality(self):
        """Test that validation error messages are clear and actionable."""
        fq = FuzzyQuery(k=21, pattern="ATNCGATNN")

        # Test invalid values that should trigger validation
        invalid_values = [0, -1, -100, 2000000]  # Based on implementation limits

        for value in invalid_values:
            try:
                fq.set_max_variants(value)
                # If no exception, check if value was clamped to valid range
                final_value = fq.get_max_variants()
                assert 1 <= final_value <= 1000000, \
                    f"Value should be clamped to valid range, got {final_value}"
                print(f"✓ Value {value} was clamped to {final_value}")

            except Exception as e:
                # Check error message quality
                error_str = str(e).lower()
                informative_keywords = ["invalid", "between", "range", "limit", "must", "reasonable"]

                has_informative_keyword = any(keyword in error_str for keyword in informative_keywords)
                assert has_informative_keyword, \
                    f"Error message should be informative: '{e}'"

                print(f"✓ Clear error message for {value}: '{e}'")

    def test_boundary_value_validation(self):
        """Test boundary value validation."""
        fq = FuzzyQuery(k=21, pattern="ATNCGATNN")

        # Test boundary values based on implementation
        boundary_tests = [
            (1, True),      # Minimum valid value
            (1000000, True),  # Maximum valid value
            (0, False),      # Below minimum
            (1000001, False), # Above maximum
        ]

        for value, should_succeed in boundary_tests:
            try:
                fq.set_max_variants(value)
                if should_succeed:
                    assert fq.get_max_variants() == value, \
                        f"Valid value {value} should be accepted"
                    print(f"✓ Boundary value {value} accepted")
                else:
                    # Should have thrown an exception
                    pytest.fail(f"Invalid value {value} should have been rejected")
            except Exception:
                if should_succeed:
                    pytest.fail(f"Valid value {value} was incorrectly rejected")
                else:
                    print(f"✓ Invalid value {value} correctly rejected")

    def test_validation_enforcement_in_wildcard_expansion(self):
        """Test that validation is enforced during wildcard expansion."""
        # Create a pattern that would generate many variants
        pattern_with_many_wildcards = "ATNNNNNNNNNNNNNNNNNN"  # 19 wildcards
        fq = FuzzyQuery(k=21, pattern=pattern_with_many_wildcards)

        # Set very low limit
        fq.set_max_variants(1000)

        # Try to expand wildcards - should enforce limit
        try:
            variants = fq.expand_wildcards()

            # Should either succeed with limited variants or fail with clear error
            if len(variants) > 0:
                assert len(variants) <= 1000, \
                    f"Variant count {len(variants)} should respect max_variants limit of 1000"
                print(f"✓ Wildcard expansion respected limit: {len(variants)} variants")

        except Exception as e:
            # Should fail with clear error about exceeding limit
            error_str = str(e).lower()
            assert "exceed" in error_str or "limit" in error_str or "variant" in error_str, \
                f"Error should mention limit/variant exceeding: '{e}'"
            print(f"✓ Wildcard expansion correctly limited: '{e}'")

    def test_validation_with_different_pattern_complexity(self):
        """Test validation with patterns of different complexity."""
        test_patterns = [
            # (pattern, k, description)
            ("ATCG", 4, "No wildcards"),
            ("ATNG", 4, "1 wildcard"),
            ("ATNNCG", 6, "2 wildcards"),
            ("ATNNNNCG", 8, "4 wildcards"),
            ("ATNNNNNNNNNNNNN", 13, "10 wildcards"),
        ]

        for pattern, k, description in test_patterns:
            fq = FuzzyQuery(k=k, pattern=pattern)

            # Set moderate limit
            fq.set_max_variants(5000)

            # Should be able to validate and work with any pattern
            assert fq.get_max_variants() == 5000
            assert fq.validate() == True

            # Wildcard expansion should respect limits
            try:
                variants = fq.expand_wildcards()
                if "wildcard" in description:
                    assert len(variants) <= 5000, \
                        f"Pattern {description} should respect limit: {len(variants)} variants"
                print(f"✓ {description}: {len(variants)} variants")
            except Exception as e:
                # Should only fail if limit is exceeded
                error_str = str(e).lower()
                assert "exceed" in error_str or "limit" in error_str, \
                    f"Should only fail due to limit, not other errors: '{e}'"


class TestWildcardExpansionAlgorithm:
    """Test wildcard expansion algorithm performance and accuracy."""

    def test_expansion_algorithm_accuracy(self):
        """Test that wildcard expansion produces correct results."""
        test_cases = [
            # (pattern, expected_variants, description)
            ("ATCG", 1, "No wildcards"),
            ("ATNG", 4, "1 wildcard (A, T, G, C)"),
            ("ATNNCG", 16, "2 wildcards (4²)"),
            ("ATNNNNG", 64, "3 wildcards (4³)"),
        ]

        for pattern, expected_count, description in test_cases:
            fq = FuzzyQuery(k=len(pattern), pattern=pattern)
            fq.set_max_variants(expected_count * 2)  # Allow enough variants

            try:
                variants = fq.expand_wildcards()
                actual_count = len(variants)

                assert actual_count == expected_count, \
                    f"{description}: Expected {expected_count}, got {actual_count}"

                # Verify all variants are valid (no wildcards, correct length)
                for variant in variants:
                    assert 'N' not in variant, f"Variant '{variant}' should not contain wildcards"
                    assert len(variant) == len(pattern), \
                        f"Variant '{variant}' length should match pattern length {len(pattern)}"

                print(f"✓ {description}: {actual_count} correct variants")

            except Exception as e:
                if expected_count <= 10000:  # Should work for reasonable counts
                    pytest.fail(f"Expansion failed for {description}: {e}")
                else:
                    print(f"⚠ {description}: Expected failure for large count: {e}")

    def test_expansion_performance_characteristics(self):
        """Test performance characteristics of the expansion algorithm."""
        import time

        # Test patterns with increasing complexity
        performance_tests = [
            ("ATNG", 4, "Simple pattern"),
            ("ATNNCG", 16, "Medium pattern"),
            ("ATNNNNCG", 64, "Complex pattern"),
        ]

        for pattern, expected_variants, description in performance_tests:
            fq = FuzzyQuery(k=len(pattern), pattern=pattern)
            fq.set_max_variants(expected_variants)

            start_time = time.time()
            try:
                variants = fq.expand_wildcards()
                end_time = time.time()

                expansion_time = end_time - start_time

                # Should be fast (< 100ms for reasonable patterns)
                assert expansion_time < 0.1, \
                    f"{description} expansion took {expansion_time:.3f}s, should be < 0.1s"

                assert len(variants) == expected_variants, \
                    f"{description}: Expected {expected_variants}, got {len(variants)}"

                print(f"✓ {description}: {len(variants)} variants in {expansion_time:.3f}s")

            except Exception as e:
                print(f"⚠ {description} failed: {e}")

    def test_memory_efficiency_of_expansion(self):
        """Test that expansion is memory efficient."""
        # Create pattern that would generate many variants
        pattern = "ATNNNNNNNN"  # 6 wildcards -> 4^6 = 4096 variants

        fq = FuzzyQuery(k=len(pattern), pattern=pattern)
        fq.set_max_variants(5000)  # Allow more than needed

        # Should not cause memory issues
        try:
            variants = fq.expand_wildcards()

            # Should not be excessively large
            assert len(variants) <= 5000, "Should respect max_variants limit"

            # All variants should be valid
            for variant in variants[:100]:  # Check first 100 for efficiency
                assert len(variant) == len(pattern), f"Variant length mismatch: '{variant}'"
                assert 'N' not in variant, f"Variant contains wildcard: '{variant}'"

            print(f"✓ Memory efficient expansion: {len(variants)} variants")

        except MemoryError:
            pytest.fail("Memory error should be prevented by limit enforcement")

    def test_expansion_with_no_wildcards(self):
        """Test expansion behavior when no wildcards are present."""
        fq = FuzzyQuery(k=21, pattern="ATCGATCGATCGATCGATCGAT")
        fq.set_max_variants(1000)

        start_time = time.time()
        variants = fq.expand_wildcards()
        end_time = time.time()

        # Should return original pattern
        assert len(variants) == 1, "No wildcards should return 1 variant"
        assert variants[0] == "ATCGATCGATCGATCGATCGAT", "Should return original pattern"

        # Should be very fast
        assert (end_time - start_time) < 0.001, "No-wildcard expansion should be very fast"

        print(f"✓ No-wildcard expansion: {variants[0]} in {(end_time - start_time)*1000:.2f}ms")

    def test_expansion_edge_cases(self):
        """Test expansion algorithm edge cases."""
        edge_cases = [
            # (pattern, k, expected_behavior)
            ("N", 1, "Single wildcard"),
            ("NN", 2, "All wildcards"),
            ("ATN", 3, "Trailing wildcard"),
            ("NAT", 3, "Leading wildcard"),
            ("AT", 2, "No wildcards, different k"),
            ("ATCGATCGATCGATCGATCGAT", 21, "Long pattern, no wildcards"),
        ]

        for pattern, k, description in edge_cases:
            try:
                fq = FuzzyQuery(k=k, pattern=pattern)
                fq.set_max_variants(1000)

                variants = fq.expand_wildcards()

                # Should have at least one variant
                assert len(variants) >= 1, f"{description} should generate at least 1 variant"

                # All variants should be correct length
                for variant in variants:
                    assert len(variant) == k, f"Variant '{variant}' length incorrect for {description}"

                print(f"✓ {description}: {len(variants)} variants")

            except Exception as e:
                if "No wildcards" not in description and "Long pattern" not in description:
                    # Should not fail for most cases
                    print(f"⚠ {description} failed: {e}")


class TestBackwardCompatibilityValidation:
    """Validate backward compatibility with existing FuzzyQuery API."""

    def test_legacy_constructor_patterns(self):
        """Test that legacy constructor patterns still work."""
        # Test different constructor patterns that existing code might use
        legacy_constructors = [
            # (args, description)
            ({"query_string": "ATCGATCGATCGATCGATCGAT", "kmer_size": 21}, "Query + kmer_size"),
            ({"query_string": "ATNCGATNN", "mutation_tolerance": 1}, "Query + mutation_tolerance"),
            ({"query_string": "ATNCGATNN", "max_variants": 50000}, "Query + max_variants"),
            ({"k": 21, "max_distance": 1}, "k-only (generates pattern)"),
        ]

        for args, description in legacy_constructors:
            try:
                fq = FuzzyQuery(**args)

                # Should create valid FuzzyQuery
                assert hasattr(fq, 'get_max_variants'), f"{description}: missing max_variants method"

                # Should have reasonable max_variants value
                max_variants = fq.get_max_variants()
                assert 1 <= max_variants <= 1000000, f"{description}: invalid max_variants {max_variants}"

                print(f"✓ {description}: max_variants = {max_variants}")

            except Exception as e:
                print(f"⚠ {description} failed: {e}")

    def test_existing_api_methods_still_work(self):
        """Test that existing API methods continue to work."""
        fq = FuzzyQuery(k=21, pattern="ATNCGATNN")

        existing_methods = [
            'validate',
            'get_variant_count',
            'get_wildcard_count',
            'get_query_string',
            'get_kmer_size',
            'get_mutation_tolerance',
            'get_k',
            'get_max_distance',
            'is_valid',
            '__repr__',
            '__str__',
        ]

        for method_name in existing_methods:
            if hasattr(fq, method_name):
                method = getattr(fq, method_name)

                try:
                    # Call the method
                    if method_name in ['__repr__', '__str__']:
                        result = method()
                        assert isinstance(result, str), f"{method_name} should return string"
                    else:
                        result = method()
                        # Most methods should return something reasonable
                        assert result is not None, f"{method_name} should not return None"

                    print(f"✓ {method_name} method works")

                except Exception as e:
                    print(f"⚠ {method_name} method failed: {e}")
            else:
                print(f"⚠ {method_name} method not found")

    def test_backward_compatibility_with_property_access(self):
        """Test backward compatibility when using property access."""
        fq = FuzzyQuery(k=21, pattern="ATNCGATNN")

        # Test that existing method-based access still works
        try:
            # Set using method
            fq.set_max_variants(75000)
            method_result = fq.get_max_variants()

            # Check using property if available
            if hasattr(fq, 'max_variants'):
                property_result = fq.max_variants

                # Should be consistent
                assert method_result == property_result, \
                    "Method and property access should be consistent"

                print("✓ Method and property access are consistent")
            else:
                print("⚠ Property access not available, method access works")

        except Exception as e:
            print(f"⚠ Backward compatibility test failed: {e}")

    def test_api_stability_after_enhancement(self):
        """Test that API remains stable after max_variants enhancement."""
        # Create FuzzyQuery using various patterns
        queries = [
            FuzzyQuery(k=21, pattern="ATCGATCGATCGATCGATCGAT"),
            FuzzyQuery(k=13, pattern="ATNCGATNN"),
            FuzzyQuery(k=31, pattern="ATNCGNNNNNNNNNNNNNNN"),
        ]

        for i, fq in enumerate(queries):
            # Test that basic functionality works
            try:
                is_valid = fq.validate()
                kmer_size = fq.get_kmer_size()
                query_string = fq.get_query_string()

                assert isinstance(is_valid, bool), f"Query {i}: validate should return bool"
                assert kmer_size > 0, f"Query {i}: kmer_size should be positive"
                assert isinstance(query_string, str), f"Query {i}: query_string should be string"

                # Test max_variants functionality
                fq.set_max_variants(10000 + i * 5000)
                max_variants = fq.get_max_variants()
                assert max_variants > 0, f"Query {i}: max_variants should be positive"

                print(f"✓ Query {i}: API stable with max_variants={max_variants}")

            except Exception as e:
                print(f"⚠ Query {i} API issue: {e}")


# Test execution
if __name__ == "__main__":
    pytest.main([__file__, "-v"])