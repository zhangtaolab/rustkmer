//! One-shot golden fixture generator (plan 01-03, Task 1, decision D-10).
//!
//! CRITICAL (D-10): this generator is the ONLY producer of the pre-refactor
//! golden `.rkdb` baseline. It replicates the CURRENT count-path writer from
//! `src/cli/commands/count.rs` (`output_binary_format`, lines ~503-532) byte
//! for byte — the same `DatabaseHeader` struct literal, the same
//! `header.write_to`, and the same raw `writer.write_u128::<LittleEndian>(kmer)`
//! / `writer.write_u32::<LittleEndian>(count)` entry loop. It does NOT call any
//! `format.rs` canonical writer for the entries, so the bytes it emits are
//! exactly what the current pre-refactor count path emits.
//!
//! Run with: `cargo test --test golden_generate -- --ignored --nocapture`
//!
//! The test is `#[ignore]`d so it only runs on demand (it writes committed
//! binary fixtures and is not part of the regression gate — `golden_tests.rs`
//! is the gate).

#![allow(clippy::print_stdout, clippy::print_stderr)]

use std::fs;
use std::io::BufWriter;
use std::io::Write;
use std::path::Path;

use byteorder::{LittleEndian, WriteBytesExt};
use rustkmer::database::format::{DatabaseHeader, DATABASE_MAGIC, DATABASE_VERSION};
use rustkmer::hash::table::KmerCounter;
use rustkmer::kmer::canonical::canonical_kmer_u128;
use rustkmer::kmer::encoding::encode_kmer_bytes_u128;
use sha2::{Digest, Sha256};

/// Fixed, deterministic DNA input used to seed every golden fixture.
///
/// Hardcoded on purpose (D-10 / D-13): the bytes must be reproducible across
/// machines and across the refactor, so the input cannot depend on the OS PRNG
/// or wall clock. The sequences are short and chosen to exercise distinct
/// 2-bit codes (A/C/G/T) and to produce a handful of collisions (so the count
/// values are > 1 in some cells).
const GOLDEN_INPUT: &[&str] = &[
    "ACGTACGTACGTACGTACGTACGTACGTACGTACGTACGTACGTACGTACGTACGTACGTACGTAC",
    "TTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTT",
    "ACACACACACACACACACACACACACACACACACACACACACACACACACACACACACACACACAC",
    "GTGTGTGTGTGTGTGTGTGTGTGTGTGTGTGTGTGTGTGTGTGTGTGTGTGTGTGTGTGTGTGTGT",
    "AAAACCCCGGGGTTTTAAAACCCCGGGGTTTTAAAACCCCGGGGTTTTAAAACCCCGGGGTTTTAA",
    "GATTACAGATTACAGATTACAGATTACAGATTACAGATTACAGATTACAGATTACAGATTACAGATT",
];

/// Matrix cell: (k, canonical, sorted). D-13 coverage.
struct Cell {
    k: usize,
    canonical: bool,
    sorted: bool,
}

fn all_cells() -> Vec<Cell> {
    let mut out = Vec::new();
    for &k in &[21usize, 32, 64] {
        for &canonical in &[true, false] {
            for &sorted in &[true, false] {
                out.push(Cell {
                    k,
                    canonical,
                    sorted,
                });
            }
        }
    }
    out
}

fn cell_name(c: &Cell) -> String {
    let canon = if c.canonical { "canon" } else { "noncanon" };
    let sort = if c.sorted { "sorted" } else { "unsorted" };
    format!("golden_k{}_{}_{}", c.k, canon, sort)
}

/// Count the fixed input with the given (k, canonical) — exactly the way the
/// count command would, via `KmerCounter`.
fn count_input(k: usize, canonical: bool) -> rustkmer::error::ProcessingResult<Vec<(u128, u32)>> {
    let counter = KmerCounter::new(k, canonical, 4096, 1)?;
    for seq in GOLDEN_INPUT {
        // Encode each overlapping k-mer in the sequence (sliding window), same
        // as the count command's FASTA path.
        let bytes = seq.as_bytes();
        if bytes.len() < k {
            continue;
        }
        for window in bytes.windows(k) {
            let kmer = encode_kmer_bytes_u128(window).map_err(|e| {
                rustkmer::error::ProcessingError::new(format!("encode failure: {}", e))
            })?;
            let final_kmer = if canonical {
                canonical_kmer_u128(kmer, k).map_err(|e| {
                    rustkmer::error::ProcessingError::new(format!("canonical failure: {}", e))
                })?
            } else {
                kmer
            };
            counter.increment(final_kmer)?;
        }
    }
    Ok(counter.get_all_kmers())
}

/// Replicate the EXACT current pre-refactor count-path writer
/// (`src/cli/commands/count.rs::output_binary_format`, header literal + raw
/// `write_u128`/`write_u32` entry loop). Do NOT delegate to `KmerEntry::write_to`
/// — that would taint the pre-refactor baseline (D-10).
fn write_golden_like_count_path(
    kmers: &mut [(u128, u32)],
    k: usize,
    canonical: bool,
    sorted: bool,
    out_path: &Path,
) -> rustkmer::error::ProcessingResult<()> {
    let kmer_count = kmers.len();

    if sorted {
        kmers.sort_by_key(|(a, _)| *a);
    }

    let file = std::fs::File::create(out_path).map_err(|e| {
        rustkmer::error::KmerError::FileWriteError(format!("Failed to create output file: {}", e))
    })?;
    let mut writer = BufWriter::new(file);

    // --- verbatim copy of count.rs:503-514 header literal ---
    let header = DatabaseHeader {
        magic: *DATABASE_MAGIC,
        version: DATABASE_VERSION,
        kmer_size: k as u8,
        total_kmers: kmer_count as u64,
        sorted,
        data_offset: 42, // Fixed header size for RKDB format
        index_offset: 0,
        canonical,
        unique_kmers: kmer_count as u64, // Same as total_kmers for now
        file_size: 42 + (kmer_count as u64 * 12), // Header + k-mer entries (8+4 bytes each)
    };

    // --- verbatim copy of count.rs:524-526 header write ---
    header.write_to(&mut writer).map_err(|e| {
        rustkmer::error::KmerError::FileWriteError(format!(
            "Failed to write database header: {}",
            e
        ))
    })?;

    // --- verbatim copy of count.rs:528-532 entry loop ---
    // IMPORTANT: this is the RAW write_u128/write_u32 path, NOT KmerEntry::write_to.
    // This is what makes the bytes a faithful pre-refactor baseline.
    for (kmer, count) in kmers.iter() {
        writer.write_u128::<LittleEndian>(*kmer)?;
        writer.write_u32::<LittleEndian>(*count)?;
    }

    writer.flush()?;
    Ok(())
}

fn sha256_hex(bytes: &[u8]) -> String {
    let mut hasher = Sha256::new();
    hasher.update(bytes);
    let hash = hasher.finalize();
    format!("{:x}", hash)
}

#[test]
#[ignore = "one-shot golden fixture generator (D-10); run with --ignored"]
fn generate_golden_fixtures() -> Result<(), Box<dyn std::error::Error>> {
    let fixtures_dir = Path::new("tests/fixtures");
    fs::create_dir_all(fixtures_dir)?;

    let mut manifest: Vec<(String, String)> = Vec::new();

    for cell in all_cells() {
        let mut kmers = count_input(cell.k, cell.canonical)?;

        // Guard against the >1M count endianness heuristic in KmerEntry::read_from
        // (RESEARCH.md §4 Pitfall 9) — our counts are small by construction.
        assert!(
            kmers.iter().all(|(_, c)| *c <= 1_000_000),
            "golden fixture counts must stay small"
        );

        let fname = format!("{}.rkdb", cell_name(&cell));
        let path = fixtures_dir.join(&fname);
        write_golden_like_count_path(&mut kmers, cell.k, cell.canonical, cell.sorted, &path)?;

        let bytes = fs::read(&path)?;
        let hex = sha256_hex(&bytes);
        println!(
            "{}  {}  ({} bytes, {} kmers)",
            hex,
            fname,
            bytes.len(),
            kmers.len()
        );
        manifest.push((fname, hex));
    }

    // Write the manifest: `<basename> <sha256-hex>` per line, sorted by name for stability.
    manifest.sort_by(|a, b| a.0.cmp(&b.0));
    let manifest_path = fixtures_dir.join("golden_manifest.sha256");
    let mut out = String::new();
    for (name, hex) in &manifest {
        out.push_str(&format!("{} {}\n", name, hex));
    }
    fs::write(&manifest_path, out)?;
    println!(
        "wrote {} ({} entries)",
        manifest_path.display(),
        manifest.len()
    );

    // --- Legacy sample (D-12): data_offset = 42, generated by the CURRENT code ---
    // A tiny 4-k-mer db. The header literal above hardcodes data_offset=42, so
    // any small write produces a valid legacy sample. We use a k=21 canonical
    // sorted subset to keep it minimal and unambiguous.
    let mut legacy_kmers: Vec<(u128, u32)> = vec![
        (encode_kmer_bytes_u128(b"ACGTACGTACGTACGTACGTA")?, 7),
        (encode_kmer_bytes_u128(b"TTTTTTTTTTTTTTTTTTTTT")?, 3),
        (encode_kmer_bytes_u128(b"GATCACAGGTGATCATACCTG")?, 11),
        (encode_kmer_bytes_u128(b"AAAACCCCGGGGTTTTAAAAT")?, 2),
    ];
    let legacy_path = fixtures_dir.join("legacy_v2_offset42.rkdb");
    write_golden_like_count_path(&mut legacy_kmers, 21, false, false, &legacy_path)?;
    let lb = fs::read(&legacy_path)?;
    println!(
        "wrote {} ({} bytes, {} kmers, data_offset=42)",
        legacy_path.display(),
        lb.len(),
        legacy_kmers.len()
    );

    Ok(())
}
