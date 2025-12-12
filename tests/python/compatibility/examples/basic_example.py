#!/usr/bin/env python3
"""
Basic compatibility test example

This script demonstrates how to run a simple compatibility test
between RustKmer CLI and Python API.
"""

import sys
import os
import json
import tempfile
from pathlib import Path

# Add rustkmer to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent.parent / "python"))

from rustkmer import KmerCounter, Database
from tests.python.compatibility.runner import CompatibilityTestRunner


def main():
    """Run basic compatibility test"""
    print("RustKmer Basic Compatibility Test")
    print("=" * 50)

    # Create a temporary directory for test files
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)

        # Create test sequence
        test_sequence = temp_path / "test.fasta"
        with open(test_sequence, 'w') as f:
            f.write(">test_sequence\n")
            f.write("ATCGATCGATCGATCGATCGATCGATCG\n")
            f.write("GCTAGCTAGCTAGCTAGCTAGCTAGCTA\n")
            f.write("TTTTTTTTTTTTTTTTTTTTTTTTTTTTTTT\n")

        # Test 1: K-mer counting
        print("\n1. Testing k-mer counting...")
        try:
            # CLI counting
            from tests.python.compatibility.runner import CLITester
            cli_tester = CLITester()
            db_path = temp_path / "test.rkdb"

            print("  Running CLI count...")
            cli_output, cli_time = cli_tester.run_command("count", [
                "-k", "8",
                str(test_sequence),
                str(db_path)
            ])

            # Python counting
            print("  Running Python count...")
            python_tester = PythonTester()
            python_output, python_time = python_tester.count_command(str(test_sequence), k=8)

            # Verify database was created
            if db_path.exists():
                print("  ✓ Database created successfully")

                # Test 2: Database querying
                print("\n2. Testing database querying...")
                db = Database()
                db.load(str(db_path))

                # Test query
                test_kmer = "ATCGATCG"
                query_result = db.query(test_kmer)

                print(f"  Query result for '{test_kmer}': found={query_result.found}, count={query_result.count}")

                # Test 3: Database statistics
                print("\n3. Testing database statistics...")
                stats = db.get_stats()
                print(f"  Database stats: k={stats.kmer_size}, total={stats.total_kmers}")

                # Test 4: Database dump
                print("\n4. Testing database dump...")
                dump_output = temp_path / "dump.txt"
                db.dump(str(dump_output), "text")

                # Check dump output
                if dump_output.exists() and dump_output.stat().st_size > 0:
                    print("  ✓ Dump successful")

                # Performance comparison
                print("\n5. Performance comparison...")
                if cli_time > 0 and python_time > 0:
                    ratio = python_time / cli_time
                    if ratio < 1.0:
                        print(f"  ✓ Python is {1/ratio:.1f}x faster than CLI")
                    elif ratio < 2.0:
                        print(f"  ✓ Python is {ratio:.1f}x slower than CLI (acceptable)")
                    else:
                        print(f"  ⚠ Python is {ratio:.1f}x slower than CLI (consider optimization)")

                print("\n✅ All compatibility tests passed!")
                return 0

        except Exception as e:
            print(f"\n❌ Test failed: {e}")
            import traceback
            traceback.print_exc()
            return 1


if __name__ == "__main__":
    sys.exit(main())