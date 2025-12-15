# Fuzzy Query with N's: Behavior and Best Practices

## Overview

When using fuzzy queries with k-mers containing 'N' characters (wildcards), there are important behavioral differences between the CLI and Python API that users should be aware of. This document explains these differences and provides best practices for working with N's in fuzzy queries.

## Key Finding: Default Mutation Tolerance Difference

The most significant difference between CLI and Python API is the default value for the `mutations` parameter:

- **CLI**: Default `mutations=0` (exact match only)
- **Python API**: Default `mutations=1` (allows 1 mutation by default)

This difference leads to significantly different behavior when querying k-mers with N's.

## Behavior with N's

### What Happens with N's

When a k-mer contains 'N' characters, they are treated as wildcards that can match any nucleotide (A, T, C, G). However, the mutation tolerance determines how many additional positions are allowed to differ:

1. **With mutations=0 (CLI default)**:
   - Only exact matches to the non-N positions are returned
   - All matches will have the exact same sequence in the fixed positions
   - Only the N positions are replaced with other nucleotides

2. **With mutations=1 (Python API default)**:
   - One additional position outside the N region is allowed to mutate
   - This means mutations can occur in the fixed sequences on both sides of the N region
   - Results include matches where the left/right fixed sequences may differ from the query

## Example: Query "GCCGCGNNNNNNNGCCACC"

### CLI Behavior (mutations=0)

```
Query: GCCGCGNNNNNNNGCCACC
Results:
- GCCGCGAAACCGCGCCACC (count: 1)
- GCCGCGAAACTCAGCCACC (count: 1)
- GCCGCGAACGGCGGCCACC (count: 1)
```

All results maintain the fixed sequences "GCCGCG" and "GCCACC" on both sides.

### Python API Behavior (mutations=1)

```
Query: GCCGCGNNNNNNNGCCACC
Results:
- GCCGCGAAACCGCGCCACC (count: 1)  ✓ Fixed sequences maintained
- ACCGCGAAACATCGCCACC (count: 1)  ✗ Left sequence changed
- ACCGCGAAGGAGAGCCACC (count: 1)  ✗ Left sequence changed
- GCCGCGAACTCCGGCCACC (count: 1)  ✓ Fixed sequences maintained
```

Only 4.30% of results maintain the fixed sequences, while 95.70% have mutations in the fixed regions.

## Best Practices

### 1. Explicitly Set mutations=0 for Fixed Sequence Queries

If you want to ensure that fixed sequences remain unchanged when using N's, explicitly set `mutations=0`:

```python
from rustkmer import Database

db_path = "/path/to/database.rkdb"
query_kmer = "GCCGCGNNNNNNNGCCACC"

with Database(db_path) as db:
    # Only allow N's to be replaced, not other positions
    result = db.fuzzy_query(query_kmer, mutations=0, max_variants=9999999999)
    
    # All results will maintain fixed sequences
    for match in result.matches:
        left_seq = match.kmer[:6]  # GCCGCG
        right_seq = match.kmer[-6:]  # GCCACC
        # These will always match the query
```

### 2. Use position_mutations for Precise Control

For more precise control over which positions can mutate, use the `position_mutations` parameter:

```python
# Allow mutations only in the N region (positions 7-13)
position_mutations = "7,8,9,10,11,12,13:5"

result = db.fuzzy_query(
    query_kmer, 
    mutations=5,  # Allow up to 5 mutations in N region
    position_mutations=position_mutations,
    max_variants=9999999999
)
```

### 3. Filter Results After Query

If you need to use the default mutations=1 but want only results with maintained fixed sequences:

```python
with Database(db_path) as db:
    result = db.fuzzy_query(query_kmer, max_variants=9999999999)
    
    # Filter to keep only matches with correct fixed sequences
    filtered_matches = []
    for match in result.matches:
        left_seq = match.kmer[:6]  # GCCGCG
        right_seq = match.kmer[-6:]  # GCCACC
        
        if left_seq == "GCCGCG" and right_seq == "GCCACC":
            filtered_matches.append(match)
    
    print(f"Total matches: {result.total_matches}")
    print(f"Filtered matches (fixed sequences): {len(filtered_matches)}")
```

### 4. Understanding the Trade-offs

- **mutations=0**: 
  - Pros: Fixed sequences always maintained
  - Cons: Fewer total matches (only exact matches to non-N positions)
  - Use case: When you need to find variants but must preserve context

- **mutations=1**:
  - Pros: More total matches (includes near matches)
  - Cons: Fixed sequences may change
  - Use case: When exploring sequence diversity or finding related sequences

## Implementation Details

### N Character Handling

The 'N' character is treated as a wildcard that can match any nucleotide. When generating variants:

1. Each 'N' position can be replaced by A, T, C, or G
2. With mutations=0, only these replacements are allowed
3. With mutations>0, additional positions outside the N region can also mutate

### Variant Generation

The number of variants generated is calculated as:
- For k-mer length k with n N's and m mutations:
  - Variants = 4^n × 3^m (each non-N position has 3 alternatives)
  - This grows combinatorially with both k and m

## Recommendations

1. **For sequence assembly/polishing**: Use `mutations=0` to ensure context is preserved
2. **For variant discovery**: Use `mutations=1` or higher with `position_mutations` to control where mutations occur
3. **For performance**: Use appropriate `max_variants` to limit combinatorial explosion
4. **For reproducibility**: Always document your mutation tolerance and position settings

## Troubleshooting

### Issue: Fixed Sequences Not Maintained

**Symptoms**: Results show different sequences on left/right of N region
**Cause**: Using default `mutations=1` in Python API
**Solution**: Set `mutations=0` explicitly

### Issue: Too Many Results

**Symptoms**: Query returns thousands of unexpected matches
**Cause**: High mutation tolerance with long k-mers
**Solution**: 
1. Use `max_variants` to limit results
2. Use `position_mutations` to restrict mutations to specific positions
3. Consider using exact queries for shorter k-mers

## Conclusion

Understanding the difference between CLI and Python API default behavior is crucial for obtaining expected results when working with k-mers containing N's. Always explicitly specify the `mutations` parameter to match your intended use case.
