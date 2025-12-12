"""
High-level Python wrapper for RustKmer KmerCounter.

This module provides a more Pythonic interface to the KmerCounter with additional
convenience methods and integration with Python ecosystem libraries.
"""

import rustkmer
from typing import Dict, List, Tuple, Optional, Union, Iterator, Any
from collections import Counter
import json
import csv
import os


class KmerCounter:
    """
    High-level Python wrapper for RustKmer K-mer counting functionality.

    This class provides a Pythonic interface with additional convenience methods
    for working with k-mer data in the Python ecosystem.
    """

    def __init__(self, k: int, canonical: bool = False, threads: int = 1):
        """
        Initialize a KmerCounter.

        Args:
            k: K-mer size (length of k-mers to count)
            canonical: Whether to count canonical k-mers (lexicographically smaller
                       of kmer and its reverse complement)
            threads: Number of threads to use (for future Rust implementation)
        """
        self._counter = rustkmer.KmerCounter(k, canonical, threads)
        self.k = k
        self.canonical = canonical
        self.threads = threads

    # Delegate basic methods to the underlying counter
    def count_string(self, sequence: str, progress_callback=None) -> Dict[str, int]:
        """Count k-mers in a DNA sequence string."""
        return self._counter.count_string(sequence, progress_callback)

    def count_file(self, file_path: str, progress_callback=None) -> Dict[str, int]:
        """Count k-mers in a FASTA or FASTQ file."""
        return self._counter.count_file(file_path, progress_callback)

    def get_count(self, kmer: str) -> int:
        """Get count for a specific k-mer."""
        return self._counter.get_count(kmer)

    def get_k(self) -> int:
        """Get the k-mer size."""
        return self._counter.get_k()

    def get_canonical(self) -> bool:
        """Check if counting canonical k-mers."""
        return self._counter.get_canonical()

    def get_threads(self) -> int:
        """Get the thread count."""
        return self._counter.get_threads()

    def get_total_count(self) -> int:
        """Get total k-mer count."""
        return self._counter.get_total_count()

    def get_unique_count(self) -> int:
        """Get number of unique k-mers."""
        return self._counter.get_unique_count()

    def get_all_counts(self) -> Dict[str, int]:
        """Get all k-mer counts."""
        return self._counter.get_all_counts()

    def get_top_kmers(self, n: int) -> List[Tuple[str, int]]:
        """Get top N most frequent k-mers."""
        return self._counter.get_top_kmers(n)

    def get_stats(self) -> rustkmer.CounterStats:
        """Get statistics for this counter."""
        return self._counter.get_stats()

    def reset(self) -> None:
        """Reset the counter (clear all counts)."""
        return self._counter.reset()

    # Additional Pythonic methods

    def __len__(self) -> int:
        """Return the number of unique k-mers."""
        return self.get_unique_count()

    def __contains__(self, kmer: str) -> bool:
        """Check if a k-mer exists in the counter."""
        return self.get_count(kmer) > 0

    def __getitem__(self, kmer: str) -> int:
        """Get count for a k-mer using dictionary syntax."""
        return self.get_count(kmer)

    def __iter__(self) -> Iterator[Tuple[str, int]]:
        """Iterate over k-mer, count pairs."""
        for kmer, count in self.get_all_counts().items():
            yield (kmer, count)

    def items(self) -> Iterator[Tuple[str, int]]:
        """Return iterator over (kmer, count) pairs."""
        return iter(self)

    def keys(self) -> Iterator[str]:
        """Return iterator over k-mer keys."""
        return (kmer for kmer, _ in self)

    def values(self) -> Iterator[int]:
        """Return iterator over count values."""
        return (count for _, count in self)

    def most_common(self, n: Optional[int] = None) -> List[Tuple[str, int]]:
        """
        Return most common k-mers and their counts.

        Similar to collections.Counter.most_common().

        Args:
            n: Number of most common items to return. If None, return all.

        Returns:
            List of (kmer, count) tuples sorted by count descending.
        """
        all_counts = self.get_all_counts()
        counter = Counter(all_counts)
        return counter.most_common(n)

    def frequencies(self) -> Dict[int, int]:
        """
        Get frequency distribution of counts.

        Returns:
            Dictionary mapping count -> number of k-mers with that count.
        """
        freq = {}
        for count in self.get_all_counts().values():
            freq[count] = freq.get(count, 0) + 1
        return freq

    def filter(self, min_count: int = 1, max_count: Optional[int] = None) -> Dict[str, int]:
        """
        Filter k-mers by count range.

        Args:
            min_count: Minimum count (inclusive)
            max_count: Maximum count (inclusive), if None, no upper limit

        Returns:
            Dictionary of filtered k-mers and their counts.
        """
        return self._counter.filter_by_count(min_count, max_count)

    def to_pandas_dataframe(self):
        """
        Convert k-mer counts to a pandas DataFrame.

        Returns:
            pandas.DataFrame with columns ['kmer', 'count']
        """
        try:
            import pandas as pd
        except ImportError:
            raise ImportError("pandas is required for to_pandas_dataframe(). Install with: pip install pandas")

        counts = self.get_all_counts()
        df = pd.DataFrame(list(counts.items()), columns=['kmer', 'count'])
        df = df.sort_values('count', ascending=False).reset_index(drop=True)
        return df

    def to_csv(self, file_path: str, sep: str = ',', header: bool = True):
        """
        Save k-mer counts to a CSV file.

        Args:
            file_path: Output CSV file path
            sep: Separator character (default: comma)
            header: Whether to write header row
        """
        counts = self.get_all_counts()
        with open(file_path, 'w', newline='') as f:
            writer = csv.writer(f, delimiter=sep)
            if header:
                writer.writerow(['kmer', 'count'])
            for kmer, count in sorted(counts.items(), key=lambda x: x[1], reverse=True):
                writer.writerow([kmer, count])

    def from_csv(self, file_path: str, sep: str = ',', header: bool = True):
        """
        Load k-mer counts from a CSV file.

        Note: This creates a new counter with the loaded data.

        Args:
            file_path: Input CSV file path
            sep: Separator character (default: comma)
            header: Whether file has header row
        """
        # Create a new counter to load data into
        loaded_counts = {}
        with open(file_path, 'r') as f:
            reader = csv.reader(f, delimiter=sep)
            if header:
                next(reader)  # Skip header
            for kmer, count in reader:
                loaded_counts[kmer] = int(count)

        # Replace current counter's data
        self._counter.counts = loaded_counts

    def to_json(self, file_path: str, indent: Optional[int] = None):
        """
        Save k-mer counts to a JSON file.

        Args:
            file_path: Output JSON file path
            indent: JSON indentation level (None for compact)
        """
        counts = self.get_all_counts()
        data = {
            'k': self.k,
            'canonical': self.canonical,
            'counts': counts,
            'stats': {
                'total_kmers': self.get_unique_count(),
                'total_count': self.get_total_count()
            }
        }
        with open(file_path, 'w') as f:
            json.dump(data, f, indent=indent, sort_keys=True)

    def from_json(self, file_path: str):
        """
        Load k-mer counts from a JSON file.

        Note: This creates a new counter with the loaded data.

        Args:
            file_path: Input JSON file path
        """
        with open(file_path, 'r') as f:
            data = json.load(f)

        # Validate data structure
        if data.get('k') != self.k:
            raise ValueError(f"K-mer size mismatch: file has k={data.get('k')}, counter has k={self.k}")

        if data.get('canonical') != self.canonical:
            raise ValueError(f"Canonical mode mismatch: file has canonical={data.get('canonical')}, counter has canonical={self.canonical}")

        # Load counts
        loaded_counts = {kmer: int(count) for kmer, count in data['counts'].items()}
        self._counter.counts = loaded_counts

    def merge_with(self, other: 'KmerCounter') -> None:
        """
        Merge another KmerCounter into this one.

        Args:
            other: Another KmerCounter to merge with

        Raises:
            ValueError: If counters have incompatible settings
        """
        if self.k != other.k:
            raise ValueError(f"Cannot merge counters with different k-mer sizes: {self.k} vs {other.k}")
        if self.canonical != other.canonical:
            raise ValueError(f"Cannot merge counters with different canonical modes: {self.canonical} vs {other.canonical}")

        self._counter.merge(other._counter)

    def save_database(self, database_path: str, compression: bool = True) -> None:
        """
        Save k-mer counts to a database file.

        Args:
            database_path: Output database file path
            compression: Whether to use compression (when supported)
        """
        self._counter.save_to_database(database_path, compression)

    def __repr__(self) -> str:
        """String representation of the KmerCounter."""
        return f"KmerCounter(k={self.k}, canonical={self.canonical}, unique_kmers={self.get_unique_count()})"

    def __str__(self) -> str:
        """User-friendly string representation."""
        stats = self.get_stats()
        # Handle both dict and object return types for compatibility
        if isinstance(stats, dict):
            return (f"KmerCounter:\n"
                    f"  K-mer size: {self.k}\n"
                    f"  Canonical: {self.canonical}\n"
                    f"  Unique k-mers: {stats['total_kmers']}\n"
                    f"  Total counts: {stats['total_count']}\n"
                    f"  Average count: {stats['average_count']:.2f}\n"
                    f"  Max count: {stats['max_count']}")
        else:
            return (f"KmerCounter:\n"
                    f"  K-mer size: {self.k}\n"
                    f"  Canonical: {self.canonical}\n"
                    f"  Unique k-mers: {stats.total_kmers}\n"
                    f"  Total counts: {stats.total_count}\n"
                    f"  Average count: {stats.average_count:.2f}\n"
                    f"  Max count: {stats.max_count}")

    def summary(self) -> Dict[str, Any]:
        """
        Get a summary dictionary of counter information.

        Returns:
            Dictionary with counter statistics and metadata.
        """
        stats = self.get_stats()
        # Handle both dict and object return types for compatibility
        if isinstance(stats, dict):
            return {
                'k': self.k,
                'canonical': self.canonical,
                'threads': self.threads,
                'unique_kmers': stats['total_kmers'],
                'total_counts': stats['total_count'],
                'average_count': stats['average_count'],
                'median_count': stats['median_count'],
                'max_count': stats['max_count'],
                'frequency_distribution': self.frequencies()
            }
        else:
            return {
                'k': self.k,
                'canonical': self.canonical,
                'threads': self.threads,
                'unique_kmers': stats.total_kmers,
                'total_counts': stats.total_count,
                'average_count': stats.average_count,
                'median_count': stats.median_count,
                'max_count': stats.max_count,
                'frequency_distribution': self.frequencies()
            }


# Convenience function
def count_kmers(sequence: str, k: int, canonical: bool = False) -> Dict[str, int]:
    """
    Convenience function to count k-mers in a sequence.

    Args:
        sequence: DNA sequence string
        k: K-mer size
        canonical: Whether to count canonical k-mers

    Returns:
        Dictionary of k-mer counts
    """
    counter = KmerCounter(k, canonical)
    return counter.count_string(sequence)


def count_kmers_file(file_path: str, k: int, canonical: bool = False,
                    progress_callback=None) -> Dict[str, int]:
    """
    Convenience function to count k-mers in a file.

    Args:
        file_path: Path to FASTA/FASTQ file
        k: K-mer size
        canonical: Whether to count canonical k-mers
        progress_callback: Optional progress callback

    Returns:
        Dictionary of k-mer counts
    """
    counter = KmerCounter(k, canonical)
    return counter.count_file(file_path, progress_callback)