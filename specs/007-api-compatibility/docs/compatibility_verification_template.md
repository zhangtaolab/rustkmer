# Compatibility Verification Report Template

**Date**: [YYYY-MM-DD]
**Verifier**: [Name]
**Test Suite**: [Name of test suite]
**Environment**: [Test environment details]

## Executive Summary

- **Overall Status**: [PASS/FAIL/PARTIAL]
- **Tests Run**: [Number]
- **Tests Passed**: [Number]
- **Tests Failed**: [Number]
- **Coverage**: [Percentage]

## Test Results

### Database Format Consistency

#### Test Configuration
- **Input File**: [File path and description]
- **K-mer Size**: [Size]
- **Canonical Mode**: [Yes/No]
- **Iterations**: [Number]

#### Results
| Test Case | CLI Success | Python Success | Files Identical | Status |
|----------|-------------|----------------|----------------|--------|
| [Test 1] | [✓/✗] | [✓/✗] | [✓/✗] | [PASS/FAIL] |
| [Test 2] | [✓/✗] | [✓/✗] | [✓/✗] | [PASS/FAIL] |

#### Performance Metrics
- **CLI Average Time**: [Time in seconds]
- **Python Average Time**: [Time in seconds]
- **Overhead**: [Percentage]

### Query Interoperability

#### Test Configuration
- **Database**: [Database path]
- **Test K-mers**: [List of test k-mers]
- **Iterations**: [Number]

#### Results
| K-mer | CLI Found | Python Found | Count Match | Status |
|-------|----------|---------------|------------|--------|
| [K1] | [✓/✗] | [✓/✗] | [✓/✗] | [PASS/FAIL] |
| [K2] | [✓/✗] | [✓/✗] | [✓/✗] | [PASS/FAIL] |

#### Performance Metrics
- **CLI Average Query Time**: [Time in milliseconds]
- **Python Average Query Time**: [Time in milliseconds]
- **Overhead**: [Percentage]

### Fuzzy Query Consistency

#### Test Configuration
- **Database**: [Database path]
- **Test Patterns**: [List of test patterns]
- **Mutation Tolerance**: [Level]

#### Results
| Pattern | CLI Results | Python Results | Match Status | Status |
|--------|-------------|----------------|-------------|--------|
| [P1] | [Results] | [Results] | [✓/✗] | [PASS/FAIL] |
| [P2] | [Results] | [Results] | [✓/✗] | [PASS/FAIL] |

## Issues Found

### Critical Issues
1. **[Issue Title]**
   - **Description**: [Detailed description]
   - **Impact**: [High/Medium/Low]
   - **Location**: [File/function/module]
   - **Reproduction Steps**: [Steps to reproduce]

### Major Issues
1. **[Issue Title]**
   - **Description**: [Detailed description]
   - **Impact**: [High/Medium/Low]

### Minor Issues
1. **[Issue Title]**
   - **Description**: [Detailed description]
   - **Impact**: [Low]

## Recommendations

### Immediate Actions
1. [Action item with priority]
2. [Action item with priority]

### Code Changes Required
- **File**: [File path]
  - **Change**: [Description of required change]
  - **Priority**: [High/Medium/Low]

### Further Investigation
- [Area]: [Description of area needing further investigation]
- **Reason**: [Why further investigation is needed]

## Performance Analysis

### Overhead Summary
- **Database Creation**: [Percentage] [PASS/FAIL]
- **Query Operations**: [Percentage] [PASS/FAIL]
- **Fuzzy Queries**: [Percentage] [PASS/FAIL]

### Performance Targets
- **<10% overhead for all operations**: [✓/✗]
- **Query rate parity**: [✓/✗]

## Test Environment Details

### System Information
- **OS**: [Operating system]
- **CPU**: [CPU information]
- **Memory**: [Memory information]
- **Python Version**: [Version]
- **RustKmer Version**: [Version]

### Test Data
- **Small Datasets**: [Size and count]
- **Medium Datasets**: [Size and count]
- **Large Datasets**: [Size and count]

## Appendices

### Detailed Test Logs
[Include relevant test logs or error messages]

### Screenshots
[Include relevant screenshots if applicable]

### Raw Data
[Include any raw measurement data]

---
**Report Generated**: [Timestamp]
**Next Review**: [Date for next review]