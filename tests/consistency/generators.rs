use std::collections::HashMap;
use std::fs;
use std::io::Write;

/// Generate test FASTA files for consistency testing
#[allow(dead_code)]
pub fn generate_test_fasta(filename: &str, sequences: Vec<&str>) {
    let mut file = fs::File::create(filename).unwrap();

    for (i, seq) in sequences.iter().enumerate() {
        writeln!(file, ">test_seq_{}", i + 1).unwrap();
        writeln!(file, "{}", seq).unwrap();
    }
}

/// Generate expected k-mer counts for test sequences
#[allow(dead_code)]
pub fn generate_expected_counts(sequences: Vec<&str>, k: usize) -> HashMap<String, u32> {
    let mut counts = HashMap::new();

    for seq in sequences {
        // Skip sequences shorter than k
        if seq.len() < k {
            continue;
        }

        // Extract all k-mers from sequence
        for i in 0..=seq.len() - k {
            let kmer = &seq[i..i + k];

            // Skip if contains ambiguous bases
            if kmer.contains('N') {
                continue;
            }

            *counts.entry(kmer.to_string()).or_insert(0) += 1;
        }
    }

    counts
}

/// Create mixed sequences with various patterns
#[allow(dead_code)]
pub fn create_mixed_sequences() -> Vec<String> {
    vec![
        // Simple repeats
        "A".repeat(32),
        "C".repeat(32),
        "G".repeat(32),
        "T".repeat(32),
        // Alternating patterns
        "AC".repeat(16),
        "AG".repeat(16),
        "AT".repeat(16),
        "CG".repeat(16),
        // Complex patterns
        "ACGTACGTACGTACGTACGTACGTACGTACGTACGTACGTACGTACGTACGTACGTACGTACGACGT".to_string(),
        "TTTTGGGGAAAAACCCCTTTTGGGGGGGAAAAACCCCTTTTGGGGGGGAAAAACCCCTTTTGGGGGGGAAAAACCC".to_string(),
        // With ambiguous bases
        "ACGTACGTACGTACGTACGTACGTACGTACGTACGTACGTACGTACGTACGTACGTACGTACGTACGTACGTACGNN".to_string(),
        // Edge cases
        "A".to_string(),   // Single base
        "AC".to_string(),  // Two bases
        "ACG".to_string(), // Three bases
    ]
}
