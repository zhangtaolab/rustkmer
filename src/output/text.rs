//! Text output format for k-mer counts
//!
//! Provides human-readable text format for k-mer counting results.

use crate::error::{ProcessingError, ProcessingResult};
use crate::hash::table::CounterStats;
use crate::kmer::encoding::decode_kmer;
use std::io::Write;

/// Write k-mer counts in text format
///
/// Each line contains: kmer_sequence<TAB>count
///
/// # Arguments
/// * `writer` - Output writer
/// * `kmer_counts` - Vector of (kmer, count) pairs
/// * `kmer_length` - Length of k-mers
/// * `include_header` - Whether to include header information
///
/// # Returns
/// Result indicating success or error
pub fn write_text_format<W: Write>(
    mut writer: W,
    kmer_counts: &[(u64, u32)],
    kmer_length: usize,
    include_header: bool,
) -> ProcessingResult<()> {
    // Write header if requested
    if include_header {
        writeln!(writer, "# rustkmer text format v1")
            .map_err(|e| ProcessingError::with_context("Failed to write header", e))?;
        writeln!(writer, "# kmer_length: {}", kmer_length)
            .map_err(|e| ProcessingError::with_context("Failed to write kmer length", e))?;
        writeln!(writer, "# total_kmers: {}", kmer_counts.len())
            .map_err(|e| ProcessingError::with_context("Failed to write total k-mers", e))?;
        writeln!(writer, "# format: kmer_sequence<TAB>count")
            .map_err(|e| ProcessingError::with_context("Failed to write format description", e))?;
    }

    // Write k-mer counts
    for (kmer, count) in kmer_counts {
        let sequence = decode_kmer(*kmer, kmer_length);
        writeln!(writer, "{}\t{}", sequence, count)
            .map_err(|e| ProcessingError::with_context("Failed to write k-mer count", e))?;
    }

    Ok(())
}

/// Write k-mer counts in JSON format
///
/// # Arguments
/// * `writer` - Output writer
/// * `kmer_counts` - Vector of (kmer, count) pairs
/// * `kmer_length` - Length of k-mers
/// * `stats` - Statistics for metadata
///
/// # Returns
/// Result indicating success or error
pub fn write_json_format<W: Write>(
    mut writer: W,
    kmer_counts: &[(u64, u32)],
    kmer_length: usize,
    stats: &CounterStats,
) -> ProcessingResult<()> {
    writeln!(writer, "{{")
        .map_err(|e| ProcessingError::with_context("Failed to write JSON start", e))?;
    writeln!(writer, "  \"format\": \"rustkmer-json\",")
        .map_err(|e| ProcessingError::with_context("Failed to write format", e))?;
    writeln!(writer, "  \"version\": 1,")
        .map_err(|e| ProcessingError::with_context("Failed to write version", e))?;
    writeln!(writer, "  \"kmer_length\": {},", kmer_length)
        .map_err(|e| ProcessingError::with_context("Failed to write kmer length", e))?;
    writeln!(writer, "  \"canonical_mode\": {},", stats.canonical_mode)
        .map_err(|e| ProcessingError::with_context("Failed to write canonical mode", e))?;
    writeln!(
        writer,
        "  \"total_kmers_processed\": {},",
        stats.total_kmers
    )
    .map_err(|e| ProcessingError::with_context("Failed to write total processed", e))?;
    writeln!(writer, "  \"unique_kmers\": {},", stats.unique_kmers)
        .map_err(|e| ProcessingError::with_context("Failed to write unique count", e))?;
    writeln!(writer, "  \"kmers\": [")
        .map_err(|e| ProcessingError::with_context("Failed to write k-mers start", e))?;

    // Write k-mer counts
    for (i, (kmer, count)) in kmer_counts.iter().enumerate() {
        let sequence = decode_kmer(*kmer, kmer_length);
        let is_last = i == kmer_counts.len() - 1;

        if is_last {
            writeln!(
                writer,
                "    {{\"sequence\": \"{}\", \"count\": {}}}",
                sequence, count
            )
            .map_err(|e| ProcessingError::with_context("Failed to write last k-mer", e))?;
        } else {
            writeln!(
                writer,
                "    {{\"sequence\": \"{}\", \"count\": {}}},",
                sequence, count
            )
            .map_err(|e| ProcessingError::with_context("Failed to write k-mer", e))?;
        }
    }

    writeln!(writer, "  ]")
        .map_err(|e| ProcessingError::with_context("Failed to write k-mers end", e))?;
    writeln!(writer, "}}")
        .map_err(|e| ProcessingError::with_context("Failed to write JSON end", e))?;

    Ok(())
}

/// Write summary statistics only
///
/// # Arguments
/// * `writer` - Output writer
/// * `stats` - Statistics to write
///
/// # Returns
/// Result indicating success or error
pub fn write_summary<W: Write>(mut writer: W, stats: &CounterStats) -> ProcessingResult<()> {
    writeln!(writer, "rustkmer summary:")
        .map_err(|e| ProcessingError::with_context("Failed to write summary header", e))?;
    writeln!(writer, "  K-mer length: {}", stats.kmer_length)
        .map_err(|e| ProcessingError::with_context("Failed to write kmer length", e))?;
    writeln!(writer, "  Canonical mode: {}", stats.canonical_mode)
        .map_err(|e| ProcessingError::with_context("Failed to write canonical mode", e))?;
    writeln!(writer, "  Total k-mers processed: {}", stats.total_kmers)
        .map_err(|e| ProcessingError::with_context("Failed to write total processed", e))?;
    writeln!(writer, "  Unique k-mers: {}", stats.unique_kmers)
        .map_err(|e| ProcessingError::with_context("Failed to write unique count", e))?;

    if stats.total_kmers > 0 {
        let avg_count = stats.total_kmers as f64 / stats.unique_kmers as f64;
        writeln!(writer, "  Average count per k-mer: {:.2}", avg_count)
            .map_err(|e| ProcessingError::with_context("Failed to write average count", e))?;
    }

    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::hash::table::CounterStats;

    #[test]
    fn test_text_format() {
        let kmer_counts = vec![(0x12345678, 10), (0x87654321, 5)];
        let mut output = Vec::new();

        write_text_format(&mut output, &kmer_counts, 8, false).unwrap();

        let result = String::from_utf8(output).unwrap();
        let lines: Vec<&str> = result.lines().collect();

        assert_eq!(lines.len(), 2);
        // Each line should have format: sequence<TAB>count
        assert!(lines[0].contains('\t'));
        assert!(lines[1].contains('\t'));
    }

    #[test]
    fn test_text_format_with_header() {
        let kmer_counts = vec![(0x12345678, 10)];
        let mut output = Vec::new();

        write_text_format(&mut output, &kmer_counts, 8, true).unwrap();

        let result = String::from_utf8(output).unwrap();
        let lines: Vec<&str> = result.lines().collect();

        // Should have header lines plus data
        assert!(lines.len() > 1);
        assert!(lines[0].starts_with("# rustkmer"));
        assert!(lines[1].contains("kmer_length"));
    }

    #[test]
    fn test_summary() {
        let stats = CounterStats {
            total_kmers: 1000,
            unique_kmers: 100,
            kmer_length: 21,
            canonical_mode: true,
        };

        let mut output = Vec::new();
        write_summary(&mut output, &stats).unwrap();

        let result = String::from_utf8(output).unwrap();
        assert!(result.contains("K-mer length: 21"));
        assert!(result.contains("Total k-mers processed: 1000"));
        assert!(result.contains("Unique k-mers: 100"));
        assert!(result.contains("Canonical mode: true"));
        assert!(result.contains("Average count per k-mer: 10.00"));
    }

    #[test]
    fn test_json_format() {
        let kmer_counts = vec![(0x12345678, 10)];
        let stats = CounterStats {
            total_kmers: 100,
            unique_kmers: 50,
            kmer_length: 13,
            canonical_mode: false,
        };

        let mut output = Vec::new();
        write_json_format(&mut output, &kmer_counts, 13, &stats).unwrap();

        let result = String::from_utf8(output).unwrap();
        assert!(result.contains("\"format\": \"rustkmer-json\""));
        assert!(result.contains("\"kmer_length\": 13"));
        assert!(result.contains("\"canonical_mode\": false"));
        assert!(result.contains("\"total_kmers_processed\": 100"));
        assert!(result.contains("\"unique_kmers\": 50"));
        assert!(result.contains("\"kmers\": ["));
    }
}
