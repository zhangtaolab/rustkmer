#!/usr/bin/env python3
"""
T031: Large-Scale Production Validation using Rice Genome Dataset

This test performs comprehensive validation using the 364MB rice genome dataset
from `/Users/forrest/Temp/demodata/fasta/osa1_r7.asm.fa` to ensure production-level
compatibility between CLI and Python API.

Test Phases:
1. Database Creation: CLI vs Python API (bit-for-bit comparison)
2. Query Accuracy: Regular queries on both platforms
3. Cross-Platform Usage: CLI databases accessed via Python API and vice versa
4. Fuzzy Query: Wildcard and mutation tolerance testing
5. Resource Management: Memory usage and timeout handling
"""

import os
import sys
import time
import json
from pathlib import Path
from typing import Dict, Any

# Add the compatibility framework to path
sys.path.insert(0, os.path.dirname(__file__))
from compatibility_framework.large_dataset_validator import LargeDatasetValidator
from compatibility_framework.fuzzy_query_comparator import FuzzyQueryComparator
from compatibility_framework.query_validator import CrossPlatformQueryValidator

# Test configuration
RICE_GENOME_DATASET = "/Users/forrest/Temp/demodata/fasta/osa1_r7.asm.fa"
FALLBACK_DATASET = "/Users/forrest/GitHub/rustkmer/examples/data/demo_rice_genome.fa.gz"


def validate_dataset_availability():
    """Validate that the required dataset is available."""
    if os.path.exists(RICE_GENOME_DATASET):
        return RICE_GENOME_DATASET, False  # False = don't use sample
    elif os.path.exists(FALLBACK_DATASET):
        print(f"⚠️  Rice genome dataset not found at {RICE_GENOME_DATASET}")
        print(f"Using fallback dataset: {FALLBACK_DATASET}")
        return FALLBACK_DATASET, True  # True = use sample
    else:
        raise FileNotFoundError(
            f"Neither rice genome dataset ({RICE_GENOME_DATASET}) "
            f"nor fallback dataset ({FALLBACK_DATASET}) found"
        )


def test_large_scale_database_compatibility(dataset_path: str, use_sample: bool = False) -> Dict[str, Any]:
    """
    Test T031.1: Large-scale database creation compatibility.

    Creates databases using both CLI and Python API on the large dataset
    and verifies they are bit-for-bit identical.
    """
    print(f"\n🧬 T031.1: Large-Scale Database Creation Compatibility")
    print(f"Dataset: {dataset_path}")
    print(f"File size: {os.path.getsize(dataset_path) / (1024*1024):.1f} MB")
    print(f"Using sample: {use_sample}")
    print("=" * 60)

    validator = LargeDatasetValidator(
        memory_limit_gb=6.0,  # Increased for large dataset
        timeout_minutes=45     # Extended timeout for 364MB dataset
    )

    # Progress tracking
    def progress_callback(progress):
        percent = (progress.completed_steps / progress.total_steps) * 100
        print(f"  📊 Progress: {progress.completed_steps}/{progress.total_steps} ({percent:.1f}%) - {progress.current_operation}")
        if progress.total_bytes > 0:
            data_percent = (progress.bytes_processed / progress.total_bytes) * 100
            print(f"  📁 Data: {data_percent:.1f}% ({progress.bytes_processed // (1024*1024)} MB / {progress.total_bytes // (1024*1024)} MB)")

    validator.set_progress_callback(progress_callback)

    # Test with multiple k-mer sizes and canonical modes
    kmer_sizes = [13, 21]  # Reduced for large dataset to manage time
    canonical_modes = [True, False]

    try:
        results = validator.validate_large_dataset_compatibility(
            input_file=dataset_path,
            kmer_sizes=kmer_sizes,
            canonical_modes=canonical_modes,
            use_sample=use_sample
        )

        print(f"\n✅ T031.1 COMPLETED")
        print(f"Configurations tested: {results['summary']['total_configurations']}")
        print(f"Passed: {results['summary']['passed']}")
        print(f"Failed: {results['summary']['failed']}")
        print(f"Pass rate: {results['summary']['pass_rate_percent']:.1f}%")
        print(f"Database compatibility: {results['summary']['database_compatibility_rate']:.1f}%")
        print(f"Query compatibility: {results['summary']['query_compatibility_rate']:.1f}%")
        print(f"Cross-platform compatibility: {results['summary']['cross_platform_compatibility_rate']:.1f}%")

        # Resource usage summary
        if 'resource_usage' in results and 'max_memory_mb' in results['resource_usage']:
            resources = results['resource_usage']
            print(f"\n💾 Resource Usage:")
            print(f"  Peak memory: {resources['max_memory_mb']:.1f} MB")
            print(f"  Average memory: {resources['avg_memory_mb']:.1f} MB")
            print(f"  Peak CPU: {resources['max_cpu_percent']:.1f}%")

        return results

    except Exception as e:
        print(f"❌ T031.1 FAILED: {e}")
        return {
            "status": "error",
            "error": str(e),
            "summary": {"overall_status": "FAILED"}
        }


def test_fuzzy_query_compatibility(dataset_path: str, use_sample: bool = False) -> Dict[str, Any]:
    """
    Test T031.2: Large-scale fuzzy query compatibility.

    Tests fuzzy query functionality on databases created from the large dataset
    to ensure wildcard and mutation tolerance works identically on both platforms.
    """
    print(f"\n🔍 T031.2: Large-Scale Fuzzy Query Compatibility")
    print(f"Dataset: {dataset_path}")
    print("=" * 60)

    # For fuzzy query testing, we'll use a sample to manage computational complexity
    fuzzy_query_input = dataset_path
    if not use_sample and os.path.getsize(dataset_path) > 50 * 1024 * 1024:  # 50MB threshold
        print("Creating sample for fuzzy query testing (to manage complexity)...")
        validator = LargeDatasetValidator()
        fuzzy_query_input = validator._create_sample_dataset(dataset_path, sample_size_mb=20)
        print(f"Fuzzy query sample: {fuzzy_query_input}")

    try:
        comparator = FuzzyQueryComparator()

        # Create a database for fuzzy query testing
        import tempfile
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = os.path.join(temp_dir, "fuzzy_test_db.rkdb")

            print("Creating database for fuzzy query testing...")

            # Create database using CLI
            success, msg = comparator.database_comparator.create_database_cli(
                fuzzy_query_input, db_path, kmer_size=13, canonical=False
            )

            if not success:
                raise Exception(f"Failed to create database: {msg}")

            print("Running fuzzy query compatibility tests...")

            # Create a focused set of test cases for large-scale testing
            test_cases = [
                # Exact matches
                comparator.FuzzyQueryTestCase(
                    query="AAAAAAAAAAAAAA", kmer_size=13, description="All A's exact match"
                ),
                comparator.FuzzyQueryTestCase(
                    query="CCCCCCCCCCCCCC", kmer_size=13, description="All C's exact match"
                ),

                # Single wildcard
                comparator.FuzzyQueryTestCase(
                    query="AAAAAAAAAAAANA", kmer_size=13, description="Single N wildcard"
                ),
                comparator.FuzzyQueryTestCase(
                    query="ACGTACGTACGTN", kmer_size=13, description="Trailing N wildcard"
                ),

                # Multiple wildcards (limited for performance)
                comparator.FuzzyQueryTestCase(
                    query="AAAAAAAAANANA", kmer_size=13, description="Double N wildcards"
                ),

                # Mutation tolerance
                comparator.FuzzyQueryTestCase(
                    query="ACGTACGTACGTAC", kmer_size=13, mutation_tolerance=1, description="1 mutation tolerance"
                ),
                comparator.FuzzyQueryTestCase(
                    query="CCCCCCCCCCCCCC", kmer_size=13, mutation_tolerance=2, description="2 mutation tolerance"
                ),
            ]

            # Run fuzzy query validation
            results = comparator.validate_fuzzy_query_compatibility(db_path, test_cases)

            print(f"\n✅ T031.2 COMPLETED")
            summary = results["summary"]
            print(f"Total fuzzy query tests: {summary['total_tests']}")
            print(f"Successful: {summary['successful_tests']}")
            print(f"Failed: {summary['failed_tests']}")
            print(f"Success rate: {summary['success_rate_percent']:.1f}%")
            print(f"Overall status: {summary['overall_status']}")

            if "performance" in results:
                perf = results["performance"]
                print(f"\n⚡ Fuzzy Query Performance:")
                print(f"  Avg CLI time: {perf['avg_cli_time_ms']:.3f}ms")
                print(f"  Avg Python time: {perf['avg_python_time_ms']:.3f}ms")
                print(f"  Overhead: {perf['overhead_factor']:.1f}x")

            return results

    except Exception as e:
        print(f"❌ T031.2 FAILED: {e}")
        return {
            "status": "error",
            "error": str(e),
            "summary": {"overall_status": "FAILED"}
        }

    finally:
        # Clean up sample file if created
        if 'fuzzy_query_input' in locals() and fuzzy_query_input != dataset_path:
            try:
                os.remove(fuzzy_query_input)
                os.rmdir(os.path.dirname(fuzzy_query_input))
            except:
                pass


def test_cross_platform_interchangeability() -> Dict[str, Any]:
    """
    Test T031.3: Cross-platform database interchangeability.

    Tests that databases created by one platform can be used by the other
    platform without any issues.
    """
    print(f"\n🔄 T031.3: Cross-Platform Database Interchangeability")
    print("=" * 60)

    try:
        from compatibility_framework.compare_databases import DatabaseComparator

        comparator = DatabaseComparator()

        # Use a smaller dataset for interchangeability testing
        test_input = FALLBACK_DATASET
        if not os.path.exists(test_input):
            # Create minimal test data
            import tempfile
            with tempfile.NamedTemporaryFile(mode='w', suffix='.fa', delete=False) as f:
                f.write(">test_seq\nACGTACGTACGTACGTACGTACGTACGT\n>test_seq2\nGCTAGCTAGCTAGCTAGCTAGCTAGCTA\n")
                test_input = f.name

        try:
            # Run compatibility test
            result = comparator.run_compatibility_test(test_input, kmer_size=13, canonical=False)

            print(f"CLI creation: {'✅ SUCCESS' if result['cli_creation']['success'] else '❌ FAILED'}")
            print(f"Python creation: {'✅ SUCCESS' if result['python_creation']['success'] else '❌ FAILED'}")

            if result['comparison']:
                identical = result['comparison']['identical']
                print(f"Database comparison: {'✅ IDENTICAL' if identical else '❌ DIFFERENT'}")
                if not identical:
                    print(f"  Reason: {result['comparison']['reason']}")
            else:
                print("Database comparison: ❌ NOT PERFORMED")

            # Save test databases for manual inspection
            test_dbs_dir = "test_databases"
            if os.path.exists(test_dbs_dir):
                print(f"📁 Test databases saved in: {test_dbs_dir}")

            return {
                "status": "completed",
                "cli_creation_success": result['cli_creation']['success'],
                "python_creation_success": result['python_creation']['success'],
                "databases_identical": result['comparison']['identical'] if result['comparison'] else False,
                "overall_status": "PASSED" if (
                    result['cli_creation']['success'] and
                    result['python_creation']['success'] and
                    result['comparison']['identical']
                ) else "FAILED"
            }

        finally:
            # Clean up temporary file
            if test_input != FALLBACK_DATASET and os.path.exists(test_input):
                try:
                    os.remove(test_input)
                except:
                    pass

    except Exception as e:
        print(f"❌ T031.3 FAILED: {e}")
        return {
            "status": "error",
            "error": str(e),
            "overall_status": "FAILED"
        }


def main():
    """Main test execution function."""
    print("🧬 T031: Large-Scale Production Validation")
    print("Testing CLI vs Python API compatibility with rice genome dataset")
    print("=" * 80)

    start_time = time.time()
    test_results = {}

    try:
        # Validate dataset availability
        dataset_path, use_sample = validate_dataset_availability()

        # T031.1: Large-scale database compatibility
        test_results["database_compatibility"] = test_large_scale_database_compatibility(
            dataset_path, use_sample
        )

        # T031.2: Fuzzy query compatibility
        test_results["fuzzy_query_compatibility"] = test_fuzzy_query_compatibility(
            dataset_path, use_sample
        )

        # T031.3: Cross-platform interchangeability
        test_results["cross_platform_interchangeability"] = test_cross_platform_interchangeability()

        # Generate overall summary
        total_duration = time.time() - start_time

        db_status = test_results["database_compatibility"].get("summary", {}).get("overall_status", "FAILED")
        fuzzy_status = test_results["fuzzy_query_compatibility"].get("summary", {}).get("overall_status", "FAILED")
        cross_status = test_results["cross_platform_interchangeability"].get("overall_status", "FAILED")

        overall_status = "PASSED" if (
            db_status == "PASSED" and
            fuzzy_status == "PASSED" and
            cross_status == "PASSED"
        ) else "FAILED"

        # Final summary
        print(f"\n🎯 T031: FINAL SUMMARY")
        print("=" * 60)
        print(f"Total execution time: {total_duration:.1f} seconds")
        print(f"Dataset: {dataset_path}")
        print(f"Used sample: {use_sample}")
        print(f"\nTest Results:")
        print(f"  Database Compatibility: {db_status}")
        print(f"  Fuzzy Query Compatibility: {fuzzy_status}")
        print(f"  Cross-Platform Interchangeability: {cross_status}")
        print(f"\nOverall Status: {overall_status}")

        # Save comprehensive report
        timestamp = int(time.time())
        report_path = f"tests/007-api-compatibility/test_reports/t031_large_scale_validation_report_{timestamp}.json"

        os.makedirs(os.path.dirname(report_path), exist_ok=True)

        comprehensive_report = {
            "test_id": "T031",
            "test_name": "Large-Scale Production Validation",
            "dataset_path": dataset_path,
            "use_sample": use_sample,
            "execution_time_seconds": total_duration,
            "results": test_results,
            "overall_status": overall_status,
            "timestamp": timestamp
        }

        with open(report_path, 'w') as f:
            json.dump(comprehensive_report, f, indent=2)

        print(f"\n📄 Comprehensive report saved to: {report_path}")

        return overall_status == "PASSED"

    except Exception as e:
        print(f"\n❌ T031: EXECUTION FAILED")
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)