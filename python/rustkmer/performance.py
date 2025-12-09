"""
Performance optimization utilities for RustKmer Python API.

This module provides performance-enhancing utilities including:
- Database caching
- Batch operation optimization
- Memory management helpers
- Parallel processing utilities
"""

import os
import sys
import time
import hashlib
import weakref
import threading
from typing import Dict, List, Optional, Any, Callable, Union, Iterator
from pathlib import Path
from collections import OrderedDict
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor
from functools import lru_cache, wraps
import multiprocessing as mp

# Import RustKmer classes
from . import (
    KmerCounter,
    Database,
    DatabaseExporter,
    DatabaseMerger
)
from .exceptions import RustKmerError


class DatabaseCache:
    """
    LRU cache for Database objects with automatic cleanup.

    This cache maintains recently accessed databases in memory to avoid
    repeated disk I/O operations. Uses weak references to allow
    garbage collection when memory is needed.
    """

    def __init__(self, max_size: int = 10, max_memory_mb: int = 1024):
        """
        Initialize database cache.

        Args:
            max_size: Maximum number of databases to cache
            max_memory_mb: Maximum total memory usage in MB
        """
        self.max_size = max_size
        self.max_memory_bytes = max_memory_mb * 1024 * 1024
        self._cache: OrderedDict[str, weakref.ref] = OrderedDict()
        self._sizes: Dict[str, int] = {}
        self._current_memory = 0
        self._lock = threading.RLock()

    def get(self, path: Union[str, Path]) -> Optional[Database]:
        """
        Get database from cache.

        Args:
            path: Path to database file

        Returns:
            Database object if in cache, None otherwise
        """
        path_str = str(path)

        with self._lock:
            if path_str not in self._cache:
                return None

            # Try to get weak reference
            db_ref = self._cache[path_str]
            db = db_ref()

            if db is None:
                # Database was garbage collected
                del self._cache[path_str]
                if path_str in self._sizes:
                    self._current_memory -= self._sizes[path_str]
                    del self._sizes[path_str]
                return None

            # Move to end (most recently used)
            self._cache.move_to_end(path_str)
            return db

    def put(self, path: Union[str, Path], db: Database) -> None:
        """
        Put database into cache.

        Args:
            path: Path to database file
            db: Database object to cache
        """
        path_str = str(path)

        # Estimate database memory usage
        db_size = self._estimate_db_size(db)

        with self._lock:
            # Remove if already exists
            if path_str in self._cache:
                del self._cache[path_str]
                self._current_memory -= self._sizes.get(path_str, 0)

            # Evict old entries if necessary
            while (len(self._cache) >= self.max_size or
                   self._current_memory + db_size > self.max_memory_bytes):
                if not self._cache:
                    break
                self._evict_oldest()

            # Add to cache
            self._cache[path_str] = weakref.ref(db)
            self._sizes[path_str] = db_size
            self._current_memory += db_size

    def _evict_oldest(self) -> None:
        """Evict oldest entry from cache."""
        if not self._cache:
            return

        oldest_path, oldest_ref = self._cache.popitem(last=False)
        oldest_size = self._sizes.pop(oldest_path, 0)
        self._current_memory -= oldest_size

    def _estimate_db_size(self, db: Database) -> int:
        """Estimate memory usage of database."""
        # Rough estimate based on k-mer count and k-mer size
        try:
            stats = db.get_stats()
            kmer_bytes = stats.kmer_size // 8 + 16  # Rough estimate
            return stats.total_kmers * kmer_bytes
        except:
            return 100 * 1024 * 1024  # 100MB default estimate

    def clear(self) -> None:
        """Clear all cached databases."""
        with self._lock:
            self._cache.clear()
            self._sizes.clear()
            self._current_memory = 0

    def stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        with self._lock:
            return {
                'cached_databases': len(self._cache),
                'total_memory_mb': self._current_memory / 1024 / 1024,
                'max_memory_mb': self.max_memory_bytes / 1024 / 1024,
                'hit_rate': getattr(self, '_hit_count', 0) / max(1, getattr(self, '_hit_count', 0) + getattr(self, '_miss_count', 0))
            }


class BatchProcessor:
    """
    Optimized batch processing for k-mer operations.

    This class provides efficient batch processing of k-mer operations
    with automatic optimization based on data characteristics.
    """

    def __init__(self,
                 k: int = 31,
                 threads: Optional[int] = None,
                 batch_size: int = 1000,
                 cache_dbs: bool = True):
        """
        Initialize batch processor.

        Args:
            k: K-mer size
            threads: Number of threads (default: CPU count)
            batch_size: Default batch size for operations
            cache_dbs: Whether to cache databases
        """
        self.k = k
        self.threads = threads or mp.cpu_count()
        self.batch_size = batch_size

        # Create k-mer counter with optimal settings
        self.counter = KmerCounter(k=k, threads=self.threads)

        # Database cache if enabled
        self.db_cache = DatabaseCache() if cache_dbs else None

    def count_files_batch(self,
                         file_paths: List[Union[str, Path]],
                         progress_callback: Optional[Callable] = None) -> List[Database]:
        """
        Count k-mers from multiple files efficiently.

        Args:
            file_paths: List of input file paths
            progress_callback: Optional progress callback

        Returns:
            List of Database objects
        """
        databases = []

        for i, file_path in enumerate(file_paths):
            if progress_callback:
                progress_callback(i + 1, len(file_paths))

            # Check cache first
            if self.db_cache:
                db = self.db_cache.get(file_path)
                if db:
                    databases.append(db)
                    continue

            # Count k-mers
            db = self.counter.count_from_file(str(file_path))
            databases.append(db)

            # Cache if enabled
            if self.db_cache:
                self.db_cache.put(file_path, db)

        return databases

    def query_batch(self,
                   database: Database,
                   kmers: List[str],
                   batch_size: Optional[int] = None) -> List:
        """
        Query multiple k-mers efficiently.

        Args:
            database: Database to query
            kmers: List of k-mers to query
            batch_size: Override default batch size

        Returns:
            List of query results
        """
        batch_size = batch_size or self.batch_size
        results = []

        # Process in batches
        for i in range(0, len(kmers), batch_size):
            batch = kmers[i:i + batch_size]
            batch_results = database.query_multiple(batch)
            results.extend(batch_results)

        return results

    def merge_databases_batch(self,
                             databases: List[Database],
                             output_path: Union[str, Path],
                             max_memory_mb: Optional[int] = None) -> Dict[str, Any]:
        """
        Merge multiple databases with memory optimization.

        Args:
            databases: List of databases to merge
            output_path: Output path for merged database
            max_memory_mb: Memory limit for merging

        Returns:
            Merge result information
        """
        from . import MergeConfig

        config = MergeConfig(
            threads=self.threads,
            max_memory_mb=max_memory_mb or (self.threads * 512),
            validate_checksums=True,
            preserve_metadata=True
        )

        merger = DatabaseMerger(config)
        result = merger.merge_databases(databases, str(output_path))

        return {
            'total_databases': result.total_databases,
            'successful_merges': result.successful_merges,
            'total_kmers': result.total_kmers,
            'unique_kmers': result.total_unique_kmers,
            'duplicate_rate': result.duplicate_rate,
            'merge_time': result.merge_time_seconds
        }


class ParallelProcessor:
    """
    Parallel processing utilities for k-mer operations.

    Provides both thread-based and process-based parallel processing
    optimized for different types of operations.
    """

    def __init__(self, max_workers: Optional[int] = None):
        """
        Initialize parallel processor.

        Args:
            max_workers: Maximum number of worker threads/processes
        """
        self.max_workers = max_workers or mp.cpu_count()

    def process_files_parallel(self,
                              file_paths: List[Union[str, Path]],
                              operation: str,
                              k: int = 31,
                              use_processes: bool = False) -> List:
        """
        Process files in parallel.

        Args:
            file_paths: List of file paths to process
            operation: Operation to perform ('count', 'analyze', 'export')
            k: K-mer size for counting operations
            use_processes: Use processes instead of threads

        Returns:
            List of results
        """
        if operation == 'count':
            return self._count_files_parallel(file_paths, k, use_processes)
        else:
            raise ValueError(f"Unsupported operation: {operation}")

    def _count_files_parallel(self,
                             file_paths: List[Union[str, Path]],
                             k: int,
                             use_processes: bool) -> List[Database]:
        """Count k-mers in files in parallel."""

        def count_single_file(file_path):
            counter = KmerCounter(k=k)
            return counter.count_from_file(str(file_path))

        executor_class = ProcessPoolExecutor if use_processes else ThreadPoolExecutor

        with executor_class(max_workers=self.max_workers) as executor:
            futures = [executor.submit(count_single_file, path)
                      for path in file_paths]
            databases = [future.result() for future in futures]

        return databases

    def process_chunks_parallel(self,
                               data: Any,
                               chunk_size: int,
                               processor_func: Callable,
                               use_processes: bool = True) -> List:
        """
        Process data in parallel chunks.

        Args:
            data: Data to process (list or iterable)
            chunk_size: Size of each chunk
            processor_func: Function to process each chunk
            use_processes: Use processes instead of threads

        Returns:
            List of processed results
        """
        # Split data into chunks
        if hasattr(data, '__len__'):
            chunks = [data[i:i + chunk_size]
                     for i in range(0, len(data), chunk_size)]
        else:
            # For iterables, collect chunks manually
            chunks = []
            chunk = []
            for item in data:
                chunk.append(item)
                if len(chunk) >= chunk_size:
                    chunks.append(chunk)
                    chunk = []
            if chunk:
                chunks.append(chunk)

        executor_class = ProcessPoolExecutor if use_processes else ThreadPoolExecutor

        with executor_class(max_workers=self.max_workers) as executor:
            futures = [executor.submit(processor_func, chunk)
                      for chunk in chunks]
            results = [future.result() for future in futures]

        return results


def timer(func: Callable) -> Callable:
    """
    Decorator to time function execution.

    Args:
        func: Function to time

    Returns:
        Wrapped function that logs execution time
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        start = time.time()
        try:
            result = func(*args, **kwargs)
            return result
        finally:
            elapsed = time.time() - start
            print(f"{func.__name__} executed in {elapsed:.2f} seconds")

    return wrapper


def memory_monitor(threshold_gb: float = 4.0) -> Callable:
    """
    Decorator to monitor memory usage.

    Args:
        threshold_gb: Memory usage threshold in GB

    Returns:
        Wrapped function that checks memory usage
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            import psutil
            import os

            process = psutil.Process(os.getpid())
            initial_memory = process.memory_info().rss / 1024 / 1024 / 1024

            try:
                result = func(*args, **kwargs)

                final_memory = process.memory_info().rss / 1024 / 1024 / 1024
                memory_used = final_memory - initial_memory

                if memory_used > threshold_gb:
                    print(f"WARNING: {func.__name__} used {memory_used:.2f} GB RAM")

                return result
            except MemoryError:
                print(f"MemoryError in {func.__name__}: {initial_memory:.2f} GB used")
                raise

        return wrapper
    return decorator


@lru_cache(maxsize=1024)
def kmer_hash_cache(kmer: str) -> int:
    """
    Cached k-mer hash calculation.

    Args:
        kmer: K-mer to hash

    Returns:
        Hash value
    """
    from .utils import calculate_kmer_hash
    return calculate_kmer_hash(kmer)


def optimize_kmer_operations(kmer_list: List[str],
                           operation: str) -> Dict[str, Any]:
    """
    Analyze and optimize k-mer operations.

    Args:
        kmer_list: List of k-mers to analyze
        operation: Type of operation ('query', 'count', 'hash')

    Returns:
        Optimization recommendations
    """
    analysis = {
        'total_kmers': len(kmer_list),
        'unique_kmers': len(set(kmer_list)),
        'duplicate_rate': 0,
        'recommendations': []
    }

    # Calculate duplicate rate
    if analysis['total_kmers'] > 0:
        analysis['duplicate_rate'] = 1 - (analysis['unique_kmers'] / analysis['total_kmers'])

    # Generate recommendations
    if analysis['duplicate_rate'] > 0.3:
        analysis['recommendations'].append(
            "High duplicate rate (>30%). Consider using set() to remove duplicates."
        )

    if analysis['total_kmers'] > 100000:
        analysis['recommendations'].append(
            "Large k-mer list (>100k). Consider batch processing."
        )

    if operation == 'query':
        if analysis['total_kmers'] < 100:
            analysis['recommendations'].append(
                "Small query list (<100). Individual queries may be faster."
            )
        else:
            analysis['recommendations'].append(
                "Use batch querying for better performance."
            )

    return analysis


# Performance monitoring utilities
class PerformanceMonitor:
    """Monitor and log performance metrics."""

    def __init__(self):
        self.metrics: Dict[str, List[float]] = {}
        self.start_times: Dict[str, float] = {}

    def start_timer(self, operation: str):
        """Start timing an operation."""
        self.start_times[operation] = time.time()

    def end_timer(self, operation: str) -> float:
        """End timing and record duration."""
        if operation not in self.start_times:
            raise ValueError(f"Timer not started for operation: {operation}")

        duration = time.time() - self.start_times[operation]
        if operation not in self.metrics:
            self.metrics[operation] = []
        self.metrics[operation].append(duration)

        return duration

    def get_stats(self) -> Dict[str, Dict[str, float]]:
        """Get performance statistics."""
        stats = {}
        for operation, times in self.metrics.items():
            if times:
                stats[operation] = {
                    'count': len(times),
                    'total': sum(times),
                    'average': sum(times) / len(times),
                    'min': min(times),
                    'max': max(times)
                }
        return stats

    def report(self) -> str:
        """Generate performance report."""
        stats = self.get_stats()
        report = ["Performance Report:", "-" * 40]

        for operation, data in stats.items():
            report.append(f"{operation}:")
            report.append(f"  Count: {data['count']}")
            report.append(f"  Total: {data['total']:.2f}s")
            report.append(f"  Average: {data['average']:.2f}s")
            report.append(f"  Min: {data['min']:.2f}s")
            report.append(f"  Max: {data['max']:.2f}s")
            report.append("")

        return "\n".join(report)


# Global performance monitor instance
performance_monitor = PerformanceMonitor()