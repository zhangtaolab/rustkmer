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


class KmerAbundanceAnalyzer:
    """
    Analyzes k-mer abundance distributions and identifies patterns.

    This class provides methods to analyze the distribution of k-mer
    counts in a database, identify rare and abundant k-mers, and
    calculate various abundance metrics.
    """

    def __init__(self, database: 'Database'):
        """
        Initialize the analyzer with a database.

        Args:
            database: Database object to analyze
        """
        self.database = database
        self._stats_cache: Optional[DatabaseStats] = None

    def get_stats(self) -> DatabaseStats:
        """
        Get cached database statistics or calculate if not cached.

        Returns:
            DatabaseStats object with comprehensive statistics
        """
        if self._stats_cache is None:
            self._stats_cache = self.database.get_stats()
        return self._stats_cache

    def analyze_abundance_distribution(self) -> Dict[str, Any]:
        """
        Analyze the k-mer abundance distribution.

        Returns:
            Dictionary containing abundance analysis results
        """
        stats = self.get_stats()
        histogram = stats.histogram

        if not histogram:
            return {
                "total_unique_kmers": 0,
                "abundance_categories": {},
                "distribution_shape": "empty",
                "gini_coefficient": 0.0,
            }

        # Categorize k-mers by abundance
        abundance_categories = {
            "singletons": 0,  # Count of 1
            "low_abundance": 0,  # 2-10
            "medium_abundance": 0,  # 11-100
            "high_abundance": 0,  # 101-1000
            "very_high_abundance": 0,  # >1000
        }

        for count, frequency in histogram.items():
            if count == 1:
                abundance_categories["singletons"] += frequency
            elif count <= 10:
                abundance_categories["low_abundance"] += frequency
            elif count <= 100:
                abundance_categories["medium_abundance"] += frequency
            elif count <= 1000:
                abundance_categories["high_abundance"] += frequency
            else:
                abundance_categories["very_high_abundance"] += frequency

        # Calculate Gini coefficient (inequality measure)
        gini = self._calculate_gini_coefficient(histogram)

        # Determine distribution shape
        distribution_shape = self._classify_distribution_shape(histogram)

        return {
            "total_unique_kmers": stats.unique_kmers,
            "abundance_categories": abundance_categories,
            "distribution_shape": distribution_shape,
            "gini_coefficient": gini,
            "histogram": dict(histogram),
        }

    def _calculate_gini_coefficient(self, histogram: Dict[int, int]) -> float:
        """
        Calculate the Gini coefficient for inequality measurement.

        Args:
            histogram: Dictionary of count -> frequency

        Returns:
            Gini coefficient (0 = perfect equality, 1 = maximal inequality)
        """
        if not histogram:
            return 0.0

        # Sort by count
        sorted_counts = sorted(histogram.items())
        total_kmers = sum(count * freq for count, freq in sorted_counts)
        cumulative_sum = 0
        gini_sum = 0

        n = len(sorted_counts)
        for i, (count, frequency) in enumerate(sorted_counts):
            cumulative_sum += count * frequency
            gini_sum += (2 * i + 1 - n) * count * frequency

        if total_kmers == 0:
            return 0.0

        return gini_sum / (n * total_kmers)

    def _classify_distribution_shape(self, histogram: Dict[int, int]) -> str:
        """
        Classify the shape of the k-mer abundance distribution.

        Args:
            histogram: Dictionary of count -> frequency

        Returns:
            String describing the distribution shape
        """
        if not histogram:
            return "empty"

        # Calculate basic statistics
        counts = list(histogram.keys())
        if len(counts) < 2:
            return "uniform"

        mean_count = sum(count * freq for count, freq in histogram.items()) / sum(histogram.values())
        median_count = sorted(counts)[len(counts) // 2]

        # Check for common patterns
        if median_count == 1 and mean_count > 10:
            return "long_tail"
        elif mean_count / median_count < 2:
            return "uniform"
        elif mean_count / median_count > 10:
            return "highly_skewed"
        else:
            return "moderately_skewed"

    def find_rare_kmers(self, threshold: int = 5) -> List[str]:
        """
        Find k-mers that appear less than or equal to a threshold.

        Args:
            threshold: Maximum count for rare k-mers

        Returns:
            List of rare k-mer sequences (placeholder - would need actual k-mers)
        """
        # This would require access to actual k-mer sequences
        # For now, return count of rare k-mers
        stats = self.get_stats()
        rare_count = sum(freq for count, freq in stats.histogram.items() if count <= threshold)

        print(f"Found {rare_count} rare k-mers with count <= {threshold}")
        # TODO: Implement actual k-mer retrieval
        return []

    def find_abundant_kmers(self, threshold: int = 100) -> List[str]:
        """
        Find k-mers that appear more than a threshold.

        Args:
            threshold: Minimum count for abundant k-mers

        Returns:
            List of abundant k-mer sequences (placeholder)
        """
        # This would require access to actual k-mer sequences
        stats = self.get_stats()
        abundant_count = sum(freq for count, freq in stats.histogram.items() if count > threshold)

        print(f"Found {abundant_count} abundant k-mers with count > {threshold}")
        # TODO: Implement actual k-mer retrieval
        return []


class DatabaseComparison:
    """
    Compare statistics between multiple databases.

    This class provides utilities to compare k-mer databases,
    identify shared and unique k-mers, and analyze differences.
    """

    def __init__(self, databases: List['Database']):
        """
        Initialize with a list of databases to compare.

        Args:
            databases: List of Database objects to compare
        """
        self.databases = databases
        self._stats_cache: List[Optional[DatabaseStats]] = [None] * len(databases)

    def get_all_stats(self) -> List[DatabaseStats]:
        """
        Get statistics for all databases.

        Returns:
            List of DatabaseStats objects
        """
        for i, db in enumerate(self.databases):
            if self._stats_cache[i] is None:
                self._stats_cache[i] = db.get_stats()
        return self._stats_cache  # type: ignore

    def compare_basic_stats(self) -> Dict[str, Any]:
        """
        Compare basic statistics across databases.

        Returns:
            Dictionary with comparison results
        """
        all_stats = self.get_all_stats()

        comparison = {
            "database_count": len(all_stats),
            "kmer_sizes": [s.kmer_size for s in all_stats],
            "unique_kmers": [s.unique_kmers for s in all_stats],
            "total_kmers": [s.total_kmers for s in all_stats],
            "overlaps": {},
            "similarities": {},
        }

        # Check if all databases have the same k-mer size
        kmer_sizes = [s.kmer_size for s in all_stats]
        comparison["same_kmer_size"] = len(set(kmer_sizes)) == 1

        # Calculate overlap estimates (simplified)
        if len(all_stats) == 2:
            min_unique = min(s.unique_kmers for s in all_stats)
            max_unique = max(s.unique_kmers for s in all_stats)
            estimated_overlap = min_unique - (max_unique - min_unique) * 0.5  # Heuristic
            comparison["overlaps"]["estimated_shared_kmers"] = max(0, int(estimated_overlap))

        return comparison

    def generate_comparison_report(self, output_path: Optional[str] = None) -> str:
        """
        Generate a detailed comparison report.

        Args:
            output_path: Optional path to save the report

        Returns:
            Report text
        """
        comparison = self.compare_basic_stats()
        all_stats = self.get_all_stats()

        lines = []
        lines.append("Database Comparison Report")
        lines.append("=" * 50)
        lines.append("")

        # Basic information
        lines.append(f"Number of databases: {comparison['database_count']}")
        lines.append(f"Same k-mer size: {comparison['same_kmer_size']}")
        lines.append("")

        # Statistics for each database
        for i, (db, stats) in enumerate(zip(self.databases, all_stats)):
            lines.append(f"Database {i + 1}:")
            lines.append(f"  File: {stats.filename}")
            lines.append(f"  K-mer size: {stats.kmer_size}")
            lines.append(f"  Unique k-mers: {stats.unique_kmers:,}")
            lines.append(f"  Total k-mers: {stats.total_kmers:,}")
            lines.append(f"  Min count: {stats.min_count}")
            lines.append(f"  Max count: {stats.max_count}")
            lines.append(f"  Mean count: {stats.mean_count:.2f}")
            lines.append(f"  Coverage: {stats.coverage_estimate:.2%}")
            lines.append("")

        # Overlap information
        if "estimated_shared_kmers" in comparison["overlaps"]:
            lines.append("Overlap Analysis:")
            lines.append(f"  Estimated shared k-mers: {comparison['overlaps']['estimated_shared_kmers']:,}")
            lines.append("")

        report = "\n".join(lines)

        if output_path:
            with open(output_path, 'w') as f:
                f.write(report)
            print(f"Comparison report saved to {output_path}")

        return report


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