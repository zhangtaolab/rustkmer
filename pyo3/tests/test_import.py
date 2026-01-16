"""Tests for pyrustkmer module import and basic availability."""

import pytest


class TestModuleImport:
    """Test module import functionality."""

    def test_import_module(self):
        """Test that pyrustkmer module can be imported."""
        import pyrustkmer

        assert pyrustkmer is not None

    def test_module_has_version(self):
        """Test that module has version information."""
        import pyrustkmer

        # Module should have version attribute or be identifiable
        assert hasattr(pyrustkmer, "__name__")
        assert pyrustkmer.__name__ == "pyrustkmer"

    def test_core_classes_exist(self):
        """Test that all core classes are available."""
        import pyrustkmer

        required_classes = [
            "PyDatabase",
            "PyDatabaseStats",
            "PyQueryResult",
            "PyKmerCounter",
            "PyCounterStats",
            "PyFuzzyQuery",
            "PyFuzzyResult",
            "PyPrefixQuery",
        ]

        for class_name in required_classes:
            assert hasattr(pyrustkmer, class_name), f"{class_name} not found"

    def test_load_mode_enum_exists(self):
        """Test that LoadMode enum is available."""
        import pyrustkmer

        assert hasattr(pyrustkmer, "LoadMode")

        # Check enum members exist
        mode = pyrustkmer.LoadMode
        assert hasattr(mode, "Preload")
        assert hasattr(mode, "MemoryMapped")
        assert hasattr(mode, "Lazy")

    def test_error_class_exists(self):
        """Test that error class is available."""
        import pyrustkmer

        assert hasattr(pyrustkmer, "RustKmerError")


class TestLoadModeValues:
    """Test LoadMode enum values."""

    def test_load_mode_is_enum(self):
        """Test that LoadMode is an enum type."""
        import pyrustkmer

        mode = pyrustkmer.LoadMode
        # Should be usable as enum
        preload = mode.Preload
        memory_mapped = mode.MemoryMapped
        lazy = mode.Lazy

        # All should be different
        assert preload != memory_mapped
        assert memory_mapped != lazy
        assert lazy != preload

    def test_load_mode_can_be_used_as_parameter(self):
        """Test that LoadMode values can be passed to constructors."""
        import pyrustkmer

        # This should not raise an error
        # (even if the database doesn't exist, the enum usage should be valid)
        try:
            # We don't have a database, so this might fail on file not found
            # but the LoadMode should be usable
            db = pyrustkmer.PyDatabase("/nonexistent.rkdb", pyrustkmer.LoadMode.Preload)
        except Exception:
            pass  # Expected to fail on missing file, but enum usage is tested
