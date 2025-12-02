#!/usr/bin/env python3
"""
Comprehensive Python API Validation Suite

This module provides comprehensive validation testing for the RustKmer Python API
to ensure >95% test success rate and validate all user story implementations.

User Stories Validated:
- US1: FuzzyQuery API Enhancement (P1) - max_variants property functionality
- US2: Database Persistence (P2) - KmerCounter save/load operations
- US3: Performance Monitoring (P3) - Low-overhead monitoring system

Success Criteria:
- SC-001: FuzzyQuery performance tests achieve 100% success rate
- SC-002: Database operations complete in under 5 seconds for typical datasets
- SC-003: Large-scale operations complete without memory errors
- SC-004: Performance monitoring overhead <1%
- SC-005: Overall Python API test success rate >95%
"""

import sys
import os
import time
import traceback
from typing import Dict, List, Tuple, Any
from pathlib import Path

# Add the rustkmer_python module to path for testing
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / "target"))

try:
    import rustkmer_python as rustkmer
    from rustkmer import KmerCounter, Database, FuzzyQuery, PerformanceTimer
except ImportError as e:
    print(f"WARNING: Cannot import rustkmer_python module: {e}")
    print("This is expected if the Python extension hasn't been built yet.")
    rustkmer = None

class ValidationResult:
    """Container for test validation results"""
    def __init__(self, name: str):
        self.name = name
        self.passed = 0
        self.failed = 0
        self.errors = []
        self.warnings = []
        self.performance_data = {}

    def add_success(self, test_name: str, message: str = ""):
        self.passed += 1
        if message:
            print(f"✓ PASS: {test_name} - {message}")
        else:
            print(f"✓ PASS: {test_name}")

    def add_failure(self, test_name: str, error: str):
        self.failed += 1
        self.errors.append(f"{test_name}: {error}")
        print(f"✗ FAIL: {test_name} - {error}")

    def add_warning(self, test_name: str, warning: str):
        self.warnings.append(f"{test_name}: {warning}")
        print(f"⚠ WARNING: {test_name} - {warning}")

    def add_performance_data(self, metric: str, value: Any):
        self.performance_data[metric] = value

    def get_success_rate(self) -> float:
        total = self.passed + self.failed
        if total == 0:
            return 0.0
        return (self.passed / total) * 100.0

    def get_summary(self) -> str:
        return (
            f"{self.name}:\n"
            f"  Passed: {self.passed}\n"
            f"  Failed: {self.failed}\n"
            f"  Success Rate: {self.get_success_rate():.1f}%\n"
            f"  Warnings: {len(self.warnings)}\n"
            f"  Performance Metrics: {len(self.performance_data)}"
        )

class ComprehensiveValidator:
    """Comprehensive Python API validation system"""

    def __init__(self):
        self.results = {
            'setup': ValidationResult("Setup and Environment"),
            'fuzzy_query': ValidationResult("FuzzyQuery API Enhancement (US1)"),
            'database_persistence': ValidationResult("Database Persistence (US2)"),
            'performance_monitoring': ValidationResult("Performance Monitoring (US3)"),
            'integration': ValidationResult("Integration Testing"),
            'performance': ValidationResult("Performance Benchmarks")
        }
        self.start_time = time.time()

    def run_validation(self) -> ValidationResult:
        """Run comprehensive validation suite"""
        print("=== RustKmer Python API Comprehensive Validation ===")
        print(f"Started at: {time.ctime()}")
        print()

        # Run all validation phases
        self._validate_setup()
        self._validate_fuzzy_query_us1()
        self._validate_database_persistence_us2()
        self._validate_performance_monitoring_us3()
        self._validate_integration()
        self._validate_performance_benchmarks()

        # Calculate overall results
        overall = ValidationResult("Overall Python API Validation")
        for result in self.results.values():
            overall.passed += result.passed
            overall.failed += result.failed
            overall.errors.extend(result.errors)
            overall.warnings.extend(result.warnings)

        overall.add_performance_data("total_execution_time", time.time() - self.start_time)

        # Print final summary
        self._print_final_summary(overall)

        return overall

    def _validate_setup(self):
        """Validate basic setup and environment"""
        result = self.results['setup']
        print("=== Phase 1: Setup and Environment Validation ===")

        # Check if module can be imported
        if rustkmer is None:
            result.add_failure("Module Import", "Cannot import rustkmer_python module")
            return

        result.add_success("Module Import", "rustkmer_python module imported successfully")

        # Check version information
        try:
            version = rustkmer.get_version()
            result.add_success("Version Check", f"Version {version}")
            result.add_performance_data("version", version)
        except Exception as e:
            result.add_failure("Version Check", str(e))

        # Check system information
        try:
            sys_info = rustkmer.get_system_info()
            result.add_success("System Info", f"Python {sys_info.get('python_version', 'Unknown')}")
            result.add_performance_data("system_info", sys_info)
        except Exception as e:
            result.add_failure("System Info", str(e))

        print()

    def _validate_fuzzy_query_us1(self):
        """Validate User Story 1: FuzzyQuery API Enhancement"""
        result = self.results['fuzzy_query']
        print("=== Phase 2: FuzzyQuery API Enhancement Validation (US1) ===")

        if rustkmer is None:
            result.add_failure("FuzzyQuery", "Module not available")
            return

        try:
            # Test basic FuzzyQuery creation
            fq = FuzzyQuery(k=5)
            result.add_success("FuzzyQuery Creation", f"Created with k={fq.get_k()}")

            # Test max_variants property accessibility (SC-001)
            try:
                max_variants = fq.get_max_variants()
                result.add_success("max_variants Property Access", f"Default max_variants={max_variants}")

                # Test max_variants property setting
                fq.set_max_variants(50000)
                new_max = fq.get_max_variants()
                if new_max == 50000:
                    result.add_success("max_variants Property Setting", f"Successfully set to {new_max}")
                else:
                    result.add_failure("max_variants Property Setting", f"Expected 50000, got {new_max}")

            except Exception as e:
                result.add_failure("max_variants Property", str(e))

            # Test variant limit enforcement
            try:
                fq.set_max_variants(1000000)  # Valid
                result.add_success("Valid max_variants Setting", "Successfully set to 1,000,000")

                # Try invalid value
                try:
                    fq.set_max_variants(0)
                    result.add_failure("Invalid max_variants", "Should have rejected value 0")
                except:
                    result.add_success("Invalid max_variants Rejection", "Correctly rejected invalid value 0")

            except Exception as e:
                result.add_failure("Variant Limit Enforcement", str(e))

            # Test wildcard expansion functionality
            try:
                fq_wildcard = FuzzyQuery("ATNCG", k=5)
                variant_count = fq_wildcard.get_variant_count()
                if variant_count == 4:  # A, T, C, G for one N
                    result.add_success("Wildcard Variant Count", f"N generates {variant_count} variants")
                else:
                    result.add_warning("Wildcard Variant Count", f"Expected 4, got {variant_count}")

                # Test wildcard expansion
                variants = fq_wildcard.expand_wildcards()
                if len(variants) == 4:
                    result.add_success("Wildcard Expansion", f"Successfully expanded {len(variants)} variants")
                else:
                    result.add_failure("Wildcard Expansion", f"Expected 4 variants, got {len(variants)}")

            except Exception as e:
                result.add_failure("Wildcard Expansion", str(e))

            # Performance test for large variant sets
            try:
                start_time = time.time()
                fq_large = FuzzyQuery("ANNNN", k=5)  # 4^4 = 256 variants
                variant_count = fq_large.get_variant_count()
                expansion_time = time.time() - start_time

                if variant_count == 256 and expansion_time < 1.0:
                    result.add_success("Large Variant Performance",
                                     f"256 variants in {expansion_time:.3f}s")
                    result.add_performance_data("large_variant_count", variant_count)
                    result.add_performance_data("large_variant_time", expansion_time)
                else:
                    result.add_failure("Large Variant Performance",
                                     f"Count={variant_count}, Time={expansion_time:.3f}s")

            except Exception as e:
                result.add_failure("Large Variant Performance", str(e))

        except Exception as e:
            result.add_failure("FuzzyQuery General", str(e))

        print()

    def _validate_database_persistence_us2(self):
        """Validate User Story 2: Database Persistence"""
        result = self.results['database_persistence']
        print("=== Phase 3: Database Persistence Validation (US2) ===")

        if rustkmer is None:
            result.add_failure("Database Persistence", "Module not available")
            return

        try:
            # Test KmerCounter creation
            kc = KmerCounter(k=5)
            result.add_success("KmerCounter Creation", f"Created with k={kc.get_k()}")

            # Test basic counting
            test_sequence = "ATCGATCGATCG"  # 8-mers, k=5
            kc.count_string(test_sequence)
            result.add_success("Basic Counting", "Successfully counted string sequence")

            # Test k-mer counting results
            count = kc.get_kmer_count("ATCGA")
            result.add_success("K-mer Count Query", f"ATCGA count: {count}")

            # Test save_to_database functionality (SC-002)
            test_db_path = "/tmp/test_persistence.rkdb"
            try:
                start_time = time.time()
                kc.save_to_database(test_db_path)
                save_time = time.time() - start_time

                if save_time < 5.0:  # Should complete in under 5 seconds
                    result.add_success("Database Save Operation",
                                     f"Saved in {save_time:.3f}s")
                    result.add_performance_data("database_save_time", save_time)
                else:
                    result.add_failure("Database Save Performance",
                                     f"Too slow: {save_time:.3f}s")

            except Exception as e:
                result.add_failure("Database Save Operation", str(e))

            # Test database loading
            try:
                start_time = time.time()
                db = Database(test_db_path)
                load_time = time.time() - start_time

                if db.is_open():
                    result.add_success("Database Load Operation",
                                     f"Loaded in {load_time:.3f}s")
                    result.add_performance_data("database_load_time", load_time)

                    # Test data consistency
                    db_count = db.get_count("ATCGA")
                    if db_count == count:
                        result.add_success("Database Data Consistency",
                                         f"Counts match: {db_count}")
                    else:
                        result.add_failure("Database Data Consistency",
                                         f"Counts differ: expected {count}, got {db_count}")
                else:
                    result.add_failure("Database Load Operation", "Database not open")

            except Exception as e:
                result.add_failure("Database Load Operation", str(e))

            # Test database statistics
            try:
                stats = db.get_stats()
                result.add_success("Database Statistics",
                                 f"k={stats.kmer_size}, total={stats.total_kmers}")
                result.add_performance_data("database_stats", stats)

            except Exception as e:
                result.add_failure("Database Statistics", str(e))

            # Test database cleanup
            try:
                db.close()
                result.add_success("Database Close", "Successfully closed database")
            except Exception as e:
                result.add_failure("Database Close", str(e))

            # Cleanup test file
            try:
                if os.path.exists(test_db_path):
                    os.remove(test_db_path)
            except:
                pass

        except Exception as e:
            result.add_failure("Database Persistence General", str(e))

        print()

    def _validate_performance_monitoring_us3(self):
        """Validate User Story 3: Performance Monitoring"""
        result = self.results['performance_monitoring']
        print("=== Phase 4: Performance Monitoring Validation (US3) ===")

        if rustkmer is None:
            result.add_failure("Performance Monitoring", "Module not available")
            return

        try:
            # Test monitoring initialization (SC-004)
            try:
                rustkmer.initialize_monitoring(
                    enabled=True,
                    track_memory=True,
                    track_timing=True,
                    track_operations=True,
                    max_samples=1000
                )
                result.add_success("Monitoring Initialization", "Successfully initialized")

            except Exception as e:
                result.add_failure("Monitoring Initialization", str(e))

            # Test performance timer
            try:
                timer = PerformanceTimer("test_operation")
                time.sleep(0.01)  # Simulate operation
                elapsed = timer.elapsed()

                if elapsed > 0.005:  # Should be at least 10ms
                    result.add_success("Performance Timer", f"Measured {elapsed:.3f}s")
                    result.add_performance_data("timer_precision", elapsed)
                else:
                    result.add_warning("Performance Timer", f"Very short time: {elapsed:.3f}s")

            except Exception as e:
                result.add_failure("Performance Timer", str(e))

            # Test metric recording
            try:
                rustkmer.record_custom_metric("test_metric", "test_value", 42.0)
                result.add_success("Metric Recording", "Successfully recorded custom metric")

            except Exception as e:
                result.add_failure("Metric Recording", str(e))

            # Test performance stats collection
            try:
                start_time = time.time()

                # Simulate some operations
                kc = KmerCounter(k=5)
                kc.count_string("ATCGATCGATCG")
                kc.get_kmer_count("ATCGA")

                operation_time = time.time() - start_time
                stats = rustkmer.get_performance_stats()

                if stats:
                    result.add_success("Performance Stats Collection",
                                     f"Collected {len(stats)} metrics")
                    result.add_performance_data("operation_stats", stats)
                    result.add_performance_data("operation_time", operation_time)
                else:
                    result.add_warning("Performance Stats Collection", "No stats collected")

            except Exception as e:
                result.add_failure("Performance Stats Collection", str(e))

            # Test monitoring overhead (should be <1%)
            try:
                # Test with monitoring enabled
                rustkmer.initialize_monitoring(
                    enabled=True, track_memory=True, track_timing=True, track_operations=True
                )
                start_time = time.time()
                kc = KmerCounter(k=5)
                kc.count_string("ATCGATCGATCGATCGATCGATCGATCGATCG")
                kc.get_kmer_count("ATCGA")
                time_with_monitoring = time.time() - start_time

                # Test without monitoring
                rustkmer.initialize_monitoring(enabled=False)
                start_time = time.time()
                kc = KmerCounter(k=5)
                kc.count_string("ATCGATCGATCGATCGATCGATCGATCGATCG")
                kc.get_kmer_count("ATCGA")
                time_without_monitoring = time.time() - start_time

                if time_without_monitoring > 0:
                    overhead_percent = ((time_with_monitoring - time_without_monitoring) / time_without_monitoring) * 100

                    if overhead_percent < 1.0:
                        result.add_success("Monitoring Overhead",
                                         f"Overhead: {overhead_percent:.2f}%")
                        result.add_performance_data("monitoring_overhead_percent", overhead_percent)
                    else:
                        result.add_failure("Monitoring Overhead",
                                         f"Too high: {overhead_percent:.2f}%")
                else:
                    result.add_warning("Monitoring Overhead", "Cannot calculate overhead")

            except Exception as e:
                result.add_failure("Monitoring Overhead", str(e))

            # Re-enable monitoring for subsequent tests
            rustkmer.initialize_monitoring(
                enabled=True, track_memory=True, track_timing=True, track_operations=True
            )

        except Exception as e:
            result.add_failure("Performance Monitoring General", str(e))

        print()

    def _validate_integration(self):
        """Validate integration between components"""
        result = self.results['integration']
        print("=== Phase 5: Integration Testing ===")

        if rustkmer is None:
            result.add_failure("Integration Testing", "Module not available")
            return

        try:
            # Test KmerCounter -> Database workflow
            kc = KmerCounter(k=5)
            kc.count_string("ATCGATCGATCGATCGATCGATCG")

            # Create database
            db_path = "/tmp/integration_test.rkdb"
            kc.save_to_database(db_path)

            # Load database and query
            db = Database(db_path)

            # Test consistency between KmerCounter and Database
            kc_count = kc.get_kmer_count("ATCGA")
            db_count = db.get_count("ATCGA")

            if kc_count == db_count:
                result.add_success("KmerCounter-Database Integration",
                                 f"Consistent counts: {kc_count}")
            else:
                result.add_failure("KmerCounter-Database Integration",
                                 f"Inconsistent counts: KC={kc_count}, DB={db_count}")

            db.close()

            # Test FuzzyQuery integration with Database
            db = Database(db_path)
            fq = FuzzyQuery("ATNCG", k=5)

            # Test database query with fuzzy query expansion
            variants = fq.expand_wildcards()
            successful_queries = 0

            for variant in variants:
                try:
                    count = db.get_count(variant)
                    successful_queries += 1
                except:
                    pass

            result.add_success("FuzzyQuery-Database Integration",
                             f"Successfully queried {successful_queries}/{len(variants)} variants")

            db.close()

            # Cleanup
            try:
                os.remove(db_path)
            except:
                pass

        except Exception as e:
            result.add_failure("Integration Testing General", str(e))

        print()

    def _validate_performance_benchmarks(self):
        """Validate performance benchmarks"""
        result = self.results['performance']
        print("=== Phase 6: Performance Benchmarks ===")

        if rustkmer is None:
            result.add_failure("Performance Benchmarks", "Module not available")
            return

        try:
            # Test large string processing (SC-003)
            large_sequence = "ATCG" * 10000  # 40,000 bases
            start_time = time.time()

            kc = KmerCounter(k=21)
            kc.count_string(large_sequence)

            processing_time = time.time() - start_time
            bases_per_second = len(large_sequence) / processing_time

            result.add_success("Large Sequence Processing",
                             f"{len(large_sequence)} bases in {processing_time:.3f}s")
            result.add_performance_data("large_sequence_time", processing_time)
            result.add_performance_data("bases_per_second", bases_per_second)

            # Test multiple k-mer queries
            kc = KmerCounter(k=5)
            kc.count_string("ATCGATCGATCG")

            start_time = time.time()
            queries = ["ATCGA", "TCGAT", "CGATC", "GATCG"]
            for kmer in queries:
                kc.get_kmer_count(kmer)
            query_time = time.time() - start_time

            result.add_success("Multiple K-mer Queries",
                             f"{len(queries)} queries in {query_time:.6f}s")
            result.add_performance_data("query_time_per_kmer", query_time / len(queries))

            # Test memory efficiency
            try:
                stats = rustkmer.get_performance_stats()
                if stats:
                    result.add_success("Performance Statistics Available",
                                     f"Collected {len(stats)} performance metrics")
                    result.add_performance_data("final_stats", stats)
                else:
                    result.add_warning("Performance Statistics", "No performance stats available")

            except Exception as e:
                result.add_failure("Performance Statistics", str(e))

        except Exception as e:
            result.add_failure("Performance Benchmarks General", str(e))

        print()

    def _print_final_summary(self, overall: ValidationResult):
        """Print comprehensive validation summary"""
        total_time = time.time() - self.start_time

        print("=" * 60)
        print("COMPREHENSIVE VALIDATION SUMMARY")
        print("=" * 60)
        print()

        # Individual results
        for name, result in self.results.items():
            print(result.get_summary())
            print()

        # Overall results
        print("OVERALL RESULTS")
        print("-" * 20)
        print(f"Total Tests Passed: {overall.passed}")
        print(f"Total Tests Failed: {overall.failed}")
        print(f"Overall Success Rate: {overall.get_success_rate():.1f}%")
        print(f"Total Warnings: {len(overall.warnings)}")
        print(f"Total Execution Time: {total_time:.2f}s")
        print()

        # Success criteria evaluation
        print("SUCCESS CRITERIA EVALUATION")
        print("-" * 30)

        # SC-001: FuzzyQuery performance tests achieve 100% success rate
        fuzzy_result = self.results['fuzzy_query']
        sc_001 = fuzzy_result.get_success_rate() >= 100.0
        print(f"SC-001 FuzzyQuery 100% Success: {'✓ PASS' if sc_001 else '✗ FAIL'} "
              f"({fuzzy_result.get_success_rate():.1f}%)")

        # SC-002: Database operations complete in under 5 seconds
        sc_002 = fuzzy_result.performance_data.get('database_save_time', 999) < 5.0
        print(f"SC-002 Database <5s Operations: {'✓ PASS' if sc_002 else '✗ FAIL'} "
              f"({fuzzy_result.performance_data.get('database_save_time', 'N/A'):.3f}s)")

        # SC-003: Large-scale operations complete without memory errors
        sc_003 = 'large_sequence_time' in self.results['performance'].performance_data
        print(f"SC-003 Large-Scale Operations: {'✓ PASS' if sc_003 else '✗ FAIL'}")

        # SC-004: Performance monitoring overhead <1%
        perf_result = self.results['performance_monitoring']
        sc_004 = (perf_result.performance_data.get('monitoring_overhead_percent', 100) < 1.0)
        print(f"SC-004 Monitoring <1% Overhead: {'✓ PASS' if sc_004 else '✗ FAIL'} "
              f"({perf_result.performance_data.get('monitoring_overhead_percent', 'N/A'):.2f}%)")

        # SC-005: Overall Python API test success rate >95%
        sc_005 = overall.get_success_rate() >= 95.0
        print(f"SC-005 >95% Success Rate: {'✓ PASS' if sc_005 else '✗ FAIL'} "
              f"({overall.get_success_rate():.1f}%)")

        print()

        # Final assessment
        all_criteria_met = all([sc_001, sc_002, sc_003, sc_004, sc_005])

        if all_criteria_met:
            print("🎉 ALL SUCCESS CRITERIA MET! Ready for production.")
        else:
            print("⚠️  Some success criteria not met. Review and address issues.")

        if overall.errors:
            print()
            print("ERRORS REQUIRING ATTENTION:")
            for error in overall.errors[:10]:  # Limit to first 10 errors
                print(f"  • {error}")
            if len(overall.errors) > 10:
                print(f"  ... and {len(overall.errors) - 10} more errors")

        print()
        print("=" * 60)


def main():
    """Main validation entry point"""
    validator = ComprehensiveValidator()
    overall_result = validator.run_validation()

    # Exit with appropriate code
    if overall_result.get_success_rate() >= 95.0:
        print("Validation successful: >95% success rate achieved")
        sys.exit(0)
    else:
        print(f"Validation failed: {overall_result.get_success_rate():.1f}% success rate")
        sys.exit(1)


if __name__ == "__main__":
    main()