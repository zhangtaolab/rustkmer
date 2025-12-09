//! Property-based tests for stats module

use proptest::prelude::*;
use rustkmer::database::stats::{StreamingStatsProcessor, StatsConfiguration, OutputFormat};
use std::time::Duration;
use std::path::PathBuf;

proptest! {
    #![proptest_config(ProptestConfig::with_cases(100))]

    #[test]
    fn test_stats_mean_median_invariants(
        counts in prop::collection::vec(1u32..=1000u32, 1..=100)
    ) {
        let config = StatsConfiguration {
            output_format: OutputFormat::Text,
            detailed: false,
            max_bins: 1000,
            approximate: false,
            show_progress: false,
            output_path: None,
        };

        let mut processor = StreamingStatsProcessor::new(config);

        // Track expected values
        let mut expected_total = 0u64;
        let mut expected_unique = counts.len() as u64;
        let mut expected_min = u32::MAX;
        let mut expected_max = 0u32;

        for count in &counts {
            processor.add_count(*count).unwrap();
            expected_total += *count as u64;
            expected_min = expected_min.min(*count);
            expected_max = expected_max.max(*count);
        }

        let stats = processor.finalize(
            PathBuf::from("test.rkdb"),
            31,
            false,
            true,
            Duration::from_millis(100),
        );

        // Property 1: Total k-mers should equal sum of counts
        prop_assert_eq!(stats.total_kmers, expected_total);

        // Property 2: Unique k-mers should equal number of entries
        prop_assert_eq!(stats.unique_kmers, expected_unique);

        // Property 3: Min and max should match expected values
        prop_assert_eq!(stats.min_count, if counts.is_empty() { 0 } else { expected_min });
        prop_assert_eq!(stats.max_count, if counts.is_empty() { 0 } else { expected_max });

        // Property 4: Mean should be between min and max (or 0 for empty)
        if !counts.is_empty() {
            prop_assert!(stats.mean_count >= stats.min_count as f64);
            prop_assert!(stats.mean_count <= stats.max_count as f64);
        } else {
            prop_assert_eq!(stats.mean_count, 0.0);
        }

        // Property 5: Median should be between min and max (or 0 for empty)
        if !counts.is_empty() {
            prop_assert!(stats.median_count >= stats.min_count as f64);
            prop_assert!(stats.median_count <= stats.max_count as f64);
        } else {
            prop_assert_eq!(stats.median_count, 0.0);
        }
    }

    #[test]
    fn test_frequency_distribution_properties(
        counts in prop::collection::vec(1u32..=20u32, 1..=50)
    ) {
        let config = StatsConfiguration {
            output_format: OutputFormat::Text,
            detailed: true,
            max_bins: 1000,
            approximate: false,
            show_progress: false,
            output_path: None,
        };

        let mut processor = StreamingStatsProcessor::new(config);

        for count in &counts {
            processor.add_count(*count).unwrap();
        }

        let stats = processor.finalize(
            PathBuf::from("test.rkdb"),
            31,
            false,
            true,
            Duration::from_millis(100),
        );

        if !counts.is_empty() {
            // Property 1: Frequency distribution should exist
            prop_assert!(stats.frequency_distribution.is_some());

            let freq_dist = stats.frequency_distribution.unwrap();

            // Property 2: Should have entries from min to max count
            prop_assert_eq!(freq_dist.len() as u32, stats.max_count - stats.min_count + 1);

            // Property 3: Sum of frequencies should equal unique k-mers
            let total_freq: u64 = freq_dist.iter().map(|(_, f)| *f).sum();
            prop_assert_eq!(total_freq, stats.unique_kmers);

            // Property 4: Actual counts should match frequencies
            let mut expected_counts = std::collections::HashMap::new();
            for count in &counts {
                *expected_counts.entry(*count).or_insert(0) += 1;
            }

            for (count, freq) in freq_dist {
                if let Some(expected) = expected_counts.get(&count) {
                    prop_assert_eq!(*freq, *expected);
                } else {
                    // Should be zero-filled
                    prop_assert_eq!(*freq, 0);
                }
            }
        } else {
            // Empty database should not have frequency distribution
            prop_assert!(stats.frequency_distribution.is_none());
        }
    }

    #[test]
    fn test_monotonic_properties(
        counts in prop::collection::vec(1u32..=100u32, 10..=100)
    ) {
        // Test that adding more counts never decreases any statistic
        let config = StatsConfiguration {
            output_format: OutputFormat::Text,
            detailed: false,
            max_bins: 1000,
            approximate: false,
            show_progress: false,
            output_path: None,
        };

        let mut processor = StreamingStatsProcessor::new(config.clone());

        // Split into two halves
        let mid = counts.len() / 2;
        let first_half = &counts[..mid];
        let second_half = &counts[mid..];

        // Process first half
        for count in first_half {
            processor.add_count(*count).unwrap();
        }

        let stats1 = processor.finalize(
            PathBuf::from("test.rkdb"),
            31,
            false,
            true,
            Duration::from_millis(100),
        );

        // Process all counts
        let mut processor2 = StreamingStatsProcessor::new(config);
        for count in &counts {
            processor2.add_count(*count).unwrap();
        }

        let stats2 = processor2.finalize(
            PathBuf::from("test.rkdb"),
            31,
            false,
            true,
            Duration::from_millis(100),
        );

        // Property: Adding more data should not decrease these metrics
        prop_assert!(stats2.total_kmers >= stats1.total_kmers);
        prop_assert!(stats2.unique_kmers >= stats1.unique_kmers);
        prop_assert!(stats2.max_count >= stats1.max_count);
    }

    #[test]
    fn test_count_preservation(
        counts in prop::collection::vec(1u32..=50u32, 1..=50)
    ) {
        // Test that the sum of all counts equals total_kmers
        let config = StatsConfiguration {
            output_format: OutputFormat::Text,
            detailed: false,
            max_bins: 1000,
            approximate: false,
            show_progress: false,
            output_path: None,
        };

        let mut processor = StreamingStatsProcessor::new(config);

        let expected_sum: u64 = counts.iter().map(|&c| c as u64).sum();

        for count in &counts {
            processor.add_count(*count).unwrap();
        }

        let stats = processor.finalize(
            PathBuf::from("test.rkdb"),
            31,
            false,
            true,
            Duration::from_millis(100),
        );

        // Property: total_kmers should equal sum of all added counts
        prop_assert_eq!(stats.total_kmers, expected_sum);

        // Property: unique_kmers should equal number of entries
        prop_assert_eq!(stats.unique_kmers, counts.len() as u64);
    }
}