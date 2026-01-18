#!/usr/bin/env python3
"""Fix circular import in counter.rs"""

# Read file
with open('counter.rs', 'r') as f:
    lines = f.readlines()

# Remove line 8: use crate::PyCounter as RustPyCounter;
# And change RustPyCounter back to PyCounter (line 108)
new_lines = []
for i, line in enumerate(lines):
    # Skip line 8 (0-indexed 7)
    if i == 7 and 'use crate::PyCounter as RustPyCounter;' in line:
        continue
    
    # Change RustPyCounter to PyCounter in line 108 (0-indexed 107)
    if i == 107 and 'RustPyCounter::new' in line:
        line = line.replace('RustPyCounter::new', 'PyCounter::new')
    
    new_lines.append(line)

# Write fixed file
with open('counter.rs', 'w') as f:
    f.writelines(new_lines)

print("Fixed circular import in counter.rs")
