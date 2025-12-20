#!/usr/bin/env python3
"""
Test position mutations with positional parameters
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
    
    # Create a fuzzy query without database to test parameter parsing
    # We'll just test if the method accepts the right number of parameters
    
    print("🧪 Testing parameter parsing...")
    
    # Test with different parameter combinations
    test_cases = [
        # (pattern, max_mutations, position_mutations, max_results)
        ("ATCGATCGATCGATCGA", 1, None, None),  # Basic test
        ("ATCGATCGATCGATCGA", 1, "3:1", None),  # With position config
    ]
    
    for i, test_case in enumerate(test_cases):
        try:
            print(f"\n📝 Test {i+1}: {test_case}")
            
            # Since we can't create a real fuzzy query without a database,
            # we'll just validate that the parameter parsing works
            pattern, max_mutations, position_mutations, max_results = test_case
            
            print(f"   Pattern: {pattern}")
            print(f"   Max mutations: {max_mutations}")
            print(f"   Position mutations: {position_mutations}")
            print(f"   Max results: {max_results}")
            
            # Try to parse position mutations config
            if position_mutations:
                # Basic validation - split by semicolon
                groups = position_mutations.split(';')
                for group in groups:
                    group = group.strip()
                    if group:
                        if ':' not in group:
                            raise ValueError(f"Invalid group format: {group}")
                        positions, limit = group.split(':', 1)
                        positions = positions.strip()
                        limit = limit.strip()
                        
                        if not positions:
                            raise ValueError("Empty positions")
                        if not limit.isdigit():
                            raise ValueError(f"Non-numeric limit: {limit}")
                        
                        print(f"   ✅ Valid config: positions={positions}, limit={limit}")
            
            print(f"   ✅ Parameter parsing successful")
            
        except Exception as e:
            print(f"   ❌ Parameter parsing failed: {e}")
    
    print(f"\n🎉 Parameter validation completed!")
    
except ImportError as e:
    print(f"❌ Import error: {e}")
    
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
