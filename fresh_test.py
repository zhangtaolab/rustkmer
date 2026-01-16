#!/usr/bin/env python3
"""
Fresh test to check PyO3 methods after rebuild
"""

import sys
import importlib

# Clear any cached modules
if "pyrustkmer" in sys.modules:
    del sys.modules["pyrustkmer"]

# Add path and import
sys.path.insert(0, "/Users/forrest/GitHub/rustkmer/pyo3/target/debug")

try:
    import pyrustkmer

    print("✅ Successfully imported pyrustkmer")

    # Force reload
    importlib.reload(pyrustkmer)

    # Check PyDatabase methods
    print(f"\nPyDatabase methods ({len(dir(pyrustkmer.PyDatabase))}):")
    methods = [m for m in dir(pyrustkmer.PyDatabase) if not m.startswith("_")]
    for method in sorted(methods):
        print(f"  {method}")

    # Check for specific new methods
    new_methods = ["query_exact", "query_exact_batch", "query_fuzzy", "query_prefix"]
    print(f"\nChecking for new methods:")
    for method in new_methods:
        has_method = hasattr(pyrustkmer.PyDatabase, method)
        print(f"  {method}: {'✅ EXISTS' if has_method else '❌ MISSING'}")

except Exception as e:
    print(f"❌ Error: {e}")
    import traceback

    traceback.print_exc()
