#!/usr/bin/env python3
"""Example usage of rustkmer test databases."""

import sys
from pathlib import Path

# Add the rustkmer package to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from rustkmer import Database

def demo_database_usage():
    """Demonstrate basic database operations."""
    test_data_dir = Path(__file__).parent
    
    databases = [
        "tiny_test.rkdb",
        "small_test.rkdb", 
        "medium_test.rkdb",
        "large_test.rkdb"
    ]
    
    for db_name in databases:
        db_path = test_data_dir / db_name
        if not db_path.exists():
            print(f"✗ Database not found: {db_name}")
            continue
            
        print(f"\n=== Testing {db_name} ===")
        
        try:
            with Database(db_path) as db:
                print(f"✓ Successfully opened {db_name}")
                
                # Try a simple query
                result = db.query("GCCGCGG")
                if result:
                    print(f"✓ Query 'GCCGCGG': count = {result.count}")
                else:
                    print("✓ Query 'GCCGCGG': not found (expected for some databases)")
                
                # Get basic stats if available
                try:
                    stats = db.stats()
                    print(f"✓ Database stats available")
                except:
                    print("✓ Database loaded (stats not available)")
                    
        except Exception as e:
            print(f"✗ Error with {db_name}: {e}")

def cli_demo():
    """Demonstrate CLI usage."""
    print("\n=== CLI Usage Examples ===")
    
    examples = [
        "rustkmer query tiny_test.rkdb GCCGCGG",
        "rustkmer query small_test.rkdb GCCGCGG ATCCTGA",
        "rustkmer count -k 7 -i large_test.fasta -o new_db.rkdb --canonical"
    ]
    
    for example in examples:
        print(f"$ {example}")

if __name__ == "__main__":
    print("RustKmer Test Database Examples")
    print("=" * 40)
    
    demo_database_usage()
    cli_demo()
    
    print(f"\n✓ All examples completed!")
    print(f"Test databases are ready for use in unit tests and demonstrations.")
