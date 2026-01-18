#!/usr/bin/env python3
"""Fix fuzzy_query.rs by adding Debug trait to PyFuzzyMatch"""

# Read file
with open('fuzzy_query.rs', 'r') as f:
    content = f.read()

# Add Debug trait to PyFuzzyMatch
content = content.replace(
    '#[pyclass]\npub struct PyFuzzyMatch {',
    '#[pyclass]\n#[derive(Debug)]\npub struct PyFuzzyMatch {'
)

# Write fixed file
with open('fuzzy_query.rs', 'w') as f:
    f.write(content)

print("Added Debug trait to PyFuzzyMatch")
