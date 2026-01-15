//! K-mer count filtering functionality
//!
//! Provides filtering structures and logic for k-mer count thresholds.
//! Implements standard -L/-U parameter behavior for count filtering.

/// Filtering criteria for k-mer counts based on occurrence frequency
#[derive(Debug, Clone, PartialEq, Eq, Default)]
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

impl CountFilter {
    /// Create a new count filter
    ///
    /// # Arguments
    /// * `min_count` - Optional minimum count threshold
    /// * `max_count` - Optional maximum count threshold
    ///
    /// # Returns
    /// New CountFilter instance
    pub fn new(min_count: Option<u64>, max_count: Option<u64>) -> Self {
        Self {
            min_count,
            max_count,
        }
    }

    /// Check if a count passes this filter
    ///
    /// # Arguments
    /// * `count` - Count to check
    ///
    /// # Returns
    /// true if count passes the filter, false otherwise
    pub fn passes(&self, count: u64) -> bool {
        // Check minimum count
        if let Some(min) = self.min_count {
            if count < min {
                return false;
            }
        }

        // Check maximum count
        if let Some(max) = self.max_count {
            if count > max {
                return false;
            }
        }

        true
    }
}

/// Configuration for count filtering with validation state
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

impl CountFilterConfig {
    /// Create a new filter configuration with validation
    ///
    /// # Arguments
    /// * `min_count` - Optional minimum count threshold
    /// * `max_count` - Optional maximum count threshold
    ///
    /// # Returns
    /// Validated CountFilterConfig
    pub fn new(min_count: Option<u64>, max_count: Option<u64>) -> Self {
        let filter = CountFilter::new(min_count, max_count);
        let enabled = min_count.is_some() || max_count.is_some();
        let validation_state = Self::validate_parameters(min_count, max_count);

        Self {
            filter,
            enabled,
            validation_state,
        }
    }

    /// Validate filtering parameters
    ///
    /// # Arguments
    /// * `min_count` - Optional minimum count threshold
    /// * `max_count` - Optional maximum count threshold
    ///
    /// # Returns
    /// ValidationState with any errors found
    fn validate_parameters(min_count: Option<u64>, max_count: Option<u64>) -> ValidationState {
        let mut errors = Vec::new();

        if let (Some(min), Some(max)) = (min_count, max_count) {
            if min > max {
                errors.push("Minimum count cannot exceed maximum count".to_string());
            }
        }

        if errors.is_empty() {
            ValidationState::Valid
        } else {
            ValidationState::Invalid(errors)
        }
    }

    /// Check if the configuration is valid
    ///
    /// # Returns
    /// true if valid, false otherwise
    pub fn is_valid(&self) -> bool {
        matches!(self.validation_state, ValidationState::Valid)
    }

    /// Get validation errors if any
    ///
    /// # Returns
    /// Vector of error messages, empty if valid
    pub fn get_errors(&self) -> Vec<String> {
        match &self.validation_state {
            ValidationState::Valid => Vec::new(),
            ValidationState::Invalid(errors) => errors.clone(),
        }
    }
}

/// Result of applying filtering to k-mer data
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

impl FilteringResult {
    /// Create a new filtering result
    ///
    /// # Arguments
    /// * `total_before` - Total k-mers before filtering
    /// * `unique_before` - Unique k-mers before filtering
    /// * `kept_after` - K-mers kept after filtering
    /// * `filter` - Filter that was applied
    ///
    /// # Returns
    /// New FilteringResult instance
    pub fn new(
        total_before: u64,
        unique_before: u64,
        kept_after: u64,
        filter: CountFilter,
    ) -> Self {
        let filtered_out = unique_before.saturating_sub(kept_after);

        Self {
            total_before,
            unique_before,
            kept_after,
            filtered_out,
            filter,
        }
    }

    /// Check if any filtering was applied
    ///
    /// # Returns
    /// true if any k-mers were filtered out
    pub fn has_filtering(&self) -> bool {
        self.filter.min_count.is_some() || self.filter.max_count.is_some()
    }

    /// Get filtering ratio as a percentage
    ///
    /// # Returns
    /// Percentage of k-mers kept (0.0 to 100.0)
    pub fn kept_percentage(&self) -> f64 {
        if self.unique_before == 0 {
            100.0
        } else {
            (self.kept_after as f64 / self.unique_before as f64) * 100.0
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_count_filter_default() {
        let filter = CountFilter::default();
        assert!(filter.passes(0));
        assert!(filter.passes(1));
        assert!(filter.passes(1000));
    }

    #[test]
    fn test_count_filter_min_only() {
        let filter = CountFilter::new(Some(5), None);
        assert!(!filter.passes(4));
        assert!(filter.passes(5));
        assert!(filter.passes(100));
    }

    #[test]
    fn test_count_filter_max_only() {
        let filter = CountFilter::new(None, Some(10));
        assert!(filter.passes(0));
        assert!(filter.passes(10));
        assert!(!filter.passes(11));
    }

    #[test]
    fn test_count_filter_range() {
        let filter = CountFilter::new(Some(5), Some(10));
        assert!(!filter.passes(4));
        assert!(filter.passes(5));
        assert!(filter.passes(7));
        assert!(filter.passes(10));
        assert!(!filter.passes(11));
    }

    #[test]
    fn test_filter_config_valid() {
        let config = CountFilterConfig::new(Some(5), Some(10));
        assert!(config.is_valid());
        assert!(config.enabled);
        assert_eq!(config.get_errors().len(), 0);
    }

    #[test]
    fn test_filter_config_invalid_range() {
        let config = CountFilterConfig::new(Some(10), Some(5));
        assert!(!config.is_valid());
        assert_eq!(config.get_errors().len(), 1);
        assert!(config.get_errors()[0].contains("Minimum count cannot exceed maximum"));
    }

    #[test]
    fn test_filter_config_no_filtering() {
        let config = CountFilterConfig::new(None, None);
        assert!(config.is_valid());
        assert!(!config.enabled);
    }

    #[test]
    fn test_filtering_result() {
        let filter = CountFilter::new(Some(5), None);
        let result = FilteringResult::new(1000, 100, 80, filter);

        assert_eq!(result.total_before, 1000);
        assert_eq!(result.unique_before, 100);
        assert_eq!(result.kept_after, 80);
        assert_eq!(result.filtered_out, 20);
        assert!(result.has_filtering());
        assert_eq!(result.kept_percentage(), 80.0);
    }
}
