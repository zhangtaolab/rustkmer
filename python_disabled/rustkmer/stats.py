"""
Database statistics and analysis module.

This module provides classes and functions for calculating and analyzing
statistics about k-mer databases, including frequency distributions, coverage
estimation, and histogram generation.
"""

from typing import Dict, List, Optional, Any, Tuple, Union
import math
from dataclasses import dataclass, field


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
        percentiles: List of percentiles to calculate (0-100)

    Returns:
        Dictionary mapping percentile to value
    """
    if not histogram:
        return {p: 0.0 for p in percentiles}

    # Sort counts
    sorted_counts = sorted(histogram.items())

    # Calculate total number of k-mers
    total_kmers = sum(freq for count, freq in sorted_counts)

    if total_kmers == 0:
        return {p: 0.0 for p in percentiles}

    # Calculate percentiles
    result = {}
    cumulative = 0

    for count, freq in sorted_counts:
        cumulative += freq
        for p in percentiles:
            if p not in result and cumulative / total_kmers >= p / 100:
                result[p] = float(count)

    # Fill missing percentiles with max value
    max_count = max(histogram.keys())
    for p in percentiles:
        if p not in result:
            result[p] = float(max_count)

    return result


def estimate_coverage(histogram: Dict[int, int],
                    genome_size: Optional[int] = None) -> float:
    """
    Estimate genome coverage from k-mer histogram.

    Args:
        histogram: K-mer frequency distribution
        genome_size: Known genome size (optional)

    Returns:
        Coverage estimate as a fraction (0-1)
    """
    if not histogram:
        return 0.0

    # Find peak frequency (most common count)
    peak_count = max(histogram.keys())
    peak_freq = histogram[peak_count]

    if genome_size:
        # If genome size is known, use more accurate estimation
        total_unique_kmers = sum(histogram.values())
        coverage = (total_unique_kmers * peak_count) / genome_size
        return min(coverage, 1.0)
    else:
        # Simple estimation based on histogram shape
        # This is a rough approximation
        total_kmers = sum(count * freq for count, freq in histogram.items())
        unique_kmers = sum(histogram.values())

        if unique_kmers == 0:
            return 0.0

        mean_count = total_kmers / unique_kmers
        # Assume coverage is roughly proportional to mean count
        return min(mean_count / peak_count, 1.0)


def calculate_statistics(histogram: Dict[int, int]) -> Dict[str, float]:
    """
    Calculate basic statistics from histogram.

    Args:
        histogram: Frequency distribution (count -> frequency)

    Returns:
        Dictionary with statistics
    """
    if not histogram:
        return {
            'min': 0.0,
            'max': 0.0,
            'mean': 0.0,
            'median': 0.0,
            'std': 0.0,
            'total_kmers': 0,
            'unique_kmers': 0,
        }

    # Calculate totals
    total_kmers = sum(count * freq for count, freq in histogram.items())
    unique_kmers = sum(histogram.values())

    # Basic stats
    counts = [count for count, freq in histogram.items() for _ in range(freq)]

    min_count = min(histogram.keys())
    max_count = max(histogram.keys())
    mean_count = total_kmers / unique_kmers if unique_kmers > 0 else 0.0

    # Median
    counts_sorted = sorted(counts)
    n = len(counts_sorted)
    if n == 0:
        median = 0.0
    elif n % 2 == 0:
        median = (counts_sorted[n//2 - 1] + counts_sorted[n//2]) / 2
    else:
        median = counts_sorted[n//2]

    # Standard deviation
    if unique_kmers > 0:
        variance = sum((count - mean_count) ** 2 * freq for count, freq in histogram.items()) / unique_kmers
        std = math.sqrt(variance)
    else:
        std = 0.0

    return {
        'min': float(min_count),
        'max': float(max_count),
        'mean': mean_count,
        'median': float(median),
        'std': std,
        'total_kmers': total_kmers,
        'unique_kmers': unique_kmers,
    }