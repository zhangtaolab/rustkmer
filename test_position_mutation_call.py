#!/usr/bin/env python3
"""
Test position mutation functionality with different calling approaches
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
    
    # Test 1: Basic positional arguments
    print("\n🧪 Test 1: Basic positional arguments")
    try:
        # This should work - basic signature
        # We can't actually test without a database, but we can check if the method accepts the right parameters
        
        # Let's try calling with all positional arguments
        # This will fail because we need a database, but it should show the signature error
        print("   Attempting basic call...")
        
    except Exception as e:
        print(f"   Expected error (no database): {type(e).__name__}")
    
    # Test 2: With keyword arguments (position_mutations=None)
    print("\n🧪 Test 2: With keyword arguments")
    try:
        # Test the new signature with position_mutations=None
        print("   Attempting call with position_mutations=None...")
        
    except Exception as e:
        print(f"   Expected error (no database): {type(e).__name__}")
    
    # Test 3: With position_mutations parameter
    print("\n🧪 Test 3: With position_mutations parameter")
    try:
        # Test with actual position_mutations string
        print("   Attempting call with position_mutations='3:1'...")
        
    except Exception as e:
        print(f"   Expected error (no database): {type(e).__name__}")
    
    # Test 4: Check method signature details
    print("\n🧪 Test 4: Method signature inspection")
    import inspect
    
    sig = inspect.signature(rustkmer_pyo3.PyFuzzyQuery.fuzzy_query)
    print(f"   Current signature: {sig}")
    
    # Get parameter details
    params = list(sig.parameters.keys())
    print(f"   Parameters: {params}")
    
    for name, param in sig.parameters.items():
        print(f"     {name}: default={param.default}, kind={param.kind}")
    
    print("✅ Signature analysis completed")
    
except ImportError as e:
    print(f"❌ Import error: {e}")
    
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
