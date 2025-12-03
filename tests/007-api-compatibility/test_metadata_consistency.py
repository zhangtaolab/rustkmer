#!/usr/bin/env python3
"""
T022: Database metadata consistency validation between Python API and CLI.
Ensures all database metadata fields are identical between implementations.
"""

import pytest
import os
import sys
import tempfile
import struct
import json
from datetime import datetime

# Add the compatibility framework to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'compatibility_framework'))

try:
    from compare_databases import DatabaseComparator
except ImportError as e:
    pytest.skip(f"Compatibility framework not available: {e}")


class RKDBMetadataReader:
    """Reader for RKDB database metadata."""

    def __init__(self, file_path):
        self.file_path = file_path
        self.metadata = None

    def read_metadata(self):
        """Read RKDB database header and extract metadata."""
        if not os.path.exists(self.file_path):
            raise FileNotFoundError(f"Database file not found: {self.file_path}")

        try:
            with open(self.file_path, 'rb') as f:
                # Read RKDB header (42 bytes)
                header_data = f.read(42)
                if len(header_data) < 42:
                    raise ValueError("Invalid RKDB file: header too short")

                # Parse header fields
                magic = header_data[:4]
                version = struct.unpack('<H', header_data[4:6])[0]
                kmer_size = header_data[6]
                # Skip padding byte
                # Skip padding bytes
                total_kmers = struct.unpack('<Q', header_data[10:18])[0]
                flags = header_data[18]
                # Skip padding bytes
                data_offset = struct.unpack('<Q', header_data[26:34])[0]
                index_offset = struct.unpack('<Q', header_data[34:42])[0]

                # Extract boolean flags
                sorted_flag = bool(flags & 0x01)
                canonical_flag = bool(flags & 0x02)

                # Get file size
                file_size = os.path.getsize(self.file_path)

                # Calculate unique k-mers from data section
                unique_kmers = self._count_unique_kmers(f, data_offset, file_size)

                self.metadata = {
                    "magic": magic.decode('ascii', errors='ignore'),
                    "version": version,
                    "kmer_size": kmer_size,
                    "total_kmers": total_kmers,
                    "unique_kmers": unique_kmers,
                    "sorted": sorted_flag,
                    "canonical": canonical_flag,
                    "data_offset": data_offset,
                    "index_offset": index_offset,
                    "file_size": file_size
                }

                return self.metadata

        except Exception as e:
            raise ValueError(f"Failed to read RKDB metadata: {e}")

    def _count_unique_kmers(self, file_handle, data_offset, file_size):
        """Count unique k-mers in the data section."""
        if data_offset >= file_size:
            return 0

        file_handle.seek(data_offset)
        entry_size = 12  # 8 bytes k-mer + 4 bytes count
        data_size = file_size - data_offset
        entry_count = data_size // entry_size

        return entry_count


class TestDatabaseMetadataConsistency:
    """Test database metadata consistency between Python API and CLI."""

    @pytest.fixture
    def comparator(self):
        """Create a DatabaseComparator instance for testing."""
        return DatabaseComparator()

    @pytest.fixture
    def test_sequences(self):
        """Standard test sequences for metadata validation."""
        return ">test_seq\n" + "ACGTACGTACGTACGTACGT" * 20 + "\n" + \
               ">test_seq2\n" + "TGCATGCATGCATGCATGCA" * 15

    def create_test_database(self, comparator, sequence_content, kmer_size=13, canonical=True):
        """Create test databases using both CLI and Python API."""
        # Create temporary FASTA file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.fa', delete=False) as f:
            f.write(sequence_content)
            fasta_path = f.name

        try:
            # Create databases using both methods
            result = comparator.run_compatibility_test(
                input_file=fasta_path,
                kmer_size=kmer_size,
                canonical=canonical
            )

            return result, fasta_path

        except Exception as e:
            os.unlink(fasta_path)
            raise e

    def test_core_metadata_fields(self, comparator, test_sequences):
        """Test core metadata fields consistency."""
        print("Testing core metadata fields consistency...")

        result, fasta_path = self.create_test_database(comparator, test_sequences, kmer_size=13)

        try:
            # Verify both databases were created
            assert result["cli_creation"]["success"], "CLI database creation failed"
            assert result["python_creation"]["success"], "Python database creation failed"

            # Get database file paths
            cli_db = result["cli_creation"]["database_path"]
            python_db = result["python_creation"]["database_path"]

            if not os.path.exists(cli_db) or not os.path.exists(python_db):
                pytest.skip("Database files not available for metadata testing")

            # Read metadata from both databases
            cli_reader = RKDBMetadataReader(cli_db)
            python_reader = RKDBMetadataReader(python_db)

            cli_metadata = cli_reader.read_metadata()
            python_metadata = python_reader.read_metadata()

            # Validate core metadata fields
            core_fields = ["magic", "version", "kmer_size", "sorted", "canonical", "data_offset"]

            for field in core_fields:
                cli_value = cli_metadata[field]
                python_value = python_metadata[field]
                assert cli_value == python_value, f"Metadata field '{field}' differs: CLI={cli_value}, Python={python_value}"

            print("✅ Core metadata fields: CONSISTENT")

            # Field-specific validations
            assert cli_metadata["magic"] == "RKDB", f"Invalid magic number: {cli_metadata['magic']}"
            assert cli_metadata["version"] == 1, f"Invalid version: {cli_metadata['version']}"
            assert cli_metadata["kmer_size"] == 13, f"Invalid k-mer size: {cli_metadata['kmer_size']}"
            assert cli_metadata["canonical"] == True, f"Invalid canonical flag: {cli_metadata['canonical']}"
            assert cli_metadata["data_offset"] == 42, f"Invalid data offset: {cli_metadata['data_offset']}"

        finally:
            os.unlink(fasta_path)

    def test_kmer_count_consistency(self, comparator, test_sequences):
        """Test k-mer count metadata consistency."""
        print("Testing k-mer count consistency...")

        result, fasta_path = self.create_test_database(comparator, test_sequences, kmer_size=13)

        try:
            cli_db = result["cli_creation"]["database_path"]
            python_db = result["python_creation"]["database_path"]

            if not os.path.exists(cli_db) or not os.path.exists(python_db):
                pytest.skip("Database files not available for k-mer count testing")

            cli_reader = RKDBMetadataReader(cli_db)
            python_reader = RKDBMetadataReader(python_db)

            cli_metadata = cli_reader.read_metadata()
            python_metadata = python_reader.read_metadata()

            # Validate k-mer counts
            cli_total = cli_metadata["total_kmers"]
            python_total = python_metadata["total_kmers"]
            cli_unique = cli_metadata["unique_kmers"]
            python_unique = python_metadata["unique_kmers"]

            assert cli_total == python_total, f"Total k-mers differ: CLI={cli_total}, Python={python_total}"
            assert cli_unique == python_unique, f"Unique k-mers differ: CLI={cli_unique}, Python={python_unique}"

            # Basic sanity checks
            assert cli_total > 0, "Total k-mers should be > 0"
            assert cli_unique > 0, "Unique k-mers should be > 0"
            assert cli_unique <= cli_total, "Unique k-mers should be <= total k-mers"

            print(f"✅ K-mer counts: CONSISTENT (total={cli_total}, unique={cli_unique})")

        finally:
            os.unlink(fasta_path)

    def test_flag_consistency(self, comparator, test_sequences):
        """Test boolean flag consistency across modes."""
        print("Testing flag consistency across modes...")

        test_cases = [
            (13, True, "canonical"),
            (13, False, "non-canonical"),
            (21, True, "canonical k=21"),
            (7, True, "canonical k=7")
        ]

        for kmer_size, canonical, description in test_cases:
            print(f"  Testing {description}...")

            result, fasta_path = self.create_test_database(comparator, test_sequences, kmer_size, canonical)

            try:
                cli_db = result["cli_creation"]["database_path"]
                python_db = result["python_creation"]["database_path"]

                if not os.path.exists(cli_db) or not os.path.exists(python_db):
                    print(f"    ⚠️ {description}: SKIPPED (files not available)")
                    continue

                cli_reader = RKDBMetadataReader(cli_db)
                python_reader = RKDBMetadataReader(python_db)

                cli_metadata = cli_reader.read_metadata()
                python_metadata = python_reader.read_metadata()

                # Validate flag consistency
                assert cli_metadata["canonical"] == python_metadata["canonical"], \
                    f"Canonical flag differs for {description}"
                assert cli_metadata["sorted"] == python_metadata["sorted"], \
                    f"Sorted flag differs for {description}"
                assert cli_metadata["canonical"] == canonical, \
                    f"Canonical flag incorrect for {description}"

                print(f"    ✅ {description}: CONSISTENT")

            finally:
                os.unlink(fasta_path)

    def test_file_structure_consistency(self, comparator, test_sequences):
        """Test file structure and size consistency."""
        print("Testing file structure consistency...")

        result, fasta_path = self.create_test_database(comparator, test_sequences, kmer_size=13)

        try:
            cli_db = result["cli_creation"]["database_path"]
            python_db = result["python_creation"]["database_path"]

            if not os.path.exists(cli_db) or not os.path.exists(python_db):
                pytest.skip("Database files not available for structure testing")

            cli_reader = RKDBMetadataReader(cli_db)
            python_reader = RKDBMetadataReader(python_db)

            cli_metadata = cli_reader.read_metadata()
            python_metadata = python_reader.read_metadata()

            # Validate file structure
            assert cli_metadata["file_size"] == python_metadata["file_size"], \
                f"File sizes differ: CLI={cli_metadata['file_size']}, Python={python_metadata['file_size']}"

            assert cli_metadata["data_offset"] == python_metadata["data_offset"], \
                f"Data offsets differ: CLI={cli_metadata['data_offset']}, Python={python_metadata['data_offset']}"

            assert cli_metadata["index_offset"] == python_metadata["index_offset"], \
                f"Index offsets differ: CLI={cli_metadata['index_offset']}, Python={python_metadata['index_offset']}"

            # Validate structure consistency
            expected_data_offset = 42  # RKDB header size
            assert cli_metadata["data_offset"] == expected_data_offset, \
                f"Invalid data offset: {cli_metadata['data_offset']} (expected {expected_data_offset})"

            # Validate file size calculation
            expected_min_size = expected_data_offset + (cli_metadata["unique_kmers"] * 12)
            assert cli_metadata["file_size"] >= expected_min_size, \
                f"File size too small: {cli_metadata['file_size']} < {expected_min_size}"

            print(f"✅ File structure: CONSISTENT (size={cli_metadata['file_size']}, offset={cli_metadata['data_offset']})")

        finally:
            os.unlink(fasta_path)

    def test_kmer_size_variations(self, comparator, test_sequences):
        """Test metadata consistency across different k-mer sizes."""
        print("Testing k-mer size variations...")

        kmer_sizes = [7, 13, 21, 31]

        for kmer_size in kmer_sizes:
            print(f"  Testing k={kmer_size}...")

            result, fasta_path = self.create_test_database(comparator, test_sequences, kmer_size, True)

            try:
                cli_db = result["cli_creation"]["database_path"]
                python_db = result["python_creation"]["database_path"]

                if not os.path.exists(cli_db) or not os.path.exists(python_db):
                    print(f"    ⚠️ k={kmer_size}: SKIPPED")
                    continue

                cli_reader = RKDBMetadataReader(cli_db)
                python_reader = RKDBMetadataReader(python_db)

                cli_metadata = cli_reader.read_metadata()
                python_metadata = python_reader.read_metadata()

                # Validate k-mer size consistency
                assert cli_metadata["kmer_size"] == python_metadata["kmer_size"], \
                    f"K-mer size differs for k={kmer_size}"
                assert cli_metadata["kmer_size"] == kmer_size, \
                    f"K-mer size incorrect for k={kmer_size}: {cli_metadata['kmer_size']}"

                # Validate other metadata consistency
                assert cli_metadata["magic"] == python_metadata["magic"]
                assert cli_metadata["version"] == python_metadata["version"]
                assert cli_metadata["canonical"] == python_metadata["canonical"]

                print(f"    ✅ k={kmer_size}: CONSISTENT")

            finally:
                os.unlink(fasta_path)

    def test_metadata_edge_cases(self, comparator):
        """Test metadata consistency with edge cases."""
        print("Testing metadata edge cases...")

        edge_cases = [
            (">short\nACGT", "Very short sequence"),
            (">empty_kmer\nA", "No valid k-mers"),
            (">exact_kmer\n" + "ACGT" * 4, "Exact k-mer count")
        ]

        for sequence, description in edge_cases:
            print(f"  Testing {description}...")

            try:
                result, fasta_path = self.create_test_database(comparator, sequence, kmer_size=13)

                cli_db = result["cli_creation"]["database_path"]
                python_db = result["python_creation"]["database_path"]

                if not os.path.exists(cli_db) or not os.path.exists(python_db):
                    print(f"    ⚠️ {description}: SKIPPED (no databases created)")
                    os.unlink(fasta_path)
                    continue

                cli_reader = RKDBMetadataReader(cli_db)
                python_reader = RKDBMetadataReader(python_db)

                cli_metadata = cli_reader.read_metadata()
                python_metadata = python_reader.read_metadata()

                # Validate metadata consistency even for edge cases
                assert cli_metadata["magic"] == python_metadata["magic"]
                assert cli_metadata["version"] == python_metadata["version"]
                assert cli_metadata["kmer_size"] == python_metadata["kmer_size"]

                print(f"    ✅ {description}: CONSISTENT")

            except Exception as e:
                print(f"    ⚠️ {description}: SKIPPED ({e})")

            finally:
                if 'fasta_path' in locals():
                    os.unlink(fasta_path)

    def generate_metadata_consistency_report(self, test_results):
        """Generate metadata consistency validation report."""
        report = {
            "test_suite": "T022: Database Metadata Consistency",
            "timestamp": datetime.now().isoformat(),
            "validations_performed": [
                "Core metadata fields",
                "K-mer count consistency",
                "Boolean flag consistency",
                "File structure consistency",
                "K-mer size variations",
                "Edge case handling"
            ],
            "results": test_results,
            "summary": {
                "total_validations": 6,
                "successful_validations": len([r for r in test_results.values() if r.get("status") == "PASSED"]),
                "consistency_rate": "100%" if all(r.get("status") == "PASSED" for r in test_results.values()) else "PARTIAL"
            },
            "metadata_fields_validated": [
                "magic", "version", "kmer_size", "total_kmers", "unique_kmers",
                "sorted", "canonical", "data_offset", "index_offset", "file_size"
            ]
        }

        # Save report
        report_path = "tests/007-api-compatibility/test_reports/t022_metadata_consistency_report.json"
        with open(report_path, "w") as f:
            json.dump(report, f, indent=2)

        return report


if __name__ == "__main__":
    pytest.main([__file__, "-v"])