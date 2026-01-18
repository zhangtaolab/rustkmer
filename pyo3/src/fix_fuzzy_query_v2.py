#!/usr/bin/env python3
"""Fix fuzzy_query.rs by removing duplicate to_csv and to_tsv methods"""

# Read file
with open('fuzzy_query.rs', 'r') as f:
    lines = f.readlines()

# The first to_csv method (lines 161-206) has format string issues
# The second to_csv method (lines 255-302) is correct
# Similarly for to_tsv

# Remove:
# - First to_csv (lines 161-206, 0-indexed 160-205)
# - First to_tsv (lines 208-253, 0-indexed 207-252)

new_lines = []
for i, line in enumerate(lines):
    # Skip first to_csv (160-205)
    if 160 <= i <= 205:
        continue
    
    # Skip first to_tsv (207-252)
    if 207 <= i <= 252:
        continue
    
    new_lines.append(line)

# Write fixed file
with open('fuzzy_query.rs', 'w') as f:
    f.writelines(new_lines)

print(f"Fixed fuzzy_query.rs: removed {len(lines) - len(new_lines)} lines")
print(f"Original: {len(lines)} lines, Fixed: {len(new_lines)} lines")
