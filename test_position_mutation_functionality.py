#!/usr/bin/env python3
"""
测试 position-mutations 功能是否真的在工作
通过比较有和无位置配置的查询结果
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
    
    # Test the same pattern with different position configurations
    pattern = "AAAAAAAAAAAAAAAAAAA"
    mutations = 2
    
    print(f"\n🧬 Testing position-mutations functionality:")
    print("=" * 60)
    print(f"Pattern: {pattern}")
    print(f"Mutations: {mutations}")
    print(f"Database k-mer size: {stats.kmer_size}")
    
    # Test 1: No position mutations (basic fuzzy query)
    print(f"\n📝 Test 1: No position mutations (basic fuzzy query)")
    try:
        result1 = fuzzy.fuzzy_query(pattern, mutations, 1000)
        print(f"   ✅ SUCCESS! {result1.total_matches} matches found")
        print(f"   Query kmer: {result1.query_kmer}")
        print(f"   Mutation tolerance: {result1.mutation_tolerance}")
        
        # Show some matches
        if result1.matches:
            print(f"   Top matches:")
            for i, match in enumerate(result1.matches[:3]):
                print(f"     [{i}] {match.kmer}: count={match.count}")
                
    except Exception as e:
        print(f"   ❌ Error: {e}")
    
    # Test 2: With position mutations - single position
    print(f"\n📝 Test 2: With position mutations (single position '3:1')")
    try:
        # Use the new method with position mutations
        result2 = fuzzy.fuzzy_query_with_position_mutations(pattern, mutations, "3:1", 1000)
        print(f"   ✅ SUCCESS! {result2.total_matches} matches found")
        print(f"   Query kmer: {result2.query_kmer}")
        print(f"   Mutation tolerance: {result2.mutation_tolerance}")
        
        # Check if this has position mutations info
        if hasattr(result2, 'has_position_mutations'):
            print(f"   Has position mutations: {result2.has_position_mutations}")
        else:
            print(f"   (Position mutations info not available)")
        
        # Show some matches
        if result2.matches:
            print(f"   Top matches:")
            for i, match in enumerate(result2.matches[:3]):
                print(f"     [{i}] {match.kmer}: count={match.count}")
                if hasattr(match, 'mutation_positions') and match.mutation_positions:
                    print(f"         Mutation positions: {match.mutation_positions}")
                    
    except AttributeError as e:
        print(f"   ❌ Method not available: {e}")
    except Exception as e:
        print(f"   ❌ Error: {e}")
    
    # Test 3: With position mutations - multiple positions
    print(f"\n📝 Test 3: With position mutations (multiple positions '3,4,5:2')")
    try:
        result3 = fuzzy.fuzzy_query_with_position_mutations(pattern, mutations, "3,4,5:2", 1000)
        print(f"   ✅ SUCCESS! {result3.total_matches} matches found")
        
        # Show some matches
        if result3.matches:
            print(f"   Top matches:")
            for i, match in enumerate(result3.matches[:3]):
                print(f"     [{i}] {match.kmer}: count={match.count}")
                if hasattr(match, 'mutation_positions') and match.mutation_positions:
                    print(f"         Mutation positions: {match.mutation_positions}")
                    
    except AttributeError as e:
        print(f"   ❌ Method not available: {e}")
    except Exception as e:
        print(f"   ❌ Error: {e}")
    
    # Compare results
    print(f"\n📊 Result Comparison:")
    try:
        result1 = fuzzy.fuzzy_query(pattern, mutations, 1000)
        result2 = fuzzy.fuzzy_query_with_position_mutations(pattern, mutations, "3:1", 1000)
        
        print(f"   No position mutations: {result1.total_matches} matches")
        print(f"   With position mutations (3:1): {result2.total_matches} matches")
        
        if result1.total_matches != result2.total_matches:
            print(f"   ✅ DIFFERENCE DETECTED! Position mutations are working!")
        else:
            print(f"   ⚠️  Same results - position mutations may not be affecting queries")
            
    except Exception as e:
        print(f"   ❌ Comparison failed: {e}")
    
    print(f"\n🎉 Position-mutations functionality test completed!")
    
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
