# Data Model: K-mer Count Filtering Enhancement

**Date**: 2025-11-28
**Purpose**: Define data entities and structures for k-mer count filtering functionality
**Requirement**: FR-008 - Handle sequence filtering based on minimum and maximum count thresholds

## Core Data Entities

### 1. CountFilter

Represents filtering criteria for k-mer counts based on occurrence frequency.

```rust
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct CountFilter {
    /// Minimum count threshold (inclusive)
    /// k-mers with count < min_count will be filtered out
    /// None means no minimum filtering
    pub min_count: Option<u64>,

    /// Maximum count threshold (inclusive)
    /// k-mers with count > max_count will be filtered out
    /// None means no maximum filtering
    pub max_count: Option<u64>,
}
```

### 2. CountFilterConfig

Configuration for count filtering with validation state.

```rust
#[derive(Debug, Clone)]
pub struct CountFilterConfig {
    /// Filter criteria
    pub filter: CountFilter,

    /// Whether filtering is enabled (has any criteria)
    pub enabled: bool,

    /// Validation state
    pub validation_state: ValidationState,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub enum ValidationState {
    /// Configuration is valid
    Valid,
    /// Configuration has validation errors
    Invalid(Vec<String>),
}
```

### 3. FilteringResult

Result of applying filtering to k-mer data.

```rust
#[derive(Debug, Clone)]
pub struct FilteringResult {
    /// Total k-mers before filtering
    pub total_before: u64,

    /// Unique k-mers before filtering
    pub unique_before: u64,

    /// K-mers kept after filtering
    pub kept_after: u64,

    /// K-mers filtered out
    pub filtered_out: u64,

    /// Filter applied
    pub filter: CountFilter,
}
```

## Enhanced KmerCounter Integration

### 4. Enhanced KmerCounter

Extended KmerCounter with filtering capabilities.

```rust
impl KmerCounter {
    /// Get k-mers with filtering applied
    ///
    /// # Arguments
    /// * `filter` - Optional count filter to apply
    ///
    /// # Returns
    /// Vector of (kmer_encoded, count) pairs after filtering
    pub fn get_filtered_kmers(&self, filter: &Option<CountFilter>) -> Vec<(u64, u32)> {
        let all_kmers = self.get_all_counts();

        match filter {
            Some(f) => all_kmers.into_iter()
                .filter(|(_, count)| {
                    let count_u64 = *count as u64;

                    // Check minimum count
                    if let Some(min) = f.min_count {
                        if count_u64 < min {
                            return false;
                        }
                    }

                    // Check maximum count
                    if let Some(max) = f.max_count {
                        if count_u64 > max {
                            return false;
                        }
                    }

                    true
                })
                .collect(),
            None => all_kmers,
        }
    }

    /// Get filtering statistics
    ///
    /// # Arguments
    /// * `filter` - Optional count filter to analyze
    ///
    /// # Returns
    /// FilteringResult with statistics
    pub fn get_filtering_stats(&self, filter: &Option<CountFilter>) -> FilteringResult {
        let all_kmers = self.get_all_counts();
        let total_before = self.total_kmers.load(std::sync::atomic::Ordering::Relaxed);
        let unique_before = all_kmers.len() as u64;

        match filter {
            Some(f) => {
                let kept_after = all_kmers.iter()
                    .filter(|(_, count)| {
                        let count_u64 = *count as u64;

                        // Apply filtering logic
                        let min_ok = f.min_count.map_or(true, |min| count_u64 >= min);
                        let max_ok = f.max_count.map_or(true, |max| count_u64 <= max);

                        min_ok && max_ok
                    })
                    .count() as u64;

                FilteringResult {
                    total_before,
                    unique_before,
                    kept_after,
                    filtered_out: unique_before - kept_after,
                    filter: f.clone(),
                }
            }
            None => FilteringResult {
                total_before,
                unique_before,
                kept_after: unique_before,
                filtered_out: 0,
                filter: CountFilter {
                    min_count: None,
                    max_count: None,
                },
            },
        }
    }
}
```

## CLI Integration Models

### 5. CountCommand Enhancement

Extended command structure for filtering parameters.

```rust
#[derive(Parser)]
pub struct CountCommand {
    /// K-mer size (1-127)
    #[arg(short, long)]
    pub k: usize,

    /// Input sequence files
    #[arg(short, long, num_args = 1..)]
    pub input: Vec<String>,

    /// Output file
    #[arg(short, long)]
    pub output: Option<String>,

    /// Use canonical k-mers (forward/reverse complement)
    #[arg(short = 'C', long)]
    pub canonical: bool,

    /// Hash table size
    #[arg(long, default_value = "1000000")]
    pub size: usize,

    /// Number of threads
    #[arg(short, long, default_value = "0")]
    pub threads: usize,

    /// Output format (binary or text)
    #[arg(long, default_value = "binary")]
    pub format: String,

    /// Quiet mode (suppress progress output)
    #[arg(short, long)]
    pub quiet: bool,

    /// Verbose mode
    #[arg(short, long)]
    pub verbose: bool,

    /// Sort output by k-mer sequence (default: unsorted for performance)
    #[arg(long)]
    pub sort: bool,

    // NEW: Filtering parameters (FR-008)

    /// Minimum k-mer count threshold (jellyfish compatible)
    #[arg(short = 'L', long = "min-count")]
    #[arg(alias = "lower-count")]
    #[arg(alias = "low-count")]
    #[arg(help = "Filter out k-mers with count below this threshold")]
    pub min_count: Option<u64>,

    /// Maximum k-mer count threshold (jellyfish compatible)
    #[arg(short = 'U', long = "max-count")]
    #[arg(alias = "upper-count")]
    #[arg(alias = "high-count")]
    #[arg(help = "Filter out k-mers with count above this threshold")]
    pub max_count: Option<u64>,
}

impl CountCommand {
    /// Create count filter from command parameters
    pub fn create_filter(&self) -> Option<CountFilter> {
        match (self.min_count, self.max_count) {
            (None, None) => None,  // No filtering
            (min, max) => Some(CountFilter { min_count: min, max_count: max }),
        }
    }

    /// Validate filtering parameters
    pub fn validate_filtering(&self) -> Result<(), Vec<String>> {
        let mut errors = Vec::new();

        if let Some(min) = self.min_count {
            if min < 0 {
                errors.push("Minimum count cannot be negative".to_string());
            }
        }

        if let Some(max) = self.max_count {
            if max <= 0 {
                errors.push("Maximum count must be positive".to_string());
            }
        }

        if let (Some(min), Some(max)) = (self.min_count, self.max_count) {
            if min > max {
                errors.push("Minimum count cannot exceed maximum count".to_string());
            }
        }

        if errors.is_empty() {
            Ok(())
        } else {
            Err(errors)
        }
    }
}
```

## Output Processing Models

### 6. FilteredOutputProcessor

Handles output generation with filtering applied.

```rust
pub struct FilteredOutputProcessor {
    pub filter: Option<CountFilter>,
    pub stats: FilteringResult,
}

impl FilteredOutputProcessor {
    /// Create new processor with filter
    pub fn new(filter: Option<CountFilter>, stats: FilteringResult) -> Self {
        Self { filter, stats }
    }

    /// Process k-mers for output with filtering
    pub fn process_kmers<'a>(
        &self,
        kmers: &'a [(u64, u32)]
    ) -> impl Iterator<Item = &'a (u64, u32)> {
        match &self.filter {
            Some(f) => kmers.iter().filter(move |(_, count)| {
                let count_u64 = *count as u64;

                // Apply filtering logic
                let min_ok = f.min_count.map_or(true, |min| count_u64 >= min);
                let max_ok = f.max_count.map_or(true, |max| count_u64 <= max);

                min_ok && max_ok
            }),
            None => kmers.iter(),
        }
    }
}
```

## State Transitions

### 7. Filter State Machine

```
[No Parameters] ──validate─→ [Valid: No Filtering]
     │                              │
     └─add min/max───validate─→ [Valid: With Filtering]
                                   │
                                   └─apply──→ [Filtering Applied]
```

### 8. Validation Flow

```
User Input ──parse─→ Command Structure ──validate─→ Validated Filter
     │                                                    │
     └─error─→ Validation Errors                       └─create─→ CountFilter
```

## Memory and Performance Considerations

### Memory Usage
- **CountFilter**: Minimal (16 bytes)
- **CountFilterConfig**: Minimal (32 bytes)
- **FilteringResult**: Small (32 bytes)
- **No additional memory** during k-mer counting

### Performance Impact
- **Validation**: O(1) - constant time
- **Filtering during output**: O(n) where n = number of unique k-mers
- **Memory overhead**: Zero (filtering applied during iteration)
- **CPU overhead**: <5% expected

## Testing Data Model

### 9. Test Scenarios

```rust
#[cfg(test)]
mod test_models {
    use super::*;

    // Test filtering logic
    #[test]
    fn test_filter_creation() {
        // Test various filter combinations
    }

    #[test]
    fn test_filter_validation() {
        // Test validation rules
    }

    #[test]
    fn test_filtering_application() {
        // Test filtering on sample data
    }

    #[test]
    fn test_statistics_calculation() {
        // Test FilteringResult accuracy
    }
}
```

This data model provides the foundation for implementing FR-008 with full jellyfish compatibility while maintaining memory efficiency and performance.