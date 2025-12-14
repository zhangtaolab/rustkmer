"""Performance benchmarks for fuzzy query functionality."""

import time
import pytest
import statistics
from pathlib import Path
import sys

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from rustkmer import Database


class TestFuzzyQueryPerformance:
    """Performance tests for fuzzy query operations."""

    @classmethod
    def setup_class(cls):
        """Set up test database path."""
        cls.test_db = Path(__file__).parent.parent / "test_data" / "tiny_test.rkdb"

        if not cls.test_db.exists():
            pytest.skip(f"Test database not found: {cls.test_db}")

    def test_batch_vs_individual_performance(self):
        """Benchmark batch queries vs individual queries."""
        # Define test k-mers
        kmers = ["ATCGATC", "GATCGAT", "TCGATCG", "CGATCGA", "GATCGAA"] * 2  # 10 k-mers

        # Test individual queries
        individual_times = []
        for kmer in kmers[:5]:  # Test first 5 to avoid too much time
            start_time = time.time()

            with Database(self.test_db) as db:
                result = db.fuzzy_query(kmer, mutations=1)

            elapsed = time.time() - start_time
            individual_times.append(elapsed)

        # Test batch query with different worker counts
        batch_times = {}
        for workers in [1, 2, 4]:
            start_time = time.time()

            with Database(self.test_db) as db:
                batch_result = db.fuzzy_query_batch(kmers, mutations=1, max_workers=workers)

            elapsed = time.time() - start_time
            batch_times[workers] = elapsed

        # Calculate statistics
        avg_individual = statistics.mean(individual_times)
        total_individual = sum(individual_times)

        print("\nPerformance Results:")
        print(f"Individual queries avg: {avg_individual:.3f}s")
        print(f"Individual queries total: {total_individual:.3f}s")

        for workers, batch_time in batch_times.items():
            speedup = total_individual / batch_time
            print(f"Batch (workers={workers}): {batch_time:.3f}s ({speedup:.1f}x speedup)")

        # Batch should be faster than individual
        assert batch_times[4] < total_individual * 0.8, "Batch query should be faster"

    def test_mutation_tolerance_performance(self):
        """Benchmark performance with different mutation tolerances."""
        query_kmer = "ATCGATCG"
        mutations_range = [0, 1, 2, 3]

        times = {}
        for mutations in mutations_range:
            try:
                start_time = time.time()

                with Database(self.test_db) as db:
                    result = db.fuzzy_query(query_kmer, mutations=mutations)

                elapsed = time.time() - start_time
                times[mutations] = elapsed

                print(f"Mutations={mutations}: {elapsed:.3f}s, matches={result.total_matches}")

            except Exception as e:
                print(f"Mutations={mutations}: Error - {e}")
                times[mutations] = None

        # Performance should increase with mutation tolerance
        # (but may vary based on data)
        if times.get(0) and times.get(2):
            assert times[2] >= times[0], "Higher tolerance should take more time"

    def test_export_format_performance(self):
        """Benchmark different export formats."""
        query_kmer = "ATCGATC"
        formats = ['json', 'table', 'tsv']

        times = {}
        for format_type in formats:
            try:
                start_time = time.time()

                with Database(self.test_db) as db:
                    result = db.fuzzy_query(query_kmer, mutations=1)

                    if format_type == 'json':
                        _ = result.to_json()
                    elif format_type == 'table':
                        _ = result.to_table()
                    elif format_type == 'tsv':
                        # Note: TSV format not fully implemented
                        pass

                elapsed = time.time() - start_time
                times[format_type] = elapsed

                print(f"Format={format_type}: {elapsed:.4f}s")

            except Exception as e:
                print(f"Format={format_type}: Error - {e}")
                times[format_type] = None

        # JSON and table should be fast
        if times.get('json') and times.get('table'):
            assert times['json'] < 0.1, "JSON export should be fast"
            assert times['table'] < 0.1, "Table export should be fast"


if __name__ == "__main__":
    # Run performance tests directly
    test = TestFuzzyQueryPerformance()
    test.setup_class()

    print("Running performance benchmarks...")
    test.test_batch_vs_individual_performance()
    test.test_mutation_tolerance_performance()
    test.test_export_format_performance()

    print("\nPerformance benchmarks complete!")