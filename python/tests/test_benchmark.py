"""Benchmark tests for rustkmer Python bindings.

These tests measure and report performance metrics for the dump operation
as specified in the requirements.
"""

import time
import psutil
import os
import json
from pathlib import Path
from datetime import datetime

import pytest

from rustkmer import Database


@pytest.mark.benchmark
class TestDumpBenchmark:
    """Benchmark tests for database dump operations."""

    @pytest.fixture
    def real_database_path(self):
        """Path to the real database file for testing."""
        return "/Users/forrest/Data/data/kmer/K19/R1_001.rkdb"

    @pytest.fixture
    def benchmark_results(self):
        """Store benchmark results for reporting."""
        return {
            "timestamp": datetime.now().isoformat(),
            "database": None,
            "results": {}
        }

    def get_memory_usage(self):
        """Get current memory usage in MB."""
        process = psutil.Process(os.getpid())
        return {
            "rss": process.memory_info().rss / 1024 / 1024,  # Resident Set Size
            "vms": process.memory_info().vms / 1024 / 1024,  # Virtual Memory Size
        }

    def save_benchmark_report(self, results, filename="benchmark_report.json"):
        """Save benchmark results to a JSON file."""
        report_path = Path(__file__).parent / filename
        with open(report_path, 'w') as f:
            json.dump(results, f, indent=2)
        print(f"\nBenchmark report saved to: {report_path}")

    @pytest.mark.slow
    def test_dump_1000_entries_benchmark(self, real_database_path, benchmark_results):
        """Benchmark dumping 1000 entries as required by SC-002."""
        # Skip if database doesn't exist
        if not Path(real_database_path).exists():
            pytest.skip(f"Real database not found at {real_database_path}")

        # Store database info
        benchmark_results["database"] = real_database_path
        db_size_mb = Path(real_database_path).stat().st_size / 1024 / 1024
        benchmark_results["database_size_mb"] = db_size_mb

        print(f"\n=== Dump Benchmark (1000 entries) ===")
        print(f"Database: {real_database_path}")
        print(f"Database size: {db_size_mb:.1f} MB")

        with Database(real_database_path) as db:
            # Get stats for context
            stats = db.stats()
            print(f"Total k-mers in database: {stats.unique_kmers:,}")

            # Benchmark configuration
            limit = 1000
            iterations = 5  # Run multiple times for average
            durations = []
            memory_usage = []

            print(f"\nRunning {iterations} iterations of dumping {limit} entries...")

            for i in range(iterations):
                # Measure memory before
                memory_before = self.get_memory_usage()

                # Measure time
                start_time = time.perf_counter()

                # Perform dump
                entries = list(db.dump(limit=limit))

                # Measure time and memory after
                duration = time.perf_counter() - start_time
                memory_after = self.get_memory_usage()

                durations.append(duration)
                memory_usage.append({
                    "before": memory_before,
                    "after": memory_after,
                    "peak": max(memory_before["rss"], memory_after["rss"]),
                    "delta": memory_after["rss"] - memory_before["rss"]
                })

                # Verify we got the expected number of entries
                assert len(entries) == limit, f"Iteration {i+1}: Expected {limit} entries, got {len(entries)}"

                print(f"  Iteration {i+1}: {duration:.3f}s, "
                      f"{memory_usage[-1]['peak']:.1f}MB RSS")

                # Small delay between iterations
                time.sleep(0.1)

            # Calculate statistics
            avg_duration = sum(durations) / len(durations)
            min_duration = min(durations)
            max_duration = max(durations)
            entries_per_second = limit / avg_duration

            avg_memory_peak = sum(m["peak"] for m in memory_usage) / len(memory_usage)
            max_memory_delta = max(m["delta"] for m in memory_usage)

            # Store results
            benchmark_results["results"]["dump_1000"] = {
                "entries": limit,
                "iterations": iterations,
                "duration": {
                    "average": avg_duration,
                    "min": min_duration,
                    "max": max_duration,
                    "unit": "seconds"
                },
                "throughput": {
                    "entries_per_second": entries_per_second,
                    "microseconds_per_entry": (avg_duration * 1000000) / limit
                },
                "memory": {
                    "peak_rss_mb_avg": avg_memory_peak,
                    "max_memory_increase_mb": max_memory_delta
                },
                "requirements_met": {
                    "sc_002_time": avg_duration < 5.0,  # <5 seconds for 1000 entries
                    "sc_003_memory": max_memory_delta < 100  # Reasonable memory increase
                }
            }

            # Print results
            print(f"\n--- Results ---")
            print(f"Average duration: {avg_duration:.3f}s (min: {min_duration:.3f}s, max: {max_duration:.3f}s)")
            print(f"Throughput: {entries_per_second:.0f} entries/second")
            print(f"Average peak RSS: {avg_memory_peak:.1f} MB")
            print(f"Maximum memory increase: {max_memory_delta:.1f} MB")

            # Verify requirements
            print(f"\n--- Requirements Check ---")
            if avg_duration < 5.0:
                print(f"✓ SC-002: Time requirement met ({avg_duration:.3f}s < 5s)")
            else:
                print(f"✗ SC-002: Time requirement FAILED ({avg_duration:.3f}s >= 5s)")

            # This is not the full 500MB requirement, just for this operation
            if max_memory_delta < 100:
                print(f"✓ Memory usage is reasonable ({max_memory_delta:.1f}MB increase)")
            else:
                print(f"⚠ Memory usage is high ({max_memory_delta:.1f}MB increase)")

        # Save benchmark report
        self.save_benchmark_report(benchmark_results)

    @pytest.mark.slow
    def test_dump_scaling_benchmark(self, real_database_path, benchmark_results):
        """Benchmark dump performance with different batch sizes."""
        # Skip if database doesn't exist
        if not Path(real_database_path).exists():
            pytest.skip(f"Real database not found at {real_database_path}")

        print(f"\n=== Dump Scaling Benchmark ===")

        # Test different dump sizes
        test_sizes = [100, 500, 1000, 5000]
        results = {}

        with Database(real_database_path) as db:
            for size in test_sizes:
                print(f"\nTesting dump size: {size} entries")

                durations = []
                for i in range(3):  # 3 iterations per size
                    start_time = time.perf_counter()
                    entries = list(db.dump(limit=size))
                    duration = time.perf_counter() - start_time

                    assert len(entries) == size, f"Expected {size}, got {len(entries)}"
                    durations.append(duration)

                avg_duration = sum(durations) / len(durations)
                entries_per_second = size / avg_duration

                results[f"dump_{size}"] = {
                    "entries": size,
                    "avg_duration": avg_duration,
                    "entries_per_second": entries_per_second
                }

                print(f"  Average: {avg_duration:.3f}s, "
                      f"{entries_per_second:.0f} entries/sec")

        # Store scaling results
        benchmark_results["results"]["dump_scaling"] = results

        # Analyze scaling
        print(f"\n--- Scaling Analysis ---")
        for size in test_sizes:
            result = results[f"dump_{size}"]
            # Calculate time per entry
            time_per_entry = result["avg_duration"] * 1000 / size  # milliseconds
            print(f"{size:5d} entries: {time_per_entry:.3f}ms/entry")

    @pytest.mark.slow
    def test_streaming_vs_list_benchmark(self, real_database_path, benchmark_results):
        """Compare streaming iteration vs list creation."""
        # Skip if database doesn't exist
        if not Path(real_database_path).exists():
            pytest.skip(f"Real database not found at {real_database_path}")

        print(f"\n=== Streaming vs List Benchmark ===")

        limit = 1000

        with Database(real_database_path) as db:
            # Benchmark list creation
            print(f"\nTesting list creation ({limit} entries)...")
            start_time = time.perf_counter()
            memory_before = self.get_memory_usage()

            entries = list(db.dump(limit=limit))

            list_duration = time.perf_counter() - start_time
            memory_after_list = self.get_memory_usage()
            memory_for_list = memory_after_list["rss"] - memory_before["rss"]

            print(f"  Duration: {list_duration:.3f}s")
            print(f"  Memory for list: {memory_for_list:.1f} MB")
            print(f"  Memory per entry: {memory_for_list * 1024 / limit:.1f} KB")

            # Clear memory
            del entries
            import gc
            gc.collect()

            # Benchmark streaming iteration
            print(f"\nTesting streaming iteration ({limit} entries)...")
            start_time = time.perf_counter()
            memory_before = self.get_memory_usage()

            count = 0
            for result in db.dump(limit=limit):
                count += 1
                # Simulate minimal processing
                _ = result.count

            stream_duration = time.perf_counter() - start_time
            memory_after_stream = self.get_memory_usage()
            memory_for_stream = memory_after_stream["rss"] - memory_before["rss"]

            print(f"  Duration: {stream_duration:.3f}s")
            print(f"  Memory increase: {memory_for_stream:.1f} MB")

            # Verify counts
            assert count == limit, f"Streamed {count} entries, expected {limit}"

            # Compare
            print(f"\n--- Comparison ---")
            time_diff = list_duration - stream_duration
            memory_diff = memory_for_list - memory_for_stream

            print(f"Time difference: {time_diff:.3f}s (list is {'faster' if time_diff < 0 else 'slower'})")
            print(f"Memory difference: {memory_diff:.1f} MB (list uses {'more' if memory_diff > 0 else 'less'} memory)")

            # Store results
            benchmark_results["results"]["streaming_vs_list"] = {
                "list": {
                    "duration": list_duration,
                    "memory_mb": memory_for_list
                },
                "stream": {
                    "duration": stream_duration,
                    "memory_mb": memory_for_stream
                },
                "difference": {
                    "time_ms": (list_duration - stream_duration) * 1000,
                    "memory_mb": memory_diff
                }
            }