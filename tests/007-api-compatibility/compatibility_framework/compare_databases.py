#!/usr/bin/env python3
"""
Database comparison utilities for CLI vs Python API compatibility testing.
"""

import os
import subprocess
import hashlib
import shutil
from pathlib import Path
from typing import Tuple, Dict, Any
import tempfile
import time

class DatabaseComparator:
    """Compare databases created by CLI and Python API."""

    def __init__(self, cli_path: str = "rustkmer"):
        self.cli_path = cli_path
        self.test_results = []

    def create_database_cli(
        self,
        input_file: str,
        output_path: str,
        kmer_size: int = 21,
        canonical: bool = True
    ) -> Tuple[bool, str]:
        """Create database using Rust CLI."""
        cmd = [
            self.cli_path, "count",
            "-k", str(kmer_size),
            "-i", input_file,
            "-o", output_path,
            "--quiet"  # Suppress progress output
        ]

        # Add canonical flag if requested
        if canonical:
            cmd.append("--canonical")

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=True,
                timeout=300  # 5 minute timeout
            )
            return True, result.stdout
        except subprocess.CalledProcessError as e:
            return False, f"CLI Error: {e.stderr}"
        except subprocess.TimeoutExpired:
            return False, "CLI Error: Timeout exceeded"

    def create_database_python(
        self,
        input_file: str,
        output_path: str,
        kmer_size: int = 21,
        canonical: bool = True
    ) -> Tuple[bool, str]:
        """Create database using Python API."""
        try:
            # Import rustkmer Python API
            import rustkmer
            from rustkmer import KmerCounter

            # Create k-mer counter
            counter = KmerCounter(k=kmer_size, canonical=canonical)

            # Process input file
            if input_file.endswith(('.fasta', '.fa')):
                counter.process_fasta(input_file)
            elif input_file.endswith(('.fastq', '.fq')):
                counter.process_fastq(input_file)
            else:
                return False, f"Unsupported file format: {input_file}"

            # Save to database
            counter.save_to_database(output_path)
            return True, "Python API: Database created successfully"

        except ImportError as e:
            return False, f"Python API Error: Module not found - {e}"
        except Exception as e:
            return False, f"Python API Error: {e}"

    def compare_files_bitwise(self, file1: str, file2: str) -> Dict[str, Any]:
        """Perform bit-for-bit comparison of two database files."""
        try:
            # Check file sizes
            size1 = os.path.getsize(file1)
            size2 = os.path.getsize(file2)

            if size1 != size2:
                return {
                    "identical": False,
                    "reason": f"File size mismatch: {size1} vs {size2} bytes",
                    "size_diff": abs(size1 - size2)
                }

            # Calculate file hashes
            def file_hash(filepath):
                hasher = hashlib.sha256()
                with open(filepath, 'rb') as f:
                    for chunk in iter(lambda: f.read(4096), b""):
                        hasher.update(chunk)
                return hasher.hexdigest()

            hash1 = file_hash(file1)
            hash2 = file_hash(file2)

            if hash1 != hash2:
                return {
                    "identical": False,
                    "reason": f"Hash mismatch: {hash1[:16]}... vs {hash2[:16]}...",
                    "file1_hash": hash1,
                    "file2_hash": hash2
                }

            return {"identical": True, "hash": hash1}

        except Exception as e:
            return {
                "identical": False,
                "reason": f"Comparison error: {e}",
                "error": str(e)
            }

    def run_compatibility_test(
        self,
        input_file: str,
        kmer_size: int = 21,
        canonical: bool = True
    ) -> Dict[str, Any]:
        """Run complete compatibility test between CLI and Python API."""
        test_start = time.time()

        # Create temporary directory for test
        with tempfile.TemporaryDirectory() as temp_dir:
            cli_db = os.path.join(temp_dir, "cli_database.rkdb")
            python_db = os.path.join(temp_dir, "python_database.rkdb")

            results = {
                "input_file": input_file,
                "kmer_size": kmer_size,
                "canonical": canonical,
                "test_start": test_start,
                "cli_creation": None,
                "python_creation": None,
                "comparison": None,
                "test_duration": None
            }

            # Create database with CLI
            cli_start = time.time()
            cli_success, cli_msg = self.create_database_cli(
                input_file, cli_db, kmer_size, canonical
            )
            cli_end = time.time()
            results["cli_creation"] = {
                "success": cli_success,
                "message": cli_msg,
                "duration": cli_end - cli_start
            }

            # Create database with Python API
            python_start = time.time()
            python_success, python_msg = self.create_database_python(
                input_file, python_db, kmer_size, canonical
            )
            python_end = time.time()
            results["python_creation"] = {
                "success": python_success,
                "message": python_msg,
                "duration": python_end - python_start
            }

            # Compare results
            if cli_success and python_success and os.path.exists(cli_db) and os.path.exists(python_db):
                results["comparison"] = self.compare_files_bitwise(cli_db, python_db)

                # Save test databases for manual inspection if needed
                os.makedirs("test_databases", exist_ok=True)
                test_name = Path(input_file).stem + f"_k{kmer_size}"
                shutil.copy2(cli_db, f"test_databases/{test_name}_cli.rkdb")
                shutil.copy2(python_db, f"test_databases/{test_name}_python.rkdb")
            else:
                results["comparison"] = {
                    "identical": False,
                    "reason": "One or both database creation failed"
                }

            results["test_duration"] = time.time() - test_start
            results["test_end"] = time.time()

        self.test_results.append(results)
        return results

    def get_test_summary(self) -> Dict[str, Any]:
        """Get summary of all completed tests."""
        if not self.test_results:
            return {"total_tests": 0, "passed": 0, "failed": 0}

        total = len(self.test_results)
        passed = sum(1 for result in self.test_results
                   if result.get("comparison", {}).get("identical", False))
        failed = total - passed

        return {
            "total_tests": total,
            "passed": passed,
            "failed": failed,
            "pass_rate": (passed / total) * 100 if total > 0 else 0
        }


# Example usage
if __name__ == "__main__":
    comparator = DatabaseComparator()

    # Example test with a sample file (if available)
    sample_files = [
        "test_data/small/sample.fasta",
        "test_data/small/sample.fastq"
    ]

    for sample_file in sample_files:
        if os.path.exists(sample_file):
            print(f"Testing with {sample_file}")
            result = comparator.run_compatibility_test(sample_file)
            print(f"Result: {result['comparison']}")
            print("-" * 50)
        else:
            print(f"Sample file not found: {sample_file}")

    summary = comparator.get_test_summary()
    print(f"Test Summary: {summary}")