#!/usr/bin/env python3
"""Fix database.rs by removing duplicate methods in PyPrefixQueryResult"""

# Read file
with open('database.rs', 'r') as f:
    lines = f.readlines()

# Need to remove duplicate methods from PyPrefixQueryResult impl:
# - Duplicate to_csv (lines 276-295, 0-indexed 275-294)
# - Duplicate to_tsv (lines 297-316, 0-indexed 296-315)
# - Duplicate to_table (lines 318-384, 0-indexed 317-383)

new_lines = []
line_num = 0

for i, line in enumerate(lines):
    line_num = i + 1
    
    # Skip duplicate to_csv in PyPrefixQueryResult (275-294)
    if 275 <= i <= 294:
        continue
    
    # Skip duplicate to_tsv in PyPrefixQueryResult (296-315)
    if 296 <= i <= 315:
        continue
    
    # Skip duplicate to_table in PyPrefixQueryResult (317-383)
    if 317 <= i <= 383:
        continue
    
    new_lines.append(line)

# Write fixed file
with open('database.rs', 'w') as f:
    f.writelines(new_lines)

print(f"Fixed database.rs (pass 2): removed {len(lines) - len(new_lines)} lines")
print(f"Original: {len(lines)} lines, Fixed: {len(new_lines)} lines")
