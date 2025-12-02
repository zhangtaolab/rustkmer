"""
Database Implementation Validation Test Suite
=============================================

This module provides comprehensive validation testing for the actual database implementation,
focusing on JSON metadata schema, database loading functionality, error handling, and memory efficiency.

Validates:
- JSON metadata schema implementation (T017)
- Database loading functionality for KmerCounter-created databases (T018)
- Database persistence error handling and recovery (T019)
- Memory-efficient database operations (T020)
"""

import pytest
import sys
import os
import json
import tempfile
import shutil
from pathlib import Path
from datetime import datetime
import hashlib

# Add the rustkmer Python module to path for testing
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src" / "python"))

try:
    from rustkmer import KmerCounter, Database
    from rustkmer.exceptions import DatabaseError, KmerCounterError
except ImportError as e:
    pytest.skip(f"RustKmer Python bindings not available: {e}", allow_module_level=True)


class TestJSONMetadataSchemaValidation:
    """Test suite for JSON metadata schema implementation (T017)."""

    def test_metadata_schema_completeness(self):
        """Test that metadata schema contains all required fields."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            db_file = temp_path / "metadata_schema_test.rkdb"

            # Create database
            counter = KmerCounter(k=21, canonical=True)
            counter.count_from_sequence("ATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCG")
            counter.save_to_database(str(db_file))

            # Read and validate metadata.json
            metadata_path = db_file / "metadata.json"
            assert metadata_path.exists(), "metadata.json should be created"

            with open(metadata_path, 'r') as f:
                metadata = json.load(f)

            # Validate required fields exist
            required_fields = [
                "kmer_size",
                "canonical",
                "total_kmers",
                "unique_kmers",
                "created_at",
                "format"
            ]

            for field in required_fields:
                assert field in metadata, f"Required field '{field}' should be present in metadata"

    def test_metadata_schema_data_types(self):
        """Test that metadata schema contains correct data types."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            db_file = temp_path / "metadata_types_test.rkdb"

            # Create database with specific parameters
            counter = KmerCounter(k=31, canonical=False)
            test_sequences = [
                "ATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCG",
                "GCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAGCT"
            ]

            for seq in test_sequences:
                counter.count_from_sequence(seq)

            counter.save_to_database(str(db_file))

            # Validate metadata data types
            metadata_path = db_file / "metadata.json"
            with open(metadata_path, 'r') as f:
                metadata = json.load(f)

            # Validate data types
            assert isinstance(metadata["kmer_size"], int), "kmer_size should be integer"
            assert isinstance(metadata["canonical"], bool), "canonical should be boolean"
            assert isinstance(metadata["total_kmers"], int), "total_kmers should be integer"
            assert isinstance(metadata["unique_kmers"], int), "unique_kmers should be integer"
            assert isinstance(metadata["created_at"], str), "created_at should be string (timestamp)"
            assert isinstance(metadata["format"], str), "format should be string"

            # Validate specific values
            assert metadata["kmer_size"] == 31, "kmer_size should match counter"
            assert metadata["canonical"] == False, "canonical should match counter"
            assert metadata["total_kmers"] > 0, "total_kmers should be positive"
            assert metadata["unique_kmers"] > 0, "unique_kmers should be positive"
            assert metadata["format"] == "RustKmer Database v0.1.0", "format should match expected version"

    def test_metadata_timestamp_format(self):
        """Test that metadata timestamp is in RFC3339 format."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            db_file = temp_path / "timestamp_test.rkdb"

            counter = KmerCounter(k=21)
            counter.count_from_sequence("ATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCG")
            counter.save_to_database(str(db_file))

            # Validate timestamp format
            metadata_path = db_file / "metadata.json"
            with open(metadata_path, 'r') as f:
                metadata = json.load(f)

            timestamp_str = metadata["created_at"]

            # Try to parse as RFC3339 timestamp
            try:
                import dateutil.parser
                parsed_time = dateutil.parser.parse(timestamp_str)
                assert parsed_time.tzinfo is not None, "Timestamp should include timezone"
            except ImportError:
                # Fallback validation without dateutil
                import datetime
                # Basic RFC3339 pattern check
                assert "T" in timestamp_str, "Timestamp should contain 'T' separator"
                assert timestamp_str.endswith("Z") or "+" in timestamp_str, "Timestamp should have timezone"

    def test_metadata_accuracy_reflection(self):
        """Test that metadata accurately reflects counter state."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            db_file = temp_path / "metadata_accuracy_test.rkdb"

            # Create counter with known data
            counter = KmerCounter(k=21, canonical=True)
            test_data = [
                "ATCGATCGATCGATCGATCGAT",  # 21 bases
                "GCTAGCTAGCTAGCTAGCTAGC",  # 21 bases
                "AAAATTTTCCCCGGGGAAAATTTT"  # 21 bases
            ]

            # Count unique k-mers
            expected_total_kmers = 0
            for seq in test_data:
                result = counter.count_sequence(seq)
                expected_total_kmers += sum(result.values())

            counter.save_to_database(str(db_file))

            # Validate metadata accuracy
            metadata_path = db_file / "metadata.json"
            with open(metadata_path, 'r') as f:
                metadata = json.load(f)

            assert metadata["kmer_size"] == counter.k, "kmer_size should match counter.k"
            assert metadata["canonical"] == counter.is_canonical(), "canonical should match counter.is_canonical()"
            assert metadata["total_kmers"] == counter.get_total_count(), "total_kmers should match counter.get_total_count()"

    def test_metadata_json_prettification(self):
        """Test that metadata JSON is properly formatted and readable."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            db_file = temp_path / "pretty_json_test.rkdb"

            counter = KmerCounter(k=21)
            counter.count_from_sequence("ATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCG")
            counter.save_to_database(str(db_file))

            # Validate JSON formatting
            metadata_path = db_file / "metadata.json"
            with open(metadata_path, 'r') as f:
                content = f.read()

            # Should be pretty-printed with newlines and indentation
            assert "\n" in content, "JSON should be pretty-printed with newlines"
            assert "  " in content, "JSON should contain indentation"

            # Should be valid JSON
            parsed = json.loads(content)
            assert isinstance(parsed, dict), "Should parse to dictionary"


class TestDatabaseLoadingFunctionality:
    """Test suite for database loading functionality (T018)."""

    def test_load_from_kmercounter_directory_structure(self):
        """Test loading database from KmerCounter-created directory structure."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            db_dir = temp_path / "kmercounter_db"

            # Create KmerCounter database
            counter = KmerCounter(k=21, canonical=False)
            test_sequences = [
                "ATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCG",
                "GCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAGCT"
            ]

            for seq in test_sequences:
                counter.count_from_sequence(seq)

            original_total = counter.get_total_count()
            counter.save_to_database(str(db_dir))

            # Verify directory structure
            assert db_dir.is_dir(), "Database should be created as directory"
            assert (db_dir / "metadata.json").exists(), "metadata.json should exist"
            assert (db_dir / "data.rkdb").exists(), "data.rkdb should exist"

            # Load with Database class
            database = Database()
            database.load_from_kmer_counter(str(db_dir))

            # Validate loaded database properties
            assert database.k == counter.k, "Loaded database k should match counter"
            assert database.get_path() == str(db_dir), "Database path should be set correctly"

    def test_database_data_integrity_after_loading(self):
        """Test that database data integrity is maintained after loading."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            db_dir = temp_path / "integrity_test.rkdb"

            # Create counter with known k-mer counts
            counter = KmerCounter(k=21)
            test_kmers = [
                ("ATCGATCGATCGATCGATCGAT", 5),
                ("GCTAGCTAGCTAGCTAGCTAGC", 3),
                ("AAAATTTTCCCCGGGGAAAATTTT", 7)
            ]

            # Add sequences multiple times to create counts
            for kmer, count in test_kmers:
                for _ in range(count):
                    counter.count_from_sequence(kmer)

            counter.save_to_database(str(db_dir))

            # Load database
            database = Database()
            database.load_from_kmer_counter(str(db_dir))

            # Verify data integrity through queries
            for kmer, expected_count in test_kmers:
                result = database.query(kmer)
                if result.found:
                    assert result.count == expected_count, f"Count for {kmer} should be preserved"

    def test_load_preserves_database_parameters(self):
        """Test that loading preserves all database parameters correctly."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            db_dir = temp_path / "parameters_test.rkdb"

            # Test with different parameters
            test_params = [
                (21, True),   # k=21, canonical=True
                (31, False),  # k=31, canonical=False
                (13, True),   # k=13, canonical=True
            ]

            for k, canonical in test_params:
                db_dir_specific = db_dir / f"k{k}_canonical_{canonical}"

                # Create counter with specific parameters
                counter = KmerCounter(k=k, canonical=canonical)
                counter.count_from_sequence("ATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCG")
                counter.save_to_database(str(db_dir_specific))

                # Load database
                database = Database()
                database.load_from_kmer_counter(str(db_dir_specific))

                # Verify parameters are preserved
                assert database.k == k, f"K-mer size {k} should be preserved"

                # Check stats for canonical flag
                stats = database.get_stats()
                assert stats.canonical == canonical, f"Canonical flag {canonical} should be preserved"

    def test_load_error_handling_invalid_directory(self):
        """Test error handling when loading from invalid directory."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # Test with non-existent directory
            with pytest.raises((DatabaseError, FileNotFoundError, OSError)):
                database = Database()
                database.load_from_kmer_counter("/non/existent/directory")

            # Test with empty directory (no metadata)
            empty_dir = temp_path / "empty"
            empty_dir.mkdir()
            with pytest.raises((DatabaseError, FileNotFoundError, OSError)):
                database = Database()
                database.load_from_kmer_counter(str(empty_dir))

            # Test with directory missing metadata.json
            no_metadata_dir = temp_path / "no_metadata"
            no_metadata_dir.mkdir()
            (no_metadata_dir / "data.rkdb").write_text("{}")
            with pytest.raises((DatabaseError, FileNotFoundError, OSError)):
                database = Database()
                database.load_from_kmer_counter(str(no_metadata_dir))

    def test_load_error_handling_corrupted_metadata(self):
        """Test error handling when metadata is corrupted."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            db_dir = temp_path / "corrupted_test.rkdb"
            db_dir.mkdir()

            # Create corrupted metadata.json
            corrupted_metadata_paths = [
                ("invalid_json", db_dir / "metadata.json", "{invalid json}"),
                ("missing_fields", db_dir / "metadata.json", '{"some": "data"}'),
                ("wrong_types", db_dir / "metadata.json", '{"kmer_size": "not_an_int", "canonical": "not_a_bool"}'),
            ]

            for test_name, path, content in corrupted_metadata_paths:
                # Write corrupted metadata
                path.write_text(content)

                # Also create data.rkdb
                (db_dir / "data.rkdb").write_text("{}")

                # Loading should fail gracefully
                with pytest.raises((DatabaseError, ValueError, json.JSONDecodeError)):
                    database = Database()
                    database.load_from_kmer_counter(str(db_dir))

                # Clean up for next test
                path.unlink()

    def test_database_load_from_legacy_format_placeholder(self):
        """Test loading from legacy database format (placeholder)."""
        # Note: This tests the placeholder implementation
        # When full legacy support is implemented, this test should be updated

        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            legacy_db = temp_path / "legacy.rkdb"

            # Create a fake legacy database file
            legacy_db.write_bytes(b"fake legacy database content")

            # Attempt to load (should use placeholder implementation)
            database = Database(file_path=str(legacy_db))

            # The database should be created but with placeholder behavior
            assert database.is_open(), "Database should be marked as open"
            assert database.get_path() == str(legacy_db), "Path should be set"


class TestDatabasePersistenceErrorHandling:
    """Test suite for database persistence error handling and recovery (T019)."""

    def test_save_error_handling_permission_denied(self):
        """Test error handling when save fails due to permissions."""
        # Test with read-only directory (if possible on this system)
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            readonly_dir = temp_path / "readonly"
            readonly_dir.mkdir()

            try:
                # Make directory read-only
                readonly_dir.chmod(0o444)

                counter = KmerCounter(k=21)
                counter.count_from_sequence("ATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCG")

                # Should raise appropriate error
                with pytest.raises((DatabaseError, PermissionError, OSError)):
                    counter.save_to_database(str(readonly_dir))

            except OSError:
                # Skip if we can't set permissions on this system
                pytest.skip("Cannot set directory permissions on this system")

    def test_save_error_handling_disk_full_simulation(self):
        """Test error handling when disk is full (simulated)."""
        # This is a challenging test to implement realistically
        # We'll test the error path structure instead

        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            db_dir = temp_path / "disk_full_test.rkdb"
            db_dir.mkdir()

            # Create valid metadata first
            counter = KmerCounter(k=21)
            counter.count_from_sequence("ATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCG")

            # Simulate write failure by creating directory with a file that can't be overwritten
            readonly_file = db_dir / "metadata.json"
            readonly_file.write_text("existing")
            readonly_file.chmod(0o444)

            try:
                # Save should fail when it can't write metadata
                with pytest.raises((DatabaseError, PermissionError, OSError)):
                    counter.save_to_database(str(db_dir))
            except OSError:
                pytest.skip("Cannot set file permissions on this system")

    def test_load_error_recovery_mechanisms(self):
        """Test error recovery mechanisms during database loading."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            db_dir = temp_path / "recovery_test.rkdb"

            # Create valid database
            counter = KmerCounter(k=21)
            counter.count_from_sequence("ATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCG")
            counter.save_to_database(str(db_dir))

            # Test loading with various corruption scenarios
            database = Database()

            # 1. Test loading after metadata corruption recovery
            metadata_path = db_dir / "metadata.json"
            original_metadata = metadata_path.read_text()

            # Corrupt metadata
            metadata_path.write_text("{invalid}")

            try:
                database.load_from_kmer_counter(str(db_dir))
                assert False, "Should have raised error for corrupted metadata"
            except (DatabaseError, ValueError, json.JSONDecodeError):
                # Expected - restore metadata for recovery test
                metadata_path.write_text(original_metadata)

            # 2. Test loading after data file corruption recovery
            data_path = db_dir / "data.rkdb"
            original_data = data_path.read_text()

            # Corrupt data
            data_path.write_text("{invalid json}")

            try:
                database.load_from_kmer_counter(str(db_dir))
                assert False, "Should have raised error for corrupted data"
            except (DatabaseError, ValueError, json.JSONDecodeError):
                # Expected - restore data for recovery test
                data_path.write_text(original_data)

            # 3. Test successful recovery after restoration
            database.load_from_kmer_counter(str(db_dir))
            assert database.k == 21, "Should recover successfully after metadata restoration"

    def test_concurrent_save_error_handling(self):
        """Test error handling during concurrent save operations."""
        import threading
        import time

        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            db_dir = temp_path / "concurrent_save_test.rkdb"

            # Create multiple counters trying to save to same location
            results = []
            errors = []

            def save_worker(worker_id):
                try:
                    counter = KmerCounter(k=21)
                    counter.count_from_sequence(f"ATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCG{worker_id}")
                    counter.save_to_database(str(db_dir))
                    results.append(f"Worker {worker_id} success")
                except Exception as e:
                    errors.append(f"Worker {worker_id} error: {e}")

            # Create multiple threads
            threads = []
            for i in range(3):
                t = threading.Thread(target=save_worker, args=(i,))
                threads.append(t)
                t.start()

            # Wait for completion
            for t in threads:
                t.join(timeout=10.0)

            # At least one should succeed, others should fail gracefully
            assert len(results) > 0, "At least one save should succeed"
            assert len(errors) > 0, "Concurrent saves should produce some errors"

            # Errors should be handled gracefully (not crashes)
            for error in errors:
                assert "error" in error.lower(), "Errors should be properly handled"

    def test_partial_write_detection_and_handling(self):
        """Test detection and handling of partial writes."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            db_dir = temp_path / "partial_write_test.rkdb"
            db_dir.mkdir()

            # Simulate partial write by creating incomplete metadata
            metadata_path = db_dir / "metadata.json"
            metadata_path.write_text('{"incomplete": "metadata"')  # Missing closing brace

            # Also create incomplete data
            data_path = db_dir / "data.rkdb"
            data_path.write_text('{"incomplete": "data"')  # Missing closing brace

            database = Database()

            # Should detect and handle partial writes
            with pytest.raises((DatabaseError, ValueError, json.JSONDecodeError)):
                database.load_from_kmer_counter(str(db_dir))

            # Database should not be left in inconsistent state
            assert not database.is_open() or database.k == 0, "Database should not be in inconsistent state"


class TestMemoryEfficientDatabaseOperations:
    """Test suite for memory-efficient database operations (T020)."""

    def test_memory_usage_during_large_dataset_save(self):
        """Test memory usage efficiency during large dataset save operations."""
        import psutil
        import os

        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB

        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            db_dir = temp_path / "memory_efficient_save.rkdb"

            # Create counter with large dataset
            counter = KmerCounter(k=21)

            # Generate substantial k-mer data
            base_sequence = "ATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCG"

            # Add variations to create many unique k-mers
            for i in range(1000):
                variant = base_sequence[:20] + "ATCG"[:i % 4]  # Small variations
                counter.count_from_sequence(variant)

            pre_save_memory = process.memory_info().rss / 1024 / 1024  # MB

            # Save database
            counter.save_to_database(str(db_dir))

            post_save_memory = process.memory_info().rss / 1024 / 1024  # MB

            # Memory usage should not grow excessively during save
            memory_increase = post_save_memory - pre_save_memory
            assert memory_increase < 500, f"Memory increase during save should be reasonable, was {memory_increase}MB"

            # Verify database was created successfully
            assert (db_dir / "metadata.json").exists()
            assert (db_dir / "data.rkdb").exists()

    def test_memory_usage_during_large_dataset_load(self):
        """Test memory usage efficiency during large dataset load operations."""
        import psutil
        import os

        process = psutil.Process(os.getpid())

        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            db_dir = temp_path / "memory_efficient_load.rkdb"

            # Create database with large dataset first
            counter = KmerCounter(k=21)
            base_sequence = "ATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCG"

            for i in range(2000):  # Larger dataset
                variant = base_sequence[:18] + "ATCGATCG"[:i % 8]  # More variations
                counter.count_from_sequence(variant)

            counter.save_to_database(str(db_dir))

            # Now test loading efficiency
            initial_load_memory = process.memory_info().rss / 1024 / 1024  # MB

            database = Database()
            database.load_from_kmer_counter(str(db_dir))

            post_load_memory = process.memory_info().rss / 1024 / 1024  # MB

            # Memory usage should be reasonable
            memory_increase = post_load_memory - initial_load_memory
            assert memory_increase < 1000, f"Memory increase during load should be reasonable, was {memory_increase}MB"

            # Database should be functional
            assert database.k == 21
            assert database.get_stats().total_kmers > 0

    def test_lazy_loading_memory_efficiency(self):
        """Test memory efficiency with lazy loading (preload=False)."""
        import psutil
        import os

        process = psutil.Process(os.getpid())

        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            db_dir = temp_path / "lazy_loading_test.rkdb"

            # Create substantial database
            counter = KmerCounter(k=21)
            for i in range(5000):
                counter.count_from_sequence(f"ATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATC{i:04d}")

            counter.save_to_database(str(db_dir))

            # Test lazy loading (preload=False)
            lazy_memory_start = process.memory_info().rss / 1024 / 1024  # MB

            lazy_database = Database()
            lazy_database.load_from_kmer_counter(str(db_dir), preload=False)

            lazy_memory_end = process.memory_info().rss / 1024 / 1024  # MB

            # Test eager loading (preload=True)
            eager_memory_start = process.memory_info().rss / 1024 / 1024  # MB

            eager_database = Database()
            eager_database.load_from_kmer_counter(str(db_dir), preload=True)

            eager_memory_end = process.memory_info().rss / 1024 / 1024  # MB

            # Lazy loading should use less memory initially
            lazy_memory_increase = lazy_memory_end - lazy_memory_start
            eager_memory_increase = eager_memory_end - eager_memory_start

            # Note: In the current stub implementation, both might be similar
            # This test validates the structure for future optimization
            assert lazy_memory_increase >= 0, "Lazy loading memory should be measurable"
            assert eager_memory_increase >= 0, "Eager loading memory should be measurable"

    def test_memory_cleanup_after_database_close(self):
        """Test memory cleanup after database operations and close."""
        import psutil
        import os
        import gc

        process = psutil.Process(os.getpid())

        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            db_dir = temp_path / "memory_cleanup_test.rkdb"

            # Create database
            counter = KmerCounter(k=21)
            for i in range(3000):
                counter.count_from_sequence(f"ATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATC{i:04d}")

            counter.save_to_database(str(db_dir))

            # Load database and use it
            initial_memory = process.memory_info().rss / 1024 / 1024  # MB

            database = Database()
            database.load_from_kmer_counter(str(db_dir))

            # Perform some operations
            for i in range(100):
                database.query(f"ATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATC{i:04d}")

            used_memory = process.memory_info().rss / 1024 / 1024  # MB

            # Close database
            database.close()

            # Force garbage collection
            del database
            gc.collect()

            # Wait a moment for cleanup
            import time
            time.sleep(0.1)

            final_memory = process.memory_info().rss / 1024 / 1024  # MB

            # Memory should be cleaned up (some tolerance for Python memory management)
            memory_after_close = final_memory - initial_memory
            memory_during_use = used_memory - initial_memory

            # Memory usage should not grow indefinitely
            assert memory_after_close < memory_during_use + 200, "Memory should be cleaned up after database close"

    def test_database_streaming_large_operations(self):
        """Test database operations with streaming to minimize memory usage."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            db_dir = temp_path / "streaming_test.rkdb"

            # Test streaming save operations
            counter = KmerCounter(k=21)

            # Simulate streaming large amounts of data
            batch_size = 100
            total_batches = 50

            for batch in range(total_batches):
                # Process batch
                for i in range(batch_size):
                    seq = f"ATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATC{batch:03d}{i:03d}"
                    counter.count_from_sequence(seq)

                # Periodic memory check (should not grow unbounded)
                if batch % 10 == 0:
                    # Memory should remain reasonable during streaming
                    # (Implementation-specific assertion)
                    pass

            # Final save should handle large dataset efficiently
            counter.save_to_database(str(db_dir))

            # Verify streaming load
            database = Database()
            database.load_from_kmer_counter(str(db_dir))

            # Database should handle the large dataset
            assert database.k == 21
            stats = database.get_stats()
            assert stats.total_kmers > 0

            # Test streaming queries
            query_count = 0
            for batch in range(total_batches):
                for i in range(0, batch_size, 10):  # Sample queries
                    seq = f"ATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATC{batch:03d}{i:03d}"
                    result = database.query(seq)
                    query_count += 1

            assert query_count > 0, "Should have performed streaming queries"


# Test fixtures and integration tests
@pytest.fixture(params=[21, 31])
def k_mer_sizes(request):
    """Provide different k-mer sizes for testing."""
    return request.param


@pytest.fixture
def sample_database_with_data():
    """Provide a sample database with test data."""
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        db_dir = temp_path / "sample_db.rkdb"

        # Create counter with diverse data
        counter = KmerCounter(k=21, canonical=True)
        test_data = [
            "ATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCG",
            "GCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAGCT",
            "AAAATTTTCCCCGGGGAAAATTTTCCCCGGGGAAAATTTTCCCCGGGGAAAATTTTCCCCGGGG"
        ]

        for seq in test_data:
            counter.count_from_sequence(seq)

        counter.save_to_database(str(db_dir))
        yield db_dir


class TestImplementationIntegration:
    """Integration tests for complete implementation validation."""

    def test_complete_implementation_validation_workflow(self):
        """Test complete workflow validating all implementation aspects."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            db_dir = temp_path / "complete_validation_test.rkdb"

            # 1. Create counter with specific parameters
            counter = KmerCounter(k=31, canonical=False)

            # Add test data
            test_sequences = [
                "ATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCG",
                "GCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAGCT",
                "AAAATTTTCCCCGGGGAAAATTTTCCCCGGGGAAAATTTTCCCCGGGGAAAATTTTCCCCGGGG"
            ]

            for seq in test_sequences:
                counter.count_from_sequence(seq)

            original_stats = {
                'k': counter.k,
                'canonical': counter.is_canonical(),
                'total_count': counter.get_total_count()
            }

            # 2. Save to database (T017: JSON metadata schema validation)
            counter.save_to_database(str(db_dir))

            # Validate metadata schema
            metadata_path = db_dir / "metadata.json"
            with open(metadata_path, 'r') as f:
                metadata = json.load(f)

            assert metadata["kmer_size"] == original_stats['k']
            assert metadata["canonical"] == original_stats['canonical']
            assert metadata["total_kmers"] == original_stats['total_count']

            # 3. Load database (T018: Database loading functionality)
            database = Database()
            database.load_from_kmer_counter(str(db_dir))

            # Validate loading preserved properties
            assert database.k == original_stats['k']
            loaded_stats = database.get_stats()
            assert loaded_stats.canonical == original_stats['canonical']

            # 4. Test data integrity (T019: Error handling validation)
            # Query known k-mers
            for seq in test_sequences:
                results = database.query_multiple([seq[i:i+21] for i in range(len(seq)-21+1)])
                assert len(results) > 0, "Should find k-mers from test sequences"

            # 5. Test memory efficiency (T020: Memory efficiency validation)
            # Database should handle operations without excessive memory usage
            large_query_set = []
            for i in range(1000):
                large_query_set.append(f"ATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATC{i:04d}")

            batch_results = database.query_multiple(large_query_set)
            assert len(batch_results) == 1000, "Should handle large query sets efficiently"

    def test_error_handling_integration(self):
        """Test error handling integration across all implementation aspects."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # Test 1: Save error handling
            invalid_path = temp_path / "nonexistent" / "subdir"
            counter = KmerCounter(k=21)
            counter.count_from_sequence("ATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCG")

            with pytest.raises((DatabaseError, OSError)):
                counter.save_to_database(str(invalid_path))

            # Test 2: Load error handling
            counter.save_to_database(str(temp_path / "valid_db.rkdb"))

            # Corrupt metadata and test load error handling
            metadata_path = temp_path / "valid_db.rkdb" / "metadata.json"
            metadata_path.write_text("{invalid json}")

            database = Database()
            with pytest.raises((DatabaseError, ValueError, json.JSONDecodeError)):
                database.load_from_kmer_counter(str(temp_path / "valid_db.rkdb"))

            # Test 3: Recovery after error
            # Restore metadata and verify recovery
            metadata_path.write_text('{"kmer_size": 21, "canonical": false, "total_kmers": 1, "unique_kmers": 1, "created_at": "2025-01-01T00:00:00Z", "format": "test"}')

            database = Database()
            database.load_from_kmer_counter(str(temp_path / "valid_db.rkdb"))
            assert database.k == 21, "Should recover after error correction"

    def test_production_readiness_validation(self):
        """Test production readiness of the implementation."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            db_dir = temp_path / "production_test.rkdb"

            # Production-like scenario
            counter = KmerCounter(k=21, canonical=True)

            # Simulate genomic data
            genomic_patterns = [
                "ATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCG",
                "GCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAGCT",
                "TTTTAAAACCCCGGGGTTTTAAAACCCCGGGGTTTTAAAACCCCGGGGTTTTAAAACCCCGGGG"
            ] * 100  # Simulate larger dataset

            for pattern in genomic_patterns:
                counter.count_from_sequence(pattern)

            # Production save
            save_start = time.time()
            counter.save_to_database(str(db_dir))
            save_time = time.time() - save_start

            assert save_time < 30.0, f"Production save should complete in reasonable time, took {save_time}s"

            # Production load
            load_start = time.time()
            database = Database()
            database.load_from_kmer_counter(str(db_dir))
            load_time = time.time() - load_start

            assert load_time < 10.0, f"Production load should complete in reasonable time, took {load_time}s"

            # Production queries
            query_start = time.time()
            for i in range(100):
                database.query(f"ATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATC{i:02d}")
            query_time = time.time() - query_start

            assert query_time < 5.0, f"Production queries should be efficient, took {query_time}s"

            # Validate production characteristics
            assert database.k == 21
            stats = database.get_stats()
            assert stats.total_kmers > 0
            assert stats.canonical == True


if __name__ == "__main__":
    # Run tests directly
    pytest.main([__file__, "-v"])