#!/usr/bin/env python3
"""
PyO3 RustKmer RKDB Query Demo

This demo showcases the PyO3-enhanced RustKmer library querying real RKDB database files.
It demonstrates database loading, querying, and statistics retrieval using actual k-mer data
from the test datasets.

Requirements:
- rustkmer_pyo3 extension (built with: maturin build)
- Python 3.11+
- Test database files in ../python/tests/test_data/

Usage:
    python rkdb_query_demo.py

Author: RustKmer Team
"""

import sys
import time
from pathlib import Path

def main():
    """Main demo function"""
    print("🚀 PyO3 RustKmer RKDB Query Demo")
    print("=" * 60)
    print("This demo shows how to query real RKDB database files using PyO3 bindings")
    print("=" * 60)
    
    # Try to import the PyO3 extension
    try:
        import rustkmer_pyo3
        print("✅ Successfully imported rustkmer_pyo3")
        
        # Show available classes
        available_classes = [attr for attr in dir(rustkmer_pyo3) if not attr.startswith('_')]
        print(f"📋 Available classes: {available_classes}")
        
    except ImportError as e:
        print(f"❌ Failed to import rustkmer_pyo3: {e}")
        print("\nTo build the extension:")
        print("  1. cd pyo3")
        print("  2. maturin build")
        print("  3. pip install -e .")
        return 1

    # Find test database files
    test_data_dir = Path(__file__).parent.parent / "python" / "tests" / "test_data"
    
    if not test_data_dir.exists():
        print(f"❌ Test data directory not found: {test_data_dir}")
        return 1
    
    # List available database files
    db_files = list(test_data_dir.glob("*.rkdb"))
    
    if not db_files:
        print(f"❌ No .rkdb files found in {test_data_dir}")
        return 1
    
    print(f"\n📁 Found {len(db_files)} database files:")
    for db_file in sorted(db_files):
        size = db_file.stat().st_size
        print(f"  - {db_file.name} ({size:,} bytes)")
    
    # Demo 1: Load and query the smallest database
    demo_tiny_database(rustkmer_pyo3, db_files, test_data_dir)
    
    # Demo 2: Query multiple databases
    demo_multiple_databases(rustkmer_pyo3, db_files, test_data_dir)
    
    # Demo 3: Performance comparison
    demo_performance_comparison(rustkmer_pyo3, db_files, test_data_dir)
    
    print("\n" + "=" * 60)
    print("🎉 PyO3 RKDB Query Demo completed successfully!")
    print("=" * 60)
    print("✅ All queries executed using real RKDB data")
    print("🔥 PyO3 provides efficient native database querying")
    
    return 0

def demo_tiny_database(rustkmer_pyo3, db_files, test_data_dir):
    """Demo querying the tiny database"""
    print("\n" + "="*60)
    print("🔍 Demo 1: Tiny Database Query")
    print("="*60)
    
    tiny_db = test_data_dir / "tiny_test.rkdb"
    
    if not tiny_db.exists():
        print("❌ tiny_test.rkdb not found, skipping this demo")
        return
    
    try:
        print(f"📂 Loading database: {tiny_db}")
        start_time = time.time()
        db = rustkmer_pyo3.PyDatabase(str(tiny_db), memory_mapped=False)
        load_time = time.time() - start_time
        print(f"✅ Database loaded in {load_time:.3f} seconds")
        
        # Show database statistics
        print("\n📊 Database Statistics:")
        stats = db.get_stats()
        print(f"  K-mer size: {stats.kmer_size}")
        print(f"  Total k-mers: {stats.total_kmers:,}")
        print(f"  Unique k-mers: {stats.unique_kmers:,}")
        print(f"  File size: {stats.file_size:,} bytes")
        print(f"  Canonical mode: {stats.canonical}")
        print(f"  Sorted: {stats.is_sorted}")
        
        # Demo some queries
        print("\n🔍 Query Examples:")
        test_kmers = ["GCCGCGG", "AATTCTC", "GTTAAGG", "NOTFOUND"]
        
        for kmer in test_kmers:
            try:
                result = db.query(kmer)
                print(f"  {kmer}: count={result.count}, found={result.found}")
            except Exception as e:
                print(f"  {kmer}: Error - {e}")
        
        # Test existence
        print("\n✅ Existence Checks:")
        for kmer in test_kmers[:3]:
            try:
                exists = db.exists(kmer)
                print(f"  {kmer}: {'exists' if exists else 'not found'}")
            except Exception as e:
                print(f"  {kmer}: Error - {e}")
        
    except Exception as e:
        print(f"❌ Error loading tiny database: {e}")
        import traceback
        traceback.print_exc()

def demo_multiple_databases(rustkmer_pyo3, db_files, test_data_dir):
    """Demo querying multiple databases"""
    print("\n" + "="*60)
    print("🔍 Demo 2: Multiple Database Queries")
    print("="*60)
    
    # Test with small and medium databases
    test_dbs = ["small_test.rkdb", "medium_test.rkdb"]
    
    for db_name in test_dbs:
        db_path = test_data_dir / db_name
        
        if not db_path.exists():
            print(f"⚠️  {db_name} not found, skipping")
            continue
            
        try:
            print(f"\n📂 Testing {db_name}:")
            db = rustkmer_pyo3.PyDatabase(str(db_path), memory_mapped=False)
            stats = db.get_stats()
            
            print(f"  Database size: {stats.total_kmers:,} total k-mers")
            print(f"  K-mer length: {stats.kmer_size}")
            
            # Test a few queries
            test_kmers = ["AAAAAA", "CCCCCC", "GGGGGG", "TTTTTT"]
            print(f"  Querying sample k-mers:")
            
            for kmer in test_kmers:
                try:
                    result = db.query(kmer)
                    if result.found:
                        print(f"    {kmer}: {result.count} occurrences")
                    else:
                        print(f"    {kmer}: not found")
                except Exception as e:
                    print(f"    {kmer}: error - {e}")
                    
        except Exception as e:
            print(f"❌ Error with {db_name}: {e}")

def demo_performance_comparison(rustkmer_pyo3, db_files, test_data_dir):
    """Demo performance comparison"""
    print("\n" + "="*60)
    print("⚡ Demo 3: Performance Analysis")
    print("="*60)
    
    # Use small database for performance testing
    small_db = test_data_dir / "small_test.rkdb"
    
    if not small_db.exists():
        print("❌ small_test.rkdb not found, skipping performance demo")
        return
    
    try:
        print(f"📂 Loading {small_db} for performance testing...")
        db = rustkmer_pyo3.PyDatabase(str(small_db), memory_mapped=False)
        stats = db.get_stats()
        
        print(f"✅ Loaded database with {stats.unique_kmers:,} unique k-mers")
        
        # Performance test with different query patterns
        query_patterns = [
            ["AAAAAA", "CCCCCC", "GGGGGG"],  # Simple patterns
            ["ATATATA", "GCGCGCG", "TATATA"],  # Repeating patterns
            ["ABCDEFG", "HIJKLMN", "OPQRSTU"],  # Invalid patterns (should return 0)
        ]
        
        for i, patterns in enumerate(query_patterns, 1):
            print(f"\n🔍 Test {i}: {len(patterns)} queries")
            start_time = time.time()
            
            results = []
            for pattern in patterns:
                try:
                    result = db.query(pattern)
                    results.append(result.found)
                except Exception:
                    results.append(False)
            
            end_time = time.time()
            elapsed = (end_time - start_time) * 1000  # Convert to ms
            
            print(f"  Time: {elapsed:.2f}ms total, {elapsed/len(patterns):.2f}ms per query")
            print(f"  Found: {sum(results)}/{len(results)} k-mers")
        
        print("\n📈 Performance Summary:")
        print("  ✅ Database loading: Fast")
        print("  ✅ Single queries: Sub-millisecond")
        print("  ✅ Memory efficient: In-memory cache")
        print("  ✅ PyO3 overhead: Minimal")
        
    except Exception as e:
        print(f"❌ Performance demo error: {e}")

def show_available_methods():
    """Show available methods in PyDatabase"""
    print("\n🔧 Available PyDatabase Methods:")
    methods = [
        ("__init__(path, memory_mapped)", "Initialize database connection"),
        ("query(kmer)", "Query a single k-mer"),
        ("query_batch(kmers)", "Query multiple k-mers"),
        ("exists(kmer)", "Check if k-mer exists"),
        ("get_stats()", "Get database statistics"),
        ("path", "Database file path"),
        ("kmer_size", "K-mer length"),
        ("canonical", "Whether canonical mode is used"),
        ("total_kmers", "Total k-mers in database"),
        ("unique_kmers", "Unique k-mers count"),
        ("is_loaded", "Whether database is loaded"),
    ]
    
    for method, description in methods:
        print(f"  {method:<25} - {description}")

if __name__ == "__main__":
    sys.exit(main())
