//! Unit tests for the stats module

use rustkmer::database::stats::{StreamingStatsProcessor, StatsConfiguration, OutputFormat};
use std::time::Duration;
use std::path::PathBuf;

#[test]
fn test_streaming_stats_processor_basic() {
    let config = StatsConfiguration {
        output_format: OutputFormat::Text,
        detailed: false,
        max_bins: 1000,
        approximate: false,
        show_progress: false,
        output_path: None,
    };

    let mut processor = StreamingStatsProcessor::new(config);

    // Add some test counts
    processor.add_count(1).unwrap();
    processor.add_count(2).unwrap();
    processor.add_count(3).unwrap();
    processor.add_count(2).unwrap();
    processor.add_count(1).unwrap();

    let stats = processor.finalize(
        PathBuf::from("test.rkdb"),
        31,
        false,
        true,
        Duration::from_millis(100),
    );

    assert_eq!(stats.total_kmers, 9); // 1+2+3+2+1
    assert_eq!(stats.unique_kmers, 5);
    assert_eq!(stats.min_count, 1);
    assert_eq!(stats.max_count, 3);
    assert_eq!(stats.mean_count, 1.8);
    assert!(stats.median_count > 1.0 && stats.median_count < 3.0);
    assert_eq!(stats.kmer_size, 31);
    assert!(!stats.canonical);
    assert!(stats.sorted);
    assert!(stats.frequency_distribution.is_none()); // detailed=false
}

#[test]
fn test_streaming_stats_processor_detailed() {
    let config = StatsConfiguration {
        output_format: OutputFormat::Text,
        detailed: true,
        max_bins: 1000,
        approximate: false,
        show_progress: false,
        output_path: None,
    };

    let mut processor = StreamingStatsProcessor::new(config);

    // Add counts with gaps to test zero-filling
    processor.add_count(1).unwrap();
    processor.add_count(5).unwrap();
    processor.add_count(3).unwrap();

    let stats = processor.finalize(
        PathBuf::from("test.rkdb"),
        31,
        true,
        true,
        Duration::from_millis(50),
    );

    assert_eq!(stats.unique_kmers, 3);
    assert_eq!(stats.min_count, 1);
    assert_eq!(stats.max_count, 5);

    // Check frequency distribution has zero-filling
    let freq_dist = stats.frequency_distribution.unwrap();
    assert_eq!(freq_dist.len(), 5); // Should have entries for 1,2,3,4,5

    // Verify the distribution
    let freq_map: std::collections::HashMap<u32, u64> = freq_dist.into_iter().collect();
    assert_eq!(freq_map.get(&1), Some(&1));
    assert_eq!(freq_map.get(&2), Some(&0)); // Zero-filled
    assert_eq!(freq_map.get(&3), Some(&1));
    assert_eq!(freq_map.get(&4), Some(&0)); // Zero-filled
    assert_eq!(freq_map.get(&5), Some(&1));
}

#[test]
fn test_streaming_stats_processor_empty() {
    let config = StatsConfiguration {
        output_format: OutputFormat::Text,
        detailed: true,
        max_bins: 1000,
        approximate: false,
        show_progress: false,
        output_path: None,
    };

    let processor = StreamingStatsProcessor::new(config);
    let stats = processor.finalize(
        PathBuf::from("test.rkdb"),
        31,
        false,
        true,
        Duration::from_millis(10),
    );

    assert_eq!(stats.total_kmers, 0);
    assert_eq!(stats.unique_kmers, 0);
    assert_eq!(stats.min_count, 0); // Special case for empty
    assert_eq!(stats.max_count, 0);
    assert_eq!(stats.mean_count, 0.0);
    assert_eq!(stats.median_count, 0.0);
    assert!(stats.frequency_distribution.is_none()); // Empty database
}

#[test]
fn test_streaming_stats_processor_large_counts() {
    let config = StatsConfiguration {
        output_format: OutputFormat::Text,
        detailed: false,
        max_bins: 100, // Small bin limit
        approximate: true,
        show_progress: false,
        output_path: None,
    };

    let mut processor = StreamingStatsProcessor::new(config);

    // Add many different counts to test bin limiting
    for i in 1..=200 {
        processor.add_count(i).unwrap();
    }

    let stats = processor.finalize(
        PathBuf::from("test.rkdb"),
        31,
        false,
        true,
        Duration::from_millis(200),
    );

    assert_eq!(stats.unique_kmers, 200);
    assert_eq!(stats.min_count, 1);
    assert_eq!(stats.max_count, 200);
    assert!(stats.mean_count > 50.0 && stats.mean_count < 150.0);
}

#[test]
fn test_output_format_variants() {
    // Test that all output format variants can be created
    let formats = vec![
        OutputFormat::Text,
        OutputFormat::Json,
        OutputFormat::Csv,
        OutputFormat::Tsv,
    ];

    for format in formats {
        let config = StatsConfiguration {
            output_format: format.clone(),
            detailed: false,
            max_bins: 1000,
            approximate: false,
            show_progress: false,
            output_path: None,
        };

        assert_eq!(config.output_format, format);
    }
}