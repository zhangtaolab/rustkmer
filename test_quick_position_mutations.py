#!/usr/bin/env python3
"""
Quick test of position-mutations functionality
"""

import sys
import os

# Add the target directory to Python path
target_dir = os.path.join(os.path.dirname(__file__), 'target', 'wheels')
if os.path.exists(target_dir):
    sys.path.insert(0, target_dir)

try:
    import rustkmer_pyo3
    print("✅ Successfully imported rustkmer_pyo3")
    
    # Real genomic database path
    db_path = "/Users/forrest/Data/data/kmer/K19/R1_001.rkdb"
    
    print(f"📁 Database: {db_path}")
    
    # Load the genomic database
    print("🔄 Loading genomic database...")
    db = rustkmer_pyo3.PyDatabase(db_path, rustkmer_pyo3.LoadMode.Preload)
    print("✅ Database loaded")
    
    # Get database stats
    stats = db.get_stats()
    print(f"📊 Stats: {stats.kmer_size}-mers, {stats.total_kmers:,} total k-mers")
    
    # Create fuzzy query engine
    print("🎯 Creating fuzzy query engine...")
    fuzzy = rustkmer_pyo3.PyFuzzyQuery(db)
    
    # Test cases
    test_cases = [
        {
            "name": "Single Position Mutation",
            "pattern": "AAAAAAAAAAAAAAAAAAA",
            "mutations": 1,
            "position_config": "3:1",
        },
        {
            "name": "Multiple Positions",
            "pattern": "AAAAAAAAAAAAAAAAAAA", 
            "mutations": 2,
            "position_config": "3,4,5:2",
        },
    ]
    
    print(f"\n🧬 Testing {len(test_cases)} scenarios:")
    print("-" * 50)
    
    for i, test_case in enumerate(test_cases, 1):
        name = test_case["name"]
        pattern = test_case["pattern"]
        mutations = test_case["mutations"]
        position_config = test_case["position_config"]
        
        print(f"\n🔬 Test {i}: {name}")
        print(f"   Pattern: {pattern}")
        print(f"   Mutations: {mutations}")
        print(f"   Position config: {position_config}")
        
        try:
            # Test calling the basic method (for now)
            print(f"   Calling fuzzy_query (basic)...")
            result = fuzzy.fuzzy_query(pattern, mutations, 1000)
            
            print(f"   ✅ SUCCESS! {result.total_matches:,} matches found")
            
            # Show some sample matches
            if result.matches:
                print(f"   🏆 Top 3 matches:")
                for j, match in enumerate(result.matches[:3]):
                    print(f"     [{j}] {match.kmer}: count={match.count:,}")
                    if hasattr(match, 'mutation_positions') and match.mutation_positions:
                        print(f"         Mutations at: {match.mutation_positions}")
                    else:
                        print(f"         (No mutation position info available)")
            else:
                print(f"   ⚠️  No matches found")
                    
        except Exception as e:
            print(f"   ❌ Error: {type(e).__name__}: {e}")
    
    print(f"\n🎉 Quick test completed!")
    
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
