//! Stage-isolation microbench for the rustkmer k=21 counting hot path.
//!
//! Legacy single-threaded arms (positional mode, unchanged):
//! A: current production path (per-window O(k) encode + O(k) revcomp + DashMap)
//! B: rolling 2-bit encode + bit-parallel revcomp + same DashMap increment
//! C: DashMap increment only (pre-encoded keys)
//! D: rolling encode + canonical only (no table)
//! E: current encode + canonical only (no table)
//!
//! Multi-thread contention arms (flag mode, PROF-03 / 05-05) isolate the
//! global-atomics vs shared-table (bandwidth/locality) shares of the in-vivo
//! increment multiplier. All four operate on the SAME pre-encoded canonical
//! key vector, split into disjoint per-worker ranges:
//!   shared-counter : one production KmerCounter shared across T workers —
//!                    DashMap traffic PLUS per-window total_kmers fetch_add
//!                    and insert-time unique_kmers fetch_add (both Relaxed).
//!   shared-dashmap : raw dashmap::DashMap<u64, u32> (default RandomState,
//!                    SipHash-1-3, production-locked dashmap 6.2.1), same
//!                    entry().and_modify().or_insert() table work, NO global
//!                    counters.
//!   atomic-only    : no table — exactly `windows` fetch_add(1, Relaxed) ops
//!                    on one shared AtomicU64 plus `distinct` fetch_adds on a
//!                    second, distributed across the same T workers.
//!   thread-local   : private std HashMap<u64, u32> + private u64 total per
//!                    worker, joined and reduced into one map inside the
//!                    timed region — the locality/bandwidth control. Evidence
//!                    only, NOT a production engine.
//!
//! Every rep is conservation-checked (sum of counts == windows AND unique ==
//! precomputed distinct); a failed check aborts with a loud error (exit 1),
//! never a recorded pass. Every worker handle is joined and its Result
//! propagated — worker failures are never discarded.
//!
//! Usage:
//!   legacy: rk-microbench [k] [nreads] [variants]     (default input path)
//!   flags:  rk-microbench --k 21 --reads 200000 --threads 4 --reps 1 \
//!               --variant shared-counter --input reads.fq [--json out.json]
//! Flag mode takes precedence when any `--` flag is present.

use rustkmer::hash::KmerCounter;
use rustkmer::kmer::canonical::canonical_kmer_u128;
use rustkmer::kmer::encoding::encode_kmer_bytes_u128;
use std::time::Instant;

fn load_reads(path: &str, n: usize) -> Vec<Vec<u8>> {
    use std::io::BufRead;
    let f = std::fs::File::open(path).unwrap();
    let r = std::io::BufReader::new(f);
    let mut out = Vec::new();
    for (i, line) in r.lines().enumerate() {
        let line = line.unwrap();
        if i % 4 == 1 {
            out.push(line.into_bytes());
            if out.len() >= n {
                break;
            }
        }
    }
    out
}

#[inline]
fn code(b: u8) -> u64 {
    match b.to_ascii_uppercase() {
        b'A' => 0,
        b'C' => 1,
        b'G' => 2,
        b'T' => 3,
        _ => 4,
    }
}

/// Bit-parallel reverse complement of a right-aligned 2-bit packed k-mer.
#[inline]
fn rc_bits(x: u64, k: usize) -> u64 {
    let mut v = !x;
    v = ((v & 0x3333_3333_3333_3333) << 2) | ((v >> 2) & 0x3333_3333_3333_3333);
    v = ((v & 0x0F0F_0F0F_0F0F_0F0F) << 4) | ((v >> 4) & 0x0F0F_0F0F_0F0F_0F0F);
    v = v.swap_bytes();
    v >> (64 - 2 * k)
}

/// Rolling encoder: yields canonical k-mers, skipping windows with N.
fn rolling_canonical(seq: &[u8], k: usize, mut emit: impl FnMut(u64)) {
    let mask: u64 = if k == 32 { u64::MAX } else { (1u64 << (2 * k)) - 1 };
    let shift = 2 * (k - 1);
    let mut fwd: u64 = 0;
    let mut rev: u64 = 0;
    let mut valid: usize = 0;
    for &b in seq {
        let c = code(b);
        if c == 4 {
            valid = 0;
            fwd = 0;
            rev = 0;
            continue;
        }
        fwd = ((fwd << 2) | c) & mask;
        rev = (rev >> 2) | ((3 - c) << shift);
        valid += 1;
        if valid >= k {
            emit(fwd.min(rev));
        }
    }
}

/// Correctness: rolling keys == production keys (first 2000 reads).
/// Runs in BOTH modes — the contention arms are only meaningful if the
/// pre-encoded keys are the production keys.
fn key_identity_check(reads: &[Vec<u8>], k: usize) {
    let mut a: Vec<u64> = Vec::new();
    let mut b: Vec<u64> = Vec::new();
    for seq in reads.iter().take(2000) {
        if seq.len() < k {
            continue;
        }
        for i in 0..=(seq.len() - k) {
            if let Ok(e) = encode_kmer_bytes_u128(&seq[i..i + k]) {
                a.push(canonical_kmer_u128(e, k).unwrap() as u64);
            }
        }
        rolling_canonical(seq, k, |x| b.push(x));
    }
    assert_eq!(a, b, "rolling canonical keys must equal production keys");
    println!("key-identity check: PASS ({} keys)", a.len());
}

// =====================================================================
// Legacy positional mode (unchanged behavior — post_matrix.sh reproduction)
// =====================================================================

fn legacy_main(args: &[String]) {
    let k: usize = args.get(1).map(|s| s.parse().unwrap()).unwrap_or(21);
    let nreads: usize = args.get(2).map(|s| s.parse().unwrap()).unwrap_or(200_000);
    let variants: String = args.get(3).cloned().unwrap_or_else(|| "ABCDE".into());
    let reads = load_reads("/tmp/rkmer-v2-prof/data/slice4M.fq", nreads);
    let windows: usize = reads.iter().map(|s| s.len().saturating_sub(k - 1)).sum();
    println!("k={k} reads={} windows~={windows} variants={variants}", reads.len());

    key_identity_check(&reads, k);

    if variants.contains('A') {
        let c = KmerCounter::new(k, true, 1_000_000, 1).unwrap();
        let t = Instant::now();
        for seq in &reads {
            if seq.len() < k {
                continue;
            }
            for i in 0..=(seq.len() - k) {
                if let Ok(e) = encode_kmer_bytes_u128(&seq[i..i + k]) {
                    let ck = canonical_kmer_u128(e, k).unwrap();
                    c.increment(ck).unwrap();
                }
            }
        }
        let dt = t.elapsed();
        println!(
            "A production encode+canon+increment: {:.2}s  {:.1} ns/window  (unique={})",
            dt.as_secs_f64(),
            dt.as_nanos() as f64 / windows as f64,
            c.unique_kmers()
        );
    }

    if variants.contains('B') {
        let c = KmerCounter::new(k, true, 1_000_000, 1).unwrap();
        let t = Instant::now();
        for seq in &reads {
            rolling_canonical(seq, k, |x| c.increment(x as u128).unwrap());
        }
        let dt = t.elapsed();
        println!(
            "B rolling+bitrc+increment:           {:.2}s  {:.1} ns/window  (unique={})",
            dt.as_secs_f64(),
            dt.as_nanos() as f64 / windows as f64,
            c.unique_kmers()
        );
    }

    if variants.contains('C') {
        let mut keys: Vec<u64> = Vec::with_capacity(windows);
        for seq in &reads {
            rolling_canonical(seq, k, |x| keys.push(x));
        }
        let c = KmerCounter::new(k, true, 1_000_000, 1).unwrap();
        let t = Instant::now();
        for &x in &keys {
            c.increment(x as u128).unwrap();
        }
        let dt = t.elapsed();
        println!(
            "C increment-only (pre-encoded):      {:.2}s  {:.1} ns/window  (unique={})",
            dt.as_secs_f64(),
            dt.as_nanos() as f64 / keys.len() as f64,
            c.unique_kmers()
        );
    }

    if variants.contains('D') {
        let t = Instant::now();
        let mut acc: u64 = 0;
        for seq in &reads {
            rolling_canonical(seq, k, |x| acc = acc.wrapping_add(x));
        }
        let dt = t.elapsed();
        println!(
            "D rolling encode+canon only:         {:.2}s  {:.1} ns/window  (acc={})",
            dt.as_secs_f64(),
            dt.as_nanos() as f64 / windows as f64,
            acc
        );
    }

    if variants.contains('E') {
        let t = Instant::now();
        let mut acc: u64 = 0;
        for seq in &reads {
            if seq.len() < k {
                continue;
            }
            for i in 0..=(seq.len() - k) {
                if let Ok(e) = encode_kmer_bytes_u128(&seq[i..i + k]) {
                    let ck = canonical_kmer_u128(e, k).unwrap();
                    acc = acc.wrapping_add(ck as u64);
                }
            }
        }
        let dt = t.elapsed();
        println!(
            "E production encode+canon only:      {:.2}s  {:.1} ns/window  (acc={})",
            dt.as_secs_f64(),
            dt.as_nanos() as f64 / windows as f64,
            acc
        );
    }
}

// =====================================================================
// Flag mode: multi-thread contention arms (PROF-03)
// =====================================================================

const VARIANT_NAMES: [&str; 4] = [
    "shared-counter",
    "shared-dashmap",
    "atomic-only",
    "thread-local",
];

struct Flags {
    k: usize,
    reads: usize,
    threads: usize,
    reps: usize,
    variant: String,
    input: String,
    json: Option<String>,
}

fn parse_flags(args: &[String]) -> Result<Flags, String> {
    let mut f = Flags {
        k: 21,
        reads: 200_000,
        threads: 1,
        reps: 1,
        variant: String::new(),
        input: String::new(),
        json: None,
    };
    let mut it = args.iter().skip(1);
    while let Some(arg) = it.next() {
        let mut value = || -> Result<String, String> {
            it.next()
                .cloned()
                .ok_or_else(|| format!("missing value for {arg}"))
        };
        match arg.as_str() {
            "--k" => f.k = value()?.parse().map_err(|_| "invalid --k".to_string())?,
            "--reads" => {
                f.reads = value()?.parse().map_err(|_| "invalid --reads".to_string())?
            }
            "--threads" => {
                f.threads = value()?.parse().map_err(|_| "invalid --threads".to_string())?
            }
            "--reps" => {
                f.reps = value()?.parse().map_err(|_| "invalid --reps".to_string())?
            }
            "--variant" => f.variant = value()?,
            "--input" => f.input = value()?,
            "--json" => f.json = Some(value()?),
            other => return Err(format!("unknown flag {other}")),
        }
    }
    // The rolling encoder packs keys into u64, so flag mode supports k <= 32
    // (the production counter itself supports k <= 64; the contention study
    // targets k=21).
    if f.k < 1 || f.k > 32 {
        return Err("--k must be in 1..=32 (u64 pre-encoded keys)".into());
    }
    if f.reads < 1 {
        return Err("--reads must be >= 1".into());
    }
    if f.threads < 1 {
        return Err("--threads must be >= 1".into());
    }
    if f.reps < 1 {
        return Err("--reps must be >= 1".into());
    }
    if !VARIANT_NAMES.contains(&f.variant.as_str()) {
        return Err(format!(
            "--variant is required and must be one of {VARIANT_NAMES:?}"
        ));
    }
    if f.input.is_empty() {
        return Err("--input <FASTQ path> is required in flag mode".into());
    }
    Ok(f)
}

/// Pre-encode ALL canonical keys once (outside every timed region).
fn preencode_keys(reads: &[Vec<u8>], k: usize) -> Vec<u64> {
    let mut keys: Vec<u64> = Vec::new();
    for seq in reads {
        rolling_canonical(seq, k, |x| keys.push(x));
    }
    keys
}

/// Single-threaded counting pre-pass over the same keys: the exact distinct
/// count every arm is conservation-checked against. Sort+dedup is used (a
/// deterministic counting pass) to keep the pre-pass fast and allocation-lean.
fn precompute_distinct(keys: &[u64]) -> usize {
    let mut sorted = keys.to_vec();
    sorted.sort_unstable();
    sorted.dedup();
    sorted.len()
}

/// Disjoint per-worker index ranges (parallel_count_tests.rs pattern).
fn disjoint_ranges(len: usize, workers: usize) -> Vec<(usize, usize)> {
    let w = workers.max(1).min(len.max(1));
    let per = len.div_ceil(w);
    let mut out = Vec::new();
    for i in 0..w {
        let start = i * per;
        let end = ((i + 1) * per).min(len);
        if start < end {
            out.push((start, end));
        }
    }
    out
}

struct ArmOutcome {
    elapsed_ns: u128,
    total_count: u64,
    unique_count: u64,
}

/// Arm 1: production KmerCounter shared across T scoped workers — DashMap
/// traffic plus BOTH global atomics (per-window total fetch_add after each
/// successful increment, insert-time unique fetch_add; src/hash/table.rs).
fn run_shared_counter(keys: &[u64], k: usize, threads: usize) -> Result<ArmOutcome, String> {
    let counter = KmerCounter::new(k, true, 1_000_000, 1).map_err(|e| e.to_string())?;
    let ranges = disjoint_ranges(keys.len(), threads);
    let t = Instant::now();
    std::thread::scope(|s| -> Result<(), String> {
        let mut handles = Vec::new();
        for (start, end) in ranges {
            let c = &counter;
            let slice = &keys[start..end];
            handles.push(s.spawn(move || -> Result<(), String> {
                for &x in slice {
                    c.increment(x as u128).map_err(|e| e.to_string())?;
                }
                Ok(())
            }));
        }
        for h in handles {
            h.join()
                .map_err(|_| "shared-counter worker panicked".to_string())??;
        }
        Ok(())
    })?;
    let elapsed_ns = t.elapsed().as_nanos();
    let counts = counter.get_all_counts();
    let total_count: u64 = counts.iter().map(|(_, c)| *c as u64).sum();
    // Production invariant: the global total atomic must equal the table sum.
    if counter.total_kmers() != total_count {
        return Err(format!(
            "production total_kmers atomic ({}) disagrees with table sum ({})",
            counter.total_kmers(),
            total_count
        ));
    }
    Ok(ArmOutcome {
        elapsed_ns,
        total_count,
        unique_count: counter.unique_kmers(),
    })
}

/// Arm 2: raw shared DashMap<u64, u32>, default RandomState (SipHash-1-3,
/// matching the production-locked dashmap 6.2.1), identical entry-chain table
/// work, NO global counters. Capacity mirrors KmerCounter::new's 1M initial.
fn run_shared_dashmap(keys: &[u64], threads: usize) -> Result<ArmOutcome, String> {
    use dashmap::DashMap;
    let map: DashMap<u64, u32> = DashMap::with_capacity(1_000_000);
    let ranges = disjoint_ranges(keys.len(), threads);
    let t = Instant::now();
    std::thread::scope(|s| -> Result<(), String> {
        let mut handles = Vec::new();
        for (start, end) in ranges {
            let m = &map;
            let slice = &keys[start..end];
            handles.push(s.spawn(move || -> Result<(), String> {
                for &x in slice {
                    m.entry(x).and_modify(|c| *c += 1).or_insert(1);
                }
                Ok(())
            }));
        }
        for h in handles {
            h.join()
                .map_err(|_| "shared-dashmap worker panicked".to_string())??;
        }
        Ok(())
    })?;
    let elapsed_ns = t.elapsed().as_nanos();
    let total_count: u64 = map.iter().map(|r| *r.value() as u64).sum();
    Ok(ArmOutcome {
        elapsed_ns,
        total_count,
        unique_count: map.len() as u64,
    })
}

/// Arm 3: no table — exactly `windows` Relaxed fetch_add(1) ops on one shared
/// AtomicU64 (mirroring the production per-window total) plus `distinct`
/// fetch_adds on a second (mirroring insert-time unique), distributed across
/// the same T workers.
fn run_atomic_only(windows: usize, distinct: usize, threads: usize) -> Result<ArmOutcome, String> {
    use std::sync::atomic::{AtomicU64, Ordering};
    let total = AtomicU64::new(0);
    let unique = AtomicU64::new(0);
    let ranges = disjoint_ranges(windows, threads);
    let w = ranges.len();
    let base = distinct / w;
    let rem = distinct % w;
    let t = Instant::now();
    std::thread::scope(|s| -> Result<(), String> {
        let mut handles = Vec::new();
        for (idx, (start, end)) in ranges.into_iter().enumerate() {
            let tot = &total;
            let uniq = &unique;
            let unique_share = base + usize::from(idx < rem);
            handles.push(s.spawn(move || -> Result<(), String> {
                for _ in start..end {
                    tot.fetch_add(1, Ordering::Relaxed);
                }
                for _ in 0..unique_share {
                    uniq.fetch_add(1, Ordering::Relaxed);
                }
                Ok(())
            }));
        }
        for h in handles {
            h.join()
                .map_err(|_| "atomic-only worker panicked".to_string())??;
        }
        Ok(())
    })?;
    let elapsed_ns = t.elapsed().as_nanos();
    Ok(ArmOutcome {
        elapsed_ns,
        total_count: total.load(std::sync::atomic::Ordering::Relaxed),
        unique_count: unique.load(std::sync::atomic::Ordering::Relaxed),
    })
}

/// Arm 4: thread-local tables + private totals, joined and reduced into one
/// map INSIDE the timed region — the locality/bandwidth control. Each private
/// HashMap is presized to its worker's slice so steady-state local table
/// traffic (not growth rehashing) is what the control measures. Evidence
/// only — NOT a production engine.
fn run_thread_local(keys: &[u64], threads: usize) -> Result<ArmOutcome, String> {
    use std::collections::HashMap;
    let ranges = disjoint_ranges(keys.len(), threads);
    let t = Instant::now();
    let partials = std::thread::scope(|s| -> Result<Vec<(HashMap<u64, u32>, u64)>, String> {
        let mut handles = Vec::new();
        for (start, end) in ranges {
            let slice = &keys[start..end];
            handles.push(s.spawn(move || -> Result<(HashMap<u64, u32>, u64), String> {
                let mut local: HashMap<u64, u32> = HashMap::with_capacity(slice.len());
                let mut local_total: u64 = 0;
                for &x in slice {
                    *local.entry(x).or_insert(0) += 1;
                    local_total += 1;
                }
                Ok((local, local_total))
            }));
        }
        let mut out = Vec::new();
        for h in handles {
            out.push(
                h.join()
                    .map_err(|_| "thread-local worker panicked".to_string())??,
            );
        }
        Ok(out)
    })?;
    let mut merged: HashMap<u64, u32> = HashMap::new();
    let mut private_total_sum: u64 = 0;
    for (map, local_total) in partials {
        private_total_sum += local_total;
        for (key, count) in map {
            *merged.entry(key).or_insert(0) += count;
        }
    }
    let elapsed_ns = t.elapsed().as_nanos();
    let total_count: u64 = merged.values().map(|c| *c as u64).sum();
    if private_total_sum != total_count {
        return Err(format!(
            "thread-local private totals ({private_total_sum}) disagree with merged sum ({total_count})"
        ));
    }
    Ok(ArmOutcome {
        elapsed_ns,
        total_count,
        unique_count: merged.len() as u64,
    })
}

fn flag_main(args: &[String]) {
    let flags = match parse_flags(args) {
        Ok(f) => f,
        Err(e) => {
            eprintln!("rk-microbench: {e}");
            std::process::exit(2);
        }
    };
    let reads = load_reads(&flags.input, flags.reads);
    if reads.is_empty() {
        eprintln!("rk-microbench: no reads loaded from {}", flags.input);
        std::process::exit(2);
    }
    key_identity_check(&reads, flags.k);
    let keys = preencode_keys(&reads, flags.k);
    let windows = keys.len();
    let distinct = precompute_distinct(&keys);
    println!(
        "k={} reads={} windows={} distinct={} variant={} threads={} reps={}",
        flags.k,
        reads.len(),
        windows,
        distinct,
        flags.variant,
        flags.threads,
        flags.reps
    );
    if windows == 0 {
        eprintln!("rk-microbench: zero k-mer windows — nothing to measure");
        std::process::exit(2);
    }

    let mut records: Vec<serde_json::Value> = Vec::new();
    for rep in 0..flags.reps {
        let outcome = match flags.variant.as_str() {
            "shared-counter" => run_shared_counter(&keys, flags.k, flags.threads),
            "shared-dashmap" => run_shared_dashmap(&keys, flags.threads),
            "atomic-only" => run_atomic_only(windows, distinct, flags.threads),
            "thread-local" => run_thread_local(&keys, flags.threads),
            other => {
                eprintln!("rk-microbench: unknown variant {other}");
                std::process::exit(2);
            }
        };
        let outcome = match outcome {
            Ok(o) => o,
            Err(e) => {
                eprintln!("rk-microbench: arm failed: {e}");
                std::process::exit(2);
            }
        };
        let conservation_ok =
            outcome.total_count == windows as u64 && outcome.unique_count == distinct as u64;
        if !conservation_ok {
            eprintln!(
                "CONSERVATION FAILURE variant={} rep={} threads={}: total_count={} (expected windows={}) unique_count={} (expected distinct={}) — run INVALID, aborting",
                flags.variant, rep, flags.threads, outcome.total_count, windows, outcome.unique_count, distinct
            );
            std::process::exit(1);
        }
        let ns_per_window = outcome.elapsed_ns as f64 / windows as f64;
        println!(
            "rep {rep}: {} t{} {:.3}s  {ns_per_window:.1} ns/window  total={} unique={} conservation=OK",
            flags.variant,
            flags.threads,
            outcome.elapsed_ns as f64 / 1e9,
            outcome.total_count,
            outcome.unique_count
        );
        records.push(serde_json::json!({
            "variant": flags.variant,
            "threads": flags.threads,
            "k": flags.k,
            "reads": reads.len(),
            "windows": windows,
            "distinct": distinct,
            "elapsed_ns": outcome.elapsed_ns as u64,
            "ns_per_window": ns_per_window,
            "total_count": outcome.total_count,
            "unique_count": outcome.unique_count,
            "conservation_ok": conservation_ok,
            "rep": rep,
        }));
    }

    if let Some(path) = &flags.json {
        let doc = serde_json::json!({ "records": records });
        let text = serde_json::to_string_pretty(&doc).unwrap();
        if let Err(e) = std::fs::write(path, text + "\n") {
            eprintln!("rk-microbench: cannot write JSON to {path}: {e}");
            std::process::exit(2);
        }
        println!("wrote {} records to {path}", records.len());
    }
}

fn main() {
    let args: Vec<String> = std::env::args().collect();
    if args.iter().skip(1).any(|a| a.starts_with("--")) {
        flag_main(&args);
    } else {
        legacy_main(&args);
    }
}
