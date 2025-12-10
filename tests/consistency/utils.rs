use std::collections::HashMap;
use std::process::Command;

use super::ProcessingStats;

/// Generate test sequences for consistency testing
#[allow(dead_code)]
pub fn generate_test_sequences() -> Vec<String> {
    vec![
        "A".repeat(64),  // Homopoly A
        "C".repeat(64),  // Homopoly C
        "G".repeat(64),  // Homopoly G
        "T".repeat(64),  // Homopoly T
        "ACGT".repeat(16),  // Repeating pattern
        "TTTTGGGGAAAA".repeat(6) + "TTTTGGGGAAAA",  // Mixed pattern
        "N".repeat(64),   // All ambiguous
        "ACGTACGTACGTACGTACGTACGTACGTACGTACGTACGTACGTACGTACGTACGTACGTACGACGT".to_string(),  // 64 with N
        // Edge cases
        "A".to_string(),  // k=1
        "AC".to_string(),  // k=2
        "ACG".to_string(),  // k=3
        "ACGT".repeat(16),  // k=64 exact
    ]
}

/// Parse processing stats from command output
#[allow(dead_code)]
pub fn parse_stats_output(output: &str) -> ProcessingStats {
    let mut stats = ProcessingStats {
        total_sequences: 0,
        valid_kmers: 0,
        skipped_ambiguous: 0,
        skipped_too_short: 0,
        unique_kmers: 0,
        total_count: 0,
    };

    for line in output.lines() {
        if line.contains("Total sequences:") {
            if let Some(num) = line.split(':').nth(1) {
                stats.total_sequences = num.trim().parse().unwrap_or(0);
            }
        } else if line.contains("Valid k-mers:") {
            if let Some(num) = line.split(':').nth(1) {
                stats.valid_kmers = num.trim().parse().unwrap_or(0);
            }
        } else if line.contains("Skipped ambiguous:") {
            if let Some(num) = line.split(':').nth(1) {
                stats.skipped_ambiguous = num.trim().parse().unwrap_or(0);
            }
        } else if line.contains("Skipped too short:") {
            if let Some(num) = line.split(':').nth(1) {
                stats.skipped_too_short = num.trim().parse().unwrap_or(0);
            }
        } else if line.contains("Unique k-mers:") {
            if let Some(num) = line.split(':').nth(1) {
                stats.unique_kmers = num.trim().parse().unwrap_or(0);
            }
        } else if line.contains("Total count:") {
            if let Some(num) = line.split(':').nth(1) {
                stats.total_count = num.trim().parse().unwrap_or(0);
            }
        }
    }

    stats
}

/// Extract k-mer counts from dump output
#[allow(dead_code)]
pub fn parse_kmer_counts(output: &str) -> HashMap<String, u32> {
    let mut counts = HashMap::new();

    for line in output.lines().skip(1) {  // Skip header
        if let Some((kmer, count_str)) = line.split_once('\t') {
            if let Ok(count) = count_str.trim().parse::<u32>() {
                counts.insert(kmer.to_string(), count);
            }
        }
    }

    counts
}

/// Run command and return output
#[allow(dead_code)]
pub fn run_command(cmd: &str, args: &[&str]) -> Result<String, std::io::Error> {
    let output = Command::new(cmd)
        .args(args)
        .output()?;

    Ok(String::from_utf8_lossy(&output.stdout).to_string())
}