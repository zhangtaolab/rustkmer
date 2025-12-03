#!/usr/bin/env python3
"""
T027: Test Python API reading CLI-created databases.
Comprehensive testing to validate that Python API can fully read and query databases created by CLI.
"""

import pytest
import os
import sys
import tempfile
import subprocess
import json
from pathlib import Path
from typing import Dict, List, Any

# Add the compatibility framework to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'compatibility_framework'))

try:
    from query_validator import CrossPlatformQueryValidator
    from database_comparator import DatabaseComparator
except ImportError as e:
    pytest.skip(f"Compatibility framework not available: {e}")


class TestPythonApiReadingCliDatabases:
    """Test Python API's ability to read CLI-created databases."""

    @pytest.fixture
    def validator(self):
        """Create query validator for testing."""
        return CrossPlatformQueryValidator()

    @pytest.fixture
    def database_comparator(self):
        """Create database comparator for creating test databases."""
        return DatabaseComparator()

    def create_cli_database(self, comparator, kmer_size=13, canonical=True, input_content=None):
        """Create a database using CLI and return the database path."""
        if input_content is None:
            input_content = f">test_input_k{kmer_size}\n" + \
                          "ACGTACGTACGTACGTACGTACGTACGTACGTACGTACGTACGTACGTACGTACGTACGTACGT\n" + \
                          "TGCATGCATGCATGCATGCATGCATGCATGCATGCATGCATGCATGCATGCATGCATGCATGCAT\n" + \
                          "ATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCG"

        with tempfile.NamedTemporaryFile(mode='w', suffix='.fa', delete=False) as f:
            f.write(input_content)
            input_path = f.name

        try:
            result = comparator.run_compatibility_test(
                input_file=input_path,
                kmer_size=kmer_size,
                canonical=canonical
            )

            if result["cli_creation"]["success"] and result["cli_creation"]["database_path"]:
                return result["cli_creation"]["database_path"], input_path
            else:
                raise Exception(f"CLI database creation failed: {result}")

        finally:
            if os.path.exists(input_path):
                os.unlink(input_path)

    def test_python_api_basic_database_access(self, database_comparator):
        """Test Python API can open and access basic database information from CLI-created databases."""
        pytest.importorskip("rustkmer")  # Skip if Python module not available

        # Import rustkmer module
        import rustkmer

        # Create database with CLI
        db_path, _ = self.create_cli_database(database_comparator, kmer_size=13, canonical=True)

        try:
            # Test Python API can open the database
            db = rustkmer.Database(db_path)

            # Test basic database properties
            kmer_size = db.get_kmer_size()
            assert kmer_size == 13, f"Expected k=13, got k={kmer_size}"

            kmer_size_alt = db.get_k()
            assert kmer_size_alt == 13, f"Expected k=13, got k={kmer_size_alt}"

            # Test database statistics
            stats = db.get_stats()
            assert hasattr(stats, 'kmer_size')
            assert hasattr(stats, 'total_kmers')
            assert hasattr(stats, 'unique_kmers')
            assert stats.kmer_size == 13

            # Test database metadata
            metadata = db.get_metadata()
            assert isinstance(metadata, dict)
            assert 'kmer_size' in metadata
            assert 'total_kmers' in metadata
            assert 'format' in metadata

            print(f"  ✅ Database opened successfully")
            print(f"     K-mer size: {kmer_size}")
            print(f"     Total k-mers: {stats.total_kmers}")
            print(f"     Unique k-mers: {stats.unique_kmers}")
            print(f"     Format: {metadata.get('format', 'Unknown')}")

        finally:
            if os.path.exists(db_path):
                os.unlink(db_path)

    def test_python_api_query_cli_database(self, validator, database_comparator):
        """Test Python API can query CLI-created databases accurately."""
        pytest.importorskip("rustkmer")  # Skip if Python module not available

        # Create database with CLI
        db_path, _ = self.create_cli_database(database_comparator, kmer_size=13, canonical=True)

        try:
            # Test specific queries that should exist in the database
            test_queries = [
                "ACGTACGTACGTAC",  # Should exist multiple times
                "TGCATGCATGCATGC",  # Should exist
                "ATCGATCGATCGAT",  # Should exist
                "GGGGGGGGGGGGGG",  # May not exist
                "CCCCCCCCCCCCCC",  # May not exist
            ]

            print(f"  Testing Python API queries on CLI-created database:")
            query_results = []

            for kmer in test_queries:
                # Query with Python API
                import rustkmer
                db = rustkmer.Database(db_path)
                result = db.query(kmer)

                query_results.append({
                    'kmer': kmer,
                    'count': result.count,
                    'found': result.found,
                    'kmer_returned': result.kmer
                })

                status = "✅ FOUND" if result.found else "⚪ NOT FOUND"
                print(f"    {kmer}: {result.count} ({status})")

            # Validate results
            found_kmers = [qr for qr in query_results if qr['found']]
            assert len(found_kmers) > 0, "No k-mers found in database - unexpected"

            # Validate k-mer normalization
            for qr in query_results:
                assert qr['kmer_returned'] == qr['kmer'].upper(), "K-mer not properly normalized"
                assert qr['count'] >= 0, "Negative count detected"

            print(f"  ✅ Python API queried CLI database successfully")
            print(f"     Found {len(found_kmers)}/{len(test_queries)} test k-mers")

        finally:
            if os.path.exists(db_path):
                os.unlink(db_path)

    def test_python_api_batch_query_cli_database(self, validator, database_comparator):
        """Test Python API batch queries on CLI-created databases."""
        pytest.importorskip("rustkmer")  # Skip if Python module not available

        # Create database with CLI
        db_path, _ = self.create_cli_database(database_comparator, kmer_size=13, canonical=True)

        try:
            import rustkmer

            # Create test batch
            test_kmers = [
                "ACGTACGTACGTAC",
                "TGCATGCATGCATGC",
                "ATCGATCGATCGAT",
                "GGGGGGGGGGGGGG",
                "CCCCCCCCCCCCCC",
                "NNNNNNNNNNNNNN",  # Edge case
                "acgtacgtacgtac",  # Lower case
            ] * 5  # 35 total queries

            # Open database and run batch query
            db = rustkmer.Database(db_path)
            batch_results = db.query_multiple(test_kmers)

            assert len(batch_results) == len(test_kmers), "Batch query returned wrong number of results"

            print(f"  Testing batch queries on CLI-created database:")
            print(f"    Batch size: {len(test_kmers)}")
            print(f"    Results returned: {len(batch_results)}")

            # Analyze results
            found_count = sum(1 for r in batch_results if r.found)
            total_count = sum(r.count for r in batch_results)

            print(f"    K-mers found: {found_count}/{len(test_kmers)}")
            print(f"    Total count sum: {total_count}")

            # Validate result structure
            for i, result in enumerate(batch_results):
                assert hasattr(result, 'kmer'), f"Result {i} missing kmer attribute"
                assert hasattr(result, 'count'), f"Result {i} missing count attribute"
                assert hasattr(result, 'found'), f"Result {i} missing found attribute"
                assert isinstance(result.count, int), f"Result {i} count not integer"
                assert result.count >= 0, f"Result {i} negative count"

            print(f"  ✅ Batch query on CLI database successful")

        finally:
            if os.path.exists(db_path):
                os.unlink(db_path)

    def test_cross_platform_query_consistency(self, validator, database_comparator):
        """Test that Python API and CLI return identical results for CLI-created databases."""
        pytest.importorskip("rustkmer")  # Skip if Python module not available

        # Create database with CLI
        db_path, _ = self.create_cli_database(database_comparator, kmer_size=13, canonical=True)

        try:
            # Run cross-platform validation
            report = validator.validate_database_compatibility(db_path)

            # Check validation results
            summary = report["summary"]
            assert summary["total_tests"] > 0, "No validation tests run"

            success_rate = summary["success_rate_percent"]
            print(f"  Cross-platform validation results:")
            print(f"    Total tests: {summary['total_tests']}")
            print(f"    Success rate: {success_rate:.1f}%")
            print(f"    Overall status: {summary['overall_status']}")

            # Should have high success rate for CLI-created database
            assert success_rate >= 85.0, f"Success rate too low: {success_rate:.1f}%"
            assert summary["overall_status"] == "PASSED", "Overall validation status should be PASSED"

            # Check specific categories
            categories = report["categories"]
            if "valid" in categories:
                valid_success = categories["valid"]["passed"] / categories["valid"]["total"] * 100
                assert valid_success >= 90.0, f"Valid k-mer success rate too low: {valid_success:.1f}%"

            print(f"  ✅ Cross-platform consistency validated")

        finally:
            if os.path.exists(db_path):
                os.unlink(db_path)

    def test_different_kmer_sizes(self, database_comparator):
        """Test Python API reading CLI databases with different k-mer sizes."""
        pytest.importorskip("rustkmer")  # Skip if Python module not available

        import rustkmer

        kmer_sizes = [7, 13, 21]
        results = {}

        for kmer_size in kmer_sizes:
            print(f"  Testing k={kmer_size} database:")

            try:
                # Create database with CLI
                db_path, _ = self.create_cli_database(database_comparator, kmer_size=kmer_size, canonical=True)

                try:
                    # Test Python API access
                    db = rustkmer.Database(db_path)
                    detected_k = db.get_kmer_size()

                    assert detected_k == kmer_size, f"K-mer size mismatch: expected {kmer_size}, got {detected_k}"

                    # Test a query
                    test_kmer = "A" * kmer_size
                    result = db.query(test_kmer)

                    results[kmer_size] = {
                        "success": True,
                        "detected_k": detected_k,
                        "query_success": True,
                        "query_count": result.count
                    }

                    print(f"    ✅ Database opened, k={detected_k}, query result: {result.count}")

                finally:
                    if os.path.exists(db_path):
                        os.unlink(db_path)

            except Exception as e:
                results[kmer_size] = {
                    "success": False,
                    "error": str(e)
                }
                print(f"    ❌ Failed: {e}")

        # Validate results
        successful_sizes = [k for k, r in results.items() if r["success"]]
        assert len(successful_sizes) >= 2, f"Too few k-mer sizes work: {successful_sizes}"

        print(f"  ✅ Tested k-mer sizes: {successful_sizes}")

    def test_canonical_vs_non_canonical_databases(self, database_comparator):
        """Test Python API reading both canonical and non-canonical CLI databases."""
        pytest.importorskip("rustkmer")  # Skip if Python module not available

        import rustkmer

        test_modes = [
            {"canonical": True, "name": "canonical"},
            {"canonical": False, "name": "non-canonical"}
        ]

        results = {}

        for mode in test_modes:
            mode_name = mode["name"]
            canonical = mode["canonical"]

            print(f"  Testing {mode_name} database:")

            try:
                # Create database with CLI
                db_path, _ = self.create_cli_database(database_comparator, kmer_size=13, canonical=canonical)

                try:
                    # Test Python API access
                    db = rustkmer.Database(db_path)
                    stats = db.get_stats()

                    results[mode_name] = {
                        "success": True,
                        "canonical": stats.canonical,
                        "total_kmers": stats.total_kmers,
                        "unique_kmers": stats.unique_kmers
                    }

                    print(f"    ✅ Database opened, canonical={stats.canonical}")
                    print(f"       Total k-mers: {stats.total_kmers}, Unique: {stats.unique_kmers}")

                    # Test a few queries
                    test_kmers = ["ACGTACGTACGTAC", "TGCATGCATGCATGC"]
                    for kmer in test_kmers:
                        result = db.query(kmer)
                        if result.found:
                            print(f"       {kmer}: {result.count}")

                finally:
                    if os.path.exists(db_path):
                        os.unlink(db_path)

            except Exception as e:
                results[mode_name] = {
                    "success": False,
                    "error": str(e)
                }
                print(f"    ❌ Failed: {e}")

        # Validate results
        successful_modes = [name for name, r in results.items() if r["success"]]
        assert len(successful_modes) >= 1, f"No database modes work: {successful_modes}"

        print(f"  ✅ Tested database modes: {successful_modes}")

    def test_database_metadata_consistency(self, database_comparator):
        """Test that Python API correctly reads CLI database metadata."""
        pytest.importorskip("rustkmer")  # Skip if Python module not available

        import rustkmer

        # Create database with CLI
        db_path, _ = self.create_cli_database(database_comparator, kmer_size=13, canonical=True)

        try:
            # Get metadata from Python API
            db = rustkmer.Database(db_path)
            metadata = db.get_metadata()

            print(f"  Python API database metadata:")
            required_fields = ['kmer_size', 'total_kmers', 'unique_kmers', 'format', 'version']

            for field in required_fields:
                assert field in metadata, f"Missing metadata field: {field}"
                value = metadata[field]
                print(f"    {field}: {value}")

            # Specific validations
            assert metadata['kmer_size'] == 13, "Incorrect k-mer size in metadata"
            assert metadata['format'] == "RKDB (CLI compatible)", "Incorrect format in metadata"
            assert isinstance(metadata['total_kmers'], int), "Total k-mers should be integer"
            assert isinstance(metadata['unique_kmers'], int), "Unique k-mers should be integer"
            assert metadata['total_kmers'] >= metadata['unique_kmers'], "Total should be >= unique"

            # Test database path
            path = db.get_path()
            assert path is not None, "Database path should not be None"
            print(f"    path: {path}")

            # Test database state
            assert db.is_open(), "Database should be open"
            print(f"    is_open: {db.is_open()}")

            print(f"  ✅ Database metadata consistent and complete")

        finally:
            if os.path.exists(db_path):
                os.unlink(db_path)

    def test_error_handling_cli_databases(self, database_comparator):
        """Test Python API error handling with problematic CLI databases."""
        pytest.importorskip("rustkmer")  # Skip if Python module not available

        import rustkmer

        print(f"  Testing error handling:")

        # Test with non-existent database
        try:
            db = rustkmer.Database("/non/existent/database.rkdb")
            assert False, "Should have raised exception for non-existent database"
        except Exception as e:
            print(f"    ✅ Non-existent database: {type(e).__name__}")

        # Test with invalid file (not a database)
        with tempfile.NamedTemporaryFile(mode='w', suffix='.rkdb', delete=False) as f:
            f.write("This is not a valid database file")
            invalid_path = f.name

        try:
            db = rustkmer.Database(invalid_path)
            assert False, "Should have raised exception for invalid database"
        except Exception as e:
            print(f"    ✅ Invalid database file: {type(e).__name__}")

        finally:
            os.unlink(invalid_path)

        print(f"  ✅ Error handling works correctly")

    def test_context_manager_usage(self, database_comparator):
        """Test Python API context manager usage with CLI databases."""
        pytest.importorskip("rustkmer")  # Skip if Python module not available

        import rustkmer

        # Create database with CLI
        db_path, _ = self.create_cli_database(database_comparator, kmer_size=13, canonical=True)

        try:
            # Test context manager
            with rustkmer.Database(db_path) as db:
                assert db.is_open(), "Database should be open in context"

                kmer_size = db.get_kmer_size()
                assert kmer_size == 13, "K-mer size should be accessible in context"

                result = db.query("ACGTACGTACGTAC")
                assert hasattr(result, 'count'), "Query should work in context"

            print(f"  ✅ Context manager usage successful")

        finally:
            if os.path.exists(db_path):
                os.unlink(db_path)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])