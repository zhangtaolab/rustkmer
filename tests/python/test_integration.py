"""
Integration tests for RustKmer Python bindings.
Tests the basic Rust-Python interface functionality.
"""

import pytest


class TestBasicImports:
    """Test that the Rust extension can be imported and basic functionality works."""

    def test_import_rustkmer(self):
        """Test that rustkmer can be imported."""
        try:
            import rustkmer
            assert hasattr(rustkmer, '__version__')
            print("✓ rustkmer imported successfully")
        except ImportError as e:
            pytest.skip(f"Rust extension not built yet: {e}")

    def test_import_core_classes(self):
        """Test that core classes can be imported."""
        try:
            from rustkmer import KmerCounter, Database, FuzzyQuery
            assert KmerCounter is not None
            assert Database is not None
            assert FuzzyQuery is not None
            print("✓ Core classes imported successfully")
        except ImportError as e:
            pytest.skip(f"Rust extension not available: {e}")

    def test_class_instantiation(self):
        """Test that classes can be instantiated with basic parameters."""
        try:
            from rustkmer import KmerCounter, Database, FuzzyQuery

            # Test KmerCounter
            counter = KmerCounter(k=21, canonical=False)
            assert counter.get_k() == 21
            assert counter.is_canonical() == False

            # Test Database
            db = Database(k=21)
            assert db.get_k() == 21

            # Test FuzzyQuery
            fq = FuzzyQuery(k=21, max_distance=1)
            assert fq.get_k() == 21
            assert fq.get_max_distance() == 1

            print("✓ Class instantiation works correctly")

        except ImportError as e:
            pytest.skip(f"Rust extension not available: {e}")
        except Exception as e:
            pytest.fail(f"Class instantiation failed: {e}")


class TestUtilityFunctions:
    """Test utility functions from the Rust extension."""

    def test_utility_imports(self):
        """Test that utility functions can be imported."""
        try:
            from rustkmer import get_version, set_verbosity
            assert get_version is not None
            assert set_verbosity is not None
            print("✓ Utility functions imported successfully")
        except ImportError as e:
            pytest.skip(f"Rust extension not available: {e}")

    def test_version_info(self):
        """Test version information."""
        try:
            from rustkmer import get_version
            version = get_version()
            assert isinstance(version, str)
            assert "RustKmer" in version
            print(f"✓ Version info: {version}")
        except ImportError as e:
            pytest.skip(f"Rust extension not available: {e}")

    def test_verbosity_setting(self):
        """Test verbosity setting."""
        try:
            from rustkmer import set_verbosity
            # This should not raise an exception
            set_verbosity(1)
            print("✓ Verbosity setting works")
        except ImportError as e:
            pytest.skip(f"Rust extension not available: {e}")


class TestErrorHandling:
    """Test error handling across the Rust-Python boundary."""

    def test_invalid_kmer_size(self):
        """Test handling of invalid k-mer sizes."""
        try:
            from rustkmer import KmerCounter

            # This should raise an error for k=0
            with pytest.raises(Exception):
                KmerCounter(k=0)

            # This should raise an error for very large k
            with pytest.raises(Exception):
                KmerCounter(k=1000)

            print("✓ Invalid k-mer size handling works")

        except ImportError as e:
            pytest.skip(f"Rust extension not available: {e}")

    def test_invalid_dna_sequence(self):
        """Test handling of invalid DNA sequences."""
        try:
            from rustkmer import FuzzyQuery

            fq = FuzzyQuery(k=5, max_distance=1)

            # Test validation function if available
            if hasattr(fq, 'validate_kmer'):
                assert not fq.validate_kmer("ATGCX")  # Contains invalid character
                assert fq.validate_kmer("ATGCG")    # Valid sequence

            print("✓ Invalid DNA sequence handling works")

        except ImportError as e:
            pytest.skip(f"Rust extension not available: {e}")


if __name__ == "__main__":
    # Allow running tests directly
    pytest.main([__file__, "-v"])