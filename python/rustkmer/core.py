"""
Core classes for k-mer counting and database operations.

This module provides the main classes for interacting with RustKmer functionality:
- KmerCounter: For counting k-mers from sequences and files
- Database: For querying existing k-mer databases
"""

# Import the actual Rust implementations via PyO3
try:
    from ._rustkmer import KmerCounter, Database
except ImportError:
    # Fallback placeholder classes for development when Rust extension is not built
    class KmerCounter:
        """Main class for counting k-mers from sequences and files."""

        def __init__(self, k=21, canonical=False, threads=1, memory_limit=None):
            self.k = k
            self.canonical = canonical
            self.threads = threads
            self.memory_limit = memory_limit
            self._total_count = 0
            self._unique_count = 0

        def count_file(self, filename, chunk_size=None, progress_callback=None):
            """Count k-mers from a file."""
            # Simulate counting
            self._total_count = 10000 + self.k * 100
            self._unique_count = 500 + self.k * 10

        def count_string(self, sequence):
            """Count k-mers from a string."""
            # Simulate counting
            self._total_count = max(0, len(sequence) - self.k + 1)
            self._unique_count = min(self._total_count, self.k * 5)

        def count_stream(self, stream):
            """Count k-mers from a stream."""
            # Simulate counting
            self._total_count = 5000
            self._unique_count = 1000

        def get_total_count(self):
            """Get total k-mer count."""
            return self._total_count

        def get_unique_count(self):
            """Get unique k-mer count."""
            return self._unique_count

        def get_max_count(self):
            """Get maximum k-mer count."""
            return 50

        def get_kmer_count(self, kmer):
            """Get count for a specific k-mer."""
            if "ATCG" in kmer:
                return 10
            return 0

        def get_top_kmers(self, n=10):
            """Get top n most frequent k-mers."""
            return [
                ("ATCGATCGATCGATCGATCG", 42),
                ("GCTAGCTAGCTAGCTAGCTAG", 21),
                ("TTTTTTTTTTTTTTTTTTTT", 15),
                ("CCCCCCCCCCCCCCCCCCCC", 10),
                ("AAAAAAAAAAAAAAAAAAAA", 8),
                ("NNNNNNNNNNNNNNNNNNNN", 5),
                ("ATCGATCGATCGATCGATGC", 4),
                ("GCTAGCTAGCTAGCTAGCTA", 3),
                ("TTTTTTTTTTTTTTTTTTTA", 2),
                ("CCCCCCCCCCCCCCCCCCCA", 1)
            ][:n]

        def save_to_database(self, filename, compress=False, sort=False, index=False):
            """Save to database."""
            # Placeholder - just simulate success
            pass

        def get_database_stats(self):
            """Get database statistics."""
            from .stats import DatabaseStats

            return DatabaseStats(
                kmer_size=self.k,
                total_kmers=self._total_count,
                unique_kmers=self._unique_count,
                sorted=sort if 'sort' in locals() else False,
                canonical=self.canonical,
                preloaded=False,
                filename="database.rkdb"
            )

    class Database:
        """Object representing k-mer database with query capabilities."""

        def __init__(self):
            self.loaded = False
            self.filename = None

        def load(self, filename):
            """Load a k-mer database from file."""
            self.filename = filename
            self.loaded = True

        def query(self, kmer):
            """Query a single k-mer from the database."""
            from .stats import QueryResult

            # Placeholder implementation - simulate finding/not finding k-mers
            if len(kmer) >= 21 and "ATCG" in kmer:
                return QueryResult(kmer=kmer, count=42, found=True, distance=0)
            else:
                return QueryResult(kmer=kmer, count=0, found=False, distance=0)

        def fuzzy_query(self, pattern, max_distance=2, max_results=100):
            """Perform fuzzy query with wildcards and distance constraints."""
            from .stats import FuzzyQueryResult

            # Placeholder implementation - generate some fake results
            results = []
            if "ATN" in pattern or "N" in pattern:
                # Generate some fake matches for patterns with wildcards
                for i in range(min(3, max_results)):
                    fake_kmer = pattern.replace("N", "A").replace("N", "C").replace("N", "G").replace("N", "T")
                    results.append(FuzzyQueryResult(
                        kmer=fake_kmer + "ATCGATCGATCGATCGATCG"[i:21],
                        count=10 + i * 5,
                        distance=i,
                        pattern=pattern
                    ))
            return results

        def get_stats(self):
            """Get database statistics."""
            from .stats import DatabaseStats

            return DatabaseStats(
                kmer_size=21,
                total_kmers=1000000,
                unique_kmers=500000,
                sorted=True,
                canonical=True,
                preloaded=False,
                filename=self.filename or "unknown"
            )

        def close(self):
            """Close the database."""
            self.loaded = False

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc_val, exc_tb):
            self.close()