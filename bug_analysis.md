# rustkmer Query Bug Analysis

## Problem Summary

The rustkmer query functionality has serious bugs that cause it to fail finding k-mers that are clearly present in the database according to the dump output.

## Key Findings

### 1. Dump vs Query Mismatch
- **Dump shows**: `AAAAAAAAAAAAAAAAAAAAA	1593`, `AAAAAAAAAAAAAAAAAAAAC	137`, `AAAAAAAAAAAAAAAAAAAAG	95`
- **Query finds**: Only the first k-mer with count 57, others return NOT_FOUND
- **Expected**: All three should be found with matching counts

### 2. Count Discrepancies
When k-mers are found by both tools:
- **rustkmer**: 57 occurrences
- **jellyfish**: 879 occurrences
- **Ratio**: ~15x difference

### 3. Test Database Analysis
Small test database with `--canonical` and `sorted=false`:
- Works correctly with memory queries (`--load`)
- Fails with disk queries due to unsorted database (expected behavior)
- Canonical transformation works correctly (AAAAA vs TTTTT both return same count)

### 4. Real Database Properties
- **K-mer size**: 21
- **Total k-mers**: 272,278,487
- **Sorted**: true
- **Canonical**: true
- **Database format**: RKDB

## Root Cause Hypothesis

The most likely causes are:

1. **File offset/corruption issue**: The query may be reading from wrong file positions
2. **Endianness issue**: Similar to the count reading bug fixed earlier
3. **Canonical encoding mismatch**: Between dump output and query lookup
4. **Binary search bug**: In the disk-based query implementation

## Next Steps

1. Verify that dump and query use the same reading functions
2. Check for file offset calculation issues in query code
3. Test with known good k-mers from the beginning of the database
4. Compare the actual byte sequences being stored vs queried

## Impact

This is a critical bug that makes the query functionality essentially unusable for production use.