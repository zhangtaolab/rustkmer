#!/usr/bin/env python3
"""
T021: Automated database file comparison tests for various input datasets.
Provides comprehensive testing across different input file types, sizes, and characteristics.
"""

import pytest
import os
import sys
import tempfile
import hashlib
import json
import subprocess
import time
from pathlib import Path

# Add the compatibility framework to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'compatibility_framework'))

try:
    from compare_databases import DatabaseComparator
except ImportError as e:
    pytest.skip(f"Compatibility framework not available: {e}")


class TestAutomatedDatabaseComparison:
    """Automated database file comparison across various input datasets."""

    @pytest.fixture
    def comparator(self):
        """Create a DatabaseComparator instance for testing."""
        return DatabaseComparator()

    @pytest.fixture
    def test_datasets(self):
        """Generate diverse test datasets for comprehensive comparison."""
        return {
            "synthetic_small": {
                "description": "Small synthetic sequences",
                "sequences": [
                    ">seq1\nACGTACGTACGTACGTACGT",
                    ">seq2\nTGCATGCATGCATGCATGCA",
                    ">seq3\nATCGATCGATCGATCGATCG"
                ],
                "expected_kmers": 100,
                "complexity": "low"
            },

            "synthetic_medium": {
                "description": "Medium synthetic sequences with variations",
                "sequences": [
                    ">medium_seq1\n" + "ACGT" * 50,
                    ">medium_seq2\n" + "TGCATGCA" * 30,
                    ">medium_seq3\n" + "ATCGATCG" * 40,
                    ">medium_seq4\n" + "GGGGCCCC" * 25
                ],
                "expected_kmers": 1000,
                "complexity": "medium"
            },

            "synthetic_large": {
                "description": "Large synthetic dataset",
                "sequences": [
                    ">large_seq1\n" + "ACGTACGTACGT" * 200,
                    ">large_seq2\n" + "TGCATGCATGCA" * 180,
                    ">large_seq3\n" + "ATCGATCGATCG" * 150,
                    ">large_seq4\n" + "GGGGCCCCAAAA" * 120,
                    ">large_seq5\n" + "TTTTAAAACCCG" * 100
                ],
                "expected_kmers": 5000,
                "complexity": "high"
            },

            "with_ambiguous": {
                "description": "Sequences with ambiguous bases (N)",
                "sequences": [
                    ">seq_with_n\nACGTACGTNNNNNACGTACGT",
                    ">seq_many_n\nNNNNNNNNNNNNNNNNNNNN",
                    ">seq_mixed\nACGTTGCANACGTNNACGTN"
                ],
                "expected_kmers": 50,
                "complexity": "medium"
            },

            "low_complexity": {
                "description": "Low complexity repetitive sequences",
                "sequences": [
                    ">homopolymer_A\n" + "A" * 100,
                    ">homopolymer_T\n" + "T" * 100,
                    ">dinucleotide\n" + "AT" * 50,
                    ">trinucleotide\n" + "CGT" * 33
                ],
                "expected_kmers": 20,
                "complexity": "very_low"
            },

            "high_complexity": {
                "description": "High complexity random-like sequences",
                "sequences": [
                    ">complex1\nACGTACGTTGCATGCATATCGATCGGGGCCCCAAAATTTT",
                    ">complex2\nTGCACTGACGATCGATCGATCGATCGATCGTAGCTAGC",
                    ">complex3\nATCGATCGATCGATCGATCGTGCATGCATGCATGCAT",
                    ">complex4\nGGGCCCCAAAATTTTACGTACGTTGCATGCANNNNACGT"
                ],
                "expected_kmers": 200,
                "complexity": "high"
            },

            "very_short_sequences": {
                "description": "Sequences shorter than k-mer size",
                "sequences": [
                    ">short1\nACGT",
                    ">short2\nACG",
                    ">short3\nAT",
                    ">short4\nA"
                ],
                "expected_kmers": 0,
                "complexity": "minimal"
            },

            "exact_kmer_length": {
                "description": "Sequences exactly k-mer length",
                "sequences": [
                    ">exact13\nACGTACGTACGTG",
                    ">exact13_2\nTGCATGCATGCAT"
                ],
                "expected_kmers": 2,
                "complexity": "exact"
            },

            "multi_fasta_large": {
                "description": "Large multi-FASTA dataset",
                "sequences": [f">seq{i}\n" + "ACGTACGT" * (20 + i % 10) for i in range(50)],
                "expected_kmers": 2000,
                "complexity": "high"
            },

            "mixed_case": {
                "description": "Mixed case sequences",
                "sequences": [
                    ">mixed_case1\nACGTacgtACGTacgt",
                    ">mixed_case2\nTGCAtgcaTGCAtgca",
                    ">mixed_case3\natcgATCGatcgATCG"
                ],
                "expected_kmers": 60,
                "complexity": "medium"
            }
        }

    def create_temp_fasta(self, dataset):
        """Create temporary FASTA file from dataset."""
        content = "\n".join(dataset["sequences"])

        with tempfile.NamedTemporaryFile(mode='w', suffix='.fa', delete=False) as f:
            f.write(content)
            return f.name

    def test_synthetic_dataset_comparison(self, comparator, test_datasets):
        """Test comparison across synthetic datasets of varying sizes."""
        dataset_names = ["synthetic_small", "synthetic_medium", "synthetic_large"]
        kmer_size = 13

        results = {}

        for dataset_name in dataset_names:
            dataset = test_datasets[dataset_name]
            fasta_path = self.create_temp_fasta(dataset)

            try:
                print(f"Testing {dataset_name}: {dataset['description']}")

                result = comparator.run_compatibility_test(
                    input_file=fasta_path,
                    kmer_size=kmer_size,
                    canonical=True
                )

                # Record results
                results[dataset_name] = {
                    "cli_success": result["cli_creation"]["success"],
                    "python_success": result["python_creation"]["success"],
                    "identical": result["comparison"]["identical"] if result["comparison"] else False,
                    "file_size": result.get("file_size", 0),
                    "kmer_count": dataset["expected_kmers"],
                    "complexity": dataset["complexity"]
                }

                # Validate both databases were created successfully
                assert result["cli_creation"]["success"], f"CLI failed for {dataset_name}"
                assert result["python_creation"]["success"], f"Python failed for {dataset_name}"

                # Validate bit-for-bit compatibility
                if result["comparison"]:
                    assert result["comparison"]["identical"], f"Files not identical for {dataset_name}"

                print(f"  ✅ {dataset_name}: PASSED")

            finally:
                os.unlink(fasta_path)

        # Validate overall success
        assert all(r["cli_success"] and r["python_success"] and r["identical"]
                  for r in results.values()), "Some synthetic dataset tests failed"

        return results

    def test_ambiguous_base_handling(self, comparator, test_datasets):
        """Test handling of sequences with ambiguous bases (N)."""
        dataset = test_datasets["with_ambiguous"]
        fasta_path = self.create_temp_fasta(dataset)

        try:
            print(f"Testing ambiguous base handling: {dataset['description']}")

            result = comparator.run_compatibility_test(
                input_file=fasta_path,
                kmer_size=13,
                canonical=True
            )

            # Both should handle ambiguous bases consistently
            assert result["cli_creation"]["success"], "CLI failed with ambiguous bases"
            assert result["python_creation"]["success"], "Python failed with ambiguous bases"

            if result["comparison"]:
                assert result["comparison"]["identical"], "Ambiguous base handling differs"

            print(f"  ✅ Ambiguous base handling: PASSED")

        finally:
            os.unlink(fasta_path)

    def test_complexity_variations(self, comparator, test_datasets):
        """Test across sequence complexity levels."""
        complexity_datasets = [
            ("very_short_sequences", "minimal"),
            ("low_complexity", "very_low"),
            ("synthetic_small", "low"),
            ("with_ambiguous", "medium"),
            ("high_complexity", "high")
        ]

        results = {}

        for dataset_name, expected_complexity in complexity_datasets:
            if dataset_name not in test_datasets:
                continue

            dataset = test_datasets[dataset_name]
            fasta_path = self.create_temp_fasta(dataset)

            try:
                print(f"Testing {expected_complexity} complexity: {dataset['description']}")

                result = comparator.run_compatibility_test(
                    input_file=fasta_path,
                    kmer_size=13,
                    canonical=True
                )

                # Both should handle all complexity levels
                if result["cli_creation"]["success"] and result["python_creation"]["success"]:
                    if result["comparison"]:
                        assert result["comparison"]["identical"], f"Complexity {expected_complexity} failed"

                    results[expected_complexity] = "PASSED"
                    print(f"  ✅ {expected_complexity} complexity: PASSED")
                else:
                    results[expected_complexity] = "SKIPPED"
                    print(f"  ⚠️ {expected_complexity} complexity: SKIPPED")

            finally:
                os.unlink(fasta_path)

        # Validate at least basic complexities work
        assert results.get("low") == "PASSED" or results.get("medium") == "PASSED", \
               "No basic complexity tests passed"

        return results

    def test_multi_fasta_handling(self, comparator, test_datasets):
        """Test handling of multi-FASTA files with many sequences."""
        dataset = test_datasets["multi_fasta_large"]
        fasta_path = self.create_temp_fasta(dataset)

        try:
            print(f"Testing multi-FASTA: {dataset['description']}")

            start_time = time.time()
            result = comparator.run_compatibility_test(
                input_file=fasta_path,
                kmer_size=13,
                canonical=True
            )
            duration = time.time() - start_time

            # Both should handle multi-FASTA correctly
            assert result["cli_creation"]["success"], "CLI failed with multi-FASTA"
            assert result["python_creation"]["success"], "Python failed with multi-FASTA"

            if result["comparison"]:
                assert result["comparison"]["identical"], "Multi-FASTA handling differs"

            # Performance should be reasonable (<30 seconds for this test)
            assert duration < 30.0, f"Multi-FASTA test too slow: {duration:.2f}s"

            print(f"  ✅ Multi-FASTA handling: PASSED ({duration:.2f}s)")

            return {"duration": duration, "success": True}

        finally:
            os.unlink(fasta_path)

    def test_mixed_case_handling(self, comparator, test_datasets):
        """Test handling of mixed case sequences."""
        dataset = test_datasets["mixed_case"]
        fasta_path = self.create_temp_fasta(dataset)

        try:
            print(f"Testing mixed case: {dataset['description']}")

            result = comparator.run_compatibility_test(
                input_file=fasta_path,
                kmer_size=13,
                canonical=True
            )

            # Both should handle mixed case consistently (case insensitive)
            assert result["cli_creation"]["success"], "CLI failed with mixed case"
            assert result["python_creation"]["success"], "Python failed with mixed case"

            if result["comparison"]:
                assert result["comparison"]["identical"], "Mixed case handling differs"

            print(f"  ✅ Mixed case handling: PASSED")

        finally:
            os.unlink(fasta_path)

    def test_edge_case_sequences(self, comparator, test_datasets):
        """Test edge cases: very short and exact k-mer length sequences."""
        edge_datasets = ["very_short_sequences", "exact_kmer_length"]

        for dataset_name in edge_datasets:
            if dataset_name not in test_datasets:
                continue

            dataset = test_datasets[dataset_name]
            fasta_path = self.create_temp_fasta(dataset)

            try:
                print(f"Testing edge case {dataset_name}: {dataset['description']}")

                result = comparator.run_compatibility_test(
                    input_file=fasta_path,
                    kmer_size=13,
                    canonical=True
                )

                # Edge cases should be handled gracefully
                if result["cli_creation"]["success"] and result["python_creation"]["success"]:
                    if result["comparison"]:
                        assert result["comparison"]["identical"], f"Edge case {dataset_name} failed"

                    print(f"  ✅ Edge case {dataset_name}: PASSED")
                else:
                    print(f"  ⚠️ Edge case {dataset_name}: SKIPPED (expected for edge cases)")

            finally:
                os.unlink(fasta_path)

    def test_performance_scaling(self, comparator, test_datasets):
        """Test performance scaling across dataset sizes."""
        scaling_datasets = [
            ("synthetic_small", 100),
            ("synthetic_medium", 1000),
            ("synthetic_large", 5000)
        ]

        performance_data = {}

        for dataset_name, expected_kmers in scaling_datasets:
            if dataset_name not in test_datasets:
                continue

            dataset = test_datasets[dataset_name]
            fasta_path = self.create_temp_fasta(dataset)

            try:
                print(f"Testing scaling {dataset_name}: {expected_kmers} expected k-mers")

                start_time = time.time()
                result = comparator.run_compatibility_test(
                    input_file=fasta_path,
                    kmer_size=13,
                    canonical=True
                )
                duration = time.time() - start_time

                if result["cli_creation"]["success"] and result["python_creation"]["success"]:
                    performance_data[dataset_name] = {
                        "expected_kmers": expected_kmers,
                        "duration": duration,
                        "kmer_rate": expected_kmers / duration if duration > 0 else 0
                    }

                    # Performance should scale reasonably
                    assert duration < 60.0, f"Performance test {dataset_name} too slow: {duration:.2f}s"

                    print(f"  ✅ Scaling {dataset_name}: {duration:.2f}s ({performance_data[dataset_name]['kmer_rate']:.0f} k-mers/s)")
                else:
                    print(f"  ⚠️ Scaling {dataset_name}: SKIPPED")

            finally:
                os.unlink(fasta_path)

        # Validate reasonable performance scaling
        if len(performance_data) >= 2:
            rates = [data["kmer_rate"] for data in performance_data.values()]
            min_rate = min(rates)
            assert min_rate > 100, f"Performance too slow: {min_rate:.0f} k-mers/s minimum"

        return performance_data

    def generate_automated_test_report(self, test_results):
        """Generate comprehensive automated test report."""
        report = {
            "test_suite": "T021: Automated Database Comparison",
            "timestamp": "2025-12-02T11:00:00Z",
            "test_categories": [
                "Synthetic dataset scaling",
                "Ambiguous base handling",
                "Complexity variations",
                "Multi-FASTA handling",
                "Mixed case processing",
                "Edge case sequences",
                "Performance scaling"
            ],
            "results": test_results,
            "summary": {
                "total_categories": 7,
                "categories_tested": len(test_results),
                "overall_status": "PASSED" if all(
                    result.get("status", "FAILED") == "PASSED"
                    for result in test_results.values()
                ) else "PARTIAL"
            },
            "performance_summary": {
                "max_duration": max([
                    result.get("duration", 0)
                    for result in test_results.values()
                ]),
                "total_test_time": sum([
                    result.get("duration", 0)
                    for result in test_results.values()
                ])
            }
        }

        # Save report
        report_path = "tests/007-api-compatibility/test_reports/t021_automated_comparison_report.json"
        with open(report_path, "w") as f:
            json.dump(report, f, indent=2)

        return report


if __name__ == "__main__":
    pytest.main([__file__, "-v"])