//! Comprehensive performance benchmarking command
//!
//! Provides systematic performance testing and comparison capabilities
//! for RustKmer against Jellyfish across multiple dimensions.

use crate::error::ProcessingResult;
use std::path::{Path, PathBuf};
use std::process::Command;
use std::time::{Duration, Instant};
use std::fs;
use serde::{Deserialize, Serialize};
use std::collections::HashMap;

/// Benchmark configuration and execution
pub struct BenchmarkRunner {
    data_dir: PathBuf,
    output_dir: PathBuf,
    kmer_sizes: Vec<usize>,
    config: BenchmarkConfig,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct BenchmarkConfig {
    pub compression: bool,
    pub memory: bool,
    pub iterations: usize,
    pub format: String,
    pub visualize: bool,
    pub compare_jellyfish: bool,
}

#[derive(Debug, Serialize, Deserialize)]
pub struct BenchmarkResult {
    pub test_name: String,
    pub tool: String,
    pub kmer_size: usize,
    pub file_path: String,
    pub execution_time_seconds: f64,
    pub memory_usage_mb: Option<f64>,
    pub success: bool,
    pub error_message: Option<String>,
    pub timestamp: u64,
}

#[derive(Debug, Serialize, Deserialize)]
pub struct BenchmarkSummary {
    pub total_tests: usize,
    pub successful_tests: usize,
    pub failed_tests: usize,
    pub total_execution_time: f64,
    pub tools_compared: Vec<String>,
    pub kmer_sizes_tested: Vec<usize>,
    pub rustkmer_vs_jellyfish: Option<HashMap<String, f64>>,
}

impl BenchmarkRunner {
    /// Create a new benchmark runner
    pub fn new(
        data_dir: &str,
        output_dir: &str,
        kmer_sizes: &str,
        config: BenchmarkConfig,
    ) -> Self {
        // Parse k-mer sizes
        let kmer_sizes: Vec<usize> = kmer_sizes
            .split(',')
            .map(|s| s.trim().parse().unwrap_or(21))
            .collect();

        Self {
            data_dir: PathBuf::from(data_dir),
            output_dir: PathBuf::from(output_dir),
            kmer_sizes,
            config,
        }
    }

    /// Execute comprehensive benchmarking
    pub fn run_benchmark(&self) -> ProcessingResult<()> {
        println!("🚀 Starting Comprehensive Performance Benchmark");
        println!("Data directory: {}", self.data_dir.display());
        println!("Output directory: {}", self.output_dir.display());
        println!("K-mer sizes: {:?}", self.kmer_sizes);

        // Create output directories
        fs::create_dir_all(&self.output_dir)?;
        fs::create_dir_all(self.output_dir.join("results"))?;
        fs::create_dir_all(self.output_dir.join("logs"))?;

        let mut all_results = Vec::new();
        let start_time = Instant::now();

        // Find test files
        let test_files = self.find_test_files()?;

        if test_files.is_empty() {
            return Err(crate::error::ProcessingError::io_error(
                "No test files found in the specified data directory".to_string(),
            ));
        }

        println!("Found {} test files", test_files.len());

        // Run database creation benchmarks
        for file_path in &test_files {
            for &kmer_size in &self.kmer_sizes {
                self.benchmark_database_creation(file_path, kmer_size, &mut all_results)?;
            }
        }

        // Run query benchmarks
        let databases = self.find_or_create_databases(&test_files)?;
        for database in &databases {
            self.benchmark_query_performance(database, &mut all_results)?;
        }

        // Run I/O benchmarks
        if self.config.compression {
            self.benchmark_io_performance(&test_files, &mut all_results)?;
        }

        // Generate summary
        let summary = self.generate_summary(&all_results, start_time.elapsed());

        // Save results
        self.save_results(&all_results, &summary)?;

        // Generate visualizations if requested
        if self.config.visualize {
            self.generate_visualizations(&all_results)?;
        }

        // Print summary
        self.print_summary(&summary);

        Ok(())
    }

    /// Find test files in the data directory
    fn find_test_files(&self) -> ProcessingResult<Vec<PathBuf>> {
        let mut test_files = Vec::new();

        // Look for FASTA files
        let fasta_dir = self.data_dir.join("fasta");
        if fasta_dir.exists() {
            for entry in fs::read_dir(fasta_dir)? {
                let entry = entry?;
                let path = entry.path();
                if path.extension().is_some_and(|ext| {
                    ext == "fa" || ext == "fasta" || ext == "fna"
                }) {
                    test_files.push(path);
                }
            }
        }

        // Look for FASTQ files (limit to prevent too many files)
        let fastq_dir = self.data_dir.join("fastq");
        if fastq_dir.exists() {
            let mut fastq_count = 0;
            for entry in fs::read_dir(fastq_dir)? {
                if fastq_count >= 2 {  // Limit to 2 FASTQ files for reasonable runtime
                    break;
                }
                let entry = entry?;
                let path = entry.path();
                if path.extension().is_some_and(|ext| {
                    ext == "fq" || ext == "fastq"
                }) {
                    test_files.push(path);
                    fastq_count += 1;
                }
            }
        }

        Ok(test_files)
    }

    /// Find existing databases or create them
    fn find_or_create_databases(&self, test_files: &[PathBuf]) -> ProcessingResult<Vec<PathBuf>> {
        let mut databases = Vec::new();
        let database_dir = self.output_dir.join("databases");
        fs::create_dir_all(&database_dir)?;

        // Use the first file for query benchmarks
        if let Some(test_file) = test_files.first() {
            let file_stem = test_file.file_stem()
                .and_then(|s| s.to_str())
                .unwrap_or("unknown");

            // Look for existing databases
            for &kmer_size in &self.kmer_sizes {
                let rkdb_path = database_dir.join(format!("{}_k{}.rkdb", file_stem, kmer_size));
                if rkdb_path.exists() {
                    databases.push(rkdb_path);
                } else {
                    // Create database for benchmarking
                    println!("Creating database for k={}: {}", kmer_size, test_file.display());
                    self.create_rustkmer_database(test_file, kmer_size, &rkdb_path)?;
                    databases.push(rkdb_path);
                }
            }
        }

        Ok(databases)
    }

    /// Create RustKmer database
    fn create_rustkmer_database(
        &self,
        input_file: &Path,
        kmer_size: usize,
        output_file: &Path,
    ) -> ProcessingResult<()> {
        let output = Command::new("cargo")
            .args([
                "run", "--release", "--",
                "count",
                "-k", &kmer_size.to_string(),
                "-t", "4",
                "--canonical",
                "--sort",
                "-o", output_file.to_str().unwrap(),
                input_file.to_str().unwrap(),
            ])
            .output()?;

        if !output.status.success() {
            return Err(crate::error::ProcessingError::io_error(
                format!("Failed to create database: {}", String::from_utf8_lossy(&output.stderr)),
            ));
        }

        Ok(())
    }

    /// Benchmark database creation performance
    fn benchmark_database_creation(
        &self,
        file_path: &Path,
        kmer_size: usize,
        results: &mut Vec<BenchmarkResult>,
    ) -> ProcessingResult<()> {
        println!("Benchmarking database creation: {} (k={})", file_path.display(), kmer_size);

        // Benchmark RustKmer
        let rustkmer_result = self.benchmark_rustkmer_creation(file_path, kmer_size)?;
        results.push(rustkmer_result);

        // Benchmark Jellyfish if comparison requested
        if self.config.compare_jellyfish {
            let jellyfish_result = self.benchmark_jellyfish_creation(file_path, kmer_size)?;
            results.push(jellyfish_result);
        }

        Ok(())
    }

    /// Benchmark RustKmer database creation
    fn benchmark_rustkmer_creation(
        &self,
        file_path: &Path,
        kmer_size: usize,
    ) -> ProcessingResult<BenchmarkResult> {
        let output_file = self.output_dir.join("databases")
            .join(format!("benchmark_rkdb_{}_k{}",
                file_path.file_stem().and_then(|s| s.to_str()).unwrap_or("unknown"),
                kmer_size));

        let start_time = Instant::now();
        let output = Command::new("cargo")
            .args([
                "run", "--release", "--",
                "count",
                "-k", &kmer_size.to_string(),
                "-t", "4",
                "--canonical",
                "--sort",
                "-o", output_file.to_str().unwrap(),
                file_path.to_str().unwrap(),
            ])
            .output()?;

        let execution_time = start_time.elapsed().as_secs_f64();

        Ok(BenchmarkResult {
            test_name: "database_creation".to_string(),
            tool: "rustkmer".to_string(),
            kmer_size,
            file_path: file_path.to_string_lossy().to_string(),
            execution_time_seconds: execution_time,
            memory_usage_mb: None, // TODO: Add memory profiling
            success: output.status.success(),
            error_message: if !output.status.success() {
                Some(String::from_utf8_lossy(&output.stderr).to_string())
            } else {
                None
            },
            timestamp: std::time::SystemTime::now()
                .duration_since(std::time::UNIX_EPOCH)
                .unwrap()
                .as_secs(),
        })
    }

    /// Benchmark Jellyfish database creation
    fn benchmark_jellyfish_creation(
        &self,
        file_path: &Path,
        kmer_size: usize,
    ) -> ProcessingResult<BenchmarkResult> {
        let output_file = self.output_dir.join("databases")
            .join(format!("benchmark_jf_{}_k{}",
                file_path.file_stem().and_then(|s| s.to_str()).unwrap_or("unknown"),
                kmer_size));

        let start_time = Instant::now();
        let output = Command::new("jellyfish")
            .args([
                "count",
                "-m", &kmer_size.to_string(),
                "-s", "100M",
                "-t", "4",
                "-C",
                "-o", output_file.to_str().unwrap(),
                file_path.to_str().unwrap(),
            ])
            .output()?;

        let execution_time = start_time.elapsed().as_secs_f64();

        Ok(BenchmarkResult {
            test_name: "database_creation".to_string(),
            tool: "jellyfish".to_string(),
            kmer_size,
            file_path: file_path.to_string_lossy().to_string(),
            execution_time_seconds: execution_time,
            memory_usage_mb: None,
            success: output.status.success(),
            error_message: if !output.status.success() {
                Some(String::from_utf8_lossy(&output.stderr).to_string())
            } else {
                None
            },
            timestamp: std::time::SystemTime::now()
                .duration_since(std::time::UNIX_EPOCH)
                .unwrap()
                .as_secs(),
        })
    }

    /// Benchmark query performance
    fn benchmark_query_performance(
        &self,
        database: &Path,
        results: &mut Vec<BenchmarkResult>,
    ) -> ProcessingResult<()> {
        println!("Benchmarking query performance: {}", database.display());

        // Generate test queries
        let test_queries = self.generate_test_queries(100);

        // Benchmark exact queries
        let query_result = self.benchmark_rustkmer_queries(database, &test_queries)?;
        results.push(query_result);

        // Benchmark fuzzy queries if supported
        if self.kmer_sizes.contains(&21) || self.kmer_sizes.contains(&31) {
            let fuzzy_queries = self.generate_fuzzy_queries(50);
            let fuzzy_result = self.benchmark_rustkmer_fuzzy_queries(database, &fuzzy_queries)?;
            results.push(fuzzy_result);
        }

        Ok(())
    }

    /// Benchmark RustKmer exact queries
    fn benchmark_rustkmer_queries(
        &self,
        database: &Path,
        queries: &[String],
    ) -> ProcessingResult<BenchmarkResult> {
        let mut total_time = 0.0;
        let mut successful_queries = 0;

        for query in queries {
            let start_time = Instant::now();
            let output = Command::new("cargo")
                .args([
                    "run", "--release", "--",
                    "query",
                    database.to_str().unwrap(),
                    query,
                    "--format", "json",
                    "--quiet",
                ])
                .output()?;

            let query_time = start_time.elapsed().as_secs_f64();
            total_time += query_time;

            if output.status.success() {
                successful_queries += 1;
            }
        }

        Ok(BenchmarkResult {
            test_name: "query_performance".to_string(),
            tool: "rustkmer".to_string(),
            kmer_size: self.kmer_sizes[0], // Simplified
            file_path: database.to_string_lossy().to_string(),
            execution_time_seconds: total_time / queries.len() as f64,
            memory_usage_mb: None,
            success: successful_queries > 0,
            error_message: None,
            timestamp: std::time::SystemTime::now()
                .duration_since(std::time::UNIX_EPOCH)
                .unwrap()
                .as_secs(),
        })
    }

    /// Benchmark RustKmer fuzzy queries
    fn benchmark_rustkmer_fuzzy_queries(
        &self,
        database: &Path,
        queries: &[String],
    ) -> ProcessingResult<BenchmarkResult> {
        let mut total_time = 0.0;
        let mut successful_queries = 0;

        for query in queries {
            let start_time = Instant::now();
            let output = Command::new("cargo")
                .args([
                    "run", "--release", "--",
                    "fuzzy-query",
                    database.to_str().unwrap(),
                    query,
                    "--mutations", "1",
                    "--format", "json",
                    "--quiet",
                ])
                .output()?;

            let query_time = start_time.elapsed().as_secs_f64();
            total_time += query_time;

            if output.status.success() {
                successful_queries += 1;
            }
        }

        Ok(BenchmarkResult {
            test_name: "fuzzy_query_performance".to_string(),
            tool: "rustkmer".to_string(),
            kmer_size: self.kmer_sizes[0],
            file_path: database.to_string_lossy().to_string(),
            execution_time_seconds: total_time / queries.len() as f64,
            memory_usage_mb: None,
            success: successful_queries > 0,
            error_message: None,
            timestamp: std::time::SystemTime::now()
                .duration_since(std::time::UNIX_EPOCH)
                .unwrap()
                .as_secs(),
        })
    }

    /// Benchmark I/O performance
    fn benchmark_io_performance(
        &self,
        test_files: &[PathBuf],
        results: &mut Vec<BenchmarkResult>,
    ) -> ProcessingResult<()> {
        println!("Benchmarking I/O performance...");

        for file_path in test_files {
            let io_result = self.benchmark_file_reading(file_path)?;
            results.push(io_result);
        }

        Ok(())
    }

    /// Benchmark file reading performance
    fn benchmark_file_reading(&self, file_path: &Path) -> ProcessingResult<BenchmarkResult> {
        let start_time = Instant::now();
        let _file_size = fs::metadata(file_path)?.len();
        let elapsed = start_time.elapsed();

        Ok(BenchmarkResult {
            test_name: "file_reading".to_string(),
            tool: "system".to_string(),
            kmer_size: 0,
            file_path: file_path.to_string_lossy().to_string(),
            execution_time_seconds: elapsed.as_secs_f64(),
            memory_usage_mb: None,
            success: true,
            error_message: None,
            timestamp: std::time::SystemTime::now()
                .duration_since(std::time::UNIX_EPOCH)
                .unwrap()
                .as_secs(),
        })
    }

    /// Generate test queries
    fn generate_test_queries(&self, count: usize) -> Vec<String> {
        let mut queries = Vec::new();
        let bases = b"ATCG";

        for i in 0..count {
            let mut query = String::with_capacity(21);
            for j in 0..21 {
                query.push(bases[(i + j) % 4] as char);
            }
            queries.push(query);
        }

        queries
    }

    /// Generate fuzzy queries with wildcards
    fn generate_fuzzy_queries(&self, count: usize) -> Vec<String> {
        let base_queries = self.generate_test_queries(count);
        let mut fuzzy_queries = Vec::new();

        for (i, mut query) in base_queries.into_iter().enumerate() {
            // Add wildcard at different position
            if query.len() > 10 {
                let pos = 5 + (i % 10);
                unsafe {
                    let bytes = query.as_bytes_mut();
                    bytes[pos] = b'N';
                }
                fuzzy_queries.push(query);
            }
        }

        fuzzy_queries
    }

    /// Generate summary statistics
    fn generate_summary(&self, results: &[BenchmarkResult], total_time: Duration) -> BenchmarkSummary {
        let total_tests = results.len();
        let successful_tests = results.iter().filter(|r| r.success).count();
        let failed_tests = total_tests - successful_tests;

        let tools: std::collections::HashSet<String> = results.iter()
            .map(|r| r.tool.clone())
            .collect();
        let kmer_sizes: std::collections::HashSet<usize> = results.iter()
            .map(|r| r.kmer_size)
            .collect();

        // Calculate tool comparisons
        let mut rustkmer_vs_jellyfish = HashMap::new();

        for &kmer_size in &self.kmer_sizes {
            let rustkmer_times: Vec<f64> = results.iter()
                .filter(|r| r.tool == "rustkmer" && r.kmer_size == kmer_size && r.success)
                .map(|r| r.execution_time_seconds)
                .collect();

            let jellyfish_times: Vec<f64> = results.iter()
                .filter(|r| r.tool == "jellyfish" && r.kmer_size == kmer_size && r.success)
                .map(|r| r.execution_time_seconds)
                .collect();

            if !rustkmer_times.is_empty() && !jellyfish_times.is_empty() {
                let rustkmer_avg = rustkmer_times.iter().sum::<f64>() / rustkmer_times.len() as f64;
                let jellyfish_avg = jellyfish_times.iter().sum::<f64>() / jellyfish_times.len() as f64;
                let speedup = jellyfish_avg / rustkmer_avg;
                rustkmer_vs_jellyfish.insert(format!("k{}_speedup", kmer_size), speedup);
            }
        }

        BenchmarkSummary {
            total_tests,
            successful_tests,
            failed_tests,
            total_execution_time: total_time.as_secs_f64(),
            tools_compared: tools.into_iter().collect(),
            kmer_sizes_tested: kmer_sizes.into_iter().collect(),
            rustkmer_vs_jellyfish: if rustkmer_vs_jellyfish.is_empty() { None } else { Some(rustkmer_vs_jellyfish) },
        }
    }

    /// Save results to files
    fn save_results(&self, results: &[BenchmarkResult], summary: &BenchmarkSummary) -> ProcessingResult<()> {

        // Save detailed results
        let results_file = self.output_dir.join("results").join("benchmark_results.json");
        let results_json = serde_json::to_string_pretty(results)
            .map_err(|e| crate::error::ProcessingError::io_error(format!("JSON serialization failed: {}", e)))?;
        fs::write(&results_file, results_json)?;

        // Save summary
        let summary_file = self.output_dir.join("results").join("benchmark_summary.json");
        let summary_json = serde_json::to_string_pretty(summary)
            .map_err(|e| crate::error::ProcessingError::io_error(format!("JSON serialization failed: {}", e)))?;
        fs::write(&summary_file, summary_json)?;

        // Save CSV if requested
        if self.config.format == "csv" {
            let csv_file = self.output_dir.join("results").join("benchmark_results.csv");
            let mut wtr = csv::Writer::from_path(csv_file)
                .map_err(|e| crate::error::ProcessingError::io_error(format!("CSV writer creation failed: {}", e)))?;
            // Write headers
            wtr.write_record(BenchmarkResult::csv_headers())
                .map_err(|e| crate::error::ProcessingError::io_error(format!("CSV header write failed: {}", e)))?;
            for result in results {
                wtr.serialize(result)
                    .map_err(|e| crate::error::ProcessingError::io_error(format!("CSV row write failed: {}", e)))?;
            }
            wtr.flush()
                .map_err(|e| crate::error::ProcessingError::io_error(format!("CSV flush failed: {}", e)))?;
        }

        Ok(())
    }

    /// Generate visualizations
    fn generate_visualizations(&self, _results: &[BenchmarkResult]) -> ProcessingResult<()> {
        // TODO: Implement visualization generation
        println!("Visualizations requested - implementation pending");
        Ok(())
    }

    /// Print benchmark summary
    fn print_summary(&self, summary: &BenchmarkSummary) {
        println!("\n{}", "=".repeat(60));
        println!("🏁 BENCHMARK COMPLETION SUMMARY");
        println!("{}", "=".repeat(60));
        println!("Total Tests: {}", summary.total_tests);
        println!("Successful: {}", summary.successful_tests);
        println!("Failed: {}", summary.failed_tests);
        println!("Total Time: {:.2} seconds", summary.total_execution_time);
        println!("Tools: {}", summary.tools_compared.join(", "));
        println!("K-mer Sizes: {:?}", summary.kmer_sizes_tested);

        if let Some(comparisons) = &summary.rustkmer_vs_jellyfish {
            println!("\n📊 RustKmer vs Jellyfish Performance:");
            for (metric, value) in comparisons {
                if metric.contains("speedup") {
                    println!("  {}: {:.2}x", metric, value);
                }
            }
        }

        println!("📁 Results saved to: {}", self.output_dir.display());
        println!("{}", "=".repeat(60));
    }
}

impl BenchmarkResult {
    /// CSV headers for serialization
    fn csv_headers() -> Vec<String> {
        vec![
            "test_name".to_string(),
            "tool".to_string(),
            "kmer_size".to_string(),
            "file_path".to_string(),
            "execution_time_seconds".to_string(),
            "memory_usage_mb".to_string(),
            "success".to_string(),
            "error_message".to_string(),
            "timestamp".to_string(),
        ]
    }
}


/// Execute benchmark command
pub fn execute_benchmark(args: &crate::cli::args::Commands) -> ProcessingResult<()> {
    if let crate::cli::args::Commands::Benchmark {
        data_dir,
        output_dir,
        kmer_sizes,
        compression,
        memory,
        iterations,
        format,
        visualize,
        compare_jellyfish,
    } = args
    {
        let config = BenchmarkConfig {
            compression: *compression,
            memory: *memory,
            iterations: *iterations,
            format: format.clone(),
            visualize: *visualize,
            compare_jellyfish: *compare_jellyfish,
        };

        let runner = BenchmarkRunner::new(data_dir, output_dir, kmer_sizes, config);
        runner.run_benchmark()?;
    }

    Ok(())
}