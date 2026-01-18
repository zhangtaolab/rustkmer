#!/usr/bin/env python3
"""Fix fuzzy_query.rs by adding Debug trait to PyFuzzyMatch"""

# Read file
with open('fuzzy_query.rs', 'r') as f:
    lines = f.readlines()

# Find line 19 (0-indexed 18) which has #[derive(Clone)]
# Replace it with #[derive(Clone, Debug)]
for i, line in enumerate(lines):
    if i == 18 and '#[derive(Clone)]' in line:
        lines[i] = line.replace('#[derive(Clone)]', '#[derive(Clone, Debug)]')
        break

# Write fixed file
with open('fuzzy_query.rs', 'w') as f:
    f.writelines(lines)

print("Added Debug trait to PyFuzzyMatch")
