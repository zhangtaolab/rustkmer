#!/usr/bin/env python3
"""
RustKmer CLI vs Python API Cross-Platform Compatibility Demonstration

This script demonstrates that rustkmer CLI and Python API produce identical databases
and can query each other's databases seamlessly.

Test Data: tests/007-api-compatibility/test_data/small_dataset.fa
K-mer Size: 7 (optimal for test data)
"""

import subprocess
import tempfile
import os
import sys
import time
from pathlib import Path

def run_command(cmd, cwd="/Users/forrest/GitHub/rustkmer"):
    """Run a command and return stdout, stderr, and return code"""
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, cwd=cwd)
        return result.stdout, result.stderr, result.returncode
    except Exception as e:
        return "", str(e), 1

def test_database_creation():
    """Test database creation with both CLI and Python API"""
    print("🧪 Phase 1: Database Creation")
    print("=" * 50)

    # Use the better test data
    input_file = "/Users/forrest/GitHub/rustkmer/tests/007-api-compatibility/test_data/small_dataset.fa"
    cli_db = "/Users/forrest/GitHub/rustkmer/demo_cli_database.rkdb"
    py_db = "/Users/forrest/GitHub/rustkmer/demo_python_database.rkdb"

    # Test CLI database creation
    print("1. Creating database with rustkmer CLI...")
    start_time = time.time()
    stdout, stderr, code = run_command(
        f"./target/release/rustkmer count -k 7 -i tests/007-api-compatibility/test_data/small_dataset.fa -o demo_cli_database.rkdb"
    )

    if code != 0:
        print(f"❌ CLI database creation failed: {stderr}")
        return False, None, None

    cli_time = time.time() - start_time
    cli_size = os.path.getsize("/Users/forrest/GitHub/rustkmer/demo_cli_database.rkdb")
    print(f"✅ CLI database created: {cli_size} bytes in {cli_time:.3f}s")

    # Test Python database creation
    print("2. Creating database with Python API...")
    start_time = time.time()
    stdout, stderr, code = run_command(f'''
python3 -c "
from rustkmer import KmerCounter
import time

start_time = time.time()
counter = KmerCounter(k=7, canonical=False)
counter.count_file('{input_file}')
counter.save_to_database('{py_db}', False)
py_time = time.time() - start_time
print(f'Python database creation time: {{py_time:.3f}}s')
"
''')

    if code != 0:
        print(f"❌ Python database creation failed: {stderr}")
        return False, None, None

    py_time = time.time() - start_time
    py_size = os.path.getsize("/Users/forrest/GitHub/rustkmer/demo_python_database.rkdb")
    print(f"✅ Python database created: {py_size} bytes in {py_time:.3f}s")

    # Compare file sizes
    if abs(cli_size - py_size) > 100:  # Allow small difference
        print(f"⚠️  File size difference: CLI={cli_size}, Python={py_size}")
    else:
        print(f"✅ File sizes match: CLI={cli_size}, Python={py_size}")

    return True, "/Users/forrest/GitHub/rustkmer/demo_cli_database.rkdb", "/Users/forrest/GitHub/rustkmer/demo_python_database.rkdb"

def test_database_content_compatibility(cli_db, py_db):
    """Test that databases have identical content"""
    print("\n🧪 Phase 2: Database Content Comparison")
    print("=" * 50)

    # Dump both databases
    print("1. Dumping CLI database content...")
    stdout, stderr, code = run_command(f"./target/release/rustkmer dump demo_cli_database.rkdb")

    if code != 0:
        print(f"❌ CLI database dump failed: {stderr}")
        return False

    cli_content = stdout.strip()
    cli_lines = [line for line in cli_content.split('\n') if not line.startswith('#') and line.strip()]
    print(f"✅ CLI database contains {len(cli_lines)} k-mers")

    print("2. Dumping Python database content...")
    stdout, stderr, code = run_command(f"./target/release/rustkmer dump demo_python_database.rkdb")

    if code != 0:
        print(f"❌ Python database dump failed: {stderr}")
        return False

    py_content = stdout.strip()
    py_lines = [line for line in py_content.split('\n') if not line.startswith('#') and line.strip()]
    print(f"✅ Python database contains {len(py_lines)} k-mers")

    # Compare content
    if len(cli_lines) != len(py_lines):
        print(f"❌ Different number of k-mers: CLI={len(cli_lines)}, Python={len(py_lines)}")
        return False

    # Parse and compare k-mer counts
    cli_kmers = {}
    py_kmers = {}

    for line in cli_lines:
        if '\t' in line:
            kmer, count = line.strip().split('\t')
            cli_kmers[kmer] = int(count)

    for line in py_lines:
        if '\t' in line:
            kmer, count = line.strip().split('\t')
            py_kmers[kmer] = int(count)

    # Check for differences
    differences = 0
    all_kmers = set(cli_kmers.keys()) | set(py_kmers.keys())

    for kmer in all_kmers:
        cli_count = cli_kmers.get(kmer, 0)
        py_count = py_kmers.get(kmer, 0)
        if cli_count != py_count:
            differences += 1
            if differences <= 5:  # Show first 5 differences
                print(f"❌ {kmer}: CLI={cli_count}, Python={py_count}")

    if differences == 0:
        print("✅ All k-mer counts match perfectly!")
        return True
    else:
        print(f"❌ Found {differences} k-mer count differences")
        return False

def test_cross_platform_querying(cli_db, py_db):
    """Test that CLI and Python API can query each other's databases"""
    print("\n🧪 Phase 3: Cross-Platform Querying")
    print("=" * 50)

    # Test k-mers that should exist in our data
    test_kmers = [
        "ACGTACG",  # From seq1
        "CGTACGT",  # From seq1
        "GCTAGCT",  # From seq2
        "CTAGCTA",  # From seq2
        "TTTTTTT",  # From seq3
        "CCCCCCC",  # From seq4
        "GGGGGGG",  # From seq5
        "AAAAAAA",  # Should not exist
    ]

    print("1. Testing CLI queries on both databases...")
    cli_results_cli_db = {}
    cli_results_py_db = {}

    for kmer in test_kmers:
        # Query CLI-created database
        stdout, stderr, code = run_command(f"./target/release/rustkmer query demo_cli_database.rkdb {kmer}")
        if code == 0 and stdout.strip():
            parts = stdout.strip().split('\t')
            if len(parts) >= 2:
                cli_results_cli_db[kmer] = int(parts[1])
            else:
                cli_results_cli_db[kmer] = 0
        else:
            cli_results_cli_db[kmer] = 0

        # Query Python-created database
        stdout, stderr, code = run_command(f"./target/release/rustkmer query demo_python_database.rkdb {kmer}")
        if code == 0 and stdout.strip():
            parts = stdout.strip().split('\t')
            if len(parts) >= 2:
                cli_results_py_db[kmer] = int(parts[1])
            else:
                cli_results_py_db[kmer] = 0
        else:
            cli_results_py_db[kmer] = 0

        print(f"   {kmer}: CLI_db={cli_results_cli_db[kmer]}, Python_db={cli_results_py_db[kmer]}")

    print("2. Testing Python API queries on both databases...")
    test_kmers_str = str(test_kmers)
    stdout, stderr, code = run_command(f'''
python3 -c "
from rustkmer import Database

db1 = Database()
db1.load('/Users/forrest/GitHub/rustkmer/demo_cli_database.rkdb')

db2 = Database()
db2.load('/Users/forrest/GitHub/rustkmer/demo_python_database.rkdb')

test_kmers = {test_kmers_str}

print('=== Python API querying CLI database ===')
for kmer in test_kmers:
    result = db1.query(kmer)
    print(f'{{kmer}}:{{result.count}}')

print('=== Python API querying Python database ===')
for kmer in test_kmers:
    result = db2.query(kmer)
    print(f'{{kmer}}:{{result.count}}')
"
''')

    if code != 0:
        print(f"❌ Python API querying failed: {stderr}")
        return False

    # Parse Python results
    lines = stdout.strip().split('\n')
    py_results_cli_db = {}
    py_results_py_db = {}

    current_section = None
    for line in lines:
        if "CLI database" in line:
            current_section = "cli"
        elif "Python database" in line:
            current_section = "py"
        elif ':' in line and current_section:
            kmer, count = line.split(':', 1)
            count = int(count)
            if current_section == "cli":
                py_results_cli_db[kmer] = count
            else:
                py_results_py_db[kmer] = count

    print("   Python API results parsed successfully")

    # Verify all results are identical
    print("3. Verifying result consistency...")
    all_consistent = True

    for kmer in test_kmers:
        cli_cli = cli_results_cli_db.get(kmer, 0)
        cli_py = cli_results_py_db.get(kmer, 0)
        py_cli = py_results_cli_db.get(kmer, 0)
        py_py = py_results_py_db.get(kmer, 0)

        if cli_cli == cli_py == py_cli == py_py:
            print(f"   ✅ {kmer}: All methods return {cli_cli}")
        else:
            print(f"   ❌ {kmer}: CLI_on_CLI={cli_cli}, CLI_on_Py={cli_py}, Py_on_CLI={py_cli}, Py_on_Py={py_py}")
            all_consistent = False

    return all_consistent

def test_database_stats():
    """Test database statistics functionality"""
    print("\n🧪 Phase 4: Database Statistics")
    print("=" * 50)

    stdout, stderr, code = run_command('''
python3 -c "
from rustkmer import KmerCounter, Database

# Test database creation with stats
counter = KmerCounter(k=7, canonical=False)
counter.count_file('/Users/forrest/GitHub/rustkmer/tests/007-api-compatibility/test_data/small_dataset.fa')
counter.save_to_database('/Users/forrest/GitHub/rustkmer/stats_test.rkdb', False)

# Test database stats
db = Database()
db.load('/Users/forrest/GitHub/rustkmer/stats_test.rkdb')
stats = db.get_stats()

print(f'Database loaded: {stats.uses_memory_mapping}')
print(f'K-mer size: {stats.kmer_size}')
print(f'Total k-mers: {stats.total_kmers}')
print(f'Canonical: {stats.canonical}')

# Test a query
result = db.query('ACGTACG')
print(f'Query ACGTACG: count={result.count}, found={result.found}')

# Cleanup
import os
os.remove('/Users/forrest/GitHub/rustkmer/stats_test.rkdb')
"
''')

    if code != 0:
        print(f"❌ Database stats test failed: {stderr}")
        return False

    print("✅ Database statistics test completed")
    print(f"Output: {stdout.strip()}")
    return True

def main():
    """Run the complete compatibility demonstration"""
    print("🚀 RustKmer CLI vs Python API Cross-Platform Compatibility Demo")
    print("=" * 70)
    print("This demonstration proves that CLI and Python API produce identical")
    print("databases and can query each other's databases seamlessly.")
    print("=" * 70)

    # Phase 1: Database creation
    success, cli_db, py_db = test_database_creation()
    if not success:
        print("\n❌ Database creation phase failed - aborting demonstration")
        return 1

    # Phase 2: Content comparison
    success = test_database_content_compatibility(cli_db, py_db)
    if not success:
        print("\n❌ Database content comparison failed")
        content_ok = False
    else:
        content_ok = True
        print("\n✅ Database content comparison passed")

    # Phase 3: Cross-platform querying
    success = test_cross_platform_querying(cli_db, py_db)
    if not success:
        print("\n❌ Cross-platform querying failed")
        query_ok = False
    else:
        query_ok = True
        print("\n✅ Cross-platform querying passed")

    # Phase 4: Database statistics
    success = test_database_stats()
    if not success:
        print("\n❌ Database statistics test failed")
        stats_ok = False
    else:
        stats_ok = True
        print("\n✅ Database statistics test passed")

    # Cleanup
    for db_file in [cli_db, py_db]:
        if os.path.exists(db_file):
            os.remove(db_file)
            print(f"🧹 Cleaned up {db_file}")

    # Final results
    print(f"\n{'='*70}")
    print("🏆 DEMONSTRATION RESULTS")
    print(f"{'='*70}")

    results = [
        ("Database Creation", True),  # We got this far, so it worked
        ("Content Compatibility", content_ok),
        ("Cross-Platform Querying", query_ok),
        ("Database Statistics", stats_ok),
    ]

    passed = 0
    for test_name, success in results:
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status:<8} {test_name}")
        if success:
            passed += 1

    print(f"\nOverall Result: {passed}/{len(results)} test phases passed")

    if passed == len(results):
        print("\n🎉 CROSS-PLATFORM COMPATIBILITY VERIFIED!")
        print("\n✅ Key Achievements:")
        print("  • CLI and Python API create identical databases")
        print("  • Both platforms can query each other's databases")
        print("  • All query results are consistent across platforms")
        print("  • Database statistics and metadata are accessible")
        print("  • 007-api-compatibility implementation is working correctly")
        return 0
    else:
        print("\n❌ Some compatibility tests failed")
        return 1

if __name__ == "__main__":
    exit(main())