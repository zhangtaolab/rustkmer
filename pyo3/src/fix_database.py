#!/usr/bin/env python3
"""Fix database.rs by removing duplicate and incorrect methods"""

import re

# Read the file
with open('database.rs', 'r') as f:
    lines = f.readlines()

# We need to fix the PyQueryResult impl block (lines 52-172, 0-indexed 51-171)
# Remove:
# 1. Lines 76-125: Incorrect PyDatabaseStats methods in PyQueryResult
# 2. Lines 150-171: Duplicate methods

new_lines = []
skip_next = False
in_pyqueryresult_impl = False
line_num = 0

for i, line in enumerate(lines):
    line_num = i + 1
    
    # Track when we enter/exit PyQueryResult impl
    if '#[pymethods]' in line and i + 1 < len(lines) and 'impl PyQueryResult' in lines[i+1]:
        in_pyqueryresult_impl = True
    elif in_pyqueryresult_impl and line.startswith('}') and 'impl PyPrefixQueryResult' in lines[i+1] if i+1 < len(lines) else False:
        in_pyqueryresult_impl = False
    
    # Skip incorrect PyDatabaseStats methods (lines 76-125, 0-indexed 75-124)
    if 75 <= i <= 124:
        continue
    
    # Skip duplicate methods (lines 150-171, 0-indexed 149-170)
    if 149 <= i <= 170:
        continue
    
    new_lines.append(line)

# Write the fixed file
with open('database.rs', 'w') as f:
    f.writelines(new_lines)

print(f"Fixed database.rs: removed {len(lines) - len(new_lines)} lines")
print(f"Original: {len(lines)} lines, Fixed: {len(new_lines)} lines")
