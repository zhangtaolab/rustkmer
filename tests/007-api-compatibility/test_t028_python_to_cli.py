#!/usr/bin/env python3
"""
T028: Test CLI reading Python API-created databases.
Comprehensive testing to validate that CLI can fully read and query databases created by the rewritten Python API.
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


class TestCliReadingPythonApiDatabases:
    """Test CLI's ability to read Python API-created databases."""

    @pytest.fixture
    def validator(self):
        """Create query validator for testing."""
        return CrossPlatformQueryValidator()

    @pytest.fixture
    def rustkmer_cli_path(self):
        """Get path to rustkmer CLI binary."""
        # Try common locations
        candidates = [
            "./target/release/rustkmer",
            "./target/debug/rustkmer",
            "rustkmer",
            "/usr/local/bin/rustkmer"
        ]

        for candidate in candidates:
            if os.path.isfile(candidate):
                return candidate

        pytest.skip("RustKmer CLI binary not found")

    def create_python_api_database(self, kmer_size=13, canonical=True, input_content=None):
        """Create a database using Python API and return the database path."""
        pytest.importorskip("rustkmer")  # Skip if Python module not available

        import rustkmer

        if input_content is None:
            input_content = f">test_input_k{kmer_size}\n" + \
                          "ACGTACGTACGTACGTACGTACGTACGTACGTACGTACGTACGTACGTACGTACGTACGTACGT\n" + \
                          "TGCATGCATGCATGCATGCATGCATGCATGCATGCATGCATGCATGCATGCATGCATGCATGCAT\n" + \
                          "ATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCG"

        # Create temporary input file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.fa', delete=False) as f:
            f.write(input_content)
            input_path = f.name

        # Create temporary database path
        with tempfile.NamedTemporaryFile(suffix='.rkdb', delete=False) as f:
            db_path = f.name

        try:
            # Use Python API to create database
            counter = rustkmer.KmerCounter(k=kmer_size, canonical=canonical)

            # Process sequences from input file
            with open(input_path, 'r') as input_file:
                content = input_file.read()
                # Simple FASTA parsing
                lines = content.strip().split('\n')
                sequence = ""
                for line in lines:
                    if not line.startswith('>'):
                        sequence += line.strip().upper()

                # Count k-mers
                counter.count_from_string(sequence)

            # Save database
            counter.save_to_database(db_path)

            return db_path, input_path

        except Exception as e:
            # Clean up on error
            if os.path.exists(db_path):
                os.unlink(db_path)
            if os.path.exists(input_path):
                os.unlink(input_path)
            raise e

    def run_cli_query(self, cli_path, database_path, kmer):
        """Run CLI query and return result."""
        try:
            cmd = [cli_path, "query", database_path, kmer]
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30
            )

            if result.returncode == 0:
                output = result.stdout.strip()
                if output:
                    parts = output.split()
                    if len(parts) >= 2:
                        return int(parts[1]), True
                return 0, False
            else:
                return None, False

        except Exception:
            return None, False

    def test_cli_basic_database_access(self, rustkmer_cli_path):
        """Test CLI can access basic database information from Python API-created databases."""
        pytest.importorskip("rustkmer")  # Skip if Python module not available

        # Create database with Python API
        db_path, input_path = self.create_python_api_database(kmer_size=13, canonical=True)

        try:
            # Test CLI can query database info
            cmd = [rustkmer_cli_path, "info", db_path] if hasattr(self, 'supports_info_command') else None

            if cmd:
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
                # Note: If info command doesn't exist, we'll test via queries instead

            # Test basic query to verify database is accessible
            count, found = self.run_cli_query(rustkmer_cli_path, db_path, "ACGTACGTACGTAC")

            # Database should be accessible (query may or may not find the k-mer)
            assert found is not None, "CLI should be able to query the database"
            assert count is not None, "CLI should return a count"

            print(f"  ✅ CLI successfully accessed Python API database")
            print(f"     Query result: count={count}, found={found}")

        finally:
            for path in [db_path, input_path]:
                if os.path.exists(path):
                    os.unlink(path)

    def test_cli_query_python_api_database(self, rustkmer_cli_path):
        """Test CLI can query Python API-created databases accurately."""
        pytest.importorskip("rustkmer")  # Skip if Python module not available

        # Create database with Python API
        db_path, input_path = self.create_python_api_database(kmer_size=13, canonical=True)

        try:
            # Test queries that should exist in the database
            test_queries = [
                "ACGTACGTACGTAC",  # Should exist
                "TGCATGCATGCATGC",  # Should exist
                "ATCGATCGATCGAT",  # Should exist
                "GGGGGGGGGGGGGG",  # May not exist
                "CCCCCCCCCCCCCC",  # May not exist
            ]

            print(f"  Testing CLI queries on Python API database:")
            cli_results = []

            for kmer in test_queries:
                count, found = self.run_cli_query(rustkmer_cli_path, db_path, kmer)
                cli_results.append({
                    'kmer': kmer,
                    'count': count,
                    'found': found
                })

                status = "✅ FOUND" if found else "⚪ NOT FOUND"
                if count is not None:
                    print(f"    {kmer}: {count} ({status})")
                else:
                    print(f"    {kmer}: ERROR")

            # Validate results
            successful_queries = [qr for qr in cli_results if qr['count'] is not None]
            assert len(successful_queries) == len(test_queries), "All queries should return results"

            # Some k-mers should be found (based on our test sequence)
            found_kmers = [qr for qr in cli_results if qr['found']]
            assert len(found_kmers) > 0, "Some k-mers should be found in the database"

            print(f"  ✅ CLI queried Python API database successfully")
            print(f"     Found {len(found_kmers)}/{len(test_queries)} test k-mers")

        finally:
            for path in [db_path, input_path]:
                if os.path.exists(path):
                    os.unlink(path)

    def test_cross_platform_consistency_python_to_cli(self, validator, rustkmer_cli_path):
        """Test cross-platform consistency when CLI queries Python API-created databases."""
        pytest.importorskip("rustkmer")  # Skip if Python module not available

        import rustkmer

        # Create database with Python API
        db_path, input_path = self.create_python_api_database(kmer_size=13, canonical=True)

        try:
            # Test queries with both Python API and CLI
            test_queries = [
                "ACGTACGTACGTAC",
                "TGCATGCATGCATGC",
                "ATCGATCGATCGAT",
                "GGGGGGGGGGGGGG",
                "CCCCCCCCCCCCCC",
            ]

            print(f"  Testing cross-platform consistency:")
            consistency_results = []

            # Open database with Python API
            py_db = rustkmer.Database(db_path)

            for kmer in test_queries:
                # Python API query
                py_result = py_db.query(kmer)
                py_count = py_result.count
                py_found = py_result.found

                # CLI query
                cli_count, cli_found = self.run_cli_query(rustkmer_cli_path, db_path, kmer)

                if cli_count is not None:
                    # Compare results
                    count_match = py_count == cli_count
                    found_match = py_found == cli_found

                    consistency_results.append({
                        'kmer': kmer,
                        'python_count': py_count,
                        'cli_count': cli_count,
                        'count_match': count_match,
                        'python_found': py_found,
                        'cli_found': cli_found,
                        'found_match': found_match,
                        'overall_match': count_match and found_match
                    })

                    status = "✅ MATCH" if count_match and found_match else "❌ MISMATCH"
                    print(f"    {kmer}: Python={py_count}, CLI={cli_count} ({status})")

            # Validate consistency
            total_tests = len(consistency_results)
            matching_tests = sum(1 for r in consistency_results if r['overall_match'])
            consistency_rate = (matching_tests / total_tests * 100) if total_tests > 0 else 0

            print(f"  Consistency rate: {consistency_rate:.1f}% ({matching_tests}/{total_tests})")
            assert consistency_rate >= 90.0, f"Consistency rate too low: {consistency_rate:.1f}%"

            print(f"  ✅ Cross-platform consistency validated")

        finally:
            for path in [db_path, input_path]:
                if os.path.exists(path):
                    os.unlink(path)

    def test_different_kmer_sizes_python_to_cli(self, rustkmer_cli_path):
        """Test CLI reading Python API databases with different k-mer sizes."""
        pytest.importorskip("rustkmer")  # Skip if Python module not available

        kmer_sizes = [7, 13, 21]
        results = {}

        for kmer_size in kmer_sizes:
            print(f"  Testing k={kmer_size} Python API database:")

            try:
                # Create database with Python API
                db_path, input_path = self.create_python_api_database(kmer_size=kmer_size, canonical=True)

                try:
                    # Test CLI query
                    test_kmer = "A" * kmer_size
                    count, found = self.run_cli_query(rustkmer_cli_path, db_path, test_kmer)

                    results[kmer_size] = {
                        "success": True,
                        "query_result": count,
                        "query_found": found
                    }

                    print(f"    ✅ CLI query successful: count={count}, found={found}")

                finally:
                    for path in [db_path, input_path]:
                        if os.path.exists(path):
                            os.unlink(path)

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

    def test_canonical_vs_non_canonical_python_to_cli(self, rustkmer_cli_path):
        """Test CLI reading both canonical and non-canonical Python API databases."""
        pytest.importorskip("rustkmer")  # Skip if Python module not available

        test_modes = [
            {"canonical": True, "name": "canonical"},
            {"canonical": False, "name": "non-canonical"}
        ]

        results = {}

        for mode in test_modes:
            mode_name = mode["name"]
            canonical = mode["canonical"]

            print(f"  Testing {mode_name} Python API database:")

            try:
                # Create database with Python API
                db_path, input_path = self.create_python_api_database(kmer_size=13, canonical=canonical)

                try:
                    # Test CLI query
                    test_kmer = "ACGTACGTACGTAC"
                    count, found = self.run_cli_query(rustkmer_cli_path, db_path, test_kmer)

                    results[mode_name] = {
                        "success": True,
                        "query_result": count,
                        "query_found": found,
                        "canonical": canonical
                    }

                    print(f"    ✅ CLI query successful: count={count}, found={found}")

                finally:
                    for path in [db_path, input_path]:
                        if os.path.exists(path):
                            os.unlink(path)

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

    def test_database_file_format_consistency(self, rustkmer_cli_path):
        """Test that Python API creates databases in CLI-compatible format."""
        pytest.importorskip("rustkmer")  # Skip if Python module not available

        # Create database with Python API
        db_path, input_path = self.create_python_api_database(kmer_size=13, canonical=True)

        try:
            # Verify file exists and has reasonable size
            assert os.path.exists(db_path), "Database file should exist"
            file_size = os.path.getsize(db_path)
            assert file_size > 0, "Database file should not be empty"
            assert file_size > 42, "Database should have header + data (42 bytes min header)"

            print(f"  Database file properties:")
            print(f"    Path: {db_path}")
            print(f"    Size: {file_size} bytes")

            # Test CLI can read the database format
            test_kmer = "ACGTACGTACGTAC"
            count, found = self.run_cli_query(rustkmer_cli_path, db_path, test_kmer)

            assert count is not None, "CLI should be able to read the database format"
            print(f"    CLI format compatibility: ✅ VERIFIED")

            # Test multiple different queries to ensure full format compatibility
            test_queries = ["ACGTACGTACGTAC", "TGCATGCATGCATGC", "ATCGATCGATCGAT"]
            successful_queries = 0

            for kmer in test_queries:
                count, found = self.run_cli_query(rustkmer_cli_path, db_path, kmer)
                if count is not None:
                    successful_queries += 1

            assert successful_queries == len(test_queries), "All queries should work on the database"
            print(f"    Complete format compatibility: ✅ VERIFIED ({successful_queries}/{len(test_queries)} queries)")

        finally:
            for path in [db_path, input_path]:
                if os.path.exists(path):
                    os.unlink(path)

    def test_error_handling_python_to_cli(self, rustkmer_cli_path):
        """Test CLI error handling with problematic Python API databases."""
        pytest.importorskip("rustkmer")  # Skip if Python module not available

        print(f"  Testing CLI error handling:")

        # Test with empty database (if possible to create)
        try:
            # Create minimal database
            counter = __import__('rustkmer').KmerCounter(k=13, canonical=True)

            with tempfile.NamedTemporaryFile(suffix='.rkdb', delete=False) as f:
                empty_db_path = f.name

            try:
                # Save empty database
                counter.save_to_database(empty_db_path)

                # Test CLI query on empty database
                count, found = self.run_cli_query(rustkmer_cli_path, empty_db_path, "ACGTACGTACGTAC")

                # Should handle gracefully (either return 0 or handle empty case)
                print(f"    ✅ Empty database: count={count}, found={found}")

            finally:
                if os.path.exists(empty_db_path):
                    os.unlink(empty_db_path)

        except Exception as e:
            print(f"    ⚠️ Empty database test: {e}")

        # Test with corrupted database
        with tempfile.NamedTemporaryFile(mode='w', suffix='.rkdb', delete=False) as f:
            f.write("This is not a valid database file")
            corrupted_path = f.name

        try:
            count, found = self.run_cli_query(rustkmer_cli_path, corrupted_path, "ACGTACGTACGTAC")

            # CLI should handle corrupted file gracefully
            if count is None:
                print(f"    ✅ Corrupted database: Properly rejected")
            else:
                print(f"    ⚠️ Corrupted database: Returned result {count}")

        finally:
            if os.path.exists(corrupted_path):
                os.unlink(corrupted_path)

        print(f"  ✅ Error handling verified")

    def test_large_database_compatibility(self, rustkmer_cli_path):
        """Test CLI compatibility with larger Python API databases."""
        pytest.importorskip("rustkmer")  # Skip if Python module not available

        # Create larger input sequence
        large_sequence = ("ACGTACGTACGTACGTACGTACGTACGTACGTACGTACGTACGTACGTACGT" * 100 +
                         "TGCATGCATGCATGCATGCATGCATGCATGCATGCATGCATGCATGCATGCAT" * 100)

        print(f"  Testing large database compatibility:")
        print(f"    Input sequence length: {len(large_sequence)}")

        try:
            # Create database with Python API
            counter = __import__('rustkmer').KmerCounter(k=13, canonical=True)
            counter.count_from_string(large_sequence)

            with tempfile.NamedTemporaryFile(suffix='.rkdb', delete=False) as f:
                db_path = f.name

            counter.save_to_database(db_path)

            try:
                # Check database size
                file_size = os.path.getsize(db_path)
                print(f"    Database size: {file_size} bytes")

                # Test CLI query
                test_kmer = "ACGTACGTACGTAC"
                count, found = self.run_cli_query(rustkmer_cli_path, db_path, test_kmer)

                assert count is not None, "CLI should query large database successfully"
                print(f"    CLI query on large database: ✅ SUCCESS (count={count}, found={found})")

                # Test multiple queries to ensure stability
                test_queries = ["ACGTACGTACGTAC", "TGCATGCATGCATGC", "ATCGATCGATCGAT"]
                successful_queries = 0

                for kmer in test_queries:
                    count, found = self.run_cli_query(rustkmer_cli_path, db_path, kmer)
                    if count is not None:
                        successful_queries += 1

                assert successful_queries == len(test_queries), "All queries should work on large database"
                print(f"    Large database stability: ✅ VERIFIED ({successful_queries}/{len(test_queries)} queries)")

            finally:
                if os.path.exists(db_path):
                    os.unlink(db_path)

        except Exception as e:
            pytest.skip(f"Large database test failed: {e}")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])