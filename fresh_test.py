#!/usr/bin/env python3
"""
Fresh test to check PyO3 methods after rebuild
"""

import sys
import importlib

# Clear any cached modules
if 'rustkmer_pyo3' in sys.modules:
    del sys.modules['rustkmer_pyo3']

# Add path and import
sys.path.insert(0, '/Users/forrest/GitHub/rustkmer/pyo3/target/debug')

try:
    import rustkmer_pyo3
    print("✅ Successfully imported rustkmer_pyo3")
    
    # Force reload
    importlib.reload(rustkmer_pyo3)
    
    # Check PyDatabase methods
    print(f"\nPyDatabase methods ({len(dir(rustkmer_pyo3.PyDatabase))}):")
    methods = [m for m in dir(rustkmer_pyo3.PyDatabase) if not m.startswith('_')]
    for method in sorted(methods):
        print(f"  {method}")
    
    # Check for specific new methods
    new_methods = ['query_exact', 'query_exact_batch', 'query_fuzzy', 'query_prefix']
    print(f"\nChecking for new methods:")
    for method in new_methods:
        has_method = hasattr(rustkmer_pyo3.PyDatabase, method)
        print(f"  {method}: {'✅ EXISTS' if has_method else '❌ MISSING'}")
        
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
