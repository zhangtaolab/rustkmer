//! Stats command implementation
//!
//! This module implements the `rustkmer stats` command for calculating
//! comprehensive statistics about RKDB databases.

use crate::cli::args::Args;
use crate::database::stats::{OutputFormat, Result, StatsConfiguration, StatsError};
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
        split_output,
        freq_output,
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
            split_output: *split_output,
            freq_output_path: freq_output.as_ref().map(PathBuf::from),
        };

        // Execute statistics calculation
        let start_time = Instant::now();
        let stats = calculate_statistics(database.as_str(), config.clone())
            .with_context(|| format!("Failed to calculate statistics for {}", database))?;

        // Output results
        output_results(&stats, &config).with_context(|| "Failed to output statistics")?;

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
    use std::fs::File;
    use std::io::{BufReader, Seek, SeekFrom};
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
    let header = crate::database::format::DatabaseHeader::read_from(&mut file).map_err(|e| {
        StatsError::InvalidFormat {
            reason: format!("Failed to read database header: {}", e),
        }
    })?;

    header.validate().map_err(|e| StatsError::InvalidFormat {
        reason: format!("Invalid database header: {}", e),
    })?;

    // Check if database is empty
    if header.total_kmers == 0 {
        return Err(StatsError::EmptyDatabase);
    }

    // Initialize statistics processor
    let mut processor = crate::database::stats::StreamingStatsProcessor::new(config.clone());

    // `header.validate()` (called above) already enforces `data_offset == 42`
    // per the SPEC P3 invariant — the silent read-side reconciliation that
    // used to live here has been removed (CR-01). The header offset is the
    // canonical offset and is safe to use directly.
    file.seek(SeekFrom::Start(header.data_offset))?;

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

    if config.split_output {
        // Validate that freq_output_path is provided when split_output is true
        let freq_path =
            config
                .freq_output_path
                .as_ref()
                .ok_or_else(|| StatsError::InvalidFormat {
                    reason: "Frequency output path is required when using split output".to_string(),
                })?;

        // Output basic statistics
        let writer: Box<dyn std::io::Write> = match &config.output_path {
            Some(path) => {
                let file = std::fs::File::create(path)?;
                Box::new(std::io::BufWriter::new(file))
            }
            None => Box::new(std::io::stdout()),
        };

        // Create a modified stats object without frequency distribution for basic stats
        let mut basic_stats = stats.clone();
        basic_stats.frequency_distribution = None;

        match config.output_format {
            OutputFormat::Text => output_text(writer, &basic_stats),
            OutputFormat::Json => output_json(writer, &basic_stats),
            OutputFormat::Csv => output_csv(writer, &basic_stats),
            OutputFormat::Tsv => output_tsv(writer, &basic_stats),
        }?;

        // Output frequency distribution separately
        let freq_writer: Box<dyn std::io::Write> = {
            let file = std::fs::File::create(freq_path)?;
            Box::new(std::io::BufWriter::new(file))
        };

        output_frequency_distribution(freq_writer, stats, config)?;
    } else {
        // Original behavior: single file output
        let writer: Box<dyn std::io::Write> = match &config.output_path {
            Some(path) => {
                let file = std::fs::File::create(path)?;
                Box::new(std::io::BufWriter::new(file))
            }
            None => Box::new(std::io::stdout()),
        };

        match config.output_format {
            OutputFormat::Text => output_text(writer, stats)?,
            OutputFormat::Json => output_json(writer, stats)?,
            OutputFormat::Csv => output_csv(writer, stats)?,
            OutputFormat::Tsv => output_tsv(writer, stats)?,
        }
    }

    Ok(())
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

    // Write header
    wtr.write_record([
        "database_file",
        "kmer_size",
        "canonical",
        "sorted",
        "total_kmers",
        "unique_kmers",
        "min_count",
        "max_count",
        "mean_count",
        "median_count",
        "processing_time_ms",
        "memory_peak_bytes",
        "frequency_distribution_available",
    ])?;

    // Write data record
    wtr.write_record([
        stats.database_file.to_string_lossy().as_ref(),
        &stats.kmer_size.to_string(),
        &stats.canonical.to_string(),
        &stats.sorted.to_string(),
        &stats.total_kmers.to_string(),
        &stats.unique_kmers.to_string(),
        &stats.min_count.to_string(),
        &stats.max_count.to_string(),
        &stats.mean_count.to_string(),
        &stats.median_count.to_string(),
        &stats.processing_time.as_millis().to_string(),
        &stats.memory_peak_bytes.to_string(),
        if stats.frequency_distribution.is_some() {
            "true"
        } else {
            "false"
        },
    ])?;

    // Note: Frequency distribution is too large for standard CSV format
    // It's available in JSON format or through the text output

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

    // Write header
    wtr.write_record([
        "database_file",
        "kmer_size",
        "canonical",
        "sorted",
        "total_kmers",
        "unique_kmers",
        "min_count",
        "max_count",
        "mean_count",
        "median_count",
        "processing_time_ms",
        "memory_peak_bytes",
        "frequency_distribution_available",
    ])?;

    // Write data record
    wtr.write_record([
        stats.database_file.to_string_lossy().as_ref(),
        &stats.kmer_size.to_string(),
        &stats.canonical.to_string(),
        &stats.sorted.to_string(),
        &stats.total_kmers.to_string(),
        &stats.unique_kmers.to_string(),
        &stats.min_count.to_string(),
        &stats.max_count.to_string(),
        &stats.mean_count.to_string(),
        &stats.median_count.to_string(),
        &stats.processing_time.as_millis().to_string(),
        &stats.memory_peak_bytes.to_string(),
        if stats.frequency_distribution.is_some() {
            "true"
        } else {
            "false"
        },
    ])?;

    // Note: Frequency distribution is too large for standard TSV format
    // It's available in JSON format or through the text output
    if stats.frequency_distribution.is_some() {
        wtr.write_record([
            "frequency_distribution_available",
            "true",
            "",
            "",
            "",
            "",
            "",
            "",
            "",
            "",
            "",
            "",
            "",
        ])?;
    }

    wtr.flush()?;
    Ok(())
}
/// Output frequency distribution to a separate file
fn output_frequency_distribution<W: std::io::Write>(
    mut writer: W,
    stats: &crate::database::stats::DatabaseStatistics,
    config: &StatsConfiguration,
) -> Result<()> {
    use crate::database::stats::OutputFormat;

    if let Some(ref dist) = stats.frequency_distribution {
        match config.output_format {
            OutputFormat::Text => {
                writeln!(writer, "Frequency Distribution")?;
                writeln!(writer, "====================")?;
                writeln!(writer, "Database: {:?}", stats.database_file)?;
                writeln!(writer, "K-mer size: {}", stats.kmer_size)?;
                writeln!(writer, "Total k-mers: {}", stats.total_kmers)?;
                writeln!(writer, "Unique k-mers: {}", stats.unique_kmers)?;
                writeln!(writer)?;
                writeln!(writer, "Count	Frequency")?;
                for (count, freq) in dist {
                    writeln!(writer, "{}	{}", count, freq)?;
                }
            }
            OutputFormat::Json => {
                // Create a JSON object with just the frequency distribution
                let freq_json = serde_json::json!({
                    "database_file": stats.database_file,
                    "kmer_size": stats.kmer_size,
                    "frequency_distribution": dist
                });
                serde_json::to_writer(&mut writer, &freq_json)?;
            }
            OutputFormat::Csv => {
                let mut wtr = csv::Writer::from_writer(&mut writer);

                // Write header
                wtr.write_record(["Count", "Frequency"])?;

                // Write data
                for (count, freq) in dist {
                    wtr.write_record([&count.to_string(), &freq.to_string()])?;
                }

                wtr.flush()?;
            }
            OutputFormat::Tsv => {
                let mut wtr = csv::WriterBuilder::new()
                    .delimiter(b'\t')
                    .from_writer(&mut writer);

                // Write header
                wtr.write_record(["Count", "Frequency"])?;

                // Write data
                for (count, freq) in dist {
                    wtr.write_record([&count.to_string(), &freq.to_string()])?;
                }

                wtr.flush()?;
            }
        }
    } else {
        return Err(StatsError::InvalidFormat {
            reason: "No frequency distribution data available".to_string(),
        });
    }

    Ok(())
}
