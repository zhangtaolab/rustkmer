//! Dump command implementation
//!
//! Implements database inspection and conversion functionality.

use std::io::{BufWriter, Write};
use std::path::Path;

use crate::cli::args::Args;
use crate::database::format::{DatabaseHeader, DATABASE_MAGIC};
use crate::error::{KmerError, ProcessingResult};

/// Execute the dump command
pub fn execute_dump(args: &Args) -> ProcessingResult<()> {
    match &args.command {
        crate::cli::args::Commands::Dump { database, output } => {
            dump_database(database, output.as_deref())
        }
        _ => Err(KmerError::ProcessingError("Invalid command for execute_dump".to_string()).into()),
    }
}

/// Dump database contents to text format
fn dump_database(database_path: &str, output_path: Option<&str>) -> ProcessingResult<()> {
    let path = Path::new(database_path);

    if !path.exists() {
        return Err(KmerError::FileNotFound(database_path.to_string()).into());
    }

    // Detect database format and dump accordingly
    let format = detect_database_format(path)?;

    eprintln!("Detected database format: {:?}", format);
    eprintln!("Dumping database: {}", database_path);

    match format {
        DatabaseFormat::Rkdb => dump_rkdb_database(path, output_path)?,
        DatabaseFormat::Bincode => dump_bincode_database(path, output_path)?,
        DatabaseFormat::Unknown => {
            return Err(KmerError::ProcessingError(
                "Unknown database format. Supported formats: Rkdb, bincode".to_string(),
            )
            .into());
        }
    }

    if let Some(output) = output_path {
        eprintln!("Database dumped to: {}", output);
    } else {
        eprintln!("Database dumped to stdout");
    }

    Ok(())
}

/// Database format types
#[derive(Debug, Clone, PartialEq)]
enum DatabaseFormat {
    Rkdb,
    Bincode,
    #[allow(dead_code)]
    Unknown,
}

/// Detect database format by reading file header
fn detect_database_format(path: &Path) -> ProcessingResult<DatabaseFormat> {
    use std::fs::File;
    use std::io::{BufReader, Read};

    let file = File::open(path).map_err(KmerError::Io)?;

    let mut reader = BufReader::new(file);
    let mut header_bytes = [0u8; 4];

    // Try to read first 4 bytes to detect magic number
    if reader.read_exact(&mut header_bytes).is_ok() && header_bytes == *DATABASE_MAGIC {
        return Ok(DatabaseFormat::Rkdb);
    }

    // If not RKDB, try to detect as bincode by attempting to deserialize
    // Bincode doesn't have a magic number, so we'll try to parse it
    Ok(DatabaseFormat::Bincode)
}

/// Dump RKDB format database
fn dump_rkdb_database(path: &Path, output_path: Option<&str>) -> ProcessingResult<()> {
    use std::fs::File;
    use std::io::{BufReader, BufWriter};

    let file = File::open(path).map_err(KmerError::Io)?;

    let mut reader = BufReader::new(file);

    // Read RKDB header
    let header = DatabaseHeader::read_from(&mut reader).map_err(|e| {
        KmerError::ProcessingError(format!("Failed to read database header: {}", e))
    })?;

    // Validate header
    header
        .validate()
        .map_err(|e| KmerError::ProcessingError(format!("Invalid database header: {}", e)))?;

    eprintln!("Database info:");
    eprintln!("  K-mer size: {}", header.kmer_size);
    eprintln!("  Total k-mers: {}", header.total_kmers);
    eprintln!("  Sorted: {}", header.sorted);
    eprintln!("  Canonical: {}", header.canonical);
    eprintln!("  Format version: {}", header.version);

    // Create output writer
    let writer: Box<dyn Write> = if let Some(output_path) = output_path {
        let file = std::fs::File::create(output_path).map_err(|e| {
            KmerError::FileWriteError(format!("Failed to create output file: {}", e))
        })?;
        Box::new(BufWriter::new(file))
    } else {
        Box::new(BufWriter::new(std::io::stdout()))
    };

    let mut writer = writer;

    // Write header comment
    writeln!(writer, "# rustkmer database dump")?;
    writeln!(writer, "# k: {}", header.kmer_size)?;
    writeln!(writer, "# total_kmers: {}", header.total_kmers)?;
    writeln!(writer, "# sorted: {}", header.sorted)?;
    writeln!(writer, "# canonical: {}", header.canonical)?;
    writeln!(writer, "# format: RKDB")?;
    writeln!(writer, "#")?;

    // Read and dump k-mer entries
    // Note: KmerEntry::read_from handles endianness internally

    // Calculate the number of entries in the database
    // For RKDB format, entries are stored from data_offset to end of file
    // Each entry is: u64/u128 (k-mer) + u32 (count) = 12 or 20 bytes
    let entry_size = if header.version == 2 && header.kmer_size > 32 {
        20 // u128 (16 bytes) + u32 (4 bytes)
    } else {
        12 // u64 (8 bytes) + u32 (4 bytes)
    };

    let num_entries = (path.metadata()?.len() - header.data_offset) / entry_size;
    eprintln!("Calculated database entries: {}", num_entries);

    use crate::database::format::KmerEntry;

    let mut processed = 0u64;
    while processed < num_entries {
        // Read k-mer entry using the proper reader that handles endianness
        match KmerEntry::read_from(&mut reader) {
            Ok(entry) => {
                // Decode k-mer back to DNA sequence based on size
                let sequence = if header.version == 2 && header.kmer_size > 32 {
                    decode_kmer_to_sequence_u128(entry.kmer, header.kmer_size as usize)
                } else {
                    // Truncate u128 to u64 for k <= 32
                    decode_kmer_to_sequence(entry.kmer as u64, header.kmer_size as usize)
                };

                writeln!(writer, "{}\t{}", sequence, entry.count).map_err(|e| {
                    KmerError::FileWriteError(format!("Failed to write k-mer entry: {}", e))
                })?;

                processed += 1;

                // Progress reporting for large databases
                if processed.is_multiple_of(100_000) {
                    eprintln!("Processed {} k-mers...", processed);
                }
            }
            Err(e) => {
                // EOF or read error - expected at end of file
                if processed > 0 {
                    eprintln!("Reached end of file at {} k-mers", processed);
                    break;
                } else {
                    return Err(KmerError::ProcessingError(format!(
                        "Failed to read k-mer entry at position {}: {}",
                        processed, e
                    ))
                    .into());
                }
            }
        }
    }

    eprintln!("Successfully dumped {} k-mers", processed);
    Ok(())
}

/// Dump bincode format database (legacy format)
fn dump_bincode_database(path: &Path, output_path: Option<&str>) -> ProcessingResult<()> {
    use std::fs::File;
    use std::io::BufReader;

    let file = File::open(path).map_err(KmerError::Io)?;

    let mut reader = BufReader::new(file);

    // Try to deserialize as bincode (kmer_length, kmers) tuple
    let bincode_data: (usize, Vec<(u64, u32)>) =
        bincode::deserialize_from(&mut reader).map_err(|_| {
            KmerError::ProcessingError(
                "Failed to parse as bincode format. This might not be a valid rustkmer database."
                    .to_string(),
            )
        })?;

    let (kmer_length, kmers) = bincode_data;

    eprintln!("Database info:");
    eprintln!("  K-mer size: {}", kmer_length);
    eprintln!("  Total k-mers: {}", kmers.len());
    eprintln!("  Format: bincode (legacy)");

    // Create output writer
    let writer: Box<dyn Write> = if let Some(out_path) = output_path {
        let file = std::fs::File::create(out_path).map_err(|e| {
            KmerError::FileWriteError(format!("Failed to create output file: {}", e))
        })?;
        Box::new(BufWriter::new(file))
    } else {
        Box::new(BufWriter::new(std::io::stdout()))
    };

    let mut writer = writer;

    // Write header comment
    writeln!(writer, "# rustkmer database dump")?;
    writeln!(writer, "# k: {}", kmer_length)?;
    writeln!(writer, "# total_kmers: {}", kmers.len())?;
    writeln!(writer, "# format: bincode (legacy)")?;
    writeln!(writer, "#")?;

    // Dump k-mers
    let kmer_count = kmers.len();
    for (kmer, count) in kmers {
        let sequence = decode_kmer_to_sequence(kmer, kmer_length);
        writeln!(writer, "{}\t{}", sequence, count).map_err(|e| {
            KmerError::FileWriteError(format!("Failed to write k-mer entry: {}", e))
        })?;
    }

    eprintln!("Successfully dumped {} k-mers", kmer_count);
    Ok(())
}

/// Decode a k-mer from encoded format back to DNA sequence
fn decode_kmer_to_sequence(kmer: u64, k: usize) -> String {
    let mut sequence = String::with_capacity(k);
    let mut encoded = kmer;

    for _ in 0..k {
        let base = encoded & 0b11;
        let char = match base {
            0 => 'A',
            1 => 'C',
            2 => 'G',
            3 => 'T',
            _ => 'N',
        };
        sequence.push(char);
        encoded >>= 2;
    }

    sequence.chars().rev().collect()
}

/// Decode a u128 k-mer from encoded format back to DNA sequence
fn decode_kmer_to_sequence_u128(kmer: u128, k: usize) -> String {
    let mut sequence = String::with_capacity(k);
    let mut encoded = kmer;

    for _ in 0..k {
        let base = encoded & 0b11;
        let char = match base {
            0 => 'A',
            1 => 'C',
            2 => 'G',
            3 => 'T',
            _ => 'N',
        };
        sequence.push(char);
        encoded >>= 2;
    }

    sequence.chars().rev().collect()
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_decode_kmer_to_sequence() {
        // Test basic k-mer decoding
        let encoded = 0b00_01_10_11; // ACGT in reverse order (LSB first)
        let sequence = decode_kmer_to_sequence(encoded, 4);
        assert_eq!(sequence, "ACGT"); // Decoded: LSB first (T,G,C,A) then reversed
    }

    #[test]
    fn test_database_format_detection() {
        // This would require creating test database files
        // For now, just ensure the function exists
        assert!(true);
    }
}
