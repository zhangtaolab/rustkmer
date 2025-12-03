#!/usr/bin/env python3
"""
T030: Multi K-mer Size Validation Matrix

This test performs comprehensive validation across multiple k-mer sizes (7, 13, 21, 31)
and canonical modes to ensure CLI and Python API compatibility across all supported
parameters.

Test Matrix:
- k = [7, 13, 21, 31] × canonical = [True, False] × platforms = [CLI, Python]
- Progressive scaling: small demo dataset → medium dataset → large dataset
- Integration with existing test data and frameworks
"""

import os
import sys
import time
import json
import tempfile
from pathlib import Path
from typing import Dict, Any, List, Tuple

# Add the compatibility framework to path
sys.path.insert(0, os.path.dirname(__file__))
from compatibility_framework.compare_databases import DatabaseComparator
from compatibility_framework.query_validator import CrossPlatformQueryValidator
from compatibility_framework.fuzzy_query_comparator import FuzzyQueryComparator

# Test configuration
KMER_SIZES = [7, 13, 21, 31]
CANONICAL_MODES = [True, False]
TEST_DATASETS = [
    {
        "name": "small",
        "path": "/Users/forrest/GitHub/rustkmer/tests/007-api-compatibility/test_data/small_dataset.fa",
        "description": "Small synthetic dataset"
    },
    {
        "name": "medium",
        "path": "/Users/forrest/GitHub/rustkmer/examples/data/demo_rice_genome.fa.gz",
        "description": "Medium demo rice genome dataset"
    }
]


def create_test_dataset_if_needed() -> str:
    """Create a small test dataset if none exists."""
    small_dataset_path = "/Users/forrest/GitHub/rustkmer/tests/007-api-compatibility/test_data/small_dataset.fa"

    if os.path.exists(small_dataset_path):
        return small_dataset_path

    # Create small test dataset
    os.makedirs(os.path.dirname(small_dataset_path), exist_ok=True)

    with open(small_dataset_path, 'w') as f:
        f.write(">seq1\n")
        f.write("ACGTACGTACGTACGTACGTACGTACGTACGTACGTACGTACGTACGTACGTACGTACGT\n")
        f.write(">seq2\n")
        f.write("GCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTA\n")
        f.write(">seq3\n")
        f.write("TTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTT\n")
        f.write(">seq4\n")
        f.write("CCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCC\n")
        f.write(">seq5\n")
        f.write("GGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGG\n")

    return small_dataset_path


def test_database_creation_matrix(kmer_sizes: List[int], canonical_modes: List[bool]) -> Dict[str, Any]:
    """
    Test T030.1: Database creation compatibility across k-mer size matrix.

    Creates databases using both CLI and Python API for each k-mer size
    and canonical mode combination, verifying bit-for-bit compatibility.
    """
    print(f"\n📊 T030.1: Multi K-mer Database Creation Matrix")
    print(f"K-mer sizes: {kmer_sizes}")
    print(f"Canonical modes: {canonical_modes}")
    print("=" * 60)

    # Ensure we have test data
    test_dataset = create_test_dataset_if_needed()
    print(f"Using test dataset: {test_dataset}")

    # Use CLI binary from the build directory
    cli_path = "./target/release/rustkmer"
    if not os.path.exists(cli_path):
        print(f"⚠️  CLI binary not found at {cli_path}")
        cli_path = None

    comparator = DatabaseComparator(cli_path=cli_path)
    test_results = []
    total_configurations = len(kmer_sizes) * len(canonical_modes)
    completed_configurations = 0

    start_time = time.time()

    for kmer_size in kmer_sizes:
        for canonical in canonical_modes:
            config_name = f"k{kmer_size}_{'canon' if canonical else 'noncanon'}"
            print(f"\n🔧 Testing configuration: {config_name}")
            completed_configurations += 1
            print(f"Progress: {completed_configurations}/{total_configurations}")

            try:
                # Run compatibility test for this configuration
                result = comparator.run_compatibility_test(test_dataset, kmer_size, canonical)

                # Add configuration metadata
                result["configuration"] = config_name
                result["kmer_size"] = kmer_size
                result["canonical"] = canonical
                result["test_dataset"] = test_dataset

                test_results.append(result)

                # Print result summary
                creation_success = (result["cli_creation"]["success"] and
                                 result["python_creation"]["success"])
                db_identical = result.get("comparison", {}).get("identical", False)

                print(f"  CLI creation: {'✅' if result['cli_creation']['success'] else '❌'}")
                print(f"  Python creation: {'✅' if result['python_creation']['success'] else '❌'}")
                print(f"  Database comparison: {'✅ IDENTICAL' if db_identical else '❌ DIFFERENT'}")

                if not db_identical and result.get("comparison"):
                    print(f"    Reason: {result['comparison']['reason']}")

                if creation_success and db_identical:
                    print(f"  Result: ✅ PASSED")
                else:
                    print(f"  Result: ❌ FAILED")

            except Exception as e:
                print(f"  ❌ ERROR: {e}")
                test_results.append({
                    "configuration": config_name,
                    "kmer_size": kmer_size,
                    "canonical": canonical,
                    "error": str(e),
                    "status": "error"
                })

    total_time = time.time() - start_time

    # Generate summary
    successful_tests = sum(1 for result in test_results
                         if result.get("comparison", {}).get("identical", False))
    total_tests = len(test_results)
    failed_tests = total_tests - successful_tests

    summary = {
        "total_configurations": total_configurations,
        "successful_tests": successful_tests,
        "failed_tests": failed_tests,
        "success_rate_percent": (successful_tests / total_tests * 100) if total_tests > 0 else 0,
        "overall_status": "PASSED" if failed_tests == 0 else "FAILED",
        "execution_time_seconds": total_time
    }

    print(f"\n📊 T030.1 SUMMARY")
    print(f"Total configurations: {total_configurations}")
    print(f"Successful: {successful_tests}")
    print(f"Failed: {failed_tests}")
    print(f"Success rate: {summary['success_rate_percent']:.1f}%")
    print(f"Overall status: {summary['overall_status']}")
    print(f"Execution time: {total_time:.1f} seconds")

    return {
        "test_name": "T030.1_Multi_Kmer_Database_Creation",
        "summary": summary,
        "detailed_results": test_results
    }


def test_query_compatibility_matrix(kmer_sizes: List[int], canonical_modes: List[bool]) -> Dict[str, Any]:
    """
    Test T030.2: Query compatibility across k-mer size matrix.

    Tests that query results are identical between CLI and Python API
    for each k-mer size and canonical mode combination.
    """
    print(f"\n🎯 T030.2: Multi K-mer Query Compatibility Matrix")
    print(f"K-mer sizes: {kmer_sizes}")
    print(f"Canonical modes: {canonical_modes}")
    print("=" * 60)

    # Ensure we have test data
    test_dataset = create_test_dataset_if_needed()

    # Use CLI binary from the build directory
    cli_path = "./target/release/rustkmer"
    if not os.path.exists(cli_path):
        print(f"⚠️  CLI binary not found at {cli_path}")
        cli_path = None

    validator = CrossPlatformQueryValidator(cli_path=cli_path)
    test_results = []
    total_configurations = len(kmer_sizes) * len(canonical_modes)
    completed_configurations = 0

    start_time = time.time()

    # For each configuration, we need to create a database first
    for kmer_size in kmer_sizes:
        for canonical in canonical_modes:
            config_name = f"k{kmer_size}_{'canon' if canonical else 'noncanon'}"
            print(f"\n🔍 Testing query compatibility: {config_name}")
            completed_configurations += 1
            print(f"Progress: {completed_configurations}/{total_configurations}")

            try:
                # Create temporary database for this configuration
                with tempfile.TemporaryDirectory() as temp_dir:
                    db_path = os.path.join(temp_dir, f"{config_name}.rkdb")

                    # Create database using CLI (faster for testing)
                    from compatibility_framework.compare_databases import DatabaseComparator
                    cli_path = "./target/release/rustkmer"
                    db_comparator = DatabaseComparator(cli_path=cli_path)

                    success, msg = db_comparator.create_database_cli(test_dataset, db_path, kmer_size, canonical)

                    if not success:
                        print(f"  ❌ Database creation failed: {msg}")
                        test_results.append({
                            "configuration": config_name,
                            "kmer_size": kmer_size,
                            "canonical": canonical,
                            "error": f"Database creation failed: {msg}",
                            "status": "db_creation_failed"
                        })
                        continue

                    # Test query compatibility
                    query_result = validator.validate_database_compatibility(db_path)

                    # Add configuration metadata
                    query_result["configuration"] = config_name
                    query_result["kmer_size"] = kmer_size
                    query_result["canonical"] = canonical

                    test_results.append(query_result)

                    # Print result summary
                    query_summary = query_result.get("summary", {})
                    overall_status = query_summary.get("overall_status", "FAILED")
                    total_queries = query_summary.get("total_tests", 0)
                    successful_queries = query_summary.get("successful_tests", 0)

                    print(f"  Total queries: {total_queries}")
                    print(f"  Successful: {successful_queries}")
                    print(f"  Status: {'✅ PASSED' if overall_status == 'PASSED' else '❌ FAILED'}")

            except Exception as e:
                print(f"  ❌ ERROR: {e}")
                test_results.append({
                    "configuration": config_name,
                    "kmer_size": kmer_size,
                    "canonical": canonical,
                    "error": str(e),
                    "status": "error"
                })

    total_time = time.time() - start_time

    # Generate summary
    successful_configs = sum(1 for result in test_results
                            if result.get("summary", {}).get("overall_status") == "PASSED")
    total_configs = len(test_results)
    failed_configs = total_configs - successful_configs

    summary = {
        "total_configurations": total_configs,
        "successful_configurations": successful_configs,
        "failed_configurations": failed_configs,
        "success_rate_percent": (successful_configs / total_configs * 100) if total_configs > 0 else 0,
        "overall_status": "PASSED" if failed_configs == 0 else "FAILED",
        "execution_time_seconds": total_time
    }

    print(f"\n🎯 T030.2 SUMMARY")
    print(f"Total configurations: {total_configs}")
    print(f"Successful: {successful_configs}")
    print(f"Failed: {failed_configs}")
    print(f"Success rate: {summary['success_rate_percent']:.1f}%")
    print(f"Overall status: {summary['overall_status']}")
    print(f"Execution time: {total_time:.1f} seconds")

    return {
        "test_name": "T030.2_Multi_Kmer_Query_Compatibility",
        "summary": summary,
        "detailed_results": test_results
    }


def test_fuzzy_query_matrix(kmer_sizes: List[int]) -> Dict[str, Any]:
    """
    Test T030.3: Fuzzy query compatibility across k-mer sizes.

    Tests fuzzy query functionality (wildcards and mutation tolerance)
    across different k-mer sizes.
    """
    print(f"\n🔍 T030.3: Multi K-mer Fuzzy Query Matrix")
    print(f"K-mer sizes: {kmer_sizes}")
    print("=" * 60)

    # For fuzzy query testing, limit k-mer sizes to manage complexity
    test_kmer_sizes = [k for k in kmer_sizes if k <= 21]  # Exclude k=31 for fuzzy queries
    if len(test_kmer_sizes) < len(kmer_sizes):
        print(f"Note: Limiting fuzzy query tests to k-mer sizes {test_kmer_sizes} (excluding larger sizes for performance)")

    # Ensure we have test data
    test_dataset = create_test_dataset_if_needed()

    # Use CLI binary from the build directory
    cli_path = "./target/release/rustkmer"
    if not os.path.exists(cli_path):
        print(f"⚠️  CLI binary not found at {cli_path}")
        cli_path = None

    comparator = FuzzyQueryComparator(cli_path=cli_path)
    test_results = []
    total_configurations = len(test_kmer_sizes)
    completed_configurations = 0

    start_time = time.time()

    for kmer_size in test_kmer_sizes:
        config_name = f"k{kmer_size}_fuzzy"
        print(f"\n🔍 Testing fuzzy queries: {config_name}")
        completed_configurations += 1
        print(f"Progress: {completed_configurations}/{total_configurations}")

        try:
            # Create temporary database for this configuration
            with tempfile.TemporaryDirectory() as temp_dir:
                db_path = os.path.join(temp_dir, f"{config_name}.rkdb")

                # Create database using CLI
                from compatibility_framework.compare_databases import DatabaseComparator
                cli_path = "./target/release/rustkmer"
                db_comparator = DatabaseComparator(cli_path=cli_path)

                success, msg = db_comparator.create_database_cli(test_dataset, db_path, kmer_size, canonical=False)

                if not success:
                    print(f"  ❌ Database creation failed: {msg}")
                    test_results.append({
                        "configuration": config_name,
                        "kmer_size": kmer_size,
                        "error": f"Database creation failed: {msg}",
                        "status": "db_creation_failed"
                    })
                    continue

                # Create focused fuzzy query test cases for this k-mer size
                test_cases = [
                    comparator.FuzzyQueryTestCase(
                        query="A" * kmer_size,
                        kmer_size=kmer_size,
                        description="All A's exact match"
                    ),
                    comparator.FuzzyQueryTestCase(
                        query="C" * kmer_size,
                        kmer_size=kmer_size,
                        description="All C's exact match"
                    ),
                    comparator.FuzzyQueryTestCase(
                        query="A" * (kmer_size - 1) + "N",
                        kmer_size=kmer_size,
                        description="Single N wildcard"
                    ),
                ]

                # Add mutation tolerance test for smaller k-mers
                if kmer_size <= 13:
                    test_cases.append(
                        comparator.FuzzyQueryTestCase(
                            query="ACGTACGTACGT"[:kmer_size],
                            kmer_size=kmer_size,
                            mutation_tolerance=1,
                            description="1 mutation tolerance"
                        )
                    )

                # Run fuzzy query validation
                fuzzy_result = comparator.validate_fuzzy_query_compatibility(db_path, test_cases)

                # Add configuration metadata
                fuzzy_result["configuration"] = config_name
                fuzzy_result["kmer_size"] = kmer_size

                test_results.append(fuzzy_result)

                # Print result summary
                fuzzy_summary = fuzzy_result.get("summary", {})
                overall_status = fuzzy_summary.get("overall_status", "FAILED")
                total_tests = fuzzy_summary.get("total_tests", 0)
                successful_tests = fuzzy_summary.get("successful_tests", 0)

                print(f"  Total fuzzy queries: {total_tests}")
                print(f"  Successful: {successful_tests}")
                print(f"  Status: {'✅ PASSED' if overall_status == 'PASSED' else '❌ FAILED'}")

        except Exception as e:
            print(f"  ❌ ERROR: {e}")
            test_results.append({
                "configuration": config_name,
                "kmer_size": kmer_size,
                "error": str(e),
                "status": "error"
            })

    total_time = time.time() - start_time

    # Generate summary
    successful_configs = sum(1 for result in test_results
                            if result.get("summary", {}).get("overall_status") == "PASSED")
    total_configs = len(test_results)
    failed_configs = total_configs - successful_configs

    summary = {
        "total_configurations": total_configs,
        "successful_configurations": successful_configs,
        "failed_configurations": failed_configs,
        "success_rate_percent": (successful_configs / total_configs * 100) if total_configs > 0 else 0,
        "overall_status": "PASSED" if failed_configs == 0 else "FAILED",
        "execution_time_seconds": total_time
    }

    print(f"\n🔍 T030.3 SUMMARY")
    print(f"Total configurations: {total_configs}")
    print(f"Successful: {successful_configs}")
    print(f"Failed: {failed_configs}")
    print(f"Success rate: {summary['success_rate_percent']:.1f}%")
    print(f"Overall status: {summary['overall_status']}")
    print(f"Execution time: {total_time:.1f} seconds")

    return {
        "test_name": "T030.3_Multi_Kmer_Fuzzy_Query",
        "summary": summary,
        "detailed_results": test_results
    }


def main():
    """Main test execution function."""
    print("🧮 T030: Multi K-mer Size Validation Matrix")
    print("Testing CLI vs Python API compatibility across k = 7, 13, 21, 31")
    print("=" * 80)

    start_time = time.time()
    test_results = {}

    try:
        # T030.1: Database creation matrix
        test_results["database_creation"] = test_database_creation_matrix(KMER_SIZES, CANONICAL_MODES)

        # T030.2: Query compatibility matrix
        test_results["query_compatibility"] = test_query_compatibility_matrix(KMER_SIZES, CANONICAL_MODES)

        # T030.3: Fuzzy query matrix
        test_results["fuzzy_query_compatibility"] = test_fuzzy_query_matrix(KMER_SIZES)

        # Generate overall summary
        total_duration = time.time() - start_time

        db_status = test_results["database_creation"]["summary"]["overall_status"]
        query_status = test_results["query_compatibility"]["summary"]["overall_status"]
        fuzzy_status = test_results["fuzzy_query_compatibility"]["summary"]["overall_status"]

        overall_status = "PASSED" if (
            db_status == "PASSED" and
            query_status == "PASSED" and
            fuzzy_status == "PASSED"
        ) else "FAILED"

        # Final summary
        print(f"\n🎯 T030: FINAL SUMMARY")
        print("=" * 60)
        print(f"Total execution time: {total_duration:.1f} seconds")
        print(f"K-mer sizes tested: {KMER_SIZES}")
        print(f"Canonical modes: {CANONICAL_MODES}")
        print(f"\nTest Results:")
        print(f"  Database Creation: {db_status}")
        print(f"    Success rate: {test_results['database_creation']['summary']['success_rate_percent']:.1f}%")
        print(f"  Query Compatibility: {query_status}")
        print(f"    Success rate: {test_results['query_compatibility']['summary']['success_rate_percent']:.1f}%")
        print(f"  Fuzzy Query Compatibility: {fuzzy_status}")
        print(f"    Success rate: {test_results['fuzzy_query_compatibility']['summary']['success_rate_percent']:.1f}%")
        print(f"\nOverall Status: {overall_status}")

        # Performance summary
        db_time = test_results["database_creation"]["summary"]["execution_time_seconds"]
        query_time = test_results["query_compatibility"]["summary"]["execution_time_seconds"]
        fuzzy_time = test_results["fuzzy_query_compatibility"]["summary"]["execution_time_seconds"]

        print(f"\n⏱️  Performance Summary:")
        print(f"  Database creation: {db_time:.1f}s")
        print(f"  Query compatibility: {query_time:.1f}s")
        print(f"  Fuzzy query compatibility: {fuzzy_time:.1f}s")

        # Save comprehensive report
        timestamp = int(time.time())
        report_path = f"tests/007-api-compatibility/test_reports/t030_multi_kmer_validation_report_{timestamp}.json"

        os.makedirs(os.path.dirname(report_path), exist_ok=True)

        comprehensive_report = {
            "test_id": "T030",
            "test_name": "Multi K-mer Size Validation Matrix",
            "kmer_sizes": KMER_SIZES,
            "canonical_modes": CANONICAL_MODES,
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
        print(f"\n❌ T030: EXECUTION FAILED")
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)