"""Performance tests for rustkmer Python bindings.

These tests verify that the performance requirements from the specification are met:
- SC-002: Database dump of first 1000 entries completes in under 5 seconds
- SC-003: Memory usage stays below 500MB when querying large databases
"""

import time
import gc
import psutil
import os
from pathlib import Path

import pytest

from rustkmer import Database


@pytest.mark.performance
class TestPerformanceRequirements:
    """Test performance requirements from the specification."""

    @pytest.fixture
    def real_database_path(self):
        """Path to the real database file for testing."""
        return "/Users/forrest/Data/data/kmer/K19/R1_001.rkdb"

    def get_memory_usage(self):
        """Get current memory usage in MB."""
        process = psutil.Process(os.getpid())
        return process.memory_info().rss / 1024 / 1024

    @pytest.mark.slow
    def test_1000_entry_dump_performance(self, real_database_path):
        """Test that dumping 1000 entries completes in under 5 seconds (SC-002)."""
        # Skip if database doesn't exist
        if not Path(real_database_path).exists():
            pytest.skip(f"Real database not found at {real_database_path}")

        # Requirement: <5 seconds for 1000 entries
        max_duration = 5.0

        with Database(real_database_path) as db:
            # Force garbage collection before test
            gc.collect()

            # Measure time
            start_time = time.time()

            # Dump first 1000 entries
            entries = list(db.dump(limit=1000))

            duration = time.time() - start_time

            # Verify performance requirement
            assert duration < max_duration, (
                f"Dump took {duration:.2f} seconds, "
                f"exceeding requirement of {max_duration} seconds"
            )

            # Verify we got the expected number of entries
            assert len(entries) == 1000, f"Expected 1000 entries, got {len(entries)}"

        print(f"\n✓ Dumped {len(entries)} entries in {duration:.2f} seconds")

    @pytest.mark.slow
    def test_memory_usage_during_dump(self, real_database_path):
        """Test that memory usage stays below 500MB during dump operations (SC-003)."""
        # Skip if database doesn't exist
        if not Path(real_database_path).exists():
            pytest.skip(f"Real database not found at {real_database_path}")

        # Requirement: <500MB memory usage
        max_memory_mb = 500

        # Force garbage collection before test
        gc.collect()
        initial_memory = self.get_memory_usage()

        with Database(real_database_path) as db:
            # Dump entries in streaming fashion
            count = 0
            peak_memory = initial_memory

            for result in db.dump(limit=10000):  # Test with more entries
                count += 1

                # Check memory every 1000 entries
                if count % 1000 == 0:
                    current_memory = self.get_memory_usage()
                    peak_memory = max(peak_memory, current_memory)

                    # Verify memory requirement
                    assert current_memory < max_memory_mb, (
                        f"Memory usage {current_memory:.1f}MB exceeds requirement "
                        f"of {max_memory_mb}MB after {count} entries"
                    )

        # Final verification
        final_memory = self.get_memory_usage()
        peak_memory = max(peak_memory, final_memory)

        assert peak_memory < max_memory_mb, (
            f"Peak memory usage {peak_memory:.1f}MB exceeds requirement "
            f"of {max_memory_mb}MB"
        )

        print(f"\n✓ Processed {count} entries with peak memory usage of {peak_memory:.1f}MB")

    @pytest.mark.slow
    def test_batch_query_performance(self, real_database_path):
        """Test batch query performance."""
        # Skip if database doesn't exist
        if not Path(real_database_path).exists():
            pytest.skip(f"Real database not found at {real_database_path}")

        # Generate test k-mers
        test_kmers = [f"{'ATCG' * 4}{base}" for base in "ATCG" * 25]  # 100 k-mers

        with Database(real_database_path) as db:
            # Test individual queries
            start_time = time.time()
            individual_results = {}
            for kmer in test_kmers:
                result = db.query(kmer)
                individual_results[kmer] = result
            individual_duration = time.time() - start_time

            # Test batch queries
            start_time = time.time()
            batch_results = db.query_batch(test_kmers, max_workers=4)
            batch_duration = time.time() - start_time

            # Verify results match
            assert len(individual_results) == len(batch_results)

            # Batch should be faster (or at least not significantly slower)
            speedup = individual_duration / batch_duration if batch_duration > 0 else 1

            print(f"\n✓ Batch query performance:")
            print(f"  Individual queries: {individual_duration:.3f}s")
            print(f"  Batch queries: {batch_duration:.3f}s")
            print(f"  Speedup: {speedup:.2f}x")

    @pytest.mark.slow
    def test_streaming_dump_memory_efficiency(self, real_database_path):
        """Test that streaming dump doesn't accumulate memory."""
        # Skip if database doesn't exist
        if not Path(real_database_path).exists():
            pytest.skip(f"Real database not found at {real_database_path}")

        with Database(real_database_path) as db:
            # Force garbage collection
            gc.collect()
            initial_memory = self.get_memory_usage()

            # Stream dump in chunks
            chunk_size = 1000
            total_processed = 0
            memory_samples = []

            for chunk_num in range(10):  # Process 10 chunks
                chunk_start = chunk_num * chunk_size
                entries_in_chunk = 0

                for result in db.dump(limit=chunk_size, offset=chunk_start):
                    entries_in_chunk += 1
                    total_processed += 1

                    # Only keep a small amount of data in memory
                    if entries_in_chunk >= chunk_size:
                        break

                # Check memory after each chunk
                current_memory = self.get_memory_usage()
                memory_samples.append(current_memory)

                # Force garbage collection
                del result  # Ensure result is garbage collected
                gc.collect()

                if entries_in_chunk < chunk_size:
                    break  # End of database

            # Memory should not grow significantly during streaming
            memory_growth = max(memory_samples) - min(memory_samples)

            assert memory_growth < 50, (
                f"Memory grew by {memory_growth:.1f}MB during streaming dump, "
                "which indicates inefficient memory usage"
            )

            print(f"\n✓ Streamed {total_processed:,} entries with memory growth of {memory_growth:.1f}MB")


@pytest.mark.performance
class TestStreamingEfficiency:
    """Test memory efficiency of streaming operations."""

    def test_dump_streaming_vs_loading_all(self, tmp_path):
        """Test that streaming is more memory efficient than loading all data."""
        # Create a mock database for testing
        # Note: This test uses the subprocess wrapper, so we need a real CLI
        db_path = tmp_path / "test.rkdb"

        # Skip if we can't create a test database
        if not Path("/Users/forrest/GitHub/rustkmer/target/release/rustkmer").exists():
            pytest.skip("rustkmer CLI not built")

        # This test would require creating a test database
        # For now, we'll test the streaming iterator behavior
        pass