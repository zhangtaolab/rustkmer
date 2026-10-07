//! DENSE-01 (plan 03-06) — the storage-width claim, asserted against the
//! representation a REAL `KmerCounter` actually stores.
//!
//! # Why this file exists
//!
//! Plan 03-03 shipped DENSE-01 with three assertions that all compared a
//! **model constant against itself**: `memory_usage()` derived its key width
//! from `kmer_length`, so `counter.memory_usage() == n * DENSE_BYTES_PER_ENTRY`
//! was true for *any* width. The mutation "always store the wide variant" left
//! every one of them green, while the underlying defect was real and measured:
//! `KmerKey` is an enum with a `u128` variant, so Rust gave it 16-byte
//! alignment and a 32-byte key, making the `(K, V)` slot the map stores 48
//! bytes instead of 32. A 4M-entry `/proc/self/status` probe of the pre-fix
//! tree measured **102.89 B/entry** for k ≤ 32 against **69.34 B/entry** for
//! the pre-Phase-3 `u128`-keyed map — ratio **1.487**. DENSE-01 claims the
//! opposite.
//!
//! # The two rules that make these tests non-vacuous
//!
//! 1. **Construct the production type.** Every assertion here builds a real
//!    `KmerCounter` through `KmerCounter::new`. A test that allocated its own
//!    local hash maps at both widths would measure the test binary's own
//!    allocations and would stay green under both the "always-Wide" mutation
//!    and a full revert of the counter to an enum-keyed map. This file
//!    therefore contains **no reference to the map type at all**, by design:
//!    `grep -c` for it over this file must print 0.
//! 2. **Observe the STORED representation.** `stored_key_bytes()` matches the
//!    live `CounterTable` variant rather than re-deriving the width from
//!    `kmer_length`. That is the single difference between this file and the
//!    three assertions it replaces.
//!
//! # Running this binary
//!
//! `k21_counting_memory_is_below_k64_over_the_same_entry_count` reads
//! `VmRSS` from `/proc/self/status`, which is a **process-global** measurement:
//! another thread allocating concurrently would be charged to whichever counter
//! happened to be alive. Run with `--test-threads=1`:
//!
//! ```text
//! cargo test --test dense_memory_tests -- --test-threads=1 --nocapture
//! ```
//!
//! The measurement is gated `#[cfg(target_os = "linux")]`; the other two tests
//! are unconditional and run everywhere.

use rustkmer::hash::table::KmerCounter;

/// Entry count for the RSS measurement.
///
/// Chosen to match the phase verifier's own 4M-entry probe so the numbers are
/// directly comparable to the 102.89 / 69.34 B/entry figures that motivated
/// this plan. Both counters get the SAME count, so the only difference between
/// them is the key width — which is the entire claim.
#[cfg(target_os = "linux")]
const MEASUREMENT_ENTRIES: usize = 4_000_000;

/// `(key, count)` is the slot the sharded map stores per entry. These are Rust
/// layout constants, asserted by `slot_layout_is_pinned_for_both_widths` so the
/// RSS ratio has a deterministic floor to stand on.
const DENSE_SLOT_BYTES: usize = core::mem::size_of::<(u64, u32)>();
const WIDE_SLOT_BYTES: usize = core::mem::size_of::<(u128, u32)>();

/// Current resident set size in kB, from `/proc/self/status`.
///
/// The `VmRSS:` line is in kB; the value before the unit is what we want.
#[cfg(target_os = "linux")]
fn vm_rss_kb() -> u64 {
    let status = std::fs::read_to_string("/proc/self/status")
        .expect("/proc/self/status must be readable on Linux");
    status
        .lines()
        .find_map(|line| {
            let rest = line.strip_prefix("VmRSS:")?;
            let value = rest.split_whitespace().next()?;
            value.parse::<u64>().ok()
        })
        .expect("/proc/self/status must carry a parseable VmRSS line (Linux-only path)")
}

/// What one measured counter cost, in bytes per entry.
#[cfg(target_os = "linux")]
#[derive(Debug, Clone, Copy)]
struct PerEntry {
    /// The `KmerCounter` is built with this `kmer_length`.
    kmer_length: usize,
    /// RSS delta across building + filling the counter.
    #[allow(
        dead_code,
        reason = "carried in the printed record and in the failure path"
    )]
    total_bytes: u64,
    /// Entries actually present when the measurement closed.
    unique_kmers: u64,
    /// What `stored_key_bytes()` reported for the live variant.
    stored_key_bytes: usize,
    /// `total_bytes / unique_kmers`, the comparable figure.
    bytes_per_entry: f64,
}

/// Build and fill a counter of `kmer_length`, returning it ALONG WITH the RSS
/// delta and entry count. Does NOT drop — the caller owns the returned counter
/// so the NEXT measurement cannot recycle this one's freed pages.
///
/// Distinct values `0..entries` are used on both widths so the two tables hold
/// exactly the same number of entries and differ only in key width.
/// `kmer_length` 21 and 64 both accept them (the dense path narrows
/// `0..4_000_000`, which is well inside `u64::MAX`; the wide path stores them
/// untruncated).
///
/// Holding the first counter while the second is measured is what makes the two
/// numbers comparable. An RSS *delta* measures how much fresh memory the
/// allocator had to obtain, so if the previous counter has already been dropped,
/// the new table can be satisfied entirely from free-list blocks that are
/// already resident — and the delta collapses. Measured that way, a 4M-entry
/// dense counter reads **2.51 B/entry, below its own 16-byte `(u64, u32)`
/// slot**, which is not a footprint measurement at all. With the sibling held
/// alive, the second delta must come from pages the process does not have, so
/// both deltas measure a genuine allocation rather than a reuse.
#[cfg(target_os = "linux")]
fn build_and_measure(kmer_length: usize, entries: usize) -> (KmerCounter, PerEntry) {
    let before = vm_rss_kb();
    let counter = KmerCounter::new(kmer_length, true, entries, 1).unwrap();
    for i in 0..entries {
        counter
            .increment(i as u128)
            .expect("distinct k-mers below u32::MAX cannot overflow");
    }
    let after = vm_rss_kb();

    // Read the counters BEFORE the caller drops them, so a fixture that
    // silently shrank fails loudly instead of measuring a smaller table and
    // reporting a flattering ratio.
    let unique_kmers = counter.unique_kmers();
    let stored_key_bytes = counter.stored_key_bytes();
    let total_bytes = after.saturating_sub(before) * 1024;

    (
        counter,
        PerEntry {
            kmer_length,
            total_bytes,
            unique_kmers,
            stored_key_bytes,
            bytes_per_entry: total_bytes as f64 / unique_kmers as f64,
        },
    )
}

/// Measure both widths in the given order, holding each counter while the next
/// is measured, then releasing both.
///
/// Returns `(k21, k64)` regardless of the order requested, so the caller can
/// run both orders and compare.
#[cfg(target_os = "linux")]
fn measure_both(first_k: usize, entries: usize) -> (PerEntry, PerEntry) {
    let (first_counter, first) = build_and_measure(first_k, entries);
    let second_k = if first_k == 21 { 64 } else { 21 };
    let (second_counter, second) = build_and_measure(second_k, entries);

    // Both measurements are complete; release in reverse build order.
    drop(second_counter);
    drop(first_counter);

    if first_k == 21 {
        (first, second)
    } else {
        (second, first)
    }
}

/// A deterministic layout pin — the floor the RSS ratio stands on, and
/// explicitly NOT the evidence that closes G1.
///
/// `size_of::<(u64, u32)>() == 16` is a **language constant**. No source
/// mutation can turn it red: force the production table to always be `Wide`
/// and this test still passes, because it never looks at the production type at
/// all. It is pinned here so that when `k21_counting_memory_is_below_k64_over_
/// the_same_entry_count` reports a ratio, there is a known slot size on both
/// sides for that ratio to be interpreted against.
///
/// The G1 evidence is `real_counter_reports_the_width_it_actually_stores` and
/// the RSS measurement — both construct a real `KmerCounter`, which is the only
/// thing this constant cannot do.
#[test]
fn slot_layout_is_pinned_for_both_widths() {
    assert_eq!(
        DENSE_SLOT_BYTES, 16,
        "a (u64, u32) map slot must be 16 bytes"
    );
    assert_eq!(
        WIDE_SLOT_BYTES, 32,
        "a (u128, u32) map slot must be 32 bytes"
    );
    assert_eq!(
        DENSE_SLOT_BYTES * 2,
        WIDE_SLOT_BYTES,
        "the wide slot must be exactly twice the dense one"
    );
    assert_eq!(
        core::mem::size_of::<u64>(),
        8,
        "the dense key width reported by stored_key_bytes must come from the type"
    );
    assert_eq!(
        core::mem::size_of::<u128>(),
        16,
        "the wide key width reported by stored_key_bytes must come from the type"
    );
}

/// DENSE-01's storage claim, asserted against the LIVE table.
///
/// This is the assertion that goes red under the mutation "always build the
/// `Wide` table": `stored_key_bytes()` matches the variant the counter actually
/// holds, so a k=21 counter that secretly stores `u128` keys reports 16, not 8,
/// and this fails. `uses_dense_storage()` flips at the same instant.
///
/// It also pins that the width belongs to the TABLE, not to its contents —
/// `reset()` empties the table and the reported width must not move.
#[test]
fn real_counter_reports_the_width_it_actually_stores() {
    for k in [1usize, 15, 21, 32] {
        let counter = KmerCounter::new(k, false, 64, 1).unwrap();

        // Empty table: the width is a property of the table itself.
        assert_eq!(
            counter.stored_key_bytes(),
            8,
            "k={k} must report an 8-byte stored key (dense u64 table)"
        );
        assert!(
            counter.uses_dense_storage(),
            "k={k} must be on the dense storage path"
        );

        // Populated: feeding a few k-mers must not change the reported width.
        for kmer in 1u128..=8 {
            counter.increment(kmer).unwrap();
        }
        assert_eq!(counter.unique_kmers(), 8);
        assert_eq!(
            counter.stored_key_bytes(),
            8,
            "k={k} must still report 8 stored key bytes with entries present"
        );
        assert!(
            counter.uses_dense_storage(),
            "k={k} must still be dense with entries present"
        );

        // Emptied: the width must survive `reset()` — it belongs to the table,
        // not to its contents.
        counter.reset();
        assert_eq!(counter.unique_kmers(), 0);
        assert_eq!(
            counter.stored_key_bytes(),
            8,
            "k={k} width must be unchanged after reset() — the width belongs to \
             the table, not to its contents"
        );
        assert!(
            counter.uses_dense_storage(),
            "k={k} must stay dense after reset"
        );
    }

    for k in [33usize, 48, 64] {
        let counter = KmerCounter::new(k, false, 64, 1).unwrap();
        assert_eq!(
            counter.stored_key_bytes(),
            16,
            "k={k} must report a 16-byte stored key (wide u128 table)"
        );
        assert!(
            !counter.uses_dense_storage(),
            "k={k} must not be on the dense storage path"
        );
        for kmer in 1u128..=8 {
            counter.increment(kmer).unwrap();
        }
        assert_eq!(
            counter.stored_key_bytes(),
            16,
            "k={k} must still report 16 stored key bytes with entries present"
        );
    }
}

/// DENSE-01 measured end to end: the k ≤ 32 counter must cost strictly fewer
/// bytes per entry than the k > 32 counter over the SAME entry count.
///
/// The pre-fix tree measured **102.89 B/entry (k=21) vs 69.34 (k=64), ratio
/// 1.487** — memory went UP ~49% for exactly the case DENSE-01 is about. This
/// test inverts that number.
///
/// Two real `KmerCounter`s are built and filled, one per width, at the same
/// entry count, and each is measured through `VmRSS` from `/proc/self/status`
/// around its own construction. The whole sequence then runs a SECOND time in
/// the reverse order and the smaller of the two ratios is asserted, so an
/// allocator-fragmentation ordering artifact cannot inflate the result — the
/// pre-fix measurement was taken in both orders precisely because ordering
/// matters at this scale.
///
/// Linux-only: the `/proc/self/status` read has no portable equivalent. Run the
/// binary with `--test-threads=1` — `VmRSS` is process-global, so a concurrent
/// test's allocations would be charged to whichever counter is alive.
#[cfg(target_os = "linux")]
#[test]
fn k21_counting_memory_is_below_k64_over_the_same_entry_count() {
    // Both orders, 4,000,000 entries each: 8 counters built in total. Within each
    // order the first counter is held alive while the second is measured — see
    // `build_and_measure` for why dropping it first would measure free-list
    // reuse instead of footprint.
    let (k21_a, k64_a) = measure_both(21, MEASUREMENT_ENTRIES);
    let (k21_b, k64_b) = measure_both(64, MEASUREMENT_ENTRIES);

    for measurement in [k21_a, k64_a, k21_b, k64_b] {
        assert_eq!(
            measurement.unique_kmers, MEASUREMENT_ENTRIES as u64,
            "k={} measurement must hold exactly {} entries — a fixture that \
             silently shrank would measure a smaller table and report a \
             flattering ratio",
            measurement.kmer_length, MEASUREMENT_ENTRIES
        );
        // Each measurement must also have observed the width it was built for.
        // Without this the ratio could be produced by two counters at the SAME
        // width that happened to land on different allocator states.
        let expected_key_bytes = if measurement.kmer_length <= 32 { 8 } else { 16 };
        assert_eq!(
            measurement.stored_key_bytes, expected_key_bytes,
            "the k={} measurement counter must report {} stored key bytes",
            measurement.kmer_length, expected_key_bytes
        );
    }

    let ratio_a = k21_a.bytes_per_entry / k64_a.bytes_per_entry;
    let ratio_b = k21_b.bytes_per_entry / k64_b.bytes_per_entry;
    let (k21, k64, ratio, order) = if ratio_a <= ratio_b {
        (k21_a, k64_a, ratio_a, "k21 first")
    } else {
        (k21_b, k64_b, ratio_b, "k64 first")
    };

    println!(
        "k21_bytes_per_entry = {:.2} (k=21, {} entries, stored_key_bytes = {}, order: {})",
        k21.bytes_per_entry, k21.unique_kmers, k21.stored_key_bytes, order
    );
    println!(
        "k64_bytes_per_entry = {:.2} (k=64, {} entries, stored_key_bytes = {}, order: {})",
        k64.bytes_per_entry, k64.unique_kmers, k64.stored_key_bytes, order
    );
    println!(
        "k21/k64 bytes-per-entry ratio = {:.4} (order A: {:.4}, order B: {:.4}) \
         [dense slot {} B, wide slot {} B]",
        ratio, ratio_a, ratio_b, DENSE_SLOT_BYTES, WIDE_SLOT_BYTES
    );
    println!(
        "pre-fix baseline for comparison: k=21 102.89 B/entry, k=64 69.34 B/entry, \
         ratio 1.487 (INVERTED — this is what plan 03-06 fixes)"
    );
    println!(
        "raw: A(k21-first) k21={:.2} k64={:.2} | B(k64-first) k21={:.2} k64={:.2}",
        k21_a.bytes_per_entry, k64_a.bytes_per_entry, k21_b.bytes_per_entry, k64_b.bytes_per_entry
    );

    // Both orders must agree that the dense counter is the cheaper one. Asserting
    // only the better of the two would let one bad ordering hide a real
    // regression.
    assert!(
        k21_a.bytes_per_entry < k64_a.bytes_per_entry,
        "k21-first: k=21 must cost strictly fewer bytes per entry than k=64 \
         (k21_bytes_per_entry = {:.2}, k64_bytes_per_entry = {:.2})",
        k21_a.bytes_per_entry,
        k64_a.bytes_per_entry
    );
    assert!(
        k21_b.bytes_per_entry < k64_b.bytes_per_entry,
        "k64-first: k=21 must cost strictly fewer bytes per entry than k=64 \
         (k21_bytes_per_entry = {:.2}, k64_bytes_per_entry = {:.2})",
        k21_b.bytes_per_entry,
        k64_b.bytes_per_entry
    );
    assert!(
        ratio < 1.0,
        "DENSE-01: k21/k64 bytes-per-entry ratio must be below 1.0 \
         (k21_bytes_per_entry = {:.2}, k64_bytes_per_entry = {:.2}, ratio = {:.4}, \
         order = {}). The pre-fix tree measured ratio 1.487 — memory INCREASED.",
        k21.bytes_per_entry,
        k64.bytes_per_entry,
        ratio,
        order
    );
}
