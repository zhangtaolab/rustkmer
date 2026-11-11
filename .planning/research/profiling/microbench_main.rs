//! Stage-isolation microbench for the rustkmer k=21 counting hot path.
//!
//! A: current production path (per-window O(k) encode + O(k) revcomp + DashMap)
//! B: rolling 2-bit encode + bit-parallel revcomp + same DashMap increment
//! C: DashMap increment only (pre-encoded keys)
//! D: rolling encode + canonical only (no table)
//! E: current encode + canonical only (no table)
//!
//! All single-threaded, same real reads, same KmerCounter type. Reports
//! ns per k-mer window. Keys produced by B are asserted identical to A.
//!
//! Usage: rk-microbench [k] [nreads] [variants]

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

fn main() {
    let args: Vec<String> = std::env::args().collect();
    let k: usize = args.get(1).map(|s| s.parse().unwrap()).unwrap_or(21);
    let nreads: usize = args.get(2).map(|s| s.parse().unwrap()).unwrap_or(200_000);
    let variants: String = args.get(3).cloned().unwrap_or_else(|| "ABCDE".into());
    let reads = load_reads("/tmp/rkmer-v2-prof/data/slice4M.fq", nreads);
    let windows: usize = reads.iter().map(|s| s.len().saturating_sub(k - 1)).sum();
    println!("k={k} reads={} windows~={windows} variants={variants}", reads.len());

    // Correctness: rolling keys == production keys.
    {
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