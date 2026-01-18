#!/usr/bin/env python3
"""Fix formatter.rs by removing type extensions and duplicate functions"""

# Read file
with open('formatter.rs', 'r') as f:
    lines = f.readlines()

# Keep:
# - Serde wrappers (lines 1-137, 0-indexed 0-136)
# - PyFormatter class (lines 232-292, 0-indexed 231-291)
# - Helper functions (lines 295-316, 0-indexed 294-315)
# - After helper functions, keep until end (should be the rest)

# Remove:
# - PyQueryResult extensions (lines 144-226, 0-indexed 143-225)
# - PyPrefixQueryResult extensions (lines 323-504, 0-indexed 322-503)
# - PyFuzzyResult extensions (lines 511-664, 0-indexed 510-663)
# - PyDatabaseStats extensions (lines 671-761, 0-indexed 670-760)
# - Duplicate functions (lines 763-784, 0-indexed 762-783)

new_lines = []

for i, line in enumerate(lines):
    # Keep Serde wrappers and header (0-136)
    if i <= 136:
        new_lines.append(line)
    # Skip PyQueryResult extensions (143-225)
    elif 143 <= i <= 225:
        continue
    # Keep PyFormatter class (231-291)
    elif 231 <= i <= 291:
        new_lines.append(line)
    # Skip PyPrefixQueryResult extensions (322-503)
    elif 322 <= i <= 503:
        continue
    # Keep helper functions (294-315) - but check if we already passed them
    elif 294 <= i <= 315:
        new_lines.append(line)
    # Skip PyFuzzyResult extensions (510-663)
    elif 510 <= i <= 663:
        continue
    # Skip PyDatabaseStats extensions (670-760)
    elif 670 <= i <= 760:
        continue
    # Skip duplicate functions (762-783)
    elif 762 <= i <= 783:
        continue
    # Skip the blank/comment lines between sections (137-142, 292-293, 316-321, 504-509, 664-669, 761)
    # We'll skip these gaps as they're part of removed sections
    elif (137 <= i <= 142) or (292 <= i <= 293) or (316 <= i <= 321) or (504 <= i <= 509) or (664 <= i <= 669) or i == 761:
        continue
    else:
        # Keep anything else
        new_lines.append(line)

# Write fixed file
with open('formatter.rs', 'w') as f:
    f.writelines(new_lines)

print(f"Fixed formatter.rs: removed {len(lines) - len(new_lines)} lines")
print(f"Original: {len(lines)} lines, Fixed: {len(new_lines)} lines")
