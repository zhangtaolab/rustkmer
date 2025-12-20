#!/usr/bin/env python3
"""
测试新的统一接口
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
    
    # Create fuzzy query engine
    print("🎯 Creating fuzzy query engine...")
    fuzzy = rustkmer_pyo3.PyFuzzyQuery(db)
    
    # Test different calling patterns
    pattern = "AAAAAAAAAAAAAAAAAAA"
    mutations = 1
    
    print(f"\n🧬 Testing unified interface:")
    print("=" * 50)
    print(f"Pattern: {pattern}")
    print(f"Mutations: {mutations}")
    
    # Test 1: Basic call (no position mutations)
    print(f"\n📝 Test 1: Basic call (no position mutations)")
    try:
        result1 = fuzzy.fuzzy_query(pattern, mutations, None)
        print(f"   ✅ SUCCESS! {result1.total_matches} matches found")
        
        if hasattr(result1, 'has_position_mutations'):
            print(f"   Has position mutations: {result1.has_position_mutations}")
            
    except Exception as e:
        print(f"   ❌ Error: {e}")
    
    # Test 2: Call with None position_mutations
    print(f"\n📝 Test 2: Call with position_mutations=None")
    try:
        result2 = fuzzy.fuzzy_query(pattern, mutations, None, None)
        print(f"   ✅ SUCCESS! {result2.total_matches} matches found")
        
        if hasattr(result2, 'has_position_mutations'):
            print(f"   Has position mutations: {result2.has_position_mutations}")
            
    except Exception as e:
        print(f"   ❌ Error: {e}")
    
    # Test 3: Call with position_mutations (this should fail for now if not supported)
    print(f"\n📝 Test 3: Call with position_mutations='3:1'")
    try:
        result3 = fuzzy.fuzzy_query(pattern, mutations, "3:1", None)
        print(f"   ✅ SUCCESS! {result3.total_matches} matches found")
        
        if hasattr(result3, 'has_position_mutations'):
            print(f"   Has position mutations: {result3.has_position_mutations}")
            
    except TypeError as e:
        if "unexpected keyword argument" in str(e):
            print(f"   ❌ Method signature issue: {e}")
        else:
            print(f"   ❌ Type error: {e}")
    except Exception as e:
        print(f"   ❌ Error: {e}")
    
    # Test 4: Positional arguments
    print(f"\n📝 Test 4: All positional arguments")
    try:
        result4 = fuzzy.fuzzy_query(pattern, mutations, "3:1", None)
        print(f"   ✅ SUCCESS! {result4.total_matches} matches found")
        
        if hasattr(result4, 'has_position_mutations'):
            print(f"   Has position mutations: {result4.has_position_mutations}")
            
    except TypeError as e:
        print(f"   ❌ Type error: {e}")
    except Exception as e:
        print(f"   ❌ Error: {e}")
    
    print(f"\n🎉 Unified interface test completed!")
    
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
