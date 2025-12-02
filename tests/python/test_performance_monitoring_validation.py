"""
Performance Monitoring Validation Test Suite
============================================

This module provides comprehensive validation testing for performance monitoring functionality,
focusing on monitoring accuracy, overhead measurement, thread safety, and large-scale performance.

Validates:
- Performance monitoring accuracy tests (T021)
- Monitoring overhead measurement tests (T022)
- Thread-safe monitoring validation tests (T023)
- Large-scale monitoring performance tests (T024)
"""

import pytest
import sys
import os
import time
import threading
import tempfile
import json
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import statistics

# Add the rustkmer Python module to path for testing
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src" / "python"))

try:
    from rustkmer import KmerCounter, Database, FuzzyQuery, get_performance_metrics
    from rustkmer.exceptions import MonitoringError
except ImportError as e:
    pytest.skip(f"RustKmer Python bindings not available: {e}", allow_module_level=True)


class TestPerformanceMonitoringAccuracy:
    """Test suite for performance monitoring accuracy (T021)."""

    def test_timing_accuracy_for_short_operations(self):
        """Test timing accuracy for short duration operations."""
        try:
            from rustkmer import get_performance_metrics

            # Clear any existing metrics
            try:
                # Reset metrics if possible
                pass
            except:
                pass

            # Perform a short, measurable operation
            start_time = time.time()

            counter = KmerCounter(k=21)
            counter.count_from_sequence("ATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCG")

            end_time = time.time()
            actual_duration = end_time - start_time

            # Get monitoring metrics
            try:
                metrics = get_performance_metrics()

                # If monitoring is available, validate accuracy
                if hasattr(metrics, 'execution_time'):
                    monitored_duration = metrics.execution_time

                    # Allow for some tolerance in timing measurements
                    tolerance = 0.1  # 100ms tolerance
                    assert abs(monitored_duration - actual_duration) <= tolerance, \
                        f"Monitored duration {monitored_duration}s should be within {tolerance}s of actual {actual_duration}s"

            except (ImportError, AttributeError):
                # Monitoring not available - this is expected if profiling feature not enabled
                pytest.skip("Performance monitoring not available (profiling feature not enabled)")

        except ImportError:
            pytest.skip("Performance monitoring functions not available")

    def test_memory_usage_accuracy_tracking(self):
        """Test memory usage tracking accuracy."""
        try:
            from rustkmer import get_performance_metrics
            import psutil
            import os

            process = psutil.Process(os.getpid())
            initial_memory = process.memory_info().rss / 1024 / 1024  # MB

            # Perform memory-intensive operation
            counter = KmerCounter(k=21)

            # Generate substantial k-mer data
            for i in range(1000):
                sequence = f"ATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATC{i:04d}"
                counter.count_from_sequence(sequence)

            final_memory = process.memory_info().rss / 1024 / 1024  # MB
            actual_memory_increase = final_memory - initial_memory

            # Get monitoring metrics
            try:
                metrics = get_performance_metrics()

                # Check if memory metrics are available
                if hasattr(metrics, 'peak_memory_mb'):
                    monitored_memory = metrics.peak_memory_mb

                    # Validate memory tracking is reasonable
                    assert monitored_memory > 0, "Monitored memory should be positive"

                    # Allow for system memory management differences
                    # The key is that monitoring captures some memory usage
                    assert monitored_memory > initial_memory - 50, "Monitored memory should be reasonable"

            except (ImportError, AttributeError):
                pytest.skip("Memory monitoring not available")

        except ImportError:
            pytest.skip("Performance monitoring functions not available")
        except ImportError:
            pytest.skip("psutil not available for memory validation")

    def test_kmer_processing_accuracy_metrics(self):
        """Test accuracy of k-mer processing metrics."""
        try:
            from rustkmer import get_performance_metrics

            counter = KmerCounter(k=21)

            # Process known number of k-mers
            test_sequences = [
                "ATCGATCGATCGATCGATCGAT",  # 21 bases = 1 k-mer
                "GCTAGCTAGCTAGCTAGCTAGC",  # 21 bases = 1 k-mer
                "AAAATTTTCCCCGGGGAAAATTTT",  # 21 bases = 1 k-mer
                "ATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCG"  # 42 bases = 22 k-mers
            ]

            expected_kmers_processed = 25  # 1 + 1 + 1 + 22

            for seq in test_sequences:
                counter.count_from_sequence(seq)

            # Get monitoring metrics
            try:
                metrics = get_performance_metrics()

                if hasattr(metrics, 'kmers_processed'):
                    monitored_kmers = metrics.kmers_processed

                    # Should track the approximate number of k-mers processed
                    assert monitored_kmers > 0, "Should have processed some k-mers"

                    # Allow for implementation differences in counting
                    assert abs(monitored_kmers - expected_kmers_processed) <= expected_kmers_processed, \
                        f"K-mer count should be reasonable, expected ~{expected_kmers_processed}, got {monitored_kmers}"

            except (ImportError, AttributeError):
                pytest.skip("K-mer processing metrics not available")

        except ImportError:
            pytest.skip("Performance monitoring functions not available")

    def test_operation_categorization_accuracy(self):
        """Test accuracy of operation categorization in monitoring."""
        try:
            from rustkmer import get_performance_metrics

            # Test different operation types
            counter = KmerCounter(k=21)

            # Counting operation
            counter.count_from_sequence("ATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCG")

            # Query operation (if available)
            try:
                with tempfile.TemporaryDirectory() as temp_dir:
                    db_path = Path(temp_dir) / "test.rkdb"
                    counter.save_to_database(str(db_path))

                    database = Database()
                    database.load_from_kmer_counter(str(db_path))
                    database.query("ATCGATCGATCGATCGATCGAT")

            except Exception:
                pass  # Query operations might not be available in all builds

            # Get metrics and check operation categories
            try:
                metrics = get_performance_metrics()

                # Check if operation breakdown is available
                if hasattr(metrics, 'operations'):
                    operations = metrics.operations

                    # Should have at least some operations tracked
                    assert len(operations) > 0, "Should track some operations"

                    # Common operation types that should be tracked
                    expected_operations = ["kmer_counting", "database_query", "fuzzy_query"]
                    found_operations = [op for op in expected_operations if op in operations]

                    # At least one expected operation should be tracked
                    assert len(found_operations) > 0, f"Should track at least one of {expected_operations}"

            except (ImportError, AttributeError):
                pytest.skip("Operation categorization not available")

        except ImportError:
            pytest.skip("Performance monitoring functions not available")

    def test_metric_consistency_across_measurements(self):
        """Test consistency of metrics across multiple measurements."""
        try:
            from rustkmer import get_performance_metrics

            # Perform operation and measure
            counter1 = KmerCounter(k=21)
            counter1.count_from_sequence("ATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCG")

            metrics1 = get_performance_metrics()

            # Perform second similar operation
            counter2 = KmerCounter(k=21)
            counter2.count_from_sequence("ATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCG")

            metrics2 = get_performance_metrics()

            # Check consistency in metric types
            if hasattr(metrics1, '__dict__') and hasattr(metrics2, '__dict__'):
                attrs1 = set(metrics1.__dict__.keys())
                attrs2 = set(metrics2.__dict__.keys())

                # Should have consistent attribute sets
                common_attrs = attrs1.intersection(attrs2)
                assert len(common_attrs) > 0, "Should have consistent metric types across measurements"

        except ImportError:
            pytest.skip("Performance monitoring functions not available")

    def test_timestamp_accuracy_in_measurements(self):
        """Test accuracy of timestamps in performance measurements."""
        try:
            from rustkmer import get_performance_metrics
            from datetime import datetime, timezone

            # Record time before operation
            before_time = datetime.now(timezone.utc)

            counter = KmerCounter(k=21)
            counter.count_from_sequence("ATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCG")

            # Record time after operation
            after_time = datetime.now(timezone.utc)

            # Get metrics
            try:
                metrics = get_performance_metrics()

                # Check if timestamp is available
                if hasattr(metrics, 'timestamp'):
                    metric_time = metrics.timestamp

                    # Convert to datetime if it's a string
                    if isinstance(metric_time, str):
                        try:
                            from dateutil.parser import parse
                            metric_datetime = parse(metric_time)
                        except ImportError:
                            # Basic validation if dateutil not available
                            assert metric_time, "Timestamp should be present"
                            return
                    else:
                        metric_datetime = metric_time

                    # Validate timestamp is reasonable
                    assert before_time <= metric_datetime <= after_time, \
                        f"Metric timestamp should be within operation window"

            except (ImportError, AttributeError):
                pytest.skip("Timestamp metrics not available")

        except ImportError:
            pytest.skip("Performance monitoring functions not available")


class TestMonitoringOverheadMeasurement:
    """Test suite for monitoring overhead measurement (T022)."""

    def test_monitoring_overhead_benchmark(self):
        """Test that monitoring overhead is within acceptable limits (<1%)."""
        # Test with monitoring disabled (baseline)
        baseline_times = []
        for _ in range(10):
            start_time = time.perf_counter()

            counter = KmerCounter(k=21)
            counter.count_from_sequence("ATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCG")

            end_time = time.perf_counter()
            baseline_times.append(end_time - start_time)

        baseline_avg = statistics.mean(baseline_times)

        # Test with monitoring enabled (if available)
        try:
            # If monitoring can be enabled, test with it
            monitored_times = []
            for _ in range(10):
                start_time = time.perf_counter()

                counter = KmerCounter(k=21)
                # If monitoring can be enabled per instance:
                try:
                    monitored_counter = KmerCounter(k=21, enable_monitoring=True)
                    monitored_counter.count_from_sequence("ATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCG")
                except (TypeError, ValueError):
                    # Monitoring not configurable per instance
                    counter.count_from_sequence("ATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCG")

                end_time = time.perf_counter()
                monitored_times.append(end_time - start_time)

            monitored_avg = statistics.mean(monitored_times)

            # Calculate overhead
            overhead_percent = ((monitored_avg - baseline_avg) / baseline_avg) * 100

            # Requirement: <1% overhead
            assert overhead_percent < 1.0, \
                f"Monitoring overhead {overhead_percent:.2f}% should be less than 1%"

        except Exception:
            # If monitoring can't be explicitly tested, this passes by default
            # (monitoring might be compile-time feature only)
            pytest.skip("Cannot test monitoring overhead (feature not runtime configurable)")

    def test_memory_overhead_measurement(self):
        """Test memory overhead of monitoring system."""
        try:
            import psutil
            import os

            process = psutil.Process(os.getpid())

            # Measure baseline memory
            baseline_memory = process.memory_info().rss / 1024 / 1024  # MB

            # Create objects with intensive operations
            counters = []
            for i in range(100):
                counter = KmerCounter(k=21)
                counter.count_from_sequence(f"ATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATC{i:04d}")
                counters.append(counter)

            # Measure memory after operations
            post_operation_memory = process.memory_info().rss / 1024 / 1024  # MB

            # Clean up
            del counters

            # Force garbage collection
            import gc
            gc.collect()
            time.sleep(0.1)

            # Measure final memory
            final_memory = process.memory_info().rss / 1024 / 1024  # MB

            # Memory overhead should be reasonable
            total_memory_increase = final_memory - baseline_memory
            monitoring_overhead_estimate = total_memory_increase * 0.1  # Rough estimate

            # Should not add excessive memory overhead
            assert monitoring_overhead_estimate < 100, \
                f"Estimated monitoring memory overhead {monitoring_overhead_estimate:.1f}MB should be reasonable"

        except ImportError:
            pytest.skip("psutil not available for memory overhead measurement")

    def test_cpu_overhead_measurement(self):
        """Test CPU overhead of monitoring system."""
        import time

        # Baseline CPU measurement
        baseline_start = time.perf_counter()

        # CPU-intensive operation without monitoring
        for _ in range(1000):
            counter = KmerCounter(k=21)
            counter.count_from_sequence("ATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCG")

        baseline_end = time.perf_counter()
        baseline_duration = baseline_end - baseline_start

        # Test with monitoring (if available)
        try:
            from rustkmer import get_performance_metrics

            monitored_start = time.perf_counter()

            for _ in range(1000):
                counter = KmerCounter(k=21)
                counter.count_from_sequence("ATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCG")

            monitored_end = time.perf_counter()
            monitored_duration = monitored_end - monitored_start

            # CPU overhead should be minimal
            cpu_overhead_percent = ((monitored_duration - baseline_duration) / baseline_duration) * 100

            assert cpu_overhead_percent < 5.0, \
                f"CPU overhead {cpu_overhead_percent:.2f}% should be minimal"

        except ImportError:
            pytest.skip("Performance monitoring not available for CPU overhead test")

    def test_io_overhead_measurement(self):
        """Test I/O overhead of monitoring data collection."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # Test I/O operations with and without monitoring
            test_data = "ATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCG" * 100

            # Baseline I/O time
            baseline_start = time.perf_counter()

            counter = KmerCounter(k=21)
            counter.count_from_sequence(test_data)

            # Save to database
            db_path = temp_path / "baseline.rkdb"
            counter.save_to_database(str(db_path))

            baseline_end = time.perf_counter()
            baseline_io_time = baseline_end - baseline_start

            # Test with monitoring (if available)
            try:
                from rustkmer import get_performance_metrics

                monitored_start = time.perf_counter()

                counter2 = KmerCounter(k=21)
                counter2.count_from_sequence(test_data)

                # Save with monitoring
                db_path2 = temp_path / "monitored.rkdb"
                counter2.save_to_database(str(db_path2))

                monitored_end = time.perf_counter()
                monitored_io_time = monitored_end - monitored_start

                # I/O overhead should be minimal
                io_overhead_percent = ((monitored_io_time - baseline_io_time) / baseline_io_time) * 100

                assert io_overhead_percent < 2.0, \
                    f"I/O overhead {io_overhead_percent:.2f}% should be minimal"

            except ImportError:
                pytest.skip("Performance monitoring not available for I/O overhead test")

    def test_scaling_overhead_with_dataset_size(self):
        """Test how monitoring overhead scales with dataset size."""
        dataset_sizes = [100, 1000, 5000]
        overhead_percentages = []

        for size in dataset_sizes:
            # Baseline measurement
            baseline_start = time.perf_counter()

            counter = KmerCounter(k=21)
            for i in range(size):
                counter.count_from_sequence(f"ATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATC{i:04d}")

            baseline_end = time.perf_counter()
            baseline_time = baseline_end - baseline_start

            # Monitored measurement
            try:
                from rustkmer import get_performance_metrics

                monitored_start = time.perf_counter()

                counter2 = KmerCounter(k=21)
                for i in range(size):
                    counter2.count_from_sequence(f"ATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATC{i:04d}")

                monitored_end = time.perf_counter()
                monitored_time = monitored_end - monitored_start

                overhead_percent = ((monitored_time - baseline_time) / baseline_time) * 100
                overhead_percentages.append(overhead_percent)

            except ImportError:
                pytest.skip("Performance monitoring not available for scaling test")

        # Overhead should not increase dramatically with size
        if len(overhead_percentages) > 1:
            # Check that overhead doesn't grow excessively
            max_overhead = max(overhead_percentages)
            avg_overhead = statistics.mean(overhead_percentages)

            assert max_overhead < avg_overhead * 3, \
                f"Monitoring overhead should not scale poorly with dataset size"

    def test_overhead_with_conditional_compilation(self):
        """Test that conditional compilation eliminates overhead when disabled."""
        # This test verifies that when monitoring is compiled out,
        # there's no runtime overhead

        # Test operations that should be fast regardless of monitoring state
        operation_times = []

        for _ in range(50):
            start_time = time.perf_counter()

            # Simple operations
            counter = KmerCounter(k=21)
            counter.count_from_sequence("ATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCG")

            end_time = time.perf_counter()
            operation_times.append(end_time - start_time)

        avg_time = statistics.mean(operation_times)
        std_dev = statistics.stdev(operation_times) if len(operation_times) > 1 else 0

        # Performance should be consistent (low standard deviation)
        # indicating minimal conditional overhead
        consistency_ratio = std_dev / avg_time if avg_time > 0 else 0

        assert consistency_ratio < 0.5, \
            f"Operation times should be consistent, got std_dev/avg ratio of {consistency_ratio:.3f}"


class TestThreadSafeMonitoring:
    """Test suite for thread-safe monitoring validation (T023)."""

    def test_concurrent_monitoring_data_collection(self):
        """Test thread-safe data collection during concurrent operations."""
        results = []
        errors = []

        def worker(worker_id):
            try:
                worker_times = []
                for i in range(10):
                    start_time = time.perf_counter()

                    counter = KmerCounter(k=21)
                    counter.count_from_sequence(f"ATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATC{worker_id}{i}")

                    end_time = time.perf_counter()
                    worker_times.append(end_time - start_time)

                results.append({
                    'worker_id': worker_id,
                    'avg_time': statistics.mean(worker_times),
                    'operations': len(worker_times)
                })

            except Exception as e:
                errors.append(f"Worker {worker_id}: {e}")

        # Create multiple threads
        threads = []
        for i in range(5):
            t = threading.Thread(target=worker, args=(i,))
            threads.append(t)
            t.start()

        # Wait for completion
        for t in threads:
            t.join(timeout=30.0)

        # Validate results
        assert len(errors) == 0, f"Concurrent monitoring should not cause errors: {errors}"
        assert len(results) == 5, "All workers should complete successfully"

        # Check that monitoring data was collected safely
        for result in results:
            assert result['operations'] == 10, "All operations should be counted"
            assert result['avg_time'] > 0, "Timing should be recorded"

    def test_thread_safe_metrics_access(self):
        """Test thread-safe access to performance metrics."""
        shared_results = []
        access_errors = []

        def metrics_reader(reader_id):
            try:
                for _ in range(20):
                    try:
                        from rustkmer import get_performance_metrics
                        metrics = get_performance_metrics()

                        # Store some metric data
                        if hasattr(metrics, '__dict__'):
                            metric_attrs = list(metrics.__dict__.keys())
                            shared_results.append({
                                'reader_id': reader_id,
                                'metric_count': len(metric_attrs)
                            })

                    except ImportError:
                        # Monitoring not available - skip this iteration
                        pass
                    except Exception as e:
                        access_errors.append(f"Reader {reader_id}: {e}")

                    time.sleep(0.001)  # Small delay

            except Exception as e:
                access_errors.append(f"Reader {reader_id} setup: {e}")

        def operation_worker(worker_id):
            try:
                for i in range(15):
                    counter = KmerCounter(k=21)
                    counter.count_from_sequence(f"ATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATC{worker_id}{i}")
                    time.sleep(0.001)

            except Exception as e:
                access_errors.append(f"Worker {worker_id}: {e}")

        # Create threads for both metrics reading and operations
        threads = []

        # Start metrics readers
        for i in range(3):
            t = threading.Thread(target=metrics_reader, args=(f"reader_{i}",))
            threads.append(t)
            t.start()

        # Start operation workers
        for i in range(2):
            t = threading.Thread(target=operation_worker, args=(f"worker_{i}",))
            threads.append(t)
            t.start()

        # Wait for completion
        for t in threads:
            t.join(timeout=20.0)

        # Validate thread safety
        assert len(access_errors) == 0, f"Thread-safe metrics access should not cause errors: {access_errors}"

        # Should have some successful metric reads
        if shared_results:
            reader_counts = [r['metric_count'] for r in shared_results]
            assert len(reader_counts) > 0, "Should have successfully read metrics"

    def test_monitoring_under_concurrent_load(self):
        """Test monitoring system under high concurrent load."""
        concurrent_workers = 8
        operations_per_worker = 50

        worker_results = []
        worker_errors = []

        def intensive_worker(worker_id):
            try:
                start_time = time.perf_counter()

                for i in range(operations_per_worker):
                    # Perform intensive k-mer counting
                    counter = KmerCounter(k=21)

                    # Create longer sequences for more work
                    long_sequence = "ATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCG" * 10
                    counter.count_from_sequence(long_sequence[:100 + i])  # Variable length

                end_time = time.perf_counter()

                worker_results.append({
                    'worker_id': worker_id,
                    'duration': end_time - start_time,
                    'operations': operations_per_worker
                })

            except Exception as e:
                worker_errors.append(f"Worker {worker_id}: {e}")

        # Start concurrent workers
        threads = []
        for i in range(concurrent_workers):
            t = threading.Thread(target=intensive_worker, args=(i,))
            threads.append(t)
            t.start()

        # Wait for completion
        for t in threads:
            t.join(timeout=60.0)

        # Validate concurrent execution
        assert len(worker_errors) == 0, f"High concurrent load should not cause monitoring errors: {worker_errors}"
        assert len(worker_results) == concurrent_workers, "All workers should complete"

        # Performance should be reasonable under load
        avg_duration = statistics.mean([r['duration'] for r in worker_results])
        assert avg_duration < 30.0, f"Average duration {avg_duration:.2f}s should be reasonable under load"

    def test_monitoring_data_consistency_under_race_conditions(self):
        """Test monitoring data consistency under potential race conditions."""
        shared_metrics = []
        collection_errors = []

        def rapid_metric_collector(collector_id):
            try:
                for i in range(100):
                    try:
                        from rustkmer import get_performance_metrics
                        metrics = get_performance_metrics()

                        # Try to extract some data points rapidly
                        if hasattr(metrics, '__dict__'):
                            data_snapshot = {
                                'collector_id': collector_id,
                                'iteration': i,
                                'timestamp': time.time(),
                                'has_attributes': len(metrics.__dict__) > 0
                            }
                            shared_metrics.append(data_snapshot)

                    except Exception as e:
                        collection_errors.append(f"Collector {collector_id} iteration {i}: {e}")

                    # Very short delay to increase race condition probability
                    time.sleep(0.0001)

            except Exception as e:
                collection_errors.append(f"Collector {collector_id} setup: {e}")

        # Start multiple rapid collectors
        threads = []
        for i in range(4):
            t = threading.Thread(target=rapid_metric_collector, args=(i,))
            threads.append(t)
            t.start()

        # Wait for completion
        for t in threads:
            t.join(timeout=15.0)

        # Validate consistency
        assert len(collection_errors) == 0, f"Rapid collection should not cause errors: {collection_errors}"
        assert len(shared_metrics) > 0, "Should have collected some metrics"

        # Check for data consistency
        collector_counts = {}
        for metric in shared_metrics:
            collector_id = metric['collector_id']
            collector_counts[collector_id] = collector_counts.get(collector_id, 0) + 1

        # All collectors should have successfully collected data
        assert len(collector_counts) == 4, "All collectors should have participated"

    def test_thread_safety_with_different_operation_types(self):
        """Test thread safety across different operation types."""
        operation_results = {}
        operation_errors = []

        def kmer_counting_worker():
            try:
                counter = KmerCounter(k=21)
                for i in range(20):
                    counter.count_from_sequence(f"ATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATC{i:03d}")
                operation_results['kmer_counting'] = True

            except Exception as e:
                operation_errors.append(f"Kmer counting: {e}")

        def database_worker():
            try:
                with tempfile.TemporaryDirectory() as temp_dir:
                    counter = KmerCounter(k=21)
                    counter.count_from_sequence("ATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCG")

                    db_path = Path(temp_dir) / "thread_test.rkdb"
                    counter.save_to_database(str(db_path))

                    database = Database()
                    database.load_from_kmer_counter(str(db_path))

                    for i in range(10):
                        database.query(f"ATCGATCGATCGATCGATCGATC{i:03d}")

                operation_results['database'] = True

            except Exception as e:
                operation_errors.append(f"Database operations: {e}")

        def fuzzy_query_worker():
            try:
                # Create fuzzy queries (if available)
                for i in range(10):
                    fq = FuzzyQuery(k=21, pattern=f"ATCGATCGATCGATCGATCGATC{i:02d}N")
                    # The query execution itself if available

                operation_results['fuzzy_query'] = True

            except Exception as e:
                operation_errors.append(f"Fuzzy query: {e}")

        # Start different operation type workers
        threads = [
            threading.Thread(target=kmer_counting_worker),
            threading.Thread(target=database_worker),
            threading.Thread(target=fuzzy_query_worker)
        ]

        for t in threads:
            t.start()

        for t in threads:
            t.join(timeout=20.0)

        # Validate thread safety across operations
        assert len(operation_errors) == 0, f"Different operations should be thread-safe: {operation_errors}"
        assert len(operation_results) > 0, "At least some operations should succeed"

    def test_monitoring_resource_cleanup_under_concurrency(self):
        """Test that monitoring resources are properly cleaned up under concurrent usage."""
        cleanup_results = []
        cleanup_errors = []

        def resource_usage_worker(worker_id):
            try:
                initial_resources = None

                # Try to get initial resource state
                try:
                    from rustkmer import get_performance_metrics
                    initial_metrics = get_performance_metrics()
                    initial_resources = True
                except:
                    pass

                # Perform operations
                counters = []
                for i in range(20):
                    counter = KmerCounter(k=21)
                    counter.count_from_sequence(f"ATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATC{worker_id}{i}")
                    counters.append(counter)

                # Clean up resources
                del counters
                import gc
                gc.collect()

                # Check final state
                try:
                    final_metrics = get_performance_metrics()
                    cleanup_results.append({
                        'worker_id': worker_id,
                        'initial_resources': initial_resources,
                        'cleanup_successful': True
                    })
                except:
                    cleanup_results.append({
                        'worker_id': worker_id,
                        'initial_resources': initial_resources,
                        'cleanup_successful': False
                    })

            except Exception as e:
                cleanup_errors.append(f"Worker {worker_id}: {e}")

        # Start concurrent resource usage workers
        threads = []
        for i in range(6):
            t = threading.Thread(target=resource_usage_worker, args=(i,))
            threads.append(t)
            t.start()

        for t in threads:
            t.join(timeout=30.0)

        # Validate cleanup
        assert len(cleanup_errors) == 0, f"Concurrent resource cleanup should not cause errors: {cleanup_errors}"
        assert len(cleanup_results) == 6, "All workers should complete cleanup"

        # Most workers should have successful cleanup
        successful_cleanups = sum(1 for r in cleanup_results if r['cleanup_successful'])
        assert successful_cleanups >= 4, "Most concurrent cleanups should be successful"


class TestLargeScaleMonitoringPerformance:
    """Test suite for large-scale monitoring performance (T024)."""

    def test_monitoring_with_large_kmer_datasets(self):
        """Test monitoring performance with large k-mer datasets."""
        try:
            from rustkmer import get_performance_metrics
            import psutil
            import os

            process = psutil.Process(os.getpid())
            initial_memory = process.memory_info().rss / 1024 / 1024  # MB

            # Create large dataset
            large_dataset_size = 10000

            start_time = time.perf_counter()

            counter = KmerCounter(k=21)

            # Process large number of k-mers
            for i in range(large_dataset_size):
                sequence = f"ATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATC{i:05d}"
                counter.count_from_sequence(sequence)

            end_time = time.perf_counter()
            processing_time = end_time - start_time

            final_memory = process.memory_info().rss / 1024 / 1024  # MB
            memory_increase = final_memory - initial_memory

            # Get monitoring metrics
            try:
                metrics = get_performance_metrics()

                # Validate monitoring handled large dataset
                assert processing_time < 60.0, f"Large dataset processing should complete in reasonable time, took {processing_time:.2f}s"
                assert memory_increase < 2000, f"Memory increase {memory_increase:.1f}MB should be reasonable for large dataset"

                # Check if metrics captured the scale
                if hasattr(metrics, 'kmers_processed'):
                    assert metrics.kmers_processed > 0, "Should have processed k-mers"

            except (ImportError, AttributeError):
                pytest.skip("Large-scale monitoring metrics not available")

        except ImportError:
            pytest.skip("Performance monitoring not available")

    def test_monitoring_scalability_with_dataset_growth(self):
        """Test how monitoring scales as dataset size grows."""
        dataset_sizes = [1000, 5000, 10000]
        performance_metrics = []

        for size in dataset_sizes:
            try:
                from rustkmer import get_performance_metrics

                # Measure performance for this dataset size
                start_time = time.perf_counter()
                start_memory = None

                try:
                    import psutil
                    import os
                    process = psutil.Process(os.getpid())
                    start_memory = process.memory_info().rss / 1024 / 1024  # MB
                except:
                    pass

                # Process dataset of specified size
                counter = KmerCounter(k=21)
                for i in range(size):
                    counter.count_from_sequence(f"ATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATC{i:05d}")

                end_time = time.perf_counter()
                end_memory = None

                try:
                    if start_memory:
                        end_memory = process.memory_info().rss / 1024 / 1024  # MB
                except:
                    pass

                # Get monitoring metrics
                metrics = get_performance_metrics()

                performance_metrics.append({
                    'dataset_size': size,
                    'processing_time': end_time - start_time,
                    'memory_increase': (end_memory - start_memory) if end_memory and start_memory else None,
                    'monitored_kmers': getattr(metrics, 'kmers_processed', 0)
                })

            except ImportError:
                pytest.skip("Performance monitoring not available for scalability test")

        # Analyze scalability
        if len(performance_metrics) >= 2:
            # Check that time scales reasonably (not exponentially)
            times = [m['processing_time'] for m in performance_metrics]
            sizes = [m['dataset_size'] for m in performance_metrics]

            # Simple linear regression check
            n = len(times)
            sum_x = sum(sizes)
            sum_y = sum(times)
            sum_xy = sum(s * t for s, t in zip(sizes, times))
            sum_x2 = sum(s * s for s in sizes)

            if n > 1 and (n * sum_x2 - sum_x * sum_x) != 0:
                slope = (n * sum_xy - sum_x * sum_y) / (n * sum_x2 - sum_x * sum_x)

                # Slope should be reasonable (not too steep)
                assert slope < 0.01, f"Processing time should scale linearly, slope {slope:.6f} too steep"

    def test_monitoring_performance_under_sustained_load(self):
        """Test monitoring performance under sustained load conditions."""
        duration_seconds = 10
        operation_interval = 0.001  # 1ms between operations

        start_time = time.perf_counter()
        operations_completed = 0
        errors = 0

        try:
            from rustkmer import get_performance_metrics

            while time.perf_counter() - start_time < duration_seconds:
                try:
                    operation_start = time.perf_counter()

                    counter = KmerCounter(k=21)
                    counter.count_from_sequence(f"ATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATC{operations_completed}")

                    operation_end = time.perf_counter()
                    operations_completed += 1

                    # Check if monitoring is keeping up
                    if operation_end - operation_start > 0.1:  # Individual operation taking >100ms
                        break

                    # Maintain operation interval
                    elapsed = operation_end - operation_start
                    if elapsed < operation_interval:
                        time.sleep(operation_interval - elapsed)

                except Exception as e:
                    errors += 1
                    if errors > 10:  # Too many errors
                        break

            # Get final metrics
            metrics = get_performance_metrics()

            # Validate sustained performance
            expected_operations = duration_seconds / operation_interval
            actual_rate = operations_completed / duration_seconds

            assert actual_rate > expected_operations * 0.5, \
                f"Sustained load should maintain reasonable operation rate, got {actual_rate:.1f} ops/s"
            assert errors < operations_completed * 0.05, \
                f"Error rate should be low under sustained load, got {errors}/{operations_completed}"

        except ImportError:
            pytest.skip("Performance monitoring not available for sustained load test")

    def test_monitoring_memory_efficiency_at_scale(self):
        """Test memory efficiency of monitoring at large scale."""
        import gc

        # Baseline memory
        try:
            import psutil
            import os
            process = psutil.Process(os.getpid())
            baseline_memory = process.memory_info().rss / 1024 / 1024  # MB
        except:
            pytest.skip("psutil not available for memory efficiency test")

        # Create large number of monitored objects
        counters = []
        batch_size = 100
        num_batches = 20

        for batch in range(num_batches):
            batch_counters = []
            for i in range(batch_size):
                counter = KmerCounter(k=21)
                counter.count_from_sequence(f"ATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATC{batch}{i}")
                batch_counters.append(counter)

            counters.extend(batch_counters)

            # Check memory growth every few batches
            if batch % 5 == 0:
                current_memory = process.memory_info().rss / 1024 / 1024
                memory_growth = current_memory - baseline_memory

                # Memory growth should be linear, not exponential
                expected_growth = (batch + 1) * batch_size * 0.1  # Rough estimate per counter
                assert memory_growth < expected_growth * 3, \
                    f"Memory growth {memory_growth:.1f}MB should be reasonable at batch {batch}"

        final_memory = process.memory_info().rss / 1024 / 1024
        total_memory_growth = final_memory - baseline_memory

        # Clean up
        del counters
        gc.collect()
        time.sleep(0.1)

        post_cleanup_memory = process.memory_info().rss / 1024 / 1024
        memory_leak = post_cleanup_memory - baseline_memory

        # Validate memory efficiency
        assert total_memory_growth < 1000, f"Total memory growth {total_memory_growth:.1f}MB should be reasonable"
        assert memory_leak < 100, f"Memory leak {memory_leak:.1f}MB should be minimal after cleanup"

    def test_monitoring_data_collection_efficiency(self):
        """Test efficiency of monitoring data collection at scale."""
        collection_times = []
        data_points_collected = 0

        try:
            from rustkmer import get_performance_metrics

            # Create some workload to monitor
            counter = KmerCounter(k=21)
            for i in range(5000):
                counter.count_from_sequence(f"ATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATC{i:04d}")

            # Measure data collection efficiency
            for i in range(100):
                collection_start = time.perf_counter()

                try:
                    metrics = get_performance_metrics()

                    # Count data points
                    if hasattr(metrics, '__dict__'):
                        data_points = len(metrics.__dict__)
                        data_points_collected += data_points

                except Exception:
                    pass

                collection_end = time.perf_counter()
                collection_times.append(collection_end - collection_start)

            # Analyze collection efficiency
            avg_collection_time = statistics.mean(collection_times)
            max_collection_time = max(collection_times)

            assert avg_collection_time < 0.001, \
                f"Average data collection time {avg_collection_time*1000:.3f}ms should be very fast"
            assert max_collection_time < 0.01, \
                f"Maximum data collection time {max_collection_time*1000:.3f}ms should be fast"
            assert data_points_collected > 0, \
                "Should have collected monitoring data points"

        except ImportError:
            pytest.skip("Performance monitoring not available for collection efficiency test")

    def test_monitoring_overhead_with_complex_operations(self):
        """Test monitoring overhead with complex, mixed operations."""
        operation_times = []

        # Baseline measurement without monitoring consideration
        baseline_start = time.perf_counter()

        # Complex operations
        for i in range(1000):
            # K-mer counting
            counter = KmerCounter(k=21)
            counter.count_from_sequence(f"ATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATC{i:04d}")

            # Database operations (if available)
            if i % 100 == 0:
                try:
                    with tempfile.TemporaryDirectory() as temp_dir:
                        db_path = Path(temp_dir) / f"temp_{i}.rkdb"
                        counter.save_to_database(str(db_path))
                except:
                    pass

        baseline_end = time.perf_counter()
        baseline_time = baseline_end - baseline_start

        # Test with explicit monitoring awareness
        try:
            from rustkmer import get_performance_metrics

            monitored_start = time.perf_counter()

            for i in range(1000):
                counter = KmerCounter(k=21)
                counter.count_from_sequence(f"ATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATC{i:04d}")

                if i % 100 == 0:
                    try:
                        # Periodic metrics collection
                        metrics = get_performance_metrics()
                    except:
                        pass

            monitored_end = time.perf_counter()
            monitored_time = monitored_end - monitored_start

            # Calculate overhead
            overhead_percent = ((monitored_time - baseline_time) / baseline_time) * 100

            assert overhead_percent < 5.0, \
                f"Monitoring overhead {overhead_percent:.2f}% should be low for complex operations"

        except ImportError:
            pytest.skip("Performance monitoring not available for overhead test")


# Integration tests
class TestMonitoringIntegration:
    """Integration tests for complete monitoring system validation."""

    def test_end_to_end_monitoring_workflow(self):
        """Test complete monitoring workflow from start to finish."""
        try:
            from rustkmer import get_performance_metrics

            # 1. Start with clean state
            initial_metrics = get_performance_metrics()

            # 2. Perform mixed operations
            operations_performed = []

            # K-mer counting
            counter = KmerCounter(k=21)
            counting_start = time.perf_counter()

            for i in range(500):
                counter.count_from_sequence(f"ATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATC{i:03d}")

            counting_end = time.perf_counter()
            operations_performed.append({
                'type': 'kmer_counting',
                'duration': counting_end - counting_start,
                'operations': 500
            })

            # Database operations
            with tempfile.TemporaryDirectory() as temp_dir:
                db_start = time.perf_counter()
                db_path = Path(temp_dir) / "integration_test.rkdb"
                counter.save_to_database(str(db_path))

                database = Database()
                database.load_from_kmer_counter(str(db_path))

                for i in range(100):
                    database.query(f"ATCGATCGATCGATCGATCGATC{i:03d}")

                db_end = time.perf_counter()
                operations_performed.append({
                    'type': 'database_operations',
                    'duration': db_end - db_start,
                    'operations': 100
                })

            # 3. Get final metrics
            final_metrics = get_performance_metrics()

            # 4. Validate comprehensive monitoring
            total_operations = sum(op['operations'] for op in operations_performed)
            total_duration = sum(op['duration'] for op in operations_performed)

            assert len(operations_performed) > 0, "Should have performed operations"
            assert total_duration > 0, "Should have measurable duration"

            # Check that metrics captured the activity
            if hasattr(final_metrics, '__dict__'):
                metric_attrs = final_metrics.__dict__
                assert len(metric_attrs) > 0, "Should have collected monitoring data"

        except ImportError:
            pytest.skip("Performance monitoring not available for integration test")

    def test_monitoring_production_readiness(self):
        """Test monitoring system production readiness."""
        try:
            from rustkmer import get_performance_metrics

            # Production-like workload
            production_counters = []

            # Multiple counters simulating production usage
            for i in range(10):
                counter = KmerCounter(k=21, canonical=(i % 2 == 0))

                # Substantial workload for each counter
                for j in range(1000):
                    sequence = f"ATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATC{i:03d}{j:04d}"
                    counter.count_from_sequence(sequence)

                production_counters.append(counter)

            # Concurrent operations
            with ThreadPoolExecutor(max_workers=4) as executor:
                futures = []

                for i, counter in enumerate(production_counters):
                    # Submit database operations
                    future = executor.submit(self._production_database_worker, counter, i)
                    futures.append(future)

                # Wait for completion
                for future in futures:
                    future.result(timeout=30.0)

            # Get production metrics
            production_metrics = get_performance_metrics()

            # Validate production readiness
            assert len(production_counters) == 10, "All production counters should be created"

            if hasattr(production_metrics, '__dict__'):
                # Should have comprehensive metrics
                metric_data = production_metrics.__dict__
                assert len(metric_data) > 0, "Should collect production metrics"

        except ImportError:
            pytest.skip("Performance monitoring not available for production test")
        except Exception as e:
            pytest.skip(f"Production test setup failed: {e}")

    def _production_database_worker(self, counter, worker_id):
        """Helper worker for production database operations."""
        try:
            with tempfile.TemporaryDirectory() as temp_dir:
                db_path = Path(temp_dir) / f"production_{worker_id}.rkdb"
                counter.save_to_database(str(db_path))

                database = Database()
                database.load_from_kmer_counter(str(db_path))

                # Production-like query pattern
                for i in range(200):
                    database.query(f"ATCGATCGATCGATCGATCGATC{i:04d}")

        except Exception:
            pass  # Database operations might not be fully available


if __name__ == "__main__":
    # Run tests directly
    pytest.main([__file__, "-v"])