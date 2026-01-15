//! Integration tests for the stats command

use std::fs;
use std::path::Path;
use std::process::Command;

/// Helper function to run rustkmer stats command
fn run_stats_command(args: &[&str]) -> (String, i32) {
    let mut cmd = Command::new("./target/debug/rustkmer");
    cmd.args(args);

    let output = cmd.output().expect("Failed to execute rustkmer stats");
    let stdout = String::from_utf8(output.stdout).unwrap();
    let stderr = String::from_utf8(output.stderr).unwrap();
    let exit_code = output.status.code().unwrap();

    // Combine stdout and stderr for easier debugging
    let combined = if !stderr.is_empty() {
        format!("{}\n{}", stdout, stderr)
    } else {
        stdout
    };

    (combined, exit_code)
}

/// Helper to create a test database
fn create_test_database(name: &str, sequences: &[&str], k: usize) -> std::path::PathBuf {
    let temp_dir = std::env::temp_dir();
    let fasta_path = temp_dir.join(format!("{}_{}.fa", name, k));
    let rkdb_path = temp_dir.join(format!("{}_{}.rkdb", name, k));

    // Create FASTA file
    let mut fasta_content = String::new();
    for (i, seq) in sequences.iter().enumerate() {
        fasta_content.push_str(&format!(">seq{}\n{}\n", i, seq));
    }
    fs::write(&fasta_path, fasta_content).unwrap();

    // Create database
    let output = Command::new("./target/debug/rustkmer")
        .args(&[
            "count",
            "-k",
            &k.to_string(),
            "-i",
            fasta_path.to_str().unwrap(),
            "-o",
            rkdb_path.to_str().unwrap(),
        ])
        .output()
        .expect("Failed to create test database");

    if !output.status.success() {
        panic!(
            "Failed to create test database: {}",
            String::from_utf8_lossy(&output.stderr)
        );
    }

    // Clean up FASTA file
    fs::remove_file(&fasta_path).unwrap();

    rkdb_path
}

#[test]
fn test_stats_basic_functionality() {
    let rkdb_path = create_test_database(
        "stats_basic",
        &[
            "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA",   // 30-mers, all A's
            "CCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCC",   // 30-mers, all C's
            "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA",   // Duplicate
            "CCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCC",   // Duplicate
            "GGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGG", // 30-mers, all G's
        ],
        30,
    );

    let (output, exit_code) = run_stats_command(&["stats", rkdb_path.to_str().unwrap()]);

    assert_eq!(
        exit_code, 0,
        "Stats command failed with output:\n{}",
        output
    );

    // Check that key statistics are present
    assert!(output.contains("Database Statistics"));
    assert!(output.contains("K-mer size: 30"));
    assert!(output.contains("Total k-mers: 30")); // 6 sequences * 5 k-mers each (with overlap)
    assert!(output.contains("Unique k-mers: 3"));
    assert!(output.contains("Min count: 5"));
    assert!(output.contains("Max count: 10"));
    assert!(output.contains("Mean count:"));

    // Clean up
    fs::remove_file(rkdb_path.to_str().unwrap()).unwrap();
}

#[test]
fn test_stats_detailed_output() {
    let rkdb_path = create_test_database(
        "stats_detailed",
        &[
            "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA", // Count: 5
            "CCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCC", // Count: 5
            "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA", // Count: 6
            "CCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCC", // Count: 6
        ],
        30,
    );

    let (output, exit_code) =
        run_stats_command(&["stats", "--detailed", rkdb_path.to_str().unwrap()]);

    assert_eq!(
        exit_code, 0,
        "Stats command failed with output:\n{}",
        output
    );

    // Check that frequency distribution is present
    assert!(output.contains("Frequency Distribution:"));
    assert!(output.contains("Count\tFrequency"));
    assert!(output.contains("5\t2")); // Two k-mers with count 5
    assert!(output.contains("6\t2")); // Two k-mers with count 6

    // Clean up
    fs::remove_file(rkdb_path.to_str().unwrap()).unwrap();
}

#[test]
fn test_stats_json_output() {
    let rkdb_path = create_test_database("stats_json", &["AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"], 30);

    let (output, exit_code) =
        run_stats_command(&["stats", "--format", "json", rkdb_path.to_str().unwrap()]);

    assert_eq!(
        exit_code, 0,
        "Stats command failed with output:\n{}",
        output
    );

    // Parse as JSON
    let json: serde_json::Value = serde_json::from_str(&output).expect("Invalid JSON output");

    // Check required fields
    assert!(json.get("database_file").is_some());
    assert!(json.get("kmer_size").is_some());
    assert!(json.get("total_kmers").is_some());
    assert!(json.get("unique_kmers").is_some());
    assert!(json.get("min_count").is_some());
    assert!(json.get("max_count").is_some());
    assert!(json.get("mean_count").is_some());
    assert!(json.get("median_count").is_some());
    assert!(json.get("processing_time").is_some());

    // Clean up
    fs::remove_file(rkdb_path.to_str().unwrap()).unwrap();
}

#[test]
fn test_stats_csv_output() {
    let rkdb_path = create_test_database("stats_csv", &["AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"], 30);

    let (output, exit_code) =
        run_stats_command(&["stats", "--format", "csv", rkdb_path.to_str().unwrap()]);

    assert_eq!(
        exit_code, 0,
        "Stats command failed with output:\n{}",
        output
    );

    // Check CSV header
    assert!(output.contains("database_file"));
    assert!(output.contains("kmer_size"));
    assert!(output.contains("total_kmers"));
    assert!(output.contains("unique_kmers"));
    assert!(output.contains("processing_time"));

    // Clean up
    fs::remove_file(rkdb_path.to_str().unwrap()).unwrap();
}

#[test]
fn test_stats_tsv_output() {
    let rkdb_path = create_test_database("stats_tsv", &["AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"], 30);

    let (output, exit_code) =
        run_stats_command(&["stats", "--format", "tsv", rkdb_path.to_str().unwrap()]);

    assert_eq!(
        exit_code, 0,
        "Stats command failed with output:\n{}",
        output
    );

    // TSV should have tabs, not commas
    assert!(!output.contains(","));
    assert!(output.contains("\t"));

    // Clean up
    fs::remove_file(rkdb_path.to_str().unwrap()).unwrap();
}

#[test]
fn test_stats_output_to_file() {
    let rkdb_path = create_test_database("stats_file", &["AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"], 30);
    let temp_dir = std::env::temp_dir();
    let output_path = temp_dir.join("stats_output.txt");

    let (_output, exit_code) = run_stats_command(&[
        "stats",
        "-o",
        output_path.to_str().unwrap(),
        rkdb_path.to_str().unwrap(),
    ]);

    assert_eq!(exit_code, 0, "Stats command failed");

    // Check that file was created and contains expected content
    assert!(Path::new(output_path).exists());
    let file_content = fs::read_to_string(output_path).unwrap();
    assert!(file_content.contains("Database Statistics"));

    // Clean up
    fs::remove_file(rkdb_path.to_str().unwrap()).unwrap();
    fs::remove_file(output_path).unwrap();
}

#[test]
fn test_stats_nonexistent_file() {
    let (_output, exit_code) = run_stats_command(&["stats", "/nonexistent/database.rkdb"]);

    assert_ne!(
        exit_code, 0,
        "Expected non-zero exit code for nonexistent file"
    );
}

#[test]
fn test_stats_invalid_format() {
    let rkdb_path =
        create_test_database("stats_invalid", &["AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"], 30);

    let (_output, exit_code) =
        run_stats_command(&["stats", "--format", "invalid", rkdb_path.to_str().unwrap()]);

    assert_ne!(
        exit_code, 0,
        "Expected non-zero exit code for invalid format"
    );

    // Clean up
    fs::remove_file(rkdb_path.to_str().unwrap()).unwrap();
}
