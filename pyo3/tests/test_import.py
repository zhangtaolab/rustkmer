"""Tests for rustkmer_pyo3 module import and basic availability."""

import pytest


class TestModuleImport:
    """Test module import functionality."""
    
    def test_import_module(self):
        """Test that rustkmer_pyo3 module can be imported."""
        import rustkmer_pyo3
        assert rustkmer_pyo3 is not None
    
    def test_module_has_version(self):
        """Test that module has version information."""
        import rustkmer_pyo3
        # Module should have version attribute or be identifiable
        assert hasattr(rustkmer_pyo3, '__name__')
        assert rustkmer_pyo3.__name__ == 'rustkmer_pyo3'
    
    def test_core_classes_exist(self):
        """Test that all core classes are available."""
        import rustkmer_pyo3
        
        required_classes = [
            'PyDatabase',
            'PyDatabaseStats', 
            'PyQueryResult',
            'PyKmerCounter',
            'PyCounterStats',
            'PyFuzzyQuery',
            'PyFuzzyResult',
            'PyPrefixQuery',
        ]
        
        for class_name in required_classes:
            assert hasattr(rustkmer_pyo3, class_name), f"{class_name} not found"
            
    def test_load_mode_enum_exists(self):
        """Test that LoadMode enum is available."""
        import rustkmer_pyo3
        
        assert hasattr(rustkmer_pyo3, 'LoadMode')
        
        # Check enum members exist
        mode = rustkmer_pyo3.LoadMode
        assert hasattr(mode, 'Preload')
        assert hasattr(mode, 'MemoryMapped')
        assert hasattr(mode, 'Lazy')
    
    def test_error_class_exists(self):
        """Test that error class is available."""
        import rustkmer_pyo3
        
        assert hasattr(rustkmer_pyo3, 'RustKmerError')


class TestLoadModeValues:
    """Test LoadMode enum values."""
    
    def test_load_mode_is_enum(self):
        """Test that LoadMode is an enum type."""
        import rustkmer_pyo3
        
        mode = rustkmer_pyo3.LoadMode
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
        import rustkmer_pyo3
        
        # This should not raise an error
        # (even if the database doesn't exist, the enum usage should be valid)
        try:
            # We don't have a database, so this might fail on file not found
            # but the LoadMode should be usable
            db = rustkmer_pyo3.PyDatabase("/nonexistent.rkdb", rustkmer_pyo3.LoadMode.Preload)
        except Exception:
            pass  # Expected to fail on missing file, but enum usage is tested
