"""
Database statistics and analysis module.

This module provides classes and functions for calculating and analyzing
statistics about k-mer databases, including frequency distributions, coverage
estimation, and histogram generation.
"""

from typing import Dict, List, Optional, Any, Tuple, Union
import math
from dataclasses import dataclass, field

# Import from Rust extension if available
try:
    from ._rustkmer import (
        DatabaseStats as _DatabaseStats,
    )

    # Re-export Rust class
    DatabaseStats = _DatabaseStats

except ImportError:
    # Python fallback implementation
    @dataclass
    class DatabaseStats:
        """Statistics about a k-mer database."""
        kmer_size: int
        total_kmers: int
        unique_kmers: int
        canonical: bool
        sorted: bool
        filename: str
        uses_memory_mapping: bool

        # Computed statistics
        min_count: int = 0
        max_count: int = 0
        mean_count: float = 0.0
        median_count: float = 0.0
        coverage_estimate: float = 0.0

        # Frequency distribution (count -> number of k-mers)
        histogram: Dict[int, int] = field(default_factory=dict)

        # Percentiles
        p25: float = 0.0
        p50: float = 0.0
        p75: float = 0.0
        p95: float = 0.0
        p99: float = 0.0

        # Additional metadata
        file_size_mb: float = 0.0
        creation_date: Optional[str] = None

        def to_dict(self) -> Dict[str, Any]:
            """Convert to dictionary representation."""
            return {
                'kmer_size': self.kmer_size,
                'total_kmers': self.total_kmers,
                'unique_kmers': self.unique_kmers,
                'canonical': self.canonical,
                'sorted': self.sorted,
                'filename': self.filename,
                'uses_memory_mapping': self.uses_memory_mapping,
                'min_count': self.min_count,
                'max_count': self.max_count,
                'mean_count': self.mean_count,
                'median_count': self.median_count,
                'coverage_estimate': self.coverage_estimate,
                'histogram': self.histogram,
                'p25': self.p25,
                'p50': self.p50,
                'p75': self.p75,
                'p95': self.p95,
                'p99': self.p99,
                'file_size_mb': self.file_size_mb,
                'creation_date': self.creation_date,
            }

        def to_json(self, indent: Optional[int] = None) -> str:
            """Convert to JSON string."""
            import json
            return json.dumps(self.to_dict(), indent=indent)

        def summary(self) -> str:
            """Get a human-readable summary."""
            lines = [
                f"Database Statistics",
                f"==================",
                f"Filename: {self.filename}",
                f"K-mer size: {self.kmer_size}",
                f"Total k-mers: {self.total_kmers:,}",
                f"Unique k-mers: {self.unique_kmers:,}",
                f"Canonical: {self.canonical}",
                f"Sorted: {self.sorted}",
                f"Memory mapped: {self.uses_memory_mapping}",
                "",
                f"Count Statistics:",
                f"  Min count: {self.min_count:,}",
                f"  Max count: {self.max_count:,}",
                f"  Mean count: {self.mean_count:.2f}",
                f"  Median count: {self.median_count:.2f}",
                "",
                f"Percentiles:",
                f"  25th: {self.p25:.2f}",
                f"  50th: {self.p50:.2f}",
                f"  75th: {self.p75:.2f}",
                f"  95th: {self.p95:.2f}",
                f"  99th: {self.p99:.2f}",
                "",
                f"Coverage estimate: {self.coverage_estimate:.2%}",
            ]

            if self.file_size_mb > 0:
                lines.append(f"File size: {self.file_size_mb:.1f} MB")

            return "\n".join(lines)


def calculate_percentiles(histogram: Dict[int, int],
                         percentiles: List[float] = [25, 50, 75, 95, 99]) -> Dict[float, float]:
    """
    Calculate percentile values from histogram data.

    Args:
        histogram: Frequency distribution (count -> frequency)
        percentiles: List of percentiles to calculate

    Returns:
        Dictionary of percentile -> value
    """
    if not histogram:
        return {p: 0.0 for p in percentiles}

    # Sort by count
    sorted_items = sorted(histogram.items(), key=lambda x: x[0])

    # Flatten the distribution
    flat_dist = []
    for count, freq in sorted_items:
        flat_dist.extend([count] * freq)

    if not flat_dist:
        return {p: 0.0 for p in percentiles}

    flat_dist.sort()
    n = len(flat_dist)

    result = {}
    for percentile in percentiles:
        index = int(math.ceil(percentile / 100.0 * n) - 1)
        index = max(0, min(index, n - 1))
        result[percentile] = float(flat_dist[index])

    return result


def estimate_coverage(total_kmers: int, unique_kmers: int,
                      genome_size: Optional[int] = None,
                      k: Optional[int] = None) -> float:
    """
    Estimate genome coverage based on k-mer statistics.

    Args:
        total_kmers: Total number of k-mers (including duplicates)
        unique_kmers: Number of unique k-mers
        genome_size: Estimated genome size (optional)
        k: K-mer size (optional)

    Returns:
        Coverage estimate as a fraction (0.0 to 1.0)
    """
    if total_kmers == 0:
        return 0.0

    # Simple coverage estimate based on unique k-mers
    # This is a rough approximation - real coverage estimation requires
    # more sophisticated models
    coverage = unique_kmers / total_kmers if total_kmers > 0 else 0.0

    # If genome size is provided, try to calculate more accurate coverage
    if genome_size and k and k > 0:
        # Expected unique k-mers for random genome
        # This is approximate and ignores repeats and biases
        max_possible_unique = genome_size - k + 1
        if max_possible_unique > 0:
            coverage = unique_kmers / max_possible_unique
            # Cap at 1.0
            coverage = min(coverage, 1.0)

    return coverage


def create_histogram(data: List[int], bins: Optional[int] = None) -> Dict[int, int]:
    """
    Create a histogram from count data.

    Args:
        data: List of count values
        bins: Number of bins (None for auto)

    Returns:
        Histogram as dictionary (count -> frequency)
    """
    if not data:
        return {}

    if bins is None:
        # Simple frequency counting
        histogram = {}
        for count in data:
            histogram[count] = histogram.get(count, 0) + 1
        return histogram

    # Create bins for larger datasets
    min_val = min(data)
    max_val = max(data)

    if min_val == max_val:
        return {min_val: len(data)}

    bin_size = max(1, (max_val - min_val) // bins)
    histogram = {}

    for count in data:
        bin_index = (count - min_val) // bin_size
        bin_count = min_val + bin_index * bin_size
        histogram[bin_count] = histogram.get(bin_count, 0) + 1

    return histogram


def merge_histograms(histograms: List[Dict[int, int]]) -> Dict[int, int]:
    """
    Merge multiple histograms.

    Args:
        histograms: List of histograms to merge

    Returns:
        Merged histogram
    """
    merged = {}

    for hist in histograms:
        for count, freq in hist.items():
            merged[count] = merged.get(count, 0) + freq

    return merged


class Histogram:
    """Utility class for working with histograms."""

    def __init__(self, data: Optional[List[int]] = None):
        """Initialize histogram."""
        self.data = data or []
        self._histogram = None
        self._percentiles = None

    @property
    def histogram(self) -> Dict[int, int]:
        """Get or compute histogram."""
        if self._histogram is None:
            self._histogram = create_histogram(self.data)
        return self._histogram

    @property
    def percentiles(self) -> Dict[float, float]:
        """Get or compute percentiles."""
        if self._percentiles is None:
            self._percentiles = calculate_percentiles(self.histogram)
        return self._percentiles

    def add(self, count: int):
        """Add a count value."""
        self.data.append(count)
        # Invalidate cached values
        self._histogram = None
        self._percentiles = None

    def extend(self, counts: List[int]):
        """Add multiple count values."""
        self.data.extend(counts)
        # Invalidate cached values
        self._histogram = None
        self._percentiles = None

    def get_stats(self) -> Dict[str, Any]:
        """Get basic statistics."""
        if not self.data:
            return {}

        return {
            'count': len(self.data),
            'min': min(self.data),
            'max': max(self.data),
            'mean': sum(self.data) / len(self.data),
            'median': self.percentiles[50] if 50 in self.percentiles else 0.0,
        }


# Optional matplotlib integration (lazy import)
def plot_histogram(histogram: Dict[int, int],
                    title: str = "K-mer Count Distribution",
                    save_path: Optional[str] = None,
                    bins: Optional[int] = None) -> None:
    """
    Plot histogram using matplotlib if available.

    Args:
        histogram: Histogram data (count -> frequency)
        title: Plot title
        save_path: Path to save plot (optional)
        bins: Number of bins for aggregation
    """
    try:
        import matplotlib.pyplot as plt

        counts = list(histogram.keys())
        frequencies = list(histogram.values())

        plt.figure(figsize=(10, 6))
        plt.bar(counts, frequencies)
        plt.xlabel('K-mer Count')
        plt.ylabel('Frequency')
        plt.title(title)
        plt.grid(True, alpha=0.3)

        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
        else:
            plt.show()

    except ImportError:
        print("matplotlib not available. Install with: pip install matplotlib")
    except Exception as e:
        print(f"Error plotting histogram: {e}")


# Performance utilities for large datasets
class StreamingStatsCalculator:
    """Calculate statistics without loading all data into memory."""

    def __init__(self):
        """Initialize calculator."""
        self.total_kmers = 0
        self.unique_kmers = 0
        self.sum_counts = 0
        self.min_count = float('inf')
        self.max_count = 0
        self.histogram = {}

    def add_kmer(self, count: int):
        """Add a k-mer with its count."""
        self.total_kmers += 1
        self.unique_kmers += 1
        self.sum_counts += count
        self.min_count = min(self.min_count, count)
        self.max_count = max(self.max_count, count)
        self.histogram[count] = self.histogram.get(count, 0) + 1

    def add_batch(self, counts: List[int]):
        """Add multiple k-mers."""
        for count in counts:
            self.add_kmer(count)

    def get_mean(self) -> float:
        """Get mean count."""
        return self.sum_counts / self.unique_kmers if self.unique_kmers > 0 else 0.0

    def finalize(self) -> DatabaseStats:
        """Create final DatabaseStats object."""
        # Calculate percentiles
        percentiles = calculate_percentiles(self.histogram)

        return DatabaseStats(
            kmer_size=0,  # Will be set externally
            total_kmers=self.total_kmers,
            unique_kmers=self.unique_kmers,
            canonical=False,  # Will be set externally
            sorted=False,      # Will be set externally
            filename="",      # Will be set externally
            uses_memory_mapping=False,  # Will be set externally
            min_count=int(self.min_count) if self.min_count != float('inf') else 0,
            max_count=self.max_count,
            mean_count=self.get_mean(),
            median_count=percentiles.get(50, 0.0),
            coverage_estimate=0.0,  # Will be calculated externally
            histogram=self.histogram,
            p25=percentiles.get(25, 0.0),
            p50=percentiles.get(50, 0.0),
            p75=percentiles.get(75, 0.0),
            p95=percentiles.get(95, 0.0),
            p99=percentiles.get(99, 0.0),
        )