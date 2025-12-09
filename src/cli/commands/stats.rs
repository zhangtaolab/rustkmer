//! Stats command implementation
//!
//! This module implements the `rustkmer stats` command for calculating
//! comprehensive statistics about RKDB databases.

use crate::cli::args::Args;
use crate::database::stats::{StatsConfiguration, OutputFormat, StatsError, Result};
use anyhow::Context;
use std::path::PathBuf;
use std::time::Instant;

/// Execute the stats command
pub fn execute_stats(args: &Args) -> anyhow::Result<()> {
    if let crate::cli::args::Commands::Stats {
        database,
        format,
        output,
        detailed,
        max_bins,
        approximate,
        progress,
    } = &args.command
    {
        // Parse output format
        let output_format = match format.as_str() {
            "text" => OutputFormat::Text,
            "json" => OutputFormat::Json,
            "csv" => OutputFormat::Csv,
            "tsv" => OutputFormat::Tsv,
            _ => return Err(anyhow::anyhow!("Invalid output format: {}", format)),
        };

        // Create configuration
        let config = StatsConfiguration {
            output_format,
            detailed: *detailed,
            max_bins: *max_bins,
            approximate: *approximate,
            show_progress: *progress,
            output_path: output.as_ref().map(PathBuf::from),
        };

        // Execute statistics calculation
        let start_time = Instant::now();
        let stats = calculate_statistics(database.as_str(), config.clone())
            .with_context(|| format!("Failed to calculate statistics for {}", database))?;

        // Output results
        output_results(&stats, &config)
            .with_context(|| "Failed to output statistics")?;

        let elapsed = start_time.elapsed();
        // TODO: Add quiet flag to Args if needed
        eprintln!("Statistics calculated successfully in {:?}", elapsed);

        Ok(())
    } else {
        Err(anyhow::anyhow!("Not a stats command"))
    }
}

/// Calculate statistics for a database file
fn calculate_statistics(
    database_path: &str,
    config: StatsConfiguration,
) -> Result<crate::database::stats::DatabaseStatistics> {
    use std::io::{Seek, SeekFrom, BufReader};
    use std::fs::File;
    use std::path::PathBuf;

    let start_time = std::time::Instant::now();

    // Validate database file exists
    let path = PathBuf::from(database_path);
    if !path.exists() {
        return Err(StatsError::DatabaseNotFound { path });
    }

    // Open database file
    let file = File::open(&path)?;
    let mut file = BufReader::new(file);

    // Read and validate header
    let header = crate::database::format::DatabaseHeader::read_from(&mut file)
        .map_err(|e| StatsError::InvalidFormat {
            reason: format!("Failed to read database header: {}", e)
        })?;

    header.validate()
        .map_err(|e| StatsError::InvalidFormat {
            reason: format!("Invalid database header: {}", e)
        })?;

    // Check if database is empty
    if header.total_kmers == 0 {
        return Err(StatsError::EmptyDatabase);
    }

    // Initialize statistics processor
    let mut processor = crate::database::stats::StreamingStatsProcessor::new(config.clone());

    // Fix for incorrect data_offset in header (same as in query.rs)
    let actual_data_offset = if header.data_offset < 40 {
        42  // Use correct offset when header value is too small
    } else if header.data_offset > 1000 {
        42  // Use correct offset when header value is too large
    } else {
        header.data_offset
    };

    // Seek to data section
    file.seek(SeekFrom::Start(actual_data_offset))?;

    // Read all k-mer entries and calculate statistics
    for i in 0..header.total_kmers {
        let entry = crate::database::format::KmerEntry::read_from(&mut file)?;

        // Add count to statistics
        processor.add_count(entry.count)?;

        // Show progress if enabled
        if config.show_progress && (i + 1) % 100000 == 0 {
            eprint!("\rProcessed {} k-mers...", i + 1);
        }
    }

    if config.show_progress {
        eprintln!("\rProcessed {} k-mers... Done!", header.total_kmers);
    }

    // Finalize statistics
    let processing_time = start_time.elapsed();
    let stats = processor.finalize(
        path,
        header.kmer_size,
        header.canonical,
        header.sorted,
        processing_time,
    );

    Ok(stats)
}

/// Output statistics in the configured format
fn output_results(
    stats: &crate::database::stats::DatabaseStatistics,
    config: &StatsConfiguration,
) -> Result<()> {
    use crate::database::stats::OutputFormat;

    let writer: Box<dyn std::io::Write> = match &config.output_path {
        Some(path) => {
            let file = std::fs::File::create(path)?;
            Box::new(std::io::BufWriter::new(file))
        }
        None => Box::new(std::io::stdout()),
    };

    match config.output_format {
        OutputFormat::Text => output_text(writer, stats),
        OutputFormat::Json => output_json(writer, stats),
        OutputFormat::Csv => output_csv(writer, stats),
        OutputFormat::Tsv => output_tsv(writer, stats),
    }
}

/// Output statistics in human-readable text format
fn output_text<W: std::io::Write>(
    mut writer: W,
    stats: &crate::database::stats::DatabaseStatistics,
) -> Result<()> {

    writeln!(writer, "Database Statistics")?;
    writeln!(writer, "===================")?;
    writeln!(writer, "Database: {:?}", stats.database_file)?;
    writeln!(writer, "K-mer size: {}", stats.kmer_size)?;
    writeln!(writer, "Canonical: {}", stats.canonical)?;
    writeln!(writer, "Sorted: {}", stats.sorted)?;
    writeln!(writer, "Total k-mers: {}", stats.total_kmers)?;
    writeln!(writer, "Unique k-mers: {}", stats.unique_kmers)?;
    writeln!(writer, "Min count: {}", stats.min_count)?;
    writeln!(writer, "Max count: {}", stats.max_count)?;
    writeln!(writer, "Mean count: {:.2}", stats.mean_count)?;
    writeln!(writer, "Median count: {:.2}", stats.median_count)?;
    writeln!(writer, "Processing time: {:?}", stats.processing_time)?;

    if let Some(ref dist) = stats.frequency_distribution {
        writeln!(writer, "\nFrequency Distribution:")?;
        writeln!(writer, "Count\tFrequency")?;
        for (count, freq) in dist {
            writeln!(writer, "{}\t{}", count, freq)?;
        }
    }

    Ok(())
}

/// Output statistics in JSON format
fn output_json<W: std::io::Write>(
    mut writer: W,
    stats: &crate::database::stats::DatabaseStatistics,
) -> Result<()> {
    serde_json::to_writer(&mut writer, stats)?;
    Ok(())
}

/// Output statistics in CSV format
fn output_csv<W: std::io::Write>(
    mut writer: W,
    stats: &crate::database::stats::DatabaseStatistics,
) -> Result<()> {
    let mut wtr = csv::Writer::from_writer(&mut writer);
    wtr.serialize(stats)?;
    wtr.flush()?;
    Ok(())
}

/// Output statistics in TSV format
fn output_tsv<W: std::io::Write>(
    mut writer: W,
    stats: &crate::database::stats::DatabaseStatistics,
) -> Result<()> {
    let mut wtr = csv::WriterBuilder::new()
        .delimiter(b'\t')
        .from_writer(&mut writer);
    wtr.serialize(stats)?;
    wtr.flush()?;
    Ok(())
}