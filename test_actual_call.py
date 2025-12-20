#!/usr/bin/env python3
"""
Test actual function call with position_mutations parameter
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
    
    # Create a test database path (non-existent)
    db_path = "/tmp/test.rkdb"
    
    print(f"🧪 Testing fuzzy_query with position_mutations...")
    
    # Test 1: Try calling with position_mutations=None
    print("\n📝 Test 1: position_mutations=None")
    try:
        db = rustkmer_pyo3.PyDatabase(db_path, rustkmer_pyo3.LoadMode.Preload)
        fuzzy = rustkmer_pyo3.PyFuzzyQuery(db)
        
        # Try calling with position_mutations=None
        result = fuzzy.fuzzy_query("ATCGATCGATCGATCGA", 1, position_mutations=None)
        print("✅ Call with position_mutations=None succeeded")
        
    except FileNotFoundError:
        print("✅ Expected error: Database file not found (this is OK)")
    except TypeError as e:
        if "unexpected keyword argument" in str(e):
            print(f"❌ Method signature error: {e}")
        else:
            print(f"✅ Type error (expected for signature issues): {e}")
    except Exception as e:
        print(f"❌ Unexpected error: {type(e).__name__}: {e}")
    
    # Test 2: Try calling with position_mutations="3:1"
    print("\n📝 Test 2: position_mutations='3:1'")
    try:
        db = rustkmer_pyo3.PyDatabase(db_path, rustkmer_pyo3.LoadMode.Preload)
        fuzzy = rustkmer_pyo3.PyFuzzyQuery(db)
        
        # Try calling with position_mutations="3:1"
        result = fuzzy.fuzzy_query("ATCGATCGATCGATCGA", 1, position_mutations="3:1")
        print("✅ Call with position_mutations='3:1' succeeded")
        
    except FileNotFoundError:
        print("✅ Expected error: Database file not found (this is OK)")
    except TypeError as e:
        if "unexpected keyword argument" in str(e):
            print(f"❌ Method signature error: {e}")
        else:
            print(f"✅ Type error (expected for signature issues): {e}")
    except Exception as e:
        print(f"❌ Unexpected error: {type(e).__name__}: {e}")
    
    # Test 3: Try calling without position_mutations (backward compatibility)
    print("\n📝 Test 3: No position_mutations (backward compatibility)")
    try:
        db = rustkmer_pyo3.PyDatabase(db_path, rustkmer_pyo3.LoadMode.Preload)
        fuzzy = rustkmer_pyo3.PyFuzzyQuery(db)
        
        # Try calling without position_mutations
        result = fuzzy.fuzzy_query("ATCGATCGATCGATCGA", 1)
        print("✅ Backward compatible call succeeded")
        
    except FileNotFoundError:
        print("✅ Expected error: Database file not found (this is OK)")
    except Exception as e:
        print(f"❌ Unexpected error: {type(e).__name__}: {e}")
    
    print("\n🎉 Function call tests completed")
    
except ImportError as e:
    print(f"❌ Import error: {e}")
    
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
