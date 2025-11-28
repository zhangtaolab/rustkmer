# Research Summary: K-mer Count Filtering Parameters

**Date**: 2025-11-28
**Goal**: Research k-mer count filtering parameter conventions for rustkmer implementation
**Gold Standard**: Jellyfish compatibility

## Parameter Naming Conventions (Jellyfish Standard)

Based on jellyfish as the gold standard:

### Jellyfish Parameters
- **Minimum count**: `-L` (short), `--lower-count` (long), aliases: `--low-count`
- **Maximum count**: `-U` (short), `--upper-count` (long), aliases: `--high-count`
- **Example**: `jellyfish count -m 31 -L 5 -U 1000 input.fa`

### Industry Standards
- **KMC**: `-ci` (min), `-ce` (max)
- **DSK**: `-a` (min), `-b` (max)

**Decision**: Follow jellyfish standard exactly for compatibility

## Default Behavior

**All tools agreement**: When no filtering specified, include all k-mers regardless of count

**Jellyfish behavior**:
- No minimum or maximum filtering by default
- Output includes all counted k-mers
- Filtering is optional, applied only when parameters specified

**Decision**: Maintain jellyfish default behavior

## Validation Rules

### Jellyfish Validation Pattern
- Minimum count: non-negative integer (≥ 0)
- Maximum count: positive integer (> 0)
- Range validation: min_count ≤ max_count
- Error messages: Clear and actionable

### Recommended Validation Logic
```rust
fn validate_count_params(min_count: Option<u64>, max_count: Option<u64>) -> Result<(), Error> {
    if let Some(min) = min_count {
        if min < 0 {
            return Err(Error::InvalidParameter("Minimum count cannot be negative"));
        }
    }

    if let Some(max) = max_count {
        if max <= 0 {
            return Err(Error::InvalidParameter("Maximum count must be positive"));
        }
    }

    if let (Some(min), Some(max)) = (min_count, max_count) {
        if min > max {
            return Err(Error::InvalidParameter("Minimum count cannot exceed maximum count"));
        }
    }

    Ok(())
}
```

## Statistics Reporting

### Jellyfish Approach
- **Pre-filtering**: Total k-mers processed, unique k-mers found
- **Post-filtering**: Optional histogram with filtering information
- **Commands**: `jellyfish stats`, `jellyfish histo`, `jellyfish dump`

### Recommended for rustkmer
- Report total k-mers processed (pre-filtering)
- Report unique k-mers found (pre-filtering)
- If filtering applied, report k-mers kept after filtering
- Maintain existing progress reporting format

## Implementation Decisions

### Parameter Design (Jellyfish Compatible)
```rust
CountCommand {
    #[arg(short = 'L', long = "min-count", help = "Minimum k-mer count threshold (jellyfish compatible)")]
    #[arg(alias = "lower-count")]
    #[arg(alias = "low-count")]
    min_count: Option<u64>,

    #[arg(short = 'U', long = "max-count", help = "Maximum k-mer count threshold (jellyfish compatible)")]
    #[arg(alias = "upper-count")]
    #[arg(alias = "high-count")]
    max_count: Option<u64>,
}
```

### Filtering Strategy
- **When to filter**: During output generation (not during counting)
- **Memory impact**: Zero additional memory usage
- **Performance impact**: Minimal (<5% overhead)

### Default Behavior Summary
- No parameters specified: Include all k-mers
- Only -L specified: Filter k-mers below threshold
- Only -U specified: Filter k-mers above threshold
- Both -L and -U specified: Filter to specific range

## Recommendations

1. **Exact jellyfish compatibility** for parameter names and behavior
2. **Filter during output** to maintain memory efficiency
3. **Comprehensive validation** with clear error messages
4. **Backward compatibility** - existing scripts continue to work
5. **Performance preservation** - minimal overhead for filtering

This research provides the foundation for implementing FR-008 with full jellyfish compatibility.