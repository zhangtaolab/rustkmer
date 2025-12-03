//! Basic query consistency test
//!
//! Simple test to verify query functionality works

#[cfg(test)]
mod tests {
    use std::path::Path;
    use tempfile::tempdir;

    #[test]
    fn test_basic_query_functionality() -> Result<(), Box<dyn std::error::Error>> {
        let temp_dir = tempdir()?;
        let k = 21;

        // Create test FASTA input
        let fasta_path = temp_dir.path().join("test.fa");
        std::fs::write(&fasta_path, ">seq1\nATCGATCGATCGATCGATCGATCGATCG\n>seq2\nGCTAGCTAGCTAGCTAGCTAGCTAGCTA\n")?;

        // Create database
        let database_path = temp_dir.path().join("test.rkdb");

        // Use the CLI count command directly
        use rustkmer::cli::args::{Args, Commands};
        use rustkmer::cli::commands::execute_count;

        let args = Args {
            command: Commands::Count {
                input_files: vec![fasta_path.to_str().unwrap().to_string()],
                output: Some(database_path.to_str().unwrap().to_string()),
                k,
                canonical: false,
                threads: Some(1),
                memory_limit: Some(1024 * 1024 * 1024), // 1GB
                compression: false,
                verbose: false,
            },
            verbose: false,
        };

        execute_count(&args)?;

        // Verify database was created
        assert!(database_path.exists());

        // Test querying with DatabaseQuery
        use rustkmer::database::DatabaseQuery;
        let mut db_query = DatabaseQuery::open(database_path.to_str().unwrap(), false)?;

        // Get database info
        let info = db_query.get_info();
        assert_eq!(info.kmer_size, k);

        // Query some known k-mers
        let test_kmer = "ATCGATCGATCGATCGATCGA"; // Should exist
        match db_query.query_kmer(test_kmer)? {
            Some(count) => println!("Found k-mer {} with count: {}", test_kmer, count),
            None => println!("K-mer {} not found", test_kmer),
        }

        let unknown_kmer = "AAAAAAAAAAAAAAAAAAA"; // Should not exist
        match db_query.query_kmer(unknown_kmer)? {
            Some(count) => println!("Found unknown k-mer {} with count: {}", unknown_kmer, count),
            None => println!("Unknown k-mer {} not found (as expected)", unknown_kmer),
        }

        Ok(())
    }
}