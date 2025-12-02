#!/usr/bin/env python3
"""
Database persistence tests for Python API improvements feature.

These tests should FAIL before implementation to demonstrate TDD approach.
Test Goal: Verify KmerCounter can save/load databases and work with Database class.
"""

import pytest
import sys
import os
import tempfile
import shutil

# Add the src directory to Python path for importing rustkmer
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../src'))

try:
    import rustkmer
    from rustkmer import KmerCounter, Database
except ImportError as e:
    pytest.skip(f"RustKmer Python bindings not available: {e}", allow_module_level=True)


class TestKmerCounterSaveToDatabase:
    """Test KmerCounter.save_to_database method functionality (should FAIL before implementation)."""

    def test_save_to_database_method_exists(self):
        """Test that save_to_database method exists on KmerCounter."""
        # Create a KmerCounter with some data
        counter = KmerCounter(k=5, canonical=False)

        # This should work: save_to_database method should exist
        # Currently this FAILS because save_to_database method doesn't exist
        assert hasattr(counter, 'save_to_database'), "KmerCounter should have save_to_database method"

    def test_save_to_database_creates_files(self):
        """Test that save_to_database creates proper database files."""
        counter = KmerCounter(k=3, canonical=True)

        # Count some test data
        counter.count_sequence("ATGCGATGCGC")

        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = os.path.join(temp_dir, "test_database")

            # This should create database files
            # Currently this FAILS because save_to_database method doesn't exist
            counter.save_to_database(db_path)

            # Should create metadata.json
            assert os.path.exists(os.path.join(db_path, "metadata.json")), "Database should have metadata.json"

            # Should create data.rkdb
            assert os.path.exists(os.path.join(db_path, "data.rkdb")), "Database should have data.rkdb"

    def test_save_to_database_metadata_content(self):
        """Test that save_to_database creates correct metadata content."""
        counter = KmerCounter(k=7, canonical=False)
        counter.count_sequence("ATGCGATGCGATGCG")

        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = os.path.join(temp_dir, "test_metadata_db")

            # Save database
            counter.save_to_database(db_path)

            # Load and verify metadata
            import json
            with open(os.path.join(db_path, "metadata.json"), 'r') as f:
                metadata = json.load(f)

            assert metadata["kmer_size"] == 7, "Metadata should record correct k-mer size"
            assert metadata["canonical"] is False, "Metadata should record canonical mode"
            assert "created_at" in metadata, "Metadata should include creation timestamp"
            assert "total_kmers" in metadata, "Metadata should include total k-mer count"

    def test_save_to_database_preserves_data(self):
        """Test that saved database preserves all k-mer counts."""
        counter = KmerCounter(k=5, canonical=True)
        counter.count_sequence("ATGCGATGCGATGCG")  # Multiple overlapping k-mers

        # Get original counts
        original_counts = counter.get_all_counts()
        assert len(original_counts) > 0, "Counter should have counted some k-mers"

        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = os.path.join(temp_dir, "test_preserve_db")

            # Save database
            counter.save_to_database(db_path)

            # Load database and verify counts are preserved
            loaded_db = Database(db_path)
            loaded_counts = loaded_db.get_all_counts()

            assert len(loaded_counts) == len(original_counts), "Loaded database should have same number of k-mers"

            for kmer, count in original_counts.items():
                assert loaded_counts[kmer] == count, f"Count for {kmer} should be preserved"

    def test_save_to_database_with_large_dataset(self):
        """Test save_to_database performance with larger datasets."""
        counter = KmerCounter(k=13, canonical=True)

        # Count multiple sequences
        sequences = [
            "ATGCGATGCGATGCGATGCGATGCG",
            "CGATGCGATGCGATGCGATGCGAT",
            "GATGCGATGCGATGCGATGCGATGC"
        ]

        for seq in sequences:
            counter.count_sequence(seq)

        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = os.path.join(temp_dir, "test_large_db")

            # Should handle larger datasets efficiently
            counter.save_to_database(db_path)

            # Verify database was created
            assert os.path.exists(db_path), "Database directory should be created"
            assert os.path.exists(os.path.join(db_path, "metadata.json")), "Metadata should exist"
            assert os.path.exists(os.path.join(db_path, "data.rkdb")), "Data file should exist"


class TestDatabaseCompatibility:
    """Test that KmerCounter-created databases work with Database class (should FAIL before implementation)."""

    def test_database_can_load_kmercounter_output(self):
        """Test that Database class can load databases created by KmerCounter."""
        counter = KmerCounter(k=5, canonical=False)
        counter.count_sequence("ATGCGATGCGC")

        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = os.path.join(temp_dir, "compat_test_db")

            # Save using KmerCounter
            counter.save_to_database(db_path)

            # Load using Database class
            database = Database(db_path)

            # Should be able to query the loaded database
            assert database.get_count("ATGCG") > 0, "Should be able to query loaded database"
            assert database.get_kmer_size() == 5, "Should preserve k-mer size"

    def test_database_query_performance_after_save_load(self):
        """Test that database queries work efficiently after save/load cycle."""
        counter = KmerCounter(k=7, canonical=True)

        # Create a dataset with known k-mers
        test_kmers = ["ATGCGAT", "GCGATGC", "CGATGCG"]
        for kmer in test_kmers:
            # Repeat k-mers to increase counts
            counter.count_sequence(kmer * 5)

        original_counts = {kmer: counter.get_count(kmer) for kmer in test_kmers}

        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = os.path.join(temp_dir, "performance_test_db")

            # Save and load cycle
            counter.save_to_database(db_path)
            database = Database(db_path)

            # Queries should return same results
            for kmer, expected_count in original_counts.items():
                loaded_count = database.get_count(kmer)
                assert loaded_count == expected_count, f"Query result for {kmer} should match original"

    def test_database_metadata_preservation(self):
        """Test that database metadata is preserved and accessible."""
        counter = KmerCounter(k=11, canonical=False)
        counter.count_sequence("ATGCGATGCGATGCGATGCGATG")

        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = os.path.join(temp_dir, "metadata_preserve_db")

            # Save database
            counter.save_to_database(db_path)

            # Load and check metadata through Database interface
            database = Database(db_path)

            # Database should provide access to metadata
            assert hasattr(database, 'get_metadata'), "Database should provide metadata access"
            metadata = database.get_metadata()

            assert metadata["kmer_size"] == 11, "Metadata should preserve k-mer size"
            assert metadata["canonical"] is False, "Metadata should preserve canonical setting"


class TestKmerCounterMerging:
    """Test KmerCounter merge functionality (should FAIL before implementation)."""

    def test_kmer_counter_merge_method_exists(self):
        """Test that merge method exists on KmerCounter."""
        counter1 = KmerCounter(k=5, canonical=True)
        counter2 = KmerCounter(k=5, canonical=True)

        # This should work: merge method should exist
        # Currently this FAILS because merge method isn't exposed to Python
        assert hasattr(counter1, 'merge'), "KmerCounter should have merge method"

    def test_merge_compatible_counters(self):
        """Test merging two compatible KmerCounter objects."""
        counter1 = KmerCounter(k=3, canonical=False)
        counter2 = KmerCounter(k=3, canonical=False)

        # Count different k-mers in each counter
        counter1.count_sequence("ATGCG")
        counter2.count_sequence("CGATG")

        # Merge should combine the counts
        counter1.merge(counter2)

        # Should have k-mers from both counters
        assert counter1.get_count("ATG") > 0, "Should have k-mers from first counter"
        assert counter1.get_count("CGA") > 0, "Should have k-mers from second counter"

    def test_merge_incompatible_counters_raises_error(self):
        """Test that merging incompatible counters raises appropriate error."""
        counter1 = KmerCounter(k=5, canonical=True)
        counter2 = KmerCounter(k=7, canonical=True)  # Different k-mer size
        counter3 = KmerCounter(k=5, canonical=False)  # Different canonical mode

        # Different k-mer sizes should fail
        with pytest.raises(Exception, match="k-mer size"):
            counter1.merge(counter2)

        # Different canonical modes should fail
        with pytest.raises(Exception, match="canonical"):
            counter1.merge(counter3)

    def test_merge_preserves_total_counts(self):
        """Test that merge correctly preserves total counts from both counters."""
        counter1 = KmerCounter(k=4, canonical=True)
        counter2 = KmerCounter(k=4, canonical=True)

        # Count overlapping sequences
        test_seq = "ATGCGATG"
        counter1.count_sequence(test_seq)
        counter2.count_sequence(test_seq)

        # Get counts before merge
        count_before_1 = counter1.get_count("ATGC")
        count_before_2 = counter2.get_count("ATGC")

        # Merge counters
        counter1.merge(counter2)

        # Count should be sum of both counters
        expected_count = count_before_1 + count_before_2
        actual_count = counter1.get_count("ATGC")

        assert actual_count == expected_count, "Merge should sum counts for overlapping k-mers"

    def test_merge_with_empty_counter(self):
        """Test merging with an empty counter."""
        counter1 = KmerCounter(k=3, canonical=False)
        counter2 = KmerCounter(k=3, canonical=False)

        # Add data only to first counter
        counter1.count_sequence("ATGCG")

        # Get stats before merge
        stats_before = counter1.get_stats()

        # Merge with empty counter
        counter1.merge(counter2)

        # Stats should be unchanged
        stats_after = counter1.get_stats()
        assert stats_after.total_kmers == stats_before.total_kmers, "Merge with empty counter should not change counts"

    def test_merge_multiple_counters(self):
        """Test merging multiple counters sequentially."""
        counters = []

        # Create multiple counters with different data
        for i in range(3):
            counter = KmerCounter(k=5, canonical=True)
            counter.count_sequence(f"ATGCG{i}")
            counters.append(counter)

        # Merge all into first counter
        main_counter = counters[0]
        for i in range(1, len(counters)):
            main_counter.merge(counters[i])

        # Should have accumulated all counts
        stats = main_counter.get_stats()
        assert stats.total_kmers > 0, "Merged counter should have k-mers"

    def test_merge_performance_with_large_data(self):
        """Test merge performance with larger datasets."""
        counter1 = KmerCounter(k=7, canonical=True)
        counter2 = KmerCounter(k=7, canonical=True)

        # Add substantial data to both
        large_seq = "ATGCGATGCGATGCGATGCGATGCGATGCGATGCG"
        counter1.count_sequence(large_seq * 100)
        counter2.count_sequence(large_seq * 100)

        # Merge should complete efficiently
        import time
        start_time = time.time()

        counter1.merge(counter2)

        merge_time = time.time() - start_time
        assert merge_time < 5.0, f"Merge should complete quickly, took {merge_time:.2f}s"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])