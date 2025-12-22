#!/usr/bin/env python3
"""
Test script to check if the new unified API methods work
"""

import sys
sys.path.insert(0, '/Users/forrest/GitHub/rustkmer/pyo3/target/debug')

import rustkmer_pyo3

def test_new_methods():
    """Test if new methods exist and can be called"""
    print("🔍 Testing new unified API methods")
    print("=" * 50)
    
    # Test PyDatabase new methods
    print("\n📊 Testing PyDatabase new methods:")
    db_methods = {
        'query_exact': 'Single k-mer exact query',
        'query_exact_batch': 'Batch k-mer exact query', 
        'query_fuzzy': 'Fuzzy query',
        'query_prefix': 'Prefix query'
    }
    
    for method_name, description in db_methods.items():
        try:
            method = getattr(rustkmer_pyo3.PyDatabase, method_name)
            print(f"  ✅ {method_name}: {description}")
            print(f"      Method type: {type(method)}")
        except AttributeError:
            print(f"  ❌ {method_name}: NOT FOUND - {description}")
    
    # Test PyFuzzyQuery new methods
    print("\n🎯 Testing PyFuzzyQuery new methods:")
    fuzzy_methods = {
        'query_fuzzy': 'Basic fuzzy query',
        'query_fuzzy_position': 'Position-specific fuzzy query'
    }
    
    for method_name, description in fuzzy_methods.items():
        try:
            method = getattr(rustkmer_pyo3.PyFuzzyQuery, method_name)
            print(f"  ✅ {method_name}: {description}")
            print(f"      Method type: {type(method)}")
        except AttributeError:
            print(f"  ❌ {method_name}: NOT FOUND - {description}")
    
    # Test PyExtendedPrefixQuery new methods
    print("\n📈 Testing PyExtendedPrefixQuery new methods:")
    extended_methods = {
        'query_prefix_metrics': 'Prefix query with metrics',
        'query_hybrid_metrics': 'Hybrid query with metrics',
        'query_prefix_metrics_string': 'Prefix query with metrics (string input)',
        'query_prefix_batch_metrics': 'Batch prefix query with metrics'
    }
    
    for method_name, description in extended_methods.items():
        try:
            method = getattr(rustkmer_pyo3.PyExtendedPrefixQuery, method_name)
            print(f"  ✅ {method_name}: {description}")
            print(f"      Method type: {type(method)}")
        except AttributeError:
            print(f"  ❌ {method_name}: NOT FOUND - {description}")
    
    print("\n" + "=" * 50)
    print("✅ Test completed!")

if __name__ == "__main__":
    test_new_methods()
